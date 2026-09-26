---
name: pse-historical-batch-tests-follow-active-successors
description: After a local PSE batch activation, historical candidate builders and active API tests may fail only because their expected active version stops at the prior batch.
metadata: { type: gotcha }
---
Historical `scripts/build_pse_v2_phase_b_batch_*.py` builders snapshot the current active pointer even when reproducing a much older candidate. After activating Batch 11, the full backend suite first showed 25 failures because Batch 2–10 builders accepted successor catalogs only through Batch 10 and the active API test still expected 108 entries. The same trap recurred at Batch 14: an initial 32 failures reflected stale Batch 13 successor guards, a 138-entry active-list expectation, and Batch 14's own builder still requiring Batch 13 to be active. The archived parent manifest hashes and candidate economics were unchanged; after updating guards and active-list expectations, all 385 backend tests passed.

**Why:** These are explicit release guards, not valuation regressions. Each new local activation advances the active pointer while historical reproducibility tests continue to run against the current checkout.

**How to detect / apply:** Check the active pointer and the first failure before altering valuation models. Add the newly confirmed active version to historical builders' allowed-successor lists, including the newly activated batch's own deterministic builder; retain its pinned parent manifest separately from the current active manifest. Update active-list counts and active-version assertions, keep all pinned parent hashes unchanged, and rerun the full backend suite. Run broad API sweeps and browser UAT sequentially so they do not consume the same local rate-limit window.
