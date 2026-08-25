# Controlled Batch 03 starting gate

**Valuation date:** 2026-08-14

## Frozen denominator

Manifest SHA-256: `09734cc4804691dcfcef3f1fa6ab87f8953052666787b944600f7f3c5f527890`.

Exactly ten issuers: LYV, ECHO, NWSA, GOOGL, TTD, DIS, APP, FOXA, TKO, PSKY. The
batch contains eight Communication Services core members and two same-cohort rare-subindustry
boundaries (NWSA publishing and FOXA broadcasting), all in the operating-FCFF partition family.

## Protected baseline

- Backend U.S. valuation serving hash:
  `f68fd4d359e7e20dbf5daff4fddd91caa76d68cf95d3559702d4c80ae53d2c04`.
- Frontend public-data hash:
  `5157530c9c4baf3e9d5e6b0455a54579c94a5ead79c07145d9f4d35aef0e7017`.
- Generated frontend research hash:
  `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
- Recovery Learning Watchlist: seven entries, SHA-256
  `6a4ada1c3de56831d85e0df4a855374c4b9c5b9a6a796ec9e25c2bfe0da14692`.
- Dirty worktree at start: 227 status entries; all existing tracked and untracked work remains
  user-owned and must be preserved.

## Source readiness audit

Only APP has a reusable full local submissions/Companyfacts packet in the difficult-106 corpus.
Its latest cutoff-eligible filing is accession `0001751008-26-000059`, 10-Q filed 2026-08-05,
period ended 2026-06-30. The packet is an official-source packet for the same 2026-08-14 cutoff.

LYV, ECHO, NWSA, GOOGL, TTD, DIS, FOXA, TKO, and PSKY have no complete local source packet.
They require targeted immutable SEC capture. No replacement, skip, or outcome-driven selection is
permitted.

## Initial-pass gate

1. Add an immutable Batch 03 contract and reuse/generalize Batch 02 capture infrastructure.
2. Capture exactly nine missing packets plus the reusable APP packet into one canonical Batch 03
   source root; verify identity, cutoff, hashes, and no serving mutation.
3. Capture/parse one controlling filing package per issuer outside the serving process.
4. Apply strict and practical source-bounded policy. Conditional estimates are not part of the
   initial pass.
5. Independently challenge all numeric and withheld decisions.
6. Reproduce twice, run focused/full suites, and verify the real staged API.
7. Present exact initial results and stop before recovery, watchlist mutation, Batch 04, promotion,
   merge, or deployment.

