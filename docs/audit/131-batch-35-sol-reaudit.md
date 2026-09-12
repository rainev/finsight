# Batch 35 Sol Re-audit

Date: 2026-09-04
Status: **read-only audit complete; repairs verified and user-confirmed in Audit 132**

## Reference

This audit compares the user-confirmed Batch 35 state in Audit 130 against FinSight's practical
bounded-uncertainty policy, the frozen 2026-08-14 cutoff, the source/claim traceability contract,
Pass/Conditional/Withheld semantics, the public model/calculator contract, and the real API flow.
The audited final candidates are G/H in `output/batch-35-history-run-g-20260904` and
`output/batch-35-history-run-h-20260904`.

The confirmed disposition remains Pass 0 / Conditional 10 / Withheld 0 / Numeric 10. Confirmation
and watchlist bookkeeping are not undone by this audit; the ten Batch 35 issuers remain on the
Recovery Learning Watchlist while the gaps below await repair.

## Ours today and consumer flow

The source packet chooses the latest eligible 10-K/10-Q, the structural packet parses that filing,
the Batch 35 history builder produces a private residual-income or FCFF result, the public builder
sanitizes it, the immutable catalog binds the public bytes, and the API serves list/detail/calculator
responses. Event filings are handled by a separate hard-coded capture script.

The real isolated API was re-exercised during this audit: 350 list items, 350/350 detail parity,
350/350 default-calculator parity, zero private leaks, and zero forbidden serving imports. Those
mechanical checks are clean, but they repeat the same staged artifact and therefore do not disprove
the semantic gaps below.

## What is verified clean

- ✔ The frozen denominator contains exactly WFC, WMB, AON, SCHW, GL, AJG, PNC, RJF, CFG, and JKHY;
  all controlling 10-K/10-Q identities, units, and filing dates are cutoff-safe.
- ✔ G/H contain 21 byte-identical files and the report hashes match. An independent formula written
  for this audit reproduced all 30 stored raw scenarios exactly.
- ✔ WFC, SCHW, PNC, CFG, and RJF use period-specific preferred claims; GL and JKHY have source-proven
  zero preferred claims.
- ✔ PNC's current `$5.879B` preferred-stock-plus-surplus figure matches the cached filing and its
  recorded document/package hashes. Its preferred claim is deducted once from book equity, while
  common-attributable earnings already deduct preferred dividends.
- ✔ AON's `NetIncomeLoss` is already parent-attributable: reported H1 `ProfitLoss $1.804B` less
  `$41M` NCI equals the selected `$1.763B`. The relayed proposal to subtract NCI again was rejected
  because it would double-count the adjustment.
- ✔ WMB's `$35M` preferred claim and `$2.178B` NCI are each deducted once, and its negative raw bear
  residual is retained behind the public limited-liability zero floor.
- ✔ The watchlist contains exactly 234 entries — 224 Conditional and 10 Withheld — including all ten
  Batch 35 issuers. The withheld-register and tracked serving state remain unchanged by Batch 35.

## Reuse check

No new parallel engine is required to repair these gaps. The shared residual-income calculator,
FCFF bridge, immutable receipt pattern, catalog builder, and model-aware calculator lanes already
exist. The missing work is to wire the exact Batch 35 evidence and actual model identities through
those existing paths, then add semantic assertions that prevent default parity from masking a
wrong formula or incomplete bridge.

## Gap register

### P1 — Important, verified

1. **✔ WMB omits `$2.672B` of reported financing claims from the equity bridge.**
   `batch_35_history.py:388` selects only noncurrent `LongTermDebtAndCapitalLeaseObligations`
   (`$28.121B`). The same controlling balance sheet reports `$2.197B` of long-term debt due within
   one year and `$475M` of commercial paper, both as undimensioned issuer facts. The private bridge
   and all three scenarios omit them. Adding the missing claims changes WMB from the reported
   `$0 / $17.71 / $44.06` to approximately **`$0 / $15.52 / $41.84`**; the raw bear moves from
   `-$6.90` to `-$9.05`. This is a material value overstatement and violates the complete-claims
   gate.

2. **✔ AON and AJG map their governed preferred-claim ranges in the wrong economic direction.**
   For an unreported claim, the builder creates an ascending `0% / 1% / 3%` equity range, then maps
   it directly to bear/base/bull at `batch_35_history.py:323-351`. Bear therefore deducts no claim
   while bull deducts the maximum claim. Correct conservative mapping is maximum/base/zero. With
   all other inputs unchanged, AON becomes approximately **`$46.39 / $78.04 / $112.99`** instead of
   `$47.83 / $78.04 / $109.60`; AJG becomes **`$62.38 / $104.22 / $148.38`** instead of
   `$64.31 / $104.22 / $143.93`. The base is unchanged, but both tails understate uncertainty.

