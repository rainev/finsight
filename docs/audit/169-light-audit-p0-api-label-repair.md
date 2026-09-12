# Light-audit P0 API label repair

Date: 2026-09-12
Status: user-confirmed; P0 closed.

## Intended behavior

Every manifest-controlled public artifact must retain its stored Pass/Conditional/Withheld availability label when read
through the real FastAPI list and detail endpoints. The parity verifier must compare the API with the raw canonical
catalog label rather than reproduce the API's sanitization.

## Cause

`baseline_from_public_artifact()` preserved explicit availability for residual-income, enterprise-FCFF and utility-FCFE
exact modes, but omitted `reit_affo_exact` and `timber_distribution_exact`. FastAPI sanitizes a stored artifact again at
`backend/app/routers/us_valuations.py:166-174`, so 26 Batch 48-50 REIT/timber artifacts were reclassified from
`conditional_estimate` to `available`.

The existing verifier sanitized its expected artifact at `scripts/verify_official_evidence_api.py:74-76`, reproducing
and hiding the same mutation.

## Repair

- Added `reit_affo_exact` and `timber_distribution_exact` to the existing explicit-availability preservation rule in
  `backend/app/us_valuation/baseline.py`.
- Changed `scripts/verify_official_evidence_api.py` to treat manifest-controlled catalog artifacts as already public and
  canonical, then add only runtime-owned catalog/freshness/date fields before comparison.
- Added all-500 sanitizer idempotency coverage plus direct Batch 50 REIT and Batch 48 timber regression checks.
- Updated the sanitizer/parity learnings so future verifiers cannot hide a serving mutation by transforming both sides.

## Verification evidence

- Focused sanitizer/catalog/batch tests: **27 passed**.
- Complete backend suite: **2,378 passed / 3 skipped**.
- Real staged FastAPI counts after repair: **116 available / 358 Conditional / 26 Withheld**, exactly matching the raw
  500-entry manifest; mismatch count **0**.
- Real list/detail parity: **500/500**; calculator-default parity: **500/500**.
- Private leaks: **0**; forbidden serving imports: **0**.
- Availability receipt:
  `output/universe-500-p0-label-repair-20260912/availability-parity-receipt.json`.
- Official-evidence API receipt SHA-256:
  `1cfcc6e61d08bd7b391a9de5425a29b783900cd3435835b8be417ca0d9f1f60e`.
- Launch-first API receipt SHA-256:
  `fdfb01bd53e22912cfcb562f8fa509129fcc1b8bd5b8385a8c6c8ad03dc57450`.

## Boundary

The user confirmed the repair. The stored 500-company catalog, valuation values, reliability labels, Recovery Learning
Watchlist and production serving pointer were not changed. The five P1 light-audit findings and two release gates remain
open; promotion, merge, push and deployment remain unauthorized.
