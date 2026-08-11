# Structural Bridge Account Resolvers Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generalize FinSight's structural XBRL resolver and recover governed debt, lease, preferred/temporary-equity, commercial-paper, and NCI bridge evidence without changing production valuation inputs.

**Architecture:** Keep Arelle and the normalized structural-fact boundary unchanged. Convert the marketable-specific resolver into a shared engine driven by explicit per-metric accounting policies, then expose the new metrics through the existing shadow runner. Exact aliases remain subject to period, unit, statement, dimensional, economic-class, and total/component gates.

**Tech Stack:** Python 3.11, Arelle `2.44.0`, frozen dataclasses, JSON policy configuration, pytest 8.3.4, existing SEC cache and shadow CLI.

## Global Constraints

- Arelle remains the XBRL parser; do not add or replace parser dependencies.
- No LLM or semantic similarity may approve a mapping or supply a financial value.
- Existing SEC retrieval, controlling-filing, point-in-time, provenance, and fail-closed gates remain authoritative.
- Exact aliases do not bypass accounting context.
- Absence of a line item is not zero.
- Direct zero facts must satisfy the same account, period, unit, statement, context, and economic-class gates as nonzero facts.
- Lease payment schedules may not substitute for current or noncurrent carrying-value splits.
- Preferred-equity carrying amount may not be inferred from liquidation preference, dividends, conversion value, or share count.
- Commercial paper presented as an investment asset may not enter the debt bridge or establish borrowing of zero.
- The rollout remains `none_shadow_only`; no task may mutate production valuation artifacts or clear publication gates.
- Tests are hermetic; real SEC filings are exercised separately from the test suite.
- Preserve the untracked `output/` pilot cache and never stage it.
- Every implementation task follows red-green-refactor and ends with an independently reviewable commit.

---

## File Structure

- Modify `backend/app/us_valuation/structural_xbrl.py`: bump the mapping version and allow complete evidence to use a recognized structural statement link when Arelle cannot classify a statement role.
- Modify `backend/app/us_valuation/concept_resolver.py`: shared policy helpers, metric-driven aliases/orientation/exclusions, statement support, dimensional policy, component/review handling, and deterministic reason codes.
- Modify `backend/app/us_valuation/config/structural_concept_rules.json`: per-metric accounting policies.
- Modify `backend/app/us_valuation/config/concept_aliases.json`: add governed temporary-equity carrying-amount aliases; do not add total-equity-with-NCI as an unconditional alias.
- Modify `backend/app/us_valuation/structural_shadow.py`: shared supported-field set and generalized request/report selection.
- Modify `scripts/run_structural_xbrl_shadow.py`: generalized eligibility and parser-failure reporting.
- Modify `backend/tests/test_structural_xbrl_schema.py`: structural statement-support evidence validation.
- Modify `backend/tests/test_concept_resolver.py`: focused policy and accounting regressions.
- Modify `backend/tests/test_structural_shadow.py`: supported-field and CLI behavior.
- Modify `backend/tests/test_structural_xbrl_integration.py` and its local fixtures: hermetic Arelle-to-debt-resolution coverage.
- Create `docs/plans/EVIDENCE.md`: GoodBehavior runtime evidence for the five real filings.
- Update `docs/superpowers/handoffs/2026-08-10-structural-xbrl-resolution-handoff.md`: durable continuation state and remaining uncertainty.

---

### Task 1: Generalize the resolver contract without changing marketable-securities behavior

**Model:** Luna High, because this changes the common accounting gate used by every structural metric.

**Files:**
- Modify: `backend/app/us_valuation/structural_xbrl.py:405-490`
- Modify: `backend/app/us_valuation/concept_resolver.py:1-331`
- Modify: `backend/app/us_valuation/config/structural_concept_rules.json`
- Test: `backend/tests/test_structural_xbrl_schema.py`
- Test: `backend/tests/test_concept_resolver.py`

**Interfaces:**
- Retains: `resolve_concept(request: ResolutionRequest, facts: Iterable[StructuralFact]) -> ResolutionDecision`.
- Produces: policy helpers that read `orientation`, `statement_support_parents`, `direct_statement_parents`, `structural_parents`, `extension_terms`, `required_definition_phrases`, `excluded_economic_phrases`, `component_only_concepts`, `review_only_phrases`, `direct_statement_concepts`, `concept_reason_codes`, `allowed_dimensions`, and `contextual_concepts`.
- Produces mapping version: `US-XBRL-RESOLVER-1.1` in schema defaults, resolver output, and policy version.
- Consumers: Tasks 2-5.

