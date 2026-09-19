# Latest 500 historical-estimate bridge audit

Reference: the staged 500-company successor catalog
`US-RESET-2026-08-14-B01-B50-LATEST-f96ccaf587561b8bc6960f27` and the
user's request to bridge the uncertainty behind its historical-only labels.

Status: first bridge tranche verified and user-confirmed on 2026-09-19. Checked firsthand on 2026-09-19 against
`assembly-report.json`, `unchanged-verification-v2.json`, the frozen SEC
discovery report and `scripts/verify_latest_unchanged.py`.

## Batch 1 — classification before economics

### Reference

The current staged catalog has 500 rows: 230 are current/checkable outcomes and
270 are intentionally historical-only. A historical label must mean that a
specific newer disclosure remains economically unresolved, not merely that a
large capture wrapper is absent.

### Ours today

- ✔ The 270 historical-only rows consist of 240
  `acquisition_pending_or_failed`, 13 `source_changed`, 10 `targeted_review`
  and seven `event_review` rows.
- ✔ All 240 acquisition rows carry the same public reason: a changed/event
  filing lacks a captured wrapper.
- ✔ The 240 rows contain 33 changed regular filings and 213 companies with
  discovery-listed 8-K events. Twenty-seven have neither condition in the
  discovery report; they were stopped by the broader post-baseline form scan.
- ✔ That broader scan classifies every amendment (`*/A`) and broad registration
  prefixes as potentially material. It therefore swept in 7,407 `424B2`
  filings, 715 `FWP` filings, 34 `SCHEDULE 13G/A` filings and ordinary insider
  amendments. This is a conservative intake rule, not an economic conclusion.
- ✔ Seventeen blocked companies have only ownership, insider or employee-plan
  amendment forms in the post-baseline set. No current-period regular filing
  changed for those rows.
- ✔ Fifty-one latest regular filings changed. Four are source-bound successors;
  13 lack implementation mappings, one is a prior-unavailable case, and 33 need
  source/economic review.

### Reuse check

The existing exact-recipe replay, event-review receipts, filing relationship
logic and isolated candidate assembler are reusable. The missing layer is a
deterministic disclosure-impact decision between SEC metadata discovery and
the expensive full financial capture.

### Flow and backing

The consumer flow currently treats `no full wrapper` as `historical-only`
before asking whether the new form can change financial-period facts, shares,
cash, debt, claims or operating scope. The frozen SEC submissions metadata and
approved recipe replay are sufficient to rule out only narrowly enumerated
non-economic filings; financing, transaction, earnings and ambiguous narrative
events still require their exact documents.

### Gaps

- ✔ **HB-01 P0:** acquisition failure and economic uncertainty are collapsed
  into one status for 240 companies. Separate retrieval state from disclosure
  impact.
- ✔ **HB-02 P0:** `_material_form()` over-flags any amendment and broad
  prospectus family, including third-party ownership and insider amendments.
  Add a versioned issuer-impact classifier; do not weaken integrity checks.
- ✔ **HB-03 P0:** changed regular filings still require exact current source
  binding. No event classifier may promote those 33 rows by itself.
- ✔ **HB-04 P1:** routine financial-institution issuance may be normal model
  activity, but form codes alone cannot prove cash/debt neutrality. It needs a
  family-aware rule plus exact offering terms or an explicit model-policy
  exception.
- ✔ **HB-05 P1:** 8-K Items 1.01, 2.01, 2.03, 2.04, 2.05, 3.02, 7.01 and 8.01
  remain document-review lanes unless a narrower existing receipt proves
  supersession or non-impact.
- ✔ **HB-06 P1:** after classification changes, rebuild one frozen candidate
  and verify all-company API/detail/history/calculator behavior, representative
  frontend labels, database persistence, isolated reload and rollback.

## Verified tranche result

Candidate: `US-RESET-2026-08-14-B01-B50-LATEST-a0a863f945cb84323bf4fcaf`.
It is staged only and was not activated in production.

User confirmation: accepted this exact staged tranche on 2026-09-19. The
confirmation does not activate production or approve the remaining 247
historical-only estimates.

- ✔ Current/checkable numeric estimates increased from 204 to **227**.
- ✔ Historical-only numeric estimates fell from 270 to **247**.
- ✔ The existing 26 unavailable companies remain unavailable; none was given
  an invented value.
- ✔ Twenty-two unchanged values were promoted only through a versioned
  non-economic disclosure rule or exact hash-reviewed no-change event.
- ✔ WMT became the fifth source-bound numeric successor. Its old
  $13.61 / $22.67 / $34.37 range changed to
  $14.49 / $23.74 / $35.60 after current cash, debt and leases, ordinary and
  redeemable NCI, preferred absence and shares were reconciled.
- ✔ KR's current NCI and governance event are source-bound, but its cash/debt/
  preferred bridge remains unresolved. LOW did not share the same current NCI
  mechanism. Neither was promoted.
- ✔ The qualification replay is byte-identical across two runs
  (`6364d40b9d5f24ba18e03a6c9be69d0a95a4f5fee03e1d56cc6dbf0dde3aac4c`),
  and independent assembly reproduced the same candidate ID and manifest hash.
- ✔ Focused regression passed 135 tests; the production frontend build passed.
- ✔ The isolated real API returned 500 companies, exact calculator parity for
  all five source-bound successors, reader/worker reload and rollback.
- ✔ Real redesigned-browser checks showed NOW and WMT as current and BIIB as
  historical. Isolated database save/readback and user scoping passed; the
  application database and production catalog were untouched.

## Remaining exact blockers

- 150 rows still lack a usable complete capture for their changed/event lane.
- 74 captured event rows still need exact economic classification.
- 13 changed regular filings remain source-changed without a validated successor.
- 10 mandatory targeted reviews remain historical-only.
- Prospectus and financing forms remain blocked without instrument and
  settlement evidence; form codes alone do not prove balance-sheet neutrality.
