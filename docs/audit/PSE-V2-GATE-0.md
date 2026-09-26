# PSE V2 Gate 0 — source and contract readiness

**Checked:** 2026-09-21  
**Status:** partial — local source set verified; external commercial-use terms remain unconfirmed.

**Phase A confirmation:** The user confirmed the staged eight-company Phase A result on 2026-09-21. This does not
confirm source licensing, activation, deployment, recovery, or Phase B expansion.

## Verified locally

- The pilot set is frozen at eight ordinary common-equity issuers.
- AP, SCC, BDO, AREIT, ALI, and AC have multi-period local filing corpora with document SHA-256 hashes and page-level
  extracted candidates.
- ACR and PERC have captured FY2025 Form 17-A source documents with verified hashes.
- The routing, output/status contract, dated macro snapshot, and immutable staged catalog formats are versioned.
- Existing corpus validation remains authoritative: unreviewed or missing specialist inputs produce blocked/null
  artifacts rather than inferred values.

## Current evidence outcome

- **AP:** provisional FCFF estimate using the reviewed legacy normalized-FCFF snapshot; segment revenue/capex remain
  incomplete and are disclosed as warnings.
- **SCC, ACR, PERC, BDO, AREIT, ALI, AC:** blocked until their listed specialist inputs complete human review.

Phase A.1 now publishes a separate provisional `market_relative_only` range for those seven issuers. Their specialist
intrinsic scenarios remain null, and the exact limitations above remain attached to each artifact.

## Unresolved external checkpoint

PSE/EDGE and any market-data provider's automated access, storage, and redistribution terms have not been confirmed
inside this repository. Phase A uses existing local source files only and makes no network acquisition claim. Automated
fetching and public raw-fact display remain blocked until those terms and source samples are approved.
