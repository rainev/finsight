---
name: immutable-replays-need-single-writer-lock
description: Immutable output checks do not prevent two long replay writers from racing.
metadata: { type: gotcha }
---
An offline Arelle replay can continue after the command interface yields. Retrying against the same output before the first process finishes creates concurrent writers; immutable replacement prevents corruption but the second writer may waste work or compute a byte-different operational status.

**Why:** Immutability protects the final file, not ownership of the generation process. Cache-hit and fresh-parse paths must also serialize to the same canonical status.

**How to detect / apply:** Treat a partial parsed tree without a final receipt as possibly active. Use an atomic single-writer lock for each output root, normalize cache/fresh execution to identical receipt fields, and return an existing matching receipt without reparsing. Never remove a lock until verifying no writer is active. See [[build-deploy-gotchas]].
