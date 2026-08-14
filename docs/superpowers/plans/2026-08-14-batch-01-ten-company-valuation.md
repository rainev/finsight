# FinSight Batch 01 Ten-Company Valuation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate, verify, and promote production-shaped intrinsic-value artifacts for exactly AAPL, MSFT, CRM, ANET, WDC, DELL, JPM, BAC, NEE, and O at `2026-08-14`, then stop.

**Architecture:** Freeze the ten-company manifest in code, capture immutable SEC source packets into a non-serving output tree, and run Companyfacts first with offline Arelle structural evidence only where the fast path remains incomplete. FinSight promotes only exact allowlisted structural decisions, uses source-backed aggregate ranges for still-missing FCFF bridge details, routes each issuer through its governed model, and generates staged public JSON. A separate API verifier must pass for all ten before a guarded promotion replaces exactly ten feature-branch serving artifacts.

**Tech Stack:** Python 3.11, SEC submissions and Companyfacts JSON, pinned offline Arelle 2.44, frozen dataclasses, FastAPI, JSON artifacts, pytest 8.3.4, atomic file replacement.

## Prerequisite

Complete and independently review Tasks 1–7 of `docs/superpowers/plans/2026-08-14-evidence-aware-reliability-pipeline.md` first. In particular, canonical public schema `US-PUBLIC-VALUATION-1.1`, API reliability, difficult-corpus replay, and live API verification must be proven before Batch 01 promotion. If that phase is partial or blocked, Batch 01 may be generated diagnostically but must not be promoted.

## Global Constraints

- Work only on `feat/whole-universe-greenlight` in `.worktrees/whole-universe-greenlight`; never modify the user's dirty root checkout.
- The immutable manifest is exactly AAPL, MSFT, CRM, ANET, WDC, DELL, JPM, BAC, NEE, and O. Do not drop, swap, or add a company.
- The valuation date is exactly `2026-08-14`; every accepted filing must have `filed <= 2026-08-14`.
- Governed lanes are exactly six `fcff_dcf`, two `residual_income`, one `ddm`, and one `ffo`; O remains model-capped at `Low` with `INTERIM_FFO_ROUTE`.
- Generate only beneath `output/batch-01-ten-company/` until staged API verification passes 10/10.
- Do not call `scripts/build_us_valuation_pipeline.py`; its output-root flag does not contain its serving and frontend writes.
- Arelle runs only in source ingestion. The batch generator and FastAPI process consume normalized JSON and never import Arelle.
- Never treat absence as zero. Reject future, conflicting, wrong-period, wrong-unit, wrong-currency, wrong-CIK, or wrong-share-denominator evidence.
- A source-backed aggregate may create a bounded range only when its coverage is explicit and double counting is impossible. Its uncertainty changes reliability; it does not become a false point estimate.
- Do not change the approved accounting thresholds `5%` and `20%` or scenario thresholds `20%` and `40%`.
- Never stage, commit, delete, or clean generated `output/` evidence.
- No frontend, market-price, deployment, merge-to-main, Batch 02, or remaining-universe work belongs in this plan.
- Promotion order is mandatory: generate → staged API verification → promote exactly ten → serving API verification.
- Every behavior change follows RED → GREEN TDD, and every task receives an independent task review.

---

### Task 1: Freeze the exact Batch 01 contract

**Files:**

- Create: `backend/app/us_valuation/batch_01.py`
- Create: `backend/tests/test_batch_01_contract.py`

**Interfaces:**

- Produces `BATCH_01_VALUATION_DATE: str`, immutable `BatchIssuer`, `BATCH_01_MANIFEST: tuple[BatchIssuer, ...]`, `BATCH_01_TICKERS`, and `issuer_for_ticker(ticker: str) -> BatchIssuer`.
- `BatchIssuer` fields are `ticker`, `cik`, `issuer_name`, and `primary_model`.
- Later capture, generation, API-verification, and promotion scripts import this one manifest; none duplicates a second list.

- [ ] **Step 1: Write the failing manifest tests**

```python
from app.us_valuation.batch_01 import (
    BATCH_01_MANIFEST,
    BATCH_01_TICKERS,
    BATCH_01_VALUATION_DATE,
    issuer_for_ticker,
)


def test_batch_01_manifest_is_exact_and_immutable() -> None:
    assert BATCH_01_VALUATION_DATE == "2026-08-14"
    assert tuple(
        (issuer.ticker, issuer.cik, issuer.issuer_name, issuer.primary_model)
        for issuer in BATCH_01_MANIFEST
    ) == (
        ("AAPL", "0000320193", "Apple Inc.", "fcff_dcf"),
        ("MSFT", "0000789019", "Microsoft Corporation", "fcff_dcf"),
        ("CRM", "0001108524", "Salesforce, Inc.", "fcff_dcf"),
        ("ANET", "0001596532", "Arista Networks, Inc.", "fcff_dcf"),
        ("WDC", "0000106040", "Western Digital Corporation", "fcff_dcf"),
        ("DELL", "0001571996", "Dell Technologies Inc.", "fcff_dcf"),
        ("JPM", "0000019617", "JPMorgan Chase & Co.", "residual_income"),
        ("BAC", "0000070858", "Bank of America Corporation", "residual_income"),
        ("NEE", "0000753308", "NextEra Energy, Inc.", "ddm"),
        ("O", "0000726728", "Realty Income Corporation", "ffo"),
    )
    assert BATCH_01_TICKERS == tuple(issuer.ticker for issuer in BATCH_01_MANIFEST)
    assert len(BATCH_01_MANIFEST) == 10
    assert len({issuer.cik for issuer in BATCH_01_MANIFEST}) == 10
    assert issuer_for_ticker("O").cik == "0000726728"
```

Also assert lowercase/unknown tickers fail rather than silently normalize, and dataclass mutation raises `FrozenInstanceError`.

- [ ] **Step 2: Run the test and verify RED**

```bash
PYTHONPATH=backend pytest -q backend/tests/test_batch_01_contract.py
```

Expected: collection fails because `app.us_valuation.batch_01` does not exist.

