# Controlled Universe Reset Batch 22 Initial Result

Status: **firsthand verified and user-confirmed on 2026-08-31**. Exactly the ten frozen Batch 22
issuers were processed at the 2026-08-14 valuation date. Confirmation added the three Conditional
issuers to the Recovery Learning Watchlist. No recovery, withheld-history mutation, tracked serving
promotion, Batch 23, merge, push, or deployment was performed.

## Outcome

- Pass: **7/10** — WM, IEX, ODFL, CPRT, LMT, ROK, FIX
- Conditional: **3/10** — HON, JCI, WAB
- Withheld: **0/10**
- Numeric: **10/10**
- Reliability: **10 Low / 0 Medium / 0 High**
- Cumulative through 220 issuers: **83 Pass / 128 Conditional / 9 Withheld**
- Cumulative numeric coverage: **211/220**

These are transparent baseline decision ranges, not market predictions or recommendations. Ordinary
bounded business risk remains a Pass. Conditional is reserved here for a named separation,
incomplete comparable history, or partial-period acquisition state.

| Ticker | Outcome | Low | Base | High | Simple reason |
| --- | --- | ---: | ---: | ---: | --- |
| HON | Conditional | $60.79 | $149.61 | $277.05 | Full current filing is finite; pending separation perimeter/funding can change the continuing company |
| WM | Pass | $15.87 | $65.59 | $151.14 | Complete post-Stericycle fiscal year and complete debt/lease bridge |
| IEX | Pass | $74.04 | $120.81 | $189.48 | Stable five-year industrial cash history and complete bridge |
| JCI | Conditional | $0.00 | $18.65 | $59.10 | Only two comparable annual cash periods plus current restructuring/impairment |
| ODFL | Pass | $30.55 | $44.75 | $83.24 | Five-year freight-cycle history, direct interest lineage, and minimal debt |
| CPRT | Pass | $15.82 | $24.57 | $40.12 | Four-year auction cash history, debt absence, redeemable NCI, and share sensitivity |
| LMT | Pass | $235.77 | $417.62 | $728.19 | Five-year defense history retains prior program losses; current program-loss fact is zero |
| WAB | Conditional | $41.43 | $110.65 | $192.78 | $1.062B H1 acquisition creates partial-period acquired cash history |
| ROK | Pass | $55.58 | $158.66 | $276.67 | Five-year automation-cycle history and complete short-/long-term debt bridge |
| FIX | Pass | $282.64 | $550.22 | $841.80 | Five-year construction cash history, current cash, small debt, and shares reconcile |

JCI's $0 bear value is a limited-liability floor after a deliberately weak cash scenario and the
full reported debt bridge; the private raw residual remains negative. It is not a missing value or
a zero substituted for unavailable data. JCI's base and bull values remain finite and positive.

## Controlling sources

| Ticker | Accession | Form | Filed | Report period |
| --- | --- | --- | --- | --- |
| HON | `0000773840-26-000124` | 10-Q | 2026-07-23 | 2026-06-30 |
| WM | `0001104659-26-088016` | 10-Q | 2026-07-29 | 2026-06-30 |
| IEX | `0000832101-26-000022` | 10-Q | 2026-07-29 | 2026-06-30 |
| JCI | `0000833444-26-000087` | 10-Q | 2026-07-29 | 2026-06-30 |
| ODFL | `0000878927-26-000023` | 10-Q | 2026-08-05 | 2026-06-30 |
| CPRT | `0001193125-26-245578` | 10-Q | 2026-05-29 | 2026-04-30 |
| LMT | `0001628280-26-049411` | 10-Q | 2026-07-23 | 2026-06-28 |
| WAB | `0001628280-26-049139` | 10-Q | 2026-07-22 | 2026-06-30 |
| ROK | `0001024478-26-000030` | 10-Q | 2026-08-04 | 2026-06-30 |
| FIX | `0001104659-26-086258` | 10-Q | 2026-07-23 | 2026-06-30 |

