---
name: mixed-interest-concepts-need-magnitude-alignment
description: Preserve interest-income signs and require one reconciled gross or net basis across all TTM constituents.
metadata: { type: gotcha }
---
A TTM reconstruction must not directly combine gross `InterestExpense` facts with
`InterestIncomeExpenseNonoperatingNet` facts. They differ economically, not just in sign.
Use a consistent, source-backed basis across FY/current/prior YTD. A positive net-income
fact is income: subtract it when removing nonoperating financing from operating cash flow;
do not turn it into an expense with `abs()`.

**Why:** signed arithmetic followed by one final `abs()` changes the economic expense and can
silently move cash FCFF and valuation sensitivities even though every source fact is real.

**How to detect / apply:** inspect the exact concepts and signs of all three TTM components. If
their accounting bases differ, reject the mix unless the filing explicitly reconciles it.
Regression-test the reconstructed expense/income and cash-FCFF result. Also require contiguous
FY/current/prior periods: a missing prior FY must not silently pair an older annual with a new YTD.

2026-09-08 correction: real Copart's positive $192.144M net-interest TTM is income. Refresh
normalization v2 subtracts its $154.606M after-tax amount. Legacy v1 remains replay-only.
The earlier instruction to align all net-interest facts as expense magnitudes was overbroad.

Batch 24 exposed a stricter variant for TransDigm: appending `InterestIncomeExpenseNet` to the
shared aliases selected a negative annual net-interest fact but positive current/prior
`InterestExpenseNonoperating` facts. The arithmetic produced −$1.252B and a final `abs()` made the
result look valid. The consistent cash-interest series was instead `InterestPaidNet` for all three
components: $1.481B FY + $1.210B current H1 − $908M prior H1 = $1.783B TTM.

**How to detect / apply:** Prefer one economically consistent concept across FY/current/prior
before attempting sign alignment across different concepts. For cash-FCFF, a complete
`InterestPaidNet` series is a defensible issuer-specific cash-interest proxy. Reject a TTM result
whose components change both concept and sign unless the filing explicitly reconciles them.

Batch 31 repeated this trap for CDW. The default alias produced a negative `$229M` net-interest TTM
that became a positive addback only after `abs()`. CDW reported a complete, consistently positive
`InterestPaidNet` lineage instead: `$234.3M` FY + `$116.9M` current H1 − `$120.4M` prior H1 =
`$230.8M` TTM. Using that cash-interest series also repaired the annual cash-margin history.

**How to detect / apply:** When cash-FCFF is the model, prefer the issuer's complete cash-interest
series over a mixed-sign net-interest alias and record that semantic choice in private assumptions.

Refresh now has a CDW-only versioned cash-interest selector: every TTM constituent
must be nonnegative, periods contiguous, and annual history must use the same
concept. It never falls back to generic accrual interest. CMG is different:
its owner-cash lane uses OCF minus capex with no interest/tax adjustment, and a
separate current bridge must validate its debt-free scope. Missing interest is
not a universal instruction to switch models or assume debt is zero.
