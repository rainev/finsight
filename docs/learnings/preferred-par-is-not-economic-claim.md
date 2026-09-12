---
name: preferred-par-is-not-economic-claim
description: MET zero preferred par must not erase its separately reported liquidation preference.
metadata: { type: gotcha }
---
The generic residual refresh accepted MET's zero `PreferredStockValue`, despite positive preferred shares outstanding. The actual controlling filing reports a $2.905B prior-period liquidation preference and identical current/comparative preferred series counts. The approved specialist treatment uses that economic claim, not zero par.

Require the liquidation amount in the controlling filing itself and reconcile every current/comparative series to the reported aggregate. Missing, changed, conflicting or unfamiliar nonzero series require review. Preserve raw par and effective claim separately. Do not use par-based historical ROE when an economic preferred-claim continuity rule was required; keep the explicitly approved case ROEs until comparable preferred history is available.

Verified real source binding: `output/us-refresh-runtime/source-validation/26aaae31fa9127cb264924f5f58598019010360bd1527eb8a1a7b004df41a1e3/report.json`. The earlier partial all-company diagnostic was interrupted rather than accepted as a clean completed sweep.
