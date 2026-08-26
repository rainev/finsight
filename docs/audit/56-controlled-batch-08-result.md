# Controlled Universe Reset Batch 08 Result

Status: **user confirmed on 2026-08-26**. The six initial Conditional issuers were added to the Recovery Learning Watchlist. At the initial confirmation gate, no recovery attempt or rollout action had been performed.

Recovery update: the authorized one-attempt recovery is complete in [Audit 57](57-batch-08-recovery-result.md). APTV recovered as Conditional Low; NCLH remains withheld.

## Denominator and result

Valuation date: `2026-08-14`. Exactly 10 frozen issuers were attempted once.

- Pass: **2/10** — ULTA, HLT
- Conditional: **6/10** — LULU, KDP, GM, ABNB, CVNA, DASH
- Withheld: **2/10** — NCLH, APTV
- Numeric: **8/10**
- Numeric reliability: **8 Low**

| Ticker | Outcome | Low | Base | High | Controlling filing / period |
|---|---|---:|---:|---:|---|
| LULU | Conditional | $62.72 | $235.59 | $524.62 | `0001397187-26-000078` / 2026-05-03 |
| ULTA | Pass | $302.61 | $471.31 | $709.76 | `0001104659-26-069491` / 2026-05-02 |
| KDP | Conditional | $0.00 | $7.48 | $44.53 | `0001418135-26-000051` / 2026-06-30 |
| GM | Conditional | $30.56 | $67.98 | $109.90 | `0001467858-26-000051` / 2026-06-30 |
| NCLH | Withheld | — | — | — | `0001104659-26-089657` / 2026-06-30 |
| APTV | Withheld | — | — | — | `0001521332-26-000061` / 2026-06-30 |
| ABNB | Conditional | $133.53 | $210.29 | $330.97 | `0001559720-26-000027` / 2026-06-30 |
| HLT | Pass | $93.14 | $188.97 | $369.32 | `0001585689-26-000043` / 2026-06-30 |
| CVNA | Conditional | $0.00 | $1.99 | $6.24 | `0001690820-26-000055` / 2026-06-30 |
| DASH | Conditional | $78.19 | $136.05 | $191.00 | `0001792789-26-000050` / 2026-06-30 |

All values are USD per share baseline decision ranges, not predictions or recommendations.

## Historical and specialist treatment

- LULU: five-year owner-cash history plus explicit tariff cash-margin stress; supplier finance remains operating.
- ULTA: five-year owner-cash history; current $144.899M borrowing is included once.
- KDP: annualized filed combined pro-forma revenue, legacy cash-conversion history, acquisition debt, finance leases, temporary equity, NCI, and integration-cost range.
- GM: consolidated common-equity earnings; GM Financial remains inside earnings/equity and no EV debt bridge is applied.
- ABNB: five-year reported OCF history, matched customer-fund exclusion, and current filing-table capex range; missing capex is never zero.
- HLT: five-year cash history with debt/capital leases and NCI reconciled; loyalty/deferred-revenue and VIE liabilities remain operating.
- CVNA: consolidated equity earnings with finance, floorplan, securitization, NCI, and TRA economics inside the model; no EV debt bridge.
- DASH: five-year cash history includes both PP&E and capitalized-software reinvestment; convertible debt, acquisition history, SBC, restricted funds, and contract-liability cash reserve remain explicit.

## Why two are withheld

- NCLH: current TTM and median historical cash FCFF are negative. One positive recovery year cannot establish a positive normalized base while $18.648B of newbuild contracts and $15.035B carrying debt remain load-bearing.
- APTV: Versigent was spun off on 2026-04-01. Annual Companyfacts history describes the pre-spin company, while only current and comparative H1 continuing cash exist. Combining them would value the wrong economic object.

## Independent challenge

Luna XHigh initially identified unsupported NCLH normalization, NCLH gross-versus-carrying debt inconsistency, and a DASH cash/investment reconciliation issue. Candidate-f resolves them:

- NCLH is withheld; carrying debt is $15.034785B, with $15.467745B gross principal retained only as a diagnostic.
- DASH excess cash starts from $4.424B cash + $923M current investments + $869M noncurrent investments. Restricted/processor cash is excluded and a $554M/$277M/$0 contract reserve is applied.
- Final independent verdict: **PASS; no remaining Critical or Important findings**.

## Verification evidence

- Focused Batch 08 tests: `7 passed`.
- Complete backend suite: `1,292 passed, 3 skipped, 1 warning`.
- Frontend production build: passed.
- Real FastAPI on `127.0.0.1:8765`: list 10/10; detail 10/10; calculator parity 10/10; withheld calculators fail closed; private leaks 0; directional checks passed.
- Candidate-f and candidate-g generated trees are byte-identical: `9050dd56624be73039664f6d65a0f407ce9fe5b01fd8f2cdbabf8719461c66ed`.
- Candidate-f and candidate-g public trees are byte-identical: `81072f480bab289e07076b4448ddb83d56b0eb708742ad046ac513655245e1d3`.
- API receipt SHA-256: `230c1b7caa03cb481d4258a009e7967dda48e398ed0e7b5ddbf58c6a830f67b7`.
- During valuation, challenge, replay, and API verification, protected serving artifacts and the Recovery Learning Watchlist remained unchanged.
- After user confirmation, the watchlist contains 41 entries (38 Conditional, 3 post-recovery Withheld), SHA-256 `68a3ea14f8655ca44490979b178129556a2fa4a12853cc88fb04bbcbafc35b42`.

## Confirmation gate

The user replied `y` and confirmed the initial Batch 08 result on 2026-08-26. LULU, KDP, GM, ABNB, CVNA, and DASH are now bookmarked as direct Conditional results. NCLH and APTV remain outside the post-recovery register/watchlist until their separately authorized one recovery attempt is complete. Batch 09 requires a later signal.
