# Batch 14 Conditional-to-Pass Repair Gap

Status: **firsthand audited; two practical-materiality repairs identified, implemented, and
user-confirmed in Audit 73**. The user authorized a
focused review of whether any of the nine confirmed Batch 14 Conditional companies could become a
normal Pass. This audit does not lower the Pass standard, use prices, add post-cutoff evidence, or
assume missing facts are zero.

## Reference

The governing practical policy distinguishes ordinary bounded uncertainty from a material
provisional dependency:

- missing perfect detail is not itself Conditional;
- a consolidated model is acceptable when it represents the recurring economic object;
- a named range is material when it exceeds FinSight's 5% impact threshold, changes the economic
  object, or determines whether value is positive;
- finite arithmetic is not alone a Pass release, but immaterial source-bounded sensitivity does not
  have to remain Conditional;
- no company is reclassified to improve a quota.

The confirmed starting result in Audit 71 is Pass 1 / Conditional 9 / Withheld 0. IDXX already
passes and is outside the nine-company repair denominator.

## Ours today

The nine reviewed companies are TECH, HCA, REGN, BIIB, VRTX, INCY, GILD, BSX, and MCK. Each has a
finite positive range and an explicit release condition.

First source/economic review applied a perfect-detail bar to HCA and REGN. The governing
materiality check corrected that interpretation:

- **HCA:** the entire $1.464B professional-liability reserve range is only about 1.9% of the
  source-bounded base common-equity object. The reserve is stable and remains explicitly ranged.
- **REGN:** acquired IPR&D, acquisition cash, and contingent consideration are each well below 1%
  of base common equity; collaboration revenue is recurring in comparative periods and is already
  represented in the consolidated cash history.

The other seven dependencies change the economic object or remain material regardless of
percentage precision.

## Reuse check

The repair can reuse the existing engine and evidence:

- `backend/app/us_valuation/batch_14_history.py`
- `scripts/run_batch_14_history.py`
- `backend/tests/test_batch_14_history.py`
- `output/batch-14-sec-source-packets-20260829/<TICKER>/`
- `output/batch-14-structural-sources-resume-20260829/<TICKER>/`
- `output/batch-14-history/final-a/generated/<TICKER>/valuation-private.json`

No new extractor, valuation model, forecast assumption, or public schema is needed. The narrow
repair is classification plus explicit private materiality evidence for HCA/REGN.

## Flow

For every Conditional issuer:

1. identify the named dependency and its maximum bounded impact;
2. compare that impact to base common-equity value using the existing 5% rule;
3. verify the economic object and history remain comparable;
4. require exact bridge/share/source completeness;
5. independently challenge the proposed reclassification;
6. retain all assumptions and warnings even when an immaterial dependency becomes an ordinary
   Pass sensitivity.

## What backs the repair

### HCA — candidate Pass

The controlling filing reports:

- `ProfessionalLiabilityRisks`: $1.464B at 2026-06-30 versus $1.466B at 2025-12-31;
- self-insured retained reserves: $1.892B versus $1.906B;
- insurance-subsidiary reserves: $104M versus $91M;
- expected next-12-month net claim payments: $573M, including $532M subject to self-insured
  retention;
- source-reconciled cash, debt, NCI, shares, and five comparable annual cash periods.

No-reserve base common equity is approximately $345.212/share × 220.616M shares = $76.159B.
Maximum reserve sensitivity is $1.464B / $76.159B = **1.92%**; the base half-reserve adjustment is
0.96%. Keep the 100%/50%/0% reserve range, but classify it as an immaterial source-bounded
sensitivity rather than a material provisional dependency.

### REGN — candidate Pass

The controlling filing and private bridge report:

- base common equity approximately $775.657/share × 104.877M shares = $81.349B;
- H1 collaboration revenue $4.355B versus $3.392B in prior H1;
- H1 acquired IPR&D $228.9M = **0.28%** of base equity;
- H1 intangible-acquisition cash $99.9M = **0.12%** of base equity;
- contingent consideration $67.2M = **0.08%** of base equity;
- complete cash/securities, debt/finance lease, dual-class shares, and NCI/preferred absence proof;
- five comparable annual consolidated cash periods, with current TTM cash margin below—not above—
  the historical base.

Collaboration is a recurring comparative component of the consolidated operating object. A missing
product-versus-collaboration cash allocation is not required for the consolidated FCFF route when
the actual aggregate history remains source-linked and conservative.

## Gap register

- **B14PR-01 · P0 · ✔ HCA repair candidate.** Existing code classifies a 1.92%-maximum bounded
  reserve sensitivity as material. Repair: add HCA to `PASS_TICKERS`; retain the claim range;
  record the impact ratio and stable reserve evidence; update warning/public bridge reason.
- **B14PR-02 · P0 · ✔ REGN repair candidate.** Existing code treats recurring collaboration and
  sub-1% IPR&D/claim impacts as a material specialist gap. Repair: add REGN to `PASS_TICKERS`;
  retain consolidated FCFF and $67.2M claim; bind comparative collaboration and materiality facts;
  update warning/public bridge reason.
- **B14PR-03 · P0 · ✔ TECH remains Conditional.** Pending merger and up-to-$1B Wilson Wolf event
  change the object. Release: merger and milestone outcomes.
- **B14PR-04 · P0 · ✔ BIIB remains Conditional.** Partial-period Apellis acquisition and new
  financing lack comparable combined cash history.
- **B14PR-05 · P0 · ✔ VRTX remains Conditional.** Pending Crinetics transaction and $4.5B financing
  commitment remain outside the June standalone object.
- **B14PR-06 · P0 · ✔ INCY remains Conditional.** Vega acquisition/contingent consideration and
  CMS/product normalization remain material.
- **B14PR-07 · P0 · ✔ GILD remains Conditional.** $11.318B acquisition cash, $12.15B IPR&D, and
  pipeline claims make current cash non-comparable.
- **B14PR-08 · P0 · ✔ BSX remains Conditional.** Penumbra integration, claims, NCI, and
  restructuring remain material.
- **B14PR-09 · P0 · ✔ MCK remains Conditional.** Opioid cash/reserve, NCI, acquisitions, and
  distributor working capital remain load-bearing.

## Independent lenses

- Luna High source lens: HCA and REGN supported as candidate Pass repairs under practical
  materiality; the other seven release conditions remain open.
- Luna xhigh economic lens: HCA maximum sensitivity 1.92%; REGN IPR&D/cash/claim impacts 0.28% /
  0.12% / 0.08%; both can remain consolidated source-bounded Pass ranges.
- Sol firsthand reconciliation: verified HCA filing text/facts, REGN comparative collaboration and
  IPR&D facts, private arithmetic, and the governing 5% threshold.

The initial perfect-detail conclusion was rejected after the quantified materiality pass. No
unresolved disagreement remains on the proposed two-company repair.

## Authorized implementation scope

Implement only HCA and REGN reclassification/materiality evidence, independently challenge the
exact candidate, replay twice, run focused/full/backend/frontend checks in proportion to the change,
exercise the cumulative real API, and present the before/after result. Do not alter the seven
remaining Conditional values, Batch 15, tracked serving catalog, merge, push, or deployment.