- [ ] **Step 1: Read the required TDD test-quality reference before editing tests**

Read completely:

```text
/Users/carlosconda/.codex/plugins/cache/openai-curated-remote/superpowers/6.2.0/skills/test-driven-development/writing-good-tests.md
```

- [ ] **Step 2: Write failing schema and policy tests**

Add a schema test proving an accepted fact with no classified `statement_roles` remains complete when it has a presentation parent and relationship:

```python
def test_evidence_accepts_structural_statement_support_without_classified_role() -> None:
    fact = _fact(
        statement_roles=(),
        presentation_parents=("us-gaap:DebtInstrumentLineItems",),
    )
    evidence = ResolutionEvidence.from_fact(
        fact,
        mapping_version="US-XBRL-RESOLVER-1.1",
        confidence=1.0,
        reason_codes=("EXACT_CONFIGURED_CONCEPT", "STRUCTURAL_STATEMENT_SUPPORT"),
    )
    evidence.validate_complete()
```

Add the inverse test: empty roles, empty presentation/calculation parents and ancestry, and no relationships raises `ValueError("accepted/review decisions require complete evidence")`.

In `test_concept_resolver.py`, add this general request helper for all subsequent tasks:

```python
def metric_request(metric: str, **overrides: object) -> ResolutionRequest:
    values: dict[str, object] = {
        "normalized_concept": metric,
        "period_end": PERIOD,
        "source_accession": ACCESSION,
        "unit": "USD",
        "statement_role": "balance_sheet",
        "form": "10-K",
    }
    values.update(overrides)
    return ResolutionRequest(**values)  # type: ignore[arg-type]


def account_fact(qname: str, **overrides: object) -> StructuralFact:
    local_name = qname.split(":", 1)[-1]
    values: dict[str, object] = {
        "qname": qname,
        "local_name": local_name,
        "labels": (("standard", local_name),),
        "documentation": local_name,
        "presentation_ancestry": tuple(overrides.get("presentation_parents", ())),
    }
    values.update(overrides)
    return make_fact(**values)
```

Update the rules test to assert every metric policy contains an explicit `orientation`, metric-local exclusions, and a unique supported policy version. Add a regression proving the existing marketable extension still resolves to the same value, method, confidence, and reason class after policy migration.

- [ ] **Step 3: Run the focused tests and observe the intended failures**

Run:

```bash
cd backend && python -m pytest -q tests/test_structural_xbrl_schema.py tests/test_concept_resolver.py
```

Expected: failures show the old `1.0` mapping version, marketable-only orientation/extension logic, and role-only evidence validation.

- [ ] **Step 4: Migrate marketable rules into the common policy shape**

Each marketable policy must use this concrete shape:

```json
{
  "statement_role": "balance_sheet",
  "unit": "USD",
  "orientation": "current",
  "statement_support_parents": [
    "us-gaap:AssetsCurrent",
    "us-gaap:AssetsCurrentAbstract"
  ],
  "direct_statement_parents": [
    "us-gaap:AssetsCurrent",
    "us-gaap:AssetsCurrentAbstract"
  ],
  "structural_parents": [
    "us-gaap:AssetsCurrent",
    "us-gaap:AssetsCurrentAbstract",
    "us-gaap:ShortTermInvestments",
    "us-gaap:MarketableSecuritiesCurrent"
  ],
  "extension_terms": [
    "marketable securities",
    "short term investments",
    "available for sale",
    "debt securities"
  ],
  "required_definition_phrases": [
    "available for sale",
    "debt securities",
    "marketable securities",
    "short term investments"
  ],
  "excluded_economic_phrases": [
    "strategic",
    "equity method",
    "restricted",
    "trust",
    "collateral",
    "receivable",
    "trading assets"
  ],
  "component_only_concepts": [],
  "review_only_phrases": [],
  "direct_statement_concepts": [],
  "concept_reason_codes": {},
  "allowed_dimensions": {},
  "contextual_concepts": []
}
```

Use `orientation: "noncurrent"` and noncurrent asset parents for `marketable_securities_noncurrent`. Remove the root-level marketable exclusion list so exclusions cannot leak into unrelated metrics.

- [ ] **Step 5: Implement metric-driven shared helpers**

Replace the hard-coded marketable pair and suffix inference with policy accessors. `_fact_text` must include concept, labels, documentation, dimensions, presentation parents, calculation parents, and ancestry so accounting context is searchable.

