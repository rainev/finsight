---
name: recovery-gates-pin-confirmed-inputs-and-source-bytes
description: A recovery run must pin the exact confirmed result and verify load-bearing cited source bytes.
metadata: { type: gotcha }
---
A recovery runner must require the exact confirmed report hash, denominator order, and outcome
counts. Any source fact that releases a company to Pass must be connected at runtime to the captured
receipt, package manifest, primary document, and cited document hash.

**Why:** Batch 34's first recovery runner accepted any similarly shaped report and inserted USB/BRO
source citations from constants without validating the cited HTML. The facts happened to be correct,
but execution did not prove them.

**How to detect / apply:** Fail closed on report-hash/order/count drift and source receipt/package/
primary-document hash drift. Test the failures, not just the successful path.
