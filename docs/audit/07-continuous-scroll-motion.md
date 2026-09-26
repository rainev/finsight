# Shorter, continuous walkthrough — 2026-09-07

Reference: user feedback and live inspection of https://landonorris.com/. Observed its opening portrait scale down as the background typography and foreground signature move independently. Borrow the scale/layer relationship, not the racing assets, colors, or scroll-lock behavior.

## Verified gaps

- CM-01 / P1 / ✔: `timeline.ts` stops its pose interpolation after the first 22% of each chapter. Many remaining wheel movements change neither camera nor UI pieces.
- CM-02 / P1 / ✔: action sampling excludes the first 16% and last 20% of each chapter. Combined with a 92svh unit, this creates long apparent pauses.
- CM-03 / P1 / ✔: most content changes by swapping a whole preview, with very few independently moving HTML components. This does not deliver the requested layered experience.

Reuse the native scroll sampler, HTML/Three stage, exact snapshot, source links, and accessible static view. No new dependencies, data, account writes or auth changes. Update one motion/pacing phase, then test pixel-scale scroll increments, reverse replay, full story, mobile, fallbacks, and production performance. User confirmation remains the acceptance gate.

## Implemented and verified

- ✔ Desktop nominal unit is 46svh (was 92svh); mobile is 40svh. Measured desktop scroll span is 4,617px at 1440×1000. The unchanged chapter weights imply about half the prior desktop distance. The final chapter retains only the physical runway needed for the pinned stage to reach its final pose.
- ✔ All pose components now interpolate across the full chapter: translation, rotation, scale and backplate separation. Pure tests check 99 successive motion intervals in every chapter, 1,001 reversible states and continuous boundaries.
- ✔ Actual HTML pieces move independently: introductory scenario cards fan/assemble, search/result layers slide, scenario cards rise, calculator rows offset, news dates lift and the story moves, source/evidence layers separate, saved research folds into place, AI context tiles converge, and the finale reassembles. Exact financial samples and bar/scenario pairing are unchanged.
- ✔ Production-browser suite: **10 passed, one existing account-creation test skipped**. The new test advances 12px at 5%, 45%, and 85% of every chapter (27 checkpoints), checks both the panel and a real UI piece move, then reverses and verifies the exact computed transform is restored.
- ✔ Existing data-sync, all seven news dates, keyboard/Back/CTA, render-on-demand idle behavior, simple view, reduced motion, unavailable WebGL, real context loss, mobile/tablet and short-window checks pass. Manually inspected the opening transformation and moving mobile evidence panel in the in-app browser.
- ✔ Production build, snapshot replay and diff checks pass. No new dependencies or account/financial-data changes. No subagents used.
- ✔ Current Apple M2 / ANGLE Metal production sample: 89 measured frames, median/p95 16.7/16.7 ms, maximum 16.8 ms and zero >34 ms. This is a short local sample, not a universal performance guarantee.

Evidence: [small-scroll observations](evidence/walkthrough/continuous-motion.json), [opening early](evidence/walkthrough/continuous-before.png), [opening later](evidence/walkthrough/continuous-after.png), [current performance](evidence/walkthrough/performance.json).

## Findings worth retaining

Rendering at 60 FPS does not establish perceived motion. The previous sampler stopped camera movement early and reserved long action pauses; the user's observation was not contradicted by passing cadence tests. Verification now checks actual UI-piece transforms at small scroll increments, not just frame rate or chapter changes.

The global `button, a` rule in `index.css` adds a 240ms transform transition. It made the source-filing link lag behind deterministic scroll sampling. Disable transitions specifically for anchors inside the cinematic stage, leaving the existing application's link styles unchanged. Browser assertions wait for the rendered-scroll position before comparing transforms.

Status: **verified, user confirmation needed—not done yet**. Prior registration/Google verification limitations remain unchanged and outside this motion revision.