- [ ] **Step 3: Implement the exact manifest**

Use these literal rows:

```python
BATCH_01_VALUATION_DATE = "2026-08-14"
BATCH_01_MANIFEST = (
    BatchIssuer("AAPL", "0000320193", "Apple Inc.", "fcff_dcf"),
    BatchIssuer("MSFT", "0000789019", "Microsoft Corporation", "fcff_dcf"),
    BatchIssuer("CRM", "0001108524", "Salesforce, Inc.", "fcff_dcf"),
    BatchIssuer("ANET", "0001596532", "Arista Networks, Inc.", "fcff_dcf"),
    BatchIssuer("WDC", "0000106040", "Western Digital Corporation", "fcff_dcf"),
    BatchIssuer("DELL", "0001571996", "Dell Technologies Inc.", "fcff_dcf"),
    BatchIssuer("JPM", "0000019617", "JPMorgan Chase & Co.", "residual_income"),
    BatchIssuer("BAC", "0000070858", "Bank of America Corporation", "residual_income"),
    BatchIssuer("NEE", "0000753308", "NextEra Energy, Inc.", "ddm"),
    BatchIssuer("O", "0000726728", "Realty Income Corporation", "ffo"),
)
```

Validate each ticker with `re.fullmatch(r"^[A-Z][A-Z0-9.-]{0,9}$", ticker)` and each CIK with `normalize_cik()` during module construction. `issuer_for_ticker()` accepts only an exact manifest ticker.

- [ ] **Step 4: Run focused and full tests**

```bash
PYTHONPATH=backend pytest -q backend/tests/test_batch_01_contract.py
PYTHONPATH=backend pytest -q backend/tests
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/us_valuation/batch_01.py backend/tests/test_batch_01_contract.py
git diff --cached --check
git commit -m "feat: freeze first ten-company valuation batch"
```

**Gate:** Every later Batch 01 command receives the same exact denominator, identities, lanes, and valuation date from one immutable contract.

---

### Task 2: Capture immutable SEC and Arelle source packets without serving writes

**Files:**

- Create: `scripts/capture_batch_01_sources.py`
- Create: `backend/tests/test_batch_01_source_capture.py`
- Modify: `backend/app/us_valuation/structural_xbrl.py`
- Modify: `backend/tests/test_structural_xbrl_schema.py`

**Interfaces:**

- Produces one packet per ticker at `output/batch-01-ten-company/sources/{TICKER}/` containing `submissions.json`, `companyfacts.json`, their `.meta.json` files, `source-manifest.json`, and optional `structural-filing.json` plus `package-manifest.json` hash metadata.
- Exposes `capture_sources(*, output_root: Path, user_agent: str | None, refresh: bool) -> dict[str, object]` and a CLI with `--output-root`, `--refresh`, and `--user-agent`.
- Adds `StructuralFiling.from_dict(value: Mapping[str, Any]) -> StructuralFiling`, the validating inverse of `as_dict()` used by the offline runner.
- Source capture may import Arelle lazily only after a provisional FCFF result identifies supported unresolved bridge fields. `--help` and FastAPI startup remain Arelle-free.

- [ ] **Step 1: Write failing path, identity, and no-serving-write tests**

Use a fake `SecClient` and the reduced AAPL/ANET fixtures. Require:

```python
summary = capture_sources(
    output_root=tmp_path / "batch",
    user_agent=None,
    refresh=False,
)
assert summary["manifest_count"] == 10
assert summary["source_packet_count"] == 10
assert summary["serving_artifacts_changed"] is False
```

Add tests that:

- reject output equal to, inside, or symlinked into `backend/app/data/us_valuations`, `frontend/public/data`, or `frontend/src/research/generated`;
- reject a source response whose CIK or ticker does not match the frozen issuer;
- reject a filing dated after `2026-08-14` as a structural controlling filing;
- require a monitored user agent only when a real network fetch is needed;
- make a second identical cached run byte-identical;
- refuse to overwrite an existing packet when bytes differ;
- round-trip `StructuralFiling.from_dict(filing.as_dict())`, while rejecting malformed facts, diagnostics, form, dates, and metadata; and
- prove importing the module and running `--help` does not import `arelle`.

- [ ] **Step 2: Run tests and verify RED**

```bash
PYTHONPATH=backend pytest -q backend/tests/test_batch_01_source_capture.py
```

Expected: collection fails because the capture script does not exist.

- [ ] **Step 3: Implement contained source capture**

For each frozen issuer:

1. create a `SecClient(user_agent=user_agent, cache_dir=packet / "sec-cache")`;
2. capture submissions and Companyfacts with their existing durable metadata;
3. verify normalized CIK, manifest ticker, SHA-256, source URL, and metadata before publishing the packet;
4. run `build_us_valuation()` provisionally from only those two JSON inputs;
5. for an FCFF result whose supported bridge fields remain unresolved, obtain its controlling accession/form/primary document, call `cache_structural_filing_package()`, then call `parse_structural_filing()`;
6. write `StructuralFiling.as_dict()` to `structural-filing.json` and copy only the matching immutable `package-manifest.json` into the packet root;
7. hash every completed packet payload file in `source-manifest.json`, explicitly excluding `source-manifest.json` itself; and
8. hash all protected serving roots before and after and fail if any changed.

Write via a sibling temporary directory followed by `os.replace()`. Existing identical packets are accepted; different packets require a fresh output root rather than destructive overwrite. The source packet contains no generated valuation and performs no frontend write.

- [ ] **Step 4: Run focused and full tests**

```bash
PYTHONPATH=backend pytest -q \
  backend/tests/test_batch_01_source_capture.py \
  backend/tests/test_structural_xbrl_schema.py
PYTHONPATH=backend pytest -q backend/tests
```

- [ ] **Step 5: Commit**

```bash
git add \
  scripts/capture_batch_01_sources.py \
  backend/app/us_valuation/structural_xbrl.py \
  backend/tests/test_batch_01_source_capture.py \
  backend/tests/test_structural_xbrl_schema.py
git diff --cached --check
git commit -m "feat: capture isolated batch one filing sources"
```

