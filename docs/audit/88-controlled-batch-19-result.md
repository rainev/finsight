# Controlled Universe Reset Batch 19 Initial Result

Status: **firsthand verified and user-confirmed on 2026-08-30**. Exactly the ten frozen Batch 19
issuers were processed at the 2026-08-14 valuation date. Confirmation added the six direct
Conditional companies to the Recovery Learning Watchlist. No recovery, withheld-history mutation,
tracked serving promotion, Batch 20, merge, push, or deployment was performed.

## Outcome

- Pass: **4/10** — ITW, J, MAS, NDSN
- Conditional: **6/10** — GE, HUBB, MMM, PCAR, PH, DE
- Withheld: **0/10**
- Numeric: **10/10**
- Reliability: **10 Low / 0 Medium / 0 High**
- Cumulative through 190 issuers: **68 Pass / 113 Conditional / 9 Withheld**
- Cumulative numeric coverage: **181/190**

These are baseline decision ranges, not predictions or recommendations. Conditional companies
have finite usable values but retain a named separation, acquisition, legal-claim, insurance, or
captive-finance dependency.

## Company results

| Ticker | Outcome | Low | Base | High | Reliability | Simple reason |
| --- | --- | ---: | ---: | ---: | --- | --- |
| GE | Conditional | $33.33 | $76.31 | $150.90 | Low | Mixed aerospace/run-off-insurance parent-equity model and short post-separation history |
| HUBB | Conditional | $54.92 | $166.69 | $293.91 | Low | June NSI acquisition; filed pro-forma scale but incomplete acquired cash conversion |
| ITW | Pass | $59.82 | $112.34 | $183.01 | Low | Stable five-year cash history and cutoff note principal/proceeds reconciled once |
| J | Pass | $33.74 | $77.92 | $196.80 | Low | Continuing engineering cash, Amentum separation, PA interest repurchase, and debt reconcile |
| MAS | Pass | $20.74 | $35.88 | $59.64 | Low | Five-year building-products cash history and complete debt/NCI/share bridge |
| MMM | Conditional | $0.00 | $39.46 | $85.13 | Low | $9.756B recorded legal liabilities plus unquantified PFAS/personal-injury tails |
| NDSN | Pass | $64.84 | $131.77 | $224.76 | Low | Stable cash history; new commercial-paper program is capacity, not issued debt |
| PCAR | Conditional | $38.63 | $82.68 | $158.62 | Low | Mixed truck/captive-finance residual-income model |
| PH | Conditional | $168.41 | $344.41 | $566.30 | Low | Filtration Group closed at cutoff; cost/funding overlay without invented acquired cash flow |
| DE | Conditional | $114.65 | $265.49 | $521.76 | Low | Mixed equipment/captive-finance residual-income model and cutoff financing fee |

3M's public bear value is zero only because the raw bear residual is negative after recorded legal
liabilities. The raw value remains private, the base is positive, and no missing input was replaced
with zero.

## Controlling sources

| Ticker | Accession | Form | Filed | Report period |
| --- | --- | --- | --- | --- |
| GE | `0000040545-26-000049` | 10-Q | 2026-07-16 | 2026-06-30 |
| HUBB | `0001628280-26-050405` | 10-Q | 2026-07-29 | 2026-06-30 |
| ITW | `0000049826-26-000049` | 10-Q | 2026-08-06 | 2026-06-30 |
| J | `0001628280-26-052573` | 10-Q | 2026-08-04 | 2026-06-26 |
| MAS | `0000062996-26-000027` | 10-Q | 2026-07-29 | 2026-06-30 |
| MMM | `0000066740-26-000246` | 10-Q | 2026-07-21 | 2026-06-30 |
| NDSN | `0000072331-26-000024` | 10-Q | 2026-05-21 | 2026-04-30 |
| PCAR | `0001193125-26-323642` | 10-Q | 2026-07-29 | 2026-06-30 |
| PH | `0000076334-26-000073` | 10-Q | 2026-05-01 | 2026-03-31 |
| DE | `0001104659-26-067311` | 10-Q | 2026-05-28 | 2026-05-03 |

Malformed top-level structural dates for HUBB, Jacobs, Masco, 3M, Nordson, PACCAR, and Deere were
retained only as diagnostics. Filing selection uses the source receipt and each fact's own period.

## Source capture and cutoff events

- Exact manifest SHA-256:
  `0350deebae8c9fef54ba37afd4e51e7221708eceb3ed40115b1398f815c6c1f6`
- SEC packets: ITW/PH/DE reused; seven fetched; exact 10/10
- Structural wrappers: the same three reused; seven captured under Python 3.11/Arelle; 10/10 parsed
- Source packet initial/replay A/B tree SHA-256:
  `33efaa7671f82a15a272d4392293681c53ca2d4621824f947fd654dcc8ccc184`
- Structural replay A/B tree SHA-256:
  `439261d48d2ecb84a5b157c462b8e55e5f9033bedaa00ecc9e02c238679f5001`
- Initial mixed capture-mode structural tree SHA-256:
  `435c69d56180c351be7c3f45864e256ea997799cf8acc8860647f6a36c931f4b`
