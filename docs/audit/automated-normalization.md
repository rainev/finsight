# AR2: automated valuation normalization

Checked 2026-09-08 against the named source modules.

## Reference
User-approved Automated U.S. Valuation Pipeline Improvements plan.

## Ours today
history.py provides medians and period/source metadata; practical_models.py provides cash FCFF and claims arithmetic. Working-capital/unusual-item treatment is distributed across issuer/batch branches.

## Reuse and consumer flow
Reuse source capture, pure model engines, sanitizer, and versioned catalog. Target flow: capture -> normalize -> evaluate -> validate -> complete catalog -> API/browser.

## Gaps
- P0 ✔ AR2: One auditable normalization contract with evidence-backed cash adjustments, total-capex defaults and finite timed commitments.
- Runtime validation for the replacement flow remains open; existing tests do not establish new-flow acceptance.

## Evidence and status
Firsthand source review and prior reproduction in this task. Open; tracked by AUTOMATED-US-VALUATION.md.
