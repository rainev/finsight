# AR4: automated valuation forecast-evaluation

Checked 2026-09-08 against the named source modules.

## Reference
User-approved Automated U.S. Valuation Pipeline Improvements plan.

## Ours today
Frozen reports and scenario traces exist. No forecast-vintage versus later-actual evaluation command is present in inspected scripts.

## Reuse and consumer flow
Reuse source capture, pure model engines, sanitizer, and versioned catalog. Target flow: capture -> normalize -> evaluate -> validate -> complete catalog -> API/browser.

## Gaps
- P0 ✔ AR4: Immutable forecasts/actual vintages, period/scope matched errors and coverage; no automatic policy changes.
- Runtime validation for the replacement flow remains open; existing tests do not establish new-flow acceptance.

## Evidence and status
Firsthand source review and prior reproduction in this task. Open; tracked by AUTOMATED-US-VALUATION.md.
