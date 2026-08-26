# Batch 04 Pass reclassification audit

**Reference:** A normal **Pass** permits ordinary growth, margin, cycle, and discount-rate
estimation when the source facts and economic model are bounded. **Conditional** is reserved for a
named material dependency that remains load-bearing. **Withheld** means no defensible baseline can
be produced without excessive invention.

**Scope:** read-only review of the ten frozen Batch 04 source packets, controlling structural
filings, candidate-e private/public artifacts, valuation implementation, and Audit 46. No values,
watchlist entries, serving artifacts, or publication states were changed.

## Reconciled outcome

| Ticker | Current | Reclassification recommendation | Reason |
| --- | --- | --- | --- |
| F | Conditional | **Conditional** | Ford Credit funding/equity, warranty, pension, and captive-finance economics remain material; the model explicitly is not a Ford Credit SOTP. |
| GPC | Conditional | **Conditional** | A $2.017B supplier-finance movement, restructuring, acquisition/working-capital normalization, and a zero bear floor remain load-bearing. |
| HAS | Conditional | **Conditional** | $1.022B goodwill impairment, disposal history, restructuring, and entertainment/licensing transition make normalized cash provisional. |
| LOW | Conditional | **Conditional** | Recent acquisitions, housing-cycle normalization, and unresolved ownership claims remain material to the current run rate. |
| MCD | Conditional | **Pass candidate after bounded bridge fix** | Franchise/lease cash model is economically suitable and operating leases are not double-counted; resolve the NCI/equity-method bridge and remove the generic asset reserve. |
| TJX | Conditional | **Pass candidate after extraction fix** | Ordinary off-price economics, but candidate-e uses a 2018 revenue source. Correct TTM revenue to about $61.584B from FY $60.372B + current Q1 $14.323B − prior Q1 $13.111B, then resolve the small bridge reserve. |
| NKE | Conditional | **Conditional** | Deteriorated cash conversion plus China, FX, inventory, channel mix, and margin recovery are a genuine material transition. |
| HD | Conditional | **Pass candidate after bounded bridge fix** | Debt/commercial paper and the consolidated cash model are source-backed; housing-cycle forecasting is ordinary. Resolve post-SRS run-rate and NCI treatment. |
| ROST | Conditional | **Pass candidate after extraction fix** | Ordinary off-price economics, but candidate-e uses 2020 interest. Reconstruct current interest from the controlling filing and resolve the small bridge reserve. |
| MGM | Conditional | **Conditional** | Casino/JV/NCI/digital economics, large operating leases, negative digital EBITDA, and Osaka investment complexity remain specialist dependencies. |

## Exact counts

**Current verified artifacts:**

- Pass: **0/10**
- Conditional: **10/10**
- Withheld: **0/10**

**Credible result after the four bounded repairs above:**

- Pass: **4/10** — MCD, TJX, HD, ROST
- Conditional: **6/10** — F, GPC, HAS, LOW, NKE, MGM
- Withheld: **0/10**

These recommendations were user-approved and implemented in Audit 50.

## Gap register

- **P0 ✔ TJX current revenue extraction:** candidate-e sources revenue to 2018-05-05 while OCF
  and capex end 2026-05-02. The controlling filing provides the current/prior Q1 facts and the
  latest FY fact required for a $61.584B TTM reconstruction.
- **P1 ✔ ROST current interest extraction:** candidate-e sources interest to 2020-02-01. The
  controlling filing reports current long-term-debt and other-interest facts; the error is small
  but a Pass cannot retain stale provenance.
- **P1 ✔ MCD/HD bridge closure:** the generic 2%/1%/0% asset reserve has less than a 1% base-value
  effect, but a Pass should replace it with source-proven absence or an exact bounded claim.
- **P1 ✔ blanket reserve semantics:** GPC, HAS, and MGM already report NCI, yet the valuation code
  still adds a 2%/1%/0% asset reserve without a matching estimated source-ledger row. This does not
  overturn their Conditional status but must be corrected before any future Pass replay.
- **P1 ✔ material economic dependencies:** F, GPC, HAS, LOW, NKE, and MGM have named transition,
  acquisition, finance, or specialist dependencies that remain load-bearing rather than ordinary
  forecasting noise.

## Evidence

- Frozen sources: `output/batch-04-sec-source-packets-20260825/<TICKER>/`
- Structural facts: `output/batch-04-structural-sources-20260825/<TICKER>/`
- Candidate artifacts: `output/batch-04-launch-first/candidate-e/generated/<TICKER>/valuation-private.json`
- Implementation: `backend/app/us_valuation/batch_04_launch_first.py`
- Original result: `docs/audit/46-controlled-batch-04-result.md`

Independent lenses: Luna-High source/lineage audit and Luna-XHigh economic-model audit. Sol
rechecked the load-bearing period errors and reconciled the disagreement. User authorization is
required before implementing the four repairs or changing the watchlist.
