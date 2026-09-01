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
| 08 | NCLH | 0001513761 | 1 | 0 | Negative cash conversion; newbuild funding, debt service, and dilution remain unbounded | `docs/audit/57-batch-08-recovery-result.md` |
| 11 | BG | 0001996862 | 1 | 0 | No comparable combined Viterra history or filed pro-forma cash flow; current cash is negative | `docs/audit/66-batch-11-recovery-result.md` |
| 12 | UHS | 0000352915 | 1 | 0 | No single post-Ireland/Provo/CMG/Talkspace operating and funding state | `docs/audit/69-batch-12-whole-recovery-result.md` |
| 15 | LH | 0000920148 | 1 | 0 | Ravgen royalties/interest and multiple class/ADA/derivative claim amounts remain unbounded | `docs/audit/76-batch-15-recovery-result.md` |
| 15 | ISRG | 0001035267 | 1 | 0 | Product-liability and antitrust excess-loss ranges and current insurance ceiling are undisclosed | `docs/audit/76-batch-15-recovery-result.md` |
| 15 | ALGN | 0001097149 | 1 | 0 | EU fine cap does not bound private antitrust, patent, follow-on, and indemnification exposure | `docs/audit/76-batch-15-recovery-result.md` |
| 16 | DXCM | 0001093557 | 1 | 0 | Securities, derivative, and device-class damages lack a reserve, range, or insurance ceiling | `docs/audit/80-batch-16-recovery-result.md` |
| 16 | EW | 0001099800 | 1 | 0 | Finite reserves do not bound PASCAL, Valtech, appeal, and tax exposure | `docs/audit/80-batch-16-recovery-result.md` |
| 16 | CRL | 0001100682 | 1 | 0 | Revived securities and derivative claims lack a maximum, reserve, settlement, or insurance ceiling | `docs/audit/80-batch-16-recovery-result.md` |
| 16 | ZBH | 0001136869 | 1 | 0 | China distributor excess claims and IRS/foreign-tax adjustments remain unranged | `docs/audit/80-batch-16-recovery-result.md` |
| 16 | COR | 0001140859 | 1 | 0 | The settled-opioid schedule does not cap claims, penalties, verdicts, and injunctions outside it | `docs/audit/80-batch-16-recovery-result.md` |
| 16 | ELV | 0001156039 | 1 | 0 | Bounded CMS administration does not cap the separate DOJ FCA and provider follow-on cases | `docs/audit/80-batch-16-recovery-result.md` |

This register is cumulative. An entry receives no further automatic recovery attempt. The machine-readable source is
`backend/app/us_valuation/config/universe_reset_withheld.json`.

The six Batch 16 entries preserve their consumed automatic recovery outcome. The later, explicitly
authorized whole-batch repair in Audit 82 gives each a Conditional Low reported-operations baseline;
it does not erase or reset this historical register. Current public withholding is therefore nine
companies, while this cumulative automatic-withheld history remains nineteen.
