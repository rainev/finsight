# Refresh growth and cash semantics — 2026-09-09

Scope: frozen B01–B44. This audit does not certify a whole financial model merely
because its historical growth numbers reproduce.

## Integrated and forward-replayed growth rules

Thirty-two tickers: GWW, GNRC, IR, BR, HLT, KO, PEP, HRL, PG, ADI, ADP,
ADSK, ALLE, AMAT, BBY, BF.B, BKNG, BLDR, CASY, CDW, CIEN, CPRT, CSX,
DDOG, DOV, DPZ, CMG, DECK, DRI, MAS, MSI, MCO.

MAS/MSI/MCO also have verified NCI-only claim mappings; their full current bridge
still needs evidence. MCO's growth expression is scoped to `_operating_data_result`
in Batch 37, not the unrelated energy-company function in the same file. Its
cash-interest-paid lineage is retained, without subtracting sale gains already
reconciled in reported OCF.

The compiler reads version-hashed retained generator expressions without importing
or executing the old batches. It checks the retained revenue-growth observations
with the common summarizer and reproduces each frozen scenario growth before
emitting data-only caps/floors. New filings supply new observations. Tests reject
unrecognized/ambiguous expressions and nonfinite values. Source/claim review is
still required independently.

## Follow-up group — component integration verified; bridge reviews remain

Growth rules below now forward-replay. CDW's scoped cash-interest series and
CMG's no-interest owner-cash history are implemented and checked on real source
data. BBY/DECK/DRI post-history stresses are compiled from declared generator
rates, not fitted to values; reported cash stays separate. Full source binding
still fails on unresolved bridge fields. No company was published or converted
to unavailable to evade those checks.

| Ticker | Retained generator | Growth rule | Separate economic issue |
|---|---|---|---|
| CDW | batch_31_history.py:230 | history clamp, caps -.03/.02/.05 | Inspect InterestPaidNet source lineage before using generic gross/net interest selection |
| CIEN | batch_29_history.py:443 | history clamp, caps -.03/.07/.14 | Purchase/warranty event scope remains separate |
| CMG | batch_06_launch_first.py:164 | pass-set clamp -.10/.20 | Owner cash uses OCF less capex, without financing addback |
| CPRT | batch_22_history.py:169 | history clamp, caps .02/.08/.12 | Current restricted cash and redeemable NCI still need bridge proof |
| CSX | batch_21_history.py:49 | history clamp, caps -.02/.02/.04 | Current bridge completeness remains separate |
| DDOG | batch_32_history.py:355 | history clamp, caps .05/.12/.18 | Convertible/capped-call scope is not a margin adjustment |
| DECK | batch_06_launch_first.py:178 | pass-set clamp -.10/.20 | Post-history margin haircuts .02/.005/0 must not be silently dropped or described as reported cash adjustments |
| DOV | batch_18_history.py:73 | history clamp, caps -.02/.02/.05 | Acquisition/disposition source comparability remains separate |
| DPZ | batch_07_history.py:180 | direct clamp -.10/.20 | Securitized debt bridge remains separate |
| DRI | batch_06_launch_first.py:178 | pass-set clamp -.10/.20 | Post-history margin haircuts .01/.003/0 require explicit policy treatment |

The remaining economic issues are work items, not new approved rules. Inspect the actual current
generator and retained recipe, prove all economic adjustments, and run source
binding before marking a company's refresh supported. Do not infer that a
`governed_assumptions.growth` list is historically derived: a later override may
replace the common rule with fixed special-situation assumptions.
