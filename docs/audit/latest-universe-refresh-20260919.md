# Latest 500-company refresh — September 19, 2026

Status: staged successor verified in isolation; user confirmation pending.
Production is unchanged. Only four companies have source-bound current
successors; all other limitations remain explicit below.

## Staged successor result

Immutable candidate:
`output/latest-universe-20260919/release-candidate-final/f96ccaf587561b8bc6960f27`.
It contains exactly 500 public artifacts and 474 exact private recipes. Nothing
was activated in production.

Current source-bound successors:

| Company | Prior low / base / high | Staged low / base / high | Reliability | New filing date |
|---|---:|---:|---|---:|
| BBY | 12.6585776623648 / 49.81875697263778 / 92.26031700070399 | 15.01470977114916 / 52.398544079643955 / 101.34217579293927 | Low | 2026-09-04 |
| COO | 6.726903765240069 / 25.386746111007653 / 45.11554360720105 | 6.810437902835488 / 25.846727853089796 / 52.26979882100007 | Low | 2026-09-09 |
| GILD | 47.814576621348 / 84.83355650735321 / 142.23827451110367 | 49.76389279190312 / 85.84042124873433 / 142.4802187449659 | Low | 2026-08-06 |
| INCY | 39.53829408784563 / 76.77527520525082 / 142.64357455245997 | 45.54251943713704 / 84.0120917937754 / 153.51383538106904 | Low | 2026-07-28 |

Disposition counts: source-bound 4; verified unchanged 200; prior unavailable
preserved 26; changed financial source needing further work 13; targeted review
10; event review 7; acquisition/evidence pending or failed 240. Every company is
present in `assembly-report.json`; retained numeric values are explicitly dated
historical estimates and are not relabelled current.

Real isolated verification passed: API list count 500; exact default calculator
parity for all four successors; reader pin/reload; worker reload; rollback;
database migration/save/readback/user isolation; frontend production build; and
browser checks for current versus historical status, BBY dated history, and an
edited discount rate (10% to 11%) recalculating BBY base from $52.40 to $47.87,
then resetting to the official value. Production was not touched.

## Final metadata catch-up (supersedes the initial discovery counts below)

All 500 submissions were rechecked after one fixed acceptance timestamp,
`2026-09-19T08:40:23+00:00` (4:40:23 PM Manila). Final discovery now identifies
**51 changed regular filings and 259 companies with event/amendment flags**.
KR's September 18 filing `0001104659-26-108926` was newly found; additional event
accessions were found for DASH, HBAN, LII and STZ. Raw original evidence remains
unchanged. Final source capture is under `final-discovery/`, reusing earlier
hash-checked immutable filing bodies only when fresh selection is identical.

The isolated exact-recipe API sweep on port 4187 verified all 500 list/detail
and default calculator outcomes with zero errors; receipt is
`output/latest-universe-20260919/migration-http/http-sweep.json`.
It verifies historical integration, not final successor acceptance. The temporary
server was stopped after verification. Targeted suites: 96 passed; calculator/API
suites: 12 passed; baseline-membership registry tests included in those runs.

## Frozen scope

- Original 500 identities from `US-RESET-2026-08-14-B01-B50-INITIAL-1.0`.
- Separate runtime: `output/latest-universe-20260919/runtime`.
- Discovery: 500 submissions captured; 50 different latest annual/interim filings;
  257 companies with event/amendment flags. Flags are not economic validation.
- Capture snapshot timestamp: `2026-09-18T20:21:38.303635+00:00`
  (September 19 in Manila), with the September 19 date cutoff.
- Preserve prior approvals, historical artifacts and existing unrelated work.
  No activation, scheduling, merge, push or deployment.

## Verified implementation checkpoints

1. Historical migration command rerun on the real 500-company baseline:
   **474/474 numeric recipes migrated, zero migration gaps**. The 33 repaired
   shapes reuse pure cash-schedule/enterprise engines: 25 AFFO, 5 utility FCFE,
   2 compact enterprise and 1 distribution model. Historical replay is not a
   current-filing update. Focused migration tests: 12 passed.
2. Recompiled policies: **307 contracts**, fingerprint
   `5c3c66fef5b6e791c5b5948985dffaa6252e638146c91b17752a2454f69c8b13`.
   This remains contract compilation, not source validation.
