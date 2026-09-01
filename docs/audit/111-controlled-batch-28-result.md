# Controlled Universe Reset Batch 28 Initial Result

Date: 2026-08-31  
Status: **user-confirmed on 2026-08-31**

## Outcome

- Pass: **2/10** — FICO, ZBRA
- Conditional: **8/10** — QCOM, CDNS, MCHP, GEN, PTC, CSCO, TYL, JBL
- Withheld: **0/10**
- Numeric: **10/10**

| Ticker | Outcome | Low | Base | High | Reliability | Simple reason |
| --- | --- | ---: | ---: | ---: | --- | --- |
| QCOM | Conditional | $74.31 | $141.72 | $230.96 | Low | Modular closed before the valuation date, but acquired assets and future cash conversion were not yet available |
| CDNS | Conditional | $64.39 | $107.39 | $156.23 | Low | Large cash-and-stock acquisition still lacks a complete post-deal operating history |
| FICO | Pass | $142.05 | $465.36 | $892.27 | Low | Five-year cash history, cash/securities, debt, buybacks, and shares reconcile |
| MCHP | Conditional | $3.05 | $17.76 | $46.42 | Low | Downturn recovery plus preferred dividends and March 2028 mandatory conversion materially affect common value |
| GEN | Conditional | $14.67 | $28.78 | $48.95 | Low | Cybersecurity cash is mixed with Instacash loan originations and sales after the MoneyLion transaction |
| PTC | Conditional | $54.40 | $124.67 | $191.63 | Low | Historical cash includes businesses sold in the Kepware/ThingWorx divestiture |
| CSCO | Conditional | $27.82 | $52.34 | $93.28 | Low | Splunk integration, software conversion, debt, restructuring, and product mix remain material |
| TYL | Conditional | $105.86 | $240.13 | $347.79 | Low | BFTR integration and a $537.4M purchase commitment require governed timing assumptions |
| ZBRA | Pass | $41.27 | $205.50 | $350.36 | Low | Five-year device-cycle history and the complete cash/debt/share bridge reconcile |
| JBL | Conditional | $19.54 | $104.26 | $220.20 | Low | Recent acquisition, acquired conversion, leases, restructuring, and working capital remain material |

These are baseline decision ranges, not predictions or recommendations. Every range is finite,
ordered, and has a positive base. No unavailable value was replaced with zero.

## Controlling sources

| Ticker | Accession | Filed | Report period |
| --- | --- | --- | --- |
| QCOM | 0000804328-26-000086 | 2026-07-29 | 2026-06-28 |
| CDNS | 0000813672-26-000092 | 2026-07-29 | 2026-06-30 |
| FICO | 0000814547-26-000030 | 2026-07-29 | 2026-06-30 |
| MCHP | 0000827054-26-000038 | 2026-08-06 | 2026-06-30 |
| GEN | 0000849399-26-000031 | 2026-08-07 | 2026-07-03 |
| PTC | 0001193125-26-328444 | 2026-07-31 | 2026-06-30 |
| CSCO | 0000858877-26-000078 | 2026-05-19 | 2026-04-25 |
| TYL | 0000860731-26-000050 | 2026-07-29 | 2026-06-30 |
| ZBRA | 0001628280-26-052550 | 2026-08-04 | 2026-07-04 |
| JBL | 0001628280-26-046138 | 2026-06-30 | 2026-05-31 |

Validated difficult-106 evidence was reused for CDNS, MCHP, CSCO, and JBL. Six missing packets and
controlling packages were captured once. Two cache-only source and structural replays then reused
all ten with no fetching or reparsing. Wrapper-level diagnostic dates were never used to select
facts.

## Load-bearing treatments

- QCOM includes the July 28 completed Modular transaction and all 18M reported issued shares. The
  acquired allocation was not yet practicable, so the result remains Conditional.
- MCHP models seven remaining quarterly preferred dividends and the reported March 15, 2028
  mandatory conversion range of 16.006–19.608 common shares per preferred share. The uncertain
  capped-call benefit is excluded; the $1.485B liquidation preference is not double-counted.
