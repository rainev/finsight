# Controlled Universe Reset Batch 13 Initial Result

Status: **user confirmed on 2026-08-29**. Exactly the ten frozen Batch 13
Health Care issuers were processed at the 2026-08-14 valuation date. No recovery, Recovery
Learning Watchlist or cumulative-withheld-register mutation, tracked serving promotion, Batch 14,
merge, push, or deployment was performed.

## Result

- Pass: **0/10**
- Conditional: **10/10** — PFE, TMO, JNJ, MRK, SYK, DHR, AMGN, COO, CAH, UNH
- Withheld: **0/10**
- Numeric: **10/10**, all Low reliability
- Cumulative after 130 processed issuers: **47 Pass / 77 Conditional / 6 Withheld**
- Cumulative numeric coverage: **124/130**
- Recovery Learning Watchlist: **73** at the initial-result stop; **83 after confirmation**

| Ticker | Outcome | Low | Base | High | Reliability | Controlling filing / period |
| --- | --- | ---: | ---: | ---: | --- | --- |
| PFE | Conditional | $5.94 | $14.77 | $34.61 | Low | `0000078003-26-000095` / 2026-06-28 |
| TMO | Conditional | $68.66 | $161.16 | $281.85 | Low | `0000097745-26-000144` / 2026-06-27 |
| JNJ | Conditional | $62.92 | $97.82 | $145.29 | Low | `0000200406-26-000153` / 2026-06-28 |
| MRK | Conditional | $20.57 | $47.14 | $103.86 | Low | `0000310158-26-000212` / 2026-06-30 |
| SYK | Conditional | $77.85 | $131.75 | $208.37 | Low | `0000310764-26-000050` / 2026-06-30 |
| DHR | Conditional | $33.10 | $66.62 | $118.77 | Low | `0000313616-26-000161` / 2026-06-26 |
| AMGN | Conditional | $117.49 | $239.33 | $428.56 | Low | `0000318154-26-000126` / 2026-06-30 |
| COO | Conditional | $6.73 | $25.39 | $45.12 | Low | `0001628280-26-041305` / 2026-04-30 |
| CAH | Conditional | $82.12 | $174.49 | $295.57 | Low | `0000721371-26-000038` / 2026-06-30 |
| UNH | Conditional | $68.52 | $119.98 | $211.81 | Low | `0000731766-26-000197` / 2026-06-30 |

Values are USD per-share baseline decision ranges, not predictions or recommendations. Every
company is numeric, but each has a named material acquisition, patent, legal-claim, capital, or
managed-care dependency that prevents an ordinary Pass.

## Frozen contract, sources, and cache gate

The frozen order is PFE, TMO, JNJ, MRK, SYK, DHR, AMGN, COO, CAH, and UNH. The manifest contains
eight core and two boundary issuers, with no replacement or skipped ticker.

- TMO, SYK, and AMGN SEC/structural evidence was reused; the other seven packets were captured
  only after cache preflight.
- Structural parsing: 10 attempted / 10 parsed / 0 failed.
- Every controlling filing was filed by the 2026-08-14 cutoff.
- Source replay A/B reused all ten with zero fetches and matched exactly:
  `f0ec202cec3858d5ca864b04aaf11caa715f1331bd50d6f9683d7104de3f2812`.
- Structural replay A/B matched exactly:
  `6f179db008d65e3694765dec4ab800e8f942402f607fb8e245a43880dabcd1b6`.
- Protected serving roots stayed unchanged. The watchlist and cumulative-withheld register also
  stayed unchanged.

Several structural wrappers have malformed top-level period diagnostics. Selection uses the
source receipt's filing/report dates and fact-specific periods; every private result records that
the wrapper diagnostic was not used for selection.

## Why every outcome is Conditional

- **PFE:** Metsera integration, $2.259B contingent consideration, patents/pricing, and pipeline
  productivity remain material. The sold ViiV investment's $180M H1 dividend is removed from
  valuation cash; its $1.875B sale proceeds remain once in period-end cash/investments.
- **TMO:** Clario/Solventum integration and acquired-business cash history remain material. Debt
  reconciles to $3.368B current plus $39.181B long-term debt/capital leases; separate claims total
  $364M.
- **JNJ:** the $3.7B talc accrual, $823M contingent consideration, patent/product exposure, and
  acquisition pipeline remain material.
