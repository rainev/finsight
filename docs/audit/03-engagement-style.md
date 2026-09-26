# FinSight visual engagement pass — 2026-09-07

## Reference findings (firsthand)

- [Duolingo's home-screen rationale](https://blog.duolingo.com/new-duolingo-home-screen-design/) describes a clear guided path and visible progress. Adaptation: a five-day calendar with selected/viewed states. Dates viewed are counted per component visit, not presented as articles read or understanding achieved.
- [Duolingo's art principles](https://blog.duolingo.com/shape-language-duolingos-art-style/) explain simple shapes, personality and motion that directs attention. Adaptation: tactile date/scenario buttons, a gently tilted brand mark, and a short value reveal on scenario changes.
- [Phantom](https://phantom.com/) inspected visually in-browser: pale lavender canvas, rounded white navigation, pill actions and bold typographic hierarchy. Adaptation: restrained violet accents, softer news surfaces, a distinct company mark and active navigation treatment.

These are design adaptations, not evidence that retention or engagement will increase. No engagement experiment has been run.

## Scope and verification

The bookmarked date/news pager remains the navigation authority. Existing valuation data and calculator behavior are unchanged. Added selection feedback, viewed-date count and responsive styling; no new dependencies.

✔ Live: clicking Aug 13 updates headline/date/calendar and count to 2/5; dragging to Aug 12 updates count to 3/5. Bull selection renders $123.16 and its active button state. Base restored afterward. 390×844 layout visually inspected; all five dates fit. Existing reduced-motion global rule suppresses animation and new calendar transitions explicitly respect it. Production build and diff whitespace checks pass.

User confirmation of the new aesthetic is pending. Prior date/news design was explicitly bookmarked in `docs/learnings/date-news-swipe-approved.md`.
