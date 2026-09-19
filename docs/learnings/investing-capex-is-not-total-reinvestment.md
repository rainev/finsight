---
name: investing-capex-is-not-total-reinvestment
description: Separately reported financing capital payments require cash/debt reconciliation before investing-only capex can be called total reinvestment.
metadata: { type: gotcha }
---

INTC's current filing reports PP&E payments in financing activities separately
from investing PP&E capex, plus finance-lease principal payments and extended-
term PP&E purchases. The retained investing-capex diagnostic is not thereby
complete sustainable cash flow.

Do not infer absent financing payments as zero, blindly deduct all financing
payments as capex, or deduct finance-lease principal while also deducting the
lease debt without reconciliation. Keep reported investing cash, financing cash
and debt separate; block sustainable-input validity until overlap is evidenced.
Approved post-total-reinvestment margins remain hypothetical assumptions, not
reported margins or a correction that makes missing reinvestment disappear.

Verified in WG24's hashed current INTC filing, source proof and fail-closed
calculation flow; see `docs/audit/wg24-governed-cash-margin-normalization.md`.

WG25 additionally bound the current MD&A description: financing capital cash
settles extended payment terms. The supplemental noncash amounts use duration
contexts, but that alone does NOT settle their economic stock-versus-flow or
ending-payable coverage. Keep the reported total and extended-term inclusion
separate, without treating the inclusion as an extra claim. Ending financing
liability and cash/debt overlap still need source proof; neither is supplied
by payment amounts or supplemental context shape alone.
