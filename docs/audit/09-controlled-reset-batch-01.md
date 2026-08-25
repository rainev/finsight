# Controlled reset — Batch 01 adoption audit

**Audited:** 2026-08-20 (Asia/Manila)  
**Reference:** `FinSight Controlled 500-Company Reset Plan` supplied by the user  
**Scope:** protected starting state and the fixed first batch only  
**Status:** firsthand audit complete; implementation gaps remain open

## Reference

The controlled reset preserves the SEC/Companyfacts pipeline, offline Arelle extraction,
period-aware normalization, safety contracts, existing model mathematics, tests, and old
artifacts. It requires every issuer to be re-examined at `2026-08-14`, with a private
economic profile and model-decision record, source-linked low/base/high valuation, explicit
reliability or blocker, deterministic regeneration, staged API verification, and a batch
report before any promotion. Batch 01 is fixed at AAPL, MSFT, CRM, ANET, WDC, DELL, JPM,
BAC, NEE, and O. The reset expressly supersedes the older all-ten-or-nothing promotion rule
with per-company promotion after user approval.

## Ours today

- ✔ The required worktree exists at
  `/Users/carlosconda/Desktop/Investing Application/.worktrees/whole-universe-greenlight`,
  on `codex/period-aware-valuation-policy` at
  `27c2cdad8b126e3b0aa2bb2421499bc3607eec07`.
- ✔ The starting worktree is dirty. Sixteen tracked files are modified; the existing audit,
  learning, and `output/` additions are untracked. No existing change was reset, stashed,
  staged, or overwritten during this audit.
- ✔ The baseline backend suite is `996 passed, 3 skipped` with one Passlib/Python `crypt`
  deprecation warning.
- ✔ The canonical serving-tree hash from
  `scripts/run_reliability_pipeline_replay.py::_tree_hash` is
  `34b380fe6678af826fbd63cb53b3fd737a596631e86bbb93346ad04e10c1e00a`.
- ✔ The serving directory contains 206 JSON artifacts: 88 finite
  `review_required` results and 118 withheld results.
- ✔ Batch 01's old comparison baseline is 5/10 finite (AAPL, JPM, BAC, NEE, O) and
  5/10 withheld (MSFT, CRM, ANET, WDC, DELL). None of the ten stored private artifacts
  carries a raw reliability record; the public sanitizer derives a compatibility label.
- ✔ Reliability rules, annual carry-forward boundaries, public schema `1.1`, staged data-root
  support, offline replay, and serving-write protection already exist and are covered by the
  current passing suite.
- ✔ No Batch 01 manifest module, capture command, generator, verifier, source-packet tree, or
  staged Batch 01 output exists in this worktree.

## Reuse check

The reset should reuse `classification.py`, `eligibility.py`, `pipeline.py`,
`equity_models.py`, `field_availability.py`, `bridge_policy.py`, `artifacts.py`, the SEC
client, offline Arelle package/parser, the reliability engine, and the staging data-root
override. The missing layer is orchestration and governed per-issuer decision evidence, not
a replacement valuation engine.

## Consumer flow

Required flow:

`fixed manifest -> immutable source packets -> normalized evidence -> economic profile -> model decision -> private valuation -> safe public artifact -> staged FastAPI list/detail -> deterministic rerun -> batch report -> user approval -> per-company promotion`

Today the flow starts only at legacy serving artifacts or difficult-corpus replay inputs.
There is no one-command, fixed-denominator Batch 01 path from frozen issuer identity through
staged API verification.

## What backs it

- Git branch, commit, porcelain status, and worktree inventory were read directly.
- The full backend suite was run from the protected worktree.
- Serving outcomes were recalculated from all 206 JSON files, and the canonical serving hash
  was recomputed with the repository's replay helper.
- Batch 01 module/script/output absence was checked directly.
- Existing routing configuration was read for all ten issuers. It has issuer overrides for
  the six operating companies but none for JPM, BAC, NEE, or O.

## Gaps

- **CR-01 · P0 ✔ — Roadmap mismatch.** `docs/plans/ROADMAP.md` still names the older
  evidence-aware reliability phase as NOW and does not encode the controlled 50-batch reset.
- **CR-02 · P0 ✔ — No immutable Batch 01 contract.** The fixed identities, CIKs, valuation
  date, filing regime, accounting standard, and lane hypotheses are not represented by one
  importable manifest.
- **CR-03 · P0 ✔ — Missing governance records.** There is no validated private economic
  profile/model-decision schema with rejected alternatives, maturity, cap, and supporting
  accessions.
- **CR-04 · P0 ✔ — Missing source packets.** The worktree has no ten-company immutable
  submissions/Companyfacts packets and therefore cannot yet prove point-in-time eligibility
  or source hashes.
- **CR-05 · P0 ✔ — Missing batch runner and report.** No fixed-denominator command produces
  explicit numeric/withheld/invalid outcomes for all ten without serving writes.
- **CR-06 · P0 ✔ — Missing deterministic staged API receipt.** The API can read an overridden
  data root, but no Batch 01 verifier reconciles ten staged list/detail responses to artifact
  hashes while proving Arelle isolation.
- **CR-07 · P0 ✔ — Old promotion rule conflicts with the reset.** The 2026-08-14 Batch 01
  design requires all ten to pass before any promotion; the controlled reset permits only
  individually passing companies after the full report and user approval.
- **CR-08 · P0 ⚠ — Model hypotheses need source review.** Generic FCFF/DDM/FFO labels in the
  older plan may be too coarse for research-heavy software, cyclical storage, Dell's captive
  finance, NextEra's mixed utility economics, and Realty Income's AFFO/NAV requirement. This
  remains a hypothesis until source-backed economic profiles are completed.
- **CR-09 · P1 ✔ — Canonical 500-universe proof remains absent.** This does not block Batch 01,
  which is fixed, but it blocks construction of Batches 02–50 and must be resolved before
  Batch 02.

