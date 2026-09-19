# WG40 independent BIIB source, economic and implementation challenge

Reviewer `wg38_pharma_claims` continued as `gpt-5.6-luna`, high reasoning under
`finsight-efficiency`. Cached evidence only, read-only and no network. Primary
verified each material finding firsthand.

The source challenge rejected the historical $124.3M/$62.15M/$0 legal
sensitivity. The judgment fact is disclosure-only; no Genentech carrying
accrual, payment, interest, recovery or appeal probability is reported. Apellis
transaction accounting, funding, current cash/debt and partial product revenue
bind, but acquired OCF/FCFF and comparable pro-forma cash do not.

The first code challenge found two material defects:

1. BIIB lacked an explicit preferred-zero migration guard, risking coexistence
   of the legacy mixed claim slot and new $273.5M acquisition claim if the gate
   later cleared.
2. RayThera $225M/$775M narrative terms were sourced from XBRL contexts labeled
   for TJ Bio, producing misleading lineage.

Primary corrected both. BIIB common components now reconcile exactly to $18.848B
parent equity and source preferred $0. The compiled current scenario subtracts
only the $273.5M acquisition claim; legacy values remain diagnostics. RayThera
numeric fields are null and explicitly narrative-only/unbound until correct
provenance exists. Generic workforce payments remain non-exclusive to Apellis.

Final reviewer result: **PASS**, 25 focused checks passed with 2 deselected; no
remaining material WG40 defect. Frozen workers preserve BIIB review and exact
GILD/INCY candidates. Primary focused134 and broad811 also pass. This approves the blocked evidence result, not current
BIIB valuation or publication readiness.
