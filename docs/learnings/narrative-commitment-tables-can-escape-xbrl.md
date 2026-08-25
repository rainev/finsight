---
name: narrative-commitment-tables-can-escape-xbrl
description: A complete structural-XBRL parse can still miss material commitment schedules disclosed only in filing HTML tables.
metadata: { type: gotcha }
---

Do not certify “no material commitment schedule” from an empty structural-XBRL search alone.
Trade Desk's Batch 03 controlling filing had no matching structural commitment facts, but Note 11's
HTML table reported $939.124m of operating-lease and other contractual commitments.

**Why:** A false absence proof can make a bear cash state look adequately funded and promote a
valuation that ignores material forward cash obligations.

**How to detect / apply:** Before emitting `absence_proven` for commitments, search the controlling
filing's narrative and tables, retain the primary-document hash and exact table values, and test
that the bear cash reduction covers a governed first-year burden. Keep operating commitments in
cash-flow scenarios rather than subtracting them again as bridge debt. Related:
[[operating-commitments-need-forward-cash-coverage]], [[dated-table-cell-is-not-enough]], and
[[evidence-exhaustion-needs-declared-tiers]].

