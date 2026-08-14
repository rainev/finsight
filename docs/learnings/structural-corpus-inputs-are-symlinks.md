---
name: structural-corpus-inputs-are-symlinks
description: Validate FinSight structural-XBRL corpus inputs with symlink-aware checks before declaring them absent.
metadata: { type: gotcha }
---
The staged files under `output/structural-xbrl-broad-corpus/input/` are symlinks to private `output/legacy-fcff-bridge-recovery/<TICKER>/valuation-private.json` artifacts. A check such as `find input -type f` does not count those symlinks and can falsely report an empty corpus.

**Why:** The broader-corpus runner deliberately reuses private recovery artifacts without copying them. Evidence validation must preserve and verify that lineage.

**How to detect / apply:** Inspect with `ls -la` and count readable targets with `find -L <input-dir> -maxdepth 1 -type f`. Verify every symlink target exists before replay or reconciliation. Do not treat a zero result from non-following `find -type f` as missing input.
