---
name: transaction-price-is-not-a-post-event-cash-state
description: A completed acquisition price cannot update intrinsic value without source-bound post-event cash, debt, shares and operating scope.
metadata: { type: gotcha }
---
MRK's 10-Q reports the $650M TARGAN acquisition as a subsequent event, but no
separate event receipt or post-event balance rollforward is captured.

**Why:** Subtracting the transaction price from the June bridge would look like a
cash update while carrying June debt, shares and operating scope forward.

**How to detect / apply:** Keep the transaction as context until cash, financing,
shares and acquired operating scope reconcile together. Never use consideration
as intrinsic value or a standalone bridge deduction. Purchase price minus the
disclosed acquisition loans is only an arithmetic funding gap: unless the
filing identifies its actual source and post-close treatment, it is not a
reported liability, a cash balance, or permission to carry the difference in a
legacy preferred-equity slot.

ECL demonstrates the narrow supported exception: financing and acquisition
cash were already visible in the period-end balance sheet, the later close and
operating scope were captured in the same hashed filing, and a cost-based range
was explicitly labeled as an event proxy while purchase accounting and acquired
FCFF remained unavailable. PH demonstrates the fail-closed case: the closing
8-K proves the price and two loan draws but describes them as funding only a
portion of price and fees, so the residual and post-close state remain review.

A pending fixed price may remain a clearly labeled private scenario sensitivity,
but it is not a current carrying liability. Add any separately reported current
contingent-consideration liability in every scenario, exclude cash already paid,
and never use the pending sensitivity as evidence that closing occurred.

WG32 adds a pre-close minority-investment variant. MCK's official announcement
describes approximately $13B MMS transaction enterprise valuation alongside a
$1.25B preferred investment/approximately13% subsidiary interest. Enterprise
transaction value is not MCK intrinsic value, MMS common-equity value, current
redemption claim, conversion ratio or parent dilution. Preserve it as dated
event evidence only; never use it without complete capital structure/contract scope.
