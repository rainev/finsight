# Controlled Batch 02 initial result

**Valuation date:** 2026-08-14

**Frozen denominator:** OMC, VZ, T, TTWO, NFLX, CHTR, CMCSA, TMUS, META, WBD

**Status:** initial pass verified; recovery was subsequently authorized and is recorded in Audit 18

## Exact outcome

- Attempted: **10/10**
- Strict policy: **0 numeric / 10 withheld / 0 invalid**
- Practical transparent policy: **4 numeric Low / 6 withheld / 0 invalid**
- No company replaced or skipped
- Serving promotions: **0**
- Recovery attempts: **0** — this is the initial pass only

| Ticker | Initial result | Reliability | Low | Base | High |
| --- | --- | --- | ---: | ---: | ---: |
| OMC | Withheld | Low public safety label | — | — | — |
| VZ | Numeric | Low | 21.000979 | 58.645419 | 124.322671 |
| T | Numeric | Low | 11.591258 | 30.721373 | 68.758048 |
| TTWO | Withheld | Low public safety label | — | — | — |
| NFLX | Numeric | Low | 21.055572 | 41.210464 | 72.190931 |
| CHTR | Withheld | Low public safety label | — | — | — |
| CMCSA | Withheld | Low public safety label | — | — | — |
| TMUS | Numeric | Low | 54.829503 | 230.681181 | 450.041337 |
| META | Withheld | Low public safety label | — | — | — |
| WBD | Withheld | Low public safety label | — | — | — |

These ranges are filing-only assumption ranges, not confidence intervals and not trading
recommendations. No stock price, analyst target, or peer multiple is used.

## Why the four companies are numeric

### VZ — Verizon

The current filing says the completed Frontier acquisition was not material enough to require pro
forma consolidated revenue/earnings disclosure. Cash FCFF includes `$1.371bn` of TTM spectrum
license purchases in addition to PP&E capex. The bridge reconciles `$3.088bn` of cash/investments,
`$165.231bn` of current plus long-term debt, zero preferred, `$1.276bn` NCI, and 4.190bn diluted
shares. Wide cash/growth/WACC/share scenarios keep the result at Low.

### T — AT&T

The model uses continuing-operations OCF and deducts `$1.034bn` of structurally tagged license
cash. A `0 / $133m / $266m` range bounds the continuing-versus-consolidated capex scope. The
pending Forged Fiber sale is not assigned invented proceeds: realization is ranged from zero to
the filed `$4.051bn` net held-for-sale carrying amount. Debt is `$143.954bn`; NCI and redeemable
NCI total `$17.995bn`. Reliability remains Low.

### NFLX — Netflix

Cash FCFF is content-aware because operating cash flow already includes content cash payments.
The reported `$2.8bn` WBD termination fee is removed from recurring cash. Content commitments stay
out of the debt bridge to avoid double counting. Private evidence retains `$25.106705bn` total,
`$19.6bn` unrecorded, and `$11.939734bn` next-12-month obligations. The bear starting-cash
reduction of `$2.672956bn` exceeds the filed `$2.388970bn` H1 increase in content additions. Debt
is `$14.309306bn`; the result remains Low.

### TMUS — T-Mobile US

Cash FCFF deducts `$2.163bn` of TTM spectrum purchases. The bridge reconciles reported debt,
finance leases, and the separately reported `$3.461bn` interest-bearing tower obligation exactly
once, for `$90.381bn` total financing claims. Current and annual cash conversion, WACC, growth,
and share dilution are broadly stressed, so reliability remains Low.

## Why six companies are withheld

### OMC — Omnicom

The IPG merger closed in November 2025. Omnicom explicitly says post-merger results are not
comparable with historical periods and supplies no combined pro forma cash history. A complete
current Arelle parse repairs the empty Companyfacts accession, but one combined half-year cannot
bound normalized owner cash flow. Hard reasons: `MAJOR_EVENT_UNBOUNDED`, `MODEL_UNSUPPORTED`.

### TTWO — Take-Two Interactive

TTM cash/FCFF is nonpositive and value is concentrated in a release pipeline. The filing does not
provide a finite source-backed timing and hit-rate range. Hard reasons:
`MAJOR_EVENT_UNBOUNDED`, `MODEL_UNSUPPORTED`, `NONFINITE_OR_NONPOSITIVE_VALUE`.

### CHTR — Charter Communications

The pending Cox and Liberty Broadband transactions introduce material cash consideration,
`$6bn` convertible preferred units, common units, and assumed debt without current combined
operations. Hard reasons: `MAJOR_EVENT_UNBOUNDED`, `CLAIMS_UNBOUNDED`.

### CMCSA — Comcast

The proposed NBCUniversal/Sky separation has unsettled financing, retained ownership, approval,
terms, and timing. The present consolidated company is not a defensible terminal state. Hard
reasons: `MAJOR_EVENT_UNBOUNDED`, `MODEL_UNSUPPORTED`.

