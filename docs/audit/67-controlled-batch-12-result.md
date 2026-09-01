# Controlled Universe Reset Batch 12 Initial Result

Status: **firsthand verified; user confirmation required**. Exactly the ten frozen Batch 12
Health Care issuers were processed at the 2026-08-14 valuation date. No recovery, Recovery
Learning Watchlist or cumulative-withheld-register mutation, tracked serving promotion, Batch 13,
merge, push, or deployment was performed.

## Result

- Pass: **0/10**
- Conditional: **9/10** — ABT, BAX, BDX, BMY, RVTY, HUM, LLY, CVS, WST
- Withheld: **1/10** — UHS
- Numeric: **9/10**, all Low reliability
- Cumulative after 120 processed issuers: **47 Pass / 67 Conditional / 6 Withheld**
- Cumulative numeric coverage: **114/120**
- Recovery Learning Watchlist: **63**, unchanged at the initial-result stop

| Ticker | Outcome | Low | Base | High | Reliability | Controlling filing / period |
| --- | --- | ---: | ---: | ---: | --- | --- |
| ABT | Conditional | $20.75 | $42.13 | $68.16 | Low | `0001628280-26-050134` / 2026-06-30 |
| BAX | Conditional | $0.00 | $6.87 | $23.60 | Low | `0001628280-26-051118` / 2026-06-30 |
| BDX | Conditional | $37.78 | $89.98 | $161.39 | Low | `0000010795-26-000035` / 2026-06-30 |
| BMY | Conditional | $39.97 | $60.49 | $95.54 | Low | `0000014272-26-000020` / 2026-06-30 |
| RVTY | Conditional | $17.05 | $39.34 | $73.53 | Low | `0000031791-26-000027` / 2026-07-05 |
| HUM | Conditional | $49.06 | $124.31 | $254.86 | Low | `0000049071-26-000050` / 2026-06-30 |
| LLY | Conditional | $41.47 | $149.70 | $279.32 | Low | `0000059478-26-000081` / 2026-06-30 |
| CVS | Conditional | $12.94 | $25.93 | $57.27 | Low | `0000064803-26-000098` / 2026-06-30 |
| WST | Conditional | $55.15 | $79.81 | $114.54 | Low | `0000105770-26-000099` / 2026-06-30 |
| UHS | Withheld | — | — | — | — | `0001193125-26-340278` / 2026-06-30 |

Values are USD per-share baseline decision ranges, not predictions or recommendations. BAX's
bear DCF is negative before the disclosed limited-liability floor, so the published bear endpoint
is zero.

## Frozen contract, source, and cache gate

The frozen manifest is ABT, BAX, BDX, BMY, RVTY, HUM, LLY, CVS, WST, and UHS. Its SHA-256 is
`14fe6100339dc1827785e70eaa1e6ee428b5dc202d891e5d20e9910613a6727e`, matching the frozen
partition receipt.

- BDX's pre-existing SEC packet was reused byte-for-byte from the difficult-106 cache; the other
  nine packets were fetched only after cache preflight.
- BDX's exact structural package was reused from `official-evidence-difficult-106-part-2`; the
  other nine controlling packages were captured and parsed.
- Structural parsing: 10 attempted / 10 parsed / 0 failed.
- All ten packet payload manifests pass their declared hashes.
- All 30 source-packet/package/structural receipt hashes reconcile.
- Source packet replay A/B reused all ten locally with zero fetches and matched exactly:
  `e0f4338b576198f7f9dfdf5afe29d8c17368c305fd699d6ab627c00cac61d6b1`.
- Structural replay A/B reused the completed wrapper for all ten and matched exactly:
  `dd587c928d437c40f78446796ca8614999140e44363d5c3af671990d0dcd585b`.
- Every controlling filing was filed on or before 2026-08-14.
- Protected serving roots stayed unchanged under every capture and generation guard.

The structural wrapper's top-level `period_end` is a parser diagnostic and is malformed for BAX,
BMY, RVTY, HUM, LLY, CVS, WST, and UHS. Selection uses the bound receipt/package report date and
fact-specific periods; every private result marks the diagnostic `used_for_selection: false`.

The replay exposed and fixed one cache-path issue: Batch 12 can now reuse either the older
official-evidence `packages`/`parsed` layout or its own completed immutable ticker wrappers. The
fixed offline replay reports all ten reused and no captures.

## Outcome decisions and load-bearing treatments

- **ABT Conditional:** FCFF is retained, but the $20.6B Exact Sciences acquisition, $19.962B
  acquisition/R&D cash, new debt, $263M contingent consideration, $652M NCI, and incomplete
  acquired-business cash history remain material.
- **BAX Conditional:** continuing-operations FCFF remains sensitive to the disposition and
  separation. Interest was corrected to a coherent net-interest TTM magnitude: $238M annual +
  $130M current H1 − $122M prior H1 = **$246M**. The private ledger explicitly records the 21%
  practical tax fallback used when three positive annual pretax observations are unavailable.
