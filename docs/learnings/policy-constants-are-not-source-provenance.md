---
name: policy-constants-are-not-source-provenance
description: A numerically correct bridge constant is not evidence until the exact filing fact, period, unit, and treatment are attached.
metadata: { type: gotcha }
---

Do not treat a hard-coded cash, debt, NCI, lease, or share value as source evidence merely because
the arithmetic reproduces. The private ledger must retain the exact filing fact, accession, period,
unit, and whether a missing claim is reported, explicit zero, unresolved, or covered by a governed
range.

**Why:** Batch 04 candidate-a reproduced every valuation but traced only total assets. Its cash,
debt, NCI, and share bridge values were policy constants, so a reviewer could not distinguish
reported facts from assumptions. Six issuers also mislabeled unresolved NCI as reported zero.

**How to detect / apply:** Require fact-level bridge sources and one reconciliation record before
approving arithmetic. For unresolved claims, store `reported_nci: null`, an explicit unresolved
status, and the estimated reserve range. Related: [[specialist-facts-require-filed-lineage]],
[[input-range-zero-endpoint-is-not-zero-substitution]], and [[financing-claims-reconcile-to-statement-totals]].

