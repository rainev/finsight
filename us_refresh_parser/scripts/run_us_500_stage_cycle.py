#!/usr/bin/env python3
"""Check the approved active universe and stage only supported new filing values.

The active catalog is a read-only input. Unsupported or incomplete changes keep
their prior dated value and become explicit holds; this command never activates.
"""

from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
from datetime import date, datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.us_valuation.artifacts import sanitize_public_artifact  # noqa: E402
from app.us_valuation.private_integration import project_review_artifact  # noqa: E402
from app.us_valuation.calculation_recipe import evaluate_recipe  # noqa: E402
from app.us_valuation.calculator import baseline_version  # noqa: E402
from app.us_valuation.catalog import (  # noqa: E402
    artifact_tree_sha256, canonical_json_bytes, load_active_catalog,
    load_catalog_version, sha256_bytes,
)
from app.us_valuation.refresh_bindings import (  # noqa: E402
    AcquisitionIncomplete, EconomicException, bind_current_recipe,
)
from app.us_valuation.refresh_job import (  # noqa: E402
    configured_sec_user_agent, policy_readiness, refreshed_public,
    refreshed_recipe_version, writer,
)
from app.us_valuation.refresh_source_ingestion import capture_company_source, _event_with_index  # noqa: E402
from app.us_valuation.sec_client import SecClient  # noqa: E402
from app.us_valuation.table_first import inspect_tables, metadata_exceptions, VERSION as TABLE_VERSION  # noqa: E402


REGULAR_FORMS = {"10-K", "10-Q", "20-F", "40-F"}
EVENT_FORMS = {"8-K", "8-K/A", "6-K", "10-K/A", "10-Q/A", "20-F/A", "40-F/A"}


def _json(path: Path) -> dict:
    value = json.loads(path.read_bytes())
    if not isinstance(value, dict):
        raise ValueError(f"invalid JSON object: {path}")
    return value


def _filings(submissions: dict, cutoff: str) -> list[dict]:
    recent = submissions.get("filings", {}).get("recent", {})
    accessions = recent.get("accessionNumber", [])
    if not isinstance(accessions, list):
        raise ValueError("SEC submissions have no recent filing accessions")
    rows = []
    for index, accession in enumerate(accessions):
        row = {key: values[index] for key, values in recent.items()
               if isinstance(values, list) and index < len(values)}
        filed = row.get("filingDate")
        if isinstance(filed, str) and filed <= cutoff and row.get("accessionNumber") == accession:
            rows.append(row)
    return rows


def _latest_regular(rows: list[dict], *, private600_amendments: bool = False) -> dict | None:
    forms = REGULAR_FORMS | {'10-K/A','10-Q/A'} if private600_amendments else REGULAR_FORMS
    regular = [row for row in rows if row.get("form") in forms]
    return max(regular, key=lambda row: (row.get("filingDate", ""), row.get("acceptanceDateTime", ""))) if regular else None


class Sources:
    def __init__(self, *, state_root: Path, runtime_root: Path, offline_root: Path | None,
                 offline_packages_root: Path | None = None,
                 offline_event_cache_root: Path | None = None, table_first: bool = False):
        self.state_root = state_root
        self.offline_root = offline_root
        self.offline_packages_root = offline_packages_root
        self.offline_event_cache_root = offline_event_cache_root
        self.table_first = table_first
        self.user_agent = None if offline_root else configured_sec_user_agent(runtime_root)
        self.client = None if offline_root else SecClient(
            user_agent=self.user_agent, cache_dir=state_root / "sec-cache",
            requests_per_second=2, max_retries=2, timeout_seconds=30,
        )

    def submissions(self, ticker: str, cik: str) -> tuple[dict, str]:
        if self.offline_root:
            path = self.offline_root / "sec-cache" / f"CIK{cik}-submissions.json"
            raw = path.read_bytes()
            value = json.loads(raw)
        else:
            value = self.client.submissions(cik, refresh=True)
            path = self.state_root / "sec-cache" / f"CIK{cik}-submissions.json"
            raw = path.read_bytes()
        if str(value.get("cik", "")).zfill(10) != cik:
            raise ValueError(f"{ticker}: SEC submissions CIK mismatch")
        return value, sha256_bytes(raw)

    def packet(self, ticker: str, cik: str, cutoff: str, prior_cutoff: str) -> dict:
        if self.offline_root:
            if self.offline_packages_root:
                paths = {}
                for manifest_path in (self.offline_packages_root / ticker).rglob("package-manifest.json"):
                    manifest = _json(manifest_path)
                    accession = manifest.get("accession")
                    entrypoint_name = manifest.get("entrypoint_local_path")
                    if (not isinstance(accession, str) or not isinstance(entrypoint_name, str)
                            or manifest_path.parent.parent.parent.name != accession
                            or manifest.get("primary_document") != entrypoint_name):
                        raise ValueError(f"{ticker}: cached package identity mismatch")
                    entrypoint = (manifest_path.parent / entrypoint_name).resolve()
                    if not entrypoint.is_relative_to(manifest_path.parent.resolve()) or not entrypoint.is_file():
                        raise ValueError(f"{ticker}: unsafe or missing cached package entrypoint")
                    if accession in paths:
                        raise ValueError(f"{ticker}: duplicate cached package accession")
                    paths[accession] = entrypoint
                with tempfile.TemporaryDirectory(prefix="us500-offline-packet-") as packet_dir:
                    for source_name, cache_name in (
                        ("submissions.json", f"CIK{cik}-submissions.json"),
                        ("companyfacts.json", f"CIK{cik}-companyfacts.json"),
                    ):
                        (Path(packet_dir) / source_name).symlink_to(
                            (self.offline_root / "sec-cache" / cache_name).resolve())
                    packet = capture_company_source(
                        ticker=ticker, cik=cik, cutoff=cutoff,
                        offline_packet_dir=Path(packet_dir),
                        event_since=prior_cutoff, capture_event_relationships=not self.table_first,
                        capture_events=not self.table_first,
                        require_structural=True, structural_paths=paths,
                        parsed_cache_dir=self.state_root / "parsed",
                        compress_parsed_cache=True,
                    )
                    if self.offline_event_cache_root and not self.table_first:
                        client = ReadOnlyEventCache(
                            user_agent=None, cache_dir=self.offline_event_cache_root)
                        packet["events"] = [
                            _event_with_index(client, event, cik=cik, refresh=False)
                            for event in packet["events"]
                        ]
                    return packet
            path = self.offline_root / "captures" / f"{ticker}.json.gz"
            if not path.is_file():
                path = path.with_suffix("")
            if not path.is_file():
                raise AcquisitionIncomplete('current financial-filing source packet is missing; prior dated estimate retained')
            raw = path.read_bytes()
            receipt = json.loads(gzip.decompress(raw) if path.suffix == ".gz" else raw)
            packet = receipt["packet"]
            if receipt.get("ticker") != ticker or str(receipt.get("cik", "")).zfill(10) != cik:
                raise ValueError("offline packet identity mismatch")
            if sha256_bytes(canonical_json_bytes(packet)) != receipt.get("packet_sha256"):
                raise ValueError("offline packet hash mismatch")
            return packet
        return capture_company_source(
            ticker=ticker, cik=cik, cutoff=cutoff,
            cache_dir=self.state_root / "sec-cache", user_agent=self.user_agent,
            refresh=True, event_since=prior_cutoff,
            require_structural=True, capture_event_relationships=not getattr(self, 'table_first', False),
            capture_events=not getattr(self, 'table_first', False),
            structural_output_dir=self.state_root / "filings",
            parsed_cache_dir=self.state_root / "parsed",
            resource_store=self.state_root / "resource-store",
            compress_parsed_cache=True,
        )


