# Audit 21 — PSE V2 Phase B Batch 11

**Status:** frozen ten implemented, staged, results-confirmed, separately activated locally, live-verified, and user-confirmed on 2026-09-23. Batch 10 remains preserved for rollback.

## Reference and gaps

- Confirmed set: `SMC, LTG, AGI, COSCO, FDC, FPH, ANS, LPZ, APO, TFHI`.
- All ten are diversified or layered holding companies. Their primary intrinsic route is attributable SOTP, including parent-only claims and ownership. The component bridges are incomplete, so a reported-book-value P/B screen is published separately, provisionally, with Low reliability.
- Before Batch 11, there was no source-bound route or candidate for these ten. The confirmed parent catalog contained exactly 108 issuers. The batch-specific source, routing, overlap, and candidate gaps are addressed within this frozen scope; unresolved SOTP economics remain explicitly disclosed, not treated as complete intrinsic valuations.
- [PSE financial summaries](https://edge.pse.com.ph/) provided FY2025 annual and 1H2026 interim context and reported 1H2026 book value per share. The source receipts contain the official links, period, unit, normalized metric, and hash, but not redistributed filing copies. They are labeled as summaries, not as original 17-Q filings. Publication dates and source pages were not established from the summary pages; this limits provenance depth and remains a follow-up for an intrinsic SOTP review. The PSE page states that access/download is for personal, non-commercial use unless otherwise stated; commercial automated acquisition or redistribution rights are **not confirmed** and require review before broader use.

## Batch 11 values per share

All figures are PHP per share. Low/base/high are **market-relative P/B screens**, not intrinsic SOTP values or additive holdings values. The P/B bands are analyst screening assumptions, not peer-calibrated multiples.

| Ticker | PSE financial summary | P/B band | Low | Base | High |
|---|---|---|---:|---:|---:|
| SMC | [PSE](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=154) | 0.25/0.40/0.55 | 22.0250 | 35.2400 | 48.4550 |
| LTG | [PSE](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=12) | 0.45/0.60/0.75 | 10.8000 | 14.4000 | 18.0000 |
| AGI | [PSE](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=212) | 0.45/0.60/0.75 | 18.1485 | 24.1980 | 30.2475 |
| COSCO | [PSE](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=50) | 0.45/0.60/0.75 | 11.0835 | 14.7780 | 18.4725 |
| FDC | [PSE](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=75) | 0.45/0.60/0.75 | 11.2815 | 15.0420 | 18.8025 |
| FPH | [PSE](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=197) | 0.25/0.40/0.55 | 119.2600 | 190.8160 | 262.3720 |
| ANS | [PSE](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=14) | 0.45/0.60/0.75 | 14.0895 | 18.7860 | 23.4825 |
| LPZ | [PSE](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=61) | 0.25/0.40/0.55 | 6.4175 | 10.2680 | 14.1185 |
| APO | [PSE](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=52) | 0.45/0.60/0.75 | 1.3725 | 1.8300 | 2.2875 |
| TFHI | [PSE](https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=650) | 0.25/0.40/0.55 | 109.3925 | 175.0280 | 240.6635 |

All ten artifacts are `market_relative_only` and `provisional`. Their intrinsic scenario values are null. The SMC–TFHI, LPZ–FPH–FGEN, AGI–EMI/MEG, COSCO–PGOLD/KEEPR, and APO–resource company overlaps are called out in warnings; corresponding per-share screens must not be added. There is no dated market-price comparison.

## Evidence and verification

- Cumulative staged candidate: 118 exact artifacts — 34 intrinsic, 84 market-relative, 0 unavailable; all 118 provisional.
- Persistence: 10 securities, 10 current hashed source receipts, 10 current reported facts, 30 assumptions, 10 current runs, and 10 verified current MinIO objects. Ten superseded receipts/runs from the initial source-label draft remain as immutable local history; the verifier selects only hashes matching the final candidate.
- Deterministic twin builds were byte-identical. The final candidate manifest SHA-256 is `82481331464c9910fc80c79215ef9c0ead4d709238bd2f2d3c0f3f101f684974`; the pointer loader validated every manifest entry and internal artifact hash.
- Real authenticated staged API after the source-label correction: 118/118 stored-detail parity, 10/10 calculator parity, unauthenticated 401. SMC base was PHP35.24; a 0.5x edit produced PHP44.05 and persisted scenario `#26`.
- Real staged browser after the source-label correction: SMC displayed PHP35.24, a 118-company footer, a market-relative/provisional label, and the PSE financial-summary source link. Editing the multiple to 0.5x displayed PHP44.05 and saved scenario `#27`. TFHI displayed PHP175.03 with the SMC overlap warning; LPZ displayed PHP10.27 with the FPH/ABS overlap warning.
- Full backend regression: 373 passed, one pre-existing `crypt` deprecation warning. Frontend production build passed with the existing large-chunk warning.
- The active Batch 10 pointer SHA-256 remains `08b448c02edaf2e4f93bb1f307b8f9bad85bc90279cfbbb685d35387fe74f2a6`; its manifest remains `d835ccf5a75b9728a76e7a01f89a7fcc1054e06cf7564070f3f9c1973dbd5018`. Batch 11 is absent from the serving root. The activation guard now pins the exact confirmed candidate hash, but activation has not been run.

## Gate

**Verified and user-confirmed on 2026-09-23.** This confirmation accepts the staged Batch 11 results only. Local activation requires a separate explicit request; no deployment, push, Batch 12, or Phase C work is authorized.

## Local activation

- The user separately authorized local Batch 11 activation on 2026-09-23. `active.json` and `staged.json` now select `PSE-V2-PHASE-B-B11-2026-09-23-1.0`, exactly 118 issuers. Active pointer SHA-256: `795bd88681e26e70565743058887f1fa19ac8ac09a49b43c6f0900032c36c227`; manifest SHA-256 remains `82481331464c9910fc80c79215ef9c0ead4d709238bd2f2d3c0f3f101f684974`.
- The active catalog's 129 files are byte-identical to the confirmed candidate. The Batch 10 rollback manifest remains unchanged at `d835ccf5a75b9728a76e7a01f89a7fcc1054e06cf7564070f3f9c1973dbd5018`.
- Real active API: 118/118 stored-detail parity, 10/10 calculator parity, unauthenticated 401, and SMC's 0.5x scenario persisted as `#28` (PHP35.24 baseline, PHP44.05 edited).
- Real active UI: switched from US to PH, selected SMC via search, saw the 118-company footer and market-relative/provisional status, recalculated PHP35.24 to PHP44.05 at 0.5x, and saved scenario `#29`. TFHI rendered PHP175.03 and the SMC overlap warning. The initial browser pass briefly encountered the normal rate limit while the API sweep was running; a sequential repeat passed without that error.
- Persistence: 10 current receipts/facts/runs/objects and 30 assumptions verified. Frontend production build passed. The full backend suite initially failed 25 tests whose historical builder guards and active-list expectation stopped at Batch 10; after updating only those successor expectations, **373 backend tests passed**. Pinned parent manifest hashes and valuation artifacts were not changed.

**Activation status:** locally active, live-verified, and user-confirmed on 2026-09-23. The usual site on port 4000 was not running during verification; isolated ports 4020/4021 were used and then closed. No deployment, push, Batch 12, or Phase C work occurred. The commercial-use/source-rights caveat above remains open for broader use.
