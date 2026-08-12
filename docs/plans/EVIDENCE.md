# Structural bridge resolver verification evidence

Status: **verified — your confirmation needed**

Date: 2026-08-13 (Asia/Manila)

## Scope and tested commits

- Task 6 implementation checkpoint: `1544335 fix: harden structural bridge resolution`
- Independently reviewed follow-up: `432e9db fix: classify structural relationship roles safely`
- Final role-bypass correction: `8155326 fix: preserve fail-closed relationship roles`
- Mapping policy: `US-XBRL-RESOLVER-1.1`
- Publication effect: `none_shadow_only`
- Production valuation inputs and serving artifacts were not changed.

The verification used cached filing packages only. No SEC refresh was requested, expected
values were not supplied to the resolver, and all generated pilot files remain untracked
under `output/structural-xbrl-pilot/`.

## Automated verification

At approximately 2026-08-13 00:02 PST:

```text
pytest -q backend/tests/test_structural_xbrl_schema.py \
  backend/tests/test_concept_resolver.py \
  backend/tests/test_arelle_adapter.py \
  backend/tests/test_filing_package.py \
  backend/tests/test_structural_shadow.py \
  backend/tests/test_structural_xbrl_integration.py

316 passed in 6.21s
```

```text
pytest -q backend/tests

459 passed, 3 skipped, 1 failed in 7.42s
```

The single full-suite failure is pre-existing and unrelated to structural XBRL:

```text
test_microsoft_public_artifact_contains_no_raw_financial_amounts
KeyError: 'automated_review'
```

The test already expected `public["automated_review"]` before this branch, while
`backend/app/us_valuation/artifacts.py` did not emit it. Neither that production file nor
the failing test was changed by Task 6.

`git diff --check` and JSON policy validation passed. No files under
`backend/app/data/us_valuations/` or `frontend/public/data/` changed.

## Offline Arelle replay

Final immutable local run:

```text
output/structural-xbrl-pilot/results-run24/
```

Summary: [results-run24/summary.json](../../output/structural-xbrl-pilot/results-run24/summary.json)

| Ticker | Accession | Facts | Parser result |
| --- | --- | ---: | --- |
| ANET | `0001596532-26-000078` | 576 | parsed |
| CRM | `0001108524-26-000127` | 772 | parsed |
| DELL | `0001571996-26-000030` | 1,040 | parsed |
| FTNT | `0001262039-26-000021` | 1,043 | parsed |
| WDC | `0001628280-26-029054` | 990 | parsed |

Total: 5/5 parsed, zero parser failures, 4,421 facts. The 26 governed requests produced
13 accepted, 2 review, 11 rejected, and 0 unresolved decisions.

## Accepted accounting baseline

Values are USD millions.

| Ticker | FinSight field | Value | Source concept | Decision basis |
| --- | --- | ---: | --- | --- |
| ANET | marketable securities, current | 9,563.7 | `AvailableForSaleSecuritiesDebtSecuritiesCurrent` | known taxonomy alias |
| ANET | preferred equity | 0 | `PreferredStockValue` | governed carrying amount |
| CRM | marketable securities, current | 2,902 | `AvailableForSaleSecuritiesDebtSecuritiesCurrent` | known taxonomy alias |
| CRM | finance lease, total | 664 | `FinanceLeaseLiability` | exact carrying-value concept |
| CRM | noncurrent debt | 39,280 | `LongTermDebtNoncurrent` | exact carrying-value concept |
| DELL | current debt | 7,550 | `DebtCurrent` | governed taxonomy alias |
| DELL | noncurrent debt | 23,611 | `LongTermDebtNoncurrent` | exact carrying-value concept |
| DELL | NCI | 0 | `StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest` | exact NCI member dimension |
| FTNT | current debt | 0 | `LongTermDebtCurrent` | direct current carrying amount |
| FTNT | noncurrent debt | 496.9 | `LongTermDebtNoncurrent` | direct noncurrent carrying amount |
| WDC | current debt | 1,581 | `LongTermDebtCurrent` | direct current carrying amount |
| WDC | noncurrent debt | 0 | `LongTermDebtNoncurrent` | direct noncurrent carrying amount |
| WDC | preferred equity | 0 | `TemporaryEquityCarryingAmountAttributableToParent` | temporary-equity carrying amount |

## Required non-accepted outcomes

