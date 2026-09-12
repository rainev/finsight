# Controlled Universe Reset Batch 41 Starting Gate

Date: 2026-09-07
Status: verified starting gate; implementation authorized.

## Frozen denominator

Valuation date: **2026-08-14**. Manifest SHA-256:
`8029d2b9a03ba54d119876aa61ad48b15df8f4c954947337fe1993cb79f393af`.

Exactly ten issuers, in frozen order: APD, AVY, BALL, ECL, EQT, HAL, IFF, IP, NUE, PKG.
The core cohort is resource-cycle Materials/Energy; APD and BALL are the predeclared rare-subindustry boundaries.

## Confirmed predecessor

Batch 40 and its one-attempt COIN recovery are user-confirmed. COIN remains Withheld. The isolated 400-company recovery
catalog has **116 Pass / 271 Conditional / 13 Withheld**. Its manifest SHA-256 is
`9c37cb0be8ec98853475f6b258b1f41abb38ade6a2776a1be259d9a7a10631b2`.

The Recovery Learning Watchlist has 284 entries, SHA-256
`54a9744a54435a0f44ba93c766be436374e6037d5b02b037f7cf092c1a5e950d`. The cumulative withheld register has
23 entries, SHA-256 `d3d8601fcd7c7387622781a7777fae0436cb10171e01b454c73c94d780133992`.

## Required model gates

- APD: industrial-gas operating FCFF with large project capex, project commitments, debt and any completed financing
  reconciled; no unreported project value.
- AVY/ECL: company-history operating FCFF with restructuring, acquisition/disposal, working-capital and reinvestment
  distortions identified and bounded.
- BALL/IP/PKG: packaging-cycle operating FCFF with post-divestiture/current-company scope, debt, capex and container or
  paper-cycle margins normalized from comparable periods.
- EQT: gas-producer resource-cycle FCFF with acquisition scope, commodity/hedge sensitivity, gathering commitments,
  debt and current shares reconciled.
- HAL: oilfield-services resource-cycle FCFF with cycle margins, international exposure, capex, legal claims and debt.
- IFF: specialty-ingredients current-company FCFF with divestitures, impairment/restructuring, pension and debt handled
  once; no discontinued proceeds double count.
- NUE: steel-cycle FCFF with through-cycle margins, large project capex, working capital, debt and current shares.

Every numeric result requires finite ordered low/base/high values and a reliability label. Missing facts remain null;
unbounded model-critical commitments/claims or nonpositive base values remain withheld.

## Protected state

Tracked serving roots at entry using the batch-runner tree-hash contract:

- backend catalog: `ea5e778fb6e4da2ea47bacf90cb813eca24654d1fe8fd62dec9cc3cb102bfe62`
- frontend public data: `5157530c9c4baf3e9d5e6b0455a54579c94a5ead79c07145d9f4d35aef0e7017`
- generated research: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`

Keep evidence untracked. Do not change tracked serving artifacts, root/main, watchlist, withheld register, recover Batch 40,
merge, push, deploy, start Batch 42, or replace any issuer during the initial Batch 41 run.
