# PSE V2 — Automated Intrinsic Refresh (draft)

**Status:** Internal stage-only runner, local filing-watch loop, and offline PSE summary-snapshot comparator implemented, 2026-09-26; no process is installed or left running. No external source is enabled, and a complete four-issuer filing refresh, approval, or activation has not occurred.

## Objective and boundary

Keep PSE intrinsic values current when a permitted new filing or an approved material assumption arrives. Automate the repeatable work from source identification through a **staged** valuation and change report; retain human judgment and a separate activation decision. No share-price feed, current-upside calculation, new valuation engine, or automatic publication is part of this work.

The locally active Batch 28 catalog has 282 ordinary-common records: 34 intrinsic valuations, 205 market-relative screens, and 43 unavailable results. The user's acceptance of existing numerical results is the planning baseline, **not** evidence that missing original-filing lineage or model judgments have been independently verified. Keep intrinsic, market-relative, and unavailable labels distinct; do not rewrite the active catalog merely to record this plan. The first automated refresh scope is the 34 intrinsic issuers. Relative screens and unavailable cases remain unchanged unless separately reviewed.

## One refresh cycle

1. **Identify a permitted change.** One idempotent scheduled job checks only approved source paths for new or amended filings. An authorized manually supplied filing can trigger the same job. Check source-access, automated-use, storage, and display rights **per source** before enabling its fetcher; an accessible URL is not permission. Do not fetch from an uncleared source. Approved dated macro observations may also trigger a rerun. Prices do not.
2. **Capture and reconcile.** Store permitted original bytes and their content hash privately in existing MinIO; record URL, publication/retrieval dates, period, page, and rights basis in Postgres. Keep original-file hashes distinct from hashes of analyst fact receipts. Extract candidate facts, preserving currency, units, consolidation scope, restatements, ordinary-common shares, minority claims, and ownership. A reviewer resolves material extraction/accounting ambiguities; missing critical facts block the affected rerun rather than becoming zero.
3. **Revalue only affected issuers.** Reuse the four V2 engines and versioned route/assumption records. Recalculate bear/base/bull from reviewed facts and approved macro inputs. Include parent SOTP dependencies when a subsidiary changes. Do not silently carry an obsolete benchmark, share count, ownership bridge, or unsupported terminal period forward.
4. **Stage and explain.** Produce deterministic, hash-bound artifacts and a complete 282-entry candidate catalog, preserving unchanged artifacts byte-for-byte. Report old versus new value, source/fact/assumption changes, status and warnings. Changes over 20% require an explicit attribution; a failed check or incomplete source produces a staged hold, never a replacement active value.
5. **Review, then activate separately.** A human signs off on the new filing interpretation, material assumptions, attribution, and candidate result. Only a separately confirmed activation switches the active pointer. The prior catalog stays available for rollback; the API and UI keep showing its dated value until activation.

## Small rollout

**Gate 0 — source path:** Identify permitted issuer-first filing paths and an approved macro source for the pilot. Record what automated retrieval, private storage, derived-value display, and links are allowed. Where rights are not cleared, use only authorized manual inputs and leave the automated fetcher disabled. No price-source decision is needed.

**Pilot — one issuer per intrinsic engine:** AP (FCFF), BPI (residual income), RCR (distributions), and RLC (SOTP). Reuse the supervised findings, but do not treat them as completed refreshes: AP still needs a filing-to-FCFF bridge, RCR a post-issuance payout/share check, and RLC an attributable property/ownership bridge. A blocked pilot route stays blocked while other routes proceed. Start with a real permitted filing, not a synthetic event.

**Expansion:** Once a complete pilot cycle has produced reviewed staged artifacts and a separately confirmed activation, extend the same templates to the remaining intrinsic issuers in small groups. Keep the 205 market-relative and 43 unavailable records outside this intrinsic-refresh job unless the user separately changes their scope.

## Acceptance checks

- The same filing and versions produce identical hashes; unchanged filings create no duplicate run or catalog.
- Amended filings, restatements, unit/scope conflicts, share changes, missing facts, stale macro observations, and parent dependencies are handled explicitly.
- Independent calculation checks cover all four engines; material value movements show attributable drivers.
- The staged catalog has exactly 282 entries; inherited artifacts are byte-identical; stored artifacts match authenticated staged API responses and the staged PSE page.
- The real pilot works on a clean Postgres/MinIO environment. An invalid source or failed check leaves the active pointer and public values unchanged.
- No live fetch, automatic approval, deployment, or activation occurs merely because tests pass or a schedule exists.

**Current prerequisite:** The [RCR source-rights review](../audit/59-pse-rcr-issuer-source-validation-rights-decision.md) has not cleared automated acquisition/storage/display. The later [RCR internal source-backed stage](../audit/61-pse-rcr-issuer-source-staged-refresh.md) produced a provisional candidate, but not original-file capture or issuer approval. The [RLC ownership review](../audit/62-pse-rlc-ownership-bridge-review.md) remains on hold. Enable external metadata polling or original-file capture only after its specific rights basis is recorded.

