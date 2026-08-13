# Evidence-Aware Bridge and Publication Policy Design

**Date:** 2026-08-13
**Status:** Approved direction; implementation not started

## Decision summary

FinSight will add one evidence-aware normalization and policy layer between extraction and valuation. SEC Companyfacts, governed filing-text evidence, and the planned Arelle structural-XBRL resolver will all produce source-linked field candidates. FinSight—not Arelle—will classify each accepted field's availability, reconcile bridge groups, bound any residual uncertainty, and decide whether an FCFF valuation is usable, review-required, or withheld.

The rollout remains fail-closed. A blank fact never becomes zero by itself, stale facts never become current, conflicts remain blocking, and the first Arelle increment stays shadow-only. Publication may be relaxed only for an evidence-backed zero or not-applicable conclusion, a non-overlapping aggregate that replaces unavailable detail, or a source-supported uncertainty range whose combined low-to-high per-share spread is no more than 1% of its positive midpoint. Unbounded uncertainty remains withheld.

This design extends rather than replaces the existing [Structural XBRL Concept Resolution Design](2026-08-10-structural-xbrl-concept-resolution-design.md).

## Scope decomposition

The complete recommendation spans four dependent increments. Each increment must be independently tested and live-verified before the next one can affect publication:

1. **Structural discovery:** implement the existing Arelle shadow pipeline and deterministic resolver.
2. **Evidence-aware bridge:** add the common availability schema, bridge groups, materiality bounds, and publication decision. This document defines that increment.
3. **Sector-aware operating NWC:** replace the global four-account assumption with governed sector templates and a coverage score. This receives a separate design after bridge behavior is verified.
4. **Presentation:** expose field states, materiality, proxies, and review reasons through the existing API and valuation detail UI. This receives a focused design after the backend response is stable.

Separating these increments prevents a new parser, a valuation-policy change, and a UI change from being validated as one opaque release.

## Alternatives considered

### Patch aliases and relax the required-field tuple

This is the fastest option, but it cannot resolve issuer extensions reliably and would encourage account-by-account exceptions. It also risks treating an extraction miss as an economic zero. Rejected.

### Add a common evidence layer beneath a staged Arelle resolver

This keeps existing sources working, adds structural discovery without granting it immediate publication authority, and centralizes economic policy in FinSight. It is auditable and can be rolled out with corpus-level comparisons. Selected.

### Replace Companyfacts and filing evidence with Arelle

Arelle provides richer XBRL structure but does not decide FinSight's accounting meaning or valuation materiality. A wholesale replacement would discard stable point-in-time and governed-evidence behavior while coupling serving code to a heavy parser. Rejected.

## Pipeline architecture

```text
SEC submissions + Companyfacts + controlling filing package
          |              |                 |
          |              |                 +--> isolated Arelle worker (shadow first)
          |              +----------------------> exact configured concepts
          +-------------------------------------> governed filing evidence
                                                    |
                                                    v
                                      source-linked field candidates
                                                    |
                                                    v
                                  deterministic resolution + conflicts
                                                    |
                                                    v
                                   availability state for every field
                                                    |
                                                    v
                              bridge-group reconciliation + uncertainty
                                                    |
                                                    v
                                FCFF valuation and publication decision
```

Arelle ends at structural candidate production. It does not calculate enterprise value, infer zero, assign materiality, or choose publication state. The application-serving process consumes bounded JSON and must not import Arelle.

## Source precedence and conflict rules

Candidate resolution uses the following order, subject to period, accession, unit, context, and as-of-date hard gates:

1. Current controlling-filing fact using an exact configured standard concept.
2. Current governed filing evidence with explicit locator and evidence class.
3. Current structurally resolved standard or extension fact accepted by the FinSight resolver.
4. A source-supported proxy or bound that is explicitly permitted for the field.

Precedence does not erase disagreement. Two current, equally applicable candidates with materially different values produce `conflict` and block the affected bridge group. A stale candidate is retained for diagnostics but cannot satisfy a current-period requirement. Shadow Arelle candidates are recorded but cannot clear a gate until their evidence class is promoted after corpus review.

## Availability schema

Each normalized field will add an `availability` record while the existing `values`, `sources`, and `field_states` keys remain during compatibility rollout:

