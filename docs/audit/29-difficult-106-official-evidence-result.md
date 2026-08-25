# Audit 29 — difficult-106 official-evidence completion result

Status: **verified — general SEC evidence gate passes; specialist gate remains blocked**

Reference: PLAN Phase 5 and Audit 28's former 101-package blocker.

## Verified source and package completion

- The exact denominator is 106 issuers. All 106 immutable SEC submissions and Companyfacts packets were captured using the user-supplied identification contact without storing that contact in code, reports, or serving artifacts.
- The controller/latest-annual manifest contains 1,422 material requests and 205 unique filing packages. Seven issuers need only one package because the controlling filing is also the latest annual filing.
- Initial acquisition exposed 11 official directories that published XBRL only through `*-xbrl.zip`. Safe bounded ZIP extraction was added with archive-member, logical-URL, source-URL, size, path, and hash controls. All 11 repaired successfully; final failed-package count is zero.
- The final combined ingestion A/B receipt SHA-256 is `b71b32f39b25fddd01e970911ecdfaf0b09dde8649f336d22136c2a3f32e7ea1`.

## Verified evidence results

- All 1,422 requests have explicit outcomes: 308 reported, 87 explicit zero, 135 bounded estimate, four conflicting, and 888 unresolved.
- Selected evidence: 323 current Companyfacts facts, 64 exact structural filing facts, eight consolidated filing-table facts, 116 annual carry-forwards, and 19 company-history ranges.
- Generic peer/sector estimates were rejected from production. Two table candidates without consolidated-title proof were retained diagnostically but not promoted.
- Four current-debt conflicts remain visible and fail closed: CSCO, HPE, LOW, and VRT.
- Table/no-match searches remain unresolved because an empty attachment list is not treated as proof of a complete attachment inventory.
- Policy A/B SHA-256 is `b4c7f68508dc2e609f6947cc837591fa50f5e95590166ad33031ad66ae487e66`; table A/B SHA-256 is `2db320ab99a884a499fc63d4aba8cd3bbf0bff310c0226879b1f77f7d7e7da04`.

## Verified valuation-consumer behavior

- The real `build_us_valuation` consumer executed 106/106 with zero build errors, zero unsafe promotions, zero public-shape changes, and a private evidence trace for all 106.
- Of 530 projectable records, 525 were consumed exactly. Five remained unused because COHR/JCI were safely withheld at source-normalization before bridge arithmetic; unused evidence did not become a public number.
- This generic official-evidence lane remains zero numeric before and zero after. That is not a failure quota: the remaining blockers are model/forecast/economic rather than missing official packages. The separate historical practical replay remains 11 numeric results and is not attributed to this new evidence run.
- Valuation replay A/B SHA-256 is `469aa5e9800487d171b65413d062beed6b369ef97f62af1dc8f6ca421691b910`.

## Verified validation and API

- Restatement ledger: 1,472,634 cutoff-eligible candidates, 29,685 value-change links, zero confirmed restatements because the Companyfacts dimension context is insufficient. A/B SHA-256: `1f031695de8c640aa6bcfe7f84ba8b5a4b343e4622cbdfb21b3e5abad659af20`.
- DQC: 106 controlling filings, 212 canonical rule executions, zero applicable assertions, zero diagnostics/errors, and zero created values. A/B SHA-256: `60d8c5695867e158db1170012ba3cae93af4d4a57f04065af52f36ae2ab6ceff`.
- Real localhost `app.main:app`: list HTTP 200/count 106; 106/106 detail HTTP 200 with exact staged parity; zero private leaks and zero forbidden Arelle/regulator/ingestion serving imports. API A/B SHA-256: `d3fac2071dee1485b2a7475305ab6544760e0018fd26ea8d07de31f2257b2f2e`.
- Complete backend suite: **1,177 passed, 3 optional-capture skips**. Protected serving artifacts remain unchanged.

## Remaining verified blocker

General SEC evidence for the difficult 106 is no longer blocked. Specialist packets remain nonpromotable: FR Y-9C bulk access is blocked, FERC identity/payload/allocation remains unresolved, and Realty Income's SEC supplement lacks a complete immutable AFFO reconciliation. Batch 03, serving promotion, merge, and deployment remain frozen until this evidence is presented and the user confirms the next action.

The controlling machine report is `output/fod6-difficult-106-completion-c.json`, SHA-256 `b8a08738decd52aae6acd5ec50080ccab3442e7722891742264bcc8dc7bdb7e8`.