## Implemented internal stage-only entry point

`PYTHONPATH=backend python scripts/stage_pse_intrinsic_refresh.py --bundle <reviewed-bundle.json> --output <new-isolated-directory>`

The bundle pins the active manifest hash, a deterministic `PSE-V2-REFRESH-...` catalog version and valuation date, and **exactly** AP/BPI/RCR/RLC cases. Each case is either `hold` with a reason or `ready` with a relative path and SHA-256 for a reviewer-supplied JSON fact receipt. A ready receipt contains the filing period/publication date, source identifier and page, reviewer/date, normalized facts with per-fact units/scope/period/page, and three versioned scenario assumption sets. Discounted routes also require an explicitly reviewed ten-year benchmark; an observation over 90 days old needs a carry-forward reason. The [synthetic test helper](../../backend/tests/test_pse_internal_refresh.py) shows the exact shape but is **not** a source for a real valuation.

The runner replays all four pure model functions, checks RLC's property-by-owner bridge, carries held/unchanged artifacts byte-for-byte into an exact 282-entry catalog, writes a private change/hold report, and serves through the existing staged API when its catalog root/pointer are explicitly selected. New artifacts stay `provisional`, omit prices and public source URLs, and identify their hashes as **fact-receipt** hashes. A changed RCR with held RLC is flagged as a parent dependency. It never fetches, writes Postgres/MinIO, approves, activates, or deploys. Original-file capture, source-rights decisions, live scheduler deployment, and completion of the four-route refresh pilot remain future work.

## Internal filing-watch pilot

`PYTHONPATH=backend python scripts/run_pse_intrinsic_refresh_watch.py --bundle-inbox <reviewed-bundles-directory> --stage-root <isolated-candidates-directory> --state-dir <private-watch-state-directory>`

One invocation performs one tick; `--watch --interval-minutes 1440` keeps **one local process** repeating. No OS/Cloud Scheduler job has been installed or started. The versioned [source registry](../../backend/app/pse_valuation/config/internal_filing_watch.json) lists the four pilot issuers; all automated metadata-access flags are **false** until a source-specific rights record is cleared. Therefore the current tick makes **zero external requests**. When permission is recorded, the job can compare same-host issuer-page PDF links, baseline the first index, and flag new links for human fact review; it does not download or parse PDFs, and same-URL PDF replacements without an index change are not yet detectable.

Independently, the same tick discovers reviewer-supplied pinned bundles in the local inbox, stages each new bundle once through the existing runner, and records candidate and hold status. RLC is forced to `hold` by the scheduler; a changing RCR is reported as an RLC parent dependency. The job never changes an active pointer, approves a result, writes to Postgres/MinIO, or obtains a price. This is the *internal pilot scheduler*, not end-to-end unattended valuation underwriting or a live external filing feed.

## Offline financial-summary snapshot comparison

`PYTHONPATH=backend python scripts/run_pse_intrinsic_refresh_watch.py --bundle-inbox <reviewed-bundles-directory> --stage-root <isolated-candidates-directory> --state-dir <private-watch-state-directory> --summary-dir <locally-saved-snapshots-directory>`

This is **one local tick only**; `--summary-dir` disables all external index polling and cannot be combined with `--watch`. Supply at most one JSON snapshot per pilot ticker, named `AP.json`, `BPI.json`, `RCR.json`, or `RLC.json`. The [snapshot validator](../../backend/app/pse_valuation/summary_snapshots.py) pins each ticker to its PSE EDGE financial-summary URL and requires `schema_version: "PSE-V2-FINANCIAL-SUMMARY-SNAPSHOT-1.0"`, `ticker`, `source_url`, `observed_at`, `period_end`, `period_type` (`annual` or `quarterly`), `currency: "PHP"`, `unit` (`PHP`, `PHP_thousands`, or `PHP_millions`), `scope` (`consolidated` or `parent`), and a nonempty `facts` object of named finite numbers or explicit nulls. Dates are ISO dates. The locally supplied observations must be obtained and stored under the user's applicable source-access terms; this code does not acquire them.

The comparator hashes the period, units, scope, and supplied figures, excluding the observation date, so re-saving identical numbers does not trigger work. A first snapshot from a period later than the active artifact flags a new period; a first same-period snapshot sets a baseline; a changed same-period snapshot flags a restatement; an older period or invalid file is held. Only digest and period metadata persist in private watch state, not the summary figures. A change remains pending until a matching, hash-pinned reviewed receipt covers that period. For a restatement, the receipt must explicitly say `amended_filing`. Without that receipt, the active value stays unchanged. A matched receipt runs the existing model and writes an isolated `provisional` staged catalog; RLC still stays on hold. A PSE summary is a **change signal**, not a source of FCFF, distributions, ownership bridges, assumptions, or an automatic approval. This mode has been checked with synthetic summary signals and the previously reviewed RCR receipt; no live PSE capture or four-issuer real-source comparison is claimed.
