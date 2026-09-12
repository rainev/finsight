# AR1: automated valuation ingestion-refresh

Checked 2026-09-08 against the named source modules.

## Reference
User-approved Automated U.S. Valuation Pipeline Improvements plan.

## Ours today
Rechecked 2026-09-08 against `refresh_job.py`, `refresh_catalog_store.py` and `scripts/refresh_us_valuations.py`: the command and pinned catalog reader now exist. Issuer refresh policies remain incomplete. Existing SEC retrieval and ingest_manifest support reusable capture, but batch_44_history.py and earlier batches still embed periods, expected values, and event policy.

## Reuse and consumer flow
Reuse source capture, pure model engines, sanitizer, and versioned catalog. Target flow: capture -> normalize -> evaluate -> validate -> complete catalog -> API/browser.

## Gaps
- P0 ✔ AR1: A reusable registry, changed-source detection, immutable snapshots, checkpoints, complete catalog activation and worker reload.
- Runtime validation for the replacement flow remains open; existing tests do not establish new-flow acceptance.
- P0 ✔ A resumed acquisition previously could mix successful old retrievals with entirely recaptured inputs. Successful company packets now checkpoint with hashes; resumed retrieval pins cutoff, registry, SEC client configuration and policy/recipe/predecessor fingerprint. Real cached AAPL/JPM transport interruption/reuse is tested; live SEC retrieval remains unverified.
- P0 ✔ Activation lacked a stale-predecessor check. New refresh catalogs now require explicit compare-and-swap preconditions under the writer lock; stale and initial-race candidates must not change the active pointer or history. Focused store tests cover this; full real successor activation remains gated.
- P1 ✔ Offline snapshot ingestion now rejects extra companies globally and treats wrong-issuer/malformed payloads as retrieval failures, not new company financial invalidity.

## Evidence and status
Firsthand source review and prior reproduction in this task. Open; tracked by AUTOMATED-US-VALUATION.md.
