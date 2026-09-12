# 500-company light baseline audit

Date: 2026-09-12
Status: light audit complete; deep economic audit intentionally deferred until after the working groups.

## Reference and scope

The requested reference is the confirmed controlled universe: exactly 50 batches of 10 issuers at valuation date
2026-08-14, with transparent Pass/Conditional/Withheld states, finite ordered numeric ranges, null withheld ranges,
formula-accurate public labels, safe public evidence and no unapproved serving promotion.

This pass checks mechanical integrity, public-contract wiring, obvious calibration diagnostics, bookkeeping coverage and
release boundaries. It does **not** re-underwrite all 500 valuations, refresh SEC evidence, backtest market outcomes or
complete browser UAT.

## Ours today

- Staged catalog: `output/batch-50-api-runtime-a/catalogs/US-RESET-2026-08-14-B01-B50-INITIAL-1.0`.
- Manifest SHA-256: `c80a26aff4b4760a34c042d13a83ca93dbc096513e9847ebc73a9188a3f2ee8c`.
- Artifact-tree SHA-256: `8f8f22cd9f9750218295adb854a1be6f077ae7399f5e492b3c38fe3a970d76fc`.
- Stored counts: **500 = 116 available / 358 Conditional / 26 Withheld**, numeric **474/500**.
- Reliability: **0 High / 4 Medium / 496 Low**.
- Recovery Learning Watchlist: **384**, exactly matching the 358 Conditional plus 26 currently Withheld companies.
- The production pointer remains `US-RESET-2026-08-14-B01-B10-1.0`; the 500-company catalog is staged only.

## Reuse and consumer flow

The audit reused the manifest-controlled catalog loader, artifact hashes, public calculator, recovery watchlist, existing
500-company API receipts and the real FastAPI list/detail/calculator route. No SEC download, valuation rebuild, serving
activation or production mutation was needed.

The intended consumer flow is:

`stored catalog artifact -> FastAPI load -> list/detail response -> calculator`

The stored catalog is mechanically sound, but the real API spot-check exposed a non-idempotent public sanitization step
inside that flow.

## What backs the result

- Machine receipt: `output/universe-500-light-baseline-audit-20260912/integrity-receipt.json`.
- Live API receipt: `output/universe-500-light-baseline-audit-20260912/live-api-spot-check.json`.
- FastAPI loads and sanitizes the stored artifact at `backend/app/routers/us_valuations.py:166-174`.
- The existing parity verifier sanitizes its expected artifact again at
  `scripts/verify_official_evidence_api.py:74-76`, which can conceal non-idempotent label changes.
- Working-group status is recorded in `docs/plans/US-REFRESH-WORKING-GROUPS.md`.

## Green checks

- ✔ **500 unique tickers and 500 unique CIKs**, with all 50 batches present and exactly 10 issuers per batch.
- ✔ Every artifact exists and matches its manifest hash; every source-audit path resolves.
- ✔ All 474 numeric artifacts have finite ordered low/base/high values and positive bases.
- ✔ All 26 withheld artifacts have null ranges and disabled calculators.
- ✔ All public artifacts use an allowed High/Medium/Low reliability label and contain no private evidence keys.
- ✔ Offline calculator defaults reproduce all stored ranges.
- ✔ The real staged API returned HTTP 200 with 500 rows; the prior full receipts still show 500/500 detail and calculator
  execution with zero private leaks and zero forbidden serving imports.
- ✔ The watchlist exactly covers every stored non-Pass ticker and every current withheld ticker.

## Gap register

| ID | Severity | Finding | Verification |
| --- | --- | --- | --- |
| L500-01 | **P0** | The live API changed 26 stored REIT artifacts from `conditional_estimate` to `available`. Stored counts were 116/358/26; served counts were 142/332/26. All affected issuers were from Batches 48-50. The existing parity verifier masked this because it sanitized the expected artifact before comparison. | ✔ **RESOLVED in Audit 169** — live counts now match 116/358/26 with zero raw-to-served mismatches. |
| L500-02 | **P1** | **221/500** artifacts use `conditional_estimate` as `model_policy.primary`. That describes availability, not the valuation formula, so model identity and calculator semantics are not fully transparent. | ✔ Direct scan of all stored artifacts; only 279 name a formula as primary. |
| L500-03 | **P1** | **190/474** numeric ranges are wider than 125% of base; 61 exceed 200%, 10 exceed 500%, and WBD/BA/URI exceed 1,000%. These may be conservative, but they need post-WG calibration review before being treated as useful baseline decisions. | ✔ Recalculated `(high-low)/base` for every numeric artifact. |
| L500-04 | **P1** | **34** numeric bear cases use a zero floor. Thirty-two set the machine-readable floor flag; CHTR discloses the floor only in prose and WBD lacks a clear machine flag or equivalent floor wording. | ✔ Raw artifact scan and warning readback. |
| L500-05 | **P1** | “Pass” and reliability are poorly discriminated: 112 of 116 stored available results are still Low reliability; only four are Medium and none are High. The product must clarify whether Pass means source completeness, publication availability or confidence. | ✔ Availability/reliability cross-tab across all 500 artifacts. |
| L500-06 | **P1** | Working-group status still describes a 440-company baseline with 419 recipes, 263 compiled contracts and 156 implementation gaps. It must be rebound to the confirmed 500-company catalog before WG work resumes. | ✔ Current working-group plan readback. |
| L500-07 | **Release gate** | Production still serves the 100-company Batch 1-10 catalog. This is expected because promotion is unauthorized, but the staged 500-company result is not production-ready until L500-01 is fixed and a separate activation/UAT approval is given. | ✔ Production and staged `active.json` readback. |
| L500-08 | **Release gate** | The current worktree is on `codex/universe-reset-batch-10` with 49 tracked changes and 472 untracked paths. Generated evidence should stay untracked, but a scoped final diff and branch/remote check are required before any push. | ✔ Git branch/status/remote readback; no mutation performed. |

## Deferred to the post-WG deep audit

- issuer-by-issuer source freshness and current-period completeness;
- full economic suitability and normalized-input challenge for all 500;
- point-in-time outcome/backtest and reliability-label discrimination;
- browser list-to-detail UAT;
- final serving activation, rollback and deployment checks.

## Conclusion

The **500-company staged dataset is mechanically intact**. L500-01 is resolved, so its API Pass/Conditional totals are
now trustworthy. The dataset is still **not release-ready**: rebind the working groups to this 500-company baseline,
address the shared model-identity and calibration gaps there, then run the deep audit once.
