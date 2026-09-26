---
name: pse-evidence-replay-verification-needs-fresh-process
description: PSE evidence loaders close the shared psycopg pool, so run the persistence verifier in a fresh Python process after replay.
metadata: { type: gotcha }
---
During Batch 17, the idempotent evidence loader succeeded, but running the verifier with `runpy` in the same Python interpreter raised `psycopg_pool.PoolClosed` when it tried `pool.open()`. Running the verifier as a new Python process read back the unchanged receipts, 15 facts, 30 assumptions and 10 runs successfully.

**Why:** `app.db.pool` is a module-level connection pool, and the loader's `finally` block closes it. A closed psycopg pool cannot be reopened in that interpreter.

**How to detect / apply:** If a same-process loader→verifier sequence raises `PoolClosed`, do not treat it as lost evidence or recreate the data. Run the loader and verifier as separate commands/processes, then compare Postgres and MinIO counts and hashes.
