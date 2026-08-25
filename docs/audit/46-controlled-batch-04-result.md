# Controlled Batch 04 launch-first result

**Valuation date:** 2026-08-14

## Exact outcome

- Attempted: **10/10**.
- Numeric: **10/10**.
- Conditional Low: **10/10**.
- Not available: **0/10**.
- Invalid/skipped/replaced: **0/10**.
- Serving artifacts changed: **no**.
- Recovery Learning Watchlist changed during staging: **no**.

| Ticker | Low | Base | High | Baseline method |
| --- | ---: | ---: | ---: | --- |
| F | $1.16 | $11.59 | $37.06 | normalized consolidated equity earnings; not Ford Credit SOTP |
| GPC | $0.00 | $44.24 | $124.81 | working-capital normalized cash FCFF |
| HAS | $8.19 | $53.85 | $141.08 | post-impairment normalized cash FCFF |
| LOW | $19.32 | $130.81 | $270.10 | home-retail normalized cash FCFF |
| MCD | $42.19 | $153.48 | $310.76 | franchise/lease normalized cash FCFF |
| TJX | $34.61 | $78.60 | $142.38 | off-price normalized cash FCFF |
| NKE | $7.88 | $23.35 | $88.01 | transition normalized cash FCFF |
| HD | $44.91 | $185.42 | $421.76 | housing-cycle/SRS integration cash FCFF |
| ROST | $63.09 | $136.38 | $242.60 | off-price normalized cash FCFF |
| MGM | $12.95 | $59.76 | $152.98 | casino-cycle/JV normalized cash FCFF |

All ranges are decision-support baselines, not probability-weighted forecasts or recommendations.
GPC's bear residual is negative and therefore uses a disclosed limited-liability equity floor of
$0. All ten retain Low confidence and invalidation warnings.

## Source and model controls

- Five verified difficult-106 packets were reused; five missing issuers were fetched once.
- Ten controlling filing packages parsed successfully outside the serving process.
- Every standard bridge traces assets, cash/investments, debt components, reported NCI when
  available, and the current diluted-share denominator.
- Unreported NCI is not called zero: LOW, MCD, TJX, NKE, HD, and ROST use `null` reported NCI plus
  a 2%/1%/0% asset-based unresolved-claims reserve.
- Ford is honestly labeled a normalized consolidated equity-earnings baseline. Ford Credit
  receivables, Ford Credit funding, industrial debt, and consolidated equity are source-linked;
  no EV debt bridge or Ford Credit SOTP claim is made.
- MCD's filing reports diluted shares in millions; the private ledger records the 712.3m scale.
- MCD and MGM operating leases remain inside operating cash flow and are not subtracted again as
  bridge debt. Finance leases remain financing claims.
- HD's debt bridge explicitly reconciles long-term/current obligations plus commercial paper.
- Malformed structural summary dates are diagnostic only; submissions report dates and fact-row
  periods control.
- The public calculator is explicitly baseline-calibrated and does not claim to rerun each private
  issuer-specific model.

## Challenge

Candidate-a was rejected because Ford's model identity overstated the route and the nine standard
bridges lacked fact-level provenance. Candidate-c resolved those issues but still mislabeled six
unresolved NCI fields as reported zero. Candidate-e corrected the status and reserve ledger.

Final independent Luna-High verdict: **PASS**, no Critical or Important findings.

## Determinism and automated verification

- Frozen manifest SHA-256:
  `b577f5077d7f9a849418c610c4e8e8e62a5d275dca07f04207221c94e89c54f3`.
- Source-packet tree SHA-256:
  `1bf2ffaafeef86a5892612f26ddc502108fe14aa9f85ff34e36b6292a50256d3`.
- Structural-source tree SHA-256:
  `bedcf734ab37f6c421ccf8300d66f12cceb80c6c4ca0bf31c53317e3826b0b3a`.
- Candidate-e/candidate-f byte-identical tree SHA-256:
  `55523501fab86a0209a9c40c63b83c2bda643bc3dc1211481145a5a8eaacb464`.
- Launch-first report SHA-256:
  `e6ebdbae90f8138f23ae0f26ca61ca986d3630373d6166f20ca4a4fab9553ae8`.
- Focused Batch 04 suite: **7 passed**.
- Complete backend suite: **1,239 passed, 3 skipped, 1 warning**.
- Frontend production build: **passed**, 1,695 modules transformed.
- `git diff --check`: passed.

## Real API/calculator evidence

The real FastAPI application served the exact ten-company candidate-e stage:

- list HTTP 200/count 10;
- detail 10/10 HTTP 200;
- calculator GET 10/10 HTTP 200;
- calculator default/base parity 10/10;
- higher discount rate lowered value;
- better cash conversion increased value;
- manual-price flow passed;
- private leaks 0.

API receipt SHA-256:
`4d9ff2d4fda312c0e44719ac68297f7b5c69dd063c30d0bc7e68949c6b203f29`.

## Gate

Batch 04 is technically verified; user confirmation is required. Recovery Learning Watchlist
bookkeeping for these conditional results remains pending confirmation. No serving promotion,
merge, push, deployment, or Batch 05 work occurred.

