# Controlled Universe Reset Batch 23 Initial Result

Status: **firsthand verified and user-confirmed on 2026-08-31**. Exactly the ten frozen Batch 23
issuers were processed at the 2026-08-14 valuation date. Confirmation added the eight Conditional
issuers to the Recovery Learning Watchlist. No recovery, withheld-history mutation, tracked serving
promotion, Batch 24, merge, push, or deployment was performed.

## Outcome

- Pass: **2/10** — RSG, LII
- Conditional: **8/10** — AME, CHRW, FDX, PWR, URI, AXON, UPS, LDOS
- Withheld: **0/10**
- Numeric: **10/10**
- Reliability: **10 Low / 0 Medium / 0 High**
- Cumulative through 230 issuers: **85 Pass / 136 Conditional / 9 Withheld**
- Cumulative numeric coverage: **221/230**

These are broad baseline decision ranges, not predictions or recommendations. Ordinary bounded
business risk remains a Pass. Conditional identifies a specific acquisition, separation, claim,
fleet-capex, warrant, transformation, or integration dependency.

| Ticker | Outcome | Low | Base | High | Simple reason |
| --- | --- | ---: | ---: | ---: | --- |
| AME | Conditional | $48.45 | $104.53 | $173.28 | $5.0B Indicor closing, $1.1B acquired sales, and final funding/cash conversion |
| CHRW | Conditional | $14.80 | $47.48 | $113.04 | $604M possible loss with only $155M maximum insurance recovery |
| FDX | Conditional | $77.03 | $129.24 | $216.22 | Post-Freight separation costs, cash allocation, tariffs, leases, and pensions |
| PWR | Conditional | $64.79 | $163.71 | $930M H1 acquisitions and provisional acquired cash conversion |
| RSG | Pass | $37.80 | $82.81 | $158.64 | Five-year route/landfill cash history and complete debt/NCI bridge |
| URI | Conditional | $0.00 | $52.31 | $177.34 | Equipment cycle plus a transparent nonzero fleet-capex run-rate bridge |
| AXON | Conditional | $14.57 | $48.32 | $140.53 | Acquisitions, warrants/convertibles, strategic investments, and claim tail |
| LII | Pass | $95.16 | $209.60 | $379.78 | Five-year HVAC cash history and complete debt/warranty/share evidence |
| UPS | Conditional | $30.35 | $61.37 | $124.62 | $933M transformation costs, tariff claims, pensions, closures, and volume reset |
| LDOS | Conditional | $49.28 | $116.72 | $236.15 | $2.338B H1 acquisition, higher debt, acquired goodwill, and integration |

URI's $0 bear value is a limited-liability floor after reported debt and a pessimistic equipment-
cycle scenario. Its private raw residual is negative. No missing capex was replaced with zero: the
current nonzero $4.712B reinvestment bridge is $4.130B latest standardized annual capex plus current
H1 fleet/other capex less prior H1 fleet/other capex.

## Controlling sources

| Ticker | Accession | Form | Filed | Report period |
| --- | --- | --- | --- | --- |
| AME | `0001037868-26-000175` | 10-Q | 2026-08-04 | 2026-06-30 |
| CHRW | `0001043277-26-000031` | 10-Q | 2026-07-31 | 2026-06-30 |
| FDX | `0001048911-26-000105` | 10-K | 2026-07-20 | 2026-05-31 |
| PWR | `0001050915-26-000025` | 10-Q | 2026-07-30 | 2026-06-30 |
| RSG | `0001060391-26-000275` | 10-Q | 2026-08-07 | 2026-06-30 |
| URI | `0001067701-26-000026` | 10-Q | 2026-07-22 | 2026-06-30 |
| AXON | `0001628280-26-053646` | 10-Q | 2026-08-06 | 2026-06-30 |
| LII | `0001069202-26-000087` | 10-Q | 2026-07-29 | 2026-06-30 |
| UPS | `0001628280-26-053249` | 10-Q | 2026-08-05 | 2026-06-30 |
| LDOS | `0001336920-26-000246` | 10-Q | 2026-08-04 | 2026-07-03 |

## Challenge and corrections

One `gpt-5.6-luna` High reviewer inventoried caches/risks and independently challenged the exact
private candidate. Its first challenge found 0 Critical, 2 Important, and 1 Minor issue:

1. AME's initial Pass missed the cutoff-eligible $5.0B Indicor closing and $1.1B acquired sales;
2. CHRW's initial Pass missed a $604M possible loss and $155M maximum insurance recovery; and
3. AXON cash double-counted $19.126M already inside the $692.533M aggregate.

All three were corrected. AME and CHRW moved to Conditional, and AXON cash is counted once. The
reviewer rechecked the corrected candidate and reported **0 remaining Critical / 0 Important**.
The main agent separately reran source identity, exact DCF arithmetic, sensitivity direction,
public safety, deterministic generation, full suites, and the real API.

Independent challenge receipt SHA-256:
`a922a24d9e79da66929099d6bd723620ebadd6869f7e75e4adca798233653991`.

## Verification evidence

- Frozen manifest SHA-256:
  `ac3a445e1cbfdc1d21a2c089e2eac95bc5fac8a9d9c24fd664e27fc5a5d29209`.
- SEC packet capture: **3 reused / 7 fetched**; exact 10/10.
- SEC packet tree SHA-256:
  `16c5468478af41bd488725df3c4c96909f57e0426f723b0c263c6193ab7fe94f`.
- Structural parsing: 10/10; tree SHA-256:
  `ac0d7a4e5ce7e436ed1ef12739a1947cf1f2f8aeb58e2b6272f9176497f27f2f`.
- Corrected candidate C/D byte equality; report SHA-256:
  `2e102ab7ca0529ab3fa2c44a78e86d8a1f4842e4418acd2ea9b61b812868933e`.
- Generated-private tree SHA-256:
  `1ddab7e07bc227d04f913f091449c025736c67e8180c07947379a3f9e5d45c25`.
- Staged-public tree SHA-256:
  `a8dd2efeeb66d47d7f9493aa97bdeaa946876019ac094e46982dfd1fbb177cb0`.
- Focused Batch 23 tests: **9 passed**.
- Complete corrected backend suite: **1,454 passed, 3 skipped, 1 warning**.
- Frontend production build: **1,694 modules**, passed after correction.
- `git diff --check`: repeated at the final gate.

## Real consumer path

- Corrected isolated cumulative catalog: exactly **230** artifacts, Batches 01–23.
- Availability: **85 available / 136 conditional / 9 unavailable**.
- Publication: **221 review-required / 9 withheld**.
- Artifact-tree SHA-256:
  `50f3d7fa30781f592a703df6a4d6e1666016e57634c29a3591732a9980ee0a82`.
- Manifest SHA-256:
  `fcff37e4dbf0dd90349732e8c5248e66fc3bc1442363dd15ed47dddb304cdcab`.
- Real localhost FastAPI: list 230; detail 230/230; calculator GET/default parity 230/230;
  221 numeric POST 200; 9 unavailable POST 400; corrected Batch 23 staged/catalog parity 10/10;
  private leaks 0.
- API receipt SHA-256:
  `7be2cd2c4c2eb1b3bb9a4fc77f2528ac653da3816b84895421c0d7eb652027eb`.
- Arelle remained outside the serving process. The isolated server was stopped after verification.

## Protected state and confirmation gate

- Tracked catalog tree:
  `38efe664dc981e9d2383ece43b66e9ae326b4b9a7cc2443f2463498432ef66a8`.
- Frontend public-data tree:
  `353a14bc672002e88d248811f98d23d4c1fb47cf28e526d969f463f256260274`.
- Generated research tree:
  `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
- Recovery Learning Watchlist is **145** (136 Conditional / 9 Withheld), SHA-256
  `5d1f85996b3057160a7a074f4ead1ba62b6ca45e2b232339fe496d33da8c9845`.
- Automatic-withheld history remains **19**, SHA-256
  `28bcfdd2985f3f3d87320e9e780aac630923510d0e46c614d9cfb5035e19f3ec`.

The user replied `y` on 2026-08-31. AME, CHRW, FDX, PWR, URI, AXON, UPS, and LDOS were added as
direct Conditional entries with `recovery_outcome=not_applicable`; RSG and LII remain outside the
watchlist as Pass issuers. Because Withheld is 0/10, no recovery phase is needed. Batch 24 was not
started; the next valid signal is `Start Universe Reset Batch 24`.