| Case | Outcome | Why it remains non-accepted |
| --- | --- | --- |
| ANET debt and lease absence-based zeros | rejected | no qualifying current-period carrying-value fact; absence is not zero |
| CRM commercial-paper investment component, 94 | rejected | available-for-sale investment asset, not borrowing |
| CRM current-debt subtype zero | review | `ConvertibleDebtCurrent` is component-only, not aggregate debt |
| CRM lease current/noncurrent schedule components | rejected | payment schedules cannot replace carrying-value splits |
| DELL preferred share-count zero | rejected | share count is not a USD preferred-equity carrying amount |
| FTNT narrative-only NCI zero | rejected | no governed NCI balance with required member context |
| WDC temporary-equity liquidation preference, 265 | not selected | liquidation preference is not carrying amount |

FTNT's `$1,134.7m` `OtherShortTermInvestments` remains review-grade because the current
policy does not yet have enough structural support to auto-accept it.

## Corrections proven during Task 6

- Generic words such as `current` and `term` no longer admit unrelated accounts.
- Exact debt, preferred/temporary-equity, and dimensional NCI facts are not contaminated
  by presentation ancestry from unrelated XBRL roles.
- Relationship evidence now preserves a classified statement role. Root inference is
  fail-closed for empty, mixed, unknown, or role-conflicting relationship sets.
- `Long-Term Debt, Excluding Current Maturities` is correctly noncurrent.
- CRM commercial-paper evidence is selected by governed accounting phrases and context,
  not issuer-specific tags or expected values.
- A genuine standard or issuer-extension commercial-paper liability may use only the
  governed `FinancialInstrumentAxis/CommercialPaperMember` context.
- Rejected evidence prefers the fact that progressed furthest through the ordered hard
  gates; the hard-gate order for each fact remains unchanged.

Independent Luna High reviews identified cross-role contamination, unsafe relationship-role
inference, commercial-paper dimensional policy, failure-evidence ordering, and a final
role-name fallback bypass. Each finding received a regression and correction. The final
bounded re-review of the corrected bypass was clean.

## Remaining boundary

This verifies deterministic extraction and classification for the five-company pilot. It
does not approve production promotion, prove universe-wide coverage, or change any public
valuation. The five-company evidence is preserved above; the broader representative replay
is recorded below.

## Task 3 — representative 20-company broader replay

Status: **verified — your confirmation needed**. This section records the controller-verified
post-fix replay on 2026-08-13. It remains shadow-only: no production valuation input, serving
artifact, or publication gate was changed.

### Exact verification command and immutable outputs

Focused structural regression suite at the current code:

```bash
pytest -q backend/tests/test_structural_xbrl_schema.py backend/tests/test_concept_resolver.py backend/tests/test_arelle_adapter.py backend/tests/test_filing_package.py backend/tests/test_structural_shadow.py backend/tests/test_structural_xbrl_integration.py
```

Observed result:

```text
330 passed in 6.34s
```

The committed `scripts/run_structural_xbrl_shadow.py` CLI was replayed against the staged
20-company input with the existing cached SEC packages and with `--refresh` omitted. The
immutable runtime outputs are:

```text
output/structural-xbrl-broad-corpus/results-baseline/
output/structural-xbrl-broad-corpus/results-post-fix-20260813/
output/structural-xbrl-pilot/results-regression-20260813/
```

The runtime directories are intentionally untracked. The local Arelle environment was
restored with pinned `arelle-release==2.44.0` solely to run the cached packages; this did not
add a production dependency.

### Corpus and case-level result

The representative corpus was:

```text
A, ABBV, AMZN, APD, BA, CAT, CCL, CRDO, CSCO, DXCM, FDX,
KDP, MCD, META, NVDA, ORCL, PLTR, SBUX, TMUS, UAL
```

| Metric | Post-fix result |
| --- | ---: |
| Discovered | 20 |
| Eligible | 20 |
| Parsed by Arelle | 20 |
| Skipped | 0 |
| Parser failures | 0 |
| Model-route eligible | 20 |
| Case dispositions | 20 withhold |
| `publish_candidate` | 0 |
| `lower_confidence_candidate` | 0 |
| `data_quality_status: fail` | 20 |
| `data_quality_score: null` | 20 |
| `publication_effect: none_shadow_only` | 20 |

There were 97 field decisions:

| Status | Count |
| --- | ---: |
| Accepted | 1 |
| Review | 6 |
| Rejected | 71 |
| Unresolved | 19 |
| **Total** | **97** |

The sole accepted new mapping was:

