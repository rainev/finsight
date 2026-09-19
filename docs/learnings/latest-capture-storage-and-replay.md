---
name: latest-capture-storage-and-replay
description: Large annual SEC captures need bounded storage and parser limits; replay counts do not establish freshness.
metadata: { type: gotcha }
---

The September 19 latest-500 capture encountered only about 14 GiB free disk.
Repeated structural JSON in receipts and parser caches consumed far more space
than original filing bytes. New capture receipts use deterministic gzip and
validate decompressed packet hashes; old plain receipts remain readable.
Do not delete historical evidence to make room or launch unbounded queued work.
After all changed regular filings are captured, do not continue duplicating full
structural packages merely to re-prove unchanged approved evidence. Use the
source index, original artifact/recipe hashes, final submissions metadata and
event-specific lightweight evidence; otherwise an all-500 recapture can exhaust
disk while adding no financial information.

An SEC index can list an unavailable XBRL ZIP while individual resources remain
retrievable (HON annual capture). Transport-only fallback is safe only while
dependency closure and corrupt/unsafe archive failures remain strict.
AEP's combined annual primary is 18,321,402 bytes, above the old 16 MiB limit;
the bounded 32 MiB limit admits it, but its parser still timed out at 300 seconds.
Downloaded source, parsed source, exact recipe replay and economic update are
four different checkpoints. Never substitute one for another.
