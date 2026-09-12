# Controlled Universe Reset Batch 39 Result

Date: 2026-09-07
Status: verified initial result; user confirmation recorded.

## Exact outcomes

Exactly ten frozen issuers were processed at valuation date 2026-08-14.
Pass **0/10**, Conditional **10/10**, Withheld **0/10**, numeric **10/10**.
All numeric results are capped at Low reliability.

| Ticker | Outcome | Bear | Base | Bull |
| --- | --- | ---: | ---: | ---: |
| ARES | Conditional | $7.50 | $12.52 | $17.79 |
| RF | Conditional | $13.17 | $21.31 | $29.53 |
| CBOE | Conditional | $82.53 | $185.26 | $313.58 |
| IBKR | Conditional | $9.26 | $15.29 | $21.47 |
| TRGP | Conditional | $0.00 | $73.41 | $207.22 |
| BNY | Conditional | $43.78 | $68.85 | $96.64 |
| BX | Conditional | $8.52 | $14.09 | $19.91 |
| V | Conditional | $155.05 | $229.13 | $376.79 |
| KKR | Conditional | $21.55 | $35.49 | $49.99 |
| KMI | Conditional | $4.52 | $15.48 | $30.04 |

## Model and source decisions

- ARES/RF/IBKR/BNY/BX/KKR use five-year parent/common-equity residual income. Client AUM, deposits, custody assets,
  consolidated funds, insurance assets, repo and securities-financing balances stay inside equity economics; none is
  treated as issuer cash or EV debt.
- ARES uses only Class A plus economically identical non-voting shares (227,447,653). Non-economic Class B/C shares are
  excluded. The $1.46003B Series B claim is deducted once; its October 2027 conversion at 0.2717–0.3260 Class A shares
  per preferred share is recorded as a future invalidation event, not simultaneous dilution.
- RF uses $17.44B common equity after the exact $1.4B preferred liquidation claim. Deposits, securities, credit costs,
  AOCI and regulatory capital remain inside the regional-bank residual-income route.
- IBKR uses parent common earnings/equity and 453,078,171 current Class A/B shares. The $16.346B holding-company NCI is
  not deducted again. July registrations are bounded as up to 3,419,567 bear-case shares without assuming proceeds.
- BNY uses $39.91B common equity after its reported preferred claim. The July Series N issue adds $500M of proceeds and
  preferred claim once. Its missing exact coupon is bounded by $25M–$40M annual drag. The August $2.5B note issue adds
  fixed coupon interest plus a 4.5%–6.5% floating-note range; 0%/50%/100% proceeds-income offsets flow through the
  bear/base/bull common-earnings assumptions.
- BX derives common earnings as parent NetIncomeLoss less redeemable-NCI earnings and does not subtract consolidated-fund
  or partnership NCI again. Performance revenues, fund realizations and the tax-receivable agreement remain material.
- KKR subtracts the $2.543404B Series D preferred claim once and uses current parent common shares. Global Atlantic,
  fund and CLO financing stay inside equity economics; FRE, carry, exchangeables and realization cycles remain material.
- CBOE uses exchange operating FCFF. Matched $2.5423B clearing collateral is excluded from issuer cash; five annual
  periods plus current TTM govern cash conversion. The pending Australia/Canada sales and amended revolver keep it
  Conditional rather than Pass.
- Visa uses a manually reconstructed controlling-period TTM because the generic Companyfacts normalizer stopped at
  2026-03-31. Exact FY2025 plus current nine months less prior nine months gives revenue $44.488B, OCF $22.580B, capex
  $1.567B and interest $0.776B. Customer collateral is matched and excluded; net settlement and litigation gaps are
  reserved. The as-converted share denominator prevents a second preferred claim deduction.
- TRGP uses enterprise FCFF from reported OCF plus after-tax interest, then full/half/quarter retention of reported growth
  capex after maintenance capex. It does not feed the issuer's after-debt adjusted FCF into an enterprise model. Finance
  leases are already included in reported total debt and are not added twice. Acquisition, project and NCI risks keep it
  Conditional; its negative raw bear residual is retained privately and the public $0 is a limited-liability floor.
- KMI uses five annual periods plus current TTM enterprise FCFF. Equity-method investments are not added as surplus cash
  because OCF already removes equity earnings and adds distributions. The cutoff $1.75B note issue is treated as
  net-debt-neutral refinancing, with no unsupported project value added.

## Challenge and verification

Luna high separately reviewed ARES/BX/KKR and RF/BNY/IBKR. Luna xhigh reviewed CBOE/V/TRGP/KMI and their event bodies.
Sol reconciled all findings against the frozen filings and formula replay.

Resolved findings:

- Critical: ARES initially included non-economic Class B/C shares; corrected to Class A plus non-voting shares.
- Important: BNY initially disclosed but did not model the August note interest; fixed and floating interest ranges now
  reduce forward common earnings.
- Important: Visa's generic TTM was stale; the controlling June structural periods now drive all four TTM inputs.
- Important: TRGP's issuer-adjusted FCF is after debt service and cannot feed enterprise FCFF; the model now starts from
  reported OCF and adds after-tax interest once.

The remaining BNY Series N coupon uncertainty is a disclosed Minor limitation bounded in the Low-reliability range.
No Critical or Important finding remains.

- Deterministic candidates: `output/batch-39-history-run-d-20260907` and
  `output/batch-39-history-run-e-20260907`; all 21 files are byte-identical.
- Report SHA-256: `9771390e297b4f3a3d53a7f816ff6aec7bc83ba0509031fc6159f7e7dc294897`.
- Focused Batch 39 and calculator tests: **15 passed**.
- Complete backend regression: **1,651 passed, 3 skipped, 1 warning** (225.00 seconds). The warning is the existing
  Python `crypt` deprecation in passlib.
- Frontend production build: passed, 1,694 modules. No UI behavior changed in this batch.
- Isolated catalog: 390 companies — 116 available / 262 conditional / 12 unavailable; 378 review-required / 12 withheld.
- Catalog tree SHA-256: `b4f140f7c9ebb1778e462826cbd4fbd131fe5d2c1cc93d8b28041de2b163fc6c`.
- Catalog manifest SHA-256: `9595174838fdeec3883c15a3ee674d6db56c5af7104b2a9d7da55e8ac94cf6c5`.
- Real API: 390 list entries, 390 detail/calculator GETs, 390 expected calculator outcomes, exact list/detail parity,
  zero private leaks, and zero forbidden serving imports.
- API receipt SHA-256: `e5cdfc30f7b3a14f8ca3aeee51aefa0dffb92254f97f1d22155f9753c0952233`.
- Exact API/import receipt SHA-256: `edfc98f8512ea3dce11a10abb2120c7b1e23687447934c290e013db1d6307ea8`.

## Confirmation boundary

The confirmed predecessor remains 380 companies: 116 Pass / 252 Conditional / 12 Withheld. The Batch 39 candidate
would produce 390 companies: 116 Pass / 262 Conditional / 12 Withheld.

The Recovery Learning Watchlist now has 274 entries (262 Conditional / 12 Withheld); the cumulative withheld register
remains 22 entries because no Batch 39 issuer was withheld. Tracked serving artifacts are unchanged. Recovery, Batch 40,
merge, push and deployment have not been performed.
Watchlist SHA-256: `4c377cc1d661ea7f90a8bf4289dd22a4287685d625df977382d232ca5158ced0`.
Withheld-register SHA-256: `3f5f1ade1e95013dccce0036bbb566c3b781cd03bdb3b0e9d08431cd3fb68d2a`.
