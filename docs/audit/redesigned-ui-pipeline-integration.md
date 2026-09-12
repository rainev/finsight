# Current UI / staged pipeline integration

Checked 2026-09-08. This increment is verified locally; user confirmation and the complete automatic-refresh release remain open.

## Reference and scope

User screenshot: redesigned FinSight company page with search header, dated news, tabs, case cards and assumption controls. The source is the main checkout's `frontend/`, not the older protected-worktree frontend. Small additive edits were made to the newer UI's page/API/types while preserving its existing uncommitted redesign. Backend changes stay in `whole-universe-greenlight`.

Preview: main-checkout frontend at `http://localhost:4178`, staged API at `http://localhost:4179`, isolated database `finsight_refresh_uat_20260908`. No application catalog activation, branch merge, push, deployment or scheduler change.

## Verified contract corrections

- Requests send baseline/recipe versions and selected `scenario`; conflicting aliases reject instead of silently choosing.
- Flat presets use each case's real recipe inputs. Explicit case edits change only that case, with fixed filing facts and claims locked. Omitted scenario retains existing joint-sensitivity compatibility.
- Fields use the redesign's `percent`, `number`, `multiple`, `years` units. The live browser caught and corrected an initial `ratio`/`percent` mismatch.
- Price comparison follows the selected case, with lowercase verdicts. Zero/unavailable comparisons are represented as unavailable; vendor prices remain private.
- Saved runs retain selected-case and recipe metadata. UI readback displays the saved case, not always base.
- Catalog/version/batch labels use live metadata rather than the redesign's old hardcoded ten-batch wording.
- Dated history is accessible in Source filing. Failed-refresh status and overlapping independent custom cases have explicit messages. Missing evidence-score detail is stated, not fabricated.

## Real consumer evidence

1. AAPL official presets: bear $79.80130329911236, base $103.3303976983317, bull $123.1625608382377.
2. Browser selected bear and changed discount to 12%. Independent cash-schedule arithmetic gave $65.34926924444902. UI displayed $65.35; base/bull remained $103.33/$123.16.
3. Entered price $90: UI showed overvalued 37.7%, matching `(65.34926924444902 - 90) / 65.34926924444902`.
4. Browser saved record #6. Redesigned Portfolio → Saved scenarios read back `$65.35 — Bear case` and the matching comparison from the real database.
5. Base-only 10% edit displayed $92.38 with other cases unchanged. Reset restored $103.33 and the precise original default (displayed 9.12%).
6. Source filing → Dated valuation history displayed August 14, 2026 and $79.80/$103.33/$123.16, with financial period June 27, 2026.
7. `scripts/verify_refresh_api_uat.py` independently verified all three preset requests, selected-only arithmetic, percent unit, and real saved-case GET readback. Evidence: `output/us-refresh-runtime/api-uat-evidence.json`, including saved bear record #8.

Automated checks: broad backend run `1836 passed, 3 skipped, 1 warning`; current focused calculator checks `18 passed`; main frontend build and walkthrough script pass. Existing warning: Passlib crypt deprecation. Frontend build also reports its existing large walkthrough-scene chunk warning.

## Still not verified or completed

The 440-company automated filing refresh is not ready. All 419 numeric recipes replay, but complete production-ready issuer refresh policies, full structural/event retrieval and financial normalization integration, forecast command wiring and full successor publication acceptance remain open. This UI integration does not approve or activate the migration catalog.
