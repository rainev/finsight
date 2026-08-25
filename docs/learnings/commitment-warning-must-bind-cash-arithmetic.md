---
name: commitment-warning-must-bind-cash-arithmetic
description: A valuation cannot claim a commitment is captured unless the amount changes or explicitly reconciles to scenario cash arithmetic.
metadata: { type: gotcha }
---
A warning or source check does not prove a purchase, rights, or contractual commitment is modeled.
The governed amount must either change scenario cash/reinvestment or reconcile through an explicit
non-overlap calculation showing why reported capex/cash flow already covers it.

**Why:** The first launch-first GOOGL and FOXA candidates source-checked large commitments but their
values did not depend on those amounts. The corrected routes bind GOOGL's $707bn commitment to
5/8/12-year reinvestment tests and FOXA's contractual, other, and program-rights amounts to explicit
scenario reserves.

**How to detect / apply:** Trace each load-bearing commitment from source ledger to one formula input,
then perturb it and confirm the affected scenario moves. If it does not move, document and test the
non-overlap reconciliation; warning text alone is not evidence.
