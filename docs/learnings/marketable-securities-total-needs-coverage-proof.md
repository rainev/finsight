---
name: marketable-securities-total-needs-coverage-proof
description: A generic or note-table marketable-securities total cannot replace current/noncurrent splits without issuer-specific coverage proof.
metadata: { type: gotcha }
---
A `MarketableSecurities` fact, an available-for-sale debt total, or a note-table “total marketable securities” line is not automatically the comprehensive current-plus-noncurrent investment balance. It may be a current caption, a debt-only subtotal, an equity-only subtotal, or overlap cash and disclosed components. A replacement total needs exact `covered_fields`, a governed coverage basis, source-fact lineage, the controlling accession/period/unit, and the expected economic scope. Use the proven total once or proven splits once; never both.

**Why:** KO, AMZN, AMD, CMI, and PLTR contain same-period totals or subtotals that overlap or differ from current components. Selecting by name or rank can double count investments or fabricate a missing noncurrent balance.

**How to detect / apply:** Keep generic totals as diagnostic candidates with no coverage. Permit `fallback_level="reported_aggregate"` only when the proof metadata is complete. Corroborate same-period splits against the total; mismatches and covered-component conflicts remain blocking.
