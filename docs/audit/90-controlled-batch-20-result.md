# Controlled Universe Reset Batch 20 Initial Result

Status: **firsthand verified and user-confirmed on 2026-08-30**. Exactly the ten frozen Batch 20
issuers were processed at the 2026-08-14 valuation date. Confirmation added the seven direct
Conditional companies to the Recovery Learning Watchlist. No recovery, withheld-history mutation,
tracked serving promotion, Batch 21, merge, push, or deployment was performed.

## Outcome

- Pass: **3/10** — ROL, SWK, PAYX
- Conditional: **7/10** — PNR, AOS, SNA, LUV, UAL, UNP, CTAS
- Withheld: **0/10**
- Numeric: **10/10**
- Reliability: **10 Low / 0 Medium / 0 High**
- Cumulative through 200 issuers: **71 Pass / 120 Conditional / 9 Withheld**
- Cumulative numeric coverage: **191/200**

These are baseline decision ranges, not predictions or recommendations. Conditional companies
have finite usable values but retain a named acquisition, airline-cycle, captive-finance, or major
transaction dependency.

## Company results

| Ticker | Outcome | Low | Base | High | Reliability | Simple reason |
| --- | --- | ---: | ---: | ---: | --- | --- |
| PNR | Conditional | $22.22 | $44.02 | $74.35 | Low | Current standalone value; signed $1.425B Taco acquisition remains pending |
| ROL | Pass | $12.90 | $20.84 | $33.68 | Low | Four-year route cash history and complete current debt/share bridge |
| AOS | Conditional | $30.08 | $53.91 | $83.84 | Low | Leonard Valve acquisition has preliminary accounting and partial acquired cash history |
| SNA | Conditional | $121.89 | $272.54 | $529.43 | Low | Mixed tools/Financial Services residual-income model |
| LUV | Conditional | $7.34 | $13.80 | $28.27 | Low | Equity-earnings airline-cycle fallback; negative post-capex cash and large fleet commitments |
| SWK | Pass | $32.67 | $58.26 | $101.19 | Low | CAM sale and debt repayment reconciled; environmental/contingent claims deducted once |
| UAL | Conditional | $58.83 | $106.23 | $168.05 | Low | Airline cycle, aircraft deliveries, capacity commitments, fuel, and pensions |
| UNP | Conditional | $59.38 | $110.26 | $199.31 | Low | Current standalone rail value; Norfolk Southern transaction remains pending |
| CTAS | Conditional | $45.82 | $74.22 | $114.55 | Low | Current standalone value; approximately $5.5B UniFirst deal remains under FTC review |
| PAYX | Pass | $50.57 | $83.97 | $137.05 | Low | Full post-Paycor fiscal year and client-fund shortfall/corporate cash separated |

Every bear/base/bull value is finite, ordered, and positive. No missing input was replaced with
zero and no equity-floor convention was required.

## Controlling sources

| Ticker | Accession | Form | Filed | Report period |
| --- | --- | --- | --- | --- |
| PNR | `0000077360-26-000045` | 10-Q | 2026-07-28 | 2026-06-30 |
| ROL | `0000084839-26-000040` | 10-Q | 2026-07-23 | 2026-06-30 |
| AOS | `0000091142-26-000098` | 10-Q | 2026-07-30 | 2026-06-30 |
| SNA | `0000091440-26-000144` | 10-Q | 2026-07-23 | 2026-07-04 |
| LUV | `0000092380-26-000077` | 10-Q | 2026-07-23 | 2026-06-30 |
| SWK | `0000093556-26-000031` | 10-Q | 2026-07-29 | 2026-07-04 |
| UAL | `0000100517-26-000139` | 10-Q | 2026-07-16 | 2026-06-30 |
| UNP | `0000100885-26-000250` | 10-Q | 2026-07-23 | 2026-06-30 |
| CTAS | `0000723254-26-000028` | 10-K | 2026-07-29 | 2026-05-31 |
| PAYX | `0001193125-26-307785` | 10-K | 2026-07-17 | 2026-05-31 |

Malformed top-level structural dates were retained only as diagnostics. Filing selection uses the
source receipt and each fact's own period.

## Source capture and cutoff events

- Exact manifest SHA-256:
  `a6da41ca5e593099973619dae32ac1eca1321c322161a9ea64274b5f35986301`
- SEC packets: UAL/UNP reused; eight fetched; exact 10/10
- Structural wrappers: the same two reused; eight captured under Python 3.11/Arelle; 10/10 parsed
- Source packet initial/replay A/B tree SHA-256:
  `b6c095e8d948346be8e8ad9eb98325c58e9651982ce944fe0c1cfab1ee405be6`
- Structural replay A/B tree SHA-256:
  `bcd014ecf55e23989b191aed1a3ee4a32ed969a02ea85568900315f160bb42f4`
- Initial mixed capture-mode structural tree SHA-256:
  `e58cb511a21df8636ac1cb79af2415e3dacbb5fd65cba4e1882da11fdf3c0c1e`
