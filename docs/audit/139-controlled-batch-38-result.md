# Controlled Universe Reset Batch 38 Result

Date: 2026-09-07
Status: verified initial result; user confirmation recorded.

## Exact outcomes

Exactly ten frozen issuers were processed at valuation date 2026-08-14.
Pass **0/10**, Conditional **8/10**, Withheld **2/10**, numeric **8/10**.
Every numeric result is capped at Low reliability. These are conditional operating/insurance
baselines, not forecasts that bound every legal or transaction outcome.

| Ticker | Outcome | Bear | Base | Bull |
| --- | --- | ---: | ---: | ---: |
| EG | Conditional | $258.10 | $419.08 | $582.27 |
| GPN | Withheld | — | — | — |
| PFG | Conditional | $36.48 | $59.04 | $81.82 |
| FIS | Conditional | $0.00 | $6.22 | $36.69 |
| PRU | Conditional | $57.60 | $93.65 | $130.12 |
| WTW | Conditional | $59.44 | $147.14 | $257.11 |
| MA | Conditional | $134.71 | $212.15 | $304.43 |
| CME | Conditional | $88.57 | $137.89 | $189.49 |
| CPAY | Withheld | — | — | — |
| AIZ | Conditional | $87.44 | $142.84 | $200.21 |

## Model and source decisions

- EG/PFG/PRU/AIZ use five-year parent/common-equity residual income. Five annual earnings
  observations plus current TTM constrain governed ROE/payout/discount/terminal scenarios.
  Policy liabilities and subsidiary/client assets stay inside equity economics. NCI is not
  deducted twice from parent equity. Current share counts come from the controlling filing.
- PRU's common earnings reconcile as consolidated profit less NCI and participating earnings:
  H1 $1.642B − $60M − $21M = $1.561B. The filing's Japan suspension forecasts are $525–575M
  pre-tax for 2026 including $235M in H1, and $400–450M for 2027. The chosen 5%/8%/11% ROEs are
  already below both stressed earnings ceilings. This is a nonbinding check, not a second
  deduction or a claim that the unquantified reimbursement tail is bounded.
- GPN's January Worldpay acquisition and Issuer Solutions disposal mean old standalone history
  cannot be treated as a comparable combined year. Reported post-close H1 OCF $373.798M less
  $497M capex is negative before interest addback. A governed annualized FCFF stress, after the
  $22.418326B debt/finance-lease bridge, yields raw per-share residuals approximately
  −$67.15/−$54.67/−$39.25. Only the filing's $1.6979B available cash is included; settlement cash,
  merchant reserves and customer funds are excluded. No positive base is supported in this initial
  replay. Recovery requires source-backed sustainable integration cash economics.
- FIS uses post-January combined H1 annualization, explicitly an assumption rather than a complete
  comparable year. H1 continuing OCF $1.207B less PP&E $76M and software $441M gives $690M before
  after-tax interest addback. Legacy annual/TTM history remains diagnostic. The model includes
  $21.174B borrowing and reserves the net settlement-funding gap. Bear residual is below zero;
  its public zero is a limited-liability floor, with the negative value retained privately.
- Mastercard cash FCFF deducts PP&E and capitalized software across annual and TTM periods.
  Available cash/securities are $11.291B + $318M less $788M net settlement funding. Debt is
  $24.643B. The $296M recorded litigation accrual is charged once; unquantified legal outcomes
  remain outside the operating range with an explicit warning.
- WTW has three usable annual cash histories. Fiduciary client funds are excluded from available
  cash. The full $642M pension liability is conservatively reserved alongside ordinary operating
  pension cash; potential overlap is disclosed. The July Propel plan's $625M cash cost is discounted
  over three governed equal annual payments. Its $25M noncash cost and projected $350M net annual
  savings are not added as cash costs or benefits.
- CME cash and investments are $2.2756B, and debt plus finance leases $3.4705B. Its $158.1107B
  performance-bond/guaranty assets equal the corresponding liabilities and are excluded from
  issuer cash. The August pricing notice is qualitative context; no unsupported revenue uplift
  is assumed. The current diluted share denominator reflects the completed preferred conversion.
