# WG35 independent HCA annual-cash challenge

Checked 2026-09-17 by `wg34_hca_prof_liability`, gpt-5.6-luna with high
reasoning, one bounded read-only reviewer reused for continuity. No edits or
network access. Primary verified every material source and judgment firsthand.

The reviewer initially challenged whether the complete annual rollforward made
the old reserve sensitivity a proven double count. On explicit re-review against
the retained source-ledger release condition, the reviewer concluded it did not:
annual paid claims prove recurring cash is in historical OCF, while HCA's
outstanding noncurrent reserve still lacks a current multi-year runoff schedule
or equivalent reconciliation to normalized forward OCF.

Final code/evidence review confirms exact 2024/2025 gross/current/noncurrent/net
reserve and reinsurance balances,550/600/702M historical net payments,573M
current next-year expectation, no inferred premium or beyond-year timing,
`claim_adjustment=None`, `numeric_successor_issued=false`, and unchanged
1464/732/0M sensitivity and values. Frozen annual receipt/report execute in the
two-worker flow. Annual3256M/current3433M ordinary NCI are separate from owner
flows and counted once; HCA remains implementation_gap.

Final NCI-delta focused: **22 passed in7.52s**, no material issue. Primary focused:
**22 passed in9.50s**. Final broad: **788 passed**, one existing Passlib crypt
deprecation warning, in348.79s. Current forward runoff and every separate company/
release blocker remain required.
