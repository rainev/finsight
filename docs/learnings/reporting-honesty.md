---
name: reporting-honesty
description: Separates written, tested, live-verified, and user-confirmed FinSight claims.
metadata: { type: project }
---
Report FinSight claims at their actual evidence level: implemented, automated-test verified, real-pipeline/API verified, or user-confirmed. Never use a passing test or successful replay exit code as a substitute for correctness validation on real inputs.
*** Add File: /Users/carlosconda/Desktop/Investing Application/.worktrees/whole-universe-greenlight/docs/learnings/build-deploy-gotchas.md
---
name: build-deploy-gotchas
description: Records the deployment trigger that must not be confused with local verification.
metadata: { type: gotcha }
---
Pushing to `main` triggers the staging deployment workflow; local replay or localhost API verification does not deploy anything.

**Why:** A routine push is an externally visible state change even when intended only to share code.

**How to detect / apply:** Check the current branch and `.github/workflows/deploy.yml`; obtain explicit user authorization before any push to `main`. Use cached pipeline replays and localhost FastAPI for pre-promotion verification.
