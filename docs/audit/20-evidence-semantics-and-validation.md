# Audit 20 — evidence semantics, tables, DQC, and restatements

Reference: `/Users/carlosconda/Downloads/PLAN.md` Phase 2, lines 34–74.

## Ours today

✔ The resolver is deterministic and already hard-rejects form, accession, period, unit, economic-class, role, dimension, and orientation conflicts (`concept_resolver.py:27-38`, `360-394`). It also supports governed extension heuristics (`397-409`) and rejects ambiguity/component-total conflicts (`757-833`).

✔ The checked-in aliases/rules are reusable, but their contracts are split and narrower than the requested governed field registry. Standard aliases require an official US-GAAP namespace (`concept_resolver.py:109-119`); extension semantics depend on text/rule heuristics rather than explicit per-issuer custom-tag governance.

✔ The current table/note extractor flattens HTML into lines, takes the last numeric token, and explicitly handles CRM/WDC patterns (`filing_evidence.py:34-61`, `150-166`, `174-210`, `287-330`). It cannot prove the selected current/comparative column or complete search scope generically.

✔ `FieldAvailability` already has most fail-closed states and enforces complete extraction for `not_disclosed` plus a 365-day annual carry-forward (`field_availability.py:15-56`, `296-350`). It does not preserve the complete candidate/rejection ledger.

✔ No governed DQC execution path or restatement ledger was found in `backend/app/us_valuation`; duplicate selection currently chooses a latest eligible fact by filing/accession without linking original and correction (`xbrl.py:254-277`; `equity_fact_selection.py:111-131`).

## Reuse check

Extend the current alias/rule registry, structural fact/resolver, table evidence record, and `FieldAvailability`. Reuse Arelle parser diagnostics as the transport for DQC messages, but keep XBRL US DQC rule execution in the offline worker. Do not revive the rejected taxonomy-mismatched XUSSS normalizer.

## Consumer flow and backing

Arelle currently discovers facts and FinSight applies hard gates, which matches the intended responsibility split. The missing layer is a unified, point-in-time evidence decision that retains every accepted/rejected candidate, governed semantic meaning, consolidation identity, search completeness, and diagnostics before projection into valuation availability.

## Gaps

- **P0 ✔ OE2-01:** Expand the field registry to encode standard/custom aliases, roles, allowed dimensions and consolidation scope, units/period roles, valid aggregates, double-count exclusions, accounting meaning, and economic class.
- **P0 ✔ OE2-02:** Add explicit entity identifier/scheme and consolidation scope to structural contexts/candidates; dimensional permissibility alone cannot prove public-parent scope.
- **P0 ✔ OE2-03:** Replace ticker branches and last-number parsing with DOM table extraction that preserves table title, row label, column/date label, units, excerpt, accession, and deterministic ambiguity outcomes.
- **P0 ✔ OE2-04:** Record complete-search scope before `not_disclosed`; an empty candidate list is not completeness proof.
- **P0 ✔ OE2-05:** Run taxonomy-year-matched XBRL US DQC rules offline as diagnostics only; DQC may reject/lower confidence and must never create a value.
- **P0 ✔ OE2-06:** Create a semantic restatement ledger linking original/corrected facts and make cutoff selection replayable before and after an amendment without look-ahead.
- **P1 ✔ OE2-07:** Normalize evidence outcomes to `reported`, `reported_aggregate`, `explicit_zero`, `not_disclosed`, `stale`, `conflicting`, `bounded_estimate`, or `unresolved`, while mapping existing availability names compatibly.
- **P0 ✔ OE2-08:** Add fixtures for custom tags, consolidation dimensions, current/comparative table columns, ambiguous tables, pre/post-cutoff restatements, wrong units/periods, contradictions, and silent-zero rejection.

Status: audit complete; all findings were rechecked firsthand in the cited files. No pipeline code changed in this batch.
