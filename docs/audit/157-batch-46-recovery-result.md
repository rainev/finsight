# Batch 46 Recovery and Conditional Publication Result

Date: 2026-09-08
Status: user-confirmed; Conditional publication, verification and bookkeeping complete.

## Final outcome

The one authorized recovery attempt covered exactly **EIX, AES, PCG and SRE**. After seeing why their source state
remained incomplete, the user explicitly authorized transparent Conditional Low publication with prominent warnings.

- Recovered to Conditional: **4/4**
- Still Withheld: **0/4**
- Final Batch 46: **0 Pass / 10 Conditional / 0 Withheld**, numeric **10/10**

| Ticker | Bear | Base | Bull | Final status |
| --- | ---: | ---: | ---: | --- |
| EIX | $29.72 | $52.86 | $77.27 | Conditional Low |
| AES | $10.58 | $12.01 | $13.95 | Conditional Low |
| PCG | $8.94 | $15.04 | $22.09 | Conditional Low |
| SRE | $36.15 | $41.83 | $49.58 | Conditional Low |

These are conservative decision baselines, not reported facts, statistical confidence intervals, price predictions or
recommendations. Actual value may fall outside the ranges.

## EIX — moderated wildfire-stressed residual income

- Reported parent common equity: **$17.446B** after the $83M preferred claim.
- Reported wildfire accrual: **$1.434B**; H1 wildfire loss/recovery: **$512M / $511M**.
- The $4.3B Wildfire Fund maximum-liability and $21B claim-capacity facts are context, not total EIX exposure caps.
- Incremental governed claim stress: **$4.3B / $1.0B / $250M**.
- Shares: **390.586M / 384.814M / 379.042M**; sustainable ROE: **9% / 10% / 11%**.

Booked accruals and recoveries remain inside reported equity/assets and are not deducted or added twice. The range warns
that future claims, insurance exhaustion, fund sufficiency, CPUC/FERC recovery, securitization and parent/SCE funding
remain unresolved.

## AES — sale-gain-normalized parent residual income

- Parent common equity: **$4.942B**; shares: **713.439M**.
- FY2024/FY2025/TTM sale-gain-adjusted ROE: **36.44% / 20.72% / 37.18%**.
- Governed recurring ROE: **31.45%**, the mean of those three source-linked observations.
- TTM sale gain: **$198M**; TTM impairment activity: **$474M**.

Sale gains are removed, while impairments are not added back because future asset returns are not source-proven. NCI
$4.830B and temporary/redeemable equity $3.052B remain explicit scope controls and are not double-deducted from parent
common equity. Cost of equity alone varies at **9.5% / 8.5% / 7.5%**.

## PCG — wildfire and share-denominator-stressed residual income

- Parent common equity: **$32.322B** after $1.579B preferred; NCI: **$252M**.
- Wildfire claims/class accrual: **$309M / $300M**.
- Dixie possible loss/settlement/Fund receivable: **$2.250B / $2.049B / $244M**.
- Incremental governed claim stress: **$1.0B / $500M / $100M**.
- Shares: **2.680B / 2.285B / 2.201B**, explicitly reflecting the cover-versus-basic/diluted conflict.
- Sustainable ROE: **8% / 9% / 10%**.

The $5.1B rate-base disallowance context is not treated as a complete future loss cap. The warning preserves future
wildfire, inverse-condemnation, regulatory recovery, preferred-conversion, bond and share risk.

## SRE — pre-transaction parent residual income

- Parent common equity: **$32.685B**; TTM common earnings: **$2.262B**; shares: **653.900M**.
- Current parent ROE: **7.038%**; terminal ROE **7.5%**; payout **65%**; terminal growth **2%**.
- SI held-for-sale assets/liabilities/debt: **$32.939B / $12.992B / $9.027B**.
- Ecogas expected gain: **$165M–$205M**; parent after-tax: **$57M–$77M**.

The value is explicitly pre-KKR and pre-Ecogas. No transaction proceeds, retained-ownership benefit, project-debt
change or future capital-plan value is added. Cost of equity alone varies at **9.5% / 8.5% / 7.5%**.

## Independent challenge

Three Luna High reviewers independently challenged EIX/PCG wildfire and share stresses, AES earnings normalization and
SRE's pre-transaction boundary. Sol replayed every scenario, checked sensitivity directions and verified no claim,
recovery, NCI, temporary equity or transaction proceed was double-counted or replaced with zero.

No unresolved Critical, Important or Minor implementation finding remains. All four remain Conditional Low because
their unresolved economic risks are real and explicitly disclosed.

## Determinism and verification

- Final candidates: `output/batch-46-recovery-run-d-20260908` and
  `output/batch-46-recovery-run-e-20260908`; reports and all private/public artifacts are byte-identical.
- Recovery tree SHA-256: `809a9a5a608d5d6a82b5d0999182be7c80e3fc3e3630a281e7405e62583a581e`.
- Recovery report SHA-256: `bbf659f7d47548ceff2a1206986da00be0dd39636175c1bd4cccd27a90b4cb2d`.
- Focused Batch 46 initial/recovery/bookkeeping tests: **21 passed**.
- Complete backend regression: **1,850 passed / 3 skipped / 0 failed**.
- Frontend production build: **passed** (`1,694` modules transformed).
- Immutable catalog: `US-RESET-2026-08-14-B01-B46-RECOVERY-1.1`; two builds are byte-identical.
  Manifest SHA-256: `7da0d33c931b034b47bed60c958e82d2067852bf4b1940a8eee6bf1d5919f3b1`;
  artifact-tree SHA-256: `bc0a3970e7e4a32e098f132a09d2ef8747c9049f10e3816a943fda4c8aa4eeb7`.
- Real isolated API: **460/460** list/detail exact catalog parity, **460/460** calculator-default parity, zero private
  leaks and zero forbidden serving imports. Evidence receipt SHA-256:
  `e62e0e8cd321a69306ab2eda9c748f5bd20749ff1c3191d136f32cdf89a9aa33`; calculator receipt SHA-256:
  `94af1a4090692568ccc691df80e0d24814a2a359348d52de8356ebddce5f137d`.

## Confirmation and bookkeeping

The user explicitly instructed FinSight to include these four companies in Conditional publication and then confirm the
result. Once final verification completes, the confirmed 460-company universe is **116 Pass / 323 Conditional / 21
Withheld**, with **439/460 numeric**.

All ten Batch 46 issuers are recorded on the Recovery Learning Watchlist. EIX, AES, PCG and SRE record
`recovery_outcome=conditional_numeric_low`; none is appended to the cumulative withheld register. Batch 47, serving
promotion, merge, push and deployment remain outside this authorization.

The Recovery Learning Watchlist now contains **344 companies: 323 Conditional / 21 Withheld** and has SHA-256
`b9d184c8b43631f4bdce076e912eb2bc296b6e2dc686ec10900e100592d64304`. The cumulative automatic-withheld history
remains unchanged at 31 entries with SHA-256
`93e91a447b0836f168ccc050165a01c1cba7613434f3ed45e6a559ee45345d22`. Existing serving artifacts remain unchanged.
