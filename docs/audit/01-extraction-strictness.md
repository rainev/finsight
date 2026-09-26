# FinSight extraction strictness audit

Date: 2026-08-13  
Scope: US valuation extraction, enterprise-to-equity bridge, and publication gating  
Project profile: analysis — the real thing is the valuation output produced from real issuer data; evidence is source lineage, field-state reconciliation, and checks that the conclusion follows from the observed data.

## Executive finding

**FinSight is too strict on coverage and publication gating, but appropriately strict on provenance and unresolved-value handling. Its policy is also asymmetric: it blocks on many potentially inapplicable bridge fields while allowing a narrow four-account operating-NWC proxy to stand in for issuer-specific working capital.**

The right change is not “treat missing as zero.” It is to separate:

1. whether a fact was reported;
2. whether the account is explicitly zero or not applicable;
3. whether a value is stale, unresolved, proxied, or conflicting; and
4. whether the remaining uncertainty is material to this model’s value.

That would bring FinSight closer to the way serious fundamental-data systems operate: preserve as-reported facts and traceability, add a standardized/normalized layer, use industry-specific fields and footnotes, retain point-in-time/revision lineage, and expose confidence rather than silently filling gaps.

## Evidence ledger

### `✔ firsthand` — current FinSight implementation

- The active XBRL normalizer performs exact configured concept lookup. An unqualified alias defaults to `us-gaap`; there is no active structural discovery of issuer extensions, labels, contexts, dimensions, presentation roles, or calculation relationships in this path. See [`xbrl.py`](</Users/carlosconda/Desktop/Investing Application/backend/app/us_valuation/xbrl.py:96>) and the configured map in [`concept_aliases.json`](</Users/carlosconda/Desktop/Investing Application/backend/app/us_valuation/config/concept_aliases.json:1>).
- The filing-text fallback is intentionally a small, auditable pilot for recurring layouts. Unknown layouts return no resolved value and the caller withholds the field. See [`filing_evidence.py`](</Users/carlosconda/Desktop/Investing Application/backend/app/us_valuation/filing_evidence.py:284>).
- The enterprise-to-equity bridge currently requires ten fields to be present or resolved: cash, two marketable-securities buckets, commercial paper, current and noncurrent debt, preferred equity, NCI, and current/noncurrent finance leases. Missing any required field leaves the bridge incomplete, subject to the aggregate-finance-lease exception. The implementation is in [`xbrl.py`](</Users/carlosconda/Desktop/Investing Application/backend/app/us_valuation/xbrl.py:738>).
- The bridge does distinguish governed filing evidence from ordinary XBRL facts and rejects conflicting resolved evidence. That is a strong control; it should be expanded, not weakened. See [`filing_evidence.py`](</Users/carlosconda/Desktop/Investing Application/backend/app/us_valuation/filing_evidence.py:1214>).
- Operating NWC is currently anchored on accounts receivable and uses receivables, inventory, accounts payable, and current deferred revenue. Missing other components are recorded as absent, but the model uses the four-account proxy. See [`xbrl.py`](</Users/carlosconda/Desktop/Investing Application/backend/app/us_valuation/xbrl.py:689>).

### `✔ firsthand` — observed generated outputs

