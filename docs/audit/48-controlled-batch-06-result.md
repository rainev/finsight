# Controlled Batch 06 launch-first result

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
| BBY | $2.85 | $60.87 | $142.08 | supplier-finance normalized retail FCFF |
| DECK | $55.54 | $131.42 | $245.90 | seasonal footwear/inventory cash FCFF |
| TSCO | $0.00 | $15.48 | $37.07 | supplier-finance/inventory cash FCFF |
| LEN | $19.29 | $52.73 | $89.23 | consolidated normalized equity earnings |
| DRI | $22.21 | $107.96 | $208.89 | restaurant/finance-lease cash FCFF |
| AMZN | $0.00 | $42.29 | $120.23 | capex/lease normalized cash FCFF |
| RL | $11.87 | $264.99 | $466.57 | apparel inventory/FX cash FCFF |
| YUM | $25.08 | $89.88 | $186.36 | franchise/disposal/lease cash FCFF |
| MAR | $7.02 | $140.87 | $316.86 | asset-light franchise/lease cash FCFF |
| CMG | $7.14 | $19.78 | $37.23 | restaurant lease owner-cash proxy |

All ten are broad decision-support baselines, not price targets, probability-weighted forecasts,
or recommendations. TSCO and AMZN use a disclosed limited-liability floor of zero in the bear
case. All ten remain Low reliability and carry explicit invalidation warnings.

## Source and model controls

- Three existing SEC packets were reused (AMZN, YUM, CMG); seven missing packets were fetched once.
- Ten cutoff-eligible controlling filing packages parsed successfully outside the serving process.
- Filing metadata controls the period. The structural parser's top-level `period_end` is retained
  only as a diagnostic because it can reflect a future or ordinary fact date rather than the filing
  report period.
- Every selected fact is concept- and unit-specific; foreign-currency and issuer-specific unit rows
  are excluded from USD/share model inputs.
- BBY's latest revenue anchor ends 2026-01-31 while its reconstructed cash flows end 2026-05-02.
  The private and public evidence discloses the mixed-period conditional treatment rather than
  calling the set one aligned TTM period.
- YUM's latest FY interest is carried as an estimated addback; it is not called current-period
  reported. Its $9.462 billion aggregate debt-and-capital-lease obligation is used once.
- CMG uses an owner-cash proxy with no interest addback; missing interest is not converted to a
  reported zero. DECK and CMG report debt as unresolved and carry explicit 10%/5%/0% asset reserves
  for unreported debt, finance leases, NCI, and other financing claims.
- LEN reconstructs TTM common-stockholder earnings exactly: FY plus current YTD less prior YTD,
  producing $1.598948 billion. Mortgage and land activity remains inside the equity-level model;
  no mortgage-separated FCFF or EV debt bridge is claimed.
- BBY and TSCO source-link supplier-finance obligations and apply working-capital stresses.
- Operating leases stay inside operating cash flow; finance leases are bridged exactly once where
  reported. Buybacks affect the share range, not operating reinvestment.
- AMZN's current reported post-capex cash FCFF is approximately negative $9.046 billion. The model
  discloses that condition and treats positive future margins as governed normalization scenarios.

## Challenge

The first candidate was rejected because YUM's aggregate debt already included the separately
displayed current portion, causing a $2.823 billion double count. DECK and CMG also needed their
unresolved-debt reserve purpose stated explicitly. Candidate-g corrected both issues.

Final independent Luna-XHigh verdict: **PASS**, no Critical or Important findings.

## Determinism and automated verification

- Frozen manifest SHA-256:
  `cfbb6fec40735aac8a9ba03b604a1605d814cf60e6f31e6d3b6d65316a7e3976`.
- Source-packet tree SHA-256:
  `25f824615a94280d976454285b98a30ad23cbb5d1955f073ca0f33ae225000df`.
- Structural-source tree SHA-256:
  `1a5af60aae3bd688a7a3715bf6beb3c8eb899e3dec98d8f8f481ae650727b2dc`.
- Candidate-g/candidate-h byte-identical tree SHA-256:
  `fd618685cb391cc082b59e39b352035318b20213fcba6e0a48f10b865cd4336e`.
- Launch-first report SHA-256:
  `2803e65422181e17d531280187dda8f9dc32207152b2aa1c4ffd591eb6cbbb8c`.
- Focused Batch 06 and artifact suite: **111 passed**.
- Complete backend suite: **1,255 passed, 3 skipped, 1 warning**.
- Frontend production build: **passed**, 1,695 modules transformed.
- `git diff --check`: passed.

## Real API/calculator evidence

The real FastAPI application served the exact ten-company candidate-g stage:

- list HTTP 200/count 10;
- detail 10/10 HTTP 200;
- calculator GET 10/10 HTTP 200;
- calculator default/base parity 10/10;
- higher discount rate lowered operating value;
- higher normalized earnings raised LEN's value;
- manual-price flow passed;
- private leaks 0.

API receipt SHA-256:
`823acd8b65cfab120fd2d3e574df6c3b920597b9c8338792105c0caf6cd9a8dd`.

## Gate

Batch 06 was technically verified and user-confirmed on 2026-08-26. All ten Conditional Low
results were added to the Recovery Learning Watchlist after confirmation. No serving promotion,
merge, push, deployment, or Batch 07 work occurred.
