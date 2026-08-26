# Universe-reset catalog cutover — Batches 01–10

Status: **user confirmed on 2026-08-27**. No merge, push, deployment, or Batch 11 work was
performed.

## Exact catalog outcome

- Active catalog: `US-RESET-2026-08-14-B01-B10-1.0`.
- Universe: `US-SP500-ISSUERS-2026-08-14-1.0`; valuation date `2026-08-14`.
- Exact denominator: **100 unique tickers / 100 unique CIKs / 10 issuers per batch**.
- Internal availability: **45 available / 51 conditional_estimate / 4 not_available**.
- Public behavior: **96 displayed numeric ranges / 4 unavailable dashes**.
- Artifact tree SHA-256: `f02e62d3f76ff78d09a70ff2a19301f6166cb6d9793e2ef153bbd23695a65faa`.
- Manifest SHA-256: `3773c700af7404ff7056e3d4f38ff4ea8a30536e9e39130ffcdd0e342905d441`.
- All 100 tracked artifacts are byte-identical to the approved Batch 01–10 final roots; private-key
  scanning passed during both independent catalog builds.

The API now resolves `active.json`, validates its manifest hash, iterates only manifest entries,
and rechecks each artifact hash before reading. It no longer discovers the serving universe by
globbing an arbitrary directory.

## Legacy archive

- Exact source commit: `670f7cfe07f82a5bc6b3ae56477407131f425b39`.
- Exact source Git tree: `81fcc404ef9b25001565f7232324dbefa0b56afa`.
- Exact contents: **206 artifacts — 88 review_required / 118 withheld**.
- Archive artifact tree SHA-256: `18a83b729429a74125b0d45ed89f2ff3baddc35cec2b6534d58de6ac7a4e4948`.
- Archive manifest SHA-256: `e252b2dd19ad1ca7ea942c3378b284720923513e380095ec968458c257603988`.
- The tracked archive is byte-identical to the Git snapshot. The former mixed 211-file loose
  serving directory was removed after this reconciliation.
- An isolated rollback activation loaded all 206 archived entries through the same manifest
  integrity layer; the active project pointer was not rolled back.

## Automated verification

- Two independent reset builds: byte-identical directories and manifest hashes.
- Two independent archive builds: byte-identical directories and manifest hashes.
- Focused catalog/API/valuation checks: `121 passed, 3 skipped` before the full run; dedicated
  catalog suite: `8 passed`.
- Complete backend suite: **`1321 passed, 3 skipped, 1 warning in 35.39s`**. The warning is the
  existing Passlib/Python `crypt` deprecation.
- Frontend production build: TypeScript + Vite passed; final bundle built with same-origin API for
  browser verification.
- Real local HTTP list: count/artifact_count 100, correct catalog/universe/date, batches 1–10, and
  exact 45/51/4 availability split.
- Real local HTTP sweep: **100/100 detail responses and 100/100 calculator responses**; 96 numeric
  companies calculable, four unavailable companies non-calculable with null ranges.
- Approved-source reconciliation: `approved_source_matches=100`.
- Legacy reconciliation: `legacy_archive_matches=206`.

## Browser verification

The production-built React application was driven through the real list-to-detail flow against
the real catalog API:

- The selector displayed exactly **100 company baselines**.
- PG displayed a normal $53.08 / $78.51 / $107.10 range, Medium reliability, scenarios,
  calculator, models, Key assumptions, and SEC filing.
- KMB—internally conditional—displayed a normal $15.88 / $36.32 / $61.27 range, Low reliability,
  scenarios, calculator, intrinsic-value model card, and Key assumptions. The visible page
  contained no `Conditional` label or badge.
- NEE displayed `—`, `Valuation unavailable`, the short nonpositive-FCFE reason, no scenario
  buttons, no calculator, and its SEC filing.
- Final browser console: zero errors.

Docker is not installed in this environment, so the database-backed login stack could not run.
For UI verification only, the real app received a local auth-refresh bootstrap response; all
valuation list/detail/calculator requests used the real FastAPI routes and catalog. Auth behavior
is therefore outside this verification claim.

## Gate

Implementation and local consumer-path verification match the approved cutover plan. The user
confirmed the cutover on 2026-08-27, closing this phase's done-gate. Merge, push, staging
deployment, and Batch 11 remain separately unauthorized.
