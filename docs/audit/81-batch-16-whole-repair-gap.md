# Batch 16 Whole-Batch Repair Gap

Status: **firsthand audit complete; whole-batch repair explicitly authorized by the user**. Scope is
exactly A, DXCM, EW, CRL, ZBH, COR, PODD, ELV, VEEV, and IQV. This is an exceptional second review,
not a reset of the one automatic withheld-company recovery rule. It does not authorize Batch 17,
tracked serving promotion, merge, push, or deployment.

## Reference behavior

The user's product intent is a useful baseline decision aid: use reported financial history and
known claims, make conservative scenario assumptions, disclose what the range excludes, and reserve
Withheld for cases where even the operating/equity baseline itself is not coherent. A missing legal
loss estimate must not silently become zero, but it also need not erase an otherwise source-bounded
going-concern valuation when the public result is explicitly Conditional and Low reliability.

The existing stricter result is recorded in [Audit 80](80-batch-16-recovery-result.md). It withheld
six companies because the complete legal claim sets were not bounded.

## Ours today

- ✔ Exact denominator remains ten, with Pass 2 / Conditional 2 / Withheld 6.
- ✔ A, PODD, VEEV, and IQV already have finite source-linked history models.
- ✔ The existing code contains a complete finite EW faded-FCFF route and a complete finite ELV
  managed-care residual-income route, but the hard-coded withheld branch makes both unreachable.
- ✔ Firsthand replay of those dormant routes produced finite ordered ranges:
  - EW: $22.72 / $42.40 / $58.05
  - ELV: $121.67 / $231.20 / $419.52
- ✔ Current source/history inputs support finite operating calculations for DXCM, CRL, and COR;
  trial calculations produced ordered positive ranges before implementation and challenge.
- ✔ ZBH has complete revenue, OCF, capex, tax, and `InterestIncomeExpenseNet` history. The shared
  alias set includes `InterestIncomeExpenseNonoperatingNet` but omits the issuer's reported
  `InterestIncomeExpenseNet`, leaving its ordinary history route unwired.
- ✔ PODD's current filing records the Hu action with a zero accrual because loss is not probable.
  Existing private evidence correctly says zero is a reported accrual, not an estimated zero loss.
- ⚠ Independent High/xhigh reviewers recommend retaining the six withholds under the old total-
  claims release rule. That is a valid safety lens but conflicts with the user's baseline-first
  product instruction and is therefore a challenge input, not the repair target.

## Reuse check

Reuse the existing Batch 16 sources, structural wrappers, history builder, faded-cash DCF,
managed-care residual-income function, public sanitizer, catalog builder, and API verifier. Add one
small shared legal-tail treatment rather than inventing lawsuit values or building six bespoke legal
models.

## Gap register

| ID | Severity | Finding | Evidence | Repair target |
| --- | --- | --- | --- | --- |
| B16W-01 | P0 | Hard-coded total-claims gating suppresses coherent going-concern baselines | ✔ Batch 16 history code plus dormant EW/ELV replay | Permit a Conditional Low operating/equity baseline using only recorded claims; label unquantified legal tail outside the range |
| B16W-02 | P0 | DXCM, CRL, and COR have usable source/history/bridge inputs but no reachable practical policy | ✔ cached SEC and structural packages; firsthand trial arithmetic | Add transparent history-backed policies and include recorded debt/NCI/claims once |
| B16W-03 | P0 | ZBH interest history uses an omitted standard concept candidate; adding it globally changes precedence for previously verified issuers | ✔ Companyfacts, `concept_aliases.json`, and full-suite YUM/SYY regression proof | Add `InterestIncomeExpenseNet` only to the ZBH repair normalizer, then verify current history without changing global selection |
| B16W-04 | P1 | PODD remains Conditional solely because a new monetary claim lacks a range despite a reported not-probable zero accrual | ✔ controlling filing evidence ledger | Upgrade to Pass while keeping Low reliability and an explicit no-zero-substitution warning |
| B16W-05 | P0 | Whole-batch successor, deterministic replay, independent challenge, full suite, and real API are absent | ✔ repository/output inventory | Stage all ten immutably, challenge, replay twice, and exercise the cumulative 160-company API |
| B16W-06 | P0 | Existing recovery/watchlist history must remain auditable after an exceptional revisit | ✔ append-only register contracts | Record superseding repair status without erasing the consumed attempt or prior Audit 80 evidence |

## Governing repair rule

For an unquantified current legal tail, a numeric baseline may be published only when issuer,
period, currency, shares, operating history, and the chosen model are source coherent; all recorded
claims used by the model are included exactly once; and the result remains finite with a positive
base. The unknown legal amount remains `None` privately and is never replaced by zero or a guessed
haircut. Publicly, the result is Conditional/Low and says the range values reported operations and
recorded claims only; an adverse unquantified legal outcome can move actual value outside it.

Continue withholding for wrong identity/period/unit, unusable shares, contradictory bridge facts,
nonfinite/nonpositive base, going-concern failure, or an event that makes the operating object itself
undefined. This repair does not claim the scenario range is a legal-loss bound.
