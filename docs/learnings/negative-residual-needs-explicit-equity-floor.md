---
name: negative-residual-needs-explicit-equity-floor
description: Never silently clamp negative residual equity; an explicit bear-only limited-liability rule must retain the raw value.
metadata: { type: gotcha }
---
Do not apply `max(0, value)` across valuation scenarios. A negative residual may become a public zero
only when it is the bear scenario, base and bull remain positive, the common-equity limited-liability
floor is explicitly disclosed, and the negative raw residual remains private evidence. A nonpositive
base remains unavailable unless a separately governed equity-at-risk contract is approved.

**Why:** The first PSKY launch-first candidate turned negative bear/base residuals into an artificial
0/0/positive range and an arbitrary 100% width. The corrected policy keeps PSKY unavailable, retains
the rejected recovery replay privately, and uses the zero floor only for bear cases such as LYV/TKO.

**How to detect / apply:** Search scenario builders for unconditional clipping, verify raw residuals,
and require a test that the floor is bear-only and the base remains positive.