**Gate:** All ten have an explicit immutable source packet or an explicit capture failure; the capture changed zero serving/frontend artifacts and Arelle remains outside serving imports.

---

### Task 3: Make specialist fact selection point-in-time and exactly attributable

**Files:**

- Create: `backend/app/us_valuation/equity_fact_selection.py`
- Modify: `backend/app/us_valuation/equity_models.py`
- Modify: `backend/app/us_valuation/pipeline.py`
- Modify: `backend/app/us_valuation/artifacts.py`
- Create: `backend/tests/test_equity_fact_selection.py`
- Modify: `backend/tests/test_us_valuation_v2_routing.py`
- Modify: `backend/tests/test_bridge_policy_artifacts.py`

**Interfaces:**

- Produces frozen `SelectedFact(concept, value, unit, period_end, filed_date, accession, form, fiscal_year)` plus these exact interfaces:
  - `annual_facts(gaap, *, concepts: tuple[str, ...], unit: str, valuation_date: str) -> dict[int, SelectedFact]`
  - `latest_instant(gaap, *, concepts: tuple[str, ...], unit: str, valuation_date: str) -> SelectedFact | None`
  - `source_statement(fact: SelectedFact, *, submissions, cik: str) -> dict[str, object]`
- Changes `build_equity_level_result(..., submissions: Mapping[str, Any])` so every selected bank/DDM/FFO input is filed on or before the valuation date and privately source-linked.
- Equity private results add `input_provenance`; canonical public output drops that private map and retains one exact `source_financial_statement`.

- [ ] **Step 1: Write failing no-lookahead selector tests**

Construct Companyfacts where one fact has `end="2026-03-31"` but `filed="2026-08-15"`, and another has `end="2025-12-31"`, `filed="2026-02-20"`. At cutoff `2026-08-14`, assert only the second is selectable. Cover `USD`, `shares`, and `USD/shares`; booleans, non-finite values, missing accession/filed date, amended filings, and duplicate period conflicts fail closed.

Add a regression where the selected period is `2026-03-31` but the first classification accession is `2026-06-30`. Assert the result uses the selected fact's own accession and exact archive URL, never the unrelated first accession.

- [ ] **Step 2: Run tests and verify RED**

```bash
PYTHONPATH=backend pytest -q \
  backend/tests/test_equity_fact_selection.py \
  backend/tests/test_us_valuation_v2_routing.py \
  -k 'lookahead or provenance or accession or filed'
```

Expected: the current selectors filter by `end`, discard fact provenance, and `_shell()` attaches an unrelated accession.

- [ ] **Step 3: Implement immutable fact selection**

Use `filed_date <= valuation_date` as the availability gate. `period_end` may not be after the valuation date, but it is not a substitute for filed date. Select deterministic records by `(period_end, filed_date, accession)` after validating unit, finite value, form, and CIK context. For the same concept/period/accession, unequal values are a conflict; do not choose one by list order.

`source_statement()` must look up the selected accession in the cutoff submissions object and emit exact `form`, `period_end`, `filed_date`, `accession`, and `https://www.sec.gov/Archives/edgar/data/{unpadded_cik}/{digits_accession}/{primary_document}`.

- [ ] **Step 4: Route source-aware specialist inputs**

Change bank, DDM, and FFO extractors to return values plus their `SelectedFact` records. Pass cutoff submissions from `build_us_valuation()` into `build_equity_level_result()`. Save an allowlisted private provenance dictionary per economic input. Derive `financial_period_end` and `source_financial_statement` from the actual controlling selected fact, not `classification.source_accessions[0]`.

Do not change model formulas, scenario assumptions, or O's `Low` cap. If an input has no safe selected fact, return the existing withheld specialist result with a concrete reason.

- [ ] **Step 5: Prove public stripping and lane behavior**

Add tests asserting canonical public output contains exact filing attribution but no `input_provenance`, raw Companyfacts, source manifest, or selected-fact internals. Build source-shaped hermetic JPM/BAC/NEE/O fixtures inside `test_equity_fact_selection.py`; exercise the real selectors and valuation models without mocking them.

- [ ] **Step 6: Run focused and full tests**

```bash
PYTHONPATH=backend pytest -q \
  backend/tests/test_equity_fact_selection.py \
  backend/tests/test_us_valuation_v2_routing.py \
  backend/tests/test_bridge_policy_artifacts.py
PYTHONPATH=backend pytest -q backend/tests
```

- [ ] **Step 7: Commit**

```bash
git add \
  backend/app/us_valuation/equity_fact_selection.py \
  backend/app/us_valuation/equity_models.py \
  backend/app/us_valuation/pipeline.py \
  backend/app/us_valuation/artifacts.py \
  backend/tests/test_equity_fact_selection.py \
  backend/tests/test_us_valuation_v2_routing.py \
  backend/tests/test_bridge_policy_artifacts.py
git diff --cached --check
git commit -m "fix: enforce point-in-time specialist provenance"
```

**Gate:** Specialist values cannot see post-cutoff filings, and every selected input and public source statement points to the filing that actually supplied it.

---

### Task 4: Add exact governed promotion for approved structural decisions

**Files:**

- Create: `backend/app/us_valuation/structural_promotion.py`
- Create: `backend/app/us_valuation/config/batch_01_structural_promotions.json`
- Modify: `backend/app/us_valuation/field_availability.py`
- Modify: `backend/app/us_valuation/xbrl.py`
- Modify: `backend/app/us_valuation/pipeline.py`
- Create: `backend/tests/test_structural_promotion.py`
- Modify: `backend/tests/test_bridge_policy_pipeline.py`

**Interfaces:**

- Produces `promote_structural_decision(decision: ResolutionDecision, *, ticker: str, cik: str, filing_date: str, valuation_date: str) -> FieldAvailability`.
- Produces frozen `BridgeEvidenceMerge(availability: dict[str, FieldAvailability], rejected_diagnostics: tuple[dict[str, object], ...])` and `merge_bridge_evidence(primary, candidates) -> BridgeEvidenceMerge`.
- `build_us_valuation(..., bridge_evidence: Iterable[FieldAvailability] = ())` passes externally prepared production evidence into normalization without importing Arelle.
- Promotion remains impossible unless every decision field exactly matches one frozen allowlist fingerprint.

