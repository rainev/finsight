# Audit 24 — FOD1 generalized official filing ingestion result

Status: **verified partial — FOD2 may proceed; difficult-corpus replay remains in FOD5**

Reference: `docs/audit/19-official-evidence-ingestion.md` and PLAN Phase 1.

## Implemented and verified

- Private `EvidenceRequest`, `EvidenceCandidate`, and `EvidenceDecision` contracts retain cutoff, identity, consolidation, selected/rejected candidates, completeness, exact source, extraction method, range provenance, and package failure.
- One canonical selector identifies the controlling 10-K/Q and latest eligible annual filing from frozen submissions. Manifest identity fields are cross-checked against submissions.
- Governed attachments, filed/report dates, XBRL context entity, and semantic package metadata are first-class. Parsed caches bind to package generation/manifest hash and reject tampering.
- One writer lock protects immutable output and records PID/time/manifest hash; cache/fresh parse paths serialize to identical receipts.
- Every material request has exactly one decision. An annual-package failure no longer masks a successfully parsed controller.
- Arelle remains child-process-only. All outputs are under untracked `output/`; protected serving hashes are embedded before/after and unchanged.

## Real cached replay evidence

### Batch 01

- Final receipts: `output/official-evidence-fod1-batch01-g/` and `batch01-h/`.
- 10 issuers; 100 requests; 100 decisions; 8 parsed packages; 10 explicit uncached-package failures.
- Outcomes: 13 `reported`, 4 `explicit_zero`, 83 `unresolved`; 18 candidates, 17 selected, 1 retained rejected candidate.
- Selected facts span AAPL, ANET, CRM, DELL, and WDC; DELL NCI was recovered from the exact filing without an exact Companyfacts accession/tag/value match.
- A/B receipt SHA-256: `a05364a335c5f87c98e005771898a613bed5685347a8f08ba655037047550e3c`; byte comparison exit 0.

### Batch 02

- Final receipts: `output/official-evidence-fod1-batch02-h/` and `batch02-i/`.
- 10 issuers; 100 requests; 100 decisions; 10 parsed controlling packages; 10 explicit uncached annual-package failures.
- Outcomes: 11 `reported`, 1 `explicit_zero`, 88 `unresolved`; 17 candidates, 12 selected, 5 retained rejected candidates.
- CHTR, CMCSA, and WBD NCI were recovered from exact filing contexts without exact Companyfacts accession/tag/value matches.
- A/B receipt SHA-256: `e092c6669f80d5d5ed9b43f03914048e99171a4fa5f75e4dbebf68cde331eb63`; byte comparison exit 0.

Both receipts record identical protected hashes before/after: backend serving `ed40fdae…`, frontend public data `353a14bc…`, generated research root empty hash `e3b0c442…`; `serving_artifacts_changed=false`.

## Automated verification

`373 passed in 6.45s` across official evidence/ingestion, filing package, structural schema/resolver/shadow, Arelle adapter/integration, and Batch 02 structural capture. `git diff --check` passed and no serving path appears in Git status.

## Explicit limitations

- Frozen local caches do not contain many latest annual packages and four Batch 01 controllers; each has an exact `OFFICIAL_PACKAGE_NOT_IN_FROZEN_CACHE` record. No monitored SEC contact is configured, so no fresh acquisition was attempted.
- The historical difficult-corpus package tree referenced by prior evidence is not present in this worktree. Its requested 106 denominator also conflicts with the retained 104-supported/21-excluded historical ledger and later 100-company replay artifacts. FOD5 must reconstruct and freeze the exact denominator/source manifest before the full replay.
- FOD1 decisions cover structural fields governed by the current registry. Table/note, DQC, restatement, and specialist sources remain FOD2/FOD3 work.

Conclusion: the reusable ingestion and evidence-record foundation is verified on the real cached Batch 01/02 consumer path. The phase is not fully complete because the difficult-corpus and missing annual packages cannot be replayed from current local inputs; those blockers are explicit and carried forward rather than papered over.
