# Structural bridge resolver verification evidence

Status: **verified — your confirmation needed**

Date: 2026-08-12 (Asia/Manila)

## Scope and tested commits

- Task 6 implementation checkpoint: `1544335 fix: harden structural bridge resolution`
- Independently reviewed follow-up: `432e9db fix: classify structural relationship roles safely`
- Mapping policy: `US-XBRL-RESOLVER-1.1`
- Publication effect: `none_shadow_only`
- Production valuation inputs and serving artifacts were not changed.

The verification used cached filing packages only. No SEC refresh was requested, expected
values were not supplied to the resolver, and all generated pilot files remain untracked
under `output/structural-xbrl-pilot/`.

## Automated verification

At approximately 2026-08-12 23:41 PST:

```text
pytest -q backend/tests/test_structural_xbrl_schema.py \
  backend/tests/test_concept_resolver.py \
  backend/tests/test_arelle_adapter.py \
  backend/tests/test_filing_package.py \
  backend/tests/test_structural_shadow.py \
  backend/tests/test_structural_xbrl_integration.py

314 passed in 6.18s
```

```text
pytest -q backend/tests

457 passed, 3 skipped, 1 failed in 7.50s
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
output/structural-xbrl-pilot/results-run23/
```

Summary: [results-run23/summary.json](../../output/structural-xbrl-pilot/results-run23/summary.json)

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

Independent Luna High reviews identified and then confirmed closure of cross-role
contamination, unsafe relationship-role inference, commercial-paper dimensional policy,
and failure-evidence ordering. The final bounded closure review was clean.

## Remaining boundary

This verifies deterministic extraction and classification for the five-company pilot. It
does not approve production promotion, prove universe-wide coverage, or change any public
valuation. The next safe step is user confirmation followed by a broader shadow-only
company corpus before production integration is considered.
