# Batch 11 SYY and BG Recovery Result

Status: **user confirmed on 2026-08-28**. The user authorized the single
permitted recovery attempt for SYY and BG. No serving promotion, Batch 12 work, merge, push, or
deployment was performed.

## Final outcome

- Recovery attempted: **2/2** — SYY, BG
- Recovered Conditional: **1/2** — SYY
- Remaining Withheld: **1/2** — BG
- Final Batch 11: **Pass 2 / Conditional 7 / Withheld 1**
- Final cumulative through 110 issuers: **Pass 47 / Conditional 58 / Withheld 5**
- Numeric coverage: **105/110**

| Ticker | Recovery outcome | Low | Base | High | Reliability |
| --- | --- | ---: | ---: | ---: | --- |
| SYY | Conditional | $25.59 | $51.64 | $79.09 | Low |
| BG | Withheld | — | — | — | — |

## SYY — Conditional pre-Jetro current-state recovery

SYY is recovered only as a standalone snapshot at the latest reportable pre-Jetro balance-sheet
date, 2026-03-28, from the 10-Q filed 2026-04-29 (`0000096021-26-000022`). The signed transaction
is not probability-weighted, blended, or included in intrinsic value.

Current standalone inputs:

- TTM revenue: `$83.567B`
- TTM OCF: `$2.656B`
- TTM capex: `$835M`
- TTM interest-expense magnitude: `$678M`
- TTM cash FCFF: `$2.346190372B`
- Excess cash: `$1.900B`
- Debt/capital leases: `$14.008B`
- Other equity claims: `$0`
- Base diluted shares: `480.738926M`
- Source-linked annual history: three periods

Two source corrections were required during independent challenge:

1. `$473M` European commercial paper is already classified inside reported long-term debt, so
   it is retained as a component fact but not added again.
2. The `$124M` available-for-sale portfolio is restricted inside Sysco's captive insurer, so it
   is not treated as excess cash. The separate `$156M` restricted-cash balance is also excluded.

The private transaction surface binds the approximate `$29.1B` price, `$21.6B` cash component,
`91.5M` expected Sysco shares, initial `$22B` bridge commitment, reduced `$19B` bridge, `$3B`
delayed-draw facility, `$6.3B` rate-lock notional, `$88M` issuance fees, and `$1.164B`
termination fee. Every Jetro row is labeled
`separate_transaction_surface_not_in_intrinsic_value`.

The result invalidates on closing, termination, financing draw or issuance, material term
change, or a newer standalone filing that changes cash, debt, or shares. It is not a
post-announcement or post-close equity value.

## BG — Withheld after one recovery attempt

BG remains Withheld. Viterra closed on 2025-07-02, but the comparative H1 2025 period excludes
Viterra and the filing contains no comparable combined annual cash history or filed pro-forma
cash-flow facts.

Current combined H1 evidence from controlling accession `0001628280-26-050540`:

- OCF: `-$1.126B`
- Capex: `$779M`
- Interest: `$378M`
- Pretax income / tax: `$1.004B / $222M`
- Current combined H1 cash FCFF: `-$1.610581673B`
- Cash plus marketable securities: `$788M`
- Debt: `$15.214B`
- NCI plus redeemable NCI: `$1.457B`
- Diluted shares: `195.536176M`

Official evidence tiers ended as:

1. controlling structural filing — accepted current combined H1, but cash is negative;
2. filed pro-forma cash flow — not disclosed;
3. comparable combined annual history — unavailable.

The consumed recovery records three hard blockers:

- `PREDECESSOR_HISTORY_NOT_COMPARABLE`
- `PRO_FORMA_CASH_FLOW_NOT_DISCLOSED`
- `NONFINITE_OR_NONPOSITIVE_VALUE`

No positive cycle midpoint or substitute model was manufactured. BG has consumed its one
automatic recovery attempt.

## Independent challenge

Three Luna XHigh reviewers challenged SYY sources/economic isolation, BG source-tier exhaustion,
and recovery/bookkeeping mechanics. Final verdict: **PASS; no remaining Critical or Important
finding**.

The Important findings resolved were SYY's commercial-paper double count and captive-insurance
investment classification. Final arithmetic, source periods, units, debt, cash, claims, share
denominators, transaction isolation, warnings, public metadata, sensitivity directions, and BG
fail-closed state reconcile.

## Bookkeeping

All eight non-Pass Batch 11 issuers are now on the Recovery Learning Watchlist:

- SYY recovered Conditional;
- CHD, COST, DLTR, MDLZ, PM, and KHC direct Conditional;
- BG Withheld after recovery.

Only BG was added to the cumulative withheld register.

- Recovery Learning Watchlist: **63** — 58 Conditional / 5 Withheld
- Watchlist SHA-256: `5936ece29b7deae46a397510b670628801ffd906e7aa98918389203afb41a471`
- Cumulative withheld register: **9** entries
- Withheld-register SHA-256: `1d24cce0812bbd3586f1c00fd8fbb894f04d930c492b06c9a5e9c63f6e81e6b5`

## Determinism, tests, build, and real API

- Final candidate-k/l full tree SHA-256: `5d394c0f2355a18cef5e4a6b70a32a32873c35c369605d80b69d686aac54046a`
- Generated-private tree SHA-256: `d697fe8723b60fad9b9359d3f99fa4dd0891479b8f75baf67b2a4554eadd18d8`
- Staged-public tree SHA-256: `633f8eb14b1d477e0ec1011ca26936f0226d461f3946b501f868476d35c8689a`
- Focused recovery/bookkeeping/catalog tests: `28 passed, 1 warning`
- Full backend suite: `1,335 passed, 3 skipped, 1 warning`
- Frontend production build: passed (`1,694` modules transformed)
- Isolated cumulative catalog: `110` artifacts, batches 01–11
- Catalog availability: `47 available / 58 conditional / 5 unavailable`
- Catalog publication: `105 review-required / 5 withheld`
- Catalog artifact-tree SHA-256: `59450105078ed482ab8b6af4482eeacde9d4fcc48751c0c2c562f163dff69045`
- Real localhost FastAPI list: HTTP 200, exact count 110
- Detail parity: 110/110
- Calculator GET parity: 110/110
- Calculator default POST parity: 105/105 numeric; five Withheld return HTTP 400
- Private leaks: 0
- API receipt SHA-256: `5862553f199a16dbd7e8773dfab6b8d40f2c2dfcfa3ef88d3e82819dfe174a9b`

The API used an isolated untracked catalog plus the documented local current-user override with
`save=false`; it verifies valuation/calculator behavior, not real authentication, Postgres,
MinIO, or persistence. Startup logged the expected unavailable local MinIO warning.

The cumulative catalog build also exposed and fixed a successor-manifest bug: base-catalog
publication counts were not accumulated before appending the next batch. A regression test now
requires the complete 105/5 publication total.

## Confirmation gate

The user confirmed the final Batch 11 recovery result on 2026-08-28. SYY and BG have each
consumed their one recovery attempt. Do not start Batch 12, promote or activate a tracked serving
catalog, merge, push, or deploy without a separate user signal.
