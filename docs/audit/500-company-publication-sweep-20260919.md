# 500-company publication sweep — 2026-09-19

## Decision

468 numeric estimates pass this launch screen using the existing human-approved, dated baseline: 76 baseline and 392 with disclosures. Six numeric estimates require targeted disposition before publishing them as current: BIIB, HON, INTC, JBL, MCK and LHX. The 26 already unavailable companies retain that status. This is screening against approved baselines and known correctness exceptions, not fresh financial underwriting of each company or certification of current September prices/evidence.

No valuation, availability label, release manifest or serving pointer was changed. No WG39 replacements were imported. No deployment occurred.

## Exact scope and reproducible evidence

Catalog: `output/batch-50-api-runtime-a/catalogs/US-RESET-2026-08-14-B01-B50-INITIAL-1.0`.
Manifest SHA256: `c80a26aff4b4760a34c042d13a83ca93dbc096513e9847ebc73a9188a3f2ee8c`.
Valuation cutoff: August 14, 2026. The dates must remain visible; this sweep does not refresh filings to September 19.

Commands:

```
python3 scripts/sweep_launch_500.py
python3 scripts/sweep_launch_500.py --serve
python3 scripts/sweep_launch_500.py --http
```

The isolated real FastAPI process on localhost:4189 used the existing staged pointer. Test JWT signing was local; no auth-service login, database persistence, UI, live market-price retrieval or remote deployment check is claimed. Save was false for every request. No dependency overrides were installed. The test server is stopped after verification.

Results from the fresh sweep:

| Check | Result |
|---|---:|
| Unique tickers and CIKs | 500 / 500 |
| Frozen batch coverage | 50 batches, exactly 10 each |
| Artifact hash and source-audit path checks | 500 passed |
| Identity and filing/cutoff date checks | 500 passed |
| Numeric ranges, finite and ordered with positive base | 474 passed |
| Unavailable ranges entirely null | 26 passed |
| Offline default-calculator parity / disabled behavior | 500 passed |
| Real HTTP detail range and availability parity | 500 passed |
| Real HTTP numeric default-calculator parity | 474 passed |
| Real HTTP unavailable calculation rejected | 26 passed |
| Known private-evidence-key scan | zero matches |
| Automated errors | zero |

The full company list, exact values, source identities, warnings and dispositions are in `output/launch-sweep-20260919/http-sweep.json` and `http-sweep.md`; offline results are alongside them. The checker is retained as `scripts/sweep_launch_500.py`.

## Six targeted exceptions

These are review outcomes, not automatic unavailable conversions. Prior human approval is retained, but the following newer source concerns need explicit resolution or historical-only presentation.

| Company | Concrete concern | Recommended disposition |
|---|---|---|
| BIIB | Retained recipe debt 7.2903B excludes 800M current debt identified in WG40; legal sensitivity and acquired-cash scope remain unresolved. | Correct the bridge and resolve legal/operating assumptions before current numeric promotion. |
| HON | Published warning says pre-separation baseline; WG36/37 identify completed separation and subsequent acquisition without a continuing-company bridge. | Historical-only estimate until continuing-company value is supported. |
| INTC | WG24/25 identify possible cash/AFS overlap and financing capital-payment treatment; approved margins are assumptions, not the defect. | Targeted cash/reinvestment reconciliation; preserve approved margins and negative history. |
| JBL | Deducted lease schedule concerns new leases, not demonstrated full current carrying value. | Reconcile current lease carrying and debt/FCFF overlap. |
| MCK | Ownership proxy can be accepted, but settlement cash/liability allocation and forecast overlap remain incomplete. | Review the exact retained payment proxy/disclosure; do not reopen approved ownership assumptions without contrary evidence. |
| LHX | Preferred/derivative outcome and environmental reserve/recovery overlap remain unresolved. | Review claim treatment and avoid duplicate deductions; keep approved assumptions where coherent. |

GILD/INCY retain original approved baselines. The TTM-exclusion discrepancy concerns proposed WG39 replacements and therefore does not justify substituting them or automatically withholding existing baselines.

## Existing unavailable companies

ALB, ALGN, AVB, BG, BKR, CEG, COIN, DVN, ECHO, EQR, EXE, GPN, IFF, IP, ISRG, LH, LYB, NCLH, NEE, NEM, NRG, ORCL, PSKY, UHS, VLO, VST.

Their existing evidence limitations remain attached to their artifacts. The sweep does not attempt recovery or treat general human approval as invented numeric evidence. ECHO's reason is in review errors (`MAJOR_EVENT_UNBOUNDED`, `CLAIMS_UNBOUNDED`) rather than warnings.

## Product-wide qualifications

1. **Calculator edits:** the selected launch catalog has no migrated recipe root. `calculator.py::calculate` uses a factor ratio and scales low/base/high proportionally when no recipe exists. Default reproduction is verified, exact edited-scenario engine parity is not. Launch should clearly present this as an approximate sensitivity tool or defer editing until exact recipes are wired. This is a feature qualification distinct from baseline publication.
2. **Model label:** 221 records use `conditional_estimate` as primary model. This is an availability label; show the actual model from calculator metadata or clarify presentation before claiming formula-specific results.
3. **Wide ranges:** 190 numeric ranges exceed 125% of base. These are disclosure flags, not automatic rejection. Low reliability likewise does not fail this screen.
4. **Consumer release gate:** no fresh browser/authentication/save/database or deployed-environment check occurred in this pass. Existing historical UAT is not a fresh deployment certificate. Verify the chosen release in the actual consumer environment before enabling it publicly.

## Handoff

The sweep is complete as a staged publication screen. The unchanged 474-numeric catalog should not be described as cleared wholesale: 468 pass this screen, six need explicit disposition, and 26 remain unavailable. Resolve those six and the calculator presentation decision, then validate the actual release environment. Full autonomous refresh, successive-quarter certification and additional WGs are separate work and are not blanket prerequisites for launching dated approved baselines.
