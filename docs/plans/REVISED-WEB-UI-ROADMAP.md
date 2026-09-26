# FinSight revised web UI — gated implementation record

## Case-specific Apple assumptions — 2026-09-07

AS-01–03: implemented source-bound Bear/Base/Bull inputs, per-case drafts and sensitivity anchors,
selected-case Reset and saved-case metadata. Seventeen backend checks and isolated browser test pass;
running public calculator endpoint returns correct presets. Actual signed-in UI remains unverified
until the user signs in. No account created. Details: [audit 08](../audit/08-case-assumption-sync.md).

## Shorter, continuously moving walkthrough — 2026-09-07

User feedback supersedes the earlier long, entrance-only choreography. Nominal scroll distance is halved;
each chapter now moves its camera and individual interface pieces across the whole interval. Actual 12px
wheel changes and exact reversal verified at 27 checkpoints. Production: 10 browser checks passed, one
account-creation test remains skipped. User motion/aesthetic confirmation pending.
Evidence: [continuous-scroll audit](../audit/07-continuous-scroll-motion.md).

## Public cinematic walkthrough — 2026-09-07

Implemented the approved public `/` introduction with eight chapters and a finale, lazy Three.js backplates,
accessible HTML, deterministic native-scroll sampling and the existing `/valuation/AAPL` entry. The existing
application is preserved. Detailed acceptance ledger: [CINEMATIC-WALKTHROUGH.md](CINEMATIC-WALKTHROUGH.md).

✔ Production build, snapshot replay, six catalog/calculator tests and nine live production-browser checks pass.
✔ Existing signed-in CTA and valuation/news/portfolio surfaces inspected through the in-app browser.
⚠ Fresh registration/password login test blocked by safety review pending permission to create one local test
account; Google sign-in not exercised. User aesthetic/behavior acceptance remains pending. Not done yet.

## Empty-space refinement — 2026-09-07

Removed the cross-row equal-height rule that stretched the overview; each row now fits its
content while retaining equal columns and equal heights within that row. Added existing
bear–bull range, reporting period and filing link beneath the headline; Evidence Health
rows distribute through their panel. No new financial inputs or model changes.

✔ Live: top row reduced from 622px to 538.5px at the same 679px column width; column
dividers align. New source/range details render; production build and diff checks pass.

## Panel alignment and percentage formatting — 2026-09-07

Four Summary panels now share one equal-column/equal-row desktop grid, stacking naturally
on mobile. Compact assumption rows and actions; separate percentage suffix from the input,
hide native spinners and display two decimal places without rounding stored model defaults.
Typing retains a local draft until blur so decimal edits remain usable.

✔ Live geometry: all four desktop panels measured 679×622px, with identical column edges.
Fields displayed 8.17, 9.12 and 2.00 with scrollWidth equal to clientWidth (71px desktop,
67px at a 390px viewport). Edited 8.25 then Reset; default values restored. Build passes.

## Current — monochrome continuous workspace

Latest user preference supersedes colored styling: black/white/grays, local Apple logo,
shared page surface and one document scroll. Sticky tabs navigate directly to section content;
seven newest-first news dates are preserved. Evidence: `docs/audit/05-monochrome-workspace.md`.

## Current — newest-first weekly brief and original palette

2026-09-07 user correction supersedes the five-day lavender styling. Seven days
descend newest-first and span the full calendar width. Teal/ivory/ink with amber
editorial accents; Back to latest, progress feedback and numeric scenario choices.
Research and verification: `docs/audit/04-weekly-brief-style.md`.

## Visual engagement pass — 2026-09-07

Date/news direction bookmarked at the user's request. Added lavender visual identity, tactile five-day timeline, real per-visit viewed-date feedback, styled active navigation and scenario buttons, and restrained value transitions. Research and live verification: `docs/audit/03-engagement-style.md`. Existing content and calculation contracts retained. Aesthetic confirmation pending.

## Date/news pager correction — 2026-09-07

The user's clarified requirement supersedes section-swiping: the top date, arrows, dots and news-card swipe now navigate five calendar days ending at the valuation date. Valuation sections use their existing tabs, independently of the news date.

