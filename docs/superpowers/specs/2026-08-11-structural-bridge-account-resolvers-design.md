# Structural Bridge Account Resolvers Design

**Date:** 2026-08-11
**Status:** Approved for implementation planning
**Parent design:** `2026-08-10-structural-xbrl-concept-resolution-design.md`

## Decision summary

FinSight will keep Arelle as the filing-level XBRL parser and generalize the existing marketable-securities resolver into a shared, policy-driven structural resolver. The shared engine will retain its existing hard gates, ambiguity handling, provenance, and fail-closed behavior. Metric-specific policy will be added for current debt, noncurrent debt, commercial-paper borrowing, finance-lease liabilities, preferred or temporary equity carrying amount, and noncontrolling interests.

The new account policies will run in shadow mode. They may recover evidence and produce governed decisions, but they will not silently alter production valuation inputs or clear publication gates during this phase.

## Problem

The existing structural records and most resolver mechanics are metric-neutral, but candidate classification is still specialized for current and noncurrent marketable securities. In particular:

- standard-concept classification checks only the two marketable-securities fields;
- current/noncurrent orientation is inferred from a marketable-specific naming convention;
- extension admission relies on securities and investment language;
- exclusions are global even when they are valid only for marketable securities; and
- the shadow runner requests only the two marketable-securities fields.

Simply adding more aliases would therefore create false positives or false negatives. CRM demonstrates the central risk: its filing reports $94 million of commercial paper inside an investment table. That is an asset security, not commercial-paper borrowing. A literal tag or label match cannot safely normalize it into FinSight's debt bridge.

## Goals

- Resolve bridge accounts using deterministic XBRL and accounting context.
- Reuse the existing fact, request, evidence, and decision records.
- Preserve exact source concept, filing, period, unit, dimensions, relationships, decision, confidence, and reason codes.
- Apply account-specific statement orientation, structural relationships, exclusions, dimensional policy, and zero policy.
- Distinguish carrying values from maturity payments, liquidation preferences, share counts, and other look-alike disclosures.
- Keep weak, incomplete, or contradictory evidence unresolved.
- Verify the policies against ANET, CRM, DELL, FTNT, and WDC before expanding the corpus.

## Non-goals

- This phase will not replace Arelle, SEC Companyfacts, or the existing filing cache.
- It will not use an LLM or semantic similarity as an automatic accounting classifier.
- It will not infer zero solely from an omitted line item.
- It will not derive current and noncurrent lease carrying values from a payment schedule.
- It will not automatically publish recovered values.
- It will not make all five pilot companies valuation-ready when required evidence remains absent.

## Alternatives considered

### Add aliases only

This is the smallest code change but is unsafe. It cannot distinguish CRM's investment commercial paper from borrowing, cannot govern custom extensions, and inherits marketable-specific orientation and exclusions.

### Build one resolver module per account

This isolates accounting policy but duplicates period, unit, role, dimension, ambiguity, evidence, and provenance logic. The duplicated mechanics would drift and increase maintenance cost.

### Shared resolver with metric-specific policies

This is the selected approach. It preserves the tested common engine while moving economic classification into explicit policy entries. It is the smallest change that addresses the actual failure mode without making the resolver fuzzy.

## Architecture

```text
Arelle filing package
        |
        v
Normalized structural facts
        |
        v
Shared hard gates and deduplication
        |
        v
Metric-specific accounting policy
  - aliases
  - statement orientation
  - structural parents
  - dimensional rules
  - exclusions
  - total/component semantics
  - zero policy
        |
        v
Accepted / review / rejected decision + evidence
        |
        v
Shadow artifact only
```

The existing structural record model remains authoritative. The resolver configuration becomes the policy boundary; it must contain only declarative accounting evidence and thresholds, while reusable mechanics remain in code.

## Shared resolver behavior

Every candidate must pass the existing filing, accession, form, period, unit, and numeric-value gates. Additional shared behavior will be generalized as follows:

1. Resolve known standard aliases for the requested metric rather than a hard-coded marketable pair.
2. Read orientation explicitly from policy: `current`, `noncurrent`, or `none`.
3. Read extension-admission terms and exclusions from the requested metric's policy.
4. Require a compatible statement role or recognized structural relationship.
5. Reject dimensional facts by default; allow them only when a metric policy explicitly identifies permitted axes or members.
6. Preserve duplicate collapse, component-versus-total conflict handling, and equal-support ambiguity checks.
7. Produce stable reason codes for both accepted and rejected decisions.

Exact aliases do not bypass accounting context. An exact concept in the wrong statement, role, dimension, or economic class must be rejected.

## Zero policy

A zero may be accepted only when one of these conditions holds:

- a direct, current-period target account fact reports zero or a filing dash normalized to zero; or
- a metric-specific policy explicitly permits a current-period disclosure that establishes zero, with the evidence marked separately from a direct structural fact.

Absence of a line item is not zero. A complete-statement absence inference, narrative ownership statement, or similar policy evidence may be preserved as review evidence, but it will not be structurally auto-accepted in this phase.

No unrelated zero, historical zero, share count, or component zero may establish a target account zero.

## Account policies

### Current debt

Accept a direct current borrowing or current-maturity carrying amount in current liabilities. Standard concepts include governed aliases such as `DebtCurrent` and `LongTermDebtCurrent`. Reject debt cash flows, maturity schedules, instrument fair values, asset securities, and subtype-only facts when they do not establish total current debt.