- The local US artifact set contains 206 valuations: 125 `withheld` and 81 `review_required`; no artifact is currently marked public `pass` in the checked snapshot.
- A local private bridge-recovery sample contains 106 artifacts. 104/106 have an incomplete bridge. Missing-field frequencies in that sample are: finance-lease current 91, finance-lease noncurrent 88, noncurrent marketable securities 79, current marketable securities 66, preferred equity 61, NCI 53, commercial paper 53, current debt 27, noncurrent debt 27, and cash 9.
- Those counts are not proof that every absent field is economically zero. They are proof that an all-fields gate creates a large false-negative surface and that the sample contains ordinary issuers, not only pathological filings. The sample is a legacy recovery subset, not the complete publication universe.
- The individual field states show why one null state is insufficient. AMZN has a current filing-backed commercial-paper zero but missing noncurrent securities and NCI; CAT has current facts alongside stale debt/securities facts; PEP has current debt and commercial paper alongside missing lease fields and stale preferred equity; WMT has current debt/leases alongside stale commercial paper and preferred-equity observations. See representative [`AMZN`](</Users/carlosconda/Desktop/Investing Application/output/legacy-fcff-bridge-recovery/AMZN/valuation-private.json>), [`CAT`](</Users/carlosconda/Desktop/Investing Application/output/legacy-fcff-bridge-recovery/CAT/valuation-private.json>), [`PEP`](</Users/carlosconda/Desktop/Investing Application/output/legacy-fcff-bridge-recovery/PEP/valuation-private.json>), and [`WMT`](</Users/carlosconda/Desktop/Investing Application/output/legacy-fcff-bridge-recovery/WMT/valuation-private.json>) artifacts.
- The existing review queue independently reports 206 generated artifacts, 107 fallback models, 182 classification-confidence values below 0.80, and 192 artifacts with weak SEC provenance. This supports prioritizing lineage and resolver coverage before adding more model sophistication. See [`US-VALUATION-REVIEW-QUEUE.md`](</Users/carlosconda/Desktop/Investing Application/docs/US-VALUATION-REVIEW-QUEUE.md:1>).

### `⚠ external` — standards and public industry methodologies

