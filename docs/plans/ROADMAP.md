# FinSight whole-universe valuation roadmap

Date: 2026-08-14

This roadmap supersedes the earlier 450-company, five-grade, and normal-`Unavailable` plan. The approved product target is one numeric intrinsic value and the same public features for exactly 500 companies, with `High`, `Medium`, or `Low` reliability.

## Definition of done

Done means the source-linked accounting pipeline, correct valuation model, generated artifact, API, and user interface work end to end on the frozen 500-company universe; the replay and point-in-time backtest are reproducible; no unsafe input is hidden; and the user confirms the result.

Tests alone are not completion. Each phase requires the real-data or consumer-path evidence named below.

## Verified starting point

- The repository contains 206 generated U.S. valuation artifacts, not a canonical 500-company manifest.
- The difficult Arelle corpus previously parsed 104 out of 104 attempted filing packages.
- Parsing did not clear the old publication gate: all 104 tested companies remained withheld.
- The main cause was policy order: unresolved details blocked valuation before their economic impact was measured.
- The approved V1 thresholds are source-informed but have not been replay-validated.

## Phase 1 — NOW: evidence-aware reliability pipeline

Detailed plan: `docs/superpowers/plans/2026-08-14-evidence-aware-reliability-pipeline.md`

### Inherited evidence-aware bridge policy gate (2026-08-13)

Evidence: `docs/audit/02-evidence-aware-bridge-replay.md`. Overall tooling
status: **verified — user confirmation needed**.

| ID | What | Status |
|---|---|---|
| **BP1** | Structural shadow serialization and non-authority boundary | **✔ FIRSTHAND VERIFIED** — 104/104 cached filings parsed; 545/545 decisions carry a shadow `availability_candidate`; all publication effects remain `none_shadow_only`. |
| **BP2** | Source-linked availability schema and exact modern/legacy replay | **✔ FIRSTHAND VERIFIED** — strict serialization tests pass; 104 real legacy private artifacts reconstruct without mutation or synthesized total-debt evidence. |
| **BP3** | Deterministic bridge-policy corpus replay | **✔ FIRSTHAND VERIFIED** — 106 candidates counted, 104 valid plus ADBE/SNPS invalid, all 106 withheld, byte-identical rerun, zero serving writes. |
| **BP4** | Activate bounded-review eligibility | **⏸ WITHHELD PENDING EVIDENCE** — zero real bounded candidates and five requested current private artifacts are absent; no production promotion is authorized. |

