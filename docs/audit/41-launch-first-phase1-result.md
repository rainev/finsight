# Launch-first Phase 1 result

## Intended behavior

Every sanitized U.S. valuation, including legacy artifacts, projects into the v1.2 retail baseline
contract; hard failures stay unavailable; private EOD records are validated separately and only a
derived discount/premium-to-FinSight percentage and date may reach public output.

## Implemented

- `backend/app/us_valuation/baseline.py` defines availability, assumption classification, ordered
  fallback attempts, `BaselineValuation`, the table-driven ladder, and legacy-to-v1.2 projection.
- `backend/app/us_valuation/market_comparison.py` validates private canonical security, primary
  listing, USD currency, positive split-adjusted close, date, provider, and hashes, then emits only
  the plan's `(base - price) / base` comparison.
- `backend/app/us_valuation/artifacts.py` now emits `US-PUBLIC-VALUATION-1.2`, treats v1.1 as current
  for one compatibility cycle, retains the v1.1 fields, and explicitly allowlists the new retail
  fields. Missing approved EOD data becomes `comparison unavailable`.

## Verification evidence

- Focused contract/artifact/Batch 03 suite: **194 passed, 3 skipped, 1 warning**.
- Real localhost FastAPI served the exact Batch 03 candidate-g directory:
  - list HTTP 200, exact count 10, exact staged parity;
  - detail 10/10 HTTP 200 with exact staged parity;
  - private leaks 0;
  - forbidden serving imports 0.
- Runtime spot checks:
  - NWSA: v1.2, `available`, Low confidence with published reasons, comparison unavailable,
    calculator link present;
  - GOOGL: v1.2, `not_available`, no confidence, comparison unavailable, calculator link present.
- Receipt: `output/launch-first/lf1-real-api.json`.
- `git diff --check`: passed before the live run.

## Gate

LF1 is **firsthand verified**. No serving artifact, approved EOD record, Batch 04 state, merge, push,
or deployment changed. Automatic percentages remain honestly unavailable until private records pass
the new validator.