- [ ] **Step 1: Write failing exact-fingerprint and merge tests**

Require an accepted, complete structural decision to remain unpromotable when any one of ticker, CIK, accession, period, form, filing date, source concept, value, unit, mapping method, mapping version, confidence, or reason codes differs. Explicitly reject:

- `NO_CANDIDATE` or absence-based zero;
- CRM's `$94m` investment commercial paper as borrowing;
- DELL's zero preferred share count as USD preferred equity;
- WDC's `$265m` liquidation preference as carrying value;
- future-filed evidence; and
- any shadow candidate not named in the allowlist.

Test merge precedence exactly as the approved ladder: matching current Companyfacts wins; matching current structural evidence corroborates it; current structural evidence replaces unresolved, stale, or `annual_carried_forward` lower-level evidence; unequal current points become `conflict`; a conflict is recorded and never silently overwritten.

- [ ] **Step 2: Run tests and verify RED**

```bash
PYTHONPATH=backend pytest -q \
  backend/tests/test_structural_promotion.py \
  backend/tests/test_bridge_policy_pipeline.py \
  -k 'structural or promotion or merge'
```

Expected: only shadow conversion exists and `build_us_valuation()` cannot consume production structural evidence.

- [ ] **Step 3: Add the exact Batch 01 allowlist**

The JSON schema version is `BATCH-01-STRUCTURAL-PROMOTION-1.0`. Add exactly these complete fingerprints; no wildcard is permitted:

```json
{
  "schema_version": "BATCH-01-STRUCTURAL-PROMOTION-1.0",
  "unit": "USD",
  "mapping_version": "US-XBRL-RESOLVER-1.1",
  "promotions": [
    {"ticker":"ANET","cik":"0001596532","field":"marketable_securities_current","value":9563700000,"period":"2026-03-31","accession":"0001596532-26-000078","form":"10-Q","filing_date":"2026-05-06","source_concept":"us-gaap:AvailableForSaleSecuritiesDebtSecuritiesCurrent","mapping_method":"known_taxonomy_alias","confidence":0.98,"reason_codes":["KNOWN_TAXONOMY_ALIAS"]},
    {"ticker":"ANET","cik":"0001596532","field":"preferred_equity","value":0,"period":"2026-03-31","accession":"0001596532-26-000078","form":"10-Q","filing_date":"2026-05-06","source_concept":"us-gaap:PreferredStockValue","mapping_method":"known_taxonomy_alias","confidence":0.98,"reason_codes":["KNOWN_TAXONOMY_ALIAS","PREFERRED_EQUITY_CARRYING_AMOUNT"]},
    {"ticker":"CRM","cik":"0001108524","field":"marketable_securities_current","value":2902000000,"period":"2026-04-30","accession":"0001108524-26-000127","form":"10-Q","filing_date":"2026-05-28","source_concept":"us-gaap:AvailableForSaleSecuritiesDebtSecuritiesCurrent","mapping_method":"known_taxonomy_alias","confidence":0.98,"reason_codes":["KNOWN_TAXONOMY_ALIAS"]},
    {"ticker":"CRM","cik":"0001108524","field":"finance_lease_total","value":664000000,"period":"2026-04-30","accession":"0001108524-26-000127","form":"10-Q","filing_date":"2026-05-28","source_concept":"us-gaap:FinanceLeaseLiability","mapping_method":"exact_configured_concept","confidence":1.0,"reason_codes":["EXACT_CONFIGURED_CONCEPT","STRUCTURAL_STATEMENT_SUPPORT"]},
    {"ticker":"CRM","cik":"0001108524","field":"noncurrent_debt","value":39280000000,"period":"2026-04-30","accession":"0001108524-26-000127","form":"10-Q","filing_date":"2026-05-28","source_concept":"us-gaap:LongTermDebtNoncurrent","mapping_method":"exact_configured_concept","confidence":1.0,"reason_codes":["EXACT_CONFIGURED_CONCEPT"]},
    {"ticker":"DELL","cik":"0001571996","field":"current_debt","value":7550000000,"period":"2026-05-01","accession":"0001571996-26-000030","form":"10-Q","filing_date":"2026-06-09","source_concept":"us-gaap:DebtCurrent","mapping_method":"known_taxonomy_alias","confidence":0.98,"reason_codes":["KNOWN_TAXONOMY_ALIAS"]},
    {"ticker":"DELL","cik":"0001571996","field":"noncurrent_debt","value":23611000000,"period":"2026-05-01","accession":"0001571996-26-000030","form":"10-Q","filing_date":"2026-06-09","source_concept":"us-gaap:LongTermDebtNoncurrent","mapping_method":"exact_configured_concept","confidence":1.0,"reason_codes":["EXACT_CONFIGURED_CONCEPT"]},
    {"ticker":"DELL","cik":"0001571996","field":"noncontrolling_interests","value":0,"period":"2026-05-01","accession":"0001571996-26-000030","form":"10-Q","filing_date":"2026-06-09","source_concept":"us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest","mapping_method":"taxonomy_and_context","confidence":0.96,"reason_codes":["GOVERNED_DIMENSIONAL_CONTEXT","STRUCTURAL_STATEMENT_SUPPORT"]},
    {"ticker":"WDC","cik":"0000106040","field":"current_debt","value":1581000000,"period":"2026-04-03","accession":"0001628280-26-029054","form":"10-Q","filing_date":"2026-05-01","source_concept":"us-gaap:LongTermDebtCurrent","mapping_method":"exact_configured_concept","confidence":1.0,"reason_codes":["EXACT_CONFIGURED_CONCEPT"]},
    {"ticker":"WDC","cik":"0000106040","field":"noncurrent_debt","value":0,"period":"2026-04-03","accession":"0001628280-26-029054","form":"10-Q","filing_date":"2026-05-01","source_concept":"us-gaap:LongTermDebtNoncurrent","mapping_method":"exact_configured_concept","confidence":1.0,"reason_codes":["EXACT_CONFIGURED_CONCEPT"]},
    {"ticker":"WDC","cik":"0000106040","field":"preferred_equity","value":0,"period":"2026-04-03","accession":"0001628280-26-029054","form":"10-Q","filing_date":"2026-05-01","source_concept":"us-gaap:TemporaryEquityCarryingAmountAttributableToParent","mapping_method":"known_taxonomy_alias","confidence":0.98,"reason_codes":["KNOWN_TAXONOMY_ALIAS","TEMPORARY_EQUITY_CARRYING_AMOUNT"]}
  ]
}
```

