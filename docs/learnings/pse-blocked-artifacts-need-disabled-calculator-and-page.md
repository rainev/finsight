---
name: pse-blocked-artifacts-need-disabled-calculator-and-page
description: A source-bounded null PSE result must return a disabled calculator view and render a real unavailable page, or the combined page load fails.
metadata: { type: gotcha }
---
The PSE V2 `not_available` artifact contract already allowed null values, but before Batch 12 `calculator_view` unconditionally read a numeric market-relative baseline. The PSE page fetched detail and calculator together, so a genuinely blocked issuer would show a generic load error instead of its reason and sources.

**Why:** Contract-valid null artifacts can still be unusable at the API/UI boundary if every consumer assumes a calculator baseline.

**How to detect / apply:** For each blocked issuer, verify real `GET /api/pse-valuations/{ticker}` returns null values and reasons, `GET .../calculator` returns `can_calculate: false` with a null baseline, and `POST .../calculator` rejects edits. Exercise the actual PSE page: it must show the blocked status, reason, and source links with no fabricated numerical range or enabled calculator. Keep the seven-day calendar and US/PH navigation available.
