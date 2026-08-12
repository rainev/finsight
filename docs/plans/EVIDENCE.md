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

Task 3 remains verified. Task 4 is now also verified below; production promotion is still not
approved.

## Task 4 — full supported 104-company shadow corpus

Status: **verified — your confirmation needed**. The corrected run is shadow-only and did not
change production valuation inputs, serving artifacts, or publication gates.

### Corpus, parser, and ledger reconciliation

The auditable manifest contains 125 flagged snapshots: 104 supported US-GAAP 10-K/10-Q cases
were included and 21 were excluded with recorded reasons. The included corpus contains 100
Form 10-Q and 4 Form 10-K cases across 13 business archetypes. Its immutable corrected output
is:

```text
output/structural-xbrl-full-corpus/results-accounting-fix-20260813/
```

| Metric | Corrected result |
| --- | ---: |
| Discovered / eligible / parsed | 104 / 104 / 104 |
| Parser failures / skipped | 0 / 0 |
| Manifest requests / unique decisions | 545 / 545 |
| Missing / duplicate / extra decisions | 0 / 0 / 0 |
| Accepted / review / rejected / unresolved | 2 / 42 / 353 / 148 |
| Publish / lower-confidence candidates | 0 / 0 |
| Withheld cases | 104 |

All 104 reports have `data_quality_status: fail`, `data_quality_score: null`,
`shadow_disposition: withhold`, and `publication_effect: none_shadow_only`. Nine unsupported
required `cash` gaps (BIIB, CSX, ILMN, MDLZ, PG, QSR, SBUX, TGT, and WAB) remain explicit
blockers. Review values are diagnostics only; rejected and unresolved decisions carry null
values and no non-accepted value entered a valuation input.

Arelle retained 6,619 fail-closed numeric diagnostics—6,414 inexact numeric values and 205 nil
facts—while producing zero parser failures. These warnings represent facts intentionally
skipped rather than accepted with unsafe precision or imputed values.

### Accepted accounting results

Independent accounting review approved the only two accepted decisions:

| Ticker | Field | Value | Source concept | Confidence |
| --- | --- | ---: | --- | ---: |
| NVDA | preferred equity | 0 | `us-gaap:PreferredStockValueOutstanding` | 0.98 |
| EXPE | noncontrolling interests | 1,260,000,000 | `us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest` with exact NCI member dimension | 0.96 |

The corpus audit caught and corrected two initially unsafe acceptances before this evidence was
approved:

- HPE preferred equity zero is now rejected because the same filing and period contain nonzero
  preferred-instrument evidence. The stable reason is
  `PREFERRED_ZERO_CONTRADICTED_BY_INSTRUMENT_EVIDENCE`.
- RTX's USD 28 million NCI-inclusive temporary-equity fact is no longer a preferred-equity
  alias and is not accepted.

The correction also removed redeemable-NCI review noise for APH, LIN, WMT, and XYL. DE and T
remain review-grade and therefore withheld; DE is conservatively safe but its embedded evidence
is liability-like and should become a future hard economic-class rejection. WDC remains governed
by the separate five-company pilot: its accepted parent-attributable temporary-equity carrying
amount is zero, while its USD 265 million liquidation preference remains non-selected.

### Regression and independent review

```text
Focused structural suite: 341 passed in 6.26s
Full backend suite: 484 passed, 3 skipped, 1 pre-existing unrelated failure
```

The sole full-suite failure remains
`test_microsoft_public_artifact_contains_no_raw_financial_amounts` with missing
`automated_review`; neither its production code nor test was changed here. Independent resolver
review approved the implementation after the HPE/RTX corrections, and independent corpus
reconciliation confirmed all 545 decision keys and all case gates. The final accounting audit
also approved the corrected output for shadow-only use, with one important traceability caveat:
HPE's corrected rejection row has `evidence: null`; the companion preferred-share evidence that
triggers the rejection remains visible in the pre-correction artifact and regression tests, but
a future report format should retain that triggering companion evidence directly. The corrected
20-company control remained byte-for-byte unchanged: 97 decisions (1 accepted, 6 review, 71
rejected, 19 unresolved) and all 20 cases withheld.

### Remaining boundary

Task 4 proves parser reliability and fail-closed accounting behavior across the full supported
104-company boundary. It does **not** make any of those 104 cases publishable: every case still
has at least one material blocker. Production promotion remains unapproved. The next engineering
work is to eliminate recurring high-value deterministic mapping gaps—starting with clearly
liability-like preferred-equity review noise—then rerun eligibility before considering any live
valuation integration. HPE companion-evidence traceability is separately parked in the
production backlog; it does not change the safe rejection or shadow-only result.