3. Optional unavailable SEC ZIP retrieval falls back to individual resources;
   retrieved corrupt/unsafe archives still fail. Filing-package tests: 34 passed.
   Real HON annual capture subsequently succeeded.
4. Acquisition now writes deterministic gzip checkpoints, checks packet hashes
   on reuse, limits outstanding work to two jobs, and refuses new captures below
   5 GiB free disk. Cached structural versions use existing parser/identity/date
   ranking; equal-ranked conflicting bytes remain an error.
5. Offline verifier accepts both compressed and original latest capture receipts
   and validates discovery, descriptor, identity and packet hashes. Combined
   loader, annual-policy and group-verification tests: 15 passed.

## First real latest-capture calculation diagnostic

Receipt: `output/latest-universe-20260919/runtime/source-validation/90e54c57f92ef442691c6504eb36dcd9b65861fd019840417c179abdd149abaf/report.json`.

| Company | Result | Low / base / high |
|---|---|---|
| GILD | Source-bound diagnostic; independent normalization review pending | 49.88609345338426 / 85.94581650290266 / 142.4802187449659 |
| AAPL | Event review required | No successor issued |
| INCY | Event review required | No successor issued |
| BIIB | Legal carrying/payment/recovery, comparable Apellis cash and RayThera cutoff blockers retained | No successor issued |

GILD predecessor: 47.814576621348 / 84.83355650735321 / 142.23827451110367.
This is an unchanged-filing recalculation, not successive-quarter evidence.
No candidate from this diagnostic has been activated or declared release ready.

## Commands and remaining gates

Resume capture (existing receipts are hash-checked and reused):

```sh
python3 scripts/capture_latest_500.py
```

Offline selected-company diagnostic:

```sh
python3 scripts/verify_us_refresh_sources.py --runtime-root output/latest-universe-20260919/runtime --capture-root output/latest-universe-20260919 --as-of 2026-09-19 --ticker GILD
```

Still required: complete source capture/inventory; resolve compatible refresh
mapping groups and targeted economics; reassess the 26 unavailable companies;
assemble one frozen 500-company successor; exact before/after recommendations;
frozen regression, full API/calculator/history, browser, actual database,
resume/failure/replay and isolated activation/reload/rollback verification.
The acquisition report is a live progress receipt, not the final release report.

## Targeted findings during the latest capture

- **AAPL:** independently challenged and checked against the original private
  lineage. The same-filing diagnostic moves the range from
  `79.80130329911236 / 103.3303976983317 / 123.1625608382377` to
  `87.44317404534581 / 107.3745809737621 / 123.59698206267868` because the adapter
  changes approved bridge uncertainty and tax normalization. This is not a new
  filing effect. Retain the approved baseline; keep the diagnostic separate.
- **ADI:** primary 8-K `0001193125-26-394361` states completed issuance of four
  note tranches totaling $3B after the quarterly period. Cash proceeds/uses must
  reconcile before a current bridge update. The separately announced Alif deal
  remains pending; its price and contingent maximum are not current liabilities.
- **ADSK:** primary 8-K `0001193125-26-387877` describes $1B notes and intended
  repayment of a term loan. Intent is not proof of repayment. The August
  acquisition loan is subsequent to the July balance-sheet date even though
  described in that 10-Q; disclosure presence is not balance-sheet inclusion.
- **BBY:** current debt table reports $1.169B including $32M finance leases,
  reconciling to $11M current plus $1.158B noncurrent. The fair-value table's
  commercial paper is an investment asset, not an issuer debt claim. Other-
  current investments and deferred-compensation assets must not be silently
  called unrestricted surplus cash. Approved cash-only scope is under review.
- **DELL:** failed annual parse came from an identity-incomplete historical
  structural JSON, not co-registrant ambiguity. Parent's local Arelle replay of
  the immutable raw annual filing produced 1,705/1,705 facts with DELL's CIK.
  Capture selection now excludes identity-incomplete structural candidates;
  parsed payloads validate before installing a new cache. Full capture retry is
  still required, with old evidence retained.

Current work state is generated by `scripts/build_latest_refresh_register.py`.
It requires source-diagnostic implementation, policy and wrapper hashes to
match; a historical success does not remain current after an implementation
change without rechecking. No current successor catalog has been issued.