3. **✔ Public model identity and calculator behavior do not match the formulas used for all ten
   issuers.** The private results identify nine residual-income models and WMB's resource-cycle
   FCFF. The inherited public builder instead maps every Conditional result to
   `model_policy.primary = conditional_estimate`, stores only a `conditional_estimate` model, and
   says it fell back from FCFF. The API list therefore reports an availability label as the model.
   The nine residual-income calculators expose only an earnings factor/multiple, not ROE, payout,
   cost of equity, and terminal assumptions. WMB's calculator defaults to a 10% discount rate even
   though the private base uses 9.5%; entering the actual 9.5% base assumption raises displayed
   value from `$17.71` to `$18.89`. Default parity passes only because the calculator rescales around
   the stored headline, not because it replays the actual model.

4. **✔ Cutoff-event control is incomplete and sometimes describes an unperformed reconciliation.**
   The event capture script contains only PNC and SCHW definitions. For other issuers,
   `_event_rows()` silently returns an empty list when no receipt exists; there is no ten-company
   scanned/rejected event ledger. JKHY filed an Item 2.02 earnings 8-K on **2026-08-11**
   (`0000779152-26-000052`) before the 2026-08-14 cutoff, yet its valuation still stops at the
   2026-03-31 10-Q. The filing is visible in the captured submissions packet but is absent from the
   event root and private ledger. PNC's `$2.0B` and SCHW's `$2.6B` note issuances are captured, but
   their receipt text says they were “reconciled” and “not added twice” even though the model neither
   updates future interest nor discloses the event publicly. Current JKHY freshness and the two note
   treatments are therefore not cutoff-complete.

5. **✔ Source hashes are recorded but not execution-bound to the valuation build.** All source and
   structural files currently match their receipts, but `build_batch_35_history_result()` reads
   `submissions.json`, `companyfacts.json`, `source-manifest.json`, and `structural-filing.json`
   without reading or verifying the packet/structural receipts. PNC's load-bearing filing table value
   and hashes are hard-coded after only checking the accession; the code never hashes the cited HTML
   or package at runtime. Two deterministic runs prove repeatability on the same local inputs, not
   that those inputs still match the pinned source bytes.

6. **✔ Verification coverage checks parity, not the missing semantic contracts.** The focused tests
   assert ordered ranges, preferred point values, default public/private value parity, and private-key
   absence. They do not assert WMB's complete debt total, adverse claim direction, cutoff-event
   completeness, runtime receipt hashes, or private/public/calculator model identity. The API verifier
   checks that empty overrides reproduce the stored value and performs generic monotonic checks on
   representative issuers; it does not recalculate Batch 35 from the public defaults. This is why
   all tests and 350/350 API parity pass despite findings 1–5.

### P2 — Minor, verified

7. **✔ Audit 130's result table omits the High value column for seven issuers.** SCHW, GL, AJG, PNC,
   RJF, CFG, and JKHY have High values in the JSON, but the Markdown row places the explanation in
   the High column. The missing values are `$45.13`, `$129.36`, `$143.93`, `$211.08`, `$112.13`,
   `$72.02`, and `$59.75`, respectively.

8. **✔ AON/AJG's public warnings do not disclose the actual governed preferred sensitivity.** They
   say preferred carrying value is unavailable, but do not tell the user that private scenarios use
   a 0%/1%/3%-of-equity policy range. The results are already Conditional Low, so this is a
   transparency issue rather than a separate withholding condition.

9. **✔ WMB counts the `$203M` aggregate cash-and-restricted-cash fact as surplus cash without a
   restriction split.** No separate unrestricted-cash fact is reported. The maximum direct effect is
   small relative to the range (about `$0.17` per base share), but the bridge should either prove
   availability or use a bounded cash range.

## Audit disposition

No Critical identity, denominator, nonfinite-value, or public-safety failure was found. The confirmed
Pass/Conditional/Withheld counts and watchlist membership remain recorded, and all ten companies are
still likely recoverable as numeric Conditional baselines. However, Batch 35 is **not promotion-ready**:
six verified Important gaps remain, WMB's value is materially overstated, and JKHY does not use the
latest cutoff-safe operating information.

Repair should preserve all ten companies and the current watchlist while producing a corrected
successor: complete WMB's debt bridge, reverse the AON/AJG claim mapping, bind the actual model to
public/calculator surfaces, complete the ten-company event ledger and JKHY refresh, enforce source
receipts, and add semantic tests before deterministic and live-API replay.

This audit made no valuation, watchlist, withheld-register, serving, merge, push, deployment, or
Batch 36 change. Only this audit record, its index entry, and the pending repair roadmap were added.

Repair update: Audit 132 closes all six Important and three Minor findings. The repaired result
remains Pass 0 / Conditional 10 / Withheld 0 / Numeric 10 and was user-confirmed on 2026-09-04.
