# Valuation UX and calculator correction

Status: **verified locally — user confirmation needed**. No merge, push, deployment, catalog
change, or Batch 11 work was performed.

## Product decisions

- Removed the user-facing Confidence card. Reliability labels and reasons remain unchanged in
  every public artifact/API response for governance and review.
- Removed Relative cross-check from the page after reconciling the active catalog: **0/100**
  artifacts have an available relative-value summary.
- Retained Market comparison because a user-entered market price produces a real comparison. The
  field is now named `Market price (optional)` and explicitly says it does not change intrinsic
  value.
- Consolidated the old `Valuation` and `US Valuations` navigation items into one `Valuations`
  section at `/valuations`. Both old routes redirect to the canonical path.
- Removed visible `CANDIDATE (review_required)` and reliability-cap wording from Key assumptions;
  source/model caveats remain visible without internal workflow labels.

## Calculator behavior

- Rate inputs display as percentages with two decimal places while requests retain decimal model
  precision: JPM Cost of equity displays `9.18`, Sustainable ROE `12.00`, and Terminal growth
  `2.00`.
- Editing a model assumption changes the headline scenario range and primary model card. The
  headline switches from `FinSight ... case` to `Your ... case` only after an assumption changes.
- Reset restores the exact FinSight baseline.
- Save errors are handled visibly; successful Save explains that edited assumptions and the
  resulting range are stored under Saved.

## Verification

- Active-catalog reconciliation: Relative cross-check `unavailable` for **100/100**; default Market
  comparison `unavailable` for **100/100** until an approved EOD record or manual price is supplied.
- Real local JPM calculator API: baseline `$190.14`; Sustainable ROE 18% produced `$308.62`
  (`+62.31%`).
- Manual market price `$100` left intrinsic value at `$308.62` and produced `Undervalued by 67.6%
  versus FinSight value`.
- Save returned `saved_id: 1` in the local verification wrapper.
- Real production-built browser flow:
  - one `Valuations` nav item and heading; old `/us-valuations` redirected to `/valuations`;
  - no visible Confidence or Relative cross-check sections;
  - JPM fields displayed 12.00%, 40.00%, 9.18%, and 2.00%; changing ROE to 18.00% changed both
    headline and primary model to `$308.62`;
  - entering market price changed only comparison; Save displayed success; Reset restored `$190.14`;
  - browser console contained zero errors.
- Frontend TypeScript + Vite production build passed.
- Complete backend suite: **`1321 passed, 3 skipped, 1 warning in 34.77s`**. The warning is the
  existing Passlib/Python `crypt` deprecation.

Docker/Postgres remain unavailable locally. The browser used the documented local auth dependency
and save-service stubs; calculator math and routing were real, while real authentication and DB
persistence are outside this verification claim.

## Gate

The requested user-facing cleanup and calculator correction match the observed real browser
behavior. This phase is **verified — user confirmation needed**, not complete. Merge, push, and
deployment remain separately unauthorized.
