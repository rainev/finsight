# Controlled Universe Reset Batch 16 Initial Result

Status: **user confirmed on 2026-08-30**. Exactly the ten frozen Batch 16 Health Care issuers were
processed at the 2026-08-14 valuation date. Initial processing changed no bookkeeping. After
confirmation, only the two direct Conditional issuers were added to the Recovery Learning
Watchlist. No recovery, cumulative-withheld-register mutation, tracked serving promotion, Batch 17,
merge, push, or deployment was performed.

## Result

- Pass: **2/10** — VEEV, IQV
- Conditional: **2/10** — A, PODD
- Withheld: **6/10** — DXCM, EW, CRL, ZBH, COR, ELV
- Numeric: **4/10**, all Low reliability
- Cumulative after 160 processed issuers: **56 Pass / 89 Conditional / 15 Withheld**
- Cumulative numeric coverage: **145/160**
- Recovery Learning Watchlist: **98** after confirmation; A and PODD were added with recovery
  outcome `not_applicable`
- Cumulative withheld register: **13**, unchanged pending the authorized one recovery attempt

| Ticker | Outcome | Low | Base | High | Reliability | Controlling filing / period |
| --- | --- | ---: | ---: | ---: | --- | --- |
| A | Conditional | $33.37 | $65.73 | $103.86 | Low | `0001090872-26-000055` / 2026-04-30 |
| DXCM | Withheld | — | — | — | — | `0001093557-26-000143` / 2026-06-30 |
| EW | Withheld | — | — | — | — | `0001099800-26-000043` / 2026-06-30 |
| CRL | Withheld | — | — | — | — | `0001100682-26-000118` / 2026-06-27 |
| ZBH | Withheld | — | — | — | — | `0001193125-26-335044` / 2026-06-30 |
| COR | Withheld | — | — | — | — | `0001140859-26-000034` / 2026-06-30 |
| PODD | Conditional | $20.95 | $68.16 | $133.34 | Low | `0001145197-26-000169` / 2026-06-30 |
| ELV | Withheld | — | — | — | — | `0001156039-26-000060` / 2026-06-30 |
| VEEV | Pass | $139.90 | $202.84 | $285.90 | Low | `0001393052-26-000026` / 2026-04-30 |
| IQV | Pass | $58.07 | $153.56 | $230.18 | Low | `0001628280-26-050211` / 2026-06-30 |

Values are USD per-share baseline decision ranges, not predictions or recommendations. No missing
claim, interest, capex, or share value was replaced with zero.

## Frozen contract and source gate

The frozen order is A, DXCM, EW, CRL, ZBH, COR, PODD, ELV, VEEV, and IQV. The manifest has eight
core and two boundary issuers, with no replacement or skipped ticker. Its SHA-256 is
`9b0301327703dd5e5e11dcf80e281bda7eefb8d38ca70f1949ee077dbbd671ad`.

- SEC packets: A, DXCM, and VEEV reused; seven were fetched after cache preflight.
- Structural parsing: 10 attempted / 10 parsed / 0 failed. Older packages for A/DXCM/VEEV used
  prior accessions, so all ten current controlling wrappers were captured once.
- Every controlling filing and Agilent's separate June 25 debt-event 8-K were filed by the cutoff.
- Source replay A/B reused all ten with zero fetches and matched:
  `7a65bd073780063b16d053d5a4ee530b0a51ae9757a473cb94972da27e2d64e3`.
- Structural replay A/B reused all ten and matched:
  `5badafb31810ff582ee6d51671c22f836301de3878cf3ed7de2a47448ef0f7ad`.
- Agilent debt-event receipt SHA-256:
  `6bdde0099a2788a277e075ab23394f82d478246b8d43603084ea8530ae476464`.
- Protected tracked serving roots remained unchanged.

## Outcome decisions

- **A Conditional:** five-year cash history and the operating bridge are complete. The cutoff bridge
  adds June's $600M notes and 99.968% gross issuance proceeds once. The pending approximately $950M
  Biocare acquisition remains separate from current standalone value; no acquired cash is invented.
- **DXCM Withheld:** securities, derivative, and G6/G7 device class actions seek damages and relief,
  while the filing says their outcomes cannot be reasonably estimated.
- **EW Withheld:** PASCAL patent, Valtech milestone, and tax matters can materially affect a period,
  with no finite excess-loss range beyond recorded reserves. The $244.1M long-term investments,
  including a $39M held-to-maturity component, are classified and conservatively excluded rather
  than silently treated as surplus cash.
- **CRL Withheld:** the securities class action and related derivative actions have no reasonably
  estimable maximum exposure or loss range.
- **ZBH Withheld:** China distributor claims may exceed current accruals and materially affect
  results; IRS/foreign tax adjustments also have no current finite range. The stale interest path
  was identified but is not used to manufacture a withheld value.
- **COR Withheld:** the $4.2B opioid accrual and $396.2M current portion are traceable, but losses for
  opioid matters outside the accrual cannot be estimated and ultimate loss may differ materially.
- **PODD Conditional:** four comparable post-transition annual periods, cash, debt/leases, and shares
  reconcile. The reversed EOFlow award is not credited. The July Hu securities action has a reported
  zero accrual because loss is not considered probable, but no loss range; the result is therefore
  numeric only at Low reliability.
