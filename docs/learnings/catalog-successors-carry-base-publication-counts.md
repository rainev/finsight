---
name: catalog-successors-carry-base-publication-counts
description: A successor valuation catalog must accumulate publication states from its base catalog, not count only the appended batch.
metadata: { type: gotcha }
---
When `build_us_valuation_catalog.py` extends an immutable base catalog, it must read each base
artifact's `review.publication_state` into the successor's publication counter before adding the
new batch. Copying only the base entries preserves availability counts but otherwise leaves the
successor manifest with new-batch-only publication counts.

**Why:** an apparently valid 110-company successor can report correct availability totals while
claiming only 10 publication outcomes, weakening cumulative verification and future promotion
evidence.

**How to detect / apply:** require successor builds to assert both cumulative availability and
publication counts. Regression-test a base-catalog extension and load the resulting immutable
catalog before any isolated activation. Related: [[serving-root-guards-follow-active-catalog]].
