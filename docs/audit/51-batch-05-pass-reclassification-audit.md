# Batch 05 Pass reclassification audit

**Reference:** A normal Pass permits ordinary growth, margin, inventory, working-capital, and
discount-rate estimation when source facts and the economic model are bounded. Conditional is
reserved for a named material dependency that remains load-bearing. Withheld means no defensible
baseline can be produced without excessive invention.

**Scope:** read-only review of Batch 05 candidate-g, cutoff-safe source packets, structural filing
evidence, the launch-first model, and Audit 47. No values, classifications, watchlist entries,
serving artifacts, or later batches were changed.

## Reconciled outcome

| Ticker | Current | Recommendation | Reason |
| --- | --- | --- | --- |
| WSM | Conditional | **Pass candidate** | Ordinary home-furnishing retail; TTM periods align. No debt instrument is reported, leases stay in OCF, and the bounded claim reserve moves base value about 1.47%. |
| CASY | Conditional | **Pass candidate** | Food/fuel mix, acquisitions, LIFO, and working capital are ordinary business-cycle sensitivities. The debt-and-capital-lease aggregate is source-complete; reserve impact is about 0.82%. |
| CCL | Conditional | **Conditional** | Cruise recovery, ship capex, $25.57B debt, leases, and a zero bear equity floor remain load-bearing. |
| PHM | Conditional | **Conditional** | Homebuilder inventory, land options, mortgage earnings, and $1.82B notes payable remain material inside the consolidated equity-earnings route. |
| SBUX | Conditional | **Conditional** | Store turnaround, large operating leases, negative equity, inventory, and margin recovery materially determine value. |
| AZO | Conditional | **Pass candidate** | Ordinary auto-parts retail. Cash/securities and $9.058B debt are sourced; the $82.161M finance-lease bound is applied once; total accounting impact is about 0.86%. |
| DHI | Conditional | **Conditional** | $26.69B real-estate inventory, $3.1B mortgage loans, $7.11B notes payable, NCI, and mortgage banking remain load-bearing. |
| RCL | Conditional | **Conditional** | Cruise capex nearly consumes operating cash; $23.407B debt, leases, NCI, and recovery assumptions materially drive the range and zero bear floor. |
| ORLY | Conditional | **Pass candidate** | Ordinary auto-parts retail with aligned TTM sources, $7.015B noncurrent debt, operating leases inside OCF, and a 0.56% base reserve impact. |
| NVR | Conditional | **Conditional** | Lot-option deposits/loss reserves and mortgage banking remain material to the consolidated equity-earnings object. |

## Exact counts

**Current verified candidate-g:**

- Pass: **0/10**
- Conditional: **10/10**
- Withheld: **0/10**

**Credible after bounded reclassification:**

- Pass: **4/10** — WSM, CASY, AZO, ORLY
- Conditional: **6/10** — CCL, PHM, SBUX, DHI, RCL, NVR
- Withheld: **0/10**

These recommendations were implemented with the revised historical layer in Audit 53.

## Gap register

- **P1 ✔ forced Conditional routing:** Batch 05 rejects the primary route for every issuer even
  when the model is ordinary and source-bounded. WSM, CASY, AZO, and ORLY should enter the normal
  available route after their claim-reserve semantics are labeled non-material.
- **P1 ✔ absent-debt wording:** WSM has no reported debt instrument and ORLY has no current-debt
  fact. Their bridge must say source-proven absence or not reported; it must not call either a
  reported zero.
- **P1 ✔ specialist dependencies:** CCL/RCL cruise recovery, PHM/DHI/NVR mortgage/homebuilder
  structures, and SBUX turnaround economics remain material rather than ordinary forecast noise.
- **P2 ✔ small bounded reserves:** the Pass candidates' base accounting impacts are 1.47% (WSM),
  0.82% (CASY), 0.86% (AZO), and 0.56% (ORLY). These are not load-bearing dependencies under the
  corrected outcome rule.

## Evidence

- Frozen sources: `output/batch-05-sec-source-packets-20260825/<TICKER>/`
- Structural facts: `output/batch-05-structural-sources-20260825/<TICKER>/`
- Candidate artifacts: `output/batch-05-launch-first/candidate-g/generated/<TICKER>/valuation-private.json`
- Implementation: `backend/app/us_valuation/batch_05_launch_first.py`
- Original result: `docs/audit/47-controlled-batch-05-result.md`

Independent lenses: Luna-High source/lineage audit and Luna-XHigh economic-model audit. Sol
rechecked source-period alignment, debt/lease scopes, and reserve materiality. User authorization
is required before implementing the reclassification or changing the watchlist.
