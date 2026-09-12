# Controlled Universe Reset Batch 40 Result

Date: 2026-09-07
Status: verified initial result; user confirmation recorded.

## Exact outcomes

Exactly ten frozen issuers were processed at valuation date 2026-08-14.
Pass **0/10**, Conditional **9/10**, Withheld **1/10**, numeric **9/10**.
All numeric results are capped at Low reliability.

| Ticker | Outcome | Bear | Base | Bull |
| --- | --- | ---: | ---: | ---: |
| MSCI | Conditional | $130.07 | $265.46 | $404.38 |
| XYZ | Conditional | $20.74 | $33.16 | $44.00 |
| ICE | Conditional | $38.95 | $85.92 | $134.26 |
| SYF | Conditional | $31.31 | $51.08 | $71.28 |
| PYPL | Conditional | $16.43 | $27.17 | $38.42 |
| COIN | Withheld | — | — | — |
| HOOD | Conditional | $7.16 | $11.98 | $17.08 |
| TPL | Conditional | $11.21 | $56.41 | $154.75 |
| APO | Conditional | $21.60 | $36.50 | $52.27 |
| BLK | Conditional | $279.99 | $464.46 | $631.38 |

## Model and source decisions

- MSCI uses data/subscription enterprise FCFF with TTM PP&E and capitalized software deducted. The pending First Street
  $120M cash price is charged across scenarios; its contingent earnout remains outside the range, keeping reliability Low.
- XYZ, SYF, PYPL, HOOD, APO and BLK use parent/common-equity residual income. Customer funds, deposits, client assets,
  crypto, loan books, securities financing, AUM, insurance assets and sponsored funds remain inside equity economics and
  are never treated as free issuer cash or ordinary EV debt.
- XYZ's volatile OCF is not used as unrestricted company cash because it includes customer-fund, settlement and lending
  movements. Current parent common equity/earnings provide the bounded fallback.
- SYF subtracts the reported $1.716B preferred claim once. Its $500M preferred issue is already in the controlling
  balance sheet and is not overlaid again; deposits, receivables, credit costs and regulatory capital remain inside equity.
- PYPL rejects the generic Companyfacts TTM ending 2026-03-31. The controlling filing's exact H1 figures reconstruct
  current cash diagnostics: revenue $34.128B, OCF $7.475B, capex $889M and interest $461M. The published route is equity
  residual income because payment-float and lending cash flows are not unrestricted FCFF.
- HOOD uses $9.480B parent equity derived from $9.541B consolidated equity less $61M NCI. Current Class A/B shares are
  combined once. Customer deposits, crypto assets, securities borrowing/lending and clearing collateral remain excluded.
- ICE uses exchange/data enterprise FCFF with PP&E and software reinvestment deducted. Matched $114.599B margin and
  guaranty-fund assets/liabilities are excluded. The pending ~$6B MarketAxess acquisition and financing remain outside the
  current-company range; the offered notes settle after the valuation cutoff.
- TPL uses land/royalty/water resource-cycle FCFF. Fixed assets, real estate and royalty-interest acquisitions are
  deducted. It has no drawn debt; commodity, production, water, land-sale and project cycles remain material, and no
  unreported Project Kilby/desalination value is added.
- APO subtracts its $1.398B preferred claim once and uses parent common earnings/equity. Athene/policyholder assets,
  consolidated VIEs and AUM are not parent cash; FRE/SRE, performance fees, insurance marks and active legal matters remain.
- BLK aligns diluted common earnings with fully diluted shares and exchangeable Subco unit equity once. AUM, sponsored
  products, securities collateral, HPS effects, performance fees, securities lending and legal matters remain outside cash.
- COIN remains withheld. TTM common earnings are −$987.766M and the earnings history is sharply discontinuous. Its
  $4.29919B client custodial funds exactly match custodial cash liabilities and are not issuer cash. A publishable value
  requires a positive through-cycle base and a specialist custody/stablecoin/crypto-financing reconciliation.

## Challenge and verification

Luna xhigh reviewed MSCI/XYZ/ICE/PYPL; Luna high separately reviewed SYF/COIN/HOOD and TPL/APO/BLK. Sol reconciled
source identities, exact periods, formula direction, private/public boundaries and calculator behavior.

The main repairs were the PYPL structural H1 TTM fallback, MSCI/ICE software reinvestment, ICE clearing-collateral
exclusion, HOOD parent-NCI attribution, BLK fully diluted Subco alignment, and TPL three-part reinvestment lineage.
No Critical or Important finding remains. A Minor semantic note remains: MSCI/ICE current-company bridges are complete
while material pending transactions stay outside the range; their public Conditional warnings state this explicitly.

- Final deterministic candidates: `output/batch-40-history-run-f-20260907` and
  `output/batch-40-history-run-g-20260907`; all 21 files are byte-identical.
- Report SHA-256: `f72e89d8c573f174607104039d40bada523ece6ae380acf0df0b04e9d52bd7e6`.
- Focused Batch 40 and calculator tests: **15 passed**.
- Complete backend regression: **1,660 passed, 3 skipped, 1 warning** (247.04 seconds). The warning is the existing
  Python `crypt` deprecation in passlib.
- Frontend production build: passed, 1,694 modules. No UI behavior changed in this batch.
- Isolated catalog: 400 companies — 116 available / 271 conditional / 13 unavailable; 387 review-required / 13 withheld.
- Catalog tree SHA-256: `90abae9b22af09537f82d67d5559b0cc102d23490d6116356afb5edc260e9a63`.
- Catalog manifest SHA-256: `10b07365ee71728c78ffa01ec5e885e5f8d3df30f74a49e7edadb4cd0e06e43f`.
- Real API: 400 list entries, 400 detail/calculator GETs, 400 expected calculator outcomes, exact list/detail parity,
  zero private leaks, and zero forbidden serving imports.
- API receipt SHA-256: `742de0fd6d346d1535df228fc7492aa156d4d28c034d1955eed08521615fa763`.
- Exact API/import receipt SHA-256: `2b62cb612959289570e79c0802cb2d1232240b065f535700bb9cfb3ff3b5543a`.

## Confirmation boundary

The user confirmed the exact initial Batch 40 result. The confirmed controlled universe is therefore 400 companies:
116 Pass / 271 Conditional / 13 Withheld. COIN's authorized one-time recovery is recorded separately in Audit 146.

The Recovery Learning Watchlist now has 283 entries (271 Conditional / 12 Withheld); the cumulative withheld register
remains 22 entries because COIN had not yet completed its one recovery attempt at this checkpoint. Tracked serving
artifacts remained unchanged. Recovery is handled separately; merge, push and deployment were not performed here.
Watchlist SHA-256: `dbdc0e45fbe0c2d9821528d6d3c81d16df18e038e2cc0006acbf49dc09f08e55`.
Withheld-register SHA-256 remains `3f5f1ade1e95013dccce0036bbb566c3b781cd03bdb3b0e9d08431cd3fb68d2a`.