### Noncurrent debt

Accept a direct noncurrent carrying amount under noncurrent liabilities. Prefer `LongTermDebtNoncurrent` over an unqualified total when both are present. Reject maturity schedules, face amounts, fair values, and instrument-level facts that do not establish the consolidated noncurrent balance.

### Commercial-paper borrowing

Accept commercial paper only when liability or debt structure establishes borrowing. Reject commercial paper presented within marketable securities, investments, current assets, or fair-value asset disclosures. Ambiguous captions remain unresolved; they do not become zero.

### Finance-lease current and noncurrent liabilities

Accept only direct carrying-value facts with the required current or noncurrent liability orientation. Payment schedules, next-twelve-month payments, and thereafter payments are review context, not substitutes for carrying-value splits. Operating-lease facts are rejected.

### Finance-lease total

Accept a direct `FinanceLeaseLiability` carrying-value or present-value total. Where a maturity table reports gross payments and imputed interest, the resolver may accept the separately tagged net liability total but must not substitute undiscounted payments. It must preserve the relationship evidence explaining the distinction.

### Preferred or temporary equity

Normalize carrying amount, not liquidation preference, dividends, share count, or conversion value. Direct preferred-stock value and temporary-equity carrying-amount concepts may qualify. The mapping output must record whether the source was permanent preferred equity or temporary/mezzanine equity so downstream policy can distinguish them if needed.

### Noncontrolling interests

Accept a direct NCI amount. A period-end equity-rollforward fact may qualify when it is explicitly dimensioned to the governed noncontrolling-interest member and the policy permits that dimension. Reject income-statement NCI concepts, total equity merely described as including NCI, and parent-only equity. Narrative 100% ownership evidence remains review-only in this structural phase.

## Five-company acceptance baseline

The real filing pilot establishes the following expected safe outcomes in USD millions:

| Metric | Accepted baseline | Must remain unresolved or rejected |
|---|---|---|
| Current debt | DELL 7,550; FTNT 0; WDC 1,581 | ANET absence inference; CRM subtype-only zeros |
| Noncurrent debt | CRM 39,280; DELL 23,611; FTNT 496.9; WDC 0 | ANET absence inference |
| Commercial-paper borrowing | None | CRM investment commercial paper of 94; CRM must not be converted to borrowing or zero |
| Finance-lease current | None | CRM payment schedule; all five lack a qualifying split |
| Finance-lease noncurrent | None | CRM maturity components; all five lack a qualifying split |
| Finance-lease total | CRM 664 | CRM undiscounted payments of 718; other companies without a direct total |
| Preferred/temporary equity | ANET 0; WDC 0 carrying amount | DELL's zero share counts are not a USD carrying-value fact; WDC liquidation preference of 265; CRM and FTNT without qualifying facts |
| NCI | DELL 0 from the governed NCI dimension | FTNT narrative policy-zero and companies without direct NCI evidence |

This table is a regression oracle, not a value-selection input. The resolver may not search for or rank candidates based on expected values.

## Shadow integration

The shadow runner will be generalized from its marketable-only allowlist to an explicit set of supported structural fields. Unsupported gaps continue to be skipped with a reason. Supported requests run through the same point-in-time and source controls as the marketable-securities path.

The rollout mode remains `none_shadow_only`: decisions are captured in diagnostic artifacts and compared with governed evidence, but production serving data is unchanged.

## Testing strategy

Implementation will follow test-driven development.

Unit and integration tests will cover:

- each direct standard-alias acceptance baseline;
- wrong-orientation and wrong-statement rejection;
- CRM investment commercial paper rejection;
- lease carrying value versus undiscounted payment distinction;
- current/noncurrent lease payment components remaining unresolved;
- preferred carrying amount versus liquidation preference, dividends, shares, and conversion values;
- governed NCI member dimension acceptance and other dimensions rejection;
- direct zero acceptance and absence-based zero rejection;
- duplicate facts, total/component conflicts, and equal-support ambiguity;
- existing marketable-securities behavior without regression;
- shadow-request selection for every supported account;
- Arelle absence or parser failure preserving existing behavior.

Tests must be hermetic. Real filing verification will separately rerun the cached ANET, CRM, DELL, FTNT, and WDC packages and compare decisions with the baseline above.

## Verification and rollout gates

1. Observe each new test fail for the intended reason before implementation.
2. Pass focused resolver and shadow tests.
3. Pass the existing structural XBRL regression suite.
4. Rerun the five cached real filing packages.
5. Confirm every accepted, review, and rejected decision has source and reason evidence.
6. Investigate all deviations from the acceptance baseline.
7. Record GoodBehavior runtime evidence and unresolved cases.
8. Keep production publication disabled until a broader reviewed corpus supports enabling it.

## Success criteria

- The resolver is metric-driven rather than marketable-securities-specific.
- CRM's asset commercial paper cannot enter the debt bridge.
- Direct debt and carrying-value facts in the five-company baseline resolve deterministically.
- Lease payment schedules do not masquerade as current or noncurrent carrying values.
- Preferred-equity and NCI look-alikes are rejected or held for review.
- No omitted account is silently converted to zero.
- Existing marketable-securities results and structural tests do not regress.
- Production valuation inputs remain unchanged during the shadow phase.
