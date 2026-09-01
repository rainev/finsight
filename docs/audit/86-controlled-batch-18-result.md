# Controlled Universe Reset Batch 18 Initial Result

Status: **firsthand verified and user-confirmed on 2026-08-30**. Exactly the ten frozen Batch 18
issuers were processed at the 2026-08-14 valuation date. Confirmation added the five direct
Conditional companies to the Recovery Learning Watchlist. No recovery, withheld-history mutation,
tracked serving promotion, Batch 19, merge, push, or deployment was performed.

## Outcome

- Pass: **5/10** — HWM, ADP, DOV, EFX, GD
- Conditional: **5/10** — BA, CAT, CMI, DAL, EMR
- Withheld: **0/10**
- Numeric: **10/10**
- Reliability: **9 Low / 1 Medium (ADP) / 0 High**
- Cumulative through 180 issuers: **64 Pass / 107 Conditional / 9 Withheld**
- Cumulative numeric coverage: **171/180**

These are baseline decision ranges, not predictions or recommendations. Conditional companies have
a finite usable value but retain a named cycle, integration, finance, or equity-floor dependency.

## Company results

| Ticker | Outcome | Low | Base | High | Reliability | Simple reason |
| --- | --- | ---: | ---: | ---: | --- | --- |
| HWM | Pass | $21.31 | $46.98 | $93.62 | Low | Complete aerospace-components cash history and current bridge |
| ADP | Pass | $133.15 | $217.05 | $303.22 | Medium | Client funds excluded from surplus cash and obligation shortfall reserved |
| BA | Conditional | $0.00 | $4.04 | $60.95 | Low | Post-Spirit production recovery and through-cycle margin; bear equity at risk |
| CAT | Conditional | $59.98 | $159.70 | $334.63 | Low | Mixed industrial/captive-finance residual-income model |
| CMI | Conditional | $65.62 | $235.41 | $444.95 | Low | Powertrain cycle, Accelera, settlement execution, guarantees, and NCI |
| DAL | Conditional | $10.59 | $55.57 | $92.30 | Low | Airline cycle, fleet capex, fuel, pensions, and debt sensitivity |
| DOV | Pass | $63.88 | $101.43 | $157.87 | Low | Stable continuing cash history and complete current bridge |
| EMR | Conditional | $35.65 | $71.98 | $122.40 | Low | Post-AspenTech integration and acquisition-funded debt |
| EFX | Pass | $32.16 | $105.54 | $171.06 | Low | Cutoff financing principal/proceeds added once; complete claims/share bridge |
| GD | Pass | $172.33 | $318.80 | $457.61 | Low | Stable defense cash/backlog; restricted cash excluded and rescission offer bounded |

Boeing's public bear value is zero only because its raw bear residual is negative. Its base uses a
source-governed through-cycle margin halfway between the all-history median and upper historical
percentile and remains positive. No missing input was replaced with zero.

## Controlling sources

| Ticker | Accession | Form | Filed | Report period |
| --- | --- | --- | --- | --- |
| HWM | `0000004281-26-000025` | 10-Q | 2026-08-06 | 2026-06-30 |
| ADP | `0000008670-26-000030` | 10-K | 2026-08-05 | 2026-06-30 |
| BA | `0001628280-26-050038` | 10-Q | 2026-07-28 | 2026-06-30 |
| CAT | `0000018230-26-000046` | 10-Q | 2026-08-05 | 2026-06-30 |
| CMI | `0000026172-26-000029` | 10-Q | 2026-08-04 | 2026-06-30 |
| DAL | `0000027904-26-000031` | 10-Q | 2026-07-10 | 2026-06-30 |
| DOV | `0000029905-26-000027` | 10-Q | 2026-07-23 | 2026-06-30 |
| EMR | `0000032604-26-000043` | 10-Q | 2026-08-04 | 2026-06-30 |
| EFX | `0000033185-26-000028` | 10-Q | 2026-07-21 | 2026-06-30 |
| GD | `0000040533-26-000032` | 10-Q | 2026-07-29 | 2026-07-05 |

## Source capture and replay

- Exact manifest SHA-256:
  `c2574b73d31c4581d84087b6f4ee5d624831adc9daf59a3fb26b5fb07b413a38`
- SEC packets: BA/CAT/CMI/DAL/GD reused; five fetched; exact 10/10
- Structural wrappers: the same five reused; five captured under Python 3.11/Arelle; 10/10 parsed
- Source packet and replay A/B tree SHA-256:
  `1aac46f2a1cdd92fd3f39ffa53831d619b7aa9187b6f5e93b1578efa0c46370c`