- **ELV Withheld:** an insurer/common-equity residual-income route is economically suitable and the
  CMS administrative range is finite, but the separate DOJ Medicare risk-adjustment False Claims Act
  lawsuit alleges unspecified payments and can create material liability beyond current accruals.
- **VEEV Pass:** debt-free owner cash deducts current software reinvestment. The stale PP&E tag and
  $267.2M interest-income misclassification are not used. Cash/AFS securities, no debt/NCI, shares,
  and the $90M/$70M Ostro acquisition trace reconcile.
- **IQV Pass:** current cash/securities, $16.081B debt, NCI, shares, $200M acquisition cash, $240M
  acquired net assets, $26M contingent/deferred consideration, and $114M H1 restructuring reconcile.
  The filing calls the acquisitions immaterial and management does not expect pending matters to be
  materially adverse; restructuring remains inside source history and cash conversion.

## Independent challenge and repairs

The source High and model xhigh lenses initially found one Critical and several Important issues.
Repairs were:

- move EW and ELV to Withheld for unbounded current claim sets;
- include Agilent's post-balance-sheet $600M note liability and $599.808M gross proceeds once;
- classify EW's recorded reserve and excluded long-term financial assets;
- add ZBH's tax-audit exposure to its hard-stop reason;
- trace PODD's Hu action, VEEV's Ostro acquisition, and IQV's acquisitions/restructuring;
- reconcile COR's current and total opioid accruals;
- retain correct share units/periods and complete debt/NCI/preferred treatment.

The exact final-c recheck found **no remaining Critical or Important finding**.

Finsight-efficiency delegation:

- source/event/claim inventory and final lineage check: `gpt-5.6-luna`, High;
- economic route, assumption, arithmetic, and exact-candidate challenge: `gpt-5.6-luna`, xhigh;
- Sol parent: implementation, source reconciliation, deterministic replay, tests, catalog, real API,
  and final synthesis.

## Determinism, tests, build, and real API

- Final-c/final-d full-tree SHA-256:
  `ea2f2da1378924f9a5ea4054f3393001241dd89483e2d4f506b727a5226d1522`
- Generated-private tree SHA-256:
  `aa8bbf07e25bc671648a62cf76c027429b5f32a289b20056d99c9458d0fbd729`
- Staged-public tree SHA-256:
  `5588ff26c959749c61a001fab9f1c4e5a00a7de466f52e7c95a335fc3ce4bc3b`
- Final report SHA-256:
  `9e06770e13fbf523b7a0512f11f40a85a62a57083c1f7aa0d7a0449525567959`
- Focused Batch 16 tests: `6 passed`
- Full backend suite: `1,525 passed, 3 skipped, 1 warning`
- Frontend production build: passed (`1,694` modules transformed)
- Isolated cumulative catalog: `160` artifacts, Batches 01–16
- Catalog availability: `56 available / 89 conditional / 15 unavailable`
- Catalog publication: `145 review-required / 15 withheld`
- Catalog artifact-tree SHA-256:
  `eae1eee5f79dd01b201f73804eb8260c858d5368152c3f9ff3b2f7af2648d105`
- Real localhost FastAPI list: HTTP 200, exact count 160
- Detail/catalog parity: 160/160; exact Batch 16 staged parity: 10/10
- Calculator GET parity: 160/160
- Batch 16 numeric calculator routes: four operating-family
- Calculator default POST parity: 145 numeric HTTP 200; 15 Withheld HTTP 400
- Private leaks: 0
- API receipt SHA-256:
  `e8bc7c84941b427d1e41001666b880d00a76148964155274d2666ea490329d19`

The API used an isolated untracked catalog and local auth harness with `save=false`. Arelle remained
outside the serving process. This is real HTTP list/detail/calculator behavior, not tracked serving
promotion or production persistence.

## Confirmation and recovery gate

The user replied `y` and confirmed the initial result on 2026-08-30. A and PODD were added to the
Recovery Learning Watchlist as direct Conditional results with recovery outcome `not_applicable`.
DXCM, EW, CRL, ZBH, COR, and ELV remain outside the watchlist and cumulative withheld register
until their separately authorized one recovery attempt is complete.

- Watchlist: 98 entries — 89 Conditional / 9 post-recovery Withheld
- Watchlist SHA-256: `5b24fad7fe85d25d5ab4d81188cc2ac22fc775acb9236d99ff9c23ea7a0e1fc0`
- Cumulative withheld register: unchanged at 13 entries, SHA-256
  `dd45d9014bf567511f346b52ff1bc5961a2258793a802f6056c4bd8f19880d5d`
- Focused Batch 16/watchlist/withheld confirmation checks: `12 passed`

The next valid signal is:

The user authorized that recovery and then an exceptional whole-batch repair. The strict 0/6
attempt remains preserved in [Audit 80](80-batch-16-recovery-result.md); the active verified result
and confirmation gate are now [Audit 82](82-batch-16-whole-repair-result.md).

Do not start Batch 17, register the six initial Withheld companies, promote, merge, push, or deploy
before the recovery gate.
