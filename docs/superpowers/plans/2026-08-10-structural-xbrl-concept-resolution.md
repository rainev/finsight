# Structural XBRL Concept Resolution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an isolated Arelle-backed structural XBRL parser and a FinSight-owned deterministic resolver that can surface strongly supported marketable-securities extensions without changing current publication behavior.

**Architecture:** Keep SEC Companyfacts and configured aliases as the production fast path. Parse controlling Inline-XBRL filings in background ingestion through a strict JSON boundary, resolve candidates with hard accounting gates and stable reason codes, and write shadow diagnostics only. The existing valuation pipeline remains authoritative until the shadow corpus is reviewed.

**Tech Stack:** Python 3.11, `arelle-release==2.44.0`, dataclasses, JSON configuration, pytest 8.3.4, existing `SecClient` and SEC cache.

## Global Constraints

- No LLM or semantic model may parse XBRL, approve a mapping, or supply a financial value.
- Existing SEC retrieval, point-in-time filters, provenance, and fail-closed valuation gates remain authoritative.
- Arelle runs only in ingestion/shadow tooling and must not become an application-serving dependency.
- New extension mappings are shadow-only and cannot clear a publication gate in this increment.
- Label similarity alone cannot accept a mapping.
- Every accepted mapping must retain concept, namespace, value, unit, period, accession, context, relationships, mapping version, confidence, and deterministic reason codes.
- Parser absence or failure must preserve current behavior and must never create a zero value.
- Tests must be hermetic and must not require SEC or taxonomy network access.
- Preserve all unrelated changes in the existing dirty worktree.

---

## File Structure

- Create `backend/app/us_valuation/structural_xbrl.py`: immutable parser-boundary and decision dataclasses plus JSON serialization.
- Create `backend/app/us_valuation/concept_resolver.py`: hard gates, standard-alias handling, structural extension classification, exclusions, confidence, and reason codes.
- Create `backend/app/us_valuation/arelle_adapter.py`: lazy Arelle integration that converts a filing model into `StructuralFiling` without leaking Arelle objects.
- Create `backend/app/us_valuation/arelle_worker.py`: child-process entrypoint that owns Arelle imports and parser resource limits.
- Create `backend/app/us_valuation/filing_package.py`: cache the controlling filing's Inline-XBRL and taxonomy/linkbase resources.
- Create `backend/app/us_valuation/structural_shadow.py`: pure shadow-case evaluation with no serving-artifact writes.
- Create `backend/app/us_valuation/config/structural_concept_rules.json`: governed structural rules for current and noncurrent marketable securities.
- Create `backend/requirements-xbrl.txt`: isolated pinned Arelle dependency.
- Create `scripts/run_structural_xbrl_shadow.py`: bounded CLI over withheld artifacts.
- Create `backend/tests/fixtures/us/structural-xbrl/`: minimal local Inline-XBRL instance and taxonomy/linkbases.
- Create focused test modules instead of expanding the already large `test_us_valuation.py`.

---

### Task 1: Define the parser boundary and auditable resolution schema

**Files:**
- Create: `backend/app/us_valuation/structural_xbrl.py`
- Test: `backend/tests/test_structural_xbrl_schema.py`

**Interfaces:**
- Produces: `StructuralFact`, `StructuralFiling`, `ParseDiagnostic`, `ResolutionRequest`, and `ResolutionDecision` frozen dataclasses.
- Produces: `StructuralFact.as_dict()`, `StructuralFact.from_dict()`, `StructuralFiling.as_dict()`, and `ResolutionDecision.as_dict()`.
- Consumers: Tasks 2, 3, and 5.

- [ ] **Step 1: Write the failing round-trip and validation tests**

