# Controlled Batch 03 initial result

**Valuation date:** 2026-08-14

**Frozen denominator:** LYV, ECHO, NWSA, GOOGL, TTD, DIS, APP, FOXA, TKO, PSKY.

## Exact result

- Attempted: **10/10**.
- Numeric: **3/10**, all Low reliability.
- Withheld: **7/10**.
- Invalid, skipped, or replaced: **0/10**.
- Serving artifacts changed: **no**.
- Recovery Learning Watchlist changed: **no**.

| Ticker | Initial outcome | Low | Base | High | Reason if withheld |
| --- | --- | ---: | ---: | ---: | --- |
| LYV | Withheld | — | — | — | Live-events route, event cash, NCI, leases, and convertible dilution remain unsupported |
| ECHO | Withheld | — | — | — | Deconsolidation/disposal, spectrum economics, debt, and NCI are unbounded |
| NWSA | Numeric Low | $4.7732 | $23.8816 | $35.1111 | — |
| GOOGL | Withheld | — | — | — | $707bn purchase commitments lack a mutually exclusive timing/cash-conversion schedule |
| TTD | Numeric Low | $19.6927 | $36.0989 | $54.4099 | — |
| DIS | Numeric Low | $29.7502 | $64.7467 | $127.9021 | — |
| APP | Withheld | — | — | — | Current 2026 capex is absent; the available $4.776m capex fact is from 2024 |
| FOXA | Withheld | — | — | — | Next-twelve-month contractual/other commitments exceed modeled bear cash coverage |
| TKO | Withheld | — | — | — | Capex/rights cash series, material NCI, and share contexts remain incomplete |
| PSKY | Withheld | — | — | — | Successor history, share conversion, debt, and ownership allocation are noncomparable |

## Source and model evidence

- All ten submissions/Companyfacts packets were captured immutably; APP reused its verified
  difficult-106 packet and nine issuers were fetched once.
- All ten controlling filing packages parsed successfully outside the serving process.
- Class-A identities were retained for NWSA, GOOGL, and FOXA; PSKY's successor identity matched the
  frozen CIK/ticker.
- GOOGL's obsolete zero bridge was removed: current preferred equity and VIE NCI are recognized as
  nonzero claims even though the company remains withheld for commitments.
- NWSA's bear state covers $573m of obligations due within twelve months and excludes $1.002bn of
  unclassified/non-liquid long-term investments from cash.
- DIS excludes $7.627bn of generic long-term investments from cash; current content balances fell
  versus the prior annual date, and customer performance obligations are not treated as cash debt.
- TTD's hashed Note 11 table reports $939.124m total commitments. Its bear cash state includes a
  $266.1744m first-year stress and does not double-count operating commitments as bridge debt.

## Challenge and corrections

The first candidate was rejected for stale APP capex, missing forward-commitment evidence, and an
unproven DIS investment bridge. The second candidate was rejected because TTD's narrative Note 11
commitment table escaped structural XBRL. All Critical and Important findings were resolved.
Final Luna-High adversarial verdict on candidate-g: **PASS**.

## Determinism and regression

- Batch 03 manifest SHA-256:
  `09734cc4804691dcfcef3f1fa6ab87f8953052666787b944600f7f3c5f527890`.
- Source-packet tree SHA-256:
  `45ddd012ccceb38426d8d012f18454fde89619556cb3750d15509a1ff19e7a77`.
- Structural-source tree SHA-256:
  `647e7ef16e357c05e16b3ee30bf86afb251c164e86e2c640dfd86cc7d7150e21`.
- Candidate-g/candidate-h byte-identical tree SHA-256:
  `53892cbae003e315cbfb368f0366c5747c499db90125011a37c7a17486b5c6c3`.
- Batch report SHA-256:
  `7aeb88e4260d743401148962ebcdb39b64903e813220b42a1979765510de8f70`.
- Focused Batch 03 tests: **6 passed**.
- Complete backend suite: **1,198 passed, 3 skipped, 1 warning**.
- `git diff --check`: passed.

## Real API

The real FastAPI application served the staged Batch 03 directory on localhost port 8765:

- list HTTP 200, exact count 10, exact staged parity;
- detail 10/10 HTTP 200 with exact staged parity;
- private leaks 0;
- forbidden Arelle/official-ingestion/specialist serving imports 0.

API receipt SHA-256:
`cf17a59ffcf3fbf11b15074ffeff8f1c966d565bc2fff3d0d0e0b9219e4784f9`.

## Gate

Initial Batch 03 is technically verified; user confirmation is required. Stop before recovery,
Recovery Learning Watchlist mutation, Batch 04, serving promotion, merge, or deployment.

