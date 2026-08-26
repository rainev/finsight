---
name: serving-root-guards-follow-active-catalog
description: Every replay and capture guard must protect the manifest-controlled catalog root, not a retired loose artifact directory.
metadata: { type: gotcha }
---
When the U.S. valuation API moved from `backend/app/data/us_valuations` to
`backend/app/data/us_valuation_catalogs`, several offline replay CLIs still resolved the retired
directory before running. Removing that directory caused otherwise unrelated shadow runs to fail
their path-identity check with `FileNotFoundError`.

**Why:** serving-root protection is intentionally duplicated across ingestion, replay, and batch
scripts so none can write into public data. A catalog migration must update every one of those
guards; changing only the API loader leaves the safety tooling stale.

**How to detect / apply:** search scripts and tests for every prior serving-root literal whenever
the active catalog location changes. Protect the whole catalog root—including `active.json`,
versioned catalogs, and archives—then rerun the path-alias/symlink tests and the full backend suite.
Related: [[immutable-replays-need-single-writer-lock]] and [[project-profile]].