```python
from app.us_valuation.structural_xbrl import (
    ResolutionDecision,
    ResolutionRequest,
    StructuralFact,
    StructuralFiling,
)


def test_structural_fact_round_trip_preserves_provenance() -> None:
    fact = StructuralFact(
        qname="fsi:LiquidInvestmentSecuritiesCurrent",
        namespace="https://example.test/fsi/2025",
        local_name="LiquidInvestmentSecuritiesCurrent",
        labels=(("standard", "Liquid investment securities"),),
        documentation="Available-for-sale debt securities classified as current.",
        value=42_500_000.0,
        unit="USD",
        period_start=None,
        period_end="2025-12-31",
        context_id="CurrentYearInstant",
        dimensions=(),
        statement_roles=("balance_sheet",),
        presentation_parents=("us-gaap:AssetsCurrent",),
        calculation_parents=("us-gaap:AssetsCurrent",),
        calculation_children=(),
        definition_parents=(),
        definition_children=(),
        source_accession="0000000000-26-000001",
    )
    assert StructuralFact.from_dict(fact.as_dict()) == fact


def test_resolution_request_rejects_empty_accession() -> None:
    with pytest.raises(ValueError, match="accession"):
        ResolutionRequest(
            normalized_concept="marketable_securities_current",
            period_end="2025-12-31",
            source_accession="",
            unit="USD",
            statement_role="balance_sheet",
        )
```

- [ ] **Step 2: Run the tests and verify the missing module failure**

Run: `cd backend && pytest -q tests/test_structural_xbrl_schema.py`

Expected: collection fails with `ModuleNotFoundError: No module named 'app.us_valuation.structural_xbrl'`.

- [ ] **Step 3: Implement immutable types and deterministic JSON serialization**

Use tuple-valued fields so hashing and equality are stable. Validate ISO dates with `date.fromisoformat`, require nonempty accession/QName/unit/context, reject booleans as numeric values, sort nested mappings before serialization, and define these decision states exactly:

```python
ResolutionStatus = Literal["accepted", "review", "rejected", "unresolved"]

@dataclass(frozen=True)
class ResolutionDecision:
    status: ResolutionStatus
    normalized_concept: str
    source_concept: str | None
    value: float | None
    unit: str | None
    period: str
    source_accession: str
    confidence: float
    mapping_method: str
    reason_codes: tuple[str, ...]
    mapping_version: str = "US-XBRL-RESOLVER-1.0"
```

Require `0 <= confidence <= 1`; only `accepted` may carry an automatically usable value, while `review` may preserve a candidate value for manual inspection.

- [ ] **Step 4: Run the schema tests**

Run: `cd backend && pytest -q tests/test_structural_xbrl_schema.py`

Expected: all tests pass.

- [ ] **Step 5: Commit the schema boundary**

```bash
git add backend/app/us_valuation/structural_xbrl.py backend/tests/test_structural_xbrl_schema.py
git commit -m "feat: define structural XBRL evidence schema"
```

---

### Task 2: Build the deterministic marketable-securities resolver

**Files:**
- Create: `backend/app/us_valuation/concept_resolver.py`
- Create: `backend/app/us_valuation/config/structural_concept_rules.json`
- Test: `backend/tests/test_concept_resolver.py`
- Read: `backend/app/us_valuation/config/concept_aliases.json`

**Interfaces:**
- Consumes: `StructuralFact`, `ResolutionRequest`, and `ResolutionDecision` from Task 1.
- Produces: `resolve_concept(request: ResolutionRequest, facts: Iterable[StructuralFact]) -> ResolutionDecision`.
- Produces: `load_structural_rules() -> dict[str, Any]`.
- Consumer: Task 5.

- [ ] **Step 1: Write failing tests for exact aliases, strong extensions, ambiguity, and false friends**