| Ticker | FinSight field | Source concept | Value | Confidence | Method | Reason |
| --- | --- | --- | ---: | ---: | --- | --- |
| NVDA | `preferred_equity` | `us-gaap:PreferredStockValueOutstanding` | 0 USD | 0.98 | `known_taxonomy_alias` | `KNOWN_TAXONOMY_ALIAS` + `PREFERRED_EQUITY_CARRYING_AMOUNT` |

This is a deterministic, current-period, direct balance-sheet equity fact. It is the only
newly accepted mapping in this replay.

### Review candidates are not valuation inputs

Six non-accepted review decisions retained candidate values in the diagnostic artifacts. The
resolver marked each `INSUFFICIENT_STRUCTURAL_SUPPORT`; the case-level gate kept every case at
`data_quality_score: null` and `shadow_disposition: withhold`. These values are listed for
manual investigation only and must not be used as valuation inputs:

| Ticker | Field | Retained candidate value | Reason |
| --- | --- | ---: | --- |
| APD | `commercial_paper` | 126,700,000 | `INSUFFICIENT_STRUCTURAL_SUPPORT` |
| KDP | `commercial_paper` | 4,816,000,000 | `INSUFFICIENT_STRUCTURAL_SUPPORT` |
| NVDA | `marketable_securities_noncurrent` | 43,364,000,000 | `INSUFFICIENT_STRUCTURAL_SUPPORT` |
| ORCL | `noncurrent_debt` | 130,105,000,000 | `INSUFFICIENT_STRUCTURAL_SUPPORT` + `STRUCTURAL_STATEMENT_SUPPORT` |
| TMUS | `commercial_paper` | 6,117,000,000 | `INSUFFICIENT_STRUCTURAL_SUPPORT` |
| UAL | `noncurrent_debt` | 24,294,000,000 | `INSUFFICIENT_STRUCTURAL_SUPPORT` |

SBUX also had one unsupported required `cash` gap. It was explicitly skipped and remained a
blocking field; it was not treated as a parser failure or as a zero.

### Baseline reconciliation and regression safety

The baseline-to-post-fix comparison conserved all 97 decision keys: zero duplicate keys and
zero missing keys. Status transitions were:

| Transition | Count |
| --- | ---: |
| Rejected → rejected | 69 |
| Rejected → unresolved | 17 |
| Review → accepted | 1 |
| Review → rejected | 2 |
| Review → review | 6 |
| Unresolved → unresolved | 2 |

The five-company current-code regression at
`output/structural-xbrl-pilot/results-regression-20260813/` parsed 5/5 files with zero
failures and unchanged fact counts. Its accepted accounting baseline was unchanged: 13
accepted values remained accepted, 2 review decisions remained review, 7 rejects remained
rejects, and 4 prior noisy rejects became explicit `NO_CANDIDATE` unresolved decisions. There
were zero new acceptances in that regression.

The broader input lineage consists of 20 symlinks under
`output/structural-xbrl-broad-corpus/input/`, each resolving to an existing readable JSON
artifact under `output/legacy-fcff-bridge-recovery/<TICKER>/valuation-private.json`. A
non-following file count can incorrectly report zero inputs; follow-links validation was used.

### Positives and limitations

Positive evidence:

- Arelle parsed every staged filing package: 20/20 parsed and zero parser failures.
- The deterministic preferred-equity alias recovered NVDA's zero carrying amount with the
  governed taxonomy and accounting reason codes.
- The case-level shadow gate correctly published no case: all 20 retained material blockers,
  with null data-quality scores and `none_shadow_only` publication effects.
- The focused suite passed, decision keys reconciled, and no production data roots or serving
  artifacts changed.

Limitations:

- No representative case became publishable or valuation-eligible. Arelle's successful parse
  is a parsing success, not proof that the required bridge accounts are unambiguous.
- 96/97 field decisions remained non-accepted; the six retained review values remain
  non-publishable candidates.
- Repeated gaps remain in finance leases, commercial paper, debt, marketable securities, NCI,
  and other bridge fields. The corpus is representative, not the full flagged universe.
- The replay used cached SEC packages and a local pinned Arelle environment; fresh SEC retrieval
  and production integration were not tested here.

### Next boundary

Task 3 is verified, but production promotion is not approved. Task 4 is next: build and run
the full supported 104-company shadow corpus, preserving the same fail-closed rules, exact
lineage, aggregate/stratified reconciliation, and `none_shadow_only` publication boundary.
