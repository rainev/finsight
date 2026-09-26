# Case-specific assumptions — 2026-09-07

User reference: Apple screenshot with Bull $123.16 but Base inputs (8.17%, 9.12%, 2.00%).

✔ Cause: `UsValuations.tsx` changes only the selected range key; `calculator_view` exposes one default input set and the existing sensitivity calculator always anchors to Base defaults.

✔ Source: confirmed B01–B10 AAPL artifact, source accession 0000320193-26-000020, scenario values 79.80130329911236 / 103.3303976983317 / 123.1625608382377. Original governed state definitions recovered read-only from `.worktrees/whole-universe-greenlight/backend/app/us_valuation/practical_models.py:PRACTICAL_FCFF_STATES`; original Batch01 result at `docs/audit/12-practical-batch-01-result.md` in that worktree confirms the same values. Bear deltas: growth −2pp, WACC +1pp, terminal growth −0.5pp. Bull: +1.5pp, −0.5pp, +0.3pp. Other coupled margin/capital/bridge adjustments are not represented by these three sliders.

## NOW — one focused phase

- P1 AS-01: expose provenance-bound Apple case presets. Do not invent presets for other catalog models; explicitly show unavailable case inputs where no verified mapping exists.
- P1 AS-02: anchor sensitivity to the selected case's own defaults, avoiding double-applying scenario stress. Each unedited case must retain its published value.
- P1 AS-03: synchronize ranges/numbers, preserve independent per-case edits, reset the selected case, invalidate stale responses, and record selected-case metadata in an explicitly saved result without changing the database schema.
- Verify: exact preset values and unchanged defaults; numeric edits and round trips; manual comparison on selected case; all-catalog Base compatibility; browser Bear/Base/Bull, sliders, edit/reset and no account saves.

Not done yet; live evidence and user confirmation are required. No catalog promotion, model-policy change or account creation is authorized.

## Implementation / evidence

- ✔ Original private Batch01 result was inspected read-only: its first projection's revenue-growth field, WACC, terminal-growth field and published value match the exact three presets. Only governed inputs are exposed, never private source packets or raw financials.
- ✔ Running GET `/api/us-valuations/AAPL/calculator` returns all three presets. Growth/discount/terminal display percentages: Bear 6.17/10.12/1.50; Base 8.17/9.12/2.00; Bull 9.67/8.62/2.30.
- ✔ Defaults remain $79.80 / $103.33 / $123.16. Scenario-specific anchors prevent stress being applied twice. Existing Base API requests stay compatible and Base defaults replay for every numeric company in the 100-company catalog.
- ✔ Frontend keeps independent input drafts and results by case. Reset restores the selected case. Range inputs use precise values with governed keyboard increments, avoiding the native range input's rounding of values such as 8.1660845769% to its 0.5pp grid.
- ✔ Calculator request/save schema records the selected case; Portfolio displays that case's saved value, with a Base fallback for old rows. Save routing was tested only with a stub—no records were created.
- ✔ 17 focused backend tests pass. Walkthrough snapshot still replays without changes. Frontend production build and diff checks pass.
- ✔ Isolated browser regression passes: Bear/Base/Bull values and slider positions, Bull growth edit to 11%, switching away/back, keyboard slider step to 11.5%, and Reset to 9.67%. All API requests in that test are intercepted fixtures; authentication is mocked and no actual account or authenticated API is accessed. Screenshot: [isolated Bull controls](evidence/walkthrough/case-inputs-isolated.png).
- ⚠ Real signed-in UI verification is pending. Both existing in-app tabs were signed out. Asked the user to sign in; no credentials were inspected or new account created. The isolated test is not a substitute for this final end-to-end step.
- Scope: verified case presets are currently available for this confirmed Apple baseline. Other companies retain published case values and Base editing; unverified Bear/Bull inputs explicitly report unavailable rather than copying or inventing presets.

Status: implemented, API and isolated UI verified; **not done yet** pending signed-in browser verification and user confirmation. No subagents used.
