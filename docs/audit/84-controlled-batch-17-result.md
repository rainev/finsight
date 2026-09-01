# Controlled Universe Reset Batch 17 Initial Result

Status: **user confirmed on 2026-08-30**. Exactly the ten frozen Batch 17 issuers
were processed at the 2026-08-14 valuation date. No recovery, watchlist/withheld-history mutation,
tracked serving promotion, Batch 18, merge, push, or deployment was performed.

## Outcome

- Pass: **2/10** — ZTS, STE
- Conditional: **8/10** — ABBV, MDT, MRNA, CI, VTRS, GEHC, KVUE, SOLV
- Withheld: **0/10**
- Numeric: **10/10**
- Reliability: **10 Low / 0 Medium / 0 High**
- Cumulative through 170 issuers: **59 Pass / 102 Conditional / 9 Withheld**
- Cumulative numeric coverage: **161/170**

These are baseline decision ranges, not predictions or recommendations. Low reliability reflects
wide scenario movement. Conditional means a useful number exists but a named event, business-state,
claim, or specialist-model dependency remains material.

## Company results

| Ticker | Outcome | Low | Base | High | Reliability | Simple reason |
| --- | --- | ---: | ---: | ---: | --- | --- |
| ABBV | Conditional | $83.13 | $172.75 | $261.85 | Low | Current standalone pre-Apogee value; signed $10B financing was not closed at cutoff |
| ZTS | Pass | $35.41 | $75.03 | $110.96 | Low | Stable five-year animal-health cash history and complete current bridge |
| MDT | Conditional | $30.52 | $55.41 | $79.21 | Low | MiniMed IPO completed, but Medtronic still owns about 90.03% and consolidates it |
| MRNA | Conditional | $0.00 | $9.54 | $12.72 | Low | Liquid-asset cash-runway baseline; no invented pipeline terminal value |
| CI | Conditional | $94.02 | $191.15 | $363.97 | Low | Managed-care residual income; claims, capital, Evernorth mix, and planned IFP exit remain material |
| STE | Pass | $65.14 | $143.06 | $222.41 | Low | Five-year sterilization/medtech cash history; current debt, claims, NCI, and shares reconcile |
| VTRS | Conditional | $1.05 | $6.46 | $16.71 | Low | Declining portfolio, restructuring, divestitures, patent outcomes, and opioid dispute |
| GEHC | Conditional | $22.06 | $42.63 | $65.41 | Low | Post-spin history plus scoped current-interest repair; tariffs and legal tail remain material |
| KVUE | Conditional | $3.59 | $8.78 | $13.55 | Low | Current pre-Kimberly-Clark standalone value with legacy litigation/indemnities |
| SOLV | Conditional | $0.00 | $36.04 | $76.34 | Low | Recent spin, Acera integration, weak current cash, and Bair Hugger indemnification |

MRNA and SOLV have public bear values of zero only because their raw bear residuals are negative and
the limited-liability floor is explicit. Their base values remain positive. No missing input was
replaced by zero.

## Controlling sources

| Ticker | Accession | Form | Filed | Report period |
| --- | --- | --- | --- | --- |
| ABBV | `0001551152-26-000026` | 10-Q | 2026-08-03 | 2026-06-30 |
| ZTS | `0001555280-26-000040` | 10-Q | 2026-08-06 | 2026-06-30 |
| MDT | `0001628280-26-044354` | 10-K | 2026-06-18 | 2026-04-24 |
| MRNA | `0001682852-26-000150` | 10-Q | 2026-07-31 | 2026-06-30 |
| CI | `0001739940-26-000065` | 10-Q | 2026-07-30 | 2026-06-30 |
| STE | `0001628280-26-054830` | 10-Q | 2026-08-07 | 2026-06-30 |
| VTRS | `0001792044-26-000041` | 10-Q | 2026-08-06 | 2026-06-30 |
| GEHC | `0001932393-26-000046` | 10-Q | 2026-07-29 | 2026-06-30 |
| KVUE | `0001944048-26-000142` | 10-Q | 2026-08-06 | 2026-06-28 |
| SOLV | `0001964738-26-000047` | 10-Q | 2026-08-05 | 2026-06-30 |

## Source capture and replay

- Exact manifest SHA-256:
  `ae4220d7346e650cce3a513166e5c2cde4a2f549e13a50194ef3f0c8e04fe444`
- SEC packets: ABBV/KVUE reused; eight fetched; exact 10/10
- Structural wrappers: ABBV/KVUE reused; eight captured with Python 3.11/Arelle; 10/10 parsed
- Source packet and replay A/B tree SHA-256:
  `cc68c1ad83c8d17e55fe2e605c7addc266cd950152e2d8aa44b2c7a834004970`
