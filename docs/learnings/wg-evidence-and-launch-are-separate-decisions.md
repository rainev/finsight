---
name: wg-evidence-and-launch-are-separate-decisions
description: Keep launch approval, captured calculation proof and future refresh certification distinct; preserve approved normalization choices during migration.
metadata: { type: gotcha }
---
The September 19 audit found that GILD/INCY refresh receipts reproduced their
calculations while reintroducing current TTM observations excluded by the approved
Batch14 history generator. Source binding and calculator parity did not detect
this economic policy difference. Future changes must compare normalization
exclusions and assumptions explicitly, as well as output arithmetic.

Global implementation hashes also stale prior company receipts. Two results on
the latest version do not mean only two companies have usable launch baselines.
The 440-company refresh register and 500-company staged launch catalog measure
different work. Track baseline approval, current replay and successive-filing
proof separately. A hash proves byte identity, not financial truth.

User direction: accept prior human approvals for the next 500-company sweep;
allow transparent Low/conditional baselines; focus exceptions on concrete
correctness problems. Autonomous-refresh completion is a separate milestone.

See `docs/audit/wg-truth-and-launch-handoff-20260919.md` for qualifications and
the deferred publication-sweep contract.
