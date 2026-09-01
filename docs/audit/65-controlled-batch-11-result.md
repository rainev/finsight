# Controlled Universe Reset Batch 11 Initial Result

Status: **user confirmed on 2026-08-28**. Exactly the ten frozen Batch 11
issuers were processed at the 2026-08-14 valuation date. No recovery, Recovery Learning
Watchlist or cumulative-withheld-register mutation, serving promotion, Batch 12 work, merge,
push, or deployment was performed.

## Result

- Pass: **2/10** — MO, MNST
- Conditional: **6/10** — CHD, COST, DLTR, MDLZ, PM, KHC
- Withheld: **2/10** — SYY, BG
- Numeric: **8/10**, all Low reliability
- Cumulative after 110 processed issuers: **47 Pass / 57 Conditional / 6 Withheld**
- Cumulative numeric coverage: **104/110**
- Recovery Learning Watchlist: **55**, unchanged at the initial-result stop

| Ticker | Outcome | Low | Base | High | Reliability | Controlling filing / period |
| --- | --- | ---: | ---: | ---: | --- | --- |
| SYY | Withheld | — | — | — | — | `0000096021-26-000022` / 2026-03-28 |
| CHD | Conditional | $34.94 | $59.71 | $87.54 | Low | `0001193125-26-327567` / 2026-06-30 |
| MO | Pass | $28.80 | $47.15 | $80.68 | Low | `0000764180-26-000094` / 2026-06-30 |
| MNST | Pass | $25.04 | $36.75 | $53.88 | Low | `0001104659-26-092193` / 2026-06-30 |
| COST | Conditional | $227.82 | $332.88 | $478.86 | Low | `0000909832-26-000051` / 2026-05-10 |
| DLTR | Conditional | $45.24 | $71.38 | $111.70 | Low | `0000935703-26-000065` / 2026-05-02 |
| MDLZ | Conditional | $13.91 | $26.32 | $42.03 | Low | `0001628280-26-050179` / 2026-06-30 |
| PM | Conditional | $57.85 | $97.25 | $147.54 | Low | `0001628280-26-049493` / 2026-06-30 |
| KHC | Conditional | $8.88 | $21.83 | $38.45 | Low | `0001637459-26-000054` / 2026-06-27 |
| BG | Withheld | — | — | — | — | `0001628280-26-050540` / 2026-06-30 |

Values are USD per-share baseline decision ranges, not predictions or recommendations. Pass
means the source identity, current bridge, model, and history are complete enough for an ordinary
source-bounded baseline. Conditional identifies a named material dependency; Withheld means no
coherent economic object or source-bounded positive baseline was available.

## Source and cache gate

The frozen Batch 11 manifest is SYY, CHD, MO, MNST, COST, DLTR, MDLZ, PM, KHC, and BG. Its
SHA-256 is `c8f0828438cc4bf94d8244d8192baa8d1be897917b4ac02bda70e54e57c96dfe`,
matching the frozen partition receipt.

- Reused pre-existing complete SEC packets: MO, COST, MDLZ, PM.
- Fetched only after cache preflight: SYY, CHD, MNST, DLTR, KHC, BG.
- Replayed all ten from the completed local cache with zero network fetches.
- Source packet A/B tree SHA-256: `0779e65e55e20f5eb71b4de0cdbfe623a463a6543c4a49f3e6128648555788bd`.
- Reused pre-existing structural packages: MO, COST, MDLZ, PM.
- Captured and parsed missing packages: SYY, CHD, MNST, DLTR, KHC, BG.
- Structural parsing: 10 attempted / 10 parsed / 0 failed.
- Structural A/B tree SHA-256: `1965d0b740593c499c47d57d9fe2758ef1425d8f9e3b2d53fffcc0dddde8e523`.
- All 30 source-packet/package/structural hashes in the ten source receipts reconcile.
- All controlling filings were filed by 2026-08-14. SYY's 2026-08-21 10-K and DLTR's
  2026-08-27 10-Q remain future and were not selected.
- Protected serving hashes stayed unchanged.

The first structural attempt used the default Python runtime and failed after package capture
because it lacked Arelle. The corrected runs used the pinned Python 3.11 / Arelle 2.44.0 runtime,
reused the complete partial cache, embedded filed/report dates, and wrote fresh immutable outputs.

## Outcome decisions and important treatments

- **SYY Withheld:** the signed Jetro Restaurant Depot transaction requires approximately $21.6B
  cash and 91.5M Sysco shares, backed by a $22B bridge facility, within $29.1B expected
  consideration. The ledger also binds a $1.164B termination fee, $473M European commercial
  paper, and $85M supplier finance. No filed post-close/termination cash-flow, debt, and share
  object exists.
- **CHD Conditional:** the bridge includes $14.6M contingent consideration. Current acquisition
  evidence includes $300M business-acquisition cash, a $180.5M acquisition-liability payment,
  $300M and $656M acquired-brand/Touchland prices, and $111.9M supply-chain finance. A full
  comparable acquired-business cash history is not available.
- **MO Pass:** $24.577B debt and $50M NCI reconcile. The $8.896B ABI/Cronos investment is not
  added again because $186M H1 distributions are inside OCF. The $1.169B settlement payable
  remains operating because H1 OCF includes a $1.009B payable reduction and history includes
  recurring settlement cash. $171M supplier finance remains in accounts payable/OCF.
