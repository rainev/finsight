# Launch-first valuation routing gap

Reference: user-supplied `FinSight Launch-First Valuation Plan`, sections 1, 2, 6, 7, and 9.

## Reference

FinSight should try a governed primary intrinsic model, consolidated fallback, normalized cash-flow
or earnings DCF, conditional/standalone baseline, and finally a clearly labeled relative baseline.
Withholding is reserved for identity/share/currency failures, contradictory evidence, no suitable
economic object/model/peers, unusable values in every reasonable scenario, or public-safety failure.

## Ours today

- The generic pipeline dispatches one configured primary family and has only a consolidated segment
  fallback (`backend/app/us_valuation/pipeline.py:684`, `backend/app/us_valuation/pipeline.py:810`).
- The public model allowlist already knows FCFF, FCFE, residual income, DDM, FFO, and conditional
  estimate (`backend/app/us_valuation/artifacts.py:172`).
- Batch-specific practical engines already provide normalized enterprise cash FCFF, bank residual
  income, utility FCFE, AFFO, and conditional scenario arithmetic
  (`backend/app/us_valuation/practical_models.py:1`,
  `backend/app/us_valuation/batch_02_conditional_estimates.py:1`).
- Batch 03 is frozen at 3 numeric / 7 withheld; the seven are LYV, ECHO, GOOGL, APP, FOXA, TKO,
  and PSKY (`backend/app/us_valuation/batch_03_practical_models.py:27`,
  `docs/audit/36-controlled-batch-03-initial-result.md:5`).
- Firsthand serving read: 206 artifacts, 88 numeric bases, 118 withheld; 192 use
  `US-VALUATION-RESULT-1.0` and 14 use `US-PUBLIC-VALUATION-1.0`.

## Reuse check

Reuse `EnterpriseCashFlowState`, `enterprise_cash_flow_dcf`, existing equity-model dispatch,
conditional-estimate arithmetic, reliability thresholds, artifact sanitizer, and frozen batch runners.
Do not add a parallel extractor or specialist model merely to satisfy coverage.

## Flow

Today a generic FCFF bridge/model failure can terminate in `withheld` before a different economic
baseline is attempted. Batch-specific conditional work proves another route can be generated, but it
is not one shared fallback decision. The consumer therefore sees older serving artifacts rather than
the staged launch-first outcomes.

## What backs it

- Focused routing/artifact/Batch 03 run on 2026-08-25: 114 passed, 3 skipped, 1 warning.
- `output/batch-01-recovery/final-confirmation-a/batch-report.json`: 9 numeric / 1 withheld.
- `output/batch-03-controlled/candidate-g/batch-report.json`: 3 numeric / 7 withheld.
- Public safety is an explicit field allowlist before validation
  (`backend/app/us_valuation/artifacts.py:588`).

## Gaps

- **LF-R1 · P0 · ✔** No shared `BaselineValuation` result or table-driven fallback decision records
  method attempts, rejection reasons, availability type, range, assumptions, and warnings.
- **LF-R2 · P0 · ✔** Batch 03's seven holdouts have not received the user-authorized launch-first
  recovery pass; ordinary forecast/model uncertainty is still represented as hard withholding.
- **LF-R3 · P0 · ✔** Batch-specific conditional output is staged rather than integrated into a
  generic public contract and fallback ladder.
- **LF-R4 · P1 · ✔** Current classification/consolidated-fallback caps can force Low even when the
  plan requires confidence to follow scenario width and bounded evidence, not merely the presence of
  an internal assumption (`backend/app/us_valuation/pipeline.py:992`).
- **LF-R5 · P1 · ✔** A zero base makes relative scenario movement undefined; the existing conditional
  fallback substitutes an artificial movement value. Zero-floor equity-at-risk states need an
  explicit rule rather than ordinary percentage-width grading.
- **LF-R6 · P2 · ✔** Relative/NAV/SOTP routes are absent from the shared router. They must remain
  unavailable until suitable peer/private-price or asset evidence exists; coverage is not a quota.
