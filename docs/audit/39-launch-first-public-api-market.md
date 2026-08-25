# Launch-first public API, calculator, and market-comparison gap

Reference: user-supplied `FinSight Launch-First Valuation Plan`, sections 3, 4, 6, 8, and 9.

## Reference

Public v1.2 should expose availability, primary method, low/base/high, confidence reasons, a derived
market-gap percentage/date, relative summary, and calculator link. Raw vendor and peer prices remain
private. GET/POST calculator endpoints must lock source facts, allow only model-suitable assumptions,
reproduce the baseline by default, accept an optional manual price, and save only explicit custom runs.

## Ours today

- The U.S. router is read-only list/detail (`backend/app/routers/us_valuations.py:59`).
- The public contract is v1.1 with an explicit top-level allowlist but no launch-first fields
  (`backend/app/us_valuation/artifacts.py:165`, `backend/app/us_valuation/artifacts.py:330`).
- The generic `/api/valuations` calculator and JSONB persistence are reusable mechanically, but they
  accept editable raw inputs and are not tied to a locked U.S. baseline
  (`backend/app/routers/valuations.py:37`, `backend/app/services/valuation_service.py:11`).
- No private U.S. EOD/peer repository or market-gap service exists in the target worktree.

## Reuse check

Extend the existing public allowlist/sanitizer and `valuations` persistence rather than bypassing them.
Load static private calculator/EOD records in the serving process; never import ingestion/vendor clients.
Reuse current valuation engines for recalculation and a U.S.-specific safe saved-run DTO.

## Flow

Callers can fetch a public artifact but cannot discover editable defaults, recalculate, compare against
an automatic/manual price, reset, or save a U.S. custom run. Adding raw EOD fields to the public JSON
would be stripped today; widening the allowlist to raw provider fields would violate the plan.

## What backs it

- Direct router/schema/frontend search in the named worktree.
- Public DTO projection at `backend/app/us_valuation/artifacts.py:588`.
- Existing forbidden price/raw-fact tests at `backend/tests/test_us_valuation.py:177` and nested
  allowlist tests at `backend/tests/test_us_valuation.py:2006`.

## Gaps

- **LF-A1 · P0 · ✔** `US-PUBLIC-VALUATION-1.2` and its compatibility fields are absent.
- **LF-A2 · P0 · ✔** GET/POST `/{ticker}/calculator` and model-specific override validation are absent.
- **LF-A3 · P0 · ✔** No separate private EOD contract validates canonical security, listing, currency,
  split-adjusted close, date, provider, and payload hash before deriving a public comparison.
- **LF-A4 · P0 · ✔** No explicit public DTO proves raw EOD/peer/provider/hash values are excluded while
  derived percentage/date survive sanitization.
- **LF-A5 · P1 · ✔** Saved valuations lack an explicit U.S. company/ticker/model-version/user-price
  contract, and generic saved responses are not the planned safe U.S. result.
- **LF-A6 · P1 · ✔** The plan's formula uses intrinsic value as denominator. The public label must say
  “discount/premium to FinSight value” (or otherwise define the denominator) rather than imply a
  conventional return-to-market-price percentage.
- **LF-A7 · P1 · ✔** No actual private vendor EOD dataset is present. Provider-neutral validation and
  loading can be implemented and tested now; automatic live percentages remain data-blocked until
  approved records are supplied.
