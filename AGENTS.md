# FinSight operating principles

## Definition of done

Done means the real FinSight pipeline works end to end on source-linked evidence, its generated private and public artifacts reconcile, the staged FastAPI list/detail responses match those artifacts, and the user confirms the evidence. A passing test, replay exit code, screenshot, or confident summary is not sufficient by itself.

## Required loop

For non-trivial work: understand the live code and inputs, audit concrete gaps against the approved reference, sequence them in the active roadmap, build one gated phase at a time, verify the real consumer path, record durable non-obvious learnings, and report verified, partial, blocked, and deferred claims separately.

Preserve the throughline. Log unrelated defects in `docs/plans/PRODUCTION-BACKLOG.md` instead of interrupting the current phase. Reuse existing pipeline components before introducing parallel mechanisms. Never promote, merge, push, or deploy merely because local checks pass.

## Stack and conventions

- Local build/test: Python/FastAPI backend and Vite/React frontend; focused backend checks use `PYTHONPATH=backend pytest`, and the full backend suite is `PYTHONPATH=backend pytest -q backend/tests`.
- Pipeline verification: rerun against cached real SEC/regulator inputs under untracked `output/`, validate counts, identities, periods, units, lineage, arithmetic, hashes, and representative traces, then exercise the staged localhost FastAPI list/detail endpoints.
- Deployment: pushes to `main` auto-deploy staging through `.github/workflows/deploy.yml`. Pushing therefore requires explicit user authorization. Production is not wired.
- This worktree must preserve all tracked and untracked work. Serving artifacts remain unchanged until the user approves evidence and promotion.

## Honesty

Label load-bearing claims as firsthand verified or unverified. Re-read written state and capture exact command/output evidence. If live verification cannot run, state the blocker; do not substitute tests or narration. A phase may be reported as `verified — user confirmation needed`, never self-declared done.