- Cutoff event-source tree SHA-256:
  `02a8abc2ba58a28389482bded2faddd79b2c09e3315bdeb2bded5a7a6a1b495e`

Southwest's August 10 $2B revolver was bound as liquidity capacity with zero outstanding, so no
debt or cash was added. Pentair, Union Pacific, and Cintas remain current standalone values with
their pending Taco, Norfolk Southern, and UniFirst transactions kept separate. A.O. Smith's
valuation revenue annualizes the filed Leonard Valve H1 contribution. Stanley Black & Decker's
$1.815B CAM proceeds were not added again because current cash and debt already reflect the sale.
Paychex excludes $4.8322B of client funds from corporate surplus cash and reserves the $52.4M
obligation excess.

## Source and economic challenge

No subagents were used. Two separate local lenses challenged the exact candidate:

1. **Source/mechanics:** issuer/accession/cutoff/period, shares, client funds, debt/leases, claims,
   acquisitions/divestitures, fleet commitments, and the Southwest cutoff event.
2. **Economic/public:** operating versus equity-level model choice, airline/finance/deal treatment,
   arithmetic, scenario direction, classification, calculator family, and public/private boundary.

Pentair's standard annual interest alias ended in 2019 even though its current interest fact and
other annual cash inputs were current. The model rejected the stale series and used a governed,
nonzero current interest/revenue ratio for annual history, labeling every repaired row estimated.

Final independent challenge receipt SHA-256:
`025c429904cd06964ce48915a50b48272347e6bfcde0298f3b33a0485f120bbe`
— 10/10 challenged, 0 Critical, 0 Important.

## Determinism and automated verification

- Candidate-B/candidate-C full-tree SHA-256:
  `917c9445d5428cea4149de2f711d29ee108f2c19eb8031ceb46dd4c0774c833e`
- Generated-private tree SHA-256:
  `20ff9773d9ff28b1dc72219ad18cdd6f85d02a376b77a6efab6445f9c4d89aab`
- Staged-public tree SHA-256:
  `6542c5fcc39322f410a845a071bd98d589b93abe3bc246267b9a520acc229aa9`
- Final report SHA-256:
  `6d03f2604d442d294e8ffe9f46fbb6d32c8ba50e9b2a4d0068082f86fcb92ca1`
- Focused Batch 20 tests: `9 passed`
- Complete backend suite: `1,573 passed, 3 skipped, 1 warning`
- Frontend production build: passed (`1,694` modules transformed)
- `git diff --check`: passed

## Real consumer path

- Isolated cumulative catalog: 200 exact artifacts, Batches 01–20
- Availability: 71 available / 120 conditional / 9 unavailable
- Publication: 191 review-required / 9 withheld
- Catalog artifact-tree SHA-256:
  `0518e21bc4ec8beba63a7b6f239811467c3490dc9bd22955c4abd38d898b2cc9`
- Catalog manifest SHA-256:
  `89ed36356f3d87e35c6cb2d8738aad8521b5e8f35417282f2cd7962255087b14`
- Real localhost FastAPI list: HTTP 200, exact count 200
- Detail/catalog parity: 200/200; exact Batch 20 staged parity: 10/10
- Calculator GET parity: 200/200
- Calculator POST: 191 numeric HTTP 200; nine unavailable HTTP 400
- Batch 20 model families: eight operating / two equity-earnings
- Private leaks: 0
- API receipt SHA-256:
  `2fe414b63c4290db1f65f33b1906e5326a7d3e95a07d0bf94282b5ffa51fb7a5`

The API used an isolated untracked catalog, a local test-only auth harness, and `save=false`. Arelle
remained outside the serving process. Tracked serving roots stayed unchanged.

## Protected state and confirmation gate

- Capture-guard protected trees remain exactly:
  - tracked valuation catalogs:
    `38efe664dc981e9d2383ece43b66e9ae326b4b9a7cc2443f2463498432ef66a8`
  - frontend public data:
    `353a14bc672002e88d248811f98d23d4c1fb47cf28e526d969f463f256260274`
  - generated research surface:
    `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
- Recovery Learning Watchlist is 129 (120 Conditional / 9 Withheld); SHA-256:
  `723b31bac31da7918a71fda0919901f8a0efbb8572cfba66d90360d29bc402b2`
- PNR, AOS, SNA, LUV, UAL, UNP, and CTAS were added with
  `recovery_outcome=not_applicable`. Pass companies ROL, SWK, and PAYX were not added.
- Cumulative automatic-withheld history remains 19; SHA-256:
  `28bcfdd2985f3f3d87320e9e780aac630923510d0e46c614d9cfb5035e19f3ec`
- Tracked valuation catalog, frontend public data, and generated research roots are unchanged.

The user replied `y` on 2026-08-30. Batch 20 is confirmed and recorded. Because Withheld is 0/10,
no recovery phase is needed. Batch 21 was not started; the next valid signal is
`Start Universe Reset Batch 21`.
