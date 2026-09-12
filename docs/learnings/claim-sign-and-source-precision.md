---
name: claim-sign-and-source-precision
description: BR exposed an additive adjustment sign guard and a rounding-versus-missing-claim distinction.
metadata: { type: gotcha }
---
The enterprise cash-FCFF engine adds `nonoperating_adjustment` to equity. Its old
guard nevertheless rejected negatives, so a separate liability could not be
represented there even though the refresh compiler already emitted negative ADP
claim adjustments. The guard now permits this finite signed field; gross cash,
debt, preferred and NCI inputs remain nonnegative. Test reclassification against
the unchanged old recipe to prove a claim is deducted exactly once.

BR's complete common-equity components differ from its total by $100,000, with
all facts explicitly rounded to $100,000 (`decimals=-5`). Scoped interval
reconciliation records the residual and sums the reported half-unit bounds;
it does not use an arbitrary percentage tolerance. Missing precision/components,
unknown equity members, nonzero NCI and gaps outside the intervals still fail.
This resolves the common-equity proof, not unresolved finance-lease evidence.
