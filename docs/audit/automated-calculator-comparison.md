# AR3: automated valuation calculator-comparison

Checked 2026-09-08 against the named source modules.

## Reference
User-approved Automated U.S. Valuation Pipeline Improvements plan.

## Ours today
Rechecked 2026-09-08: migrated private recipes independently evaluate each scenario. All 419 numeric frozen records now replay, including Charter's source-input DCF and locked transaction overlay. Real local API and browser reproduce Charter's $50.648007926630015 default and $118.83472551899075 edited base at 8% discount. Legacy proportional sensitivity remains only for catalogs without migrated recipes; full rollout remains gated. Current/historical EOD separation and scenario comparison recalculation were previously implemented and tested.

## Reuse and consumer flow
Reuse source capture, pure model engines, sanitizer, and versioned catalog. Target flow: capture -> normalize -> evaluate -> validate -> complete catalog -> API/browser.

## Gaps
- P0 ✔ AR3: Executable private recipes for all prior numeric companies; same evaluator for each edited scenario; independent current/historical comparison dates; stale-baseline rejection.
- Runtime validation for the replacement flow remains open; existing tests do not establish new-flow acceptance.

## Evidence and status
Firsthand source review and prior reproduction in this task. Open; tracked by AUTOMATED-US-VALUATION.md.