- [ ] **Step 4: Implement fail-closed promotion**

Call the existing structural decision/evidence validation first. Require `status="accepted"`, complete `StructuralFact` evidence, exact source accession, period, normalized form, and filing date, nonnegative finite USD value, known mapping version, filing date on/before valuation date, and exact allowlist equality. Return authority `production`, freshness `current`, fallback level `current_structural`, source kind `structural_xbrl`, and a public-safe reason code. Any mismatch raises a typed promotion error; it never becomes an unresolved zero.

- [ ] **Step 5: Merge evidence through the normalizer**

Add bridge evidence after Companyfacts normalization but before `reconcile_bridge()`. Validate every record by `FieldAvailability.from_dict(record.as_dict())`. Persist rejected candidates at `financials.balance_sheet.bridge_evidence_diagnostics`. Never let lower-level evidence overwrite a valid higher-level record; turn unequal current evidence into an explicit conflict.

- [ ] **Step 6: Run focused and full tests**

```bash
PYTHONPATH=backend pytest -q \
  backend/tests/test_structural_promotion.py \
  backend/tests/test_bridge_policy_pipeline.py \
  backend/tests/test_structural_xbrl_integration.py
PYTHONPATH=backend pytest -q backend/tests
```

- [ ] **Step 7: Commit**

```bash
git add \
  backend/app/us_valuation/structural_promotion.py \
  backend/app/us_valuation/config/batch_01_structural_promotions.json \
  backend/app/us_valuation/field_availability.py \
  backend/app/us_valuation/xbrl.py \
  backend/app/us_valuation/pipeline.py \
  backend/tests/test_structural_promotion.py \
  backend/tests/test_bridge_policy_pipeline.py
git diff --cached --check
git commit -m "feat: govern exact structural evidence promotion"
```

**Gate:** Arelle can improve only the exact reviewed Batch 01 facts; no absence, approximate match, conflict, or unrelated structural fact receives production authority.

---

### Task 5: Bound remaining FCFF bridge gaps with reported aggregates

**Files:**

- Create: `backend/app/us_valuation/bridge_fallbacks.py`
- Modify: `backend/app/us_valuation/bridge_policy.py`
- Create: `backend/tests/test_bridge_fallbacks.py`
- Modify: `backend/tests/test_bridge_policy.py`
- Modify: `backend/tests/test_bridge_policy_pipeline.py`

**Interfaces:**

- Produces `derive_reported_aggregate_fallbacks(*, companyfacts: Mapping[str, object], availability: Mapping[str, FieldAvailability], period_end: str, valuation_date: str) -> tuple[FieldAvailability, ...]`.
- Fallbacks are production `bounded_unresolved` records with `fallback_level="reported_aggregate"`; they never create a zero point.
- Covers only unresolved marketable securities and the complete debt/lease group. Preferred equity and NCI still require direct, structural, annual, or other approved evidence.

- [ ] **Step 1: Write failing aggregate-bound tests**

Use current source-linked `Assets`, `AssetsCurrent`, `Liabilities`, and cash facts from one controlling accession. Assert:

```python
assert current_securities.uncertainty.low == 0.0
assert current_securities.uncertainty.high == assets_current - cash
assert noncurrent_securities.uncertainty.low == 0.0
assert noncurrent_securities.uncertainty.high == assets - assets_current
assert total_debt.uncertainty.low == known_debt_and_lease_floor
assert total_debt.uncertainty.high == liabilities
assert total_debt.covered_fields == (
    "commercial_paper",
    "current_debt",
    "finance_lease_current",
    "finance_lease_noncurrent",
    "noncurrent_debt",
)
```

Add rejection tests for mixed accessions/periods, future filing dates, negative/non-finite totals, liabilities below the known debt floor, current assets below cash, current assets above assets, missing provenance, conflicting source facts, and a requested preferred-equity/NCI fallback.

- [ ] **Step 2: Run tests and verify RED**

```bash
PYTHONPATH=backend pytest -q \
  backend/tests/test_bridge_fallbacks.py \
  backend/tests/test_bridge_policy.py \
  -k 'aggregate or fallback or bounded'
```

Expected: there is no production path that turns current reported totals into bounded bridge evidence.

- [ ] **Step 3: Implement exact aggregate formulas**

Select only non-dimensional instant USD facts from forms filed on/before `2026-08-14`, at the requested period, with complete accession provenance. Prefer `Liabilities`; use no `LiabilitiesAndStockholdersEquity` substitute. For securities, require `Assets`, `AssetsCurrent`, and cash to describe the same controlling period. For debt, set the lower bound to the sum of already accepted non-overlapping debt/lease points and the upper bound to reported liabilities.

Count `finance_lease_total` when it is a valid complete-coverage aggregate; otherwise count its current/noncurrent split, never both.

Use reason codes `AGGREGATE_CURRENT_ASSET_SECURITIES_BOUND`, `AGGREGATE_NONCURRENT_ASSET_SECURITIES_BOUND`, and `AGGREGATE_TOTAL_LIABILITY_DEBT_BOUND`. Put every source accession in `UncertaintyRange.source_accessions` and describe the arithmetic in `basis`.

- [ ] **Step 4: Permit a complete bounded aggregate to replace unusable detail**

In `bridge_policy._aggregate_candidate()`, an explicit complete-coverage current aggregate may replace missing/stale/rejected detail or lower-ranked `annual_carried_forward` detail without adding those displaced records as blockers. A valid current direct or current structural point conflict against the aggregate remains blocking. Preserve every displaced lower-level reason in private diagnostics so replacement does not hide it.

