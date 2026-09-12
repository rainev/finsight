# Controlled Universe Reset Batch 42 Result

Date: 2026-09-07
Status: verified initial result; accepted through explicit recovery authorization.

## Exact outcomes

Exactly ten frozen issuers were processed at valuation date 2026-08-14.
Pass **0/10**, Conditional **8/10**, Withheld **2/10**, numeric **8/10**.
All numeric results are capped at Low reliability.

| Ticker | Outcome | Bear | Base | Bull | Reliability |
| --- | --- | ---: | ---: | ---: | --- |
| PPG | Conditional | $7.14 | $48.47 | $92.60 | Low |
| SLB | Conditional | $17.44 | $35.60 | $56.40 | Low |
| SHW | Conditional | $41.86 | $114.39 | $193.01 | Low |
| CVX | Conditional | $44.19 | $119.70 | $216.10 | Low |
| OXY | Conditional | $0.66 | $33.39 | $88.19 | Low |
| EOG | Conditional | $63.28 | $133.00 | $202.04 | Low |
| FCX | Conditional | $0.00 | $3.44 | $15.60 | Low |
| CRH | Conditional | $10.63 | $37.79 | $66.47 | Low |
| EXE | Withheld | — | — | — | — |
| ALB | Withheld | — | — | — | — |

These are conservative baseline decision ranges, not predictions, market-price targets, or recommendations.

## Source and model decisions

All ten controlling filings are cutoff-safe 10-Qs for 2026-06-30. Numeric issuers use eight-year enterprise
cash-FCFF with source-linked company history, issuer-specific cycle scenarios, current cash/debt/claims and the latest
cutoff-safe common-share denominator. H1 weighted diluted shares are diagnostic only; a transparent +/-1.5% share
stress represents unresolved dilution.

- **PPG:** reported short-term investments are included with cash; long-term investments remain excluded. NCI is a
  permanent claim, while pension/environmental balances are a bear-only stress to avoid deducting operating cash twice.
- **SLB:** ChampionX is within the current company. EOG-style activity/capex cyclicality is not used; SLB keeps its
  oilfield-services history, NCI and acquisition/integration uncertainty.
- **SHW:** current PP&E/productive-asset cash capex is source-linked. Environmental accrual plus possible additional
  loss is a bear-only stress; no Suvinil purchase value is added.
- **CVX:** Hess/current integrated-energy cash history is normalized across commodity cycles. NCI remains a bridge
  claim; pension is a bear-only operating stress. Restricted cash and projected synergies are excluded.
- **OXY:** debt/finance leases and the reported $8.287B preferred claim are deducted in every scenario. ARO,
  environmental accrual and the finite additional-loss range are bear-only stresses. Discontinued-operation gains are
  not treated as recurring cash.
- **EOG:** the current FCFF line uses `InterestExpense`, not cash interest paid. Oil-and-gas plus other PP&E capex is
  summed exactly. ARO is a bear-only stress; derivatives and future contract volumes are not bridge assets.
- **FCX:** annual capex uses productive-asset cash payments and current H1 capex uses the exact $2.077B dimensional
  long-lived-asset sum. Interest expense, net is kept on one concept lineage. NCI is deducted in every scenario;
  environmental/closure obligations are a bear-only stress. The negative raw bear is retained privately and the public
  bear uses an explicit limited-liability floor of $0.
- **CRH:** five annual periods support the construction-materials cycle range. Debt, finance leases, NCI and redeemable
  NCI are reconciled once; pension/ARO are bear-only stresses. Arcosa and its pending financing are excluded.

## Plain withheld reasons

- **EXE:** only one complete annual period exists for the current combined Expand Energy object. The corrected June TTM
  is positive, but one annual observation plus a pending Twin Eagle transaction cannot establish a defensible gas-cycle
  range without inventing a history.
