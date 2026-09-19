# WG32 — MCK public contract-evidence discovery and acquisition

Narrow official-source/floor/blocked-contract gate user-confirmed 2026-09-16;
not a completed MCK refresh or release. WG31 confirmed; not a
completed MCK refresh or pipeline release. Public SEC and official MCK discovery/
retrieval authorized only for Apollo/MMS preferred, PRISM/Core put and component
evidence eligible through 2026-08-14. No paid/private sources or release actions.

## Audit and bounded specification

| ID | Severity | Verified delta | Acceptance | Status |
|---|---|---|---|---|
| WG32.1 | P0 | Current cache lacks earlier put-floor/component documents | Discover exact official documents and cutoff identities | DISCOVERY VERIFIED |
| WG32.2 | P0 | Official documents need immutable local hashes | Bounded official retrieval, hashes, provenance and replay | VERIFIED; CONFIRMATION PENDING |
| WG32.3 | P0 | Contract terms vs event/accounting statements | Independent economic classification; no intrinsic-value inference | VERIFIED NARROW; CONTRACT GAP RETAINED |
| WG32.4 | P0 | Runtime/history preservation | Frozen workers, regression and isolated API | IN PROGRESS |

## Firsthand official-source discovery

- SEC 10-Q accession `0000927653-25-000107`, filed 2025-08-06, period
  2025-06-30, primary `mck-20250630.htm`: Core 30% put every five years **with
  a floor of 75% of initial fair value**. PRISM retained20%, but only25M was
  classified redeemable; no full PRISM put formula. [SEC filing](https://www.sec.gov/Archives/edgar/data/927653/000092765325000107/0000927653-25-000107-index.htm).
- SEC 10-Q accession `0000927653-26-000017`, filed 2026-02-04, period
  2025-12-31, primary `mck-20251231.htm`: repeats Core cadence/floor and quarterly
  Monte Carlo adjustments, not model inputs or exact exercise windows.
  [SEC filing](https://www.sec.gov/Archives/edgar/data/927653/000092765326000017/0000927653-26-000017-index.htm).
- SEC 10-K accession `0000927653-26-000069`, filed 2026-05-08, period
  2026-03-31, primary `mck-20260331.htm`: annual component rollforward/fair-value
  changes and planned Apollo transaction, but no executed preferred terms.
- Official MCK announcement dated 2026-04-20: Apollo proposed1.25B convertible
  preferred/approx13% and approx13B **transaction enterprise valuation**. This is
  an event descriptor, not MCK intrinsic value, subsidiary common value, current
  carrying claim, conversion ratio or parent dilution.
  [MCK announcement](https://investor.mckesson.com/news/financial-news/2026/McKesson-Signs-Agreement-with-Apollo-Funds-for-Strategic-Minority-Interest-in-Medical-Surgical-Solutions/default.aspx).
- SEC DEFA14A accession `0000927653-26-000182`, filed 2026-06-30, primary
  `mck-20260630.htm`, investor deck `a260604_mckinvestordeck202.pdf`: strategy/
  event material, not identified executed preferred/LLC or put agreement.
  [SEC filing](https://www.sec.gov/Archives/edgar/data/927653/000092765326000182/0000927653-26-000182-index.htm).
- SEC 8-K accession `0000927653-26-000167`, filed 2026-06-12, primary
  `mck-20260609.htm`, Exhibit10.1: MMS credit agreement amendment/term loan B,
  not preferred or put agreement. Do not infer instrument terms from it.
  [SEC filing](https://www.sec.gov/Archives/edgar/data/927653/000092765326000167/0000927653-26-000167-index.htm).

No captured/public search result supplied executed Apollo/MMS preferred subscription/
purchase or governing LLC agreement, PRISM put provisions, Core detailed pricing/
window terms, or June30 per-instrument reconciliation/workpaper. The bounded
official inventory is captured/reviewed; unpublished/private evidence may exist.

## Acquisition implementation and blocker

Reusable `capture_public_contract_evidence.py` accepts explicit label/date/URL,
allows only official HTTPS hosts, enforces frozen cutoff, safe unique labels,
20MB limit, bounded retries, governed redirects, immutable writes, hashes and
cached readback. Unit integrity checks: **2 passed in 0.05s** (host/scheme/cutoff/
label/contact rejection; immutable reuse/tamper rejection). It writes no economic
approval and sets `economic_validation=false`.

Initial acquisition was rejected because contact egress was not separately
approved. User explicitly approved 2026-09-16; no fake contact/workaround used.
Second attempt captured **6/6**, and cached replay revalidated exact official
URL/date/type/cutoff identity:

| Label | Bytes | SHA-256 |
|---|---:|---|
| Core Q1 2025 | 1,537,233 | 81c781908a0b21267762ea5fc263be1daec52d4e410feedb21d8811933eb7278 |
| Core Q3 2025 | 2,094,495 | a98f673330d7f867cfbd638f5343e24193245057995492769dcebcab70945bf4 |
| MCK annual 2026 | 3,136,637 | aa9f07b0f4e3fb615830597ddff27c3439bc85a787cb816493b3fa8dd4bd377a |
| MMS investor deck | 1,102,047 | 6297dbda709c0e1615b88d4e6c7d92dd937164b6539bbfca340963fee9826087 |
| DEFA14A cover | 13,662 | 9baa5d8760b99aa9470a0ebaa3a41627381486386e95d17f93f88ac3123ab9fd |
| Official announcement | 59,399 | f53d2618aece0d0c5807e27ab15186a062c566696e7230869541d69de3ce87c4 |

Capture report SHA-256 `e9a1620a3ab4457672150302f4010002acdeb0b85a0aa76a478938d31f977b95`;
private receipt SHA-256 `feb7e9ade6856dd313e43327d2586bc0fb2d5665162988c11c84f53b106f0990`.

## Verified financial meaning and current runtime

- Two vintages agree on Core30%/five-year/75% initial-fair-value floor. Initial
  Core RNI700M gives **525M arithmetic floor**. First exercise date/formula/current
  component remain None. This is lower-bound evidence, not claim adjustment.
- Annual historical evidence separately reports87M fair-value adjustment and
  122M Core redemption adjustment; neither is added to current carrying.
- Later omission is not source-proven revocation or current exercisability.
- Apollo1.25B/approx13%/approx13B enterprise transaction value stays event
  descriptor—not intrinsic value/current claim/conversion/parent dilution/cash.
- Investor deck12-page native-text inspection found no instrument contract terms;
  page3 strategy/EPS content visually rendered. Proxy cover only links the deck.

| Company | Retained low / base / high | Exact changes | Reliability |
|---|---:|---:|---|
| MCK | 477.99247723179093 / 849.8325771275278 / 1262.3562145555925 | 0 / 0 / 0 | Low |
| LHX control | 69.08352051394239 / 152.4724672181145 / 263.63410016487416 | 0 / 0 / 0 | Low |

Both main rows remain implementation_gap; no numeric successor/unavailable
conversion. Focused public/capture/ownership/payment set55 passed13.51s.
Independent initial7 passed3.26s; primary added exact source identity guard;
final independent8 passed3.29s, no correction. Frozen two-worker report
`output/us-refresh-group-verification/3c17504f66f459760b09d156f59c2d46108e2824a79b8cff6842b9053907a3c9/report.json`,
SHA-256 `28c81aa8fb221284c18bc24e975ed3c7b036d6731604dce903c9d2c68a4b943b`;
implementation `e2d305e21eb0195f3a5be1fdecf1319c4858650bad194ca57913aa64b8246df5`,
policy `494de6ed28a66235da15d5c6d9027dd0e73057f99a75717db3bdee7f65ccbdc3`.
Repeated current report byte-identical. Real isolated six-company PostgreSQL API/
calculator parity passes, receipt SHA-256
`7cba107478a2c95a6deba33d7da9b5bbece3fd967af0c8350837ce1bcf3d7456`.
No UI/save/model behavior changed; browser/save/activation/reload/rollback not
repeated/claimed. Final stable broad: **749 passed**, one existing Passlib crypt
deprecation warning, **229.98 seconds**. Command:
`PYTHONPATH=backend:. pytest -q backend/tests/test_refresh_*.py backend/tests/test_public_contract_capture.py backend/tests/test_calculation_recipe.py backend/tests/test_batch_28_history.py backend/tests/test_batch_26_history.py backend/tests/test_batch_21_history.py backend/tests/test_batch_14_history.py`.
Diff check/pycompile pass; HEAD remains
`4fa0a64e7b7a684a87c5732a03fde1680c88d622`. Narrow gate user-confirmed.
No release/Git/paid/private/tuning action or full MCK refresh.

Current register:440 companies/419 historical recipes;282 compiled instructions,
137 implementation gaps,196 financial flags,168 source flags,436 needs-recheck,
zero current full numeric/successive certifications. Flags overlap, not percent.

## Following working group, not started

WG33 should review governed aggregate RNI carrying treatment: bind ordinary376M
and redeemable2563M exactly once as current common-equity bridge claims; keep
Core525M floor/Apollo1.25B/13B descriptor/redemption movements/proceeds entirely
nonadditive and prohibit parent dilution. Reclassify only if legal/cash conditional
bridge and every prior burden remain value-neutral and explicit. This is a
reviewed accounting-proxy decision, not contract intrinsic valuation; preserve
all cash/funding/legal/component/prior-company blockers. No later work started.
