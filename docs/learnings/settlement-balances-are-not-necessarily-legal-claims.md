---
name: settlement-balances-are-not-necessarily-legal-claims
description: Payment-network settlement assets and liabilities are operating working-capital balances, not litigation merely because they contain the word settlement.
metadata: { type: gotcha }
---
FIS reports settlement deposits and receivables that reconcile to its settlement
assets, with a related settlement liability and OCF movement. These are payment-
processing balances. Visa likewise reports operating settlement receivables and
payables separately from litigation accruals and escrow.

**Why:** A keyword classifier can misroute operating balances into the legal
claim bridge and double-count working capital already represented in cash flow.

**How to detect / apply:** Require presentation ancestry, matched component
reconciliation and OCF context. Keep operating settlement assets/liabilities out
of litigation arithmetic; use only an explicitly scoped legal accrual and its
same-matter recognized recovery.

This also applies to the work register: never classify a claim as litigation
from the word `settlement` alone. Require litigation/legal context or a typed
litigation source policy; otherwise keep the mechanism unclassified.
