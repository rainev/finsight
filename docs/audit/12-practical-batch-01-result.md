# Practical transparent Batch 01 result

**Verified:** 2026-08-20 (Asia/Manila)

**Valuation date:** 2026-08-14

**Denominator:** AAPL, MSFT, CRM, ANET, WDC, DELL, JPM, BAC, NEE, O

**Status:** verified — user confirmation needed; no serving promotion authorized

## Outcome first

The strict policy produced **0 numeric / 10 withheld**. The practical bounded-uncertainty
policy produces **7 numeric Low / 3 withheld**, with no invalid input and no company omitted or
replaced. Every numeric value is an intrinsic-value range in USD per share. Nothing was written
to a serving directory.

| Ticker | Strict | Practical low | Practical base | Practical high | Reliability | Practical treatment or remaining blocker |
| --- | --- | ---: | ---: | ---: | --- | --- |
| AAPL | Withheld | 79.801303 | 103.330398 | 123.162561 | Low | Consolidated mature-company FCFF; segment separation is optional; R&D life is interpretation-only; preferred plus NCI is bounded jointly by a source-derived claim cap. |
| MSFT | Withheld | 223.886222 | 284.025313 | 330.867730 | Low | Consolidated FCFF; R&D is not added back to reported cash flow; AI-capex/cash conversion is calibrated from current capex/revenue versus recent annual history. |
| CRM | Withheld | 66.268770 | 101.030382 | 135.730240 | Low | Consolidated software FCFF; SBC remains expensed and dilution is ranged through 822.0m/871.0m/914.55m shares; debt is deducted once. |
| ANET | Withheld | 22.547338 | 39.788869 | 55.201453 | Low | Consolidated profitable-growth FCFF; working-capital/cash-conversion and growth fade are normalized; broad source-derived claim bounds are included in the endpoints. |
| WDC | Withheld | — | — | — | Withheld | The post-spin continuing history does not establish a complete storage cycle, and no source-verified finite external cycle range closes that gap. |
| DELL | Withheld | — | — | — | Withheld | Dell Financial Services funding, equity, earnings, and claim allocation cannot yet be separated without material double-counting risk. |
| JPM | Withheld | 124.288130 | 190.144530 | 226.655290 | Low | Common-equity residual income; corrected average common equity, TTM common income, and outstanding shares; provisional capital/payout sensitivity. |
| BAC | Withheld | 32.937107 | 50.643438 | 61.202153 | Low | Common-equity residual income; preferred equity is separated, common income/shares are source aligned, and missing capital refinement is a provisional range. |
| NEE | Withheld | — | — | — | Withheld | The latest Q2 filing exists, but the captured Companyfacts packet has no observations from that accession. A stale dividend-only model cannot bound the mixed utility/development business. |
| O | Withheld | 36.358752 | 48.288109 | 73.718342 | Low | TTM AFFO DCF; recurring-capital range and annualized current-H1 straight-line rent are explicit. Gross-lease capitalization is a private non-primary diagnostic, not NAV. |

## Why the seven values are allowed

- AAPL, MSFT, CRM, and ANET use coupled bear/base/bull operating cases. Higher WACC lowers
  value; better capital efficiency raises value. AAPL and ANET also include their joint bridge
  uncertainty in the published endpoints. R&D life changes accounting interpretation and fade,
  but current reported free cash flow is unchanged.
- JPM and BAC use residual income on common equity rather than treating deposits as debt. The
  corrected scenarios use terminal ROE of 9%/11%/12% and provisional payout of 20%/30%/40%; all
  provisional capital uncertainty is capped at Low.
- O publishes the coherent AFFO DCF only. TTM FFO and AFFO arithmetic were independently
  replayed; an unavailable annual straight-line-rent fact is represented as an explicitly
  governed annualization, never as zero.