## Inherited evidence-branch model notes
| ID | What | Status |
|---|---|---|
| **M1** | Insurance (SIC 6300-6411) → residual income | **✔ DONE** — AIG $88, PGR $70, TRV $222 (review_required, live) |
| **M3** | Securities/credit (6200-6299 / 6100-6199) → residual income | **✔ DONE** — GS $543, MS $95, AXP $83 (live) |
| **M2** | **REIT FFO/NAV model** (65/67xx, ~15: O/PLD/WELL) | **remaining — LARGE** (genuinely new model; FCFF/RI don't fit REITs) |
| **M4** | Commodity/energy reserve-aware (~40: CVX/OXY/FCX) | **remaining — LARGE** (FCFF runs but reserves/cycle distort; needs care before publish) |
| **M5** | Remaining tail archetypes (agriculture, misc) | remaining — small |

| ID | Work | Source gap | Severity | Verify method | Status |
| --- | --- | --- | --- | --- | --- |
| P1.1 | Integrate `feat/evidence-aware-bridge-policy` into the whole-universe branch | Evidence/Arelle code is on a separate branch | P0 | Full backend suite plus immutable baseline replay | NOW |
| P1.2 | Add pure `High`/`Medium`/`Low` reliability engine | Reliability logic does not exist | P0 | Exact 5%, 20%, and 40% boundary tests | Pending |
| P1.3 | Carry trustworthy annual company facts forward for up to 365 days | Annual backup is currently rejected as stale | P0 | Real normalizer fixture at 365/366-day boundary | Pending |
| P1.4 | Replace the 1% cutoff with impact-based reliability | Finite uncertainty currently withholds values | P0 | Pipeline tests and finite low-reliability result | Pending |
| P1.5 | Add reliability to safe artifacts and API | Public schema exposes publication state, not reliability | P0 | Real list/detail API responses agree | Pending |
| P1.6 | Replay the difficult corpus and audit fairness | Threshold effects are unverified | P0 | Cached replay with denominators, grades, and near-boundary cases | Pending |
| P1.7 | Verify the complete phase through the API | Tests are not end-to-end proof | P0 | Live local API consumer flow and serving-data integrity check | Pending |

Phase gate: source evidence remains fail-closed, finite fallback uncertainty lowers reliability instead of erasing values, and the difficult-corpus replay is explained with exact denominators.

## Phase 2 — freeze and ingest the 500-company universe

| ID | Work | Severity | Verify method | Status |
| --- | --- | --- | --- | --- |
| P2.1 | Recover and prove the intended historical 500-company list; if it cannot be proven, ask the user before substituting another universe | P0 | Source URL/artifact, exactly 500 issuer-level rows, unique CIKs | Pending |
| P2.2 | Add a dated, versioned canonical manifest | P0 | Schema tests and exactly one row per issuer | Pending |
| P2.3 | Acquire or reuse source-linked filing packages for every manifest member | P0 | One explicit ingestion status per 500 issuers; no silent drops | Pending |
| P2.4 | Run Companyfacts first and Arelle second for unresolved/custom facts | P0 | Full-universe extraction report with source and period coverage | Pending |

Phase gate: exactly 500 issuers are frozen and every issuer has one explicit accounting-ingestion result.

## Phase 3 — correct model lanes and complete numeric coverage

| ID | Work | Severity | Verify method | Status |
| --- | --- | --- | --- | --- |
| P3.1 | Re-verify existing FCFF/EPV, residual-income, DDM, and FFO routes | P0 | Lane registry test for every issuer | Pending |
| P3.2 | Add governed specialist lanes for commodities, captive finance, short-history/pre-profit, digital assets, and IFRS filers | P0 | Real representative issuers and lane-specific tests | Pending |
| P3.3 | Add company-history and conservative sector-estimate fallbacks without silent zeros | P0 | Source provenance, range calculation, and `Low` cap tests | Pending |
| P3.4 | Produce finite low/base/high values and one reliability label for all 500 | P0 | 500/500 replay with no missing denominator | Pending |

Phase gate: every company has one economically suitable model, finite low/base/high values, and `High`, `Medium`, or `Low` reliability.

## Phase 4 — consistent public product

| ID | Work | Severity | Verify method | Status |
| --- | --- | --- | --- | --- |
| P4.1 | Add a governed current-price source and under/over calculation | P0 | Source timestamp, unit/currency checks, hand calculation | Pending |
| P4.2 | Update the U.S. valuation UI to show value, range, price difference, and reliability for every company | P0 | Browser-driven list and detail flow | Pending |
| P4.3 | Keep features identical across `High`, `Medium`, and `Low` | P0 | UAT across one company per label | Pending |

Phase gate: the real UI provides the same features for all labels and matches the API.

## Phase 5 — backtest, fairness, and release evidence

| ID | Work | Severity | Verify method | Status |
| --- | --- | --- | --- | --- |
| P5.1 | Build a point-in-time historical valuation runner with no look-ahead data | P0 | Frozen historical inputs and look-ahead checks | Pending |
| P5.2 | Test whether reliability labels separate stronger from weaker outcomes | P0 | Results by lane, label, and observation count | Pending |
| P5.3 | Escalate suspected unfair thresholds before changing them | P0 | Affected count, boundary examples, and proposed adjustment | Pending |
| P5.4 | Run the final 500-company API/UI UAT and obtain user confirmation | P0 | Complete evidence pack and user sign-off | Pending |

Phase gate: results are reproducible, thresholds are either supported or explicitly brought to the user, and the user confirms the real product.
