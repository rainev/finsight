# Controlled Batch 05 launch-first result

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
| WSM | $66.30 | $139.79 | $303.85 | normalized home-furnishing cash FCFF |
| CASY | $53.19 | $284.92 | $563.13 | food/fuel retail normalized cash FCFF |
| CCL | $0.00 | $11.68 | $43.34 | cruise-cycle normalized cash FCFF |
| PHM | $28.37 | $77.50 | $131.07 | consolidated normalized equity earnings |
| SBUX | $6.35 | $38.04 | $77.05 | restaurant/lease turnaround cash FCFF |
| AZO | $403.48 | $1,673.02 | $3,705.92 | auto-parts working-capital cash FCFF |
| DHI | $30.24 | $82.62 | $139.73 | consolidated normalized equity earnings |
| RCL | $0.00 | $30.08 | $252.25 | cruise-cycle normalized cash FCFF |
| ORLY | $8.98 | $36.39 | $71.93 | auto-parts working-capital cash FCFF |
| NVR | $1,135.62 | $3,101.67 | $5,244.81 | consolidated normalized equity earnings |

All ten are broad decision-support baselines, not price targets, probability-weighted forecasts,
or recommendations. CCL and RCL have negative raw bear residuals and therefore use a disclosed
limited-liability floor of zero. All ten remain Low reliability and carry invalidation warnings.

## Source and model controls

- Three verified difficult-106 packets were reused; seven missing issuers were fetched once.
- Ten cutoff-eligible controlling filing packages parsed successfully outside the serving process.
- Standard FCFF bridges retain filing-level assets, cash/investments, debt, NCI/claim reserve, and
  diluted-share provenance.
- PHM, DHI, and NVR do not claim mortgage-separated FCFF. Their TTM common earnings are rebuilt
  from exact FY plus current YTD less prior YTD facts, with accession, concept, period, unit, and
  mortgage/land context. No EV debt bridge is applied to these equity-level baselines.
- Their accounting-impact ratios are issuer-specific: source-linked mortgage/land exposure is
  subjected to the governed 10%/5%/0% reserve range and measured against base common-equity value.
- AZO includes its reported securities and combined debt, while the unresolved finance-lease
  balance is bounded once by the reported $82.161m year-to-date principal-payment amount.
- CASY does not deduct finance leases twice; SBUX includes current and noncurrent investments.
- The public homebuilder calculator exposes normalized earnings and earnings multiple—not a
  misleading cash-conversion control. Defaults reproduce the staged value and higher normalized
  earnings raise value.

## Challenge

The first candidate was rejected for missing homebuilder debt, mortgage/land economic-object
errors, duplicated CASY lease claims, incomplete AZO/SBUX bridges, and unsupported reliability
metadata. Later candidates corrected the arithmetic but still lacked exact homebuilder component
lineage and honest calculator semantics. Candidate-g resolves those issues and includes
issuer-specific accounting-risk evidence.

Final independent Luna-XHigh verdict: **PASS**, no Critical or Important findings.

## Determinism and automated verification

- Frozen manifest SHA-256:
  `bb771039d557db9669905c7a40b28fec1a45f821e480b036b141d2de7a101ff7`.
- Source-packet tree SHA-256:
  `47614f963ca8b6ec800b77077a96effd176d952c64cf6f65ed3774325906556e`.
- Structural-source tree SHA-256:
  `0b188b83faabcfe2007375c65eecd1364d7294c3bbdd6dc034b859b1d0157f8d`.
- Candidate-g/candidate-h byte-identical tree SHA-256:
  `4a27f86b0329deb33d3a9349b9aba5f87d6cdf6f78f58c51c06a5abd79c06d82`.
- Launch-first report SHA-256:
  `029a5c582eecac9d05fd29585d274f1fd29457ab5d8bd723d338dac72f7bcf86`.
- Focused Batch 05 and artifact suite: **112 passed**.
- Complete backend suite: **1,247 passed, 3 skipped, 1 warning**.
- Frontend production build: **passed**, 1,695 modules transformed.
- `git diff --check`: passed.

## Real API/calculator evidence

The real FastAPI application served the exact ten-company candidate-g stage:

- list HTTP 200/count 10;
- detail 10/10 HTTP 200;
- calculator GET 10/10 HTTP 200;
- calculator default/base parity 10/10;
- higher discount rate lowered operating value;
- higher normalized earnings raised homebuilder value;
- manual-price flow passed;
- private leaks 0.

API receipt SHA-256:
`c3d57f147f62ea5e6cae98c868a8d4a6221aee04a170e000e04e9c58bd171e0a`.

## Gate

Batch 05 was technically verified and user-confirmed on 2026-08-25. All ten Conditional Low
results were added to the Recovery Learning Watchlist after confirmation. No serving promotion,
merge, push, deployment, or Batch 06 work occurred.