- CPAY's H1 $1.570343B cash inflow combines accounts payable, accrued expenses and customer
  deposits. The filing shows $8.915786B customer deposits and $7.004803B restricted cash, but
  does not identify the customer-funding share of that pooled flow. The unknown component stays
  null. A financing-aware recurring-cash or equity model is required before numeric publication.
  FTC proposed settlement, pending Maintenance sale and July performance grants remain in the
  event evidence; this initial pass consumes no recovery attempt.

## Challenge and verification

Luna High implemented and source-checked the four insurer models; Luna xhigh independently
reviewed the other operating/withheld results, event documents and calculator responses, and
checked the insurer outputs. The primary agent reconciled findings against the captured filings.
Repairs include PRU participating earnings and explicit Japan stress-headroom treatment, complete
FIS/MA software capex, CPAY source-linked funding evidence, and stale withheld batch/horizon and
WTW history-count metadata. No remaining Critical or Important finding was identified in that scope.

Final artifacts: `output/batch-38-history-run-h-20260907` and `output/batch-38-history-run-i-20260907`.
Both complete trees are byte-identical (21 files, including all ten private artifacts). Report SHA-256:
`750d2d6ecce8f5ae2aff4fe49fcf3f8181adb2176d287a721d6e2fa2b90070f9`.

- Focused Batch 38, watchlist, withheld-register, and calculator tests: **21 passed** (including formula replay,
  software, customer funds, timed costs, missing facts, source tampering, exact calculator defaults, higher-discount
  sensitivity, and Batch 38 watchlist bookkeeping).
- Frontend build: passed, 1,694 modules. No UI behavior changed in this batch.
- Complete backend regression: **1,635 passed, 3 skipped, 1 warning** (211.45 seconds).
  The warning is the existing Python `crypt` deprecation in passlib.
- Real local API: 380 list entries, 380 successful detail and calculator GETs, 380 expected
  calculator outcomes (367 numeric defaults; 13 unavailable), exact list/detail parity, zero
  detected private leaks and zero forbidden serving imports. Test authentication and save=false;
  database persistence was outside this batch's verification scope.
- API receipt SHA-256: `09f086fcf94b350210b4630f6a49086ecb34eb194ad849eb066ef7be87c46864`.
- Exact API/import receipt SHA-256: `a7ad685aad9bbfd882c336582eb44dd3266abe688014d5700c879f662788d8b9`.
- Isolated 380-company catalog: 116 available / 251 conditional / 13 unavailable.
- Catalog tree: `d84fd2f6a9461e49a1b8c2dad9757752179d84e9feed97dee96bfa8a952f52aa`.
- Catalog: `output/batch-38-api-runtime-final-v3/US-RESET-2026-08-14-B01-B38-INITIAL-1.2`.
- Manifest SHA-256: `476080d94f331a3af059afbb80d35c588e8f74162702aae70d3d9596211a6060`.

## Confirmation boundary

This is the initial Batch 38 result, now confirmed by the user. The confirmed predecessor remains 370 companies:
116 Pass / 243 Conditional / 11 Withheld. The watchlist now has 262 entries (251 Conditional / 11 Withheld),
including the eight numeric Batch 38 companies; GPN and CPAY are intentionally not added until their one recovery
attempt is complete. Watchlist SHA-256:
`b92a6086d6df9020e117c81b24c2ad93a090981b16f85c99729894aed9264dd3`.
Cumulative withheld history remains 21 entries, SHA-256
`22fb28e93e84996d6b2fe1bd836d0cee3df746f3536aec26b57dfc1215751bb6`.
Tracked serving roots are unchanged. Recovery, Batch 39, merge, push, and deployment have not been performed.
The next authorized step is one recovery attempt for GPN and CPAY; after that, any still-withheld names will be
added to the cumulative withheld register before Batch 39 is considered.
