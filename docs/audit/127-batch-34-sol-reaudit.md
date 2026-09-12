# Batch 34 Sol Re-audit

Date: 2026-09-03
Status: **read-only audit complete; repairs verified in Audit 128, confirmation pending**

## Reference

This audit compares the confirmed Batch 34 recovery state against FinSight's practical bounded-
uncertainty policy, private traceability requirements, Pass/Conditional/Withheld semantics, and the
real public API contract. The audited candidate is recovery G/H in
`output/batch-34-recovery-run-g-20260903` and `output/batch-34-recovery-run-h-20260903`, documented
in Audit 126.

The confirmed disposition is Pass 2 (USB, BRO), Conditional 8, Withheld 0, Numeric 10. The Recovery
Learning Watchlist contains 223 issuers — 213 Conditional and 10 Withheld.

## What is verified clean

- ✔ All ten issuer identities, controlling accessions, cutoff dates, report periods, currency units,
  and share units match the source manifests and structural packages.
- ✔ Five cutoff-safe annual earnings periods exist for every company; L and SPGI explicitly bridge
  consolidated earnings to parent earnings using reported NCI.
- ✔ NTRS uses exact Series D/E preferred carrying values totaling `$884.9M`.
- ✔ STT uses exact June preferred carrying values totaling `$3.559B`, adds the cutoff-safe `$500M`
  Series L claim, and adds approximately `$495M` issuance proceeds to current equity.
- ✔ All 30 displayed scenarios independently replay exactly through the residual-income formula;
  every range is finite, ordered, and positive.
- ✔ The isolated 340-company API has exact list/detail/calculator parity and zero private-key leaks;
  Arelle and specialist parsers remain outside the serving process.
- ✔ Bookkeeping is internally consistent: USB/BRO are absent from the watchlist, the eight remaining
  Batch 34 Conditional companies are present, and the withheld register is unchanged.

## Gap register

### P1 — Important, verified

1. **✔ Public model identity is wrong for USB and BRO.** Their private models and
   `primary_valuation_method` are residual-income/equity-earnings models, but the staged public
   artifacts declare `model_policy.primary = "fcff_dcf"`, expose an FCFF model/bridge surface, and
   describe an FCFF bridge as complete. The values were not calculated by FCFF. The error comes from
   the available-result branch reused from `scripts/run_batch_08_history.py`.

2. **✔ Recovery reliability is stale for BRO, NTRS, and STT.** `_reprice_with_claim()` changes the
   ranges but does not recompute `history_reliability`. The private movement ratios no longer match
   the final ranges, so sanitization replaces the public payload with
   `RELIABILITY_PAYLOAD_INVALID`. The final movement ratios are approximately `0.418926` for BRO,
   `0.372273` for NTRS, and `0.352006` for STT.

3. **✔ USB's Pass state contradicts its private baseline and reason codes.** The top-level and public
   availability are `available`, while `baseline.availability_type` remains
   `conditional_estimate`. Its retained reliability still cites `PROVISIONAL_BANK_CAPITAL_RANGE`
   and `SPECIALIST_MODEL_UNCERTAINTY`, while recovery reason codes say the release gate is closed.
   BRO likewise retains `SPECIALIST_MODEL_UNCERTAINTY` after promotion. Pass can remain Low because
   of scenario width, but open material reason codes cannot silently coexist with a closed Pass gate.

4. **✔ Confirmed-input and Pass-source evidence are not execution-bound.** The recovery runner checks
   only batch number, attempted count, and zero withheld; it does not pin the exact user-confirmed
   initial report hash, ticker order, or `0/10/0` disposition. USB and BRO Pass evidence is stored as
   hard-coded dictionaries with document hashes, but the recovery function never reads or hashes
   those HTML documents. The cited files currently match those hashes, but the executable gate does
   not prove that relationship.

5. **✔ Preferred claims are not period-specific in the beginning-equity/ROE bridge.** Recovery applies
   the current claim to both beginning and ending equity. STT's 2025-12-31 claim was `$3.559B`, but
   the private beginning common equity deducts the later Series L `$500M` too: `$23.782B` stored
   versus `$24.282B` source-reconciled. Stored TTM ROE is `13.5977%`; the current private earnings and
   correct period-specific equity imply about `13.1507%`. TFC similarly applies the current
   `$5.411B` preferred claim to 2025-12-31 even though the filing reports `$4.916B`; its corrected
   beginning common equity is `$60.273B`, not `$59.778B`.

6. **✔ Six recovery paths are labels rather than implemented repairs.** L, SPGI, PGR, TRV, KEY, and
   TFC receive a `repair_tested` string and release condition, but no recovery-specific source or
   valuation input. The separate source-audit file contains useful evidence but is not consumed by
   the recovery builder. NTRS's recorded release condition is also stale: it asks for exact preferred
   value and cutoff redemption state even though recovery now proves both.

7. **✔ Verification coverage does not assert the semantic contract above.** Current tests and API
   parity prove arithmetic and byte equality but do not reject a wrong public model identity, an
   invalid reliability fallback, an unpinned confirmed input, an unverified narrative hash, or a
   current preferred claim applied to a prior period.

### P1 — Important lead, not yet proven

8. **⚠ BRO's Pass model may be economically inconsistent with the established insurance-broker
   route.** Batch 33 values MRSH through `insurance_broker_cash_faded_fcff`, while BRO is promoted
   using book-equity residual income. BRO is acquisition-heavy and asset-light, so an FCFF or cash-
   conversion cross-check may be more suitable. This is a model-suitability lead until BRO's
   comparable cash history is reconstructed and compared; it must not drive reclassification yet.

### P2 — Minor, verified

9. **✔ L/SPGI derived parent-earnings rows omit a top-level `unit`.** Their reported components carry
   USD correctly, but the derived rows do not.
10. **✔ STT's Series L event appears twice in private preferred context.** Arithmetic counts the
    `$500M` claim once, so displayed value is unaffected.
11. **✔ The recovery source-audit receipt is stale.** It still describes NTRS/STT exact preferred
    claims as unresolved and should be labeled pre-repair or regenerated.
12. **✔ The audit index is stale.** It still labels Audits 122, 124, and 126 as requiring user
    confirmation even though those outcomes were confirmed.

## Audit disposition

No Critical source-identity or arithmetic failure was found. The reported ranges remain usable as
Low-reliability decision baselines, and USB/BRO have plausible Pass economics. However, the final
recovery artifacts are **not promotion-ready** because seven verified Important gaps remain. Fix the
public model contract, recompute reliability and period-specific equity/ROE metadata, bind the exact
confirmed/source inputs, and strengthen semantic tests before another deterministic/API replay.

This audit changed no valuation, recovery, watchlist, withheld, serving, merge, push, or deployment
state.

Repair update: Audit 128 closes all verified findings. Its repaired result is Pass 1 / Conditional
9 / Withheld 0 / Numeric 10 and awaits user confirmation because BRO returns to Conditional.
