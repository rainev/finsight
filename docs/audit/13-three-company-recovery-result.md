# Batch 01 three-company recovery result

**Verified:** 2026-08-24 (Asia/Manila)

**Valuation date:** 2026-08-14

**Recovery target:** WDC, DELL, NEE

**Status:** verified — user confirmation needed; no serving promotion authorized

## Outcome first

Recovery succeeded for **2 of 3** companies. Dell and Western Digital now have finite source-
linked Low-reliability ranges. NextEra remains withheld because complete interest-bearing
borrowing makes its bear and base consolidated FCFE nonpositive. Batch 01 therefore improves
from **7 numeric / 3 withheld** to **9 numeric / 1 withheld**. The three-company target was not
treated as a quota.

| Ticker | Before recovery | Recovery low | Recovery base | Recovery high | Final state | Why |
| --- | --- | ---: | ---: | ---: | --- | --- |
| WDC | Withheld | 28.774897 | 42.190826 | 52.780704 | Numeric Low | WDC FY2024–FY2026 continuing states and ten Seagate annual states are issuer-balanced 50/50; discontinued Flash D&A/capex are removed; tax and post-transaction shares are ranged; the current bridge is complete. |
| DELL | Withheld | 37.533831 | 105.970136 | 287.013578 | Numeric Low | Dell-reported adjusted FCF is charged once for the common-equity share of DFS-owned-asset growth under the disclosed 7:1 funding approximation; no later cash/debt bridge is applied. |
| NEE | Withheld | — | — | — | Withheld | Direct Q2 extraction fixed the period defect, but complete long-term plus commercial-paper borrowing produces nonpositive bear/base parent FCFE. |

The other seven Batch 01 values are byte-equivalent to their prior practical results. All nine
numeric results are Low; there are no High or Medium results and no invalid inputs.

## Exact recovery evidence

- NEE Q2: accession `0000753308-26-000060`, filed 2026-07-24, period 2026-06-30.
- NEE FY2025: accession `0000753308-26-000015`, filed 2026-02-13.
- DELL FY2026: accession `0001571996-26-000008`; current Q1 remains
  `0001571996-26-000030`.
- WDC FY2026: accession `0001628280-26-057139`, filed on the cutoff date.
- Seagate cycle facts: ten same-filing annual 10-K states through accession
  `0001137789-26-000159`, all filed by the cutoff.

Recovery source runs B/C are byte-identical with tree hash
`00e5eb9bffa294b6314ae7d005bcbde029a908c90b9ffe61bbe1e71749926b8e`.

## Independent challenge

The Sol High substitute independently recalculated all three routes. Important/Critical findings
were resolved before the final output:

- NEE now includes commercial paper and parent/NCI allocation; candidate common FCFE is
  `-$1.770127bn / -$0.139414bn / +$1.362117bn`, so withholding is required.
- Dell's DFS target debt of `$14.646625bn` reconciles exactly to `$9.139bn` structured debt plus
  `$5.507625bn` allocated core debt. TTM adjusted FCF is `$12.441bn`; terminal-value shares are
  35.6%–53.5%.
- WDC removes discontinued Flash D&A of `$221m/$115m` and capex of `$166m/$139m`; WDC and STX
  each receive 50% weight. Low/base/high use 25%/21%/16% tax and
  398.540944m/383m/367.140944m shares. Terminal-value shares are 23.0%–57.4%.
- WDC's bridge uses `$1.579bn` cash, `$1.052bn` total debt, and zero additional enterprise
  claims after complete structural extraction. Operating liabilities and operating leases are
  not deducted twice.

Final verdict: PASS, no Important or Critical finding remains for Dell/WDC numeric publication
or NEE withholding.

## Determinism, regression, and real consumer evidence

- Final recovery runs A/B are byte-identical with tree hash
  `6af0af0f0c5adc29697c71cbb713e9b1676d80c2a1e5c6b16e34c4b2a892ef73`.
- Final report SHA-256 A/B:
  `6558238e4261b305604524477e85f60e56cf484b3fd2b8b2f948a4e6ae55fcb7`.
- Final focused suite: **108 passed, 3 skipped**.
- Complete backend suite: **1078 passed, 3 skipped**, with one existing Passlib/Python `crypt`
  deprecation warning.
- The 106-company difficult-corpus replay remained deterministic: 104 valid private, 94 source-
  verified, 1 Low numeric, 6 build errors, 4 source-integrity failures, 0 unsafe promotions,
  0 public-contract failures, and no serving changes. Report hash A/B:
  `db42ad8e0fe91487c44971ff0672145ef42b7b45cdd6ddcca036407c9b350f4c`.
- A real localhost FastAPI process returned exactly 10 list items and 10/10 detail HTTP 200
  responses. List/detail range, state and reliability agreed; no private fields leaked; serving
  import loaded zero Arelle modules; clean shutdown.

## Batch 01 learning graduation

Only proven controls were graduated to the Batch 02+ preflight:

1. A latest eligible accession with zero Companyfacts triggers exact filing-package extraction.
2. Material captive-finance activity routes to an equity-level model before any EV debt bridge.
3. A major business change resets cycle history and requires a comparable source-backed range.
4. Capital-intensive FCFE reconciles every interest-bearing borrowing channel, including
   commercial paper.
5. Operating liabilities already embedded in FCFF are never deducted again as financing claims.

These routes remain Provisional and capped at Low; they are not marked Validated by one Batch 01
success. NEE requires a future FPL/NEER specialist SOTP or another economically suitable route;
the failed consolidated FCFE is not softened into a dividend-only value.

## Serving protection and stop gate

Serving roots remain unchanged:

- `backend/app/data/us_valuations`:
  `f68fd4d359e7e20dbf5daff4fddd91caa76d68cf95d3559702d4c80ae53d2c04`
- `frontend/public/data`:
  `5157530c9c4baf3e9d5e6b0455a54579c94a5ead79c07145d9f4d35aef0e7017`
- `frontend/src/research/generated`:
  `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`

Batch 01 recovery is **verified — user confirmation needed**. Stop here. Do not promote, start
Batch 02, merge, or deploy.