The primary source accessions are AAPL `0000320193-26-000020`, MSFT
`0001193125-26-323660`, CRM `0001108524-26-000127`, ANET
`0001596532-26-000175`, JPM `0001628280-26-054343`, BAC
`0000070858-26-000394`, and O `0000726728-26-000048` plus its 2025 annual
filing `0000726728-26-000011`. Every selected filing was public by the valuation-date cutoff.

## Policy and safety contract

- Missing advanced detail may become a source-linked finite range, but a material provisional
  assumption forces Low reliability.
- Wrong identity/source/period/unit/currency, unreliable shares, conflicts, unsupported models,
  unbounded claims/events, nonfinite/nonpositive values, and public-safety failures still
  withhold.
- An estimated missing value can never have zero as its base. Zero is permitted only as a
  source-defensible endpoint of a nonnegative range with a nonzero upper bound.
- Filing evidence and governed policy choices have distinct private provenance. Public artifacts
  expose range, state, and Low reliability without source packets, financials, input provenance,
  or practical-policy records.

## Independent challenge

- Terra Medium audited counts, sources, dates, units, public/private agreement, deterministic
  equality, sanitizer idempotence, and serving hashes. Final verdict: PASS, no Important or
  Critical issue.
- Sol High substitute independently recalculated the seven results, challenged model suitability,
  bridge bounds, bank accounting, CRM dilution, O's AFFO arithmetic, sensitivity direction, and
  disclosure parity. Four Critical issues and later transparency issues were fixed before the
  final candidate. Final verdict on the exact final artifacts: PASS, no Important or Critical
  issue.

## Determinism and regression evidence

- Practical final runs A/B contain the same files and bytes; tree hash:
  `8a3e601e42162b6cf00fd23f106f344f3acac5fe3cf3c7a4cf5ef87a4f835684`.
- Practical report SHA-256 A/B:
  `cabcd43184b1e95063548fcb2b7e7247a959b107eb94ea9ccdb8fcc644534696`.
- Strict comparison runs A/B are identical; tree hash:
  `e85d66322c10e7d5754b9663b98ceae5dc8437e672ea3c5a72479d6495610385`.
- The 106-company difficult-corpus replay remained deterministic: 104 valid private, 94
  source-verified, 1 Low numeric, 6 build errors, 4 source-integrity failures, 0 unsafe
  promotions, 0 public-contract failures, and no serving changes. Report SHA-256 A/B:
  `db42ad8e0fe91487c44971ff0672145ef42b7b45cdd6ddcca036407c9b350f4c`.
- Focused policy/bridge/model/runner/API suite: **220 passed, 3 skipped**.
- Complete backend suite: **1068 passed, 3 skipped**, with one existing Passlib/Python `crypt`
  deprecation warning.

## Real consumer verification

- A real localhost FastAPI process used only the isolated final staged-public directory.
- `GET /api/us-valuations` returned HTTP 200 and exactly 10 items.
- All 10 detail requests returned HTTP 200 and agreed with list base/state/reliability.
- Seven details contained finite ordered positive ranges and Low reliability; WDC, DELL, and NEE
  contained null ranges and remained withheld.
- Public responses contained no `financials`, `source_manifest`, `input_provenance`, or
  `practical_policy`; importing the FastAPI serving path loaded zero Arelle modules.
- The server shut down cleanly. No UI code changed, so browser verification was not required for
  this API/policy phase.

## Serving protection and stop gate

The runner recorded identical before/after hashes for every serving root:

- `backend/app/data/us_valuations`:
  `f68fd4d359e7e20dbf5daff4fddd91caa76d68cf95d3559702d4c80ae53d2c04`
- `frontend/public/data`:
  `5157530c9c4baf3e9d5e6b0455a54579c94a5ead79c07145d9f4d35aef0e7017`
- `frontend/src/research/generated`:
  `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`

Batch 01 is **verified — user confirmation needed**. Stop here. Do not promote, start Batch 02,
merge, deploy, or modify main.