Do not weaken coverage equality, source completeness, authority, freshness, unit/currency, range arithmetic, or aggregate-vs-complete-detail corroboration.

- [ ] **Step 5: Prove finite low-reliability behavior through the real model**

Run the real ANET reduced fixture with exact promoted structural facts plus reported aggregate bounds. Assert finite ordered FCFF/scenario ranges, `bounded_review`, and `Low` reliability when accounting impact exceeds 20%. Add a DELL case for bounded current securities. Assert no unrelated model switch and no zero substitution.

- [ ] **Step 6: Run focused and full tests**

```bash
PYTHONPATH=backend pytest -q \
  backend/tests/test_bridge_fallbacks.py \
  backend/tests/test_bridge_policy.py \
  backend/tests/test_bridge_policy_pipeline.py
PYTHONPATH=backend pytest -q backend/tests
```

- [ ] **Step 7: Commit**

```bash
git add \
  backend/app/us_valuation/bridge_fallbacks.py \
  backend/app/us_valuation/bridge_policy.py \
  backend/tests/test_bridge_fallbacks.py \
  backend/tests/test_bridge_policy.py \
  backend/tests/test_bridge_policy_pipeline.py
git diff --cached --check
git commit -m "feat: bound unresolved bridges with reported totals"
```

**Gate:** Remaining Batch 01 FCFF gaps can become source-backed uncertainty ranges without fabricated zeros, double counting, or source-integrity relaxation.

---

### Task 6: Build the fixed offline ten-company generator

**Files:**

- Create: `scripts/run_batch_01_ten_company.py`
- Create: `backend/tests/test_batch_01_ten_company.py`

**Interfaces:**

- Exposes `run_batch(*, source_root: Path, output_root: Path) -> dict[str, object]` and CLI options `--source-root` and `--output-root`.
- Writes only `generated/{TICKER}/valuation-private.json`, `staged-public/{TICKER}.json`, `batch-report.json`, and `batch-report.md` below the requested non-serving output root.
- Uses canonical `public_result()` and emits the six named pre-API generation gates, hashes, values, reliability, fallback levels, rejected conflicts, and blockers. It does not call a company complete before deterministic replay and API verification.

- [ ] **Step 1: Write failing exact-denominator and safety tests**

Build a ten-packet hermetic corpus from reduced fixtures. Assert the runner:

- attempts exactly `BATCH_01_TICKERS` in manifest order;
- refuses duplicate/missing/extra packet directories;
- verifies every `source-manifest.json` hash before reading source data;
- calls real `build_us_valuation()` and `public_result()` rather than mocking values;
- does not instantiate `SecClient`, open a socket, or import Arelle;
- rejects output inside/symlinked to serving or frontend roots;
- leaves serving-tree hashes unchanged;
- keeps a failing member in the denominator with an explicit blocker;
- writes no public artifact for the wrong identity or lane; and
- is byte-identical on two runs from the same immutable packets.

- [ ] **Step 2: Run tests and verify RED**

```bash
PYTHONPATH=backend pytest -q backend/tests/test_batch_01_ten_company.py
```

Expected: collection fails because the runner does not exist.

- [ ] **Step 3: Implement the per-company build sequence**

For each manifest member:

1. validate packet identity and hashes;
2. build once from Companyfacts;
3. if an FCFF bridge remains unresolved and `structural-filing.json` exists, reconstruct `StructuralFiling`, resolve only the explicit missing fields, promote only exact allowlisted decisions, and rebuild with those records;
4. if eligible FCFF gaps remain, derive reported-aggregate fallback records and rebuild with direct + structural + bounded evidence;
5. serialize through canonical `public_result()`;
6. validate ticker, CIK, lane, currency, ordered finite low/base/high, reliability DTO, public data boundary, prohibited-output check, and source dates; and
7. write private/public files atomically under the non-serving output root.

Do not switch lanes or alter assumptions after seeing a result. O must include `model_cap="Low"` and `INTERIM_FFO_ROUTE`.

- [ ] **Step 4: Implement exact reporting and exit behavior**

`batch-report.json` contains:

```python
{
    "batch": "BATCH-01",
    "valuation_date": "2026-08-14",
    "expected_count": 10,
    "attempted_count": 10,
    "generation_pass_count": int,
    "generation_failed_count": int,
    "status": "generation_pass" | "partial" | "failed",
    "serving_artifacts_changed": False,
    "companies": [...],
}
```

Each company row contains identity, source hashes, accepted/rejected evidence, lane, private/public hashes, low/base/high, unit, currency, share-denominator provenance, accounting impact, scenario movement, final label, caps, reason codes, blockers, and exactly these six generation booleans:

- `identity_matches_manifest`;
- `source_evidence_complete`;
- `governed_lane_matches`;
- `valuation_range_valid`;
- `reliability_valid`; and
- `public_boundary_safe`.

Exit `0` only when all six generation gates pass for 10/10 with zero source/build/safety failure; otherwise exit nonzero after writing the full report. The later API receipt adds `deterministic_regeneration` and `api_matches_artifact`; only that combined eight-gate receipt may call a company complete.

- [ ] **Step 5: Run focused and full tests**

```bash
PYTHONPATH=backend pytest -q backend/tests/test_batch_01_ten_company.py
PYTHONPATH=backend pytest -q backend/tests
```

- [ ] **Step 6: Commit**

```bash
git add scripts/run_batch_01_ten_company.py backend/tests/test_batch_01_ten_company.py
git diff --cached --check
git commit -m "feat: generate fixed ten-company valuation batch"
```

**Gate:** One offline command truthfully yields exactly ten explicit decisions and cannot mutate serving/frontend data.

---

### Task 7: Verify through HTTP and guard exact-ten promotion

**Files:**

- Create: `scripts/verify_batch_01_api.py`
- Create: `scripts/promote_batch_01_ten_company.py`
- Create: `backend/tests/test_batch_01_promotion.py`