```json
{
  "field": "commercial_paper",
  "value": 0,
  "state": "explicit_zero",
  "reason_code": "CURRENT_DEBT_NOTE_REPORTS_NONE_OUTSTANDING",
  "period_end": "2026-06-30",
  "source_accession": "0000000000-26-000001",
  "source_kind": "filing_debt_note",
  "evidence_class": "reported_zero",
  "freshness": "current",
  "mapping_version": "US-FIELD-AVAILABILITY-1.0",
  "uncertainty": null
}
```

Allowed states are:

- `reported` — a current accepted numeric fact.
- `explicit_zero` — the controlling filing reports zero or explicitly states that no balance is outstanding.
- `evidence_backed_zero` — a governed complete-presentation rule supports zero; the rule and source must be retained.
- `not_applicable` — the issuer's current filing structure proves the claim does not apply.
- `proxy` — an allowed substitute is used and its effect is disclosed.
- `bounded_unresolved` — no point value is accepted, but a source-supported lower and upper bound exist.
- `not_disclosed` — the filing does not separately disclose the item and no safe bound exists.
- `unresolved` — extraction or classification could not determine the field.
- `stale` — only an older period or non-controlling accession is available.
- `conflict` — applicable sources disagree.

`not_disclosed`, `unresolved`, `stale`, and `conflict` never become zero through arithmetic defaults. `not_applicable` and either zero state require current evidence, not tag absence.

`explicit_zero`, `evidence_backed_zero`, and `not_applicable` carry a normalized point value of zero only after their evidence rule passes. `bounded_unresolved`, `not_disclosed`, `unresolved`, `stale`, and `conflict` retain a null point value.

## Bridge policy

The bridge will be evaluated as economic groups rather than ten equally mandatory tags.

### Hard requirements

- Current cash or a governed cash classification bridge.
- Current common-share denominator, with the existing weighted-average diluted fallback retained as a visible proxy.
- A non-overlapping total interest-bearing debt exposure.
- Any preferred-equity or noncontrolling-interest claim that the filing reports as present.

Core revenue, operating-income, tax, capex, depreciation, and working-capital requirements remain model-input gates outside this bridge policy.

### Conditional components

- Current and noncurrent marketable securities.
- Commercial paper.
- Current and noncurrent debt detail.
- Current and noncurrent finance-lease detail.
- Preferred equity.
- Noncontrolling interests.

These fields may be satisfied by a current reported value, a governed zero or not-applicable conclusion, or a non-overlapping aggregate. Missing detail is not itself blocking when the economic group is fully resolved. For example, an aggregate finance-lease liability can replace an unavailable current/noncurrent split. A total-debt aggregate can replace detail only when the resolver proves that adding available components would double count.

### Bridge outputs

The normalized balance sheet will retain `bridge_complete` with its strict meaning: every economically relevant claim is resolved to a point value. It will add:

- `bridge_usable`: whether the valuation may proceed.
- `bridge_decision`: `complete`, `bounded_review`, or `withheld`.
- `bridge_blocking_fields`: unbounded, stale, or conflicting model-critical fields.
- `bridge_bounded_fields`: fields carried as source-supported ranges.
- `bridge_uncertainty`: aggregate low/high bridge values and per-share impact.

`bridge_usable` is true only for `complete` and `bounded_review`; it is false for `withheld`. The existing `bridge_missing_fields` remains the list of fields without a point resolution, including bounded fields, while the new blocking and bounded lists explain whether each missing point prevents use. The pipeline will gate on `bridge_usable`, not redefine `bridge_complete`. This preserves existing semantics and makes bounded review explicit.

## Materiality and publication policy

For one or more `bounded_unresolved` fields, FinSight will apply each account's bridge direction—cash and eligible nonoperating investments increase equity value; debt, preferred equity, and NCI decrease it—and calculate the joint worst-case low and high intrinsic values per share. The midpoint is `(low + high) / 2`. The bridge is eligible for `bounded_review` only when all of the following hold:

- both bounds come from current, traceable filing evidence or a governed deterministic rule;
- the bounds are finite, non-negative where the account requires it, and do not overlap another accepted component;
- the midpoint intrinsic value per share is positive;
- `(high - low) / midpoint` is no more than 1%; and
- no field in the same bridge group is stale or conflicting.

If any condition fails, `bridge_usable` is false and publication remains `withheld`. A bounded bridge can produce at most `review_required`; it can never produce `pass`. Existing downstream safety checks may still withhold it for another reason.

