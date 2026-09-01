# Controlled Universe Reset Batch 26 Initial Result

Date: 2026-08-31  
Status: **user-confirmed on 2026-08-31**

## Outcome

- Pass: **6/10** — SWKS, ADI, AMAT, GLW, HPQ, MSI
- Conditional: **4/10** — AMD, INTC, IBM, APH
- Withheld: **0/10**
- Numeric: **10/10**

| Ticker | Outcome | Low | Base | High | Reliability | Simple reason |
| --- | --- | ---: | ---: | ---: | --- | --- |
| AMD | Conditional | $28.39 | $58.21 | $103.95 | Low | ZT integration and the manufacturing divestiture change historical comparability |
| SWKS | Pass | $34.85 | $61.53 | $134.61 | Low | Complete five-year cash cycle and compact cash/debt bridge |
| ADI | Pass | $65.39 | $118.56 | $198.54 | Low | Post-Maxim history and current cash, securities, debt, and shares reconcile |
| AMAT | Pass | $68.17 | $115.04 | $214.00 | Low | Complete cash/investment total and bounded equipment-cycle reinvestment |
| GLW | Pass | $3.35 | $15.16 | $31.60 | Low | Q2 capex extraction repaired; NVIDIA warrant dilution fully bounded at about 2.1% |
| HPQ | Pass | $23.95 | $39.18 | $59.69 | Low | Mature hardware/print cash history and debt bridge reconcile despite negative book equity |
| INTC | Conditional | $0.00 | $3.00 | $16.50 | Low | Foundry/fab transformation, large debt/NCI, and four negative historical cash years |
| IBM | Conditional | $39.39 | $86.94 | $176.96 | Low | Residual income avoids finance-debt double counting, but large acquisitions remain material |
| MSI | Pass | $87.74 | $184.82 | $328.81 | Low | Stable public-safety/service cash history and complete debt/NCI bridge |
| APH | Conditional | $16.46 | $39.56 | $70.84 | Low | $10.684B first-half acquisition and integration materially change the operating scale |

These are baseline decision ranges, not market predictions or recommendations. INTC's public $0
bear is a limited-liability floor: its raw bear equity value is negative and remains preserved
privately. No missing input was replaced with zero.

## Controlling sources

| Ticker | Accession | Filed | Report period |
| --- | --- | --- | --- |
| AMD | 0000002488-26-000123 | 2026-08-05 | 2026-06-27 |
| SWKS | 0000004127-26-000049 | 2026-07-28 | 2026-07-03 |
| ADI | 0000006281-26-000052 | 2026-05-20 | 2026-05-02 |
| AMAT | 0001628280-26-037227 | 2026-05-21 | 2026-04-26 |
| GLW | 0000024741-26-000255 | 2026-07-29 | 2026-06-30 |
| HPQ | 0000047217-26-000029 | 2026-05-28 | 2026-04-30 |
| INTC | 0000050863-26-000157 | 2026-07-24 | 2026-06-27 |
| IBM | 0000051143-26-000078 | 2026-07-23 | 2026-06-30 |
| MSI | 0000068505-26-000028 | 2026-08-05 | 2026-07-04 |
| APH | 0001104659-26-089194 | 2026-07-31 | 2026-06-30 |

AMD and APH source packets and structural packages were reused from validated difficult-106
evidence. The other eight source packets and filing packages were captured once. Cache-only replay
then reused all ten with zero network fetches and zero reparsing. Malformed structural top-level
period diagnostics were never used for selection; accession, source receipt report date, and each
fact's own period controlled.

GLW required a narrow extraction repair. Companyfacts lacked the current Q2 capex fact, so the
controlling filing's structural `PaymentsForCapitalImprovements` facts reconstruct TTM capex as
$1.282B FY + $754M current H1 - $516M prior H1 = $1.520B. Revenue, OCF, and interest were
reconstructed over the same aligned periods.

## Model and event controls

- Ordinary semiconductor/hardware cycle risk is ranged and does not by itself force Conditional.
- AMD's ledger records the $4.409B ZT consideration, $860M equity portion, historical $361M
  contingency, $2.4B disposal consideration, 1.151052M disposal shares, and the source-proven
  October 2025 settlement. The current contingent claim is zero because it was settled—not because
  a missing value was substituted.
- GLW records $500M warrant proceeds already reflected in current cash, the $796M APIC adjustment,
  $180 exercise price, and 0–18M share sensitivity; no proceeds are added twice.
