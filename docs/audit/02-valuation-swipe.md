# Valuation swipe navigation — 2026-09-07

Reference: `UI Inspo/finsight-day-digest (1).html`. Content authority: `frontend/src/pages/UsValuations.tsx`.

✔ P1: Reference uses horizontal swipe/drag, arrows, and dots; current valuation sections switch by buttons only.
✔ P1: Reference scrolls each page vertically; current sections repeat the same large summary above their content.
✔ P1: Range inputs must retain their horizontal drag behavior inside a swipe surface. Reference has no calculator inputs.
✔ Content boundary: the current API supplies one valuation date per company. No daily market, news, breadth, or invented historic valuation content will be imported from the reference.

Reuse: existing React state, browser pointer events, existing valuation cards and API calls. No new animation or carousel dependency required.
Verification: live arrows, swipe, keyboard, numeric/range inputs, value preservation between pages, first/last boundaries, mobile layout, and production build.
