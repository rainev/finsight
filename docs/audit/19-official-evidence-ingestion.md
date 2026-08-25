# Audit 19 — reusable official-evidence ingestion

Reference: `/Users/carlosconda/Downloads/PLAN.md` Phase 1, lines 13–32.

## Ours today

✔ `filing_package.py:66-261` already captures a bounded, hash-addressed immutable XBRL DTS and raises typed `FilingPackageIncomplete` failures. `arelle_adapter.py:113-180` parses through a JSON-only child process, and `arelle_worker.py:600-703` runs Arelle offline. These are reusable foundations.

✔ The active generalized shadow runner still begins from withheld serving artifacts, one controlling filing, and a fixed supported-field set (`scripts/run_structural_xbrl_shadow.py:180-230`). Batch 02 separately owns a ten-issuer loop and selects one latest pre-cutoff 10-K/Q (`scripts/capture_batch_02_structural_sources.py:79-137`).

✔ `ResolutionRequest` records concept, period end, accession, unit, statement role, and form; `ResolutionDecision` records one selected fact/status/reasons (`structural_xbrl.py:397-564`). Neither is the plan's model/materiality-aware request nor a complete candidate/decision ledger.

## Reuse check

Reuse the existing `SecClient`, immutable filing package, child-process Arelle adapter, structural fact schema, resolver, protected-root hashing, and immutable JSON writer. Do not create a second SEC transport, XBRL parser, or serving-side Arelle import.

## Consumer flow and backing

Current flow is batch/shadow artifact → one controlling accession → structural package → Arelle → per-field resolver. It is not manifest-driven for arbitrary issuer sets, does not always capture the latest eligible annual alongside the controller, and is not automatically triggered by controlling-accession/material-field gaps. Package failure is captured by the shadow report but not converted into an explicit outcome for every material request.

The current DTS selector includes the primary document, schemas, linkbases, and referenced XML (`filing_package.py:118-187`, `422-442`); relevant non-XBRL attachments such as filed Exhibit 99 supplements are not in scope.

## Gaps

- **P0 ✔ OE1-01:** Add one manifest-driven issuer/filing selector that proves ticker/CIK, valuation cutoff, controlling 10-K/Q, and latest eligible annual; remove batch constants from the reusable path.
- **P0 ✔ OE1-02:** Persist filing metadata required for point-in-time safety—filed date, report date, form, accession, valuation cutoff, and issuer identity—through package, parse, request, candidate, and decision records. Current structural facts lack filed/report dates (`structural_xbrl.py:141-167`; `arelle_worker.py:574-584`).
- **P0 ✔ OE1-03:** Add private `EvidenceRequest`, `EvidenceCandidate`, and `EvidenceDecision` records with model, period role, materiality, source locator/method, rejected candidates, completeness proof, and the plan's outcome vocabulary; map rather than overload `ResolutionDecision`.
- **P0 ✔ OE1-04:** For every material request, serialize package/parse failure as an explicit unresolved evidence decision; never collapse it to an absent field.
- **P1 ✔ OE1-05:** Define and capture relevant filing attachments by governed role, not every arbitrary attachment; include SEC-filed supplemental exhibits needed by later phases.
- **P1 ✔ OE1-06:** Cache parsed structural output immutably by package generation so one filing package is parsed once across requests and replays.
- **P0 ✔ OE1-07:** Add deterministic fixtures and replay coverage for Batch 01, Batch 02, the difficult corpus, and a known empty-current-Companyfacts accession without writing serving roots.

Status: audit complete; all findings were rechecked firsthand in the cited files. No pipeline code changed in this batch.
