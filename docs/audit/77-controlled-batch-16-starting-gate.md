# Controlled Universe Reset Batch 16 Starting Gate

Status: **firsthand starting audit complete; implementation authorized by the user**.

Valuation date: `2026-08-14`

## Frozen denominator

Manifest SHA-256: `9b0301327703dd5e5e11dcf80e281bda7eefb8d38ca70f1949ee077dbbd671ad`.

Exactly ten issuers, in frozen order:

| Role | Ticker | CIK | Company | Sub-industry |
| --- | --- | --- | --- | --- |
| Core | A | 0001090872 | Agilent Technologies | Life Sciences Tools & Services |
| Core | DXCM | 0001093557 | Dexcom | Health Care Equipment |
| Core | EW | 0001099800 | Edwards Lifesciences | Health Care Equipment |
| Core | CRL | 0001100682 | Charles River Laboratories | Life Sciences Tools & Services |
| Core | ZBH | 0001136869 | Zimmer Biomet | Health Care Equipment |
| Boundary | COR | 0001140859 | Cencora | Health Care Distributors |
| Core | PODD | 0001145197 | Insulet Corporation | Health Care Equipment |
| Core | ELV | 0001156039 | Elevance Health | Managed Health Care |
| Boundary | VEEV | 0001393052 | Veeva Systems | Health Care Technology |
| Core | IQV | 0001478242 | IQVIA | Life Sciences Tools & Services |

The manifest has eight core and two same-cohort rare-subindustry boundary issuers. All ten are in
the `operating_fcff` partition family, but that partition label does not override economic model
selection: ELV requires an insurer/common-equity route; the other nine first attempt an operating
cash or owner-cash route.

## Reference and governing behavior

The reference is the confirmed workflow in `BATCH-PROCESSING-HANDOFF.md`, Audits 74–76, and the
practical bounded-uncertainty policy in Audits 11–12:

- attempt an ordinary source-bounded Pass first;
- use history-backed Conditional Low only for a named material dependency;
- withhold only for wrong identity/period/unit, unreliable shares, genuinely unbounded claims or
  event state, unsupported model, nonpositive base, or public-safety failure;
- preserve private source/assumption traces and expose only safe public ranges/warnings;
- stop after the initial result for user confirmation.

## Source readiness

✔ Complete reusable SEC packet roots exist for A, DXCM, and VEEV under
`output/difficult-106-sec-source-packets-20260824`.

Prior structural packages existed for:

- A: `output/official-evidence-difficult-106-part-0/packages/A`
- DXCM: `output/official-evidence-difficult-106-part-1/packages/DXCM`
- VEEV: `output/official-evidence-difficult-106-part-2/packages/VEEV`

Execution update: their cutoff-eligible controlling accessions had changed, so none of those older
structural packages was reused as the Batch 16 controlling wrapper. All ten current controlling
filings were captured/parsed once, then reused for deterministic replay.

✔ EW, CRL, ZBH, COR, PODD, ELV, and IQV require targeted cutoff-safe SEC packet and controlling
filing capture. Historical serving JSON is not reusable as Batch 16 evidence.

## Protected baseline

- Tracked catalog tree:
  `38efe664dc981e9d2383ece43b66e9ae326b4b9a7cc2443f2463498432ef66a8`
- Frontend public-data tree:
  `353a14bc672002e88d248811f98d23d4c1fb47cf28e526d969f463f256260274`
- Frontend generated tree:
  `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
- Recovery Learning Watchlist: 96 entries, SHA-256
  `a1151a5c7c1f2a9856eaabcff0419a764b3e21323d8f01056e0576b5fe093605`
- Cumulative withheld register: 13 entries, SHA-256
  `dd45d9014bf567511f346b52ff1bc5961a2258793a802f6056c4bd8f19880d5d`
- Dirty worktree and all prior tracked/untracked work must be preserved.

## Gap register

| ID | Severity | Finding | Evidence status | Required closure |
| --- | --- | --- | --- | --- |
| B16-01 | P0 | Batch 16 code contract does not yet bind the exact frozen denominator | ✔ manifest/code audit | Add immutable contract + exact test |
| B16-02 | P0 | Seven issuers lack Batch 16 cutoff-safe packet/structural outputs | ✔ cache inventory | Reuse 3, capture 7, parse 10/10 |
| B16-03 | P0 | No Batch 16 history/model/bridge decision exists | ✔ repository audit | Build issuer-suitable history-backed outcomes |
| B16-04 | P0 | ELV cannot use an industrial EV debt bridge | ✔ economic-lane audit | Use managed-care common-equity/residual-income route |
| B16-05 | P0 | No independent source/model challenge exists | ✔ repository audit | Challenge exact candidate; repair all Critical/Important |
| B16-06 | P0 | No deterministic, test/build, or real 160-company API proof exists | ✔ repository audit | Replay twice; focused/full/frontend/API verification |
| B16-07 | P0 | No initial Batch 16 evidence report or confirmation gate exists | ✔ repository audit | Record exact counts/values and stop before recovery/Batch 17 |

## Gate

Build only the current Batch 16 phase. Generated evidence remains untracked. Do not mutate the
watchlist/withheld register before confirmation, activate tracked serving data, recover initial
withholds, start Batch 17, merge, push, or deploy.
