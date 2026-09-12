---
name: preferred-investment-is-not-issuer-claim
description: Separate Berkshire's investee preferred assets from issuer equity claims; retain class conversion and dilution policy.
metadata: { type: gotcha }
---
Berkshire's `PreferredStockInvestmentLiquidationValue` appears under the structural investment-holdings table. A preferred-name substring scan wrongly treated this asset as Berkshire's own preferred liability. Exclusion requires explicit investment semantics and investment-table ancestry, not amount matching or a blanket ignore.

The real June 2026 primary statement separately reports common stock, common APIC, retained earnings, AOCI and treasury stock; these reconcile to $747.910B parent common equity. Its Class-B-equivalent denominator is 488,450 Class A shares times the filing's 1,500 conversion ratio plus 1,408,035,161 Class B shares. Preserve the approved Batch 37 +/-1.5% dilution sensitivity separately from the locked reported count. Replacing all case denominators with the base count silently narrows the original range.

Verified through the shared source CLI: `output/us-refresh-runtime/source-validation/d798f7b538a96adb35758019802007a5c4ae80a139fb0a17e99d70a63b6ec232/report.json`. The range reproduces 271.3103772878122 / 424.88982342561985 / 613.46855658243. This is frozen-source verification, not successive-quarter acceptance.
