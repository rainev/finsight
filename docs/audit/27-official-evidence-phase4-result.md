# Audit 27 — FOD4 evidence-order valuation integration result

Status: **verified projection boundary and real staged API; superseded by Audit 28 for consumer replay**

Reference: `docs/audit/22-evidence-policy-integration.md` and PLAN Phase 4.

## Implemented

- Each material request declares applicable tiers and records one terminal attempt for Companyfacts current, structural XBRL, filing table, regulator/SEC supplement when applicable, current aggregate, annual carry-forward, company history, and sector range.
- Precedence follows the acquisition flow while preserving conflicts among comparable current sources. A source is exhausted only when every declared tier has a value, blocker, failure, or explicit no-candidate result.
- Attempts retain filed lineage, source URL, unit, entity, consolidation, candidate identity, and aggregate coverage. Existing current availability without verifiable filing metadata is diagnostic-only.
- Annual point/range carry-forward remains carried and cutoff-limited; a bounded annual range remains `bounded_unresolved`, not a disguised reported midpoint.
- Generic peer ranges remain rejected. Only a `source_kind=sector_range`, `evidence_class=bounded_estimate` production range can enter the bounded bridge at a Low cap.
- `build_us_valuation()` accepts typed evidence projections through the existing bridge normalizer, records private availability/consumption/diagnostics, and keeps that entire trace outside the public allowlist.
- Specialist model routes are guarded by source family. Because FOD3 produced zero promotable packets, specialist inputs remain explicitly shadow-only and do not enter equity models.
- Downstream frontend-company model identity now uses the declared public primary/supporting models instead of hardcoded FCFF/EPV.

## Deterministic policy evidence

### Batch 01

- Manifest now includes model-specific bank/utility/REIT requests: 125 requests/decisions total.
- Final policy A/B hash: `ddee057519232d697125a9b8ae3ab8c9809e02dcbbd47c454de15850658e8310`.
- Outcomes: 30 reported, 11 explicit zero, 6 bounded estimate, 78 unresolved.
- Selected tiers: 40 current Companyfacts, 1 exact structural filing, 6 annual carry-forward; 47 projectable private availability records; zero projection failures/conflicts.
- Twenty-five field-specific specialist attempts are exact non-promotable blockers; unrelated fields receive no specialist blocker.

### Batch 02

- Final policy A/B hash: `68c2f4e4f31bd50a9932b0795867211560ec1d48bccc11dd2063929dd8868cdd`.
- Outcomes: 28 reported, 7 bounded estimate, 65 unresolved.
- Selected tiers: 24 current Companyfacts, 4 strict filing-table observations, 7 annual carry-forward; 35 projections; zero failures/conflicts.
- Earlier OMC table-versus-Companyfacts differences are not silently resolved: the Companyfacts rows are Q1/stale relative to the Q2 controller and fail filed/accession-period eligibility, so current Q2 table observations are selected with full lineage.

Every request has `exhausted=true` only after all declared tiers are present. Protected serving hashes are identical before/after.

## Public boundary and real API

- Final API-stage A/B report SHA-256: `ef2b8d47a74ea5d44c20a925cef611868baca6e7674f2c6d2c07d49a999787bf`.
- Final 20-file stage tree SHA-256: `2c450db911ad958d897b79ae6bce3e45c3a669e10846c7b77f8b0b6b5574cff2`.
- 20 artifacts carry 225 private policy decisions; sanitizer parity against the unaugmented baseline is exact; private leak count 0.
- A real localhost FastAPI process served `/api/us-valuations`: list HTTP 200/count 20; all 20 detail calls HTTP 200; every detail exactly matched the sanitized staged artifact.
- Public states remained 11 `review_required` and 9 `withheld`; primary model families remained `ddm`, `fcff_dcf`, `ffo`, and `residual_income`.
- Serving import audit found zero `arelle`, bank-regulatory, FERC, REIT-supplement, or official-ingestion modules.

## Automated verification

`374 passed, 3 skipped in 1.58s` across evidence policy/boundary, field availability, bridge policy/pipeline, complete U.S. valuation, and routing suites. The three skips are existing optional-capture skips. `git diff --check` passed.

Conclusion: this phase proved projection and public-boundary behavior. Audit 28 subsequently exercised those projections through the real valuation consumer, fixed table cutoff lineage and merge-boundary defects exposed there, and is the controlling end-to-end result.
