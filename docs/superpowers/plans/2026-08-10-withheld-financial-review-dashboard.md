# Withheld Financial Review Dashboard Implementation Plan

> **For Codex:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` task by task, `superpowers:test-driven-development` for code, and `superpowers:verification-before-completion` before handoff.

**Goal:** Build a private offline HTML dashboard for every withheld U.S. valuation and an Excel workbook that makes unresolved financial accounts fast to review.

**Architecture:** A Python generator reconciles public withheld artifacts with private review packets, normalizes them into one deterministic dataset, and embeds that dataset in a self-contained HTML dashboard. A JavaScript builder consumes the same JSON and creates the workbook with `@oai/artifact-tool`. Outputs remain under `outputs/withheld-financial-review/` and source artifacts are read-only.

**Tech stack:** Python 3 standard library, pytest, HTML/CSS/vanilla JavaScript, and `@oai/artifact-tool`.

---

## Task 1: Reconcile the withheld universe

**Files:**

- Create: `scripts/build_withheld_financial_review.py`
- Create: `backend/tests/test_withheld_financial_review.py`

### Steps

1. Write failing fixtures for: an excluded review-grade artifact; canonical bridge-recovery packet; model-route-only packet; duplicate packet proving canonical precedence; packet-less withheld ticker; and malformed JSON.
2. Assert deterministic ticker order, exactly one record per withheld ticker, selected source path, duplicate reporting, warnings, and `private_packet_available`.
3. Run `cd backend && pytest -q tests/test_withheld_financial_review.py -k reconciliation` and confirm failure.
4. Implement safe JSON loading; dynamic selection from `review.publication_state == "withheld"`; and private-source precedence:
   1. `output/legacy-fcff-bridge-recovery/<TICKER>/valuation-private.json`
   2. `output/model-route-rebuild/<TICKER>/valuation-private.json`
5. Include packet-less tickers and emit summary counts, missing packets, duplicate candidates, malformed files, and warnings. Never hard-code 125/120 or ticker lists in generator logic.
6. Rerun the focused test and confirm PASS.
7. Commit only these files as `feat: reconcile withheld valuation review packets`.

## Task 2: Normalize review and statement data

**Files:**

- Modify: `scripts/build_withheld_financial_review.py`
- Modify: `backend/tests/test_withheld_financial_review.py`

### Steps

1. Write failing tests for issuer/routing/filing metadata; review blockers; bridge values/states/sources; unresolved fields; annual and TTM statement data; filing evidence; packet-less fallback records; and null/unexpected data.
2. Define bridge order: cash; marketable securities current/noncurrent; commercial paper; current/noncurrent debt; finance leases current/noncurrent/total; preferred equity; NCI; common, diluted weighted-average, and incremental diluted shares.
3. Run `cd backend && pytest -q tests/test_withheld_financial_review.py -k normalization` and confirm failure.
4. Implement pure normalization functions that preserve numeric raw values, exact SEC URLs, excerpts, and relative artifact paths.
5. Each company record must include queue priority, unresolved count/list, complete bridge rows, normalized income/balance-sheet/cash-flow datasets, evidence rows, and missing-section/packet flags.
6. Run:
   - `cd backend && pytest -q tests/test_withheld_financial_review.py`
   - `cd backend && pytest -q tests/test_us_valuation.py tests/test_bridge_recovery.py tests/test_automated_review.py`
7. Commit only task files as `feat: normalize withheld financial review data`.

## Task 3: Generate the offline dashboard

**Files:**

- Create: `scripts/templates/withheld-financial-review-dashboard.html`
- Modify: `scripts/build_withheld_financial_review.py`
- Modify: `backend/tests/test_withheld_financial_review.py`

### Steps

1. Write failing tests that require safely embedded JSON; summary counters; all filters; detail tabs; next/previous/next-best controls; no external assets/API; SEC-only links; and no editing/apply action.
2. Run `cd backend && pytest -q tests/test_withheld_financial_review.py -k html` and confirm failure.
3. Build a responsive two-pane UI with:
   - searchable/filterable queue and issue counters;
   - default sort by fewest unresolved fields, evidence availability, then oldest filing;
   - ticker/name, account, sector, model, issue-state, period, and packet filters;
   - accessible state badges and preserved queue position;
   - summary, missing accounts, valuation bridge, income statement, balance sheet, cash flow, and evidence tabs;
   - compact/raw value display, copy support, adjacent SEC links/excerpts, keyboard controls, and packet-less empty states.
4. Embed the JSON payload so `file://` works offline.
5. Add CLI arguments for public directory, output root, private roots, and `--strict-count`.
6. Write:
   - `outputs/withheld-financial-review/review-data.json`
   - `outputs/withheld-financial-review/dashboard.html`
   - `outputs/withheld-financial-review/generation-summary.json`
