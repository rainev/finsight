---
name: conditional-deal-consideration-is-not-intrinsic-value
description: A signed per-share merger payment can be shown as an event-state diagnostic but cannot substitute for intrinsic value while closing remains conditional.
metadata: { type: gotcha }
---
WBD's agreement specifies `$31.00` cash per share plus a daily ticking amount after 2026-09-30.
That arithmetic is source-fixed, but litigation, regulatory clearance, termination rights, and an
alternative separation path still determine whether shareholders receive it.

**Why:** Publishing contractual consideration as intrinsic value silently assumes closing and
collapses materially different issuer states into a fake certainty.

**How to detect / apply:** Label the amount `conditional transaction consideration`, keep it
private or on a separate event surface, never assign an invented close probability, and retain the
intrinsic result as withheld until standalone/event paths are finite. Stop or refresh the diagnostic
on closing, termination, amendment, or material court/agency action.