Use these signatures:

```python
def _rule_strings(metric_rules: Mapping[str, Any], key: str) -> tuple[str, ...]: ...
def _statement_supported(request: ResolutionRequest, fact: StructuralFact, metric_rules: Mapping[str, Any]) -> bool: ...
def _dimensions_allowed(fact: StructuralFact, metric_rules: Mapping[str, Any]) -> bool: ...
def _contextual_concept_match(fact: StructuralFact, metric_rules: Mapping[str, Any]) -> bool: ...
def _orientation(fact: StructuralFact, metric_rules: Mapping[str, Any]) -> str | None: ...
def _is_plausible_extension(fact: StructuralFact, metric_rules: Mapping[str, Any]) -> bool: ...
```

`_statement_supported` returns true when the requested statement role is classified on the fact or when a presentation parent, calculation parent, or ancestry item intersects `statement_support_parents`. A concept listed in `direct_statement_concepts` must instead have the classified role or intersect `direct_statement_parents`; generic note-table support is insufficient. `_dimensions_allowed` returns true for an unsegmented fact or for an exact concept/axis/member combination declared in `allowed_dimensions`; all other dimensions fail closed.

Hard gates run in deterministic order: filing form, requested form, accession, period, unit, metric-local economic exclusion, statement support, dimensions, numeric value, orientation conflict.

- [ ] **Step 6: Generalize classification and evidence reason codes**

Preserve `1.00` canonical aliases, `0.98` governed aliases, `0.96` contextual or strongly structural mappings, and `0.75` review candidates. Add stable reasons:

```text
STRUCTURAL_STATEMENT_SUPPORT
GOVERNED_DIMENSIONAL_CONTEXT
COMPONENT_ONLY_CONCEPT
REVIEW_ONLY_ACCOUNTING_CONTEXT
EXCLUDED_ECONOMIC_CLASS
CURRENT_NONCURRENT_CONFLICT
```

An exact alias in `component_only_concepts` becomes review, not accepted. A concept in `direct_statement_concepts` cannot use generic note-table support. A matching `review_only_phrase` becomes review even if structural signals exist. Accepted decisions append the selected concept's stable code from `concept_reason_codes` when configured. Exact/contextual candidates still pass every hard gate.

- [ ] **Step 7: Relax evidence completeness only for real structural statement evidence**

Set the mapping default to `US-XBRL-RESOLVER-1.1`. In `ResolutionEvidence.validate_complete`, replace the unconditional `not fact.statement_roles` failure with:

```python
has_statement_evidence = bool(
    fact.statement_roles
    or fact.presentation_parents
    or fact.calculation_parents
    or fact.presentation_ancestry
)
```

Still require relationships, labels or documentation, decimals, filing form, filing metadata, namespace, and context. This permits DELL debt-note and CRM lease-table facts while preserving auditable structure.

- [ ] **Step 8: Run focused and existing marketable tests**

Run:

```bash
cd backend && python -m pytest -q tests/test_structural_xbrl_schema.py tests/test_concept_resolver.py
```

Expected: all tests pass and existing marketable decisions remain unchanged except mapping version `1.1`.

- [ ] **Step 9: Commit the common engine**

```bash
git add backend/app/us_valuation/structural_xbrl.py backend/app/us_valuation/concept_resolver.py backend/app/us_valuation/config/structural_concept_rules.json backend/tests/test_structural_xbrl_schema.py backend/tests/test_concept_resolver.py
git commit -m "refactor: make structural resolver policy driven"
```

---

### Task 2: Add debt and commercial-paper borrowing policies

**Model:** Luna High, because liability classification and total/component handling directly affect enterprise-value bridges.

**Files:**
- Modify: `backend/app/us_valuation/config/structural_concept_rules.json`
- Modify: `backend/tests/test_concept_resolver.py`

**Interfaces:**
- Adds policies: `current_debt`, `noncurrent_debt`, `commercial_paper`.
- Reuses aliases already present in `concept_aliases.json`.
- Consumer: Task 5 and the real-filing replay in Task 6.

- [ ] **Step 1: Write failing debt and CRM classification tests**

Add parameterized tests for these accepted direct facts:

```python
@pytest.mark.parametrize(
    "metric,qname,value,parents,roles",
    [
        ("current_debt", "us-gaap:DebtCurrent", 7_550_000_000, ("us-gaap:DebtInstrumentLineItems",), ()),
        ("current_debt", "us-gaap:LongTermDebtCurrent", 0, ("us-gaap:LiabilitiesCurrentAbstract",), ("balance_sheet",)),
        ("noncurrent_debt", "us-gaap:LongTermDebtNoncurrent", 23_611_000_000, ("us-gaap:DebtInstrumentLineItems",), ()),
        ("noncurrent_debt", "us-gaap:LongTermDebtNoncurrent", 0, ("us-gaap:LiabilitiesNoncurrentAbstract",), ("balance_sheet",)),
    ],
)
def test_direct_debt_carrying_amounts_are_accepted(metric, qname, value, parents, roles):
    decision = resolve_concept(
        metric_request(metric),
        [account_fact(qname, value=value, presentation_parents=parents, statement_roles=roles)],
    )
    assert decision.status == "accepted"
    assert decision.value == value
```

Add tests proving:

- `ConvertibleDebtCurrent` is review-only with `COMPONENT_ONLY_CONCEPT`;
- `LongTermDebt` is review-only for `noncurrent_debt` because it may include the current portion;
- `LongTermDebtCurrent` supported only by a generic debt-note parent is not accepted because it is in `direct_statement_concepts`;
- repayment, maturity, face-value, fair-value, and debt-issuance cash-flow concepts are rejected or not admitted;
- CRM's `AvailableForSaleSecuritiesDebtSecurities` carrying $94 million with `FinancialInstrumentAxis/CommercialPaperMember` is rejected as `EXCLUDED_ECONOMIC_CLASS` for `commercial_paper`;
- no commercial-paper borrowing fact returns `NO_CANDIDATE`, never accepted zero.

Add one issuer extension test for `issuer:CurrentBorrowingsAndMaturities` with current-liability presentation and calculation parents plus documentation identifying aggregate current debt carrying amount. It must be accepted at `0.96`; removing either structural signal must reduce it to review.

- [ ] **Step 2: Run the debt tests and observe missing-policy failures**

Run:

```bash
cd backend && python -m pytest -q tests/test_concept_resolver.py -k 'debt or commercial_paper'
```

Expected: new requests return `NO_CANDIDATE` because their metric policies do not exist.

- [ ] **Step 3: Add current-debt policy**

Use current-liability and debt-line-item structural support. Set:

```json
"orientation": "current",
"extension_terms": ["debt current", "current maturities", "short term borrowings"],
"component_only_concepts": ["NotesPayableCurrent", "ConvertibleDebtCurrent", "ShortTermBorrowings"],
"direct_statement_concepts": ["LongTermDebtCurrent"],
"direct_statement_parents": ["us-gaap:LiabilitiesCurrent", "us-gaap:LiabilitiesCurrentAbstract"],
"excluded_economic_phrases": ["available for sale", "investment", "receivable", "maturity repayments", "fair value", "face amount", "proceeds", "repayments"]
```

`DebtCurrent` may use `DebtInstrumentLineItems` structural support. `LongTermDebtCurrent` requires a classified balance-sheet role or current-liability parent so a debt-schedule subtype does not silently establish the aggregate.

- [ ] **Step 4: Add noncurrent-debt policy**

Use noncurrent-liability and debt-line-item structural support. Set `LongTermDebt` and `ConvertibleDebtNoncurrent` as component/review-only concepts. Exclude maturity schedules, face amount, fair value, proceeds, repayments, and issuance costs.

- [ ] **Step 5: Add commercial-paper borrowing policy**

Require current-liability or debt-line-item support. Include dimensions in candidate text, then exclude asset contexts with phrases such as `available for sale`, `investment`, `assets fair value`, and `financial instrument axis`. Do not allow dimensions for borrowing in this phase.

- [ ] **Step 6: Run debt and full resolver tests**

Run:

```bash
cd backend && python -m pytest -q tests/test_concept_resolver.py
```

Expected: all resolver tests pass; CRM's $94 million investment component is rejected and no debt zero is fabricated.

- [ ] **Step 7: Commit debt policies**

```bash
git add backend/app/us_valuation/config/structural_concept_rules.json backend/tests/test_concept_resolver.py
git commit -m "feat: govern structural debt and commercial paper"
```

---

### Task 3: Add finance-lease carrying-value policies

**Model:** Luna High, because lease carrying values must be separated from maturity-payment disclosures.

**Files:**
- Modify: `backend/app/us_valuation/config/structural_concept_rules.json`
- Modify: `backend/tests/test_concept_resolver.py`