def _write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


class ReadOnlyEventCache(SecClient):
    """Reuse independently hashed SEC archive files; a miss cannot reach the network."""

    @staticmethod
    def _write_cache_metadata(path: Path, *, url: str, raw: bytes,
                              fetched_at_epoch: float | None) -> None:
        if fetched_at_epoch is not None:
            raise RuntimeError("offline event replay attempted a network fetch")
        metadata_path = path.with_suffix(path.suffix + ".meta.json")
        metadata = _json(metadata_path)
        if metadata.get("sha256") != sha256_bytes(raw) or metadata.get("source_url") != url:
            raise ValueError(f"cached event source hash or URL mismatch: {path.name}")


def run_cycle(*, catalogs_root: Path, runtime_root: Path, state_root: Path,
              cutoff: str, offline_root: Path | None = None,
              offline_packages_root: Path | None = None,
              offline_event_cache_root: Path | None = None,
              table_first: bool = True, selected_tickers: set[str] | None = None,
              recheck_unavailable: bool = False, baseline_catalog: Path | None = None) -> dict:
    date.fromisoformat(cutoff)
    catalogs_root, runtime_root, state_root = (Path(value).resolve() for value in
                                               (catalogs_root, runtime_root, state_root))
    offline_root = Path(offline_root).resolve() if offline_root else None
    if baseline_catalog is not None and offline_root is None:
        raise ValueError('explicit staged baseline requires offline source snapshots')
    offline_packages_root = Path(offline_packages_root).resolve() if offline_packages_root else None
    offline_event_cache_root = Path(offline_event_cache_root).resolve() if offline_event_cache_root else None
    if offline_packages_root and not offline_root:
        raise ValueError("cached packages require offline source snapshots")
    if offline_event_cache_root and not offline_packages_root:
        raise ValueError("cached events require offline structural packages")
    if state_root.is_relative_to(catalogs_root) or catalogs_root.is_relative_to(state_root):
        raise ValueError("private stage and active catalog roots must be separate")
    with writer(state_root):
        pointer = (catalogs_root / "active.json").read_bytes()
        active = load_catalog_version(Path(baseline_catalog)) if baseline_catalog is not None else load_active_catalog(catalogs_root)
        quality06_schema = active.manifest.get('approved_base_inheritance', {}).get('schema_version')
        if quality06_schema in {'US-QUALITY06-OFFLINE-RETENTION-CHILD-1','US-QUALITY06-ADMITTED-RETENTION-CHILD-1'}:
            raise ValueError('Quality06 verification-only child cannot start another source cycle')
        if (quality06_schema == 'US-QUALITY06-STAGED-INHERITANCE-1'
                and (offline_root is None or os.environ.get('APP_ENV') != 'test')):
            raise ValueError('Quality06 staged runner requires isolated offline replay; no live source authority')
        if ((active.manifest.get('staged_review', active.manifest.get('private_review', {})).get('profile') in {'B11-B15-FROZEN-PRIVATE-1','B16-B20-FROZEN-PRIVATE-1','B16-B20-STAGED-PUBLIC-1'}
                or active.manifest.get('approved_base_inheritance', {}).get('schema_version') in {'US-B11-B15-APPROVED-PARENT-INHERITANCE-1','US-B1115-QUALITY-STAGED-INHERITANCE-1','US-B1115-QUALITY-RETENTION-CHILD-1'})
                and (offline_root is None or os.environ.get('APP_ENV') != 'test')):
            raise ValueError('private650 runner requires isolated offline replay; staged650 also prohibits live SEC capture')
        catalog_count = len(active.entries)
        if active.manifest.get('approved_base_inheritance',{}).get('schema_version') in {
                'US-QUALITY03-OFFLINE-RETENTION-CHILD-1',
                'US-QUALITY03-ADMITTED-RETENTION-CHILD-1'}:
            raise ValueError('Quality03 verification-only child cannot start another source cycle')
        if (active.manifest.get('approved_base_inheritance',{}).get('schema_version') == 'US-QUALITY03-STAGED-INHERITANCE-1'
                and (offline_root is None or os.environ.get('APP_ENV') != 'test')):
            raise ValueError('Quality03 staged runner requires isolated offline replay; no live source authority')
        if active.manifest.get('approved_base_inheritance',{}).get('schema_version') in {'US-QUALITY04-OFFLINE-RETENTION-CHILD-1','US-QUALITY04-ADMITTED-RETENTION-CHILD-1'}:
            raise ValueError('Quality04 verification-only child cannot start another source cycle')
        if active.manifest.get('approved_base_inheritance',{}).get('schema_version') in {'US-QUALITY05-OFFLINE-RETENTION-CHILD-1','US-QUALITY05-ADMITTED-RETENTION-CHILD-1'}:
            raise ValueError('Quality05 verification-only child cannot start another source cycle')
        if (active.manifest.get('approved_base_inheritance',{}).get('schema_version') == 'US-QUALITY05-STAGED-INHERITANCE-1'
                and (offline_root is None or os.environ.get('APP_ENV') != 'test')):
            raise ValueError('Quality05 staged runner requires isolated offline replay; no live source authority')
        if (active.manifest.get('approved_base_inheritance',{}).get('schema_version') == 'US-QUALITY04-STAGED-INHERITANCE-1'
                and (offline_root is None or os.environ.get('APP_ENV') != 'test')):
            raise ValueError('Quality04 staged runner requires isolated offline replay; no live source authority')
        if active.manifest.get('approved_base_inheritance',{}).get('schema_version') in {
                'US-QUALITY02-OFFLINE-RETENTION-CHILD-1',
                'US-QUALITY02-ADMITTED-RETENTION-CHILD-1'}:
            raise ValueError('Quality02 verification-only child cannot start another source cycle')
        if (active.manifest.get('approved_base_inheritance',{}).get('schema_version') == 'US-QUALITY02-STAGED-INHERITANCE-1'
                and (offline_root is None or os.environ.get('APP_ENV') != 'test')):
            raise ValueError('Quality02 staged runner requires isolated offline replay; no live source authority')
        if selected_tickers is not None and (not selected_tickers or not selected_tickers <= {e.ticker for e in active.entries}):
            raise ValueError('selected validation issuers must belong to the active catalog')
        registry = _json(runtime_root / "registry.json")
        identities = {(row["ticker"], str(row["cik"]).zfill(10), row["batch"]) for row in registry["entries"]}
        if len(registry["entries"]) != catalog_count or identities != {(row.ticker, row.cik, row.batch) for row in active.entries}:
            raise ValueError("refresh policy registry differs from the active issuer set")
        policies = _json(runtime_root / "refresh-policies.json")
        quality06 = active.manifest.get('approved_base_inheritance', {}).get('schema_version') == 'US-QUALITY06-STAGED-INHERITANCE-1'
        # The current authenticated quality binding, not an unrelated staged
        # module or the scratch-directory variable, defines private holds.
        binding_path = active.root / 'quality-source-binding.json'
        if binding_path.is_file():
            hold_members = _json(binding_path).get('private_held_updates', [])
            if (not isinstance(hold_members, list)
                    or not all(isinstance(t, str) for t in hold_members)
                    or len(hold_members) != len(set(hold_members))
                    or not set(hold_members) <= {entry.ticker for entry in active.entries}):
                raise ValueError('invalid profile-specific private quality hold membership')
            private_quality_holds = frozenset(hold_members)
        else:
            private_quality_holds = frozenset(
                ticker for ticker, status in active.manifest.get('refresh_status', {}).items()
                if status.get('private_quality_hold') is True)
        sources = Sources(state_root=state_root, runtime_root=runtime_root,
                          offline_root=offline_root, offline_packages_root=offline_packages_root,
                          offline_event_cache_root=offline_event_cache_root, table_first=table_first)
        entries: list[dict] = []
        artifacts: dict[str, bytes] = {}
        recipes: dict[str, bytes] = {}
        statuses: dict[str, dict] = {}
        private_rows: list[dict] = []
        source_binding_proofs = {}
        changed = 0
        consecutive_metadata_failures = 0
        for entry in active.entries:
            ticker, cik = entry.ticker, entry.cik
            old_bytes = active.verify_artifact(ticker).read_bytes()
            if active.manifest.get('approved_base_inheritance',{}).get('schema_version') in {
                    'US-QUALITY03-STAGED-INHERITANCE-1',
                    'US-QUALITY05-STAGED-INHERITANCE-1',
                    'US-B1620-LOCAL-ADMISSION-INHERITANCE-1','US-QUALITY06-LOCAL-ADMISSION-INHERITANCE-1','US-QUALITY05-LOCAL-ADMISSION-INHERITANCE-1',
                    'US-QUALITY06-ADMITTED-RETENTION-CHILD-1','US-QUALITY05-ADMITTED-RETENTION-CHILD-1',
                    'US-QUALITY04-STAGED-INHERITANCE-1',
                    'US-QUALITY02-STAGED-INHERITANCE-1',
                    'US-QUALITY02-LOCAL-ADMISSION-INHERITANCE-1',
                    'US-QUALITY03-LOCAL-ADMISSION-INHERITANCE-1',
                    'US-QUALITY04-LOCAL-ADMISSION-INHERITANCE-1'}:
                from app.us_valuation.approved_inheritance import preserved_original
                from app.us_valuation.artifacts import sanitize_public_artifact
                old_raw = json.loads(old_bytes)
                old = old_raw if preserved_original(active.root,active.manifest,ticker,old_bytes) else sanitize_public_artifact(old_raw)
            else:
                old = project_review_artifact(json.loads(old_bytes), active.manifest,
                                              ticker=ticker, artifact_sha256=entry.artifact_sha256)
            old_source = old["source_financial_statement"]
            old_accession = old_source["accession"]
            old_filed = old_source["filed_date"]
            expected_recipe = active.manifest.get("private_recipe_sha256", {}).get(ticker)
            recipe_bytes = None
            recipe = None
            if expected_recipe:
                recipe_bytes = (active.root / "recipes" / f"{ticker}.json").read_bytes()
                if sha256_bytes(recipe_bytes) != expected_recipe:
                    raise ValueError(f"{ticker}: active private recipe hash mismatch")
                recipe = json.loads(recipe_bytes)
                if recipe.get("ticker") != ticker or recipe.get("baseline_version") != baseline_version(old):
                    raise ValueError(f"{ticker}: active recipe/baseline mismatch")
            outcome, reason, metadata_hash, latest = "checked_unchanged", None, None, None
            table_audit = None
            if selected_tickers is not None and ticker not in selected_tickers:
                artifacts[ticker] = old_bytes
                if recipe_bytes is not None:
                    recipes[ticker] = recipe_bytes
                entries.append(deepcopy(active.manifest['entries'][len(entries)]))
                statuses[ticker] = deepcopy(active.manifest.get('refresh_status', {}).get(ticker, {}))
                continue
            try:
                submissions, metadata_hash = sources.submissions(ticker, cik)
                consecutive_metadata_failures = 0
                filings = _filings(submissions, cutoff)
                latest = _latest_regular(filings, private600_amendments=(
                    active.manifest.get('staged_review', active.manifest.get('private_review', {})).get('profile') in {'B06-B10-FROZEN-PRIVATE-1','B11-B15-FROZEN-PRIVATE-1','B16-B20-FROZEN-PRIVATE-1','B16-B20-STAGED-PUBLIC-1'}
                    or active.manifest.get('approved_base_inheritance',{}).get('schema_version') in {
                        'US-B06-B10-APPROVED-PARENT-INHERITANCE-1',
                        'US-B11-B15-APPROVED-PARENT-INHERITANCE-1',
                        'US-QUALITY02-STAGED-INHERITANCE-1',
                        'US-QUALITY03-STAGED-INHERITANCE-1',
                        'US-QUALITY05-STAGED-INHERITANCE-1',
                        'US-B1620-LOCAL-ADMISSION-INHERITANCE-1','US-QUALITY06-LOCAL-ADMISSION-INHERITANCE-1','US-QUALITY05-LOCAL-ADMISSION-INHERITANCE-1',
                        'US-QUALITY06-ADMITTED-RETENTION-CHILD-1','US-QUALITY05-ADMITTED-RETENTION-CHILD-1',
                        'US-QUALITY06-STAGED-INHERITANCE-1',
                        'US-QUALITY04-STAGED-INHERITANCE-1',
                        'US-QUALITY02-LOCAL-ADMISSION-INHERITANCE-1',
                        'US-QUALITY03-LOCAL-ADMISSION-INHERITANCE-1',
                        'US-QUALITY04-LOCAL-ADMISSION-INHERITANCE-1',
                        'US-B1115-QUALITY-STAGED-INHERITANCE-1',
                        'US-B1115-QUALITY-LOCAL-ADMISSION-INHERITANCE-1',
                        'US-B06-B10-LOCAL-ADMISSION-INHERITANCE-1',
                        'US-B11-B15-LOCAL-ADMISSION-INHERITANCE-1'}))
                if quality06:
                    # Quality06 is a retention/status child.  Metadata is
                    # inspected from the isolated offline snapshot, but a
                    # changed quarter/amendment is held before packet capture,
                    # binding, calculation, or source-bound replacement.
                    from app.us_valuation import quality06_staged as quality06_contract
                    amendments = [row for row in filings
                                  if row.get('form') in {'10-K/A', '10-Q/A'}
                                  and row.get('filingDate', '') > old_filed]
                    changed_metadata = (latest is None
                                        or latest['accessionNumber'] != old_accession
                                        or bool(amendments)
                                        or bool(metadata_exceptions(filings, since=old_filed)))
                    if changed_metadata:
                        outcome, reason = 'held_new_filing', 'Quality06 filing/amendment/metadata change held before source capture.'
                    elif latest is None:
                        outcome, reason = 'held_new_filing', 'Quality06 metadata has no eligible filing.'
                    else:
                        outcome, reason = 'checked_unchanged', None
                elif table_first:
                    policy = policies.get(ticker)
                    private_hold = (isinstance(policy, dict) and
                                    policy.get('schema_version') in {
                                        'FINSIGHT-PRIVATE-EXPANSION-HOLD-POLICY-1',
                                        'FINSIGHT-STAGED-EXPANSION-REVIEW-HOLD-1'})
                    declared_epoch=(isinstance(policy,dict) and policy.get('schema_version')=='FINSIGHT-B01-SUPPORTED-REFRESH-1')
                    review_since = policy.get('source_epoch', old_filed) if private_hold or declared_epoch else old_filed
                    problems = metadata_exceptions(filings, since=review_since)
                    if active.manifest.get('approved_base_inheritance', {}).get('schema_version') == 'US-B1620-LOCAL-ADMISSION-INHERITANCE-1':
                        from app.us_valuation.admitted_batches1620 import metadata_hold
                        problem = metadata_hold(ticker, submissions, cutoff)
                        if problem:
                            problems = [{'detail': problem}, *problems]
                    if active.manifest.get('staged_review', active.manifest.get('private_review', {})).get('profile') in {'B16-B20-FROZEN-PRIVATE-1','B16-B20-STAGED-PUBLIC-1'}:
                        if active.manifest.get('staged_review', {}).get('profile') == 'B16-B20-STAGED-PUBLIC-1':
                            from app.us_valuation.staged_batches1620 import metadata_hold
                        else:
                            from app.us_valuation.private_batches1620 import metadata_hold
                        frozen_problem = metadata_hold(ticker, submissions, cutoff)
                        if frozen_problem:
                            problems = [{'detail': frozen_problem}, *problems]
                    amendments = [r for r in filings if r.get('form') in {'10-K/A', '10-Q/A'}
                                  and r.get('filingDate', '') > review_since]
                    if latest is None:
                        outcome, reason = 'held_new_filing', 'missing_essential_input: no eligible financial filing'
                    elif problems:
                        outcome, reason = 'held_new_filing', problems[0]['detail']
                    elif latest['accessionNumber'] == old_accession and not amendments and (not recheck_unavailable or recipe is not None):
                        outcome = 'checked_unchanged'
                    elif private_hold:
                        changed += int(latest['accessionNumber'] != old_accession)
                        ready, why = policy_readiness(recipe or {'ticker': ticker, 'cik': cik, 'private_only': True}, policy)
                        if ready:
                            raise RuntimeError('private expansion hold cannot enable automatic revaluation')
                        outcome, reason = 'held_new_filing', why or 'private expansion requires source review'
                    else:
                        changed += int(latest['accessionNumber'] != old_accession)
                        packet = sources.packet(ticker, cik, cutoff, (recipe or {}).get('evidence_cutoff', old_filed))
                        if (packet.get('controlling_filing') or {}).get('accessionNumber') != latest['accessionNumber']:
                            raise AcquisitionIncomplete('captured filing differs from selected SEC financial metadata')
                        table_audit = inspect_tables(packet, cik=cik, cutoff=cutoff, recipe=recipe)
                        digest = sha256_bytes(canonical_json_bytes(table_audit))
                        _write(state_root / 'table-audits' / f'{ticker}-{digest}.json', canonical_json_bytes(table_audit))
                        if table_audit['exceptions']:
                            outcome, reason = 'held_new_filing', '; '.join(f"{r['code']}:{r['field']}: {r['detail']}" for r in table_audit['exceptions'])
                        elif recipe is None:
                            outcome, reason = 'held_new_filing', 'missing_model_recipe: financial tables were extracted, but the existing valuation has no executable recipe or scenario assumptions to update.'
                        else:
                            policy = policies.get(ticker)
                            ready, why = policy_readiness(recipe, policy)
                            if not ready:
                                outcome, reason = 'held_new_filing', 'missing_model_binding: ' + (why or 'source input mapping is incomplete')
                            else:
                                registry_entry = next(row for row in registry['entries'] if row['ticker'] == ticker)
                                updated, ledger = bind_current_recipe({**registry_entry, 'refresh_policy': policy}, recipe, packet, cutoff, table_first=True, staged_only=True)
                                updated['recipe_version'] = refreshed_recipe_version(updated, {**policy, 'refresh_mode': TABLE_VERSION})
                                ledger['assumption_date'] = old.get('assumption_date', old['valuation_date'])
                                valued = evaluate_recipe(updated)
                                public = refreshed_public(old, updated, valued, ledger, cutoff, output_policy=policy)
                                updated['baseline_version'] = baseline_version(public)
                                updated['replay'] = deepcopy(valued['range'])
                                recipe_bytes, old_bytes = canonical_json_bytes(updated), canonical_json_bytes(public)
                                _write(state_root / 'ledgers' / f'{ticker}-{sha256_bytes(canonical_json_bytes(ledger))}.json', canonical_json_bytes(ledger))
                                if policy.get('schema_version')=='FINSIGHT-B01-SUPPORTED-REFRESH-1':
                                    ledger.update(ticker=ticker,cik=cik)
                                    source_binding_proofs[ticker]=canonical_json_bytes(ledger)
                                outcome, reason = 'source_bound', None
                elif latest is None:
                    outcome, reason = "held_new_filing", "No eligible regular filing was identified."
                elif latest["accessionNumber"] == old_accession:
                    events = [row for row in filings if row.get("form") in EVENT_FORMS
                              and row.get("filingDate", "") > old_filed]
                    if events:
                        outcome, reason = "held_new_filing", "A later event or amendment requires review."
                else:
                    changed += 1
                    if recipe is None:
                        outcome, reason = "held_new_filing", "No supported intrinsic recipe exists."
                    else:
                        policy = policies.get(ticker)
                        ready, why = policy_readiness(recipe, policy)
                        if not ready:
                            outcome, reason = "held_new_filing", why or "Filing-to-model binding is not ready."
                        else:
                            packet = sources.packet(ticker, cik, cutoff, recipe["evidence_cutoff"])
                            controlling = packet.get("controlling_filing") or {}
                            if controlling.get("accessionNumber") != latest["accessionNumber"]:
                                raise AcquisitionIncomplete("captured filing differs from current SEC metadata")
                            registry_entry = next(row for row in registry["entries"] if row["ticker"] == ticker)
                            updated, ledger = bind_current_recipe(
                                {**registry_entry, "refresh_policy": policy}, recipe, packet, cutoff, staged_only=True)
                            updated["recipe_version"] = refreshed_recipe_version(updated, policy)
                            ledger["assumption_date"] = cutoff
                            valued = evaluate_recipe(updated)
                            public = refreshed_public(old, updated, valued, ledger, cutoff,
                                                      output_policy=policy)
                            if public["source_financial_statement"]["accession"] != latest["accessionNumber"]:
                                raise ValueError("refreshed artifact does not cite the new filing")
                            updated["baseline_version"] = baseline_version(public)
                            updated["replay"] = deepcopy(valued["range"])
                            recipe_bytes = canonical_json_bytes(updated)
                            old_bytes = canonical_json_bytes(public)
                            outcome, reason = "source_bound", None
            except (OSError, ValueError, RuntimeError, KeyError) as exc:
                outcome, reason = "held_new_filing", f"{type(exc).__name__}: {exc}"
                if metadata_hash is None:
                    consecutive_metadata_failures += 1
                    if consecutive_metadata_failures >= 3:
                        raise RuntimeError("three consecutive SEC metadata failures; retry later") from exc
            if entry.availability_type == "not_available" and outcome == "checked_unchanged":
                outcome = "prior_unavailable"
            artifacts[ticker] = old_bytes
            if recipe_bytes is not None:
                recipes[ticker] = recipe_bytes
            public_reason = ("Supported new filing recalculation staged for review."
                             if outcome == "source_bound" else
                             "New or unresolved filing evidence is held; prior dated value retained."
                             if outcome == "held_new_filing" else
                             "Prior unavailable result retained."
                             if outcome == "prior_unavailable" else
                             "No new eligible filing; dated value retained.")
            statuses[ticker] = {"outcome": outcome, "checked_as_of": cutoff,
                                "recommendation": public_reason,
                                "new_source_date": latest.get("filingDate") if latest else None,
                                "private_quality_hold": ticker in private_quality_holds,
                                "private_quality_hold_preserved": ticker in private_quality_holds}
            entries.append({**active.manifest["entries"][len(entries)],
                            "artifact_sha256": sha256_bytes(old_bytes),
                            "availability_type": json.loads(old_bytes)["availability_type"]})
            private_rows.append({"ticker": ticker, "outcome": outcome, "reason": reason,
                                 "metadata_sha256": metadata_hash,
                                 "latest_accession": latest.get("accessionNumber") if latest else None,
                                 "prior_accession": old_accession,
                                 "table_audit": table_audit,
                                 "private_quality_hold": ticker in private_quality_holds,
                                 "private_quality_hold_preserved": ticker in private_quality_holds})
            if ((active.manifest.get('staged_review', active.manifest.get('private_review', {})).get('profile') in {'B11-B15-FROZEN-PRIVATE-1','B16-B20-FROZEN-PRIVATE-1','B16-B20-STAGED-PUBLIC-1'}
                    or active.manifest.get('approved_base_inheritance', {}).get('schema_version') in {'US-QUALITY05-STAGED-INHERITANCE-1','US-B1620-LOCAL-ADMISSION-INHERITANCE-1','US-QUALITY06-LOCAL-ADMISSION-INHERITANCE-1','US-QUALITY05-LOCAL-ADMISSION-INHERITANCE-1','US-QUALITY06-ADMITTED-RETENTION-CHILD-1','US-QUALITY05-ADMITTED-RETENTION-CHILD-1','US-QUALITY04-LOCAL-ADMISSION-INHERITANCE-1','US-QUALITY03-STAGED-INHERITANCE-1','US-B11-B15-APPROVED-PARENT-INHERITANCE-1','US-B1115-QUALITY-STAGED-INHERITANCE-1','US-B1115-QUALITY-LOCAL-ADMISSION-INHERITANCE-1','US-QUALITY02-LOCAL-ADMISSION-INHERITANCE-1','US-QUALITY03-LOCAL-ADMISSION-INHERITANCE-1'})
                    and ticker in {'CBT','UTMD'}):
                from app.us_valuation.private_batches1115 import DATED_ONLY
                scope = {**DATED_ONLY[ticker], 'valuation_scope':'dated_financial_reference_only'}
                if policies[ticker].get('dated_only') != DATED_ONLY[ticker]:
                    raise ValueError('private650 dated-only/current hold policy changed')
                statuses[ticker].update(scope)
                private_rows[-1].update(scope)
        counts = Counter(row["outcome"] for row in private_rows)
        candidate = None
        if counts["source_bound"] or table_first:
            material = {"base_manifest_sha256": active.manifest_sha256, "cutoff": cutoff,
                        "entries": entries, "recipe_sha256": {t: sha256_bytes(b) for t, b in sorted(recipes.items())},
                        "metadata_sha256": {row["ticker"]: row["metadata_sha256"] for row in private_rows},
                        "refresh_mode": TABLE_VERSION if table_first else 'legacy',
                        "policy_sha256": sha256_bytes(canonical_json_bytes(policies)),
                        "statuses": statuses,
                        "audit_sha256": sha256_bytes(canonical_json_bytes(private_rows))}
            run_id = sha256_bytes(canonical_json_bytes(material))[:24]
            version = f"US-REFRESH-{catalog_count}-{cutoff}-{run_id}"
            destination = state_root / "candidates" / version
            if destination.exists():
                validated = load_catalog_version(destination)
            else:
                destination.parent.mkdir(parents=True, exist_ok=True)
                stage = Path(tempfile.mkdtemp(prefix=".us-refresh-", dir=destination.parent))
                try:
                    for ticker, payload in artifacts.items():
                        _write(stage / "artifacts" / f"{ticker}.json", payload)
                    for ticker, payload in recipes.items():
                        _write(stage / "recipes" / f"{ticker}.json", payload)
                    availability = Counter(row["availability_type"] for row in entries)
                    manifest = {**active.manifest,
                        "catalog_version": version, "valuation_date": cutoff,
                        "base_catalog_version": active.catalog_version,
                        "base_manifest_sha256": active.manifest_sha256,
                        "entries": entries, "artifact_count": catalog_count,
                        "artifact_tree_sha256": artifact_tree_sha256(entries),
                        "availability_counts": {key: availability[key] for key in
                                                ("available", "conditional_estimate", "not_available")},
                        "publication_counts": dict(Counter(json.loads(payload)['review']['publication_state'] for payload in artifacts.values())),
                        "private_recipe_sha256": {t: sha256_bytes(b) for t, b in sorted(recipes.items())},
                        "refresh_status": statuses, "refresh_cutoff": cutoff,
                        "input_fingerprints": {"run_id": run_id},
                    }
                    if ((active.manifest.get('private_integration_only') is True
                            and active.manifest.get('staged_review', active.manifest.get('private_review', {})).get('profile') in {
                                'B04-FROZEN-PRIVATE-1', 'B05-FROZEN-PRIVATE-1', 'B06-B10-FROZEN-PRIVATE-1', 'B11-B15-FROZEN-PRIVATE-1', 'B16-B20-FROZEN-PRIVATE-1','B16-B20-STAGED-PUBLIC-1'})
                            or active.manifest.get('approved_base_inheritance',{}).get('schema_version') in {
                                'US-B04-APPROVED-PARENT-INHERITANCE-1',
                                'US-B05-APPROVED-PARENT-INHERITANCE-1',
                                'US-B06-B10-APPROVED-PARENT-INHERITANCE-1',
                                'US-B11-B15-APPROVED-PARENT-INHERITANCE-1',
                                'US-QUALITY05-STAGED-INHERITANCE-1',
                                'US-B1620-LOCAL-ADMISSION-INHERITANCE-1','US-QUALITY06-LOCAL-ADMISSION-INHERITANCE-1','US-QUALITY05-LOCAL-ADMISSION-INHERITANCE-1',
                                'US-QUALITY05-ADMITTED-RETENTION-CHILD-1'}):
                        # The refresh predecessor is not a new private approval.
                        # Keep the authenticated admitted530 parent contract; bind
                        # this inactive refresh's 540 parent separately.
                        manifest['refresh_parent_catalog_version']=active.catalog_version
                        manifest['refresh_parent_manifest_sha256']=active.manifest_sha256
                        manifest['base_catalog_version']=active.manifest['base_catalog_version']
                        manifest['base_manifest_sha256']=active.manifest['base_manifest_sha256']
                    if active.manifest.get('approved_base_inheritance', {}).get('schema_version') == 'US-B1620-LOCAL-ADMISSION-INHERITANCE-1':
                        manifest.update(approved_base_inheritance={**active.manifest['approved_base_inheritance'], 'schema_version':'US-B1620-ADMITTED-RETENTION-CHILD-1'},
                            admission=False, activation=False, publication=False, staged_release_only=True, admission_prepared_only=True, catalog_kind='unadmitted_expansion1620_retention_child')
                        manifest.pop('local_admission', None)
                        manifest['refresh_parent_catalog_version']=active.catalog_version
                        manifest['refresh_parent_manifest_sha256']=active.manifest_sha256
                        manifest['base_catalog_version']=active.manifest['base_catalog_version']
                        manifest['base_manifest_sha256']=active.manifest['base_manifest_sha256']
                    if active.manifest.get('staged_review', {}).get('profile') == 'B16-B20-STAGED-PUBLIC-1':
                        manifest['refresh_parent_catalog_version']=active.catalog_version
                        manifest['refresh_parent_manifest_sha256']=active.manifest_sha256
                        manifest['base_catalog_version']=active.manifest['base_catalog_version']
                        manifest['base_manifest_sha256']=active.manifest['base_manifest_sha256']
                    if active.manifest.get('private_refresh_policy_sha256'):
                        policy_bytes=canonical_json_bytes(policies)
                        _write(stage/'refresh-policies.json',policy_bytes)
                        manifest['private_refresh_policy_sha256']=sha256_bytes(policy_bytes)
                    quality03_retention = active.manifest.get('approved_base_inheritance',{}).get('schema_version') == 'US-QUALITY03-STAGED-INHERITANCE-1'
                    quality02_retention = active.manifest.get('approved_base_inheritance',{}).get('schema_version') == 'US-QUALITY02-STAGED-INHERITANCE-1'
                    quality02_admitted_retention = active.manifest.get('approved_base_inheritance',{}).get('schema_version') == 'US-QUALITY02-LOCAL-ADMISSION-INHERITANCE-1'
                    quality03_admitted_retention = active.manifest.get('approved_base_inheritance',{}).get('schema_version') == 'US-QUALITY03-LOCAL-ADMISSION-INHERITANCE-1'
                    quality04_retention = active.manifest.get('approved_base_inheritance',{}).get('schema_version') == 'US-QUALITY04-STAGED-INHERITANCE-1'
                    quality04_admitted_retention = active.manifest.get('approved_base_inheritance',{}).get('schema_version') == 'US-QUALITY04-LOCAL-ADMISSION-INHERITANCE-1'
                    quality05_retention = active.manifest.get('approved_base_inheritance',{}).get('schema_version') == 'US-QUALITY05-STAGED-INHERITANCE-1'
                    quality05_admitted_retention = active.manifest.get('approved_base_inheritance',{}).get('schema_version') == 'US-QUALITY05-LOCAL-ADMISSION-INHERITANCE-1'
                    quality06_retention = active.manifest.get('approved_base_inheritance',{}).get('schema_version') == 'US-QUALITY06-STAGED-INHERITANCE-1'
                    quality06_admitted_retention = active.manifest.get('approved_base_inheritance',{}).get('schema_version') == 'US-QUALITY06-LOCAL-ADMISSION-INHERITANCE-1'
                    quality_retention = active.manifest.get('approved_base_inheritance',{}).get('schema_version') == 'US-B1115-QUALITY-STAGED-INHERITANCE-1'
                    quality_admitted_retention = active.manifest.get('approved_base_inheritance',{}).get('schema_version') == 'US-B1115-QUALITY-LOCAL-ADMISSION-INHERITANCE-1'
                    for relative,digest in ({} if quality_retention or quality_admitted_retention or quality02_admitted_retention or quality03_admitted_retention or quality04_retention or quality04_admitted_retention else active.manifest.get('preserved_prior_estimate_sha256',{})).items():
                        rel=Path(relative)
                        if rel.is_absolute() or '..' in rel.parts:raise ValueError('unsafe prior estimate path')
                        payload=(active.root/rel).read_bytes()
                        if sha256_bytes(payload)!=digest:raise ValueError('preserved prior estimate changed')
                        _write(stage/rel,payload)
                    preserved=deepcopy(active.manifest.get('preserved_prior_estimate_sha256',{}))
                    for row in private_rows:
                        if row['outcome']!='source_bound':continue
                        ticker=row['ticker']
                        prior={'artifact.json':active.verify_artifact(ticker).read_bytes(),
                               'recipe.json':(active.root/'recipes'/f'{ticker}.json').read_bytes()}
                        # The predecessor policy, when packaged, is the prior
                        # assumption record rather than this run's override.
                        # If it was not retained, do not fabricate prior policy.
                        if active.manifest.get('private_refresh_policy_sha256'):
                            predecessor_policies=_json(active.root/'refresh-policies.json')
                            prior['policy.json']=canonical_json_bytes(predecessor_policies[ticker])
                        for name,payload in prior.items():
                            relative=f'prior-estimates/{ticker}/{active.catalog_version}/{name}'
                            _write(stage/relative,payload);preserved[relative]=sha256_bytes(payload)
                    manifest['preserved_prior_estimate_sha256']=preserved
                    bindings=deepcopy(active.manifest.get('source_binding_sha256',{}))
                    for ticker,payload in source_binding_proofs.items():
                        relative=f'source-bindings/{ticker}.json'
                        _write(stage/relative,payload)
                        bindings[ticker]=sha256_bytes(payload)
                        preserved[relative]=bindings[ticker]
                    if bindings:manifest['source_binding_sha256']=bindings
                    if active.manifest.get('local_admission'):
                        # This approval is for the exact admitted baseline, not
                        # permission to activate a future worker candidate.
                        manifest.update(staged_release_only=True, admission_prepared_only=True,
                                        catalog_kind='staged_refresh_successor')
                    if quality_retention:
                        from app.us_valuation.quality_batches1115_retention import assemble_retention_child
                        assemble_retention_child(active,manifest,stage,private_rows,cutoff)
                    if quality02_retention:
                        from app.us_valuation.quality02_retention import assemble
                        assemble(active,manifest,stage,private_rows,cutoff)
                    if quality03_retention:
                        from app.us_valuation.quality03_retention import assemble
                        assemble(active,manifest,stage,private_rows,cutoff)
                    if quality04_retention:
                        from app.us_valuation.quality04_retention import assemble
                        assemble(active,manifest,stage,private_rows,cutoff)
                    if quality05_retention:
                        from app.us_valuation.quality05_retention import assemble
                        assemble(active,manifest,stage,private_rows,cutoff)
                    if quality05_admitted_retention:
                        from app.us_valuation.quality05_admitted_retention import assemble
                        assemble(active,manifest,stage,private_rows,cutoff)
                    if quality06_retention:
                        from app.us_valuation.quality06_retention import assemble
                        assemble(active,manifest,stage,private_rows,cutoff)
                    if quality06_admitted_retention:
                        from app.us_valuation.quality06_admitted_retention import assemble
                        assemble(active,manifest,stage,private_rows,cutoff)
                    if quality02_admitted_retention:
                        from app.us_valuation.quality02_admitted_retention import assemble
                        assemble(active,manifest,stage,private_rows,cutoff)
                    if quality03_admitted_retention:
                        from app.us_valuation.quality03_admitted_retention import assemble
                        assemble(active,manifest,stage,private_rows,cutoff)
                    if quality04_admitted_retention:
                        from app.us_valuation.quality04_admitted_retention import assemble
                        assemble(active,manifest,stage,private_rows,cutoff)
                    if quality_admitted_retention:
                        from app.us_valuation.quality_batches1115_admitted_retention import assemble
                        assemble(active,manifest,stage,private_rows,cutoff)
                    _write(stage / "manifest.json", canonical_json_bytes(manifest))
                    validated = load_catalog_version(stage)
                    if quality03_retention or quality02_retention or quality02_admitted_retention or quality03_admitted_retention or quality04_retention or quality04_admitted_retention or quality05_retention or quality05_admitted_retention or quality06_retention or quality06_admitted_retention or quality_retention or quality_admitted_retention:
                        from app.us_valuation.approved_inheritance import validate_inheritance
                        validate_inheritance(stage,validated.manifest,deep=True)
                    os.replace(stage, destination)
                except Exception:
                    shutil.rmtree(stage)
                    raise
            candidate = {"version": validated.catalog_version,
                         "manifest_sha256": validated.manifest_sha256,
                         "path": str(destination)}
        report = {"schema_version": "FINSIGHT-US-500-STAGE-CYCLE-1",
                  "selected_count": len(private_rows), "catalog_count": len(active.entries),
                  "refresh_mode": TABLE_VERSION if table_first else 'legacy',
                  "cutoff": cutoff, "base_manifest_sha256": active.manifest_sha256,
                  "counts": dict(sorted(counts.items())), "changed_regular_count": changed,
                  "candidate": candidate, "rows": private_rows, "active_changed": False}
        if quality06:
            report.update({"auto_revaluation": False,
                           "new_filing_policy": "hold_before_capture",
                           "new_SEC_capture_or_job": False,
                           "quality06_status_only": True})
        run_hash = sha256_bytes(canonical_json_bytes(report))[:24]
        report_path = state_root / "reports" / f"{cutoff}-{run_hash}.json"
        _write(report_path, canonical_json_bytes(report))
        if (catalogs_root / "active.json").read_bytes() != pointer:
            raise RuntimeError("active catalog pointer changed during the stage-only cycle")
        return {**report, "private_report_path": str(report_path)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalogs-root", type=Path, required=True)
    parser.add_argument("--runtime-root", type=Path, required=True)
    parser.add_argument("--state-root", type=Path, required=True)
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--offline-source-root", type=Path)
    parser.add_argument('--baseline-catalog', type=Path, help='Reviewed immutable baseline for offline rehearsal only')
    parser.add_argument("--offline-packages-root", type=Path)
    parser.add_argument("--offline-event-cache-root", type=Path)
    parser.add_argument('--legacy-event-review', action='store_true')
    parser.add_argument('--tickers', help='Comma-separated private validation subset; catalog membership stays unchanged')
    parser.add_argument('--recheck-unavailable', action='store_true', help='Explicitly re-extract unchanged unavailable records for private validation')
    args = parser.parse_args()
    result = run_cycle(
        catalogs_root=args.catalogs_root, runtime_root=args.runtime_root,
        state_root=args.state_root, cutoff=args.as_of,
        offline_root=args.offline_source_root,
        offline_packages_root=args.offline_packages_root,
        offline_event_cache_root=args.offline_event_cache_root,
        table_first=not args.legacy_event_review,
        selected_tickers=set(args.tickers.split(',')) if args.tickers else None,
        recheck_unavailable=args.recheck_unavailable,baseline_catalog=args.baseline_catalog)
    print(json.dumps({key: value for key, value in result.items() if key != "rows"}, sort_keys=True))


if __name__ == "__main__":
    main()