- **BDX Conditional:** the $4B spin consideration is event evidence, not intrinsic cash. The
  bridge excludes $155M restricted cash/investments and binds $450M impairment evidence. The
  $181M supplier-finance obligation remains in accounts payable/OCF and is not added again as debt.
- **BMY Conditional:** $1.027B short-term borrowings and $42.861B long-term debt are included once.
  The previously omitted **$607M contingent-value-rights liability** is now a separate
  common-equity claim.
- **RVTY Conditional:** the Advanced Chemistry Development acquisition binds $72M cash
  consideration, $8M contingent consideration, $41.311M restructuring charges, and a $32.818M
  restructuring-reserve diagnostic. The reserve is an operating liability reflected in OCF/history,
  not an extra equity claim. The bridge uses $3.2222B gross debt principal once, conservatively
  leaving $16.95M issuance discounts/costs out of excess value.
- **HUM Conditional:** the insurer is valued through normalized parent-attributable common
  earnings, not a generic FCFF debt bridge. FY/current/prior NCI is removed consistently, producing
  **$1.263B** TTM common earnings.
- **LLY Conditional:** current manufacturing capex and pipeline/acquisition dependencies remain
  specialist risks. TTM capex is **$9.893B** and aggregate interest is corrected to
  $895M + $677M − $493M = **$1.079B**. The bridge includes $54.908B debt and $2.518B contingent
  consideration.
- **CVS Conditional:** the mixed insurer/PBM/retail business uses normalized common earnings so
  medical claims, member/customer funds, regulated capital, and debt remain inside the equity
  model. TTM common earnings are **$4.890B**.
- **WST Conditional:** the completed July SmartDose divestiture adds $136M proceeds to cash;
  disposed-business history, quality/regulatory risk, capacity capex, $4.4M finance leases, and
  $3.3M contingent consideration remain explicit.
- **UHS Withheld:** after the 2026-06-30 report date, UHS completed an approximately $188M Ireland
  facilities acquisition while its approximately $835M debt-financed Talkspace acquisition was
  still pending. No single filed post-Ireland cash, debt, and operating-cash object exists, so no
  current baseline was manufactured.

## Independent challenge

Three Luna XHigh reviewers challenged separate scopes: raw source/cutoff/period/unit/share and
bridge evidence; economic model and outcome classification; and arithmetic/sensitivity/public
mechanics. Final verdict: **PASS with no remaining Critical or Important finding**.

Resolved Important findings were BAX's mixed interest scope, BMY's omitted CVR claim, RVTY's
contingent claim/acquisition/restructuring status, HUM's NCI treatment, LLY's missing current/prior
interest, and UHS's omitted completed post-period acquisition. All nine numeric models and every
scenario replay exactly. Higher cash, normalized earnings, cash conversion, or terminal growth
raises value; higher WACC, debt, claims, capex, or shares lowers value.

Remaining Minor caveats are explicit: some structural rows retain the accession while the filed
date remains in the receipt rather than the row; public `scenarios` and `sensitivities` arrays stay
empty while private scenario rows prove the governed directions; and RVTY deliberately uses gross
principal rather than net carrying debt.

## Determinism, tests, build, and real API

- Final candidate-i/j full-tree SHA-256:
  `6fc362a70a07dc00364a4096e7a084478f07585ba7ceb3f6a517c3c0b688a159`
- Generated-private tree SHA-256:
  `fd5821884f0dc302873b0da64a37a15a0a267732b7ba614c966e60ccd2d53ee8`
- Staged-public tree SHA-256:
  `45161b25da9fd9ed83279de6cd018ab0b674432dad4c08488d91e04bf9b4a319`
- Focused Batch 12 tests: `9 passed`
- Full backend suite: `1,344 passed, 3 skipped, 1 warning`
- Frontend production build: passed (`1,694` modules transformed)
- Isolated cumulative catalog: `120` artifacts, batches 01–12
- Catalog availability: `47 available / 67 conditional / 6 unavailable`
- Catalog publication: `114 review-required / 6 withheld`
- Catalog artifact-tree SHA-256:
  `70cb9ced3117f972e52303897929e21f5d5292f6bee2f1d0f0f81c06fcf63250`
- Real localhost FastAPI list: HTTP 200, exact count 120
- Detail parity: 120/120; exact Batch 12 staged parity: 10/10
- Calculator GET parity: 120/120
- Calculator default POST parity: 114/114 numeric HTTP 200; six Withheld return HTTP 400
- Private leaks: 0
- API receipt SHA-256:
  `e8f046d76b4e981bde2013d07e0d31cc5c2b03ac194c8bedf714e60c42de8a7d`

The API used an isolated untracked catalog and the documented local auth harness with
`save=false`. It verifies real list/detail/calculator HTTP behavior, not authentication,
Postgres/MinIO persistence, or production serving promotion. Final candidate-i public artifacts
are byte-identical to the candidate-e public artifacts used to build the isolated catalog.

## Confirmation gate

Stop here and wait for the user's confirmation. Do not attempt Batch 12 recovery, mutate the
Recovery Learning Watchlist or cumulative withheld register, start Batch 13, promote or activate
a tracked serving catalog, merge, push, or deploy without a separate explicit signal.
