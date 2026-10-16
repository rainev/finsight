# US700 handoff verification — 2026-10-16

Status: verified for source review and the scoped isolated consumer checks below;
user/partner acceptance still needed. This is not a hosted700 release.

## Observed checks

- The live local manifest digest is
  `45f426fc28f392077813b4e74021363c097b5a80b432811b6b5d751d98c57990`.
  All700 artifact hashes/identities match; the derived public list has exactly
  700 unique companies,574 numerical estimates and126 null results. The old500
  identity set is retained, with200 additions;50 are in expansion16–20.
- Source was copied to a separate clean checkout of the recorded Git base;
  neither original dirty checkout was switched or staged wholesale. MAIN and
  parser implementations remain separate. Private compiled configurations are
  excluded from the outgoing changes and installed only into ignored paths for
  verification. The public receipt pins the copies and separately supplied data.
- Private staging verified the exact archive digest and9,988 file hashes before
  extraction. The package contains no active pointer. No private archive,
  compiled anchors, recipes, SEC cache, credentials, DB export or runtime data
  is part of the outgoing Git tree. Private-data transfer is still pending.
- Actual localhost HTTP through the US router, under ordinary **production**
  catalog validation, returned700 list entries. Every summary base and
  availability matched the frozen artifacts/public list. Selected detail ranges
  matched for MMS,FCN,LSTR,SNX,ICFI,CBT,UTMD,AAPL,AIT. MMS/FCN retained Low warnings.
- Protected calculator POST without a token returned401. Authenticated empty-
  override calculator replay for MMS,FCN,AAPL returned200 and matched their
  frozen low/base/high ranges within runtime floating-point precision. Valid-
  baseline requests for LSTR,SNX,ICFI,CBT,UTMD returned400 unavailable, not409.
- The real worker launched the shipped parser subprocess using explicitly
  synthetic offline metadata and isolated-test permission. Exactly700 outcomes:
  574 checked unchanged,126 prior unavailable,zero source-bound recalculations.
  An inactive candidate preserved all700 entries and574 recipe hashes. Its
  disposable sandbox pointer was unchanged. No SEC request or DB job occurred.
- Clean-base focused regression command:
  `python3 -m pytest backend/tests/test_us_batch_catalog.py backend/tests/test_us_case_assumptions.py backend/tests/test_read_path_snapshot.py backend/tests/test_review_cash_dcf.py backend/tests/test_review_equity_income.py backend/tests/test_data_preserving_startup.py -q -rs -p no:cacheprovider`
  Result: **46 passed,10 skipped**. Skips are the frozen source fixtures required
  by `test_review_equity_income.py`; those private research fixtures are not
  bundled. One existing `crypt` deprecation warning was reported.
- `npm run build --prefix frontend` passed using the existing installed dependency
  tree. Vite emitted its chunk-size warning. No browser UI proof is asserted.
- The outgoing files were checked for personal email/contact strings, machine
  scratch paths, token patterns and compiled/private configuration overlap.
  The inherited provenance utility was redacted; sample `.invalid`/`.com`
  addresses in test/documentation code are not actual credentials or contacts.
- The final staged whitespace check passed after redundant EOF blank lines were
  removed from four copied legacy batch modules; the receipt pins were updated.

## Handoff-only verifier corrections retained as history

1. The sandbox initially denied localhost socket binding. Only the isolated
   verification command was rerun with the required execution permission.
2. The first HTTP harness incorrectly expected a display GET to require auth.
   Existing GETs are public; it now checks the actual protected calculator POST.
3. The first offline harness incorrectly used production mode. Production
   correctly rejected synthetic offline sources. It now uses isolated-test mode;
   no production guard was relaxed, and the separate HTTP test remains production.
4. Unavailable calculator GETs omit `baseline_version`. The harness now obtains
   the native version from the artifact rather than inventing it or accepting409.
   The final check requires400 for unavailable numerical calculations.

No economic input, valuation floor, source date, approval, hold or sealed catalog
was changed to make these handoff checks pass.

## Not proved / deliberately deferred

Full application DB/storage startup, saved valuations, rate-limit persistence,
browser rendering, Linux dependency installation, partner/cloud deployment,
live SEC acquisition, later-filing recalculation, historical corpus/test parity,
AlphaSpread numerical agreement and economic calibration are **not** proved by
these checks. Legacy500 names remain in existing controls/runner filenames.
Private compilation/proof dependencies remain necessary; a clone alone still
uses the tracked100 catalog and cannot serve the private700 baseline.

No live active pointer, Docker service, database, original seal or650/600 rollback
was changed by this source handoff. Review-branch push is distinct from merge,
activation and publication.