**Interfaces:**
- Adds policies: `finance_lease_current`, `finance_lease_noncurrent`, `finance_lease_total`.
- Keeps payment schedule facts as review evidence only.

- [ ] **Step 1: Write failing lease tests**

Add tests for direct current and noncurrent aliases under the corresponding liability parents. Add CRM total coverage:

```python
def test_finance_lease_total_accepts_net_carrying_value_not_gross_payments() -> None:
    carrying_value = account_fact(
        "us-gaap:FinanceLeaseLiability",
        value=664_000_000,
        statement_roles=(),
        presentation_parents=("us-gaap:FinanceLeaseLiabilitiesPaymentsDueAbstract",),
    )
    gross_payments = account_fact(
        "us-gaap:FinanceLeaseLiabilityPaymentsDue",
        value=718_000_000,
        statement_roles=(),
        presentation_parents=("us-gaap:FinanceLeaseLiabilitiesPaymentsDueAbstract",),
    )
    decision = resolve_concept(metric_request("finance_lease_total"), [carrying_value, gross_payments])
    assert decision.status == "accepted"
    assert decision.value == 664_000_000
    assert decision.source_concept == "us-gaap:FinanceLeaseLiability"
```

Add tests proving `FinanceLeaseLiabilityPaymentsDueNextTwelveMonths`, year-two-through-thereafter payment facts, and generic lease commitments are review-only and cannot satisfy current/noncurrent carrying-value requests. Add operating-lease rejection tests.

- [ ] **Step 2: Run lease tests and observe missing-policy failures**

Run:

```bash
cd backend && python -m pytest -q tests/test_concept_resolver.py -k 'finance_lease'
```

Expected: new requests return `NO_CANDIDATE`.

- [ ] **Step 3: Add current and noncurrent finance-lease policies**

Use `orientation: "current"` or `"noncurrent"`, direct finance-lease liability aliases, and matching liability parents. Set payment/maturity phrases to `review_only_phrases`. Exclude `operating lease`, `right of use asset`, `lease cost`, and `cash payments`.

- [ ] **Step 4: Add finance-lease total policy**

Use `orientation: "none"`. Permit `FinanceLeaseLiability` under `FinanceLeaseLiabilitiesPaymentsDueAbstract` as statement support. Put `payments due`, `minimum lease payments`, and maturity-period phrases in review-only handling so the direct net liability outranks gross payment context.

- [ ] **Step 5: Run resolver tests**

Run:

```bash
cd backend && python -m pytest -q tests/test_concept_resolver.py
```

Expected: CRM's $664 million net carrying value is accepted; $718 million gross payments and current/noncurrent payment components are not accepted as carrying values.

- [ ] **Step 6: Commit lease policies**

```bash
git add backend/app/us_valuation/config/structural_concept_rules.json backend/tests/test_concept_resolver.py
git commit -m "feat: govern structural finance lease liabilities"
```

---

### Task 4: Add preferred/temporary-equity and NCI policies

**Model:** Luna High, because mezzanine-equity semantics and dimensioned NCI facts are the highest-risk account mappings in this phase.

**Files:**
- Modify: `backend/app/us_valuation/config/concept_aliases.json`
- Modify: `backend/app/us_valuation/config/structural_concept_rules.json`
- Modify: `backend/tests/test_concept_resolver.py`

**Interfaces:**
- Adds policies: `preferred_equity`, `noncontrolling_interests`.
- Adds preferred-equity aliases: `TemporaryEquityCarryingAmountAttributableToParent` and `TemporaryEquityCarryingAmountIncludingPortionAttributableToNoncontrollingInterests`.
- Adds contextual NCI mapping only for `StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest` with `StatementEquityComponentsAxis/NoncontrollingInterestMember`.

- [ ] **Step 1: Write failing preferred/temporary-equity tests**

Test ANET `PreferredStockValue=0` and WDC `TemporaryEquityCarryingAmountAttributableToParent=0` as accepted direct USD carrying amounts. Test WDC `TemporaryEquityLiquidationPreference=265_000_000`, preferred dividends, conversion value, and preferred share counts as review/rejected and never selected over carrying amount. Test DELL preferred shares issued of zero alone returns no accepted USD value.

Require accepted preferred-stock value facts to include `PREFERRED_EQUITY_CARRYING_AMOUNT` and accepted temporary-equity facts to include `TEMPORARY_EQUITY_CARRYING_AMOUNT` in their reason codes. This records permanent versus mezzanine source semantics without changing the normalized bridge-field name.

