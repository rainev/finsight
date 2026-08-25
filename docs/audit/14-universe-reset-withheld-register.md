# Universe reset cumulative withheld register

**Valuation date:** 2026-08-14

**Workflow:** process one batch -> report initial withheld companies -> attempt recovery once ->
append only companies still withheld -> stop before the next batch. A later revisit requires an
explicit user instruction and is recorded separately; it does not reset the automatic attempt.

| Batch | Ticker | CIK | Automatic attempts | Revision retries | Final blocker | Evidence |
| ---: | --- | --- | ---: | ---: | --- | --- |
| 01 | NEE | 0000753308 | 1 | 0 | Nonpositive bear/base mixed-utility FCFE after complete borrowing | `docs/audit/13-three-company-recovery-result.md` |
| 02 | OMC | 0000029989 | 1 | 1 | No comparable combined post-IPG cash-flow history | `docs/audit/31-batch-02-revised-pipeline-retry-result.md` |
| 02 | TTWO | 0000946581 | 1 | 1 | Nonpositive cash flow and unbounded release-pipeline conversion | `docs/audit/31-batch-02-revised-pipeline-retry-result.md` |
| 02 | CHTR | 0001091667 | 1 | 1 | Pending Cox/Liberty operating and claim state lacks pro forma cash evidence | `docs/audit/31-batch-02-revised-pipeline-retry-result.md` |
| 02 | CMCSA | 0001166691 | 1 | 1 | NBCUniversal/Sky standalone cash flows and capital allocation are unfiled | `docs/audit/31-batch-02-revised-pipeline-retry-result.md` |
| 02 | META | 0001326801 | 1 | 1 | Contractual commitments and uncommenced leases lack a non-overlapping cash waterfall | `docs/audit/31-batch-02-revised-pipeline-retry-result.md` |
| 02 | WBD | 0001437107 | 1 | 1 | Conditional merger payment is not intrinsic value; standalone/event states remain unbounded | `docs/audit/31-batch-02-revised-pipeline-retry-result.md` |

This register is cumulative. An entry receives no further automatic recovery attempt. The machine-readable source is
`backend/app/us_valuation/config/universe_reset_withheld.json`.
