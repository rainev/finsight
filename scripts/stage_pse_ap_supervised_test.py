#!/usr/bin/env python3
"""Run the confirmed AP proxy case into an isolated, non-serving catalog."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date
from pathlib import Path

from app.pse_valuation import MODEL_VERSION
from app.pse_valuation.catalog import CATALOG_SCHEMA, POINTER_SCHEMA, load_pointer
from app.pse_valuation.contract import PseValuationArtifact, ScenarioValue, sha256_object
from app.pse_valuation.models.fcff import fcff_valuation


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/audit/evidence"
SERVING_ROOT = ROOT / "backend/app/data/pse_valuation_catalogs"
PROXY_PATH = EVIDENCE / "pse-ap-proxy-recommendations-2026-09-26.json"
PRIOR_PATH = EVIDENCE / "pse-phase-c-ap-rlc-candidate-workpaper.json"
PROXY_SHA256 = "77faf0089b7726f5cc3e7a4af9a57d08728eb31ee6dca555d3b9d023c9c06a4a"
PRIOR_SHA256 = "3348138b35f99657055d0cd4c9706b906f2a22a09251d06411d7e931c836ca2a"
ACTIVE_POINTER_SHA256 = "50652bb9490f77d73d8cddb8b98058197910a0271c935d6685339370e0f7da92"
CATALOG_VERSION = "PSE-V2-AP-SUPERVISED-2026-09-26-1.0"
SHARED_CATALOG_VERSION = "PSE-V2-AP-SUPERVISED-2026-09-26-1.1"


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _pinned_json(path: Path, digest: str) -> dict:
    raw = path.read_bytes()
    if _sha256(raw) != digest:
        raise ValueError(f"pinned input changed: {path.name}")
    return json.loads(raw)


def _write_json(path: Path, value: dict) -> bytes:
    raw = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return raw


def stage(
    *,
    output_root: Path,
    ap_2026_pdf: Path,
    ap_2025_pdf: Path,
    shared_starting_fcff: bool = False,
) -> Path:
    output_root = output_root.resolve()
    if output_root == SERVING_ROOT.resolve() or SERVING_ROOT.resolve() in output_root.parents:
        raise ValueError("the AP test must stay outside the serving catalog root")
    if output_root.exists():
        raise FileExistsError(f"stage output already exists: {output_root}")
    if _sha256((SERVING_ROOT / "active.json").read_bytes()) != ACTIVE_POINTER_SHA256:
        raise ValueError("active pointer changed since the confirmed input gate")

    proxy = _pinned_json(PROXY_PATH, PROXY_SHA256)
    prior = _pinned_json(PRIOR_PATH, PRIOR_SHA256)
    if (
        proxy["status"] != "staged_recommendations_unapproved_not_served"
        or proxy["approval"] is not False
        or proxy["activation"] is not False
        or proxy["publication_candidate_values"] is not None
        or proxy["rlc_status"] != "pending_user_supplied_consolidation_property_bridge"
    ):
        raise ValueError("proxy receipt does not preserve the approved test boundary")
    if prior["scope"] != ["AP", "RLC"] or prior["ap"]["publication_candidate_values"] is not None:
        raise ValueError("prior AP workpaper is not the confirmed calculation baseline")
    source_hashes = proxy["source_hashes"]
    if _sha256(ap_2026_pdf.read_bytes()) != source_hashes["ap_2026_1h_17q_sha256"]:
        raise ValueError("AP 1H2026 filing bytes differ from the reviewed original")
    if _sha256(ap_2025_pdf.read_bytes()) != source_hashes["ap_2025_17a_sha256"]:
        raise ValueError("AP FY2025 filing bytes differ from the reviewed original")

    bridge = proxy["model_inputs_unchanged_from_prior_candidate_except_minority"]
    minority_value = float(proxy["minority_claim"]["proposed_claim"])
    source_base = prior["ap"]["reported_and_derived"]
    if (
        bridge["equity_method_investment_proxy"] != proxy["equity_method_investments"]["value"]
        or bridge["cash"] != source_base["cash"]
        or bridge["borrowings_plus_leases"] != source_base["borrowings_plus_leases"]
        or bridge["shares_millions"] != source_base["common_shares_millions"]
        or proxy["tax"]["rate"] != prior["ap"]["unapproved_assumptions"]["interest_tax_shield_rate"]
    ):
        raise ValueError("provisional proxies or reported capital facts have drifted")
    starting_fcff_by_scenario = dict(bridge["starting_fcff"])
    if shared_starting_fcff:
        starting_fcff_by_scenario = {
            name: bridge["starting_fcff"]["base"] for name in ("bear", "base", "bull")
        }
    effective_bridge = {**bridge, "starting_fcff": starting_fcff_by_scenario}

    results: dict[str, ScenarioValue] = {}
    scenario_policy: dict[str, dict[str, float]] = {}
    for name in ("bear", "base", "bull"):
        assumptions = dict(prior["ap"]["engine_scenario_assumptions"][name])
        starting_fcff = float(starting_fcff_by_scenario[name])
        starting_nopat = starting_fcff / (1 - assumptions["growth_rate"] / assumptions["roic"])
        value = fcff_valuation(
            starting_nopat=starting_nopat,
            **assumptions,
            cash=float(bridge["cash"]),
            nonoperating_assets=float(bridge["equity_method_investment_proxy"]),
            debt=float(bridge["borrowings_plus_leases"]),
            minority_value=minority_value,
            other_claims=float(bridge["other_claims"]),
            shares_outstanding=float(bridge["shares_millions"]),
        )
        expected = proxy["calculation_only_scenarios"][name]
        if (not shared_starting_fcff or name == "base") and (
            abs(value["value_per_share"] - expected["value_per_share"]) > 1e-8
            or abs(value["common_equity_value"] - expected["common_equity_value"]) > 1e-6
        ):
            raise ValueError(f"AP {name} engine result differs from the confirmed proxy workpaper")
        results[name] = ScenarioValue(
            value_per_share=value["value_per_share"],
            common_equity_value=value["common_equity_value"],
            enterprise_value=value["enterprise_value"],
        )
        assumptions.pop("forecast_years")
        scenario_policy[name] = assumptions

    sources = [
        {
            "document_id": f"AP-2026-1H-17Q-P{page}",
            "label": f"AP 1H2026 SEC Form 17-Q, PDF page {page}",
            "form": "17-Q",
            "period_end": "2026-06-30",
            "published_at": "2026-08-14",
            "url": prior["ap"]["source_urls"][0],
            "source_page": page,
            "sha256": source_hashes["ap_2026_1h_17q_sha256"],
        }
        for page in (3, 12, 14, 17, 28, 46)
    ]
    sources.extend(
        {
            "document_id": f"AP-2025-17A-P{page}",
            "label": f"AP FY2025 audited annual report, local original PDF page {page}",
            "form": "17-A",
            "period_end": "2025-12-31",
            "published_at": "2026-04-15",
            "url": None,
            "source_page": page,
            "sha256": source_hashes["ap_2025_17a_sha256"],
        }
        for page in (291, 296)
    )
    values = [row.value_per_share for row in results.values()]
    input_snapshot = {
        "proxy_receipt_sha256": PROXY_SHA256,
        "prior_workpaper_sha256": PRIOR_SHA256,
        "source_hashes": source_hashes,
        "capital_bridge": effective_bridge,
        "minority_value_php_millions": minority_value,
        "scenario_policy": scenario_policy,
        "model_version": MODEL_VERSION,
    }
    if shared_starting_fcff:
        input_snapshot["scenario_starting_fcff_policy"] = "shared_base"
    warnings = [
        "Isolated calculation-only AP test; not analyst-approved, published, or active.",
        "The 25% interest tax shield and 12% zero-growth minority-distribution hurdle are unapproved review hypotheses.",
        "Equity-method investment book value is not independently assessed fair value; its three largest positions need economic review.",
        "Cash-flow normalization, other claims, and the dated macro/WACC assumptions remain unapproved.",
        (
            "One shared starting FCFF is used for bear/base/bull; growth, ROIC, WACC and terminal assumptions still vary."
            if shared_starting_fcff
            else "Scenario starting FCFF differs; the existing interactive calculator uses one base starting FCFF and will not replay bear/bull exactly."
        ),
        "Original AP filing bytes were verified temporarily; licensed durable source storage and public display rights remain unconfirmed.",
    ]
    public_assumptions = {
        "forecast_years": 5,
        "normalized_fcff_proxy_php_millions": bridge["starting_fcff"]["base"],
        "starting_fcff_by_scenario_php_millions": starting_fcff_by_scenario,
        "interest_tax_shield_rate": proxy["tax"]["rate"],
        "minority_discount_rate": proxy["minority_claim"]["assumed_cost_of_equity"],
        "minority_distribution_growth": proxy["minority_claim"]["growth_rate"],
        "scenario_assumptions": scenario_policy,
        "capital_bridge": {
            "cash_php_millions": bridge["cash"],
            "nonoperating_assets_php_millions": bridge["equity_method_investment_proxy"],
            "debt_php_millions": bridge["borrowings_plus_leases"],
            "minority_value_php_millions": minority_value,
            "other_claims_php_millions": bridge["other_claims"],
            "shares_millions": bridge["shares_millions"],
        },
        "proxy_receipt_sha256": PROXY_SHA256,
        "reliability": "Low - calculation-only supervised test",
    }
    if shared_starting_fcff:
        public_assumptions["scenario_starting_fcff_policy"] = "shared_base"
    artifact = PseValuationArtifact(
        ticker="AP",
        issuer={"issuer_id": "PSE:AP", "name": "Aboitiz Power Corporation"},
        security={"security_id": "PSE:AP:COMMON", "type": "ordinary_common"},
        subsector="Power utility and generation",
        primary_model="fcff_dcf",
        valuation_date=date(2026, 9, 26),
        filing_period="FY2025 plus 1H2026 less 1H2025 (TTM to June 2026)",
        filing_published_at="2026-08-14",
        availability_type="intrinsic_valuation",
        publication_state="provisional",
        scenarios=results,
        numerical_range={"low": min(values), "high": max(values)},
        public_assumptions=public_assumptions,
        sensitivities=[{"type": "one_way_base_proxy_checks", **proxy["one_way_base_per_share_checks"]}],
        sources=sources,
        warnings=warnings,
        blocking_reasons=[],
        input_hash=sha256_object(input_snapshot),
    ).with_artifact_hash()
    if not artifact.verify_artifact_hash():
        raise ValueError("AP internal artifact hash failed")

    catalog_version = SHARED_CATALOG_VERSION if shared_starting_fcff else CATALOG_VERSION
    catalog_root = output_root / catalog_version
    artifact_raw = _write_json(catalog_root / "artifacts/AP.json", artifact.model_dump(mode="json"))
    entry = {
        "ticker": "AP",
        "availability_type": artifact.availability_type,
        "publication_state": artifact.publication_state,
        "primary_model": artifact.primary_model,
        "artifact_sha256": _sha256(artifact_raw),
        "source_audit": (
            "docs/audit/45-pse-ap-shared-fcff-staged-test.md"
            if shared_starting_fcff
            else "docs/audit/43-pse-ap-proxy-recommendations.md"
        ),
    }
    manifest = {
        "schema_version": CATALOG_SCHEMA,
        "catalog_version": catalog_version,
        "universe_version": "PSE-V2-AP-ISOLATED-TEST-1.0",
        "valuation_date": "2026-09-26",
        "catalog_status": "staged",
        "artifact_count": 1,
        "availability_counts": {"intrinsic_valuation": 1, "market_relative_only": 0, "not_available": 0},
        "publication_counts": {"approved": 0, "blocked": 0, "provisional": 1},
        "entries": [entry],
    }
    manifest_raw = _write_json(catalog_root / "manifest.json", manifest)
    _write_json(
        output_root / "staged.json",
        {
            "schema_version": POINTER_SCHEMA,
            "status": "staged",
            "catalog_version": catalog_version,
            "catalog_path": catalog_version,
            "manifest_sha256": _sha256(manifest_raw),
        },
    )
    catalog = load_pointer(output_root)
    if catalog.status != "staged" or {entry.ticker for entry in catalog.entries} != {"AP"}:
        raise ValueError("isolated AP stage did not round-trip through the catalog reader")
    if _sha256((SERVING_ROOT / "active.json").read_bytes()) != ACTIVE_POINTER_SHA256:
        raise ValueError("active pointer changed during the isolated AP test")
    return catalog_root


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--ap-2026-pdf", type=Path, required=True)
    parser.add_argument("--ap-2025-pdf", type=Path, required=True)
    parser.add_argument("--shared-starting-fcff", action="store_true")
    args = parser.parse_args()
    print(
        stage(
            output_root=args.output,
            ap_2026_pdf=args.ap_2026_pdf,
            ap_2025_pdf=args.ap_2025_pdf,
            shared_starting_fcff=args.shared_starting_fcff,
        )
    )


if __name__ == "__main__":
    main()
