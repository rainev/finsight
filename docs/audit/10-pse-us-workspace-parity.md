# Audit 10 — PSE/US valuation workspace parity

**Implementation status:** Live verified on 2026-09-21 and user-confirmed on 2026-09-22. The active local PSE route and
catalog pointer use V2; no deployment, push, specialist-model recovery, or Phase B work has occurred.

## Reference

The current US valuation workspace is the product reference: company identity header, US/PSE switch, portfolio action,
seven-day news calendar, five swipeable valuation sections, scenario selector, manual-price comparison, assumption
calculator, save flow, evidence/source view, and catalog footer.

## Ours today

- ✔ `/valuation/:ticker` provides the complete US workspace.
- ✔ `/pse-v2` serves the correct PSE V2 artifacts but uses a separate compact page.
- ✔ `/pse` still points to the legacy four-company blended-model screen.
- ✔ PSE V2 has list/detail endpoints but no calculator or save endpoint.
- ✔ The shared `ValuationSwipeDeck` already contains the seven-day calendar and section navigation.
- ✔ Holdings support `market=PH`, but four pilot companies are absent from the shared company table and the Portfolio UI
  only resolves US catalog values/links.

## Reuse check

Reuse the US workspace classes, `ValuationSwipeDeck`, `CompanyLogo`, authentication, holdings service, saved valuation
table, and current catalog. Add a small PSE calculator over the existing AP/private bridge and market-relative policy;
do not add a new model or news provider.

## Flow

US company → click PSE → `/pse/AP` → select/search PSE ticker → calendar + valuation workspace → adjust selected case →
optional manual price → save → portfolio/saved scenario → click US → `/valuation/AAPL`.

## What backs it

- The staged PSE 1.1 catalog has one intrinsic and seven market-relative numeric baselines.
- The AP calculator can rerun the existing FCFF engine while keeping bridge facts server-side.
- Market-relative calculators need only the source-linked per-share metric and selected multiple/yield.
- The shared news calendar safely renders a generic preview when no curated ticker story exists.

## Gaps

- **P0 ✔ UI-01 — Route parity:** `/pse` still serves the legacy screen; PSE V2 is hidden at `/pse-v2`.
- **P0 ✔ UI-02 — Calculator parity:** no PSE calculator/view/save endpoints or controls exist.
- **P1 ✔ UI-03 — Workspace parity:** PSE lacks the US identity header, seven-day calendar, swipe sections, scenario
  comparison, assumptions panel, and catalog footer.
- **P1 ✔ UI-04 — Navigation parity:** header search, valuation dock, market switch, portfolio cards, and saved scenarios
  do not route consistently for PH tickers.
- **P1 ✔ UI-05 — Portfolio identity:** BDO, AREIT, ALI, and AC are not guaranteed in the shared PH company table.
- **P2 ⚠ UI-06 — News content:** the calendar can match behavior immediately, but ticker-specific PH stories remain a
  separate content/source task and are not required for this parity phase.