- Structural replay A/B tree SHA-256:
  `4e4ec39a4d301f7a9de69083ed53ef569d5bbad585acc54be7bd4fbde9e3b784`
- Initial mixed capture-mode structural tree SHA-256:
  `1a0b86c18ce531cbcbcf48f1d9384b032a9b03f788ced64d633ed49100819a70`
- AbbVie financing-event receipt SHA-256:
  `a8bd26bedfd039ff7973acd79e3e13211b422e64e71b474e032475847f33ab8d`

AbbVie's August 5 8-K reports a signed $10B note offering with approximately $9.93B expected net
proceeds, expected to close on 2026-08-18—after the valuation date. Neither principal nor proceeds
were added at cutoff. The value is explicitly current standalone and invalidates on closing.

## Source and economic challenge

Two separate local challenge passes were performed because subagent delegation was not used in this
run:

1. **Source/mechanics:** reconciled issuer/accession/period, TTM formulas, current shares, cash,
   debt/leases, NCI, recorded claims, and subsequent events. It found and repaired:
   - Viatris's $60M matter was already inside the $303M legal/professional accrual; the duplicate
     deduction was removed.
   - AbbVie's cutoff 8-K and $27.495B contingent-consideration liability were missing from the
     private event/claim diagnostics. The financing is now correctly pre-close and the liability is
     traced as an after-payment cash-conversion dependency rather than silently ignored or deducted
     twice.
2. **Economic/public:** independently recalculated every DCF, residual-income state, MRNA runway
   state, sensitivity direction, calculator family/default, public/private boundary, and exact
   ten-company parity.

Final independent challenge receipt:
`00cb9905b5bdba058265ffb25afc2814ba27de569a059c102381bac0bf94f90e`
— 10/10 challenged, 0 Critical, 0 Important.

## Determinism and automated verification

- Candidate-e/candidate-f full-tree SHA-256:
  `ec3de174f115c5029b7c998b18bc285331977d77f2f8554e85dabb6bb7816286`
- Generated-private tree SHA-256:
  `73c83fa54b2ca408aeeb279c5fe0ddc012cdca0dafed9eea0517d873e009cae9`
- Staged-public tree SHA-256:
  `0b035575437c989401c7e98730f85010b10d3cf8008eaaebda9c36e7e4c189a8`
- Final report SHA-256:
  `5481b413a1a1e1f93ad67cb478c350c23d83338f92e1a87eff0cf619eb25d48e`
- Focused Batch 17 tests: `9 passed`
- Complete backend suite: `1,546 passed, 3 skipped, 1 warning`
- Frontend production build: passed (`1,694` modules transformed)
- `git diff --check`: passed

## Real consumer path

- Isolated cumulative catalog: 170 exact artifacts, Batches 01–17
- Availability: 59 available / 102 conditional / 9 unavailable
- Publication: 161 review-required / 9 withheld
- Catalog artifact-tree SHA-256:
  `8d600204536ff298142cf1fb2910aa2801c4ae722b28efe7ff6b19c128921338`
- Real localhost FastAPI list: HTTP 200, exact count 170
- Detail/catalog parity: 170/170; exact Batch 17 staged parity: 10/10
- Calculator GET parity: 170/170
- Calculator POST: 161 numeric HTTP 200; nine unavailable HTTP 400
- Batch 17 model families: eight operating / one managed-care equity-earnings / one asset-runway
- Private leaks: 0
- API receipt SHA-256:
  `b3f59cf828fe967b328922c8abb44e3e967dc1a112cdf286e0a8f70fc188afe0`

The API used an isolated untracked catalog, a local test-only auth harness, and `save=false`. Arelle
remained outside the serving process. Tracked serving roots stayed unchanged.

## Protected state and confirmation gate

- Recovery Learning Watchlist: 111 — 102 current Conditional / 9 post-recovery Withheld; SHA-256:
  `4e240453662d70a282797e85b1ef66c668adb68ca15d7e90492a3ea8d185a137`
- The eight direct Conditional companies were added with `recovery_outcome: not_applicable`;
  MRNA and SOLV retain explicit equity-at-risk status. ZTS and STE were not added.
- Cumulative automatic-withheld history remains 19; SHA-256:
  `28bcfdd2985f3f3d87320e9e780aac630923510d0e46c614d9cfb5035e19f3ec`
- Tracked valuation catalog, frontend public data, and generated research roots are unchanged.

The user replied `y` and confirmed this exact Batch 17 result on 2026-08-30. There are no Batch 17
Withheld companies, so no recovery phase is needed. Batch 18 remains untouched and requires the
separate signal `Start Universe Reset Batch 18`.
