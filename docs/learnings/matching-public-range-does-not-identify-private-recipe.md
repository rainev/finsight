---
name: matching-public-range-does-not-identify-private-recipe
description: Try retained private candidates and source inputs before declaring a migrated event model unrecoverable.
metadata: { type: gotcha }
---

The automated migration initially reported Charter's positive event-envelope base as unrecoverable. On 2026-09-08, a renewed inspection found the $22.55B transaction claim and 33.6M additional units in the retained `batch-02-conditional/verified-run-a` private packet. Recomputing the original bull DCF, deducting the fixed claim and adding the units to shares reproduces the frozen $50.648007926630015 base.

**Why:** Matching public ranges does not make private packets interchangeable. A later packet may omit earlier economic inputs; current source code can also represent a revised model rather than the frozen historical release.

**How to detect / apply:** Inspect all range-matching private candidates and distinguish source inputs from cached calculated outputs. An executable recipe must rerun the DCF and its locked overlay, not capitalize a cached equity output as earnings. Retained migration inputs establish replay, not fresh verification of announced transaction terms. This supersedes the earlier claim that Charter's overlay inputs were absent; no historical public value was changed.
