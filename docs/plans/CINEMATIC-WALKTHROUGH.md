# Cinematic walkthrough — approved implementation

## NOW — continuous motion revision

The user's latest feedback supersedes the earlier pacing acceptance. Source: [audit 07](../audit/07-continuous-scroll-motion.md).

- CM-01 / P1: make camera pose continuous for the entire scroll interval and move real HTML UI pieces independently; verify small scroll increments inside every chapter.
- CM-02 / P1: reduce nominal desktop chapter unit from 92svh to 46svh (mobile 40svh), removing action dead zones; measure actual scroll distance and final-state reachability.
- CM-03 / P1: fan/assemble cards, slide search and calculator rows, lift news dates, separate evidence layers, fold the watchlist and reassemble the final window. Keep financial outputs exact and reduced-motion/static sections untransformed.

✔ CM-01–03 implemented and live verified: continuous full-chapter camera/HTML motion, 4,617px desktop scroll span, exact reverse restoration at 27 small-scroll checkpoints, ten passing production browser checks and roughly 60 FPS on the tested Apple M2 sample. Source: [audit 07 evidence](../audit/07-continuous-scroll-motion.md). User confirmation of the stronger motion is pending; not done yet. No authentication/account testing expansion was performed.

## NOW — one integrated homepage delivery

User approved all chapters and implementation on 2026-09-07. Preserve application data and existing routes. Definition of done: live behavior matches the approved plan with evidence and user confirmation; until confirmation, not done yet.

| Item | Gap | Build and verification |
| --- | --- | --- |
| CW-01 | P1 routing | Public lazy homepage and all three auth success destinations; exercise app entry signed in/out |
| CW-02 | P1 choreography | Shared deterministic sampler, HTML panels, lazy Three scene; forward/reverse/rapid scroll and chapter jumps |
| CW-03 | P1 provenance | Hash-verified confirmed B01–B10 snapshot; replay calculator samples and exact displayed scenarios |
| CW-04 | P1 news | Reuse sourced dated summaries and two honest empty states; check date/headline synchronization |
| CW-05 | P1 access/resilience | Static/reduced-motion/WebGL fallback, mobile/tablet, keyboard and app regressions; build and live evidence |

## Acceptance status — 2026-09-07

- ✔ CW-01: `/` is public and lazy; signed-in Continue reaches the actual Apple screen. Signed-out entry goes to login. All three successful-auth destination branches are verified in source as `/valuation/AAPL`.
- ⚠ CW-01 remaining: real registration/password-login test is opt-in and was not run. Safety review rejected creating a persistent local test account without specific approval. No account was created. Google authentication was not exercised; no configured provider/session was used for testing it.
- ✔ CW-02: browser-driven forward/backward scrolling, all three scenarios, calculator endpoints, chapter jumps, keyboard CTA, browser Back, simple-view toggle and render-on-demand idle check pass. Pure sampler replay covers 1,001 positions and camera continuity.
- ✔ CW-03: confirmed B01–B10 catalog hashes and 25 exact calculator outputs replay; displayed values are $79.80 / $103.33 / $123.16, and 12% growth produces $112.32. Six existing catalog/calculator tests pass. No financial formulas or serving artifacts changed.
- ✔ CW-04: all seven dates were exercised against their displayed headlines/empty states; portfolio demo produces no holdings/saved-run write requests. Static news includes every date in accessible disclosures.
- ✔ CW-05: reduced motion, unavailable WebGL, real context loss, 390×844, 768×1024, and compact 375×667 layouts pass. Short windows deliberately use ordinary stacked sections to preserve readability.

Production build succeeded. Nine isolated Chrome checks passed, one account-creation check skipped; repeated against the actual production bundle on local port 4173. Existing in-app browser entry, Apple valuation, Portfolio and News were inspected at port 4000. News currently has its existing no-headlines state; the walkthrough does not fabricate a live feed.

Performance: 89 measured production scroll frames on ANGLE Metal / Apple M2, 1440×1000, DPR 1: median 16.7 ms, p95 16.8 ms, max 16.8 ms, zero frames >34 ms. Renderer submission median 1.3 ms / p95 1.4 ms. This short sample is not a universal guarantee. An earlier forced-SwiftShader run had p95 50 ms and stalls; do not describe software rendering as universally smooth.

Evidence: [verification notes](../audit/06-cinematic-walkthrough.md), [desktop finale](../audit/evidence/walkthrough/desktop-finale.png), [mobile](../audit/evidence/walkthrough/390-finale.png), [measurements](../audit/evidence/walkthrough/performance.json).

Status: implemented and verified within the above bounds; **not done yet** until user confirmation and remaining authentication acceptance. No push, release, deployment, account creation or database migration was performed.