```python
def test_known_standard_alias_is_accepted() -> None:
    fact = make_fact(
        qname="us-gaap:ShortTermInvestments",
        local_name="ShortTermInvestments",
        value=100.0,
    )
    decision = resolve_concept(current_request(), [fact])
    assert decision.status == "accepted"
    assert decision.confidence == 0.98
    assert decision.mapping_method == "known_taxonomy_alias"


def test_extension_requires_two_independent_structural_signals() -> None:
    fact = make_fact(
        qname="fsi:LiquidInvestmentSecuritiesCurrent",
        local_name="LiquidInvestmentSecuritiesCurrent",
        documentation="Available-for-sale debt securities classified as current.",
        presentation_parents=("us-gaap:AssetsCurrent",),
        calculation_parents=("us-gaap:AssetsCurrent",),
        value=125.0,
    )
    decision = resolve_concept(current_request(), [fact])
    assert decision.status == "accepted"
    assert decision.confidence == 0.96
    assert set(decision.reason_codes) >= {
        "CURRENT_ASSET_PRESENTATION_PARENT",
        "CURRENT_ASSET_CALCULATION_PARENT",
        "DEFINITION_IDENTIFIES_MARKETABLE_SECURITIES",
    }


def test_label_only_extension_is_review_not_accepted() -> None:
    fact = make_fact(
        qname="fsi:MarketableInvestments",
        local_name="MarketableInvestments",
        labels=(("standard", "Marketable investments"),),
        documentation="",
        presentation_parents=(),
        calculation_parents=(),
        value=90.0,
    )
    assert resolve_concept(current_request(), [fact]).status == "review"


@pytest.mark.parametrize(
    "qname,documentation",
    [
        ("fsi:StrategicEquityInvestments", "Strategic nonmarketable equity investments."),
        ("fsi:EquityMethodInvestments", "Investments accounted for under the equity method."),
        ("fsi:RestrictedTrustAssets", "Restricted assets held in trust as collateral."),
        ("fsi:CustomerFinancingReceivables", "Customer financing receivables."),
    ],
)
def test_false_friends_are_rejected(qname: str, documentation: str) -> None:
    fact = make_fact(qname=qname, local_name=qname.split(":", 1)[1], documentation=documentation)
    assert resolve_concept(current_request(), [fact]).status == "rejected"
```

Also test rejection for wrong accession, period, unit, statement role, dimensional context, current/noncurrent conflict, duplicate component/total candidates, and equal-strength conflicting facts.

- [ ] **Step 2: Run resolver tests and verify the missing implementation failure**

Run: `cd backend && pytest -q tests/test_concept_resolver.py`

Expected: collection fails because `concept_resolver` does not exist.

- [ ] **Step 3: Add governed structural rules**

Create `structural_concept_rules.json` with version `US-XBRL-RESOLVER-1.0`, two metric sections, and explicit lists for:

```json
{
  "marketable_securities_current": {
    "statement_role": "balance_sheet",
    "unit": "USD",
    "known_current_parents": [
      "us-gaap:AssetsCurrent",
      "us-gaap:ShortTermInvestments",
      "us-gaap:MarketableSecuritiesCurrent"
    ],
    "required_definition_phrases": [
      "available-for-sale",
      "debt securities",
      "marketable securities",
      "short-term investments"
    ]
  }
}
```

Add the corresponding noncurrent parents `us-gaap:AssetsNoncurrent`, `us-gaap:LongTermInvestments`, and `us-gaap:MarketableSecuritiesNoncurrent`. Add governed exclusion phrases for strategic, equity method, restricted, trust, collateral, receivable, and financial-institution trading assets.

- [ ] **Step 4: Implement hard gates before scoring**

Apply checks in this order: accession, period, unit, statement role, dimensions, current/noncurrent compatibility, excluded economic class, and conflict/double-counting detection. Return stable reason codes such as `ACCESSION_MISMATCH`, `PERIOD_MISMATCH`, `UNIT_MISMATCH`, `DIMENSIONED_NONCONSOLIDATED_FACT`, `EXCLUDED_ECONOMIC_CLASS`, and `AMBIGUOUS_FACTS`.

- [ ] **Step 5: Implement deterministic evidence classification**

Use the existing alias configuration for standard concepts. Confidence is fixed by evidence class:

- first configured canonical concept: `1.00`, method `exact_configured_concept`;
- other configured standard alias: `0.98`, method `known_taxonomy_alias`;
- extension passing all hard gates with explicit classification plus at least one presentation and one calculation signal: `0.96`, method `extension_structural_match`;
- plausible extension without complete structural support: `0.75`, status `review`, method `insufficient_structural_support`;
- hard-gate failure: `0.00`, status `rejected`;
- no candidate: `0.00`, status `unresolved`, reason `NO_CANDIDATE`.

Do not average semantic similarities and do not allow a confidence score to override a failed gate.

- [ ] **Step 6: Run resolver and schema tests**

Run: `cd backend && pytest -q tests/test_structural_xbrl_schema.py tests/test_concept_resolver.py`

Expected: all tests pass.

- [ ] **Step 7: Commit the resolver**

