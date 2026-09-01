# Batch 16 Withheld Recovery Gap

Status: **firsthand audit complete; recovery implementation authorized by the user**. Scope is
exactly DXCM, EW, CRL, ZBH, COR, and ELV from the user-confirmed Batch 16 initial result. This audit
does not change a value, register, serving artifact, or recovery-attempt count.

## Reference and release rule

The practical bounded-uncertainty policy permits a conservative Low baseline only when the complete
material current claim set has a finite, source-supported treatment. One reserve, statutory cap, or
settlement does not release an issuer when separate current claims remain unbounded.

Cutoff sources checked firsthand:

- Batch 16 initial evidence: [Audit 78](78-controlled-batch-16-result.md)
- DXCM 10-Q `0001093557-26-000143`, filed 2026-07-30
- EW 10-Q `0001099800-26-000043`, filed 2026-08-04
- CRL 10-Q `0001100682-26-000118`, filed 2026-08-05
- ZBH 10-Q `0001193125-26-335044`, filed 2026-08-05
- COR 10-Q `0001140859-26-000034`, filed 2026-08-05
- ELV 10-Q `0001156039-26-000060`, filed 2026-07-15
- official court/DOJ materials for the CRL appeal and ELV Medicare risk-adjustment complaint

## Current recovery evidence

### DXCM

✔ Securities, derivative, and six G6/G7 consumer class-action groups seek damages, restitution,
disgorgement, injunctions, fees, and costs. The filing says it cannot reasonably estimate the
ultimate outcome of any matter. No damages accrual, cap, current insurance limit, or insurance
receivable is disclosed. The $33.5M professional-fee accrual is not a damages reserve.

### EW

✔ Finite pieces exist: $56.9M litigation reserve, a $72.4M combined litigation/insurance reserve,
an immaterial Patel settlement already recorded, and historical Valtech terms with up to $350M of
milestones. The remaining Valtech milestone balance is not filed and the two reserve aggregates
cannot be added safely.

✔ PASCAL patent damages/injunction, Valtech accelerated milestones/ancillary relief, securities and
derivative appeals, and tax exposure beyond recorded positions have no finite total range. The
filing expressly says unaccrued/additional loss cannot be estimated.

### CRL

✔ The First Circuit returned part of the securities-fraud case to district court and two derivative
actions remain stayed. The filing states that neither maximum exposure nor possible-loss range can
be estimated. No damages reserve, settlement, or current D&O insurance ceiling is disclosed.

### ZBH

✔ The $137.9M litigation estimate and acquisition/contingent-consideration ranges are finite.
However, China distributor lawsuits and possible additional claims can exceed accruals and have no
possible-loss range. IRS and foreign tax disputes may also require material payments without a
current proposed-adjustment/excess range.

### COR

✔ The opioid schedule is finite for settled matters: approximately $4.2B total liability, including
$396.2M current and the rest paid over approximately 13 years.

✔ The filing cannot estimate losses for opioid/controlled-substance matters outside the accrual and
states ultimate loss can differ materially. Additional civil penalties, private verdicts, and
injunctive relief therefore remain outside the finite settlement schedule.

### ELV

✔ The CMS administrative notice is closed and financially bounded: $935M original accrual, $342M
payment, $593M remaining, with a disclosed ±$320M adjustment range.

✔ The separate DOJ False Claims Act lawsuit alleges unspecified Medicare risk-adjustment payments;
discovery remains underway and outcome cannot be determined. The finite CMS administrative range
does not cap DOJ treble damages/penalties or separate provider follow-on cases.

## Gap register

| ID | Severity | Finding | Evidence status | Recovery decision |
| --- | --- | --- | --- | --- |
| B16R-01 | P0 | DXCM total securities/device class exposure lacks reserve, insurance ceiling, or range | ✔ current SEC evidence | Keep Withheld |
| B16R-02 | P0 | EW finite reserve/milestone pieces do not bound patent, appeal, and tax exposure | ✔ SEC + acquisition terms | Keep Withheld |
| B16R-03 | P0 | CRL securities/derivative maximum and insurance recovery are undisclosed | ✔ SEC + court opinion | Keep Withheld |
| B16R-04 | P0 | ZBH China claims and tax-audit excess exposure remain unbounded | ✔ current SEC evidence | Keep Withheld |
| B16R-05 | P0 | COR settled-opioid schedule excludes unranged current claims/penalties | ✔ current SEC evidence | Keep Withheld |
| B16R-06 | P0 | ELV bounded CMS notice is separate from an unbounded DOJ/provider claim set | ✔ SEC + DOJ evidence | Keep Withheld |
| B16R-07 | P0 | Recovery evidence, deterministic replay, challenge, API, and post-attempt bookkeeping are not recorded | ✔ repository audit | Build/verify |

## Reuse and bounded plan

Reuse the confirmed Batch 16 withheld public artifacts, current structural wrappers, public
sanitizer, catalog builder, and API verifier. Implement source-exhaustion evidence only; do not
invent lawsuit probability, stock-drop damages, punitive-damage factors, insurance recoveries, or
competitor/market-price anchors.

The evidence-supported recovery target is **0/6** unless the final independent challenge identifies
new cutoff-safe primary evidence. Success means recording honest exhaustion, not forcing a value.
