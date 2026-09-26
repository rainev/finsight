# Public cinematic walkthrough — 2026-09-07

Reference: user-approved FinSight Cinematic Walkthrough plan in this task.

## Verified gaps before implementation

- CW-01 / P1 / ✔: `frontend/src/App.tsx` redirects `/` inside ProtectedRoute; no public introduction exists. Login, Register and GoogleSignInButton all navigate to `/`, which would loop visitors back through a new introduction.
- CW-02 / P1 / ✔: the frontend has no Three.js dependency or shared scroll sampler. Existing valuation UI is account-aware and must not be mounted as a demonstration because it fetches and saves real research state.
- CW-03 / P1 / ✔: the confirmed B01–B10 Apple artifact and Python calculator exist, but no minimal public walkthrough snapshot exists. Values must be generated from these, not from loose artifacts or animation arithmetic.
- CW-04 / P1 / ✔: `valuationNewsPreview.ts` already supplies five sourced dated previews. August 8–9 have no entries and must remain explicitly empty.
- CW-05 / P1 / ✔: new presentation needs semantic fallback, keyboard entry, reduced motion, context-loss recovery, responsive layouts and live end-to-end evidence.

Reuse: existing typography, local Apple SVG, curated news previews and Python calculator. Add only procedural Three.js backplates; all copy and controls remain HTML. No API, catalog, account or database mutations are required.

Flow/security: public `/` → persistent skip/final CTA → existing protected `/valuation/AAPL` → login when necessary → `/valuation/AAPL`. Demonstration portfolio actions have no API wiring. Keep source attribution and Low reliability/review qualifications visible.

Implementation and acceptance ledger: [walkthrough roadmap](../plans/CINEMATIC-WALKTHROUGH.md).

## Firsthand verification

Commands:

```sh
PYTHONPATH=backend python3 scripts/build_walkthrough_snapshot.py --check
PYTHONPATH=backend:. python3 -m pytest -q backend/tests/test_us_batch_catalog.py
cd frontend
npm run test:walkthrough
npm run build
FINSIGHT_TEST_URL=http://127.0.0.1:4173 npm run test:walkthrough:live
```

✔ Snapshot: exact source hashes, ten batches/100 issuers, all three supplied scenarios and 25 calculator samples validated. Six existing backend tests passed. Pure sampler tests cover 1,001 forward/reverse states, camera boundaries, date/scenario/sample selection and auth branch destinations.

✔ Production browser: nine passed; the real registration/password-login test skipped. Exercised all seven news dates, both empty-news states, bear/base/bull values and marker positions, 8.17% → 12.00% / $103.33 → $112.32, reverse restoration, chapter jumps, browser Back, keyboard activation, idle-render cessation, simple view, reduced motion, blocked WebGL, actual WEBGL_lose_context extension, 390px/768px bounds and short-window static layout. No demo holdings or saved-run mutations were observed. No runtime page errors in the full-story test.

✔ In-app browser: existing authenticated session followed final CTA → `/valuation/AAPL`, rendering Apple Inc. inside `.finsight-app`, with no `.wt` styles/root. Existing Portfolio rendered its followed-company cards; News retained its existing no-headlines state. No holdings were changed for verification.

### Captured artifacts

- [Desktop scenarios](evidence/walkthrough/desktop-scenarios.png)
- [Desktop finale](evidence/walkthrough/desktop-finale.png)
- [390px finale](evidence/walkthrough/390-finale.png), [768px finale](evidence/walkthrough/768-finale.png)
- [Reduced motion](evidence/walkthrough/reduced-fallback.png), [unavailable WebGL](evidence/walkthrough/unavailable-fallback.png), [context lost](evidence/walkthrough/lost-fallback.png)
- [Measured performance](evidence/walkthrough/performance.json)

### Boundaries, findings, and remaining checks

- The first live suite caught insufficient finale scroll distance. Added runway **inside the final chapter**, keeping the sticky stage in its containing grid while the camera settles. Extra footer space alone would allow the stage to leave the viewport before the move completes.
- Wheel positions quantize to pixels. Test positioning allows <1.1px difference; scenario/sample/date assertions still verify exact semantic state. Chapter sampling uses fractional measured heights rather than rounded offsetHeight.
- Three renders only on scheduled updates. Memoized presentation snapshots and content-key checks prevent camera-only movement from rerendering the whole HTML story.
- Native Metal/Apple M2 production sample: median/p95 frame times 16.7/16.8 ms over 89 frames. Forced software rendering showed p95 50 ms; that limitation remains relevant for weak/software-rendered environments.
- Vite reports a deferred 541.24 kB scene chunk (138.25 kB gzip); initial walkthrough JS is 26.28 kB (9.03 kB gzip). The 3D module loads separately after initial HTML. npm reported seven dependency advisories; broad dependency remediation was not part of this UI task and was not attempted.
- Safety review blocked running the opt-in real-registration test because it creates a persistent local test account. This requires explicit user approval; no workaround was attempted and no account was created. Google sign-in was not tested live. All three auth success branches were updated and statically checked, which is not a substitute for live provider/login verification.
- User confirmation of choreography and visual quality is pending. Status is **verified within the listed bounds, not done yet**.
