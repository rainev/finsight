# WG22 independent financial challenge

Completed 2026-09-15 by `wg22_challenge`, spawned as `gpt-5.6-luna` with **high**
reasoning. Read-only scope: ETN current filing/structural evidence, the candidate
receipt, WG22 NCI/acquisition/precision rules and HCA/HON compiler blockers.
Earlier capacity failures are historical; they did not count as review.

## Conclusion

No material economic or integrity defect found in the current WG22 result.
The primary rechecked every load-bearing finding firsthand against the actual
code and hashed raw/structural sources. No code correction or valuation change
was required by the challenge.

- Ordinary NCI is $45M and reconciles exactly to $20.299B consolidated equity
  minus $20.254B parent equity and to the NCI equity member. It is not an earnings
  or owner-flow amount. See `refresh_reported_claim_scope.py:463` and candidate
  `ETN.json` equity-reconciliation ledger.
- Resilient contingent consideration is $32M once. Aggregate, Level-3 and named
  acquisition presentations corroborate; unknown current claims fail closed.
  Acquisition cash of $11.079B is already paid and non-additive. See
  `refresh_acquisition_claims.py:466` and `:496`.
- The raw filing separates the $32M liability from the $45M maximum and from
  $50M service/continued-employment contingent incentives. $16M H1 compensation
  expense remains operating, not another financing claim. No acquired FCFF or
  synergies are invented.
- Common-only equity components sum to $20.255B against $20.254B parent equity.
  All five inputs have context `c-13` and explicit `decimals=-6`. The existing
  `reported_precision.reconcile_reported_sum` computes $2.5M as the sum of five
  half-unit rounding bounds. Missing/coarser precision and explicit nonzero
  preferred balances fail. No balancing amount is created.
- HCA's professional-liability overlap and HON's separation/split/subsequent
  acquisition blockers remain in `refresh_operating_policies.py:625–628` and
  the real-source focused tests. Their NCI proof is not a full refresh approval.

## Non-blocking hardening note

The common-only preferred-equity scan primarily examines current USD facts;
ETN does not have an explicit preferred-share qname requirement. The primary
searched the entire current package and confirmed **no preferred or temporary-
equity facts in any unit**, so this does not invalidate current proof. An
unfamiliar future filing with share-only preferred issuance needs a fail-closed
instrument-structure guard. This is recorded as WG22-R2 before final release,
not implemented or represented as existing support.

## Primary verification after review

- Current implementation SHA-256:
  `684b97ae4f4c41a0fbb66c760c44bf2f4f146f8fb0c9019c6b5a018c1a6acceb`;
  policy SHA-256
  `4eab51ed84c75a9d5e67d4e030d633e2aff4f84a8ad566735fa1551ace9159b5`.
- Fresh direct cached-source command rehashed selected bytes and reproduced
  `eb188494a364e5da23353f2278311c6a505c16e3c8eb350837d80e0baae9c827/report.json`:
  one ETN candidate, two implementation gaps, no activation.
- The frozen two-worker manifest/report reproduced unchanged. Existing real
  FastAPI/database activation/reload/rollback and blocked/excluded parity
  receipts were rehashed and matched the current implementation checkpoint.
- Focused WG22 plus bridge-source regression: **48 passed in 1.97 seconds**.
  The prior 595-test suite remains applicable because no implementation or
  policy bytes changed; fingerprints were checked, not assumed.

Full company results and source/API hashes remain in
[WG22 evidence](wg22-ordinary-nci-mappings.md). WG22 was **verified and user-
confirmed 2026-09-15**, not rollout approval. Production, Git HEAD, scheduling,
deployment and family-adapter scope remain unchanged.
