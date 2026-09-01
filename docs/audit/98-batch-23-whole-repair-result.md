# Batch 23 Whole-Conditional Repair Result

Status: **firsthand verified and user-confirmed on 2026-08-31**. The user authorized and confirmed
one repair attempt for all eight Batch 23 Conditional issuers. The confirmed initial candidate and
Audit 96 remain preserved. No tracked serving promotion, Batch 24, merge, push, or deployment
occurred.

## Outcome

- Attempted: **8/8** — AME, CHRW, FDX, PWR, URI, AXON, UPS, LDOS
- Upgraded to Pass: **1/8** — URI
- Still Conditional: **7/8** — AME, CHRW, FDX, PWR, AXON, UPS, LDOS
- Final Batch 23: **3 Pass / 7 Conditional / 0 Withheld**
- Final numeric coverage: **10/10**
- Staged cumulative through 230 issuers: **86 Pass / 135 Conditional / 9 Withheld**
- Staged cumulative numeric coverage: **221/230**

| Ticker | Final result | Low | Base | High | Repair disposition |
| --- | --- | ---: | ---: | ---: | --- |
| AME | Conditional | $48.45 | $104.53 | $173.28 | Final Indicor funding and acquired cash conversion remain absent |
| CHRW | Conditional | $14.80 | $47.48 | $113.04 | Possible loss and collectible insurance outcome remain unresolved |
| FDX | Conditional | $77.03 | $129.24 | $216.22 | No complete post-Freight continuing-company cash history |
| PWR | Conditional | $64.79 | $163.71 | $289.37 | Acquired operating cash and final accounting remain provisional |
| RSG | Pass | $37.80 | $82.81 | $158.64 | Existing source-bounded Pass; not a repair target |
| URI | **Pass** | $0.00 | $12.34 | $165.69 | Exact FY2025/current fleet and other capex closes extraction condition |
| AXON | Conditional | $14.57 | $48.32 | $140.53 | Acquired cash, warrants/convertibles, investments, and claims remain material |
| LII | Pass | $95.16 | $209.60 | $379.78 | Existing source-bounded Pass; not a repair target |
| UPS | Conditional | $30.35 | $61.37 | $124.62 | Transformation savings, volume, tariffs, and pension cash remain unresolved |
| LDOS | Conditional | $49.28 | $116.72 | $236.15 | Post-acquisition contract cash and final integration/debt remain provisional |

## URI repair

The exact FY2025 10-K, accession `0001067701-26-000007`, reports:

- rental-fleet capex: **$4.149B**;
- other PP&E/intangible capex: **$379M**; and
- exact FY2025 total capex: **$4.528B**.

The current 10-Q reports current H1 fleet/other capex of $2.720B/$165M and prior H1 of
$2.121B/$182M. Exact TTM capex is therefore `$4.528B + $2.885B - $2.303B = $5.110B`.
TTM OCF is $5.742B and interest is $715M, producing $1.16968B cash FCFF.

The repair lowers URI's base from $52.31 to $12.34 because exact reinvestment is higher than the
provisional estimate. This is the correct direction: better evidence improved source status but made
the value more conservative. The raw bear residual is negative and the public $0 low remains an
explicit limited-liability floor, not a missing-value substitution.

## Seven retained Conditional results

Each received an explicit attempted repair. None was upgraded because its release condition is an
economic/event state rather than missing arithmetic: final acquisition funding/cash conversion,
claim settlement/insurance, post-spin cash history, realized transformation economics, or final
integration/debt. Their finite ranges remain useful Conditional baselines; promoting them to Pass
would require guessing that those states have resolved.

## Independent challenge

One `gpt-5.6-luna` High reviewer audited all eight release conditions and then independently
challenged the implemented repair. It recalculated URI's FY/H1/TTM capex, OCF, interest, FCFF, DCF,
bridge, raw bear floor, and per-share values; checked all attempt semantics and unchanged values;
and found **0 Critical / 0 Important** findings. The final challenge receipt SHA-256 is
`68fe8846cf3c21ee39a054b67dee51ac460de8be1c17428fe7897709fcf3aabb`.

## Determinism and automated verification

- Repair-source tree SHA-256:
  `8972c46201b3426a12b3b7d21ed5cab0be45aaacdb8ae5c8536aaeb4df349088`.
- Repair A/B byte equality; report SHA-256:
  `35a7a6f21b152cabcd63e2d7a4e96e8d58046c416d45ac24656306bd7a087cd4`.
- Generated-private tree SHA-256:
  `409bb0ec4a3c3b83d414e4f95e4f2c0032b2e78978d7741d26071ecdc51b569d`.
- Staged-public tree SHA-256:
  `f7543ee8ed1907f4d48ee00a5781025a7a655b4516348e28c8178eb2781f5cfb`.
- Focused Batch 23 initial/repair tests: **15 passed**.
- Complete backend suite: **1,460 passed, 3 skipped, 1 warning**.
- Frontend production build: **1,694 modules**, passed.
- `git diff --check`: repeated at the final gate.

## Real consumer path

- Isolated cumulative catalog: exactly **230** artifacts, Batches 01–23.
- Availability: **86 available / 135 conditional / 9 unavailable**.
- Publication: **221 review-required / 9 withheld**.
- Catalog artifact-tree SHA-256:
  `d2e950f81dd59e8da93c1cdc9f2c0828c6017b51b3c5399bbf339c8983db4ce0`.
- Manifest SHA-256:
  `611719659d63ad81ba0b23ad6a5f376c4c19fd784303e3cf252aec0b0e21860d`.
- Real localhost FastAPI: list 230; detail 230/230; calculator GET/default parity 230/230;
  221 numeric POST 200; 9 unavailable POST 400; repaired Batch 23 parity 10/10; private leaks 0.
- API receipt SHA-256:
  `3b2daa8120b90749d2c742cb9c286861e0b51c669a3efbec61fdf2fc0c35fcb8`.
- Arelle remained outside the serving process; the isolated server was stopped.

## Protected state and confirmation gate

- Tracked catalog tree:
  `38efe664dc981e9d2383ece43b66e9ae326b4b9a7cc2443f2463498432ef66a8`.
- Frontend public-data tree:
  `353a14bc672002e88d248811f98d23d4c1fb47cf28e526d969f463f256260274`.
- Generated research tree:
  `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
- Recovery Learning Watchlist is **144** (135 Conditional / 9 Withheld), SHA-256
  `031e1085801adc795fb469c0035f2f93830434aa63ff68ccfb92ce2034b132cc`.
- Automatic-withheld history remains **19**; no company is Withheld after this repair.

The user replied `y` on 2026-08-31. URI was removed from the watchlist as fully repaired. AME,
CHRW, FDX, PWR, AXON, UPS, and LDOS remain bookmarked with
`recovery_outcome=conditional_numeric_low`, recording that this repair attempt was consumed.
Batch 24 was not started; the next valid signal remains `Start Universe Reset Batch 24`.