- [ ] **Step 2: Write failing NCI dimensional tests**

Use the DELL structure exactly:

```python
def test_governed_nci_equity_member_is_accepted() -> None:
    fact = account_fact(
        "us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
        value=0,
        dimensions=(("us-gaap:StatementEquityComponentsAxis", "us-gaap:NoncontrollingInterestMember"),),
        statement_roles=(),
        presentation_parents=("us-gaap:IncreaseDecreaseInStockholdersEquityRollForward",),
    )
    decision = resolve_concept(metric_request("noncontrolling_interests"), [fact])
    assert decision.status == "accepted"
    assert decision.value == 0
    assert "GOVERNED_DIMENSIONAL_CONTEXT" in decision.reason_codes
```

Use the same concept with `ParentMember`, `RetainedEarningsMember`, and no dimension; none may be accepted as NCI. Test income-statement NCI concepts and FTNT narrative-only ownership as unresolved/review, not structural zero.

- [ ] **Step 3: Run targeted tests and observe missing-policy failures**

Run:

```bash
cd backend && python -m pytest -q tests/test_concept_resolver.py -k 'preferred or temporary or noncontrolling or nci'
```

Expected: policies are missing and WDC temporary equity is not a configured alias.

- [ ] **Step 4: Add preferred/temporary-equity carrying-value policy**

Use `orientation: "none"`; support equity, temporary-equity, mezzanine-equity, and liabilities presentation parents used by the WDC filing. Add liquidation preference, dividend, shares, conversion, proceeds, and EPS phrases to review-only or excluded context. Do not bypass the USD unit gate.

Set concept-specific reason codes:

```json
"concept_reason_codes": {
  "PreferredStocksIncludingAdditionalPaidInCapitalParOrStatedValue": "PREFERRED_EQUITY_CARRYING_AMOUNT",
  "PreferredStockValue": "PREFERRED_EQUITY_CARRYING_AMOUNT",
  "TemporaryEquityCarryingAmountAttributableToParent": "TEMPORARY_EQUITY_CARRYING_AMOUNT",
  "TemporaryEquityCarryingAmountIncludingPortionAttributableToNoncontrollingInterests": "TEMPORARY_EQUITY_CARRYING_AMOUNT"
}
```

- [ ] **Step 5: Add exact governed NCI dimension policy**

Declare:

```json
"allowed_dimensions": {
  "us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest": [
    ["us-gaap:StatementEquityComponentsAxis", "us-gaap:NoncontrollingInterestMember"]
  ]
},
"contextual_concepts": [
  "us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"
]
```

The contextual concept receives `0.96`, method `taxonomy_and_context`, only when the full dimension set exactly matches the policy. Unsegmented total equity and every other member remain non-accepted.

- [ ] **Step 6: Run resolver tests**

Run:

```bash
cd backend && python -m pytest -q tests/test_concept_resolver.py
```

Expected: ANET and WDC direct carrying amounts and DELL's governed NCI member pass; DELL share-count zero, WDC liquidation preference, and other NCI members do not.

- [ ] **Step 7: Commit equity policies**

```bash
git add backend/app/us_valuation/config/concept_aliases.json backend/app/us_valuation/config/structural_concept_rules.json backend/tests/test_concept_resolver.py
git commit -m "feat: govern structural preferred equity and NCI"
```

---

### Task 5: Expose bridge policies through the shadow runner

**Model:** Terra Medium, because this is bounded orchestration after accounting decisions are fixed by Tasks 1-4.

**Files:**
- Modify: `backend/app/us_valuation/structural_shadow.py`
- Modify: `scripts/run_structural_xbrl_shadow.py`
- Modify: `backend/tests/test_structural_shadow.py`
- Modify: `backend/tests/test_structural_xbrl_integration.py`
- Modify: `backend/tests/fixtures/us/structural-xbrl/fsi-20251231.htm`
- Modify: `backend/tests/fixtures/us/structural-xbrl/fsi-2025_pre.xml`
- Modify: `backend/tests/fixtures/us/structural-xbrl/fsi-2025_lab.xml`
- Modify: `backend/tests/fixtures/us/structural-xbrl/us-gaap-2025.xsd`

