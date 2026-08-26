# Batch 08 Recovery Result

Status: **verified and recorded**. The user authorized the one permitted recovery attempt for NCLH and APTV. No Batch 09, serving promotion, merge, push, or deployment was performed.

## Outcome

- Attempted: **2/2** — NCLH, APTV
- Recovered Conditional: **1/2** — APTV
- Remaining Withheld: **1/2** — NCLH
- Final Batch 08: **Pass 2 / Conditional 7 / Withheld 1**

### APTV — Conditional recovery

The recovery uses only current and comparative continuing H1 earnings from accession `0001521332-26-000061`; no pre-spin annual cash history enters the model.

- Current H1 parent-attributable continuing earnings: `$427M`
- Prior H1 parent-attributable continuing earnings: `$125M`
- Scenario earnings: `$640.5M / $854.0M / $1,067.5M`
- Multiples: `6x / 8x / 10x`
- Shares: `223.56M / 212.53M / 201.0M`
- Conditional Low value: **$17.19 / $32.15 / $53.11 per share**

The filing's NCI presentation is diagnostic and is not subtracted again from the already parent-attributable continuing-income facts. Retained debt and the spin distribution remain inside the equity-level earnings model; no EV debt bridge is applied.

### NCLH — withheld after recovery

NCLH remains withheld after one attempt.

- Current TTM cash FCFF and the five-year median are negative.
- Carrying debt: `$15.034785B`; gross principal `$15.467745B` is diagnostic only.
- Twelve non-cancelable newbuild contracts: `$18.648354B`.
- Only approximately `$10.9B` of export-credit facilities are committed, while timing/draws and four excluded ships remain unresolved.
- Advance ticket sales remain operating customer funding, not free cash.

A post-pandemic equity-earnings diagnostic is positive, but publishing it would hide the unbounded equity-funding, interest, refinancing, and exchangeable-note dilution burden. The hard stop is `newbuild_funding_and_dilution_unbounded`.

## Challenge and verification

- Independent Luna XHigh challenge found and resolved one Important APTV defect: `IncomeLossFromContinuingOperations` was already attributable to Aptiv, so NCI is not deducted twice.
- Final independent verdict: **PASS; no remaining Critical or Important findings**.
- Focused recovery tests: `3 passed`.
- Complete backend suite: `1,295 passed, 3 skipped, 1 warning`.
- Real FastAPI: list 10/10; detail 10/10; calculator parity 10/10; APTV calculator live; NCLH calculator fails closed; private leaks 0.
- Candidate-c and candidate-d generated trees match: `9218e30f904e5fd6de945de9ef9b84ec686d85d771066b349d4af74e644862e6`.
- Candidate-c and candidate-d public trees match: `cc0cebd8ccc86fc34ce1511949a110f5d37c166725cff5663d3017daefc9c305`.
- API receipt SHA-256: `855bf49673bb4be6e6547752cb350537a76f7137c6a0cd89608f40710d10f7c5`.
- Serving artifacts were unchanged by the recovery run.

## Registers

- APTV is recorded on the Recovery Learning Watchlist as a Conditional recovery.
- NCLH is recorded on the Recovery Learning Watchlist and cumulative withheld register after its one recovery attempt.
- Recovery Learning Watchlist: 43 entries — 39 Conditional, 4 Withheld.
- Recovery Learning Watchlist SHA-256: `544bfcee861bfdd8539182b6a55ef6490580d16078bb72baacfea9f6cbec8d83`.
- Cumulative withheld-register SHA-256: `779b9f79599a998c60cefd6516822d65f70f9056bed15e114a3f472ae4aeb598`.
- Final cumulative universe-reset outcomes through 80 issuers: **Pass 37 / Conditional 39 / Withheld 4**.

Batch 09 requires a separate user signal.