- **ALB:** the five-year reported cash-FCFF median remains negative. Current TTM cash is positive but is materially
  affected by Talison dividend and working-capital timing, while Ketjen changed the company perimeter and the mandatory
  convertible still needs a point-in-time conversion reconciliation.

## Independent challenge and repairs

Two Luna High reviewers independently challenged the source and model halves of the batch. Sol repaired the original
candidate by withholding EXE, correcting EOG/EXE interest concepts, replacing H1 average shares with current shares,
including PPG short-term investments, and separating fixed NCI/preferred claims from bear-only operating-liability
stress. The final E/F candidate has no unresolved Critical or Important finding.

One non-blocking metadata limitation remains: public `bridge_quality.intrinsic_value_range` describes the exact base
bridge rather than the wider valuation scenario range. The public `scenario_range` is the controlling bear/base/bull
range and is correct.

## Determinism and verification

- Final candidates: `output/batch-42-history-run-g-20260907` and
  `output/batch-42-history-run-h-20260907`; all 21 files are byte-identical and bind the confirmed Batch 41 recovery
  bookkeeping hashes.
- Candidate tree SHA-256: `e640d2966d6ab524e7f6308059947785be984710ef23334916cd2629dbd2fc11`.
- Report SHA-256: `c56561c2414cb8a44d4230720a303cd508b2869667c825efec671cb54c5e16f1`.
- Focused Batch 42 plus public-contract tests: **95 passed, 3 skipped, 1 warning**.
- Frontend production build: passed, 1,694 modules.
- Standalone real API: ten list/details, ten calculator GETs, eight numeric calculator POST 200s, two withheld POST
  400s, exact detail parity, zero private leaks and zero forbidden serving imports.
- Standalone calculator receipt SHA-256: `32f22115e2f771ca9135bead722a2b4afce1e51f6e3b102ee417cfee5f17db12`.
- Standalone exact API receipt SHA-256: `5782c2ca496b9ac60663ac877446f4a11d3cca279572a846c9c88ec127881c63`.
- Complete backend regression: **1,695 passed, 3 skipped, 1 warning** (220.80 seconds). The warning is the existing
  Python `crypt` deprecation in passlib.
- Cumulative catalog: 420 companies — 116 available / 287 conditional / 17 unavailable; 403 review-required / 17
  withheld.
- Catalog artifact-tree SHA-256: `d6f5bf803660be1fd1db802c015b4b9c3702b7880381a46aae8f406c437d202e`.
- Catalog manifest SHA-256: `7dea8f4ef6b1bc98454e060a3b7f34d794f0f1316b1b4229ca494c7b78f38aa5`.
- The cumulative catalog exactly preserves all 410 confirmed predecessor artifacts and exactly copies all ten Batch 42
  staged public artifacts; every referenced audit path resolves.
- Real cumulative API: 420 list entries, 420 detail/calculator GETs, 420 expected calculator outcomes, exact list/detail
  parity, zero private leaks and zero forbidden serving imports.
- Cumulative calculator receipt SHA-256: `0774e4038d8b765275db7076ac709a953335cdd2d4080743bc4e3042f3f6cf71`.
- Cumulative exact API/import receipt SHA-256: `edc9585637938b8f6f1aaaab71030b52c402e69ddcbffe93026e5bfa68028f9e`.

## Cumulative confirmation boundary

Batch 41 and its APD/IFF/IP recovery are user-confirmed. The confirmed predecessor has 410 companies: 116 Pass / 279
Conditional / 15 Withheld. The verified Batch 42 candidate would produce 420 companies: 116 Pass / 287 Conditional /
17 Withheld, with numeric coverage of 403/420.

The confirmed Recovery Learning Watchlist remains at 294 entries and the cumulative withheld register remains at 25
entries until the one-attempt recovery outcome is confirmed. The user explicitly authorized EXE/ALB recovery after this
result, which records acceptance of the initial Batch 42 state without authorizing bookkeeping or promotion. Tracked
serving artifacts are unchanged. Batch 43, merge, push and deployment remain untouched.