- **MRK:** Keytruda concentration and current acquisitions dominate the range. The event-distorted
  TTM margin is excluded because the filing reports $13.811B acquisition-IPR&D addbacks and
  $14.621B acquisition cash outflows; the value uses comparable annual history instead.
- **SYK:** Inari/AVS integration, $361M contingent consideration, recalls, and high current growth
  remain material.
- **DHR:** Masimo closed late in the period. The model annualizes the filing's $12.866B pro-forma
  H1 revenue once and does not add a second Masimo cash stream; integration and litigation remain.
- **AMGN:** patent erosion, Horizon/BeOne exposure, and the IRS dispute remain material. The tax
  bridge explicitly uses $7.6B net disclosed proposal exposure in bear, 50% in base, zero in bull,
  plus $171M contingent consideration in every state.
- **COO:** the $324.8M reserve less $52.5M insurance receivable plus $0.2M NCI produces a $272.5M
  net claim; tax litigation and leverage remain material.
- **CAH:** the bridge includes the $4.3B opioid reserve, $29M current IVC accrual, and $159M NCI.
  The $448M already-paid historical settlement is evidence, not a new current claim.
- **UNH:** a parent-common-equity residual-income model replaces an industrial EV bridge. Reported
  equity, normalized parent earnings, dividends, required return, and post-repurchase share
  evidence anchor the range; medical claims, capital, investigations, and acquisition integration
  remain material.

## Independent challenge and repairs

The Luna XHigh model challenge reproduced the valuation arithmetic and first identified one
Critical and six Important findings: UNH's public calculator route; MRK acquisition accounting;
AMGN tax-claim traceability; CAH's historical settlement; UNH's share denominator; PFE's ViiV
disposal; and COO's net claim. All seven were repaired and replayed. The final independent recheck
recomputed all ten values, verified the repaired source treatments and public boundary, and found
no remaining Critical or Important issue.

## Determinism, tests, build, and real API

- Final candidate A/B full-tree SHA-256:
  `7284949814602d5557eeaf55b39e40de63865cd75c2445a815a16b1b7cf797aa`
- Generated-private tree SHA-256:
  `f1aa95dea05a3279a456e89e3f7b0e9e3a70b2d0d36ce47b85cce92156fde42a`
- Staged-public tree SHA-256:
  `13bba5f47370df7572e8a9cda7798f958d51721b5cce74b9351e4b6776d7ff91`
- Focused Batch 13 tests: `4 passed`
- Full backend suite: `1,502 passed, 3 skipped, 1 warning`
- Frontend production build: passed (`1,694` modules transformed)
- Isolated cumulative catalog: `130` artifacts, Batches 01–13
- Catalog availability: `47 available / 77 conditional / 6 unavailable`
- Catalog publication: `124 review-required / 6 withheld`
- Catalog artifact-tree SHA-256:
  `f9f0fa28beccd93cba2efc30111faec6f24a4f4ad655cc21b3ed3318b880df12`
- Real localhost FastAPI list: HTTP 200, exact count 130
- Detail/catalog parity: 130/130; exact Batch 13 staged parity: 10/10
- Calculator GET parity: 130/130
- Calculator default POST parity: 124/124 numeric HTTP 200; six prior Withheld return HTTP 400
- Private leaks: 0
- API receipt SHA-256:
  `b25c1b3f2595c2abec6a7ffa2b5a6152deec257fab6dccd0a6fd3d479fed16ce`

The API used an isolated untracked catalog and local auth harness with `save=false`. It verifies
real list/detail/calculator HTTP behavior, not production authentication, database/object-storage
persistence, or serving promotion.

## Confirmation and bookkeeping

The user confirmed the Batch 13 result on 2026-08-29. All ten direct Conditional companies were
added to the Recovery Learning Watchlist with `recovery_outcome: not_applicable`; none consumed a
withheld-company recovery attempt. The watchlist now contains 83 entries: 77 Conditional and six
still-Withheld. Its SHA-256 is
`d4828f0e348e04c021b5e36ffe2bba576ebcda5be4c66e03b9ea00ff605e28a6`.

The cumulative withheld register remains byte-identical at ten entries and SHA-256
`0205878089044e64002b8e181821939c266681e5258b882d2749ef3d068ae109`. Focused Batch 13,
watchlist, and withheld-register verification passed: `10 passed`.

Do not start Batch 14, promote or activate a tracked serving catalog, merge, push, or deploy
without a separate explicit signal.