```bash
git add backend/app/us_valuation/concept_resolver.py backend/app/us_valuation/config/structural_concept_rules.json backend/tests/test_concept_resolver.py
git commit -m "feat: resolve XBRL concepts with accounting structure"
```

---

### Task 3: Add the isolated Arelle adapter and representative filing fixtures

**Files:**
- Create: `backend/requirements-xbrl.txt`
- Create: `backend/app/us_valuation/arelle_adapter.py`
- Create: `backend/app/us_valuation/arelle_worker.py`
- Create: `backend/tests/test_arelle_adapter.py`
- Create: `backend/tests/fixtures/us/structural-xbrl/fsi-20251231.htm`
- Create: `backend/tests/fixtures/us/structural-xbrl/fsi-2025.xsd`
- Create: `backend/tests/fixtures/us/structural-xbrl/us-gaap-2025.xsd`
- Create: `backend/tests/fixtures/us/structural-xbrl/fsi-2025_pre.xml`
- Create: `backend/tests/fixtures/us/structural-xbrl/fsi-2025_cal.xml`
- Create: `backend/tests/fixtures/us/structural-xbrl/fsi-2025_lab.xml`

**Interfaces:**
- Consumes: schema types from Task 1.
- Produces: `ArelleUnavailable`, `ArelleParseError`, `ArelleParseTimeout`, and `parse_structural_filing(entrypoint: Path, *, accession: str, timeout_seconds: int = 120) -> StructuralFiling`.
- Produces: child-process command `python -m app.us_valuation.arelle_worker --entrypoint PATH --accession ACCESSION --output PATH`.
- Consumer: Task 5.

- [ ] **Step 1: Pin the isolated dependency**

Create `backend/requirements-xbrl.txt` containing:

```text
-r requirements.txt
arelle-release==2.44.0
```

- [ ] **Step 2: Add a minimal local Inline-XBRL filing package**

The fixture taxonomy must define:

- `fsi:LiquidInvestmentSecuritiesCurrent`, value `42,500,000`, documentation identifying available-for-sale debt securities classified as current;
- `fsi:LiquidInvestmentSecuritiesNoncurrent`, value `8,000,000`, documentation identifying noncurrent marketable debt securities;
- `fsi:StrategicEquityInvestments`, value `70,000,000`, documentation identifying strategic nonmarketable equity investments;
- an instant context at `2025-12-31` and unit `iso4217:USD`;
- balance-sheet presentation parents for the two liquid-investment concepts;
- current/noncurrent calculation parents for those concepts;
- a local minimal `us-gaap` stub schema containing `AssetsCurrent`, `AssetsNoncurrent`, `ShortTermInvestments`, and `LongTermInvestments`, so every taxonomy import resolves without network access;
- general-special definition relationships from the extension concepts to the compatible local `us-gaap` concepts;
- labels and documentation in the label linkbase.

All imports must resolve within `backend/tests/fixtures/us/structural-xbrl/`; the test must not contact the network.

- [ ] **Step 3: Write failing adapter tests**

```python
def test_arelle_adapter_extracts_extension_structure() -> None:
    filing = parse_structural_filing(FIXTURE_ROOT / "fsi-20251231.htm", accession=ACCESSION)
    current = next(f for f in filing.facts if f.local_name == "LiquidInvestmentSecuritiesCurrent")
    assert current.value == 42_500_000
    assert current.unit == "USD"
    assert current.period_end == "2025-12-31"
    assert current.statement_roles == ("balance_sheet",)
    assert "us-gaap:AssetsCurrent" in current.presentation_parents
    assert "us-gaap:AssetsCurrent" in current.calculation_parents
    assert "us-gaap:ShortTermInvestments" in current.definition_parents
    assert "available-for-sale" in current.documentation.lower()


def test_arelle_adapter_converts_timeout_to_domain_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=args[0], timeout=kwargs["timeout"])

    monkeypatch.setattr(subprocess, "run", timeout)
    with pytest.raises(ArelleParseTimeout):
        parse_structural_filing(
            FIXTURE_ROOT / "fsi-20251231.htm",
            accession=ACCESSION,
            timeout_seconds=1,
        )
```

- [ ] **Step 4: Run the adapter tests before installing Arelle**

Run: `cd backend && pytest -q tests/test_arelle_adapter.py`