7. Run tests and `python3 scripts/build_withheld_financial_review.py --strict-count`. Current expected snapshot: 125 withheld, 120 covered, five packet-less, and three duplicate candidates.
8. Commit only implementation files as `feat: add offline withheld review dashboard`.

## Task 4: Build the Excel workbook

**Skill/runtime:** Use `spreadsheets:Spreadsheets` and load `@oai/artifact-tool` only through the workspace dependency loader. Do not install/use openpyxl, xlsxwriter, or repo-local spreadsheet packages.

**Files:**

- Create: `scripts/build_withheld_review_workbook.mjs`
- Read: `outputs/withheld-financial-review/review-data.json`
- Create: `outputs/withheld-financial-review/withheld-financial-review.xlsx`

### Steps

1. Load the approved dependency runtime, create a conversation-specific temporary work directory, and symlink its supplied `node_modules` without modifying it.
2. Create sheets:
   - `Instructions`: four-step workflow, decision meanings, zero-vs-missing warning, units/as-of date, and color legend.
   - `Summary`: formula-driven company, coverage, missing-packet, unresolved, account-count, and check metrics.
   - `Review Queue`: one row per unresolved account.
   - `Decision Lists`: the five approved decisions.
3. Prefill/protect ticker, issuer, period, form, account, current value, unit, field state, SEC source, and excerpt. Leave Correct Value, Decision, and Notes editable.
4. Add the approved dropdown to every review row; typed dates/numbers; finance formats; blue reviewer inputs; yellow required cells; conditional decision formats; filters/table; freeze panes; clickable source URLs; and compact wrapped excerpts.
5. Export the one final workbook, inspect Summary and representative queue ranges, scan errors, reconcile rows, verify validation, and render every sheet. Fix clipping or broken behavior and rerun.
6. Commit only `scripts/build_withheld_review_workbook.mjs` as `feat: generate withheld review workbook`. Do not commit generated private artifacts.

## Task 5: Full verification and handoff

**Skills:** Use `browser:control-in-app-browser` for local interaction/visual QA and `superpowers:verification-before-completion` before completion claims.

### Steps

1. Run `cd backend && pytest -q` and `git diff --check`.
2. Independently reconcile the current snapshot: 125 public withheld records; 125 unique dashboard records; 120 selected private packets; five packet-less tickers (AJG, HSY, MSFT, NOW, PANW); workbook rows equal dataset unresolved rows; and SEC URLs use approved SEC hosts.
3. Interactively test initial load, search, filters, normal and packet-less companies, all statement tabs, evidence links, navigation, queue-position preservation, and desktop/narrow layouts.
4. Visually inspect every workbook sheet for editable/source distinction, links, dropdown intent, wrapping, widths, freeze panes, and warnings.
5. Compare source hashes/Git state before and after generation; no public valuation artifact or existing private packet may change.
6. If verification requires fixes, commit only the four implementation files as `fix: verify withheld review artifacts`.

## Final Handoff

Link the HTML dashboard and workbook. Report reconciled counts, tests, and remaining limitations. State that Excel corrections are not yet imported into FinSight. Report the FinSight Efficiency Mode agent/model and evidence contribution.