✔ Added a short sourced AAPL news preview for each day August 10–14, 2026, with a Read story link. `frontend/src/lib/valuationNewsPreview.ts` contains dated source URLs and paraphrased summaries; dates were checked against the individual MacRumors reports. This is curated preview content, not a live feed. Other tickers/dates show an explicit preview placeholder.

✔ Live browser: August 14 → Earlier selected August 13 and Houston manufacturing news; dragging left selected August 12 and display-cost news. Dots selected August 10/11; earliest/latest arrows disable appropriately. Valuation date/value and Summary selection stayed unchanged. Mobile-width rendering inspected; production build passed. Temporary viewport restored.

## NOW — swipe workspace (2026-09-07)

- SW-01: adapt the Day Digest page navigation to five existing valuation sections (Summary, primary model, Cross-checks, Key assumptions, Source filing); retain actual valuation date and all existing content. Source: audit 02. Verify by swipe, arrows, and direct section selection.
- SW-02: isolate range inputs, text fields, buttons and vertical scrolling from page gestures; preserve edited state across pages. Verify in the running app.
- SW-03: responsive pager, reduced-motion support and keyboard navigation; production build and live browser evidence before handoff.

### Swipe verification — 2026-09-07

✔ Live at `http://localhost:4000/valuation/AAPL`: Next moved Summary → DCF; pointer drag moved DCF → Cross-checks; Home/End on tabs moved to first/last page with correct disabled arrows. Inactive pages are inert and excluded from accessibility navigation.

✔ Calculator isolation: editing growth to 12%, then dragging its range to 19.5%, stayed on Assumptions. Returning to Summary retained the edited input and displayed $131.50. Reset restored $103.33. These are existing calculator outputs, not a new model validation.

✔ Mobile 390×844: swipe changed the selected section; selecting the last dot revealed the Key assumptions tab and disabled Next. Independent vertical page scrolling and all existing sections remain available. Temporary viewport override reset after verification.

✔ `npm run build` and `git diff --check` passed. No backend, catalog, or model changes in this iteration. No subagents used.

Interpretation: borrowed the reference's date-pager interaction for existing valuation sections, displaying the actual valuation date. Historical date browsing is not implemented because the current content exposes one baseline date per company. User confirmation of this interpretation remains pending.

Definition of done: the current local stack is driven through the real browser and API, matches the
approved four-destination intent, and the user confirms it. A build or unit test alone is not done.

## Phase NOW — verified, user confirmation required

| ID | Outcome | Status | Live evidence |
| --- | --- | --- | --- |
| UI-01 | Publish only confirmed US Batches 01–10 | ✔ verified | `GET /api/us-valuations` returned catalog `US-RESET-2026-08-14-B01-B10-1.0`, count 100, batches 1–10; NVDA absent |
| UI-02 | Light modern shell with Valuation, News, Portfolio, AI Insights | ✔ verified | Browser rendered the four-item dock and responsive 390px, 768px, and desktop layouts |
| UI-03 | Model-aware valuation workspace and manual price comparison | ✔ verified | AAPL rendered $103.33; manual $200 produced “Overvalued by 93.6%” |
| UI-04 | Three primary sliders plus advanced assumptions | ✔ verified | Editing AAPL initial growth from 8.1661% to 12% recalculated base value from $103.33 to $112.32; Reset restored $103.33 |
| UI-05 | Market-aware watchlist and saved scenarios | ✔ verified | AAPL added through the UI, rendered in Portfolio at $103.33, and saved scenario #1 rendered under Saved scenarios |
| UI-06 | Fail-closed unavailable state | ✔ verified | NEE rendered “Valuation unavailable” with the source-bounded reason and no numeric calculator |
| UI-07 | AI Insights and notifications remain intentional placeholders | ✔ verified | AI route renders the approved coming-soon state; bell is disabled and labeled |
| UI-08 | Source-linked News destination | ⚠ partial | The real empty state renders; US-specific ingestion is backlogged until a source configuration is approved |
| UI-09 | Sector-aware company operating health | ⚠ partial | Evidence Health renders honest source/accounting/scenario/model quality; operating-health scores are backlogged because the public catalog does not contain the required ratios |

## Automated gates

- Backend: `259 passed`, one existing Python `crypt` deprecation warning.
- Frontend production build: passed (`tsc -b && vite build`).
- Browser console: zero errors on the final desktop valuation workspace.

The phase remains **verified — user confirmation required**, not complete.