**Interfaces:**

- `verify_api(*, base_url: str, run_root: Path, comparison_run_root: Path, output_path: Path) -> dict[str, object]` checks the real list and all ten detail endpoints against `run_root/staged-public`, compares the two runs' exact deterministic artifact allowlist, and writes a hash-bound eight-gate verification receipt.
- `promote(*, batch_root: Path, serving_root: Path) -> dict[str, object]` requires a 10/10 generation report plus a successful `complete_count=10` staged API receipt, then replaces exactly ten serving JSON files with rollback support.
- `recover_interrupted_promotion(*, batch_root: Path, serving_root: Path) -> dict[str, object]` validates an `in_progress` journal and restores all ten exact backup bytes before any new promotion attempt.
- Promotion never writes frontend files and cannot operate on `main` or a non-feature branch.

- [ ] **Step 1: Write failing HTTP-verifier and promotion tests**

Use a real `TestClient`-served temporary staged root and assert:

- list contains all ten expected identities with no duplicate;
- every detail has the same low/base/high, lane, and reliability label as the original `run_root/staged-public` file;
- the receipt lists all eight named per-company gates and uses `complete_count` only after all eight pass;
- changing either run's allowlisted private/public/report bytes fails deterministic regeneration, while verifier/promotion receipts and backups are explicitly outside that hash scope;
- response status, malformed JSON, unexpected ticker, hash mismatch, or list/detail mismatch fails the receipt;
- promotion rejects 9/10, 10/11, partial reports, stale receipts, receipt hashes for another staged root, unclean staged files, unsafe paths, `main`, and any destination outside the exact ten filenames;
- a forced failure after the fifth replace restores all ten original bytes;
- a pre-existing `in_progress` journal with five already-replaced files is recovered from validated backups before a retry; and
- successful promotion changes exactly ten backend files and zero frontend files.

- [ ] **Step 2: Run tests and verify RED**

```bash
PYTHONPATH=backend pytest -q backend/tests/test_batch_01_promotion.py
```

Expected: verifier and promotion scripts do not exist.

- [ ] **Step 3: Implement the API receipt**

Use standard-library HTTP requests with bounded timeouts. The deterministic hash allowlist is exactly both runs' `generated/{TICKER}/valuation-private.json`, `staged-public/{TICKER}.json`, `batch-report.json`, and `batch-report.md`; exclude API receipts, promotion receipts, journals, backups, logs, and every other file. Include the expected staged-public hashes in the API receipt. For each company, carry forward the six generation booleans and add `deterministic_regeneration` and `api_matches_artifact`. The receipt is `pass` with `complete_count=10` only when all eight gates pass for all ten. It performs no write except its requested receipt path below the batch output root.

- [ ] **Step 4: Implement guarded promotion**

Before replacement, verify branch `feat/whole-universe-greenlight`, generation status 10/10, staged API receipt status 10/10 complete, exact manifest filenames, staged hashes, and receipt hashes. If an `in_progress` journal exists, validate its paths and backup hashes and recover all ten originals before continuing; an invalid journal fails closed. Save original destination bytes and hashes under `output/batch-01-ten-company/promotion-backup/`, durably write an `in_progress` journal, then write each destination through a sibling temporary file and `os.replace()`. No API server may run during promotion. On any exception, restore every original byte, mark the journal rolled back, and exit nonzero. On the next invocation after process interruption, recovery runs before any new write. On success, assert only the ten destination hashes changed, mark the journal complete, and write a promotion receipt under output.

- [ ] **Step 5: Run focused and full tests**

```bash
PYTHONPATH=backend pytest -q backend/tests/test_batch_01_promotion.py
PYTHONPATH=backend pytest -q backend/tests
```

- [ ] **Step 6: Commit the tooling before touching serving artifacts**

```bash
git add \
  scripts/verify_batch_01_api.py \
  scripts/promote_batch_01_ten_company.py \
  backend/tests/test_batch_01_promotion.py
git diff --cached --check
git commit -m "feat: guard batch one api promotion"
```

**Gate:** Promotion is mechanically impossible until the staged real API proves all ten, and a failed promotion restores the original serving files.

---

### Task 8: Run, promote, verify, document, and stop

**Files:**

- Create: `docs/audit/06-batch-01-ten-company-verification.md`
- Modify: exactly these serving artifacts only:
  - `backend/app/data/us_valuations/AAPL.json`
  - `backend/app/data/us_valuations/MSFT.json`
  - `backend/app/data/us_valuations/CRM.json`
  - `backend/app/data/us_valuations/ANET.json`
  - `backend/app/data/us_valuations/WDC.json`
  - `backend/app/data/us_valuations/DELL.json`
  - `backend/app/data/us_valuations/JPM.json`
  - `backend/app/data/us_valuations/BAC.json`
  - `backend/app/data/us_valuations/NEE.json`
  - `backend/app/data/us_valuations/O.json`

**Interfaces:**

- Consumes all reviewed Tasks 1–7 and a monitored SEC user agent when uncached network capture is required.
- Produces immutable untracked source/run evidence, exactly ten promoted feature-branch artifacts only after 10/10 staged API proof, and one tracked verified-vs-unverified audit.

- [ ] **Step 1: Reconfirm prerequisite and working-tree boundaries**

```bash
git branch --show-current
git status --short
PYTHONPATH=backend pytest -q backend/tests
```

Expected: feature branch, only known `output/` untracked before source capture, and full suite passes. Confirm the Phase 1 audit status is verified rather than partial/blocked.

- [ ] **Step 2: Capture all ten source packets**

First check whether `SEC_USER_AGENT` is set without printing its value:

```bash
test -n "$SEC_USER_AGENT"
```

If it is unset and any packet requires network, stop this task and ask the user to supply or authorize a monitored SEC contact. Do not reuse or reveal an email from git configuration without explicit approval.

With authorization present, run:

```bash
PYTHONPATH=backend python3 scripts/capture_batch_01_sources.py \
  --output-root output/batch-01-ten-company/sources \
  --user-agent "$SEC_USER_AGENT" \
  --refresh
```

