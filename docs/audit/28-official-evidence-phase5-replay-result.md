# Audit 28 — FOD5 combined replay and rollout result

Status: **historical 20-issuer gate; difficult-corpus blocker resolved by Audit 29**

Reference: `docs/audit/23-official-evidence-replay-and-rollout.md` and PLAN Phase 5.

## Verified implementation

- The replay manifest contains 10 Batch 01, 10 Batch 02, 106 difficult-corpus, and seven cumulative-withheld memberships. The cohorts contain 133 memberships but only **121 unique issuers** because five difficult issuers overlap Batch 02 and all seven withheld issuers already belong to Batch 01/02.
- Every one of the 225 locally replayable material requests has an explicit terminal outcome: 58 reported, 11 explicit zero, 13 bounded estimate, and 143 unresolved.
- Selected evidence comprises 64 current Companyfacts facts, one exact structural filing fact, four exact filing-table facts, and 13 annual carry-forwards. Raw-filing rescues: 1; table/note rescues: 4; regulator/supplement rescues: 0; selected custom-tag mappings: 0.
- Filing-table promotions now retain filed date, entity, consolidation scope, exact package-manifest hash, scale, locator, and accession. All four selected table values were filed before the cutoff. Multiple table candidates are retained and same-tier conflict checked instead of overwritten.
- The real valuation consumer replay completed 20/20 with zero build errors. It consumed all 82 projectable availability records with zero mismatches and retained a private trace for all 20 issuers. The generic valuation path remained 4 numeric before and 4 after; its public key shape changed for zero issuers. Evidence changed five generated withheld payloads, but none was written to a serving root.
- The final safety ledger reports **zero unsafe promotions**. Every selected point is checked for cutoff, source URL, governed unit, CIK, parent consolidation, accession, and projection equality. Filing-table checks independently recompute the package-manifest hash, bind the URL/CIK/accession to that manifest, and require consolidated title scope.
- Restatement diagnostics cover 199,308 candidates and 3,014 value-change links, with zero confirmed restatements. DQC ran 20 rule entries on ten filings, produced zero applicable assertions/errors, and created zero values.
- The deterministic FOD5 A/B report SHA-256 is `4af64ca23a94ff281ad74aed5393d724838e2f06bed05d611998f41fd1973864`; the complete output trees are byte-identical. Protected serving hashes are unchanged.

## Verified real API

- A real `app.main:app` Uvicorn process served the staged 20 artifacts on localhost.
- List returned HTTP 200/count 20 with exact staged parity.
- All 20 detail calls returned HTTP 200 and exact staged parity.
- Private leak count and forbidden Arelle/regulator/supplement/ingestion serving-import count were both zero.
- The API verification A/B SHA-256 is `6f523516d8faa13fd46377e83d32d6b7b186cd32ed929018243e5ca74e9a94fc`.
- Staged public output intentionally remains 11 numeric/review-required and nine withheld before and after; no promotion or serving write was authorized.

## Verified historical comparison, not attributable to FOD

The retained period-aware difficult-corpus report has exactly 106 candidates: 104 valid private inputs, 94 source-verified outputs, two invalid inputs, four source-integrity failures, six build errors, and 11 numeric results versus zero in its earlier baseline. That improvement predates this unified official-evidence replay and is reported separately; it is not claimed as a FOD rescue.

## Verified blockers

- Only five of the difficult 106 overlap the locally frozen official-evidence cohorts. The other **101 issuers have no frozen unified official-evidence source/package receipt** in this worktree. Fresh SEC acquisition cannot proceed honestly because `SEC_USER_AGENT` is currently unset; a monitored contact must be supplied rather than invented.
- Specialist packets remain nonpromotable: the current FR Y-9C bulk attempt returned HTTP 403, FERC identity/payload/allocation is unresolved, and Realty Income's exact SEC Exhibit 99 link lacks a locally frozen source payload and has an unexplained AFFO residual.
- Therefore the acceptance statements “difficult 106 officially replayed” and “specialist sources fully available” are false. Batch 03, artifact promotion, merge, push, deployment, and serving writes remain frozen.

## Automated verification

`PYTHONPATH=backend pytest -q backend/tests` completed with **1,175 passed, 3 skipped**. The skips are existing optional-capture skips. `git diff --check` passed.

Conclusion: the reusable official-evidence pipeline was implemented and consumer-verified for the locally frozen Batch 01/02 scope. Audit 29 subsequently captured and replayed all 106 difficult issuers, resolving the former 101-package blocker. Specialist packets and user confirmation remain open.
