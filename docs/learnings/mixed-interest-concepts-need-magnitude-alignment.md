---
name: mixed-interest-concepts-need-magnitude-alignment
description: Align expense magnitudes before TTM arithmetic when annual interest is positive but comparative net-interest facts are negative.
metadata: { type: gotcha }
---
A TTM reconstruction must not directly combine a positive annual `InterestExpense` fact with
negative current/prior `InterestIncomeExpenseNonoperatingNet` facts. First interpret all three
as expense magnitudes, then calculate `FY magnitude + current YTD magnitude - prior YTD
magnitude`.

**Why:** signed arithmetic followed by one final `abs()` changes the economic expense and can
silently move cash FCFF and valuation sensitivities even though every source fact is real.

**How to detect / apply:** inspect the exact concepts and signs of all three TTM components. If
their accounting sign conventions differ, source-bind the components and record the explicit
magnitude-alignment method. Regression-test the reconstructed expense and cash-FCFF result.

Batch 24 exposed a stricter variant for TransDigm: appending `InterestIncomeExpenseNet` to the
shared aliases selected a negative annual net-interest fact but positive current/prior
`InterestExpenseNonoperating` facts. The arithmetic produced −$1.252B and a final `abs()` made the
result look valid. The consistent cash-interest series was instead `InterestPaidNet` for all three
components: $1.481B FY + $1.210B current H1 − $908M prior H1 = $1.783B TTM.

**How to detect / apply:** Prefer one economically consistent concept across FY/current/prior
before attempting sign alignment across different concepts. For cash-FCFF, a complete
`InterestPaidNet` series is a defensible issuer-specific cash-interest proxy. Reject a TTM result
whose components change both concept and sign unless the filing explicitly reconciles them.
