# Batch 15 Withheld Recovery Gap

Status: **firsthand audit complete; recovery implementation authorized by the user**. Scope is
exactly LH, ISRG, and ALGN from the user-confirmed Batch 15 initial result. This audit does not
change a value, register, serving artifact, or recovery-attempt count.

## Reference and release rule

The governing rule is the practical bounded-uncertainty policy in Audits 11–12 and the Batch 15
hard stops in Audit 74: publish a conservative baseline when a material uncertainty has a finite,
source-supported range; withhold when a current event or claim cannot be bounded without guessing.

Sources checked firsthand:

- Batch 15 initial evidence and private traces: [Audit 74](74-controlled-batch-15-result.md)
- LH controlling 10-Q: SEC accession `0000920148-26-000175`, filed 2026-08-05
- DOJ release dated 2026-07-15: `Labcorp Agrees to Pay $14.5M to Resolve False Claims Act
  Allegations`, release 26-783
- ISRG controlling 10-Q: SEC accession `0001035267-26-000058`, filed 2026-07-21, Note 8
- ALGN controlling 10-Q: SEC accession `0001097149-26-000060`, filed 2026-08-05, Notes 6–7
- EU Regulation 1/2003 Article 23 and the European Commission's June 30, 2026 Align investigation
  notice

All evidence predates or equals the 2026-08-14 valuation cutoff.

## Current recovery evidence

### LH — DOJ amount is closed, but total legal exposure is not

✔ The controlling 10-Q identifies the July 15 DOJ settlement but omits its amount. The official DOJ
release and agreement report **$14.5M** plus 4.5% annual interest beginning May 14, 2025 for the
same urine-drug-testing matter.

✔ Principal materiality is finite: `$14.5M / $8.607B reported stockholders' equity = 0.1685%`.
This closes only the DOJ subclaim.

✔ The same 10-Q also reports the Ravgen $272M verdict, $100M enhanced damages, $2.6M supplemental
damages, pre/post-judgment interest, and a $100 royalty per future test through the patent's life.
It gives no future test count or royalty-duration cash schedule. Separate AMCA and Meta Pixel class
settlements were signed subject to approval without disclosed amounts, reserves, or payment ranges.
The certified Davis/Vargas ADA class action seeks statutory damages and fees without a disclosed
range, and the stayed Raymond Eugenio derivative action also seeks damages without a filed range.

✔ The ordinary diagnostics-laboratory cash-FCFF route remains reusable, but these additional
described proceedings leave total claims materially unbounded. The filing's statement about remote,
immaterial “other” proceedings does not quantify these specifically described matters.

### ISRG — total current claim exposure remains unbounded

✔ Note 8 says product-liability losses may materially exceed current estimates/accruals and that the
possible excess loss or range cannot be estimated. It separately says loss ranges cannot be
estimated for the SIS appeal, the certified da Vinci antitrust class action, and the Restore appeal.

✔ Restricted cash associated with insurance programs and the current accrual establish that some
coverage/reserve exists, but neither supplies a coverage limit or an upper bound for the uncovered
exposure. Treating all other current liabilities as the maximum would not be a source-supported
claim estimate.

✔ The corrected $8.6255B aggregate cash/securities and debt-free owner-cash model remain reusable,
but the release condition is not satisfied.

### ALGN — one statutory cap does not bound all proceedings

✔ EU Regulation 1/2003 caps a Commission infringement fine at 10% of prior-year worldwide turnover.
That can bound the Commission fine alone.

✔ ALGN's filing also says the Straumann antitrust/unfair-competition counterclaims seek money
damages and that it cannot estimate their loss range. The EU investigation may additionally create
follow-on private litigation, which is not covered by the Commission's 10% administrative-fine cap.

✔ Current legal/VAT accruals, unused revolver capacity, and private-investment carrying value do not
create a valid upper bound for those separate claims. The owner-cash route remains reusable only
after total current claims are bounded.

## Gap register

| ID | Severity | Finding | Evidence status | Recovery decision |
| --- | --- | --- | --- | --- |
| B15R-01 | P0 | LH's DOJ subclaim is exactly bounded, but Ravgen royalties/interest and two class-settlement amounts remain unbounded | ✔ verified against DOJ + SEC | Keep Withheld |
| B15R-02 | P0 | LH needs an immutable DOJ receipt plus explicit total-claim source exhaustion; a $14.5M-only bridge would be incomplete | ✔ verified evidence delta | Build evidence only |
| B15R-03 | P0 | ISRG product-liability and antitrust loss ranges remain unestimable | ✔ verified in current 10-Q | Keep Withheld |
| B15R-04 | P0 | ALGN's EU fine is capped, but separate money-damage/follow-on claims remain unestimable | ✔ verified against SEC + EU law | Keep Withheld |
| B15R-05 | P0 | Final recovery output, challenge, deterministic replay, cumulative API, watchlist, and withheld register are not yet recorded | ✔ verified current repository state | Build/verify |

## Reuse check and bounded plan

Reuse the Batch 15 cash model, historical profile, public-artifact builder, source-capture immutability
helpers, catalog builder, and API harness. Do not create new ISRG/ALGN formulas, competitor proxies,
or market-price anchors.

The efficient recovery target is therefore **0/3** unless the independent challenge finds new
cutoff-safe primary evidence. Success does not require forcing any company numeric.
