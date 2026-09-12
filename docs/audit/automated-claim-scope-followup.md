# Refresh claim-scope follow-up — 2026-09-08

Scope: frozen B01–B44 recipes only. No source amount, filing date or scenario
value is promoted to a reusable policy merely because it matches an old output.

## Primary-verified source findings

- **APH:** retained `output/batch-26-history-run-b-20260831/generated/APH/valuation-private.json`,
  `history_backed.source_ledger.bridge_reconciliation.other_equity_claim_formula`,
  explicitly identifies $121.5M MinorityInterest plus $9M redeemable NCI.
  The bridge source ledger names both exact US GAAP concepts, accession
  `0001104659-26-089194`, period 2026-06-30. The recipe's $130.5M preferred
  slot is therefore NCI, not a contingent reserve. Current normalized bridge
  checks, preferred-claim proof and acquisition/cash-conversion caveats still apply.
- **CF:** the current generator's bridge uses MinorityInterest, but
  `batch_43_history.py::_ttm` also removes a $170M litigation receipt from
  cash FCFF. A simple NCI mapping alone would omit this operating adjustment.
  Do not release the ordinary refresh policy until that source-backed normalization
  and its affected periods are rebuilt. This is not a reason to add $170M as debt.
- **META:** its retained earnings-multiple input is revenue-based hypothetical
  owner cash, not reported earnings. Its newer generator also differs from the
  frozen artifact in shares and reserves. Preserve frozen replay; a successor
  requires explicit investment/lease/commitment timing and overlap rules.

## Reviewer triage — not yet independently certified policy mappings

The two bounded claim reviews covered 19 issuers. Aside from APH and the CF
qualification above, reviewers identified mixed/non-NCI claims:
ABBV litigation; ABT contingent consideration; AMCR pension/ARO/environmental
stress; AME subsequent acquisition funding; AMGN tax/contingent claims;
APA operating stress; AVGO backstop exposure; AVY restructuring; BA loss reserve;
BALL pension/medical; BAX negative NCI and separation/contingent claims;
BDX product liability; BIIB contingent/legal claims; BMY CVR/fixed payments;
BR contingent consideration; BSX contingent/legal/restructuring; CAH opioid/IVC.

These findings identify the next source-rule work. They are **not** authorization
to omit claims, treat missing tags as zero, or count these companies as implemented.
