# FinSight U.S. valuation profile

## The real thing

For accounting and model work, the real thing is a source-linked SEC filing package processed through Companyfacts/Arelle, FinSight normalization, the correct valuation lane, generated public-safe JSON, and the FastAPI valuation endpoint.

For user-facing work, the real thing continues through the React U.S. valuation list and detail page.

## How to exercise it

1. Run focused and full automated tests to catch contract regressions.
2. Re-run the relevant pipeline on cached real SEC filings without network acquisition or serving-data mutation.
3. Validate counts, sources, periods, units, currencies, share denominators, model lanes, value ranges, and reliability labels.
4. Request the real list and detail API endpoints.
5. When UI behavior changes, drive the list-to-detail flow in the running browser application.

## Required evidence

- Exact commands and outputs.
- Attempted and accepted counts with named denominators and selection rules.
- Before/after replay artifacts outside serving directories.
- Representative company traces with filing accession, period, model lane, fallback level, value range, and reliability reason.
- API response samples; browser evidence for UI phases.
- Explicit failures, skipped checks, and unverified claims.

## Completion rule

A phase may be reported as `verified — user confirmation needed` only after its real consumer path matches the approved design. It becomes done only after the user confirms it. Tests, a replay file, or a screenshot alone are insufficient.