- Cutoff event-source tree SHA-256:
  `caaa1efafda5e41c808796885b03f8890cd79c840691b480a13d52b7bd24a193`

Six cutoff event documents were bound. ITW's $1.5B issued notes and $1.489B estimated net proceeds
were added once without assuming the intended commercial-paper repayment. Nordson's $1.2B program
was treated as borrowing capacity, not debt. Parker's August 13 close added the reported $9.25B
acquisition-cost proxy, $7.75B term loans, and a $1.5B remaining-funding reserve without invented
synergies. Deere's $300M finance-subsidiary issuance stayed inside its equity-level route; only the
$1.733M principal/proceeds difference reduced cutoff common equity.

## Source and economic challenge

No subagents were used. Two separate local lenses challenged the exact candidate:

1. **Source/mechanics:** issuer/accession/cutoff/period, current versus pro-forma scale, shares,
   debt/leases, NCI/preferred, recorded claims, and all cutoff events.
2. **Economic/public:** operating versus equity-level model choice, acquisition and settlement
   treatment, arithmetic, scenario direction, classification, calculator family, and public/private
   boundary.

The economic lens found one Important issue: Hubbell carried the full acquisition debt while the
first candidate merely disclosed—but did not use—the filed pro-forma acquired scale. The repair
wired `reported TTM + 2 × (filed pro-forma H1 − reported H1)` into valuation revenue, moving the
range from $43.62/$146.87/$264.40 to $54.92/$166.69/$293.91.

Final independent challenge receipt SHA-256:
`fab025e5b9189eb2dee39f846a4a38bbb8661abd788503cf70fb15f14378c016`
— 10/10 challenged, 0 Critical, 0 Important.

## Determinism and automated verification

- Candidate-C/candidate-D full-tree SHA-256:
  `f5102dbedbbfbe1b875249eef94ceb60f60c281cf941ee77fa512f7d07d9acdc`
- Generated-private tree SHA-256:
  `81808a189d3b962908a880e50ba0f47f8e3cc6a0f1002c96c983be5cf0b28021`
- Staged-public tree SHA-256:
  `2e9c3ec54729e47c6fc163e3c4e8db7a8dea10641a2c338b891df72e2aea1f29`
- Final report SHA-256:
  `945def2ee65e45a1ff7a6d6cb1716e2f40e3e10e4d4e72cf26e84d8e08e2208b`
- Focused Batch 19 tests: `9 passed`
- Complete backend suite: `1,564 passed, 3 skipped, 1 warning`
- Frontend production build: passed (`1,694` modules transformed)
- `git diff --check`: passed

## Real consumer path

- Isolated cumulative catalog: 190 exact artifacts, Batches 01–19
- Availability: 68 available / 113 conditional / 9 unavailable
- Publication: 181 review-required / 9 withheld
- Catalog artifact-tree SHA-256:
  `e1193481d3149dfa18f13ba6001caf2b02a0e8630f9a69e0285fe47c1cd7de64`
- Catalog manifest SHA-256:
  `ceb97b7e9237cbd8a2cd9620afe6ec8610231059616f29fa324260441f3b2eb6`
- Real localhost FastAPI list: HTTP 200, exact count 190
- Detail/catalog parity: 190/190; exact Batch 19 staged parity: 10/10
- Calculator GET parity: 190/190
- Calculator POST: 181 numeric HTTP 200; nine unavailable HTTP 400
- Batch 19 model families: seven operating / three equity-earnings
- Private leaks: 0
- API receipt SHA-256:
  `c8f7320e0df9cd129dc3f06f6bc4edbd14e205304f3ec4863bbf12f1a78ffe40`

The API used an isolated untracked catalog, a local test-only auth harness, and `save=false`. Arelle
remained outside the serving process. Tracked serving roots stayed unchanged.

## Protected state and confirmation gate

- Capture-guard protected trees remain exactly:
  - tracked valuation catalogs:
    `38efe664dc981e9d2383ece43b66e9ae326b4b9a7cc2443f2463498432ef66a8`
  - frontend public data:
    `353a14bc672002e88d248811f98d23d4c1fb47cf28e526d969f463f256260274`
  - generated research surface:
    `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
- Recovery Learning Watchlist is 122 (113 Conditional / 9 Withheld); SHA-256:
  `fcc02bdb2cd279bf424937ebec2492c64c0818f09f3e7ba9ee0a533f1d84cbaa`
- GE, HUBB, MMM, PCAR, PH, and DE were added with `recovery_outcome=not_applicable`; MMM retains
  explicit equity-at-risk status. Pass companies ITW, J, MAS, and NDSN were not added.
- Cumulative automatic-withheld history remains 19; SHA-256:
  `28bcfdd2985f3f3d87320e9e780aac630923510d0e46c614d9cfb5035e19f3ec`
- Tracked valuation catalog, frontend public data, and generated research roots are unchanged.

The user replied `y` on 2026-08-30. Batch 19 is confirmed and recorded. Because Withheld is 0/10,
no recovery phase is needed. Batch 20 was not started; the next valid signal is
`Start Universe Reset Batch 20`.