### META — Meta Platforms

Meta reports approximately `$349.31bn` of non-cancelable contractual commitments, `$278.99bn` of
not-yet-commenced leases, and another `$68bn` of July lease commitments. Their timing and overlap
with future capex cannot be reconciled by a simple percentage sensitivity without omission or
double counting. Hard reasons: `CLAIMS_UNBOUNDED`, `MODEL_UNSUPPORTED`.

### WBD — Warner Bros. Discovery

WBD has a pending cash merger, litigation seeking to block it, and an alternative separation
path. Assigning transaction probabilities or a standalone terminal state would be invention.
Hard reasons: `MAJOR_EVENT_UNBOUNDED`, `MODEL_UNSUPPORTED`.

## Source evidence

- Immutable Companyfacts/submissions packets: **10 packets / 50 files**.
- Filing ledger: **263 cutoff-eligible filings** and **51 future filings kept separate**.
- Source tree hash:
  `96c3607b813482535584ef652cd0b03f346ab50de5e9380ff5e14e4c52516eda`.
- Controlling full filing packages: **10 attempted / 10 parsed / 0 failed** through the isolated
  Arelle path; structural output hash:
  `ba6b03242ae7263583e4b91b571fab24f59f4e9ba272bb04eaaf288053676c3b`.
- Every controlling accession, form, period, unit, and filed date is at or before the cutoff.
- OMC's latest Companyfacts accession contains zero observations; the full filing parse prevents
  stale March facts from being attributed to the June period.
- Arelle remains dynamically isolated from the serving import path.

## Challenge history

The first mechanical candidate was rejected before finalization. Self-review corrected current
debt for VZ/T, TMUS tower obligations, and reversed META from numeric to withheld. The independent
Luna-High valuation reviewer then found omitted spectrum-license cash and incomplete annual/
content/scope lineage. Those findings were resolved before candidate D.

Final independent verdict on candidate D: **PASS**, with no remaining Critical or Important
finding. The reviewer independently replayed all four ranges, bridge claims, spectrum cash,
annual tax/cash lineage, AT&T scope range, Netflix content coverage, sensitivities, and public/
private parity.

## Determinism, tests, regression, and serving safety

- Verified runs A/B: **22 files each**, byte-identical tree hash
  `fdb0a830fb724c07c59fe8cdc04016df55427e9303ebe83372da5182d7d1a25d`.
- Batch report SHA-256 A/B:
  `cf148abf1a4a538e374986f05e295ceebcf23539f4215096255313ef8f965c69`.
- Focused source/model/policy/API suite: **41 passed**.
- Complete backend suite: **1103 passed, 3 skipped**, with one existing Python `crypt`
  deprecation warning.
- Existing 94 source-verified difficult-corpus public artifacts re-sanitized idempotently:
  zero exceptions and zero contract changes. OMC/VZ/NFLX were absent from that corpus. The older
  106-private-artifact replay could not be regenerated because its original `sec-cache` input is
  absent from this worktree; this limitation is not represented as a live replay pass.
- Serving roots remained byte-identical:
  - backend JSON: `f68fd4d359e7e20dbf5daff4fddd91caa76d68cf95d3559702d4c80ae53d2c04`
  - frontend public data: `5157530c9c4baf3e9d5e6b0455a54579c94a5ead79c07145d9f4d35aef0e7017`
  - generated frontend tree: empty hash `e3b0c442…b855`

## Real API verification

After the user explicitly approved the temporary local bind, Uvicorn started on
`127.0.0.1:8765` against only `verified-run-a/staged-public`.

- `GET /api/us-valuations`: HTTP 200, exact count 10, exact frozen ticker set.
- Ten detail requests: 10/10 HTTP 200.
- List/detail/staged-file base value, publication state, and reliability: 10/10 exact parity.
- Private keys (`financials`, `source_manifest`, `input_provenance`, `practical_policy`,
  `calibration`, and diagnostics): zero leaks.
- Numeric details: four finite Low results; withheld details: six null ranges with Low public
  safety label.
- Importing the actual FastAPI serving path against the staged directory loads zero Arelle
  modules.
- Uvicorn shut down cleanly after the requests.
- Untracked API receipt SHA-256:
  `9aeed422ebd92e547839183d452db6723377db57d9dabf163c80099f1a2ba399`.

The initial missing-environment and sandbox-bind failures remain recorded as diagnostic history;
they were resolved by the documented test environment and the user's explicit local-port approval.

## Stop boundary

At this initial-pass gate, no staged Batch 02 artifact was copied into serving data, no recovery
had yet been attempted, no company had been appended to the cumulative withheld register, and
Batch 03 had not started. Recovery was subsequently authorized and completed in Audit 18.
