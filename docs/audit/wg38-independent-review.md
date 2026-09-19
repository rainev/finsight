# WG38 independent financial and implementation challenge

Reviewer `wg38_pharma_claims` was spawned as `gpt-5.6-luna` with high reasoning
under `finsight-efficiency`. It used cached evidence only, made no network calls
and did not edit the repository. The primary agent rechecked all material source
and calculation findings firsthand.

The review confirmed that BIIB, GILD and INCY share a role-based contingent-
claim framework, not one identical CVR formula. Recognized carrying liabilities,
duplicate fair-value presentations, contractual ceilings, paid cash, legal and
royalty scopes must remain separate.

The initial review found two material fail-closed defects:

1. synthetic unsupported nonzero dimensional liability rows were silently
   ignored for all three issuers; and
2. GILD's separate Immunomedics $1.1B carrying / $700M fair-value future-royalty
   obligation did not force review despite unresolved forecast-cash overlap.

The primary corrected both. Unknown nonzero claim dimensions now reject for each
issuer. GILD retains $337M as a reconciled acquisition subclaim but returns
`review_required` with
`immunomedics_future_royalty_scope_and_cash_overlap_unresolved`. BIIB remains
blocked by the Genentech judgment carrying scope. INCY's $102M ARIAD/Takeda claim
is safe as a separate bridge deduction because its $9.565M payment is classified
as financing cash and remains nonadditive; the full issuer still fails on broader
bridge fields.

Final reviewer readback: **PASS**, no remaining material WG38 defect. Reviewer
focused checks: **10 passed, 2 deselected**, plus direct adversarial mutation
checks. Primary focused suite: **40 passed**. Frozen report
`681d1199a1c283efdc39097be5ae036c5e637853335f04d1dd1c2dab8c99121d`
honestly reports three `source_or_economic_review` results. Isolated 440-company
API evidence preserves exact BIIB/GILD/INCY detail and calculator parity. Broad
regression is recorded in the main WG38 audit.
