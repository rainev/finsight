# Launch-first Phase 3 result

## Implemented

- GET/POST `/api/us-valuations/{ticker}/calculator` with model-family-specific editable assumptions,
  locked facts, safe limits, default/base parity, manual price, automatic derived comparison, reset
  semantics, and optional save.
- Baseline-calibrated sensitivity for operating, bank, REIT, and utility/equity families. The
  response explicitly warns that it is calibrated to the published baseline and does not mutate
  locked filing facts.
- Private security-master and EOD record validation; only derived percentage/label/date crosses the
  public allowlist.
- Nullable U.S. saved-run columns and `save_us`; automatic vendor prices are never persisted.
- Retail page with Available / Conditional estimate / Relative baseline / Not available vocabulary,
  FinSight Base Case, Bear/Base/Bull controls, confidence reasons, automatic/manual comparison,
  separate relative cross-check, edit/reset/save, and user result beside the baseline.
- Saved page can distinguish and render U.S. custom runs.

## Automated evidence

- Complete backend suite: **1,232 passed, 3 skipped, 1 warning**.
- Final frontend production build: TypeScript and Vite passed; 1,695 modules transformed.
- Focused calculator/API/save/EOD tests cover default parity, monotonic discount/cash conversion,
  invalid assumptions, manual price, safe save payload, raw-price scrubbing, and unavailable state.
- `git diff --check`: passed.

## Real API evidence

The real localhost FastAPI application served the flat 30-company launch-first stage:

- list 200 / exact count 30;
- detail 30/30 HTTP 200;
- calculator GET 30/30 HTTP 200;
- default calculator agreement 30/30 (including three unavailable views);
- model-family coverage: 23 operating, 2 bank, 1 REIT, 1 utility/equity, 3 unavailable;
- higher discount rate lowered value; better cash conversion increased value;
- manual price flow passed;
- private leaks 0;
- approved-EOD behavior passed with a clearly marked local verification fixture; no raw price,
  provider, or hash crossed the public response.

Receipt: `output/launch-first/lf4-real-api-30-v2.json`, SHA-256
`bf11f845eed73c6ecdab623262b49cb07de349b3ec88186de8621b084d198e21`.

## Real browser evidence

The built authenticated page was driven through the actual frontend and backend:

- login and protected U.S. route;
- APP Conditional estimate label and public claims reserve;
- NWSA Base $23.88 → Bear $4.77 and automatic EOD-derived label/date;
- cash conversion 1.0 → 1.2 changed user base $23.88 → $28.66;
- manual price switched the label to “Using your price”;
- reset restored $23.88 and automatic EOD comparison;
- save returned the local test-harness saved id;
- ECHO showed Not available, no numeric base, and disabled editor;
- JPM rendered Sustainable ROE / payout / cost-of-equity controls and reproduced $190.14;
- Realty Income rendered AFFO growth / recurring-cost controls and reproduced $48.29;
- browser console warnings/errors: 0.

The browser used a localhost-only authenticated test harness because Docker/Postgres is unavailable.
It preserved signed-JWT/protected routes and stubbed only database-backed login/save/feed operations.

## Honest limitations

- Real Postgres migration and saved-row persistence were not exercised; the local environment has no
  Docker or database. SQL/schema/service code and scoped save tests pass, but production persistence is
  **unverified**.
- No approved private vendor EOD or peer cohort exists in the worktree. Automatic and relative values
  remain unavailable in the real stage; the EOD validator was exercised only with an explicit
  verification fixture.

## Gate

LF3 is **verified with two explicit external-data/environment limitations**. User confirmation is
still required; no serving artifact, merge, push, or deployment occurred.
