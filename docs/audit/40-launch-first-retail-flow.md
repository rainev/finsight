# Launch-first retail flow gap

Reference: user-supplied `FinSight Launch-First Valuation Plan`, sections 4, 5, 7, and 9.

## Reference

The company page should lead with FinSight Base Case, bear/base/bull values, retail availability,
confidence and reasons, assumptions/warnings, automatic or manual price comparison, a separate
relative cross-check, editable assumptions, reset, save, and baseline-versus-user result.

## Ours today

- `frontend/src/pages/UsValuations.tsx` reads list/detail only.
- `StateBadge` exposes `review_required` directly (`frontend/src/pages/UsValuations.tsx:23`).
- The page labels low/high as an “Assumption range” and displays issuer classification percentage
  rather than valuation reliability/reasons (`frontend/src/pages/UsValuations.tsx:153`).
- It already has reusable source, warning, assumption, model, and range presentation.
- Frontend U.S. types omit reliability and all v1.2/calculator/market fields
  (`frontend/src/lib/types.ts:186`).

## Reuse check

Keep the existing U.S. route and its source/assumption cards. Add a calculator panel and retail state
mapping in place; do not repurpose the PHP research calculator or expose locked facts.

## Flow

The user can select a ticker and read one artifact, but cannot switch explicit bear/base/bull views,
understand availability in retail language, edit/reset assumptions, enter a price, compare results,
or save a U.S. run. The current page also promises a price-free experience, which conflicts with the
new derived-comparison policy.

## What backs it

Direct read of `frontend/src/pages/UsValuations.tsx`, `frontend/src/lib/api.ts`, and
`frontend/src/lib/types.ts`; runtime browser behavior is not yet verified.

## Gaps

- **LF-U1 · P0 · ✔** Retail availability mapping is absent; internal review vocabulary leaks.
- **LF-U2 · P0 · ✔** Bear/Base/Bull tabs and FinSight Base Case hierarchy are absent.
- **LF-U3 · P0 · ✔** Edit/reset/manual-price/baseline-versus-user calculator flow is absent.
- **LF-U4 · P1 · ✔** Reliability label/reasons are not shown even though the backend can supply them.
- **LF-U5 · P1 · ✔** Automatic derived comparison and separately labeled relative baseline are absent.
- **LF-U6 · P1 · ✔** Saved U.S. runs cannot be distinguished or rendered safely in the Saved page.
- **LF-U7 · P0 · ⚠** Browser UAT is unverified until the current frontend is built and the authenticated
  local flow is exercised against the staged API.
