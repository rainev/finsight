# WG37 — HON closing agreements and continuing-company reconciliation

Started 2026-09-18 after WG36 narrow gate user confirmation. Explicit public SEC
authorization covered HON 8-Ks `0000773840-26-000084` and
`0000773840-26-000120` plus directly linked separation, contract, pro forma and
financial exhibits. The supplied contact was used only for SEC fair-access.
This is a source/economic reconciliation gate, not a completed HON refresh.

## Acceptance status

| Item | Result |
|---|---|
| Exact filing and directly linked relevant exhibit capture | VERIFIED; CONFIRMATION PENDING |
| Offline deterministic replay and protected-serving hashes | VERIFIED; CONFIRMATION PENDING |
| Pro forma balance/history and current HON-only cash extraction | VERIFIED; CONFIRMATION PENDING |
| Separation/intercompany/trademark terms kept nonadditive | VERIFIED; CONFIRMATION PENDING |
| One current post-close HON cash/debt/NCI/FCFF bridge | BLOCKED — source does not provide it |
| Frozen workers, independent challenge, regression and API | VERIFIED; CONFIRMATION PENDING |

## Source capture

The first network capture correctly retrieved both primary filings but exposed
that SEC filing-index `type` values are MIME icons, not exhibit types. That
incomplete receipt is preserved. The corrected reusable capture follows actual
primary-document links and admits only Exhibit2/10/99 roles. It captured2/2
filings and9 documents. Exhibit3.1, XBRL dependencies and static assets are
outside this explicitly relevant exhibit scope; no complete-package claim is made.

Canonical/offline replay report SHA256
`e4e6a85880b3ba435762cde91e218ccac56106f1d1a0f3ea099af820d5bc4e42`;
bytes identical. Protected serving hashes unchanged.

| Document | SHA256 |
|---|---|
| June primary 8-K | `b5a195314fa5a0be04873c05755d2ede1aef87d04d41bff20377fddb281c1aa0` |
| Separation agreement | `8935fd51f304dc26bd2013246beae6551cc810d36e2db810b9a12832a7e77a3f` |
| Tax agreement | `af157bbdd58ea3225cee8d346dcb1d1bd679dd5bb1c1562d24a720d796fa7fd0` |
| Trademark agreement | `39372cd6500ee4be46deca887d6e2ba31811649274ccdd0e9592186235ad7a2b` |
| June release | `d80bb0fca8118b11fa33e8a0969e4969de35d434f94b3b48938d3e22c9c5167b` |
| June supplemental | `3c25c031c9e3dc7b9f3679720396d67faa1b0a9e3440ca0af4f9a1942a5033bf` |
| Pro forma financials | `e7b3ee85d9c646205c115af8febe1fae0f0a894591af6884e076a3f82e14bae6` |
| July primary 8-K | `d48c97b4607d3356d24cb4f126a3a07d3f9ac1a1b312c178bd3c5a68e112d817` |
| July earnings release | `cc6c875b63b931365efd3498c7dad62e2424a36b80517c33f01f6ade376c86f9` |

## Exact evidence and financial meaning

March31 pro forma continuing HON balance sheet:

| Field | Amount |
|---|---:|
| Cash / short investments | 10,977M / 413M |
| Cash plus short investments | 11,390M |
| Short borrowings / current debt / long debt | 4,630M / 3,094M / 13,164M |
| Total interest-bearing debt | 20,888M |
| Parent equity / NCI | 16,693M / 973M |
| Total assets and liabilities/equity | 52,879M |

This balance is illustrative March31 pro forma, not actual post-June29 or
post-July17 balances. The filing explicitly says it is not a complete presentation
and actual results may differ materially.

Continuing pro forma history binds revenue / interest / parent net income:
2023 `19,407 / 582 / 1,236M`; 2024 `19,281 / 797 / 1,302M`; 2025
`19,945 / 788 / 1,368M`; Q1 2026 `4,823 / 232 / 120M`. It contains no pro forma
cash-flow statement and its shares are not used as the current split-adjusted
denominator.