Expected: failure because the adapter module does not exist; after the module skeleton exists, importing the parent application must not import Arelle.

- [ ] **Step 5: Install the isolated dependency in the task environment**

Run: `cd backend && python3 -m pip install -r requirements-xbrl.txt`

Expected: `arelle-release==2.44.0` installs successfully on Python 3.11.

- [ ] **Step 6: Implement the adapter with a strict lifecycle**

Keep Arelle imports inside `arelle_worker.py`. The parent adapter must invoke the worker with `subprocess.run(..., timeout=timeout_seconds, check=False)`, parse only the worker's JSON output, and map timeout, missing dependency, nonzero exit, malformed JSON, and empty-fact results to explicit domain exceptions.

Inside the worker, create an Arelle controller, load the local entrypoint, reject a model with no facts or fatal errors, walk numeric facts, read contexts/units/labels, and traverse `parent-child`, `summation-item`, `general-special`, `domain-member`, and dimensional relationship sets. Convert QNames and relationship endpoints to stable prefixed strings before constructing `StructuralFact` values. Capture parser diagnostics as `ParseDiagnostic` records. Close the model and controller in `finally`.

On POSIX systems, set a 120-second CPU limit and a 2 GiB address-space limit when the platform supports `resource.RLIMIT_CPU` and `resource.RLIMIT_AS`. The parent timeout remains authoritative on platforms where either limit is unavailable.

No Arelle object may appear in a returned dataclass or JSON payload.

- [ ] **Step 7: Run adapter, resolver, and schema tests**

Run: `cd backend && pytest -q tests/test_arelle_adapter.py tests/test_concept_resolver.py tests/test_structural_xbrl_schema.py`

Expected: all tests pass without network access.

- [ ] **Step 8: Commit the adapter and fixtures**

```bash
git add backend/requirements-xbrl.txt backend/app/us_valuation/arelle_adapter.py backend/app/us_valuation/arelle_worker.py backend/tests/test_arelle_adapter.py backend/tests/fixtures/us/structural-xbrl
git commit -m "feat: parse structural XBRL with Arelle"
```

---

### Task 4: Cache complete SEC filing packages reproducibly

**Files:**
- Modify: `backend/app/us_valuation/sec_client.py:15-180`
- Create: `backend/app/us_valuation/filing_package.py`
- Create: `backend/tests/test_filing_package.py`

**Interfaces:**
- Extends: `SecClient.filing_index(cik, accession, *, refresh=False) -> dict[str, Any]`.
- Extends: `SecClient.filing_attachment(cik, accession, filename, *, refresh=False) -> bytes`.
- Produces: `cache_structural_filing_package(client: SecClient, *, cik: str, accession: str, primary_document: str, output_dir: Path, refresh: bool = False) -> Path` returning the local primary-document entrypoint.
- Consumer: Task 5.

- [ ] **Step 1: Write failing package-cache tests**

```python
def test_package_cache_downloads_only_structural_resources(tmp_path: Path) -> None:
    client = FakeSecClient(
        index_names=[
            "fsi-20251231.htm",
            "fsi-2025.xsd",
            "fsi-2025_pre.xml",
            "fsi-2025_cal.xml",
            "fsi-2025_lab.xml",
            "press-release.pdf",
        ]
    )
    entrypoint = cache_structural_filing_package(
        client,
        cik="0000000001",
        accession="0000000001-26-000001",
        primary_document="fsi-20251231.htm",
        output_dir=tmp_path,
    )
    assert entrypoint.name == "fsi-20251231.htm"
    assert not (entrypoint.parent / "press-release.pdf").exists()
    assert json.loads((entrypoint.parent / "package-manifest.json").read_text())["accession"] == "0000000001-26-000001"


@pytest.mark.parametrize("filename", ["../secret", "/tmp/file.xsd", "nested/file.xml"])
def test_filing_attachment_rejects_unsafe_names(filename: str, tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="safe file name"):
        SecClient(user_agent=None, cache_dir=tmp_path).filing_attachment(
            "1", "0000000001-26-000001", filename
        )
```

- [ ] **Step 2: Run the package tests and verify missing API failures**

Run: `cd backend && pytest -q tests/test_filing_package.py`

