# Batch 01 practical bounded-uncertainty policy audit

**Audited:** 2026-08-20 (Asia/Manila)

**Reference:** user-approved practical transparent valuation policy for controlled Batch 01

**Strict baseline:** `docs/audit/10-controlled-batch-01-result.md`

**Status:** audit complete; implemented and independently challenged in
`docs/audit/12-practical-batch-01-result.md`

## Reference

The new rule is to use an economically suitable practical model when trustworthy uncertainty
can be bounded. Missing advanced detail should widen low/base/high and cap reliability—normally
at Low—rather than automatically erase a value. Withholding remains mandatory for identity,
source, period, unit, currency, share, evidence-conflict, unsupported-model, unbounded-claims,
major-event, nonfinite/nonpositive, or public-safety failures.

The public comparison target is limited to transparent practices. AlphaSpread publicly says it
chooses operating models from company characteristics and forecasts free cash flow from company
history and other inputs. GuruFocus publicly describes two-stage DCF, historical fallback
horizons, growth constraints, and predictability warnings. Neither proprietary formula is part
of this policy.

## Ours today

- ✔ The real strict Batch 01 path is deterministic and public-safe but returns 0 numeric and
  10 withheld.
- ✔ `economic_routing.py` requires every `hypothesis` route to have a `Withhold` cap and rejects
  selected experimental models. This correctly protects immature lanes but cannot represent a
  separately governed practical fallback.
- ✔ `run_batch_01_controlled.py` unconditionally calls `_force_withheld_public()` for every
  issuer, even when the existing model produced a finite source-linked diagnostic range.
- ✔ Existing shared code already supports consolidated FCFF fallback, scenario/reliability
  grading, annual/company-history uncertainty ranges, point-in-time specialist facts, exact
  structural promotion, R&D capitalization mechanics, cycle normalization, bank common-equity
  mechanics, SOTP reconciliation, AFFO, and NAV arithmetic.
- ✔ The public reliability allowlist does not yet include the eight requested practical-policy
  reason codes.
- ✔ Current strict diagnostic ranges are finite for MSFT, CRM, JPM, BAC, NEE, and O. AAPL and
  ANET remain bridge-blocked. WDC and DELL remain both model/evidence-blocked.

## Reuse check

The practical policy should compose the existing FCFF, residual-income, DDM/FCFE support,
FFO/AFFO/NAV, bridge-range, scenario, reliability, artifact sanitizer, batch runner, and API
data-root override. The missing shared layer is a governed contract that distinguishes bounded
model uncertainty from genuinely unbounded uncertainty and feeds explicit low/base/high ranges
into those existing engines.

## Real flow and where strict behavior blocks it

`frozen packet -> normalized TTM/history -> economic route -> bounded input policy -> practical model -> low/base/high -> Low cap/reasons -> private trace -> public sanitizer -> staged API`

Today, the flow reaches a finite diagnostic for six issuers but is then forcibly changed to
withheld because the route remains a hypothesis. For AAPL and ANET, the bridge gate stops before
model generation even though the missing claims may be conservatively bounded. WDC and DELL
still lack proof that their load-bearing uncertainty is finite.

## Blocker classification

| Ticker | Bounded but previously mandatory | Model/extraction work | Materially unbounded today | Practical audit disposition |
| --- | --- | --- | --- | --- |
| AAPL | Segment separation; non-operating-claim range | R&D sensitivity; preferred/NCI range | None proven yet | Candidate consolidated FCFF, Low |
| MSFT | Exact R&D life; exact AI-capex forecast | R&D/capex/cash-conversion sensitivity | None proven | Candidate consolidated FCFF, Low |
| CRM | Segment detail; SBC/debt treatment range | Software/SBC sensitivities; debt classification | None proven | Candidate consolidated FCFF, Low |
| ANET | Perfect debt/lease/investment detail | Aggregate bridge ranges; growth fade | None proven yet | Candidate growth FCFF, Low |
| WDC | — | Cycle preprocessor; bridge extraction | Complete post-change cycle range | Withhold unless finite cycle bound is proven |
| DELL | — | Captive-finance SOTP or anti-double-counted FCFE | DFS equity/funding/claim allocation | Withhold unless separation is bounded |
| JPM | Exact capital refinements | Average common equity; capital sensitivity | None proven | Candidate provisional residual income, Low |
| BAC | Exact capital/preferred refinements | Preferred/common equity; capital sensitivity | None proven | Candidate provisional residual income, Low |
| NEE | Full FPL/NEER separation | Consolidated FCFE/mixed-business range | None proven | Candidate consolidated FCFE, Low |
| O | Exact maintenance capex/property detail | AFFO and cap-rate/NAV ranges | None proven | Candidate AFFO/NAV, Low |

These were implementation candidates at audit time. The final dispositions, corrected formulas,
source coverage, monotonic sensitivity checks, and independent challenge are recorded in
`docs/audit/12-practical-batch-01-result.md`.

## Gaps

- **PB-01 · P0 ✔ — Unconditional withholding.** The batch runner cannot emit a practical numeric
  result regardless of finite evidence.
- **PB-02 · P0 ✔ — No bounded-model decision contract.** Routing distinguishes experimental,
  provisional, and validated, but has no separate practical-fallback decision with explicit
  bounds, cap, and reasons.
- **PB-03 · P0 ✔ — Requested reason codes are absent.** The private/public reliability contract
  cannot carry consolidated, R&D, capex, cycle, bank-capital, utility, AFFO, or specialist-model
  uncertainty reasons end to end.
- **PB-04 · P0 ✔ — Advanced-detail sensitivity is not wired into valuation ranges.** Existing
  adapters calculate mechanics but do not feed current Batch 01 low/base/high outputs.
- **PB-05 · P0 ✔ — AAPL/ANET bridge gaps remain point-gated.** No practical, source-backed claim
  range is supplied to the existing bounded bridge policy.
- **PB-06 · P0 ✔ — Bank range is still single-period.** Current residual-income diagnostics do
  not include average common equity or regulatory-capital uncertainty.
- **PB-07 · P0 ✔ — NEE relies on DDM only.** The practical policy requires mixed-business SOTP or
  a transparently bounded consolidated FCFE fallback.
- **PB-08 · P0 ✔ — O relies on interim FFO multiple only.** AFFO and property NAV sensitivities
  are not connected to a finite range.
- **PB-09 · P0 ✔ — Strict/practical comparison runner is missing.** The current runner records a
  strict diagnostic but has no governed practical policy mode or change explanation.
- **PB-10 · P0 ✔ — Newly numeric challenge receipt is missing.** No independent source/arithmetic/
  suitability/uncertainty review exists for the practical outputs.
- **PB-11 · P1 ✔ — Browser verification remains environment-blocked.** Frontend dependencies and
  an authenticated local user are absent; real API verification remains available.