**Interfaces:**
- Produces: `SUPPORTED_STRUCTURAL_FIELDS: frozenset[str]` containing marketable securities, debt, commercial paper, finance leases, preferred equity, and NCI.
- Retains: `shadow_requests_from_artifact(...) -> tuple[ResolutionRequest, ...]` and `evaluate_shadow_case(...) -> dict[str, Any]`.
- Retains publication effect: `none_shadow_only`.

- [ ] **Step 1: Write failing shadow selection tests**

Replace the test that skips `commercial_paper` with a parameterized test over:

```python
SUPPORTED = {
    "marketable_securities_current",
    "marketable_securities_noncurrent",
    "commercial_paper",
    "current_debt",
    "noncurrent_debt",
    "finance_lease_current",
    "finance_lease_noncurrent",
    "finance_lease_total",
    "preferred_equity",
    "noncontrolling_interests",
}
```

Assert every field creates one USD balance-sheet request, unknown fields remain in `skipped_fields`, input artifacts are unchanged, and the CLI counts accepted/review/rejected/unresolved decisions without touching source artifacts.

- [ ] **Step 2: Run shadow tests and observe the old marketable-only behavior**

Run:

```bash
cd backend && python -m pytest -q tests/test_structural_shadow.py
```

Expected: non-marketable bridge fields are skipped.

- [ ] **Step 3: Generalize request and metadata selection**

Rename `_MARKETABLE_SECURITIES_FIELDS` to public `SUPPORTED_STRUCTURAL_FIELDS`, use it in request selection and `skipped_fields`, and update docstrings from marketable-specific to structural bridge language.

In the CLI, rename `_marketable_securities_gaps` to `_structural_gaps`, use the same supported set, and keep lazy Arelle imports. Parser failures must list supported existing field states and still report `publication_effect: none_shadow_only`.

- [ ] **Step 4: Extend the hermetic Arelle fixture with direct current debt**

Add `us-gaap:DebtCurrent` and `us-gaap:LiabilitiesCurrentAbstract` to the local US-GAAP schema and declare `xmlns:us-gaap="http://fasb.org/us-gaap/2025"` in the Inline-XBRL document. Add a `DebtCurrent` fact of `125000000` under current liabilities, a presentation link from `LiabilitiesCurrentAbstract` to `DebtCurrent`, and standard/documentation labels identifying current debt carrying amount. Update the integration artifact's `bridge_missing_fields` to include `marketable_securities_current` and `current_debt`.

Assert the report contains two accepted decisions, current debt equals `125_000_000`, and summary `accepted_shadow == 2`. Keep the network-forbidden assertion and immutable output checks.

- [ ] **Step 5: Run shadow and hermetic integration tests**

Run:

```bash
cd backend && python -m pytest -q tests/test_structural_shadow.py tests/test_structural_xbrl_integration.py
```

Expected: all tests pass and both marketable securities and current debt traverse cached package -> Arelle -> shared resolver -> shadow report.

- [ ] **Step 6: Run the focused structural suite**

Run:

```bash
cd backend && python -m pytest -q tests/test_structural_xbrl_schema.py tests/test_concept_resolver.py tests/test_arelle_adapter.py tests/test_filing_package.py tests/test_structural_shadow.py tests/test_structural_xbrl_integration.py
```

Expected: all focused tests pass.

- [ ] **Step 7: Commit shadow integration**

```bash
git add backend/app/us_valuation/structural_shadow.py scripts/run_structural_xbrl_shadow.py backend/tests/test_structural_shadow.py backend/tests/test_structural_xbrl_integration.py backend/tests/fixtures/us/structural-xbrl/fsi-20251231.htm backend/tests/fixtures/us/structural-xbrl/fsi-2025_pre.xml backend/tests/fixtures/us/structural-xbrl/fsi-2025_lab.xml backend/tests/fixtures/us/structural-xbrl/us-gaap-2025.xsd
git commit -m "feat: evaluate bridge accounts in structural shadow"
```

---

### Task 6: Verify the real five-company behavior and record GoodBehavior evidence

**Model:** Sol High locally for final accounting reconciliation; Terra Medium may inventory deterministic output differences, but Sol owns every acceptance decision.

**Files:**
- Create: `docs/plans/EVIDENCE.md`
- Update: `docs/superpowers/handoffs/2026-08-10-structural-xbrl-resolution-handoff.md`
- Runtime-only, never stage: `output/structural-xbrl-pilot/run_pilot.py`
- Runtime-only, never stage: `output/structural-xbrl-pilot/results-run6/`