- INTC uses transparent 3% / 7% / 12% cash-conversion states with the full $50.537B debt and
  $15.601B NCI bridge. Its base remains finite and positive.
- IBM uses parent common equity and common earnings in residual income. Global Financing assets and
  funding remain inside the equity object and are not subjected to an industrial EV debt bridge.
- APH separately records $10.684B of acquisition cash, $7.0077B of acquired goodwill, debt, NCI,
  and dilution.

## Independent challenge

Two disjoint reviewers were used under the FinSight efficiency workflow:

- `gpt-5.6-luna` High checked identity, cutoff, periods, TTM lineages, bridges, events, and public
  safety.
- `gpt-5.6-luna` xhigh challenged model selection, classifications, DCF/residual-income arithmetic,
  floors, sensitivities, calculator routing, and warnings.

The initial challenge found one Important AMD event/claim trace gap and minor AMD-tax/GLW-warrant
metadata gaps. All were corrected in immutable successors F/G. Final disposition: **0 Critical / 0
Important**. Minor monitoring remains for HPQ supplier finance inside operating cash flow and shared
structural helper filed-date metadata. Challenge receipt SHA-256:
`d572638f04ce38ba82dbbdbd15defe3766b1f74229a82c6fb5eef823dae5031a`.

## Determinism and verification

- Initial source capture tree (`capture_batch_02_sources._tree_hash`):
  `8e62ad7a5716151f17a3e68d1b1de74afd4b8144141a1e57a93618ed7a70b887`
- Initial structural capture tree (same contract):
  `626013940cc4056dfc0ec0dd1bc59d735387629c3a3d4d66c1de1ac63108b980`
- Cache-only source replay A/B: byte-identical, all ten reused, hash
  `8e62ad7a5716151f17a3e68d1b1de74afd4b8144141a1e57a93618ed7a70b887`
- Cache-only structural replay A/B: byte-identical, all ten reused, hash
  `036117a20f979117d926ee48f3e0f127e833b6648f8e026c8a7620dd31573780`
- Final candidate F/G: every corresponding file byte-identical; report SHA-256
  `76f7805ebe0b19f98615154503f30b0cd7ab021a227ae58ef684ee45b13cfcde`
- Final candidate tree (`run_batch_07_history._tree`):
  `227fb3353d8af50dba1234e214991d9bd9e2ee935983cfa0e30675001b182747`
- Focused Batch 26 tests: **10 passed**
- Complete backend suite: **1,635 passed, 3 skipped, 1 warning**
- Frontend production build: **1,694 modules**, passed
- Isolated cumulative catalog: **260** issuers — 98 available / 153 conditional / 9 unavailable;
  artifact tree `60858d2f511a14eab43337883c17eb6d094c381ba30e5ac03f4ff92d2d3db11a`
- Real API: 260 list, 260 detail GET, 260 calculator GET, and 260 default parity checks; 251
  numeric POST 200, 9 unavailable POST 400, zero private leaks; IBM routed to `equity_earnings`
- API receipt SHA-256:
  `92e4adfe08cdd16b8a075fea775e94b52af56e4f9de7348c2d7f9482f9c1021a`
- Catalog manifest SHA-256:
  `e3184cd77406549de3e79730f7f1fee5f81d5ee48a4351ac3c694f2407d7bd3d`
- Pre-confirmation watchlist remained 158 (149 Conditional / 9 Withheld), SHA-256
  `91680e4aedaeeebc95b468774be955b724547539ea811b98ca8c7b6c4c962457`
- Append-only withheld history remains 19, SHA-256
  `28bcfdd2985f3f3d87320e9e780aac630923510d0e46c614d9cfb5035e19f3ec`
- Tracked serving artifacts remain unchanged.

## Confirmation and bookkeeping

The user replied `y` on 2026-08-31. AMD, INTC, IBM, and APH entered the Recovery Learning
Watchlist as direct Conditional entries with `recovery_outcome: not_applicable`; INTC retains the
equity-at-risk status. The confirmed watchlist is **162 companies** — 153 Conditional and 9
Withheld. The still-Withheld register remains unchanged because Batch 26 has zero withheld
companies. No recovery is needed. Batch 27, tracked serving promotion, merge, push, and deployment
remain outside scope.

Confirmed watchlist SHA-256:
`46e368ddfca3362758475b90498e39dc6cbe45808f001d7a1d91ddc86affe67e`. The unchanged
withheld-register SHA-256 remains
`28bcfdd2985f3f3d87320e9e780aac630923510d0e46c614d9cfb5035e19f3ec`.