- GEN keeps reported Instacash originations and sales inside consolidated cash conversion and does
  not relabel financial assets as issuer cash.
- PTC records the $523.306M divestiture proceeds, $462.6M gain, $7.5M expected cash, and up to $125M
  contingent consideration without adding sale proceeds to cash twice.
- TYL discounts the reported $537.4M through-2031 purchase obligation using governed 3/4/5-year
  timing, all within the disclosed endpoint.
- ZBRA excludes the $96M nonmarketable Skild AI investment from issuer cash. JBL conservatively
  includes $4M NCI and the reported $51M finance-lease payment obligation.

## Independent challenge

Two disjoint reviewers challenged identity, cutoff, units, source lineage, event state, model
suitability, bridges, arithmetic, classifications, calculator parity, and public safety. Important
findings were repaired for QCOM's completed event, MCHP's preferred structure and share unit, GEN's
mixed financial-asset scope, PTC's divestiture scope, and TYL's commitment endpoint. Final
disposition: **0 Critical / 0 Important**. All 30 DCF scenarios independently replayed exactly.

## Determinism and verification

- Source replay A/B: byte-identical, hash
  `9b23806b3f1acb0a3928d4371365443ca663b1cb432e4bac9f78a07a783794a7`
- Structural replay A/B: byte-identical, hash
  `263ba394cf8acb564ceb9af20524c936c32dae12cfd484136c437b0fc63a390d`
- Final candidate I/J: 21/21 files byte-identical; report SHA-256
  `c018325121f1e14c53508799f56e51b425a6dc55f9125b0d461563b96d9ab6e9`
- Final candidate tree: `bcbeefe883295336d211117e4bb0500815741dcf42c066ee06324e0a99a82fab`
- Focused Batch 28 tests: **9 passed**
- Complete backend suite after the final evidence fix: **1,510 passed, 3 skipped, 1 warning**
- Frontend production build: **1,694 modules**, passed; no frontend code changed afterward
- Isolated cumulative catalog: **280 issuers** — 106 available / 165 conditional / 9 unavailable;
  artifact tree `10d3379d935317daa3013d82cfd8edef273bf95897283472ba162abdd3300e45`
- Real API: 280 list, 280 detail GET, 280 calculator GET/default parity; 271 numeric POST 200,
  9 unavailable POST 400, zero private leaks
- API receipt SHA-256:
  `d12f72de4551ae82834c992fba2603995b19bfa540e93f833ec04c94974c477f`
- Catalog manifest SHA-256:
  `235124bfa3d9814f0027e49f8511f7cd2080374532b36e5f603cc462617970cf`
- Pre-confirmation watchlist remains 166 (157 Conditional / 9 Withheld), SHA-256
  `a69685b0cecee22058f27c3e356494c2f177401d25dbe75f03cd2013b733dc04`
- Automatic-withheld history remains 19, SHA-256
  `28bcfdd2985f3f3d87320e9e780aac630923510d0e46c614d9cfb5035e19f3ec`
- Tracked serving artifacts remain unchanged.

## Confirmation and bookkeeping

The user replied `y` on 2026-08-31. QCOM, CDNS, MCHP, GEN, PTC, CSCO, TYL, and JBL entered the
Recovery Learning Watchlist as direct Conditional entries. The confirmed watchlist now contains
**174 companies** — 165 Conditional and 9 Withheld. There are no Batch 28 Withheld companies, so no
recovery attempt or withheld-register change is needed. Batch 29, serving promotion, merge, push,
and deployment remain outside scope.

Confirmed watchlist SHA-256:
`0f0f657b7ae4c802b9c4142f6173d0b5851730f11e35e8c67c4b4e354a0d22d9`. The unchanged
withheld-register SHA-256 remains
`28bcfdd2985f3f3d87320e9e780aac630923510d0e46c614d9cfb5035e19f3ec`.