No publication rule will use a fixed zero solely to make a model run. Arithmetic may use a temporary endpoint while calculating a bound, but the emitted field value remains null and the endpoint is stored under `uncertainty`.

## Initial account policies

- **Cash:** hard current requirement.
- **Debt:** hard requirement at the non-overlapping aggregate level; exact split tags are not mandatory when the aggregate is proven complete.
- **Commercial paper:** reported amount or current evidence-backed zero; otherwise unresolved unless included in a proven debt aggregate.
- **Marketable securities:** reported amount, current evidence-backed zero/not-applicable, or a source-supported bound; prevent double counting with cash equivalents and strategic investments.
- **Finance leases:** use a reported aggregate when split fields are unavailable; no blank-to-zero inference.
- **Preferred equity:** require the amount when present; accept zero/not-applicable only with current equity-presentation evidence.
- **NCI:** require the amount when present; majority-owned subsidiaries prevent a no-NCI inference unless the current statements resolve the claim.
- **Dilution:** retain the existing denominator proxy warning; add per-share sensitivity in the later presentation increment.

## Error handling

- Arelle unavailable, timed out, or malformed: retain current Companyfacts and filing-evidence behavior and emit a shadow diagnostic.
- Wrong period, accession, unit, or context: reject the candidate.
- Stale governed evidence: record `stale`; do not clear a gate.
- Current source conflict: record `conflict`; withhold the affected model.
- No defensible upper bound: record `unresolved` or `not_disclosed`; withhold.
- Double-count risk in an aggregate/component mix: reject the aggregate reconciliation and withhold.
- New policy-engine exception: fail closed and preserve public-value scrubbing.

No error path may turn an unavailable fact into zero or expose a withheld intrinsic value publicly.

## Rollout

1. Implement and test the existing Arelle parser/resolver plan in shadow mode.
2. Add the availability schema and bridge-policy evaluator while preserving current publication outcomes.
3. Replay the current artifact universe and emit comparison diagnostics: old blockers, new states, proposed bridge decisions, and value ranges.
4. Manually reconcile representative difficult and control issuers to their controlling filings. The first corpus includes AMZN, CAT, RCL, PEP, WMT, AAPL, MSFT, ANET, CRM, and WDC.
5. Promote only reviewed evidence classes. Enable `bounded_review` without enabling automatic `pass`.
6. Design and implement sector-aware operating NWC.
7. Expose stable states and reasons through the API and valuation detail UI.

## Testing and verification

Implementation follows test-driven development. Focused tests must first fail for the missing behavior, then pass with minimal production changes.

Required automated coverage includes:

- every availability state and invalid transition;
- current versus stale/accession-mismatched evidence;
- explicit zero versus absent tag;
- aggregate finance leases replacing, but not double-counting, split values;
- aggregate debt reconciliation and overlap rejection;
- finite 1% materiality boundary, just-below and just-above cases;
- conflicts overriding source precedence;
- Arelle shadow candidates unable to clear publication gates;
- bounded bridge producing at most `review_required`;
- unbounded bridge remaining withheld and publicly scrubbed;
- regression coverage for existing governed filing facts and verified zeros.

GoodBehavior live verification requires more than green tests. The real pipeline will be rerun on the representative issuer corpus. Evidence must include field-state diffs, bridge arithmetic reconciliation, per-share low/high calculations, source accession checks, publication-state changes, and confirmation that withheld public artifacts remain scrubbed. The change remains “verified—user confirmation needed” until the user reviews those results.

## Success criteria

- The serving process does not import Arelle.
- Existing exact standard concepts retain their values and provenance.
- Every bridge field exposes a deterministic state, reason, source, period, and mapping version.
- No missing or stale fact is silently converted to zero.
- Aggregate debt or lease facts can safely replace unavailable detail without double counting.
- Unbounded, stale, or conflicting model-critical uncertainty remains withheld.
- Combined bounded uncertainty at or below 1% can produce only `review_required` and emits its range for later presentation.
- Corpus replay reports every changed publication decision and its evidence.
- Existing public scrubbing and point-in-time controls do not regress.

## Deferred to separate designs

- Exact sector-specific operating-NWC account templates and materiality rules.
- Frontend layout and copy for field states and uncertainty ranges.
- Automatic promotion of Arelle extension mappings beyond shadow mode.
- IFRS/20-F extraction and normalization.
