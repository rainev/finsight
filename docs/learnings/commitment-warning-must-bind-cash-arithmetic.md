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

Batch 31's Oracle recovery added the complementary revenue-side trap. A `$638B` remaining-
performance-obligation balance supplies contracted revenue timing, not cash, margins, or proof that
`$260B` of uncommenced leases and rising capex will earn an adequate return. The recovery modeled
lease cohorts and post-year-ten residual payments explicitly, but even an optimistic replay that
excluded two known untimed cost buckets produced a negative base common-equity value.

**How to detect / apply:** Keep backlog/RPO on the revenue-evidence side and commitments on the cash-
burden side. Never add RPO to cash or use it alone to invent future cash margins. When commencement
and payment timing is only broadly bounded, label the cohort schedule as a FinSight assumption,
retain optimistic omissions, and withhold if the source-bounded base remains nonpositive.

Refresh migration trap verified 2026-09-08: historical enterprise recipes sometimes
store non-preferred reserves in the `preferred_equity` calculator input. ADP's
$475.7M is a $457.7M client-fund shortfall plus $18M net litigation claim, despite
reported preferred stock being zero. Replacing that input with a newly selected
preferred-stock tag would erase the reserve. The policy compiler now blocks
nonzero historical non-debt claims until their economic scope has an explicit
source rule. This is an implementation gate, not new company unavailability.