- Structural replay A/B tree SHA-256:
  `ede497cc0856ac9325491e0eb142b9a8f5768fefb0263d62b76f5cad781150de`
- Initial mixed capture-mode structural tree SHA-256:
  `364295d8a2078b96754c3289e1cc717d2a09358e3072767876c583bba552c599`
- EFX financing-event receipt SHA-256:
  `d45b7d22ab3d1a35b1e4410ff5e839094439045e29b3102e3354321dd8dddcdf`
- GD rescission-event receipt SHA-256:
  `cd5813aa3437618a65e8591bb536873c1984f576fca73e412c56615fc6b37e01`

Equifax's issued $1B notes and $990.5M proceeds were added at cutoff; the intended commercial-paper
repayment was not assumed completed without evidence. General Dynamics' offer covering up to
1,010,925 shares remains inside its governed share range and was not assumed exercised.

## Source and economic challenge

No subagents were used in this run. Two separate local lenses challenged the exact candidate:

1. **Source/mechanics:** issuer/accession/period, scoped ADP/BA/GD concepts, client-fund assets and
   obligations, finance/client cash, debt/leases, shares, claims, and post-balance events. It found
   and repaired General Dynamics' cash bridge: $33M restricted cash was removed from surplus cash.
2. **Economic/public:** recalculated every DCF and CAT residual-income state, Boeing's cycle-margin
   construction, sensitivity directions, calculator families/defaults, public/private boundary,
   and exact ten-company parity.

Final independent challenge receipt:
`1bd2c2430e5ed2dc34aefb60f60e1de42ddfb018626bc61a805cf582e16eef9f`
— 10/10 challenged, 0 Critical, 0 Important.

## Determinism and automated verification

- Candidate-e/candidate-f full-tree SHA-256:
  `830245407ca36c280f1b9ae3ef702f5a5e49b6544f28dbfa5b403c93084d0bbe`
- Generated-private tree SHA-256:
  `a50178d41657f9ea34b553bb6dfbd2b1fb9bf1d46f38b77be13f7e97c84f5b82`
- Staged-public tree SHA-256:
  `a2fcf721b59a3c1f42774d214b05e3f1f65ba090bffdc893de83c98d246272c0`
- Final report SHA-256:
  `c683035ccce53bf24210a7b5bf3e948ef1aa2d14647110fd0ec21af3df16c912`
- Focused Batch 18 tests: `9 passed`
- Complete backend suite: `1,555 passed, 3 skipped, 1 warning`
- Frontend production build: passed (`1,694` modules transformed)
- `git diff --check`: passed

## Real consumer path

- Isolated cumulative catalog: 180 exact artifacts, Batches 01–18
- Availability: 64 available / 107 conditional / 9 unavailable
- Publication: 171 review-required / 9 withheld
- Catalog artifact-tree SHA-256:
  `8be8800031304849612321802edb854f20512ccc954dab9186da64d314bd0771`
- Real localhost FastAPI list: HTTP 200, exact count 180
- Detail/catalog parity: 180/180; exact Batch 18 staged parity: 10/10
- Calculator GET parity: 180/180
- Calculator POST: 171 numeric HTTP 200; nine unavailable HTTP 400
- Batch 18 model families: nine operating / one mixed-finance equity-earnings
- Private leaks: 0
- API receipt SHA-256:
  `bc05eb37890538620085beac42a9f51acb7e446015a4334826bbea5c45ae1395`

The API used an isolated untracked catalog, a local test-only auth harness, and `save=false`. Arelle
remained outside the serving process. Tracked serving roots stayed unchanged.

## Protected state and confirmation gate

- Recovery Learning Watchlist is 116 (107 Conditional / 9 Withheld); SHA-256:
  `d1db5d18e687ed8a9c615cd2456c0b43f64626b04a9a1049fb71a840f023a274`
- BA, CAT, CMI, DAL, and EMR were added with `recovery_outcome=not_applicable`; BA retains explicit
  equity-at-risk status. Pass companies HWM, ADP, DOV, EFX, and GD were not added.
- Cumulative automatic-withheld history remains 19; SHA-256:
  `28bcfdd2985f3f3d87320e9e780aac630923510d0e46c614d9cfb5035e19f3ec`
- Tracked valuation catalog, frontend public data, and generated research roots are unchanged.

The user replied `y` on 2026-08-30. Batch 18 is confirmed and recorded. Because Withheld is 0/10,
no recovery phase is needed. Batch 19 was not started; the next valid signal is
`Start Universe Reset Batch 19`.
