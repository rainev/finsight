# Batch 24 Whole-Conditional Repair Result

Status: **firsthand verified and user-confirmed on 2026-08-31**. The user authorized and confirmed
one repair attempt for all six Batch 24 Conditional issuers. The confirmed initial candidate and
Audit 100 remain preserved. No tracked serving promotion, Batch 25, merge, push, or deployment
occurred.

## Outcome

- Attempted: **6/6** — NOC, TDG, GNRC, HII, UBER, ETN
- Upgraded to Pass: **0/6**
- Still Conditional: **6/6** — NOC, TDG, GNRC, HII, UBER, ETN
- Final Batch 24: **4 Pass / 6 Conditional / 0 Withheld**
- Final numeric coverage: **10/10**
- Cumulative through 240 issuers remains **90 Pass / 141 Conditional / 9 Withheld**
- Cumulative numeric coverage remains **231/240**

| Ticker | Final result | Low | Base | High | Remaining release condition |
| --- | --- | ---: | ---: | ---: | --- |
| NOC | Conditional | $88.04 | $212.13 | $410.17 | Stable program/capacity cash and resolved environmental tail |
| TDG | Conditional | $0.00 | $285.06 | $729.50 | Stable acquired cash, final subsequent acquisitions, and materially lower leverage |
| BLDR | Pass | $21.78 | $72.41 | $181.62 | Existing Pass; not a repair target |
| TT | Pass | $98.98 | $200.69 | $347.79 | Existing Pass; not a repair target |
| GNRC | Conditional | $25.43 | $63.46 | $127.39 | Acquired cash conversion and bounded warranty/tariff/channel exposure |
| HII | Conditional | $0.00 | $137.69 | $270.42 | Positive stable shipbuilding post-capex cash and program conversion |
| XYL | Pass | $21.79 | $46.83 | $85.61 | Existing Pass; not a repair target |
| UBER | Conditional | $4.70 | $48.22 | $108.25 | Stable marketplace cash and bounded restricted-fund/claim ownership |
| ETN | Conditional | $42.44 | $104.59 | $193.49 | Complete post-acquisition cash and final funding/accounting/integration |
| ALLE | Pass | $62.13 | $113.45 | $182.54 | Existing Pass; not a repair target |

## Why no company upgraded

The attempt verified that each range is finite and useful, but the remaining conditions are not
mere missing arithmetic. They concern unresolved program cash, acquisition conversion, leverage,
current negative cash, marketplace fund ownership, warranties/tariffs, or final integration.

GNRC received the closest review. Its weak cycle year and current bridge are source linked, but H1
acquisition cash is about 5.6% of base equity and acquired net assets about 9.3%; no acquired
revenue/OCF pro forma is filed, while warranty and tariff/channel exposure remains material. The
independent reviewer therefore would not clear a Pass upgrade, and the candidate correctly retained
Conditional status.

## Independent challenge

One `gpt-5.6-luna` High reviewer audited all six release conditions and the final repair candidate.
It verified exact attempt semantics, unchanged values, public safety, absence of price/target input,
deterministic replay, and unchanged protected state. After GNRC's proposed upgrade was rejected,
the reviewer found **0 Critical / 0 Important** remaining implementation or classification findings.
Challenge receipt SHA-256:
`a3a7456d61a7fd499490274aafb01e976aea0f75176613c9bea5522313be89b1`.

## Determinism and automated verification

- Repair C/D byte equality; report SHA-256:
  `205690d7b064fcf5c94857ece7b1efa09afd09e9a7c138d2e2216c77c5d306a0`.
- Generated-private tree SHA-256:
  `3ee281adb940aa6c6568a7c286d5eb29b84365827d801faedd44abb9d65b3571`.
- Staged-public tree SHA-256:
  `155142b5758c28564b2bbcbfd783c6675d62dcdea4faae43d7e527407d118af4`.
- Focused initial/repair tests: **13 passed**.
- Complete backend suite: **1,473 passed, 3 skipped, 1 warning**.
- Frontend production build: **1,694 modules**, passed.
- `git diff --check`: repeated at the final gate.

## Real consumer path

- Isolated cumulative catalog: exactly **240** artifacts, Batches 01–24.
- Availability: **90 available / 141 conditional / 9 unavailable**.
- Publication: **231 review-required / 9 withheld**.
- Catalog artifact-tree SHA-256:
  `fe6020354dc85a2dfc1c7018b62dd761afb3f4586b803c9ae08a3aa7289173b9`.
- Manifest SHA-256:
  `343d864ca9a80ba45fef8fc504518a7af1d80ffd0cced70cbad36099e90b5d2a`.
- Real localhost FastAPI: list 240; detail 240/240; calculator GET/default parity 240/240;
  231 numeric POST 200; 9 unavailable POST 400; repaired Batch 24 parity 10/10; private leaks 0.
- API receipt SHA-256:
  `cea60703b174a6345bff6b5489ffc0bb0eb4c2f1f12565f9ffe230c4e005a7f0`.
- Arelle remained outside serving; the isolated server was stopped.

## Protected state and confirmation gate

- Tracked serving roots remain unchanged at the Audit 100 hashes.
- Recovery Learning Watchlist remains **150** (141 Conditional / 9 Withheld), SHA-256
  `be9ee2703def565c10737d8323cc3ff313a8c5d86ad77b280e6d687404108e29`.
- Automatic-withheld history remains **19**; no company is Withheld after this repair.

The user replied `y` on 2026-08-31. NOC, TDG, GNRC, HII, UBER, and ETN remain bookmarked with
`recovery_outcome=conditional_numeric_low`, recording that the repair attempt was consumed. The
watchlist count remains 150 because no company upgraded. Batch 25 was not started; the next valid
signal remains `Start Universe Reset Batch 25`.