- SEC Companyfacts is deliberately comparable but limited: it aggregates facts using non-custom taxonomies for the whole filing entity. The SEC separately documents that filers can extend standard taxonomies and that custom tags can reduce comparability. Therefore Companyfacts is a useful fast path, not a complete normalized-fundamentals source. [SEC EDGAR APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces) and [SEC custom-tag trends](https://www.sec.gov/data-research/structured-data/us-gaap-xbrl-custom-tags-trend).
- SEC’s filing data sets include standard and custom taxonomy tags, plus tag metadata such as custom flag, data type, period type, balance, labels, and documentation. [SEC Financial Statement Data Sets](https://www.sec.gov/dera/data/fsds.pdf).
- SEC XBRL guidance expects consumers to identify relevant facts, contexts, dimensions, relationships, supporting properties, and custom concepts, then validate the result. [SEC EDGAR XBRL Guide](https://www.sec.gov/files/edgar/filer-information/specifications/xbrl-guide-2026-06-29.pdf).
- XBRL calculation guidance explicitly warns that missing components should not be assumed to be zero; nil means unknown, while a tagged zero represents an immaterial amount. It also explains why incomplete calculations, dimensions, and extensions make naive derivation unsafe. [XBRL calculation requirements](https://www.xbrl.org/REQ/calculation-requirements-2.0/REQ-2019-02-06/calculation-requirements-2.0-2019-02-06.html).
- Public descriptions from FactSet, S&P Global, LSEG, and Calcbench consistently describe a layered workflow: standardized data for comparability plus as-reported/source-linked data for auditability; annual/interim/LTM or YTD coverage; industry-specific templates; and point-in-time or revision lineage. These are public product descriptions, not a claim about each vendor’s proprietary implementation. [FactSet Fundamentals](https://insight.factset.com/resources/at-a-glance-factset-fundamental-datafeed), [S&P Global Fundamental Data](https://www.spglobal.com/market-intelligence/en/solutions/products/fundamental-data), [LSEG Company Data](https://www.lseg.com/en/data-catalogue/company-data), and [Calcbench numeric-data documentation](https://calcbench.github.io/python_api_client/html/numeric-data.html).

## Where FinSight is stricter than industry practice

| Area | Current FinSight behavior | Public industry/standards pattern | Assessment |
|---|---|---|---|
| Concept resolution | Exact configured aliases; narrow text fallback | Standard fast path plus extension/structure-aware normalization and source traceability | **Too strict for coverage** |
| Missing bridge fields | Ten-field all-or-nothing bridge | Field-level availability, explicit zero/not-applicable handling, model-specific materiality and review states | **Too strict for publication breadth** |
| Currentness | Same-controlling-filing/accession discipline; stale facts are surfaced | PIT data and revision chains are retained; stale/as-reported values are not silently treated as current | **Appropriately strict; keep** |
| Zero inference | Governed zero only when filing evidence supports it | XBRL guidance also rejects missing = zero; good systems preserve the evidence class | **Appropriately strict; extend the state model** |
| Working capital | Four-account NWC proxy; absent components effectively excluded | Standardized data sets and industry templates use broader, sector-relevant components and footnotes | **Too permissive economically / too narrow structurally** |
| Dilution | Cover shares plus reported incremental shares; proxy warning when incomplete | Separate basic, diluted, and award/convertible detail with traceability; quality grades are common | **Reasonable as a graded output, not a universal blocker** |
| Publication outcome | Withhold when bridge is incomplete | Layered outputs: as-reported, normalized, review/confidence, and model-specific usable data | **Too binary** |

## Account-level assessment

| Account | Verdict | Recommended policy |
|---|---|---|
| Cash | Keep as a hard current-period requirement. | Resolve from the controlling filing; permit a documented classification bridge only when cash and restricted cash are clearly distinguished. |
| Current/noncurrent debt | Keep as economically important, but do not require the exact pair of tags. | Resolve from total debt, current/noncurrent rows, debt footnotes, and structurally related concepts. Block only when total financing exposure is unresolved or stale beyond the model’s tolerance. |
| Commercial paper | Current hard blocking is usually too strict. | Accept a current filing-backed reported value or explicit no-outstanding balance; otherwise mark unresolved and apply materiality/sensitivity review. Never infer zero from a blank alone. |
| Marketable securities | The split is too strict when no separate investment balance is evidenced. | Distinguish “no separate securities balance evidenced” from “unresolved.” If an investment balance exists, resolve current/noncurrent classification structurally; if it does not, allow an explicit zero/not-applicable state with provenance. |
| Finance leases | The current aggregate fallback is directionally correct; requiring both split tags when aggregate exposure is known is too strict. | Use aggregate liability for the bridge when current/noncurrent split is not model-critical. If no lease liability is reported after checking the balance sheet and lease note, allow an evidence-backed zero/not-applicable state. |
| Preferred equity | Usually not a universal bridge blocker. | Require evidence when preferred shares or preferred equity are reported; otherwise allow explicit no-preferred evidence or a bounded review state. |
| NCI | Must remain conditional on consolidation economics. | Do not block an issuer with clear no-NCI evidence; do block or review when NCI is reported, material, or structurally ambiguous. |
| Shares and dilution | The existing proxy warning is better than a hard universal stop. | Keep cover-page shares as the denominator anchor; grade missing award/convertible detail and quantify sensitivity where possible. |
| Operating NWC | The 4-account proxy is too generic for production quality. | Add sector/model templates and a materiality flag for other operating current assets/liabilities. Keep the proxy visible and do not represent it as complete NWC. |

## Severity-tagged gap register

### P0 — bridge policy conflates absence with unresolved exposure

**Observed:** ten fields are treated as required for bridge completeness, even though several may be absent because they are inapplicable, not separately disclosed, or only represented in footnotes. The local 106-artifact sample has 104 incomplete bridges.

**Risk:** valid issuers are withheld; users cannot distinguish a missing material debt item from an absent preferred-equity or finance-lease split.

**Required direction:** replace the tuple with field policies and model-criticality tiers. At minimum, distinguish `reported`, `explicit_zero`, `inferred_zero`, `not_applicable`, `not_disclosed`, `unresolved`, `stale`, `proxy`, and `conflict`. `inferred_zero` must always carry the evidence and rule that produced it.

### P0 — active resolver has no structural extension path

**Observed:** exact aliases are the active path; the structural XBRL design exists in [`structural-xbrl-concept-resolution-design.md`](</Users/carlosconda/Desktop/Investing Application/docs/superpowers/specs/2026-08-10-structural-xbrl-concept-resolution-design.md:1>) but is not the active normalizer.

**Risk:** a valid issuer extension, alternate standard tag, dimensional fact, or custom presentation remains unresolved even when the filing contains enough evidence.

**Required direction:** implement the planned Arelle/structural adapter in shadow mode. Candidate acceptance should require multiple signals—namespace/label, documentation, data type/balance/period type, context compatibility, statement role, and calculation/presentation relationships. Label-only matching must remain disallowed.

### P1 — no materiality/sensitivity gate for residual bridge uncertainty

**Observed:** bridge completeness is effectively binary even when an unresolved field may have a small value impact or when a conservative high/low bound could be calculated.

**Risk:** publication coverage is sacrificed without measuring whether the missing item could change the decision.

**Required direction:** calculate a field-specific value range or EV/share sensitivity. Permit `review_required` when uncertainty is bounded and below a documented threshold; reserve `withheld` for unresolved model-critical, high-impact, stale, or conflicting inputs.

### P1 — NWC proxy is globally narrow

**Observed:** the four-account NWC definition omits issuer-specific operating accruals and other current operating assets/liabilities.

**Risk:** the system can be conservative about bridge completeness while under-measuring the actual operating-capital risk in the valuation.

**Required direction:** introduce sector-aware NWC templates and show coverage/omission warnings in the valuation output. Treat the current proxy as a model assumption, not a discovered fact.

### P1 — stale and unavailable facts need separate publication semantics

**Observed:** the artifacts expose states such as `verification_stale`, `missing`, and governed filing facts, but the final gate still collapses their impact into bridge incompleteness.

**Risk:** a reviewer cannot tell whether the next action is “find a current filing,” “look for a footnote,” “accept not applicable,” or “run sensitivity.”

**Required direction:** store freshness age, controlling filing date, source accession, and reason code per field; make freshness thresholds model-specific and visible.

### P2 — dilution completeness is not yet a quantified uncertainty

**Observed:** missing incremental dilution can trigger a warning, but the output does not consistently express the resulting per-share range.

**Risk:** users may either over-trust a cover-only denominator or overreact to a non-material missing award schedule.

**Required direction:** add a dilution sensitivity band and retain the existing proxy warning.

## Recommended target architecture

```text
as-reported facts + filing text + Inline XBRL structure
                    |
                    v
source-linked candidates (including extensions and dimensions)
                    |
                    v
normalized concepts with state/reason/evidence/freshness
                    |
                    v
model-specific materiality and sensitivity gate
                    |
                    v
published / review_required / withheld
```

The normalized layer should never overwrite the as-reported fact. Every accepted candidate should retain accession, filing date, period end, unit, context/dimensions, source URL, and the rule or structural signals used for the mapping.

## Proposed phased work, not yet promoted to the roadmap

1. **Measurement:** rerun the 206-artifact set with field-level reason codes; quantify how many withholds are caused by stale data, missing/inapplicable accounts, unresolved extensions, conflicts, and genuinely material exposure.
2. **Resolver shadow mode:** add structural XBRL candidate discovery and compare it with the exact-alias baseline; no publication behavior changes yet.
3. **Bridge policy:** implement account tiers, explicit-zero/not-applicable evidence, and a sensitivity gate; replay representative issuers including AMZN, CAT, RCL, PEP, and WMT.
4. **NWC policy:** add sector/model templates and a visible completeness score; compare the proxy with full operating-current-account extraction.
5. **Live verification:** exercise the real valuation pipeline on representative issuers, inspect the emitted provenance and warnings, reconcile calculated bridge values to source filings, and obtain user confirmation before calling the change done.

## Scope and limitations

- `✔ firsthand` conclusions are from the repository, current generated artifacts, and the local recovery sample. The recovery sample is not a random sample and should not be used as a population estimate without a complete rerun.
- `⚠ external` conclusions use public SEC/XBRL guidance and public provider methodology pages. Commercial vendors do not disclose every proprietary mapping rule; the comparison is about documented operating patterns, not an assertion that FinSight must reproduce any vendor exactly.
- `⚠ inferred` account recommendations need issuer-level filing validation and replay tests before implementation. In particular, absence of preferred equity, NCI, commercial paper, securities, or leases must not be auto-zeroed solely because a standard tag is blank.
- The `@App-6a3a995dbb348191af64a75893577d60` reference was not resolvable in the local workspace during this audit. The application surface itself is therefore unverified; this report compares the repository’s extraction and valuation pipeline. 
