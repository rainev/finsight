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
| 31 | ORCL | 0001341439 | 1 | 0 | Optimistic infrastructure replay still has a negative base before fully charging known untimed commitments | `docs/audit/118-batch-31-orcl-recovery-result.md` |
| 36 | VLO | 0001035002 | 1 | 0 | Port Arthur third-party and possible regulatory claims lack a finite cutoff-safe bound | `docs/audit/135-batch-36-vlo-recovery-result.md` |
| 38 | GPN | 0001123360 | 1 | 0 | Post-Worldpay cash generation remains negative against debt and claims; favorable bridge and quarterly proxy remain insufficient | `docs/audit/140-batch-38-gpn-cpay-recovery-result.md` |
| 40 | COIN | 0001679788 | 1 | 0 | History-backed bear remains negative and tax, legal, and regulatory loss ranges remain unbounded | `docs/audit/146-batch-40-coin-recovery-result.md` |
| 41 | IFF | 0000051253 | 1 | 0 | Continuing operating cash and reinvestment remain inseparable from discontinued disposal groups; parent-earnings history is negative at the median | `docs/audit/148-batch-41-recovery-result.md` |
| 41 | IP | 0000051434 | 1 | 0 | Parent earnings remain negative and continuing capex is incomplete after GCF while separation and mill actions remain unresolved | `docs/audit/148-batch-41-recovery-result.md` |
| 42 | EXE | 0000895126 | 1 | 0 | Three half-year windows cover only 18 months and cannot establish a combined-company gas cycle; Twin Eagle remains unclosed | `docs/audit/150-batch-42-exe-alb-recovery-result.md` |
| 42 | ALB | 0000915913 | 1 | 0 | Five-year median cash FCFF is negative and the post-Ketjen mandatory-convertible denominator remains unresolved | `docs/audit/150-batch-42-exe-alb-recovery-result.md` |
| 43 | DVN | 0001090012 | 1 | 0 | Coterra pro-forma earnings do not supply combined OCF, capex, interest or working-capital cash | `docs/audit/152-batch-43-recovery-result.md` |
| 43 | NEM | 0001164727 | 1 | 0 | NGM/Fourmile project values, assumed liabilities, final ownership and settlement economics remain unbounded | `docs/audit/152-batch-43-recovery-result.md` |
| 43 | LYB | 0001489393 | 1 | 0 | Continuing-company OCF, working-capital cash and capex remain inseparable after the European sale and refinery discontinuation | `docs/audit/152-batch-43-recovery-result.md` |
| 44 | BKR | 0001701605 | 1 | 0 | Chart total consideration, assumed claims, post-close cash/debt and combined OCF/capex remain unavailable | `docs/audit/154-batch-44-recovery-and-range-recalibration-result.md` |
| 47 | NRG | 0001013871 | 1 | 0 | Post-LS Power/CPower history and settled hedge/parent-project funding remain unreconciled | `docs/audit/159-batch-47-recovery-result.md` |
| 47 | VST | 0001692819 | 1 | 0 | Merchant hedge timing, preferred-adjusted earnings and nuclear/project obligations remain unnormalized | `docs/audit/159-batch-47-recovery-result.md` |
| 47 | CEG | 0001868275 | 1 | 0 | Post-Calpine history, merchant-nuclear adjustments and project/decommissioning economics remain unnormalized | `docs/audit/159-batch-47-recovery-result.md` |
| 48 | EQR | 0000906107 | 1 | 0 | Standalone guidance was withdrawn before the approved AVB merger; combined AFFO and final closing bridge were unavailable | `docs/audit/162-batch-48-recovery-result.md` |
| 49 | AVB | 0000915912 | 1 | 0 | Full-year guidance was suspended before the approved EQR merger; combined AFFO and final closing bridge were unavailable | `docs/audit/165-batch-49-avb-recovery-result.md` |

This register is cumulative. An entry receives no further automatic recovery attempt. The machine-readable source is
`backend/app/us_valuation/config/universe_reset_withheld.json`.

The six Batch 16 entries preserve their consumed automatic recovery outcome. The later, explicitly
authorized whole-batch repair in Audit 82 gives each a Conditional Low reported-operations baseline;
it does not erase or reset this historical register. Confirmed reset-state withholding is now twenty-six
companies, while this cumulative automatic-withheld history contains thirty-six entries.

Batch 46 initially withheld EIX, AES, PCG and SRE, but the user explicitly authorized transparent
Conditional Low publication after their recovery evidence and moderated ranges were reviewed. All
four recovered conditionally, so none was appended to this cumulative withheld register.