Expected: failures because the filing-index, attachment, and package-cache APIs do not exist.

- [ ] **Step 3: Add safe SEC archive accessors**

Build archive URLs from normalized CIK and digits-only accession. Reuse `_get_json` and `_get_bytes`, current throttling, User-Agent enforcement, durable cache metadata, hashes, and retries. Permit only a basename with no directory traversal.

- [ ] **Step 4: Implement bounded package selection and manifesting**

Always include the primary document. Include filing-directory resources ending in `.xsd`, `_pre.xml`, `_cal.xml`, `_def.xml`, `_lab.xml`, and the filing instance `.xml`. Exclude PDFs, images, exhibits, and unrelated HTML. Write `package-manifest.json` with accession, CIK, primary document, source URLs, relative filenames, SHA-256 hashes, and cache timestamps.

If the primary document or a locally referenced extension schema is unavailable, raise `FilingPackageIncomplete`; do not return a partial entrypoint.

- [ ] **Step 5: Run SEC client and package tests**

Run: `cd backend && pytest -q tests/test_filing_package.py tests/test_us_valuation.py -k 'sec_client or refresh_cache'`

Expected: all selected tests pass.

- [ ] **Step 6: Commit package acquisition**

```bash
git add backend/app/us_valuation/sec_client.py backend/app/us_valuation/filing_package.py backend/tests/test_filing_package.py
git commit -m "feat: cache SEC structural filing packages"
```

---

### Task 5: Add a shadow-only structural resolution path

**Files:**
- Create: `backend/app/us_valuation/structural_shadow.py`
- Create: `backend/tests/test_structural_shadow.py`
- Create: `scripts/run_structural_xbrl_shadow.py`

**Interfaces:**
- Consumes: filing-package cache from Task 4, Arelle adapter from Task 3, and resolver from Task 2.
- Produces: `shadow_requests_from_artifact(artifact: Mapping[str, Any]) -> tuple[ResolutionRequest, ...]`.
- Produces: `evaluate_shadow_case(artifact: Mapping[str, Any], filing: StructuralFiling) -> dict[str, Any]`.
- Produces: CLI diagnostic JSON under a caller-supplied output directory only.

- [ ] **Step 1: Write failing pure shadow-evaluation tests**

```python
def test_shadow_case_emits_candidate_without_mutating_artifact() -> None:
    artifact = withheld_artifact(missing=["marketable_securities_current"])
    original = deepcopy(artifact)
    report = evaluate_shadow_case(artifact, structural_filing_with_current_extension())
    assert artifact == original
    assert report["publication_effect"] == "none_shadow_only"
    assert report["decisions"][0]["status"] == "accepted"
    assert report["decisions"][0]["normalized_concept"] == "marketable_securities_current"


def test_shadow_case_ignores_non_marketability_bridge_fields() -> None:
    artifact = withheld_artifact(missing=["commercial_paper"])
    report = evaluate_shadow_case(artifact, empty_structural_filing())
    assert report["decisions"] == []
    assert report["skipped_fields"] == ["commercial_paper"]
```

Also test missing controlling accession, mismatched period, parser diagnostics, and review/rejected candidates.

- [ ] **Step 2: Run shadow tests and verify missing module failure**

Run: `cd backend && pytest -q tests/test_structural_shadow.py`

Expected: collection fails because `structural_shadow` does not exist.

- [ ] **Step 3: Implement pure artifact-to-request and report logic**

Read only explicit `bridge_missing_fields` values from withheld artifacts. Build requests only for `marketable_securities_current` and `marketable_securities_noncurrent`. Require the artifact's controlling accession and period. Return a report containing ticker, CIK, valuation date, controlling filing, existing field state, parser diagnostics, resolution decisions, skipped fields, and `publication_effect: none_shadow_only`.

- [ ] **Step 4: Implement the bounded CLI**

Support:

```text
--data-root backend/app/data/us_valuations
--cache-dir <SEC cache path>
--output-root output/structural-xbrl-shadow
--ticker TICKER            # repeatable optional filter
--refresh
--user-agent
```

The CLI discovers withheld artifacts, skips cases with no marketable-securities gap, caches the controlling filing package, parses it once, evaluates requests, and writes one immutable JSON report per ticker plus `summary.json`. It must never modify `backend/app/data/us_valuations` or frontend data.

