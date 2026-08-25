# Batch 02 canonical-universe proof blocker

**Audited:** 2026-08-24 (Asia/Manila)

**User signal:** Start universe reset Batch 02

**Status:** historical hard stop correctly reached; subsequently resolved by the user's explicit
authorization of a replacement S&P 500 universe. See Audit 16. No company was processed during
this blocker audit.

## Required gate

The controlled reset requires exactly 500 unique issuer-level identities as of 2026-08-14,
with ticker, CIK, name, filing regime, membership source/effective date, one primary share class,
and no silent substitutions. Batch 01 CIKs are then removed only from future assignment and the
remaining 490 are partitioned into 49 immutable batches.

## Firsthand result

No local or reachable Git artifact proves the intended historical 500:

- The root and protected-worktree serving corpora each contain 206 unique tickers/CIKs. These are
  valuation-output subsets, not membership manifests.
- The legacy recovery corpus contains 123 rows / 120 unique issuer CIKs, all already within the
  206 served subset.
- The period-aware difficult-case replay contains 106 companies, also within the 206.
- Historical documents mention “500 companies” and “477 with full data” but contain no 500-row
  ticker/CIK artifact, membership source, effective date, share-class rule, or immutable hash.
- Reachable Git objects contain no U.S. universe/constituent manifest. SEC caches contain facts
  only for issuers already chosen and cannot establish why the missing 294 belonged to the
  intended universe.

Therefore, no deterministic Batch 02 can be frozen. Selecting ten from the 206, the 106, or a
fresh index list would silently substitute a different universe.

## Sufficient unblock evidence

Either provide the original dated 500-row artifact, or explicitly authorize a replacement
universe. A valid replacement must be frozen with:

- exactly 500 unique normalized CIKs;
- one primary listed ticker/share class per issuer, with exceptions recorded;
- issuer name/status and filing regime;
- source URL/artifact, effective date, retrieval time, and SHA-256;
- reconciliation of the historical `500 = 477 with data + 23 explicit failures` claim when
  possible; and
- mapping of all Batch 01 and 206 served issuers without dropping unsupported companies.

## Actions completed before the stop

- NEE was added as Batch 01's first entry in the cumulative post-recovery withheld register.
- No Batch 02 manifest, source packet, valuation output, serving write, promotion, merge, or
  deployment was created.
