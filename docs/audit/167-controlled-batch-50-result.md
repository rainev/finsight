# Controlled Universe Reset Batch 50 Result

Date: 2026-09-12
Status: user-confirmed; bookkeeping verified.

## Exact outcome

Batch 50 retained the exact frozen denominator: **AMT, CSGP, SPG, HST, CBRE, EXR, DLR, PSA, INVH and VICI**.

- Pass: **0/10**
- Conditional Low: **10/10**
- Withheld: **0/10**
- Numeric: **10/10**

| Ticker | Route | Low | Base | High | Why Conditional |
| --- | --- | ---: | ---: | ---: | --- |
| AMT | Tower-REIT AFFO DCF | $145.89 | $155.95 | $167.51 | Tenant churn, foreign/FX, CoreSite/JV, leverage and refinancing |
| CSGP | Operating enterprise FCFF | $15.71 | $17.77 | $20.46 | Homes.com investment, acquisitions, software, SBC and marketplace cash conversion |
| SPG | Retail-REIT owner-cash DCF | $153.20 | $163.76 | $175.89 | Redevelopment, tenant capital, platform investments, JV/preferred units and leverage |
| HST | Lodging-REIT owner-cash DCF | $17.15 | $18.33 | $19.69 | RevPAR/Maui recovery, renovation capital, dispositions and hotel/JV scope |
| CBRE | Operating enterprise FCFF | $54.32 | $64.54 | $77.68 | Advisory cycle, working capital, acquisitions, warehouse funding, leases and NCI |
| EXR | Self-storage AFFO proxy DCF | $97.86 | $104.60 | $112.35 | Issuer AFFO unavailable; explicit PSA/INVH owner-cash proxy is Low-only and Pass-ineligible |
| DLR | Data-center AFFO DCF | $99.73 | $106.61 | $114.50 | Development, power, JV/foreign, preferred and financing risks; insurance recovery retained as sensitivity |
| PSA | Self-storage FAD DCF | $209.10 | $223.52 | $240.07 | NSA/PS Canada integration, financing, occupancy, development and preferred claims |
| INVH | Single-family-rental AFFO DCF | $21.72 | $23.21 | $24.93 | Insurance, turnover, transactions, securitization, JV/OP units and leverage |
| VICI | Gaming net-lease AFFO DCF | $32.38 | $34.61 | $37.17 | Tenant concentration, lease coverage, acquisitions, CECL, units and cutoff financing |

## Important controls and repairs

- The manifest's `reit_affo` partition label was not treated as a formula. CSGP and CBRE are operating real-estate
  service companies and use five annual plus current-TTM enterprise cash-FCFF history.
- REIT ranges lock normalized owner cash and vary only the discount rate. CSGP/CBRE also lock normalized FCFF, growth
  and the current bridge while varying WACC; no stacked-tail range is presented.
- DLR's H1 AFFO was reduced by the exact $187.871m net promote before conversion. Exact-dollar conversion is
  `(1,563.339 - 187.871) / 1,483.956 = 0.9268927111`; the earlier promote-leaking candidate was discarded.
- CSGP/CBRE public calculator growth fields and Conditional confidence labels were repaired and replayed.
- EXR uses explicit policy `BATCH-50-EXR-OWNER-CASH-PROXY-1.0`, with cutoff-safe PSA/INVH source accessions. It is
  Conditional Low only and cannot become Pass without issuer-specific recurring-capital evidence.
- Missing values were never converted to zero. Preferred absence for CSGP/CBRE is based on complete statement scope;
  authorized shares alone were not treated as an issued claim.

## Independent challenge and deterministic replay

Three Luna High reviewers separately challenged source identity/values, economic routing/calculation and public
calibration. Sol reconciled their findings and repaired all Critical, Important and Minor findings.

- Final candidates: `output/batch-50-history-run-e-20260912` and `output/batch-50-history-run-f-20260912`; all 20
  private/public artifacts and both reports are byte-identical.
- Report SHA-256: `f0c6a7b0dbd1cb8ce565022b7c44d44fbc45813c8efccd85f8cce1fc4663d273`.
- Candidate-tree SHA-256: `56bf55d52041a9f28a732e1557482abf7a4632973235280cfeb76b12f4c78f5c`.
- Focused Batch 50 and calculator tests: **15 passed**.
- Complete backend suite: **2,371 passed / 3 skipped**.
- Frontend TypeScript and production Vite build: **passed** (`1,694` modules transformed).
- Deterministic cumulative catalogs: `output/batch-50-api-runtime-a` and `output/batch-50-api-runtime-b`; both contain
  exactly **500** artifacts and share manifest SHA-256
  `c80a26aff4b4760a34c042d13a83ca93dbc096513e9847ebc73a9188a3f2ee8c` and artifact-tree SHA-256
  `8f8f22cd9f9750218295adb854a1be6f077ae7399f5e492b3c38fe3a970d76fc`.
- Cumulative candidate: **500 = 116 Pass / 358 Conditional / 26 Withheld**, numeric **474/500**.
- Real isolated API: **500/500** list/detail exact catalog parity, **500/500** calculator-default parity, zero private
  leaks and zero forbidden serving imports. Launch-first receipt SHA-256:
  `98ff8f975e2260977ce8548f2bd8626e540b4dc7e26d230b9761079373526789`; official-evidence receipt SHA-256:
  `edda81765527c205e632f6643861bf83a1e9c7a671efcc1063ceb40bb17d1b35`.

## Boundary

The user confirmed the result. All ten Batch 50 Conditional companies were appended to the Recovery Learning Watchlist;
no company was withheld, so no recovery attempt or new cumulative-withheld entry was needed.

- Recovery Learning Watchlist: **384** total — **358 Conditional / 26 Withheld**; SHA-256
  `45a59d5216f7513331342f1715a6784b40176913775c0f55c289ac1b3a271f8b`.
- Cumulative automatic-withheld register: unchanged at **36** entries; SHA-256
  `f1507416aefdc01113104902c13c62ebc97954832c048fe03bb80b195e565ee4`.
- Final bookkeeping/model contract tests: **14 passed**.

Serving artifacts remain unchanged. Final universe review, serving promotion, merge, push and deployment require
separate authorization.