**Interfaces:**
- Consumes cached filing packages for ANET, CRM, DELL, FTNT, and WDC.
- Produces a shadow-only decision matrix and durable evidence links.

- [ ] **Step 1: Run the full backend regression suite**

Run:

```bash
cd backend && python -m pytest -q
```

Expected: all tests pass except any explicitly documented, pre-existing unrelated failure. If any new or structurally related failure appears, stop and repair it before continuing.

- [ ] **Step 2: Replay all five cached real filings without refreshing SEC data**

Use the existing immutable cache under `output/structural-xbrl-pilot/cache`, the evidence rows under the main workspace's `output/evidence-recovery`, and a new immutable `results-run6` directory. Resolve every supported field through `resolve_concept`; do not use expected values to select candidates.

Update the runtime-only pilot helper so its decision function is:

```python
from app.us_valuation.structural_shadow import SUPPORTED_STRUCTURAL_FIELDS


def governed_decision(
    row: dict[str, Any], facts: tuple[StructuralFact, ...], accession: str, form: str
) -> dict[str, Any] | None:
    field = row["field"]
    if field not in SUPPORTED_STRUCTURAL_FIELDS:
        return None
    return resolve_concept(
        ResolutionRequest(
            normalized_concept=field,
            period_end=row["period_end"],
            source_accession=accession,
            unit="USD",
            statement_role="balance_sheet",
            form=form,
        ),
        facts,
    ).as_dict()
```

Store it under `governed_decision` for each account and include every non-null decision in the summary. Do not stage the helper or any `output/` file.

The replay must exercise these accessions:

```text
ANET 0001596532-26-000078
CRM  0001108524-26-000127
DELL 0001571996-26-000030
FTNT 0001262039-26-000021
WDC  0001628280-26-029054
```

Run without `--refresh`:

```bash
python output/structural-xbrl-pilot/run_pilot.py \
  --evidence-root "/Users/carlosconda/Desktop/Investing Application/output/evidence-recovery" \
  --cache-dir output/structural-xbrl-pilot/cache \
  --output-dir output/structural-xbrl-pilot/results-run6 \
  --user-agent "FinSight offline structural verification"
```

Any attempted network request is a verification failure because the five packages are already cached.

- [ ] **Step 3: Compare decisions with the approved accounting baseline**

Require these accepted structural results in USD millions:

```text
current_debt:       DELL 7550; FTNT 0; WDC 1581
noncurrent_debt:    CRM 39280; DELL 23611; FTNT 496.9; WDC 0
finance_lease_total: CRM 664
preferred_equity:   ANET 0; WDC 0 carrying amount
noncontrolling_interests: DELL 0 with NoncontrollingInterestMember
```

Require these non-accepted outcomes:

```text
ANET absence-based debt and lease zeros
CRM commercial-paper investment component of 94
CRM finance-lease current/noncurrent payment schedule components
CRM current-debt subtype-only zeros
DELL preferred share-count zero
FTNT narrative-only NCI zero
WDC temporary-equity liquidation preference of 265
```

Investigate every deviation using source concept, dimensions, statement support, relationships, and reason codes. Do not weaken a hard gate to match the expected table.

- [ ] **Step 4: Record GoodBehavior evidence**

Create `docs/plans/EVIDENCE.md` with:

- commit tested;
- exact commands and timestamps;
- focused and full test outcomes;
- five filing accessions and fact counts;
- accepted/review/rejected/unresolved matrix;
- links to immutable `results-run6` artifacts;
- confirmation that publication effect remained `none_shadow_only`;
- unresolved fields and why they remain unresolved;
- any pre-existing unrelated test failure clearly separated from this phase.

Use the status wording `verified — your confirmation needed`; do not declare production readiness.

- [ ] **Step 5: Update the handoff**

Record the new commits, policy version, exact real-filing results, unresolved uncertainty, test evidence, and the next safe step. State explicitly that `output/` remains untracked and production serving data did not change.

- [ ] **Step 6: Commit verification documentation**

```bash
git add docs/plans/EVIDENCE.md docs/superpowers/handoffs/2026-08-10-structural-xbrl-resolution-handoff.md
git commit -m "docs: record structural bridge resolver verification"
```

- [ ] **Step 7: Run final review**

Review the complete diff from `1d7de4f` through `HEAD` for spec compliance, accounting false positives, accidental production writes, output staging, and test gaps. Run `git status --short` and confirm only the pre-existing untracked `output/` remains.

Final state is `verified — your confirmation needed`, not automatically approved for publication.