Expected: 10/10 source packets, zero identity/date/hash failures, Arelle invoked only for supported unresolved FCFF cases, and zero serving/frontend changes.

- [ ] **Step 3: Generate twice and prove deterministic 10/10**

```bash
PYTHONPATH=backend python3 scripts/run_batch_01_ten_company.py \
  --source-root output/batch-01-ten-company/sources \
  --output-root output/batch-01-ten-company/run-1
PYTHONPATH=backend python3 scripts/run_batch_01_ten_company.py \
  --source-root output/batch-01-ten-company/sources \
  --output-root output/batch-01-ten-company/run-2
```

Require both reports to say attempted 10, generation-pass 10, status `generation_pass`, and serving changes false. Do not yet call the batch complete: deterministic equality and API agreement are added by the next receipt. If a company fails, retain `X/10 generated`, diagnose only that fixed member, add a regression test to the owning task's file, and rerun; never replace it or start Batch 02.

- [ ] **Step 4: Verify the staged artifacts through a real HTTP server**

Start this in a dedicated managed terminal/session:

```bash
APP_ENV=test \
JWT_ACCESS_SECRET=test-access-secret \
JWT_REFRESH_SECRET=test-refresh-secret \
PGHOST=localhost \
PGPORT=5432 \
PGUSER=test \
PGPASSWORD=test \
PGDATABASE=test \
MINIO_ENDPOINT=http://localhost:9000 \
MINIO_ROOT_USER=test \
MINIO_ROOT_PASSWORD=test \
MINIO_BUCKET=test \
FINSIGHT_US_VALUATION_DATA_ROOT=output/batch-01-ten-company/run-1/staged-public \
PYTHONPATH=backend \
uvicorn app.main:app --host 127.0.0.1 --port 8012
```

Then run:

```bash
PYTHONPATH=backend python3 scripts/verify_batch_01_api.py \
  --base-url http://127.0.0.1:8012/api/us-valuations \
  --run-root output/batch-01-ten-company/run-1 \
  --comparison-run-root output/batch-01-ten-company/run-2 \
  --output output/batch-01-ten-company/run-1/staged-api-verification.json
```

Require list plus all ten details and deterministic replay to pass, producing the first valid `complete_count=10` eight-gate receipt. Stop the server cleanly before promotion and verify port `8012` is no longer listening.

- [ ] **Step 5: Promote exactly ten and verify the serving API**

```bash
PYTHONPATH=backend python3 scripts/promote_batch_01_ten_company.py \
  --batch-root output/batch-01-ten-company/run-1 \
  --serving-root backend/app/data/us_valuations
```

Start the serving API in a dedicated managed terminal/session with the override forcibly removed:

```bash
env -u FINSIGHT_US_VALUATION_DATA_ROOT \
  APP_ENV=test \
  JWT_ACCESS_SECRET=test-access-secret \
  JWT_REFRESH_SECRET=test-refresh-secret \
  PGHOST=localhost \
  PGPORT=5432 \
  PGUSER=test \
  PGPASSWORD=test \
  PGDATABASE=test \
  MINIO_ENDPOINT=http://localhost:9000 \
  MINIO_ROOT_USER=test \
  MINIO_ROOT_PASSWORD=test \
  MINIO_BUCKET=test \
  PYTHONPATH=backend \
  uvicorn app.main:app --host 127.0.0.1 --port 8013
```

Then compare the serving API to the original staged run, not to the serving directory itself:

```bash
PYTHONPATH=backend python3 scripts/verify_batch_01_api.py \
  --base-url http://127.0.0.1:8013/api/us-valuations \
  --run-root output/batch-01-ten-company/run-1 \
  --comparison-run-root output/batch-01-ten-company/run-2 \
  --output output/batch-01-ten-company/run-1/serving-api-verification.json
```

Require the ten promoted responses to match the original staged hashes, confirm all non-batch serving artifacts are byte-identical to their pre-promotion hashes, then stop the server cleanly.

- [ ] **Step 6: Record simple verified evidence**

Create `docs/audit/06-batch-01-ten-company-verification.md` with:

- branch and exact commits;
- fixed manifest/date and baseline `5/10` numeric;
- source packet and Arelle counts;
- one row per company with lane, filing accession/period, unit, currency, share-denominator provenance, fallback level, low/base/high, accounting impact, scenario movement, label, caps, and all eight named gate results;
- exact before/after counts stated as `X out of 10`;
- focused/full test outputs;
- deterministic replay hashes;
- staged and serving API receipt results;
- exact ten changed serving files and zero frontend/main changes;
- rejected conflicts and remaining caveats; and
- every claim labeled `Verified` or `Unverified`.

Status is `verified — user confirmation needed` only for 10/10. Otherwise use `partial — X/10` and name the fixed failing members.

- [ ] **Step 7: Final verification and commit**

```bash
PYTHONPATH=backend pytest -q backend/tests
git diff --check
git status --short
git diff --name-only
```

Verify the diff contains the audit plus exactly ten serving JSON files and no `output/` paths. Then:

```bash
git add \
  docs/audit/06-batch-01-ten-company-verification.md \
  backend/app/data/us_valuations/AAPL.json \
  backend/app/data/us_valuations/MSFT.json \
  backend/app/data/us_valuations/CRM.json \
  backend/app/data/us_valuations/ANET.json \
  backend/app/data/us_valuations/WDC.json \
  backend/app/data/us_valuations/DELL.json \
  backend/app/data/us_valuations/JPM.json \
  backend/app/data/us_valuations/BAC.json \
  backend/app/data/us_valuations/NEE.json \
  backend/app/data/us_valuations/O.json
git diff --cached --check
git commit -m "data: promote verified first valuation batch"
git push origin feat/whole-universe-greenlight
```

**Gate:** The feature branch serves verified matching values for all 10/10 fixed companies, all evidence is recorded, and no implementation or generation begins for Batch 02.

## Stop condition

Report the outcome simply as `X/10 complete`, list any Low-reliability companies and why, link the audit and branch, and ask the user to confirm Batch 01. Do not continue to another company without a new explicit instruction.
