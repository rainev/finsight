---
name: narrative-input-root-is-not-implementation-root
description: Frozen verification code must receive the validated narrative input root explicitly rather than deriving it from its own checkout location.
metadata: { type: gotcha }
---

WG25's shared source ledger initially derived its narrative root from `__file__`.
That worked in the live worktree, but frozen workers run from an isolated copied
implementation while their hashed source inputs remain under a different root.
The resulting generic source/economic-review status concealed a mechanical
"manifest outside allowed source root" lookup failure.

Pass the validated acquisition/verification source root into nested readers,
retain allowed-root and document/hash/package checks, and inspect exact failure
reasons. A review count alone cannot prove the intended financial check fired.
Current real frozen INTC/JBL workers and the subprocess regression exercise the
correct handoff. See `docs/audit/wg25-lease-capital-payment-overlap.md`.