July release HON-only Q2 evidence: revenue5,187M, operating income662M,
continuing OCF563M, capex187M, separation-cost payment addback49M,
Quantinuum addback31M, adjusted FCF456M. Management's FY2026 guidance:
revenue19.8–20.0B, OCF1.9–2.2B, capex600M, separation addback400M,
Quantinuum addback100M, adjusted FCF1.8–2.1B. Guidance includes Johnson Matthey
and expected PSS/WWS divestitures. Adjusted FCF is not enterprise FCFF and the
event funding/proceeds are not reconciled.

Pro forma transaction notes bind estimated HONA retained cash1B, additional
nonrecurring-cost accrual243M,6B distributed notes,9.1B distributed cash and13B
HON third-party debt repayment. These are dated transaction components, not a
current bridge. Separation agreement requires intergroup accounts to be settled,
contributed, cancelled or extinguished but gives no amount. Schedules with numeric
asset/liability allocation are omitted.

Agreement range: Aerospace cash distribution15.1B plus up to1.5B, exact total
unknown. Trademark schedule:1.125B =18.75M upfront +59 monthly18.75M payments;
actual receipts/tax/forecast overlap remain unbound. Neither is added to cash or
intrinsic value.

## Current result

The evidence provides multiple honest but incompatible surfaces: March pro forma
balance, continuing historical earnings, adjusted Q2 cash, guidance with future
transactions, and pre-event June balance facts. No current post-close cash,
debt, NCI, intercompany settlement, Johnson Matthey funding/acquired FCFF or
divestiture proceeds tie them together. `continuing_fcff`, current bridge fields,
`acquired_fcff`, claim adjustment and numeric successor remain None/false.

| Company | Historical low / base / high | Change | Result |
|---|---:|---:|---|
| HON | 60.78533467481803 / 149.61398945604896 / 277.0528047042256 | 0 / 0 / 0 | Implementation gap; no current successor |
| HCA control | 113.67603706327972 / 341.89411295994046 / 666.5180777852703 | 0 / 0 / 0 | Existing runoff blocker preserved |

Both remain Low historical estimates. Exact historical parity is not current
post-event valuation approval.

Private runtime receipt `output/us-refresh-runtime/separation-event-evidence/HON.json`,
file SHA256 `adea7c453ddd99d67e16348c714da5b891e6ee63a954f0a6c89d0f7ad0a441e8`,
internal receipt `f0ad9c6ce5b40ae3b198d60487e2889986a929da5226b467422c756854e944c2`,
version `FINSIGHT-SEPARATION-EVENT-EVIDENCE-WG37-3`.

Frozen two-worker report
`output/us-refresh-group-verification/32c4f5eda55ae0008c624347e96459e9b8a244013605bc3231ccdeef78292db5/report.json`,
file SHA256 `e78c260507a05a6dbfa2735e283d103e912084a505c2103ecf8a983fe23f428a`;
implementation `bf149b2ec7650289eaa3ae164e9bdcd1b99b3063ee3572949d0fc6554cf5b64e`,
policy `4430283635f0f4914caf61a7a973281f833b17fb3cc02465eac02e8709bacf74`.
Repeated bytes identical. Focused36 pass; independent final9 pass and no material
defect. Final broad811 pass, one existing Passlib crypt warning,266.21s. See
[independent review](wg37-independent-review.md). Isolated real API receipt
`output/us-refresh-runtime/wg37-blocked-preservation-api-evidence.json`, SHA256
`2485fac105ab8df4ce84104d8963768844c15339ab43251c5327c0039b243fce`;
runtime passed440-record and six-company detail/calculator parity. No UI
or save behavior changed, so browser/new saved-run checks are not repeated.

Final register:440 companies,419 recipes,282 compiled instructions,137 coding
gaps,196 financial flags,168 source flags,434 needing current-version recheck,
21 prior unavailable,0 current full numeric source-bound and0 successive-period
proofs. Flags overlap and source reports are not composable release evidence.
Register JSON SHA256 `0977d31b682341cc8c21053daaca9cc1fdc1500c0afc5ea48e8213a1935849c5`.

## Following group, not started

The cutoff-safe source set is exhausted for a true current post-close HON balance.
A future post-separation filing with Johnson Matthey allocation and divestiture
proceeds is required. Do not keep combining dated surfaces or invent a bridge.
The next source-supported shared mechanism is pharma contingent consideration/
CVR and paid-cash overlap. WG38 should inspect BIIB, GILD and INCY, retaining only
companies whose actual filings prove the same mechanism. No later group starts
under WG37 authorization.