Summary counters must include discovered, eligible, parsed, accepted_shadow, review, rejected, unresolved, parser_failed, and skipped.

- [ ] **Step 5: Run shadow tests and CLI help**

Run: `cd backend && pytest -q tests/test_structural_shadow.py`

Run: `python3 scripts/run_structural_xbrl_shadow.py --help`

Expected: tests pass and help exits zero without importing Arelle until execution begins.

- [ ] **Step 6: Commit the shadow path**

```bash
git add backend/app/us_valuation/structural_shadow.py backend/tests/test_structural_shadow.py scripts/run_structural_xbrl_shadow.py
git commit -m "feat: add shadow structural XBRL resolution"
```

---

### Task 6: Verify regression safety and measure the shadow result

**Files:**
- Modify: `README.md`
- Verify: `backend/tests/`
- Generate without committing: `output/structural-xbrl-shadow/`

**Interfaces:**
- Consumes: the completed parser, resolver, package cache, and shadow CLI.
- Produces: verified test output and a bounded shadow summary; does not change serving artifacts.

- [ ] **Step 1: Document installation and shadow operation**

Add a concise README section with these commands:

```bash
cd backend
python3 -m pip install -r requirements-xbrl.txt
cd ..
python3 scripts/run_structural_xbrl_shadow.py \
  --data-root backend/app/data/us_valuations \
  --cache-dir /path/to/sec-cache \
  --output-root output/structural-xbrl-shadow \
  --user-agent "FinSight monitored-contact@example.com"
```

State explicitly that results are diagnostics and cannot clear publication gates.

- [ ] **Step 2: Run focused structural-XBRL tests**

Run:

```bash
cd backend && pytest -q \
  tests/test_structural_xbrl_schema.py \
  tests/test_concept_resolver.py \
  tests/test_arelle_adapter.py \
  tests/test_filing_package.py \
  tests/test_structural_shadow.py
```

Expected: all focused tests pass.

- [ ] **Step 3: Run existing extraction and valuation regression tests**

Run:

```bash
cd backend && pytest -q \
  tests/test_filing_evidence.py \
  tests/test_us_valuation.py \
  tests/test_us_valuation_v2_routing.py \
  tests/test_bridge_recovery.py
```

Expected: no new failures. Any pre-existing failure must be recorded with its exact test name and reproduced against the starting commit before being classified as pre-existing.

- [ ] **Step 4: Run the full backend suite**

Run: `cd backend && pytest -q`

Expected: no new failures relative to the baseline.

- [ ] **Step 5: Run a bounded shadow evaluation**

Use locally cached filing packages first. If an identifying SEC User-Agent is configured, refresh only eligible marketable-securities cases. Inspect every `accepted_shadow` decision and a sample of review/rejected decisions for accession, period, unit, consolidated context, statement role, structural signals, exclusion handling, and double-counting risk.

The handoff must report:

- eligible company count;
- parser success/failure count;
- accepted-shadow, review, rejected, and unresolved counts;
- source concepts and reason codes for every accepted-shadow case;
- any false positive or unresolved ambiguity;
- runtime and cache-size observations;
- an explicit recommendation to keep shadow-only or promote one evidence class in a later, separately approved change.

- [ ] **Step 6: Check formatting and unintended serving changes**

Run: `git diff --check`

Run: `git status --short`

Verify no file under `backend/app/data/us_valuations/` or `frontend/public/data/` was modified by this work.

- [ ] **Step 7: Commit documentation**

```bash
git add README.md
git commit -m "docs: explain structural XBRL shadow analysis"
```

---

## Final Review Checklist

- [ ] Arelle imports are lazy and isolated from application startup.
- [ ] The resolver is deterministic and has no LLM dependency.
- [ ] Standard Companyfacts aliases preserve prior values.
- [ ] Extensions require all hard gates and independent structural support.
- [ ] False-friend investments are rejected.
- [ ] Parser failures remain unresolved and never become zero.
- [ ] Shadow evaluation cannot modify serving artifacts or publication state.
- [ ] Focused, regression, and full backend tests have evidence-backed results.
- [ ] Shadow results are reviewed before any proposal to promote mappings.
