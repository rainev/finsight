# Audit 22 — evidence policy and public/private integration

Reference: `/Users/carlosconda/Downloads/PLAN.md` Phase 4, lines 127–148.

## Ours today

✔ `FieldAvailability` already models current structural/reported aggregates, annual carry-forward, company history, sector estimates, conflicts, and bounded uncertainty (`field_availability.py:15-56`). `bridge_policy.py:647-712` fail-closes non-production, stale, nonissuer, invalid, or incomplete-source evidence and preserves finite ranges.

✔ Structural resolver output currently projects to shadow authority only (`field_availability.py:546-575`); reviewed promotions are batch/fingerprint-specific rather than an official-source exhaustion pipeline.

✔ The public artifact contract is explicit allowlists (`artifacts.py:322-385`, `570-615`), and the router sanitizes both list/detail reads (`routers/us_valuations.py:48-84`). This is the correct boundary to regression-test, while all new evidence remains private.

✔ Arelle imports are isolated in `arelle_worker.py`; serving router imports only artifact sanitization. The current pipeline methodology still names Companyfacts/submissions/filing-specific tables and states some extraction is not automated (`pipeline.py:157-174`, `445-449`, `790-794`).

✔ `frontend_company()` hardcodes FCFF/EPV display policy (`artifacts.py:1886-1894`), which can mislabel specialist model output even when the private valuation route is correct.

## Reuse check

Integrate unified evidence decisions by projecting them into the existing `FieldAvailability` and bridge/specialist policies. Preserve the sanitizer/router shape and child-process parser boundary. Do not change reliability thresholds or valuation model formulas in this source phase.

## Consumer flow and backing

The required policy order must be enforced per material request, with an exhaustion receipt showing which official sources were applicable/tried and why the final point/range/unresolved outcome was selected. Current fallback names approximate the order but no orchestrator proves official-source exhaustion or carries the complete private trace into the valuation.

## Gaps

- **P0 ✔ OE4-01:** Implement deterministic source-order/exhaustion policy: current exact SEC → current regulator/supplement → current complete aggregate → annual ≤365 days → company-history range → verified sector range.
- **P0 ✔ OE4-02:** Project only complete, cutoff-safe evidence decisions into production `FieldAvailability`; retain conflicts and unresolved failures privately and fail closed.
- **P0 ✔ OE4-03:** Keep finite source-backed ranges usable with reliability caps, without turning missing points into silent zeros or authorizing unsuitable models.
- **P0 ✔ OE4-04:** Attach exact private source/arithmetic trace to every public number while ensuring no evidence candidates, excerpts, diagnostics, parser modules, or regulator payloads leak through public list/detail.
- **P1 ✔ OE4-05:** Correct specialist model identity in downstream frontend-company generation without changing the established public API schema.
- **P0 ✔ OE4-06:** Add shape snapshots, sanitizer/privacy tests, list/detail parity, staged-artifact equality, and an import assertion proving FastAPI loads neither Arelle nor regulator parsers.

Status: audit complete; all findings were rechecked firsthand in the cited files. No pipeline code changed in this batch.