Honeywell's newer `0000773840-26-000127` 10-Q/A contains only its cover-page share fact. The full
10-Q therefore controls operating and balance-sheet evidence; the amendment remains supplemental
evidence rather than falsely replacing the financial statements. HON and ODFL use direct current
`InterestAndDebtExpense` lineage instead of declaring current history absent.

## Verification evidence

- Frozen manifest SHA-256:
  `1544cd049eaaea45e1c6472554495321dba0efbdc60353224e96595391fb27a8`.
- SEC packet tree SHA-256:
  `4427edd1283b557bb750d28c115e4fcb2747b0c2a7a1af44071c590c3c126809`.
- Corrected structural tree SHA-256:
  `479cab95feb3235cb48675b48fcd46257e034896912def2ae961bad7ea6d245f`.
- Candidate A/B full-tree equality; report SHA-256:
  `9d5f40892659d428ea43b4800a233acd9f47cb8403dbdceeee5a637dc9cf7ca6`.
- Generated-private tree SHA-256:
  `916da6417a7e2cc83a7c8743b9661c6035ae6baa01a31f201241b4eb7f8415d2`.
- Staged-public tree SHA-256:
  `7c7ca3b70308acee3b167929862b7631ed8ab26a313a1edd336d88deaa261d38`.
- Independent source/economic challenge: 10/10, **0 Critical / 0 Important**; receipt SHA-256
  `35fd0c28d4b38ce5fc5d2d59b5e147b15b86cada1794ba8867566b288bde0f72`.
- Independent test arithmetic rebuilt every eight-year faded-growth DCF, terminal value, EV bridge,
  equity floor, and per-share result without calling the production valuation function.
- Focused Batch 22 tests: **9 passed**.
- Complete backend suite: **1,445 passed, 3 skipped, 1 warning**.
- Frontend production build: **1,694 modules**, passed.
- `git diff --check`: passed before this report and is repeated at the final gate.

## Real consumer path

- Isolated cumulative catalog: exactly **220** artifacts, Batches 01–22.
- Availability: **83 available / 128 conditional / 9 unavailable**.
- Publication: **211 review-required / 9 withheld**.
- Artifact-tree SHA-256:
  `5aad2ab6a3f1638086704bbb329b451a338d9dca6c71cfd67d7b4b5fd823c167`.
- Manifest SHA-256:
  `b10dfa1f1644b68717080899b5c30844a2cbfeaf977b1def5d4490e0eb2e5e4c`.
- Real localhost FastAPI: list 220; detail 220/220; calculator GET/default parity 220/220;
  211 numeric POST 200; 9 unavailable POST 400; Batch 22 staged/catalog parity 10/10;
  private leaks 0.
- API receipt SHA-256:
  `d41a5b4d37b8e8273d710144c7d74ba8f57f4c92a3a8c453f47bde01c8796d10`.
- Arelle remained outside the serving process. The API used an isolated untracked catalog and
  `save=false`; the local server was stopped after verification.

## Protected state and confirmation gate

- Tracked catalog tree:
  `38efe664dc981e9d2383ece43b66e9ae326b4b9a7cc2443f2463498432ef66a8`.
- Frontend public-data tree:
  `353a14bc672002e88d248811f98d23d4c1fb47cf28e526d969f463f256260274`.
- Generated research tree:
  `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
- Recovery Learning Watchlist is **137** (128 Conditional / 9 Withheld), SHA-256
  `d4e5eda32c326f7e3ff010e768b2cf995a9f28ec1ea0d3ced8d6e4763be8dd23`.
- Automatic-withheld history remains **19**, SHA-256
  `28bcfdd2985f3f3d87320e9e780aac630923510d0e46c614d9cfb5035e19f3ec`.

The user replied `y` on 2026-08-31. HON, JCI, and WAB were added as direct Conditional entries with
`recovery_outcome=not_applicable`; all seven Pass issuers remain outside the watchlist. Because
Withheld is 0/10, no recovery phase is needed. Batch 23 was not started; the next valid signal is
`Start Universe Reset Batch 23`.