- **MNST Pass:** $2.192424B cash plus $2.008146B complete AFS securities are counted once;
  controlling-filing structure proves no interest-bearing debt or other equity claim. Owner cash
  is OCF less capex without a fabricated interest addback.
- **COST Conditional:** $18.946B cash plus $1.050B investments and $5.670B balance-sheet debt
  reconcile. The filing reports $57M finance-lease principal payments and $116M new finance-lease
  ROU assets without a liability point, so bear/base/bull claims include a governed
  $57M/$28.5M/$0 reserve.
- **DLTR Conditional:** current OCF is continuing-operations cash. The $793M completed Family
  Dollar consideration is source-bound, while transition services, guarantees, disposal
  adjustments, and the shorter three-year comparable history remain material. $298.4M supplier
  finance and $4.6607B operating leases remain post-rent operating items.
- **MDLZ Conditional:** the latest FY plus current H1 minus prior H1 reconstruction fixes the
  stale Companyfacts period and yields a 2026-06-30 TTM object. Cash, $21.450B debt, $53M NCI,
  and $2.9B accounts-payable supplier finance reconcile. Cocoa/commodity cash conversion remains
  load-bearing.
- **PM Conditional:** the bridge includes $3.341B short-term borrowings plus $45.772B
  current/noncurrent debt and capital leases, totaling $49.113B, plus $1.926B NCI. The $1.008B
  equity-method stake and $17M investing-cash distributions are not fully integrated into FCFF,
  so the result is not a Pass. $1.0B supplier finance remains accounts payable/OCF.
- **KHC Conditional:** $2.681B cash/investments, $19.001B debt, and $124M NCI/redeemable NCI
  reconcile. The ledger binds $7.365B H1 impairment; repeated impairment, restructuring,
  portfolio actions, and leverage remain material.
- **BG Withheld:** the $10.617B Viterra combination and current bridge are source-bound, but no
  three-period comparable combined cash history or complete filed pro-forma cash bridge exists.
  Current combined cash is negative; no positive midpoint was manufactured.

MO and PM required explicit interest-magnitude reconstruction because their annual
`InterestExpense` facts are positive while current/prior H1
`InterestIncomeExpenseNonoperatingNet` facts are negative. The final TTM expense magnitudes are
$1.193B and $1.549B respectively.

## Independent challenge

Three independent Luna XHigh reviewers challenged disjoint scopes: source/cutoff/period/unit/
shares/bridge evidence; economic model and outcome classification; and arithmetic/sensitivity/
public-safety mechanics. The final verdict from all three is **PASS with no remaining Critical or
Important finding**.

Resolved findings included the SYY transaction hard stop, CHD acquisition and contingent-claim
scope, COST finance-lease reserve, PM short-term debt and affiliate classification, MO/PM mixed
interest signs, issuer-level supplier-finance treatment, MO settlement cash, and stale unavailable
metadata. All 24 numeric scenarios replay exactly; higher cash/FCFF raises value, while higher
WACC, debt, lease/claim reserves, or shares lowers value.

Remaining Minor caveats are explicit: structural top-level period diagnostics can be malformed
and are never used for selection; some structural rows carry accession while filing dates remain
in the bound receipt/package; COST's lease reserve is policy-bounded rather than a reported
liability; and public scenario/sensitivity arrays remain empty while private scenario rows contain
the verified directions.

## Determinism, tests, build, and real API

- Final candidate-o/p full tree SHA-256: `40fa8eb3e8d52b95809634ff3f55c464529fe98a687e6a788c1f450777c3978c`.
- Generated-private tree SHA-256: `5c9036ebcab127e032ce5cf53d5f1935d9cf87c5586047733706472df84ea5d3`.
- Staged-public tree SHA-256: `18973adf2be9398e54d6ac747b795fd3b413d1d4dd55a1ad9579403336400f45`.
- Focused Batch 11 tests: `9 passed`.
- Full backend suite: `1,330 passed, 3 skipped, 1 warning`.
- Frontend production build: passed (`1,694` modules transformed).
- Isolated API catalog artifact tree: `2100bfb09f396471b702f432ac070b4a00b4242873668bcdea4e6bce6e1e43e7`.
- Real localhost FastAPI list: HTTP 200, exact count 10.
- Detail parity: 10/10 HTTP 200 and exact staged-public equality.
- Calculator GET parity: 10/10 HTTP 200; 8 enabled and 2 fail closed.
- Calculator POST with `save=false`: 8/8 numeric HTTP 200 with exact base parity; SYY/BG
  return HTTP 400 and remain unavailable.
- Private leaks: 0.
- API receipt SHA-256: `d50fd0c67a7fda13042a8872fabec303140f1a00e67c409b97f3be3a314f6a64`.

The real API used an isolated untracked catalog and the documented local current-user dependency
override. It verifies the valuation routes and calculator behavior, not real authentication,
Postgres persistence, MinIO, or save behavior. Startup reported the expected unavailable local
MinIO warning; all valuation checks passed.

The documented `PYTHONPATH=backend pytest` command could not collect the catalog test because the
pytest entrypoint did not expose the repository's `scripts` package. The executable focused and
full commands used `PYTHONPATH=backend:.`; both passed. The failure is retained here rather than
hidden.

## Confirmation gate

The user confirmed the initial Batch 11 result on 2026-08-28 and subsequently authorized the
single SYY/BG recovery attempt recorded in Audit 66. This initial result remains immutable
comparison evidence. Do not promote or activate a tracked serving catalog, start Batch 12, merge,
push, or deploy without a separate user signal.
