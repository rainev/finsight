# Batch 16 Withheld Recovery Result

Status: **firsthand verified strict result; superseded before confirmation by the explicitly
authorized whole-batch repair in [Audit 82](82-batch-16-whole-repair-result.md)**. The user
authorized the one permitted automatic recovery attempt for DXCM, EW, CRL, ZBH, COR, and ELV. Its
0/6 outcome remains preserved as history and the attempt remains consumed. No Batch 17, tracked
serving promotion, merge, push, or deployment was performed.

## Outcome

- Attempted: **6/6** — DXCM, EW, CRL, ZBH, COR, ELV
- Recovered Pass: **0/6**
- Recovered Conditional: **0/6**
- Remaining Withheld: **6/6** — DXCM, EW, CRL, ZBH, COR, ELV
- Final Batch 16: **Pass 2 / Conditional 2 / Withheld 6**
- Final Batch 16 numeric coverage: **4/10**
- Cumulative through 160 issuers: **56 Pass / 89 Conditional / 15 Withheld**
- Cumulative numeric coverage: **145/160**

This was not a refusal to estimate ordinary business uncertainty. Each company has an economically
suitable operating or equity model, but also has at least one current material legal or regulatory
claim with no disclosed total amount, excess-loss range, allocated reserve, or applicable insurance
ceiling. Substituting a known smaller reserve for the complete claim set would understate claims
rather than create a conservative baseline.

## Company decisions

### DXCM

The current filing describes securities, derivative, and six overlapping G6/G7 consumer
class-action groups. It says the outcome of every matter cannot be reasonably estimated and gives
no damages reserve, cap, current insurance limit, or insurance receivable. The $33.5M professional-
fee accrual is not a damages reserve. Final blocker: `CLAIMS_UNBOUNDED`.

### EW

Finite facts include a $56.9M litigation reserve and historical Valtech milestones capped at $350M.
They do not bound PASCAL damages or a permanent injunction, the undisclosed remaining Valtech
balance and ancillary relief, appeals, or tax exposure beyond accruals. The $72.4M combined
litigation-and-insurance reserve overlaps categories and was not double counted. Final blocker:
`CLAIMS_UNBOUNDED`.

### CRL

The First Circuit returned part of the securities-fraud case to district court, and two derivative
actions remain stayed. The current filing supplies no maximum exposure, possible-loss range,
damages reserve, settlement, or applicable D&O insurance ceiling. Final blocker:
`CLAIMS_UNBOUNDED`.

### ZBH

The $137.9M litigation estimate and contingent-payment ranges are finite. They do not cap China
distributor claims beyond accruals or possible additional claims. IRS and foreign-tax audits may
also create material payments with no current adjustment or excess-loss range. Final blocker:
`CLAIMS_UNBOUNDED`.

### COR

The approximately $4.2B opioid accrual is finite for settled matters, including $396.2M current and
the remainder payable over about 13 years. The company cannot estimate losses outside that accrual;
DOJ penalties, private verdicts, and injunctions therefore remain uncapped. Final blocker:
`CLAIMS_UNBOUNDED`.

### ELV

The CMS administrative matter is bounded and closed: $935M original accrual, $342M paid, $593M
remaining, and a disclosed ±$320M adjustment range. The separate DOJ Medicare risk-adjustment
False Claims Act case alleges unspecified payments, remains in discovery, and does not have a loss
range; provider follow-on cases remain separate. Final blocker: `CLAIMS_UNBOUNDED`.

Primary evidence and the exact release-condition audit are recorded in
[Audit 79](79-batch-16-recovery-gap.md). Official public references include the current
[DXCM 10-Q](https://www.sec.gov/Archives/edgar/data/1093557/000109355726000143/dxcm-20260630.htm),
[EW 10-Q](https://www.sec.gov/Archives/edgar/data/1099800/000109980026000043/ew-20260630.htm),
[CRL 10-Q](https://www.sec.gov/Archives/edgar/data/1100682/000110068226000118/crl-20260627.htm),
[ZBH 10-Q](https://www.sec.gov/Archives/edgar/data/1136869/000119312526335044/zbh-20260630.htm),
[COR 10-Q](https://www.sec.gov/Archives/edgar/data/1140859/000114085926000034/cor-20260630.htm), and
[ELV 10-Q](https://www.sec.gov/Archives/edgar/data/1156039/000115603926000060/elv-20260630.htm).

## Independent challenge

Two independent lenses challenged all six decisions:

- `gpt-5.6-luna`, High checked DXCM, EW, and CRL source identity, claim completeness, reserves,
  insurance, and possible recovery routes.
- `gpt-5.6-luna`, xhigh checked ZBH, COR, and ELV, including whether finite subclaims could safely
  cap the complete claim set.

Both returned the same 0/6 recovery result. The final exact candidate has no remaining Critical or
Important classification finding. Known finite subclaims were kept separate from unresolved
claims and were never used as invented total caps.

## Determinism and verification

- Candidate-a/candidate-b full-tree SHA-256:
  `bd7050210a0cfe25217632af0bd4203192f4ade202e327ae002c25677fad1217`
- Generated-private tree SHA-256:
  `e88393a0d28f324d7afafa4865404d81fbaebdff584c4cdc0ab3fd3afaea6afd`
- Six recovery public artifacts SHA-256:
  `50a8f07a191997328897cfa3d4a5e89005dec46dc4de6a1903269ff23bccf3cf`
- Exact ten-company final public tree SHA-256:
  `209d6fd0df84fbff5244f41c1c87499713450519c219664dbaceb7923d712cff`
- Recovery report SHA-256:
  `91c0c77121085d312226aff065552993fd17ad0749b1fef69ec431de1cacd96e`
- Focused recovery tests before bookkeeping: `5 passed`
- Full backend suite: `1,530 passed, 3 skipped, 1 warning`
- Frontend production build: passed (`1,694` modules transformed)
- Focused recovery/watchlist/withheld/catalog checks after bookkeeping: `20 passed, 1 warning`
- `git diff --check`: passed

## Real consumer path

- Isolated cumulative catalog: `160` artifacts, Batches 01–16
- Availability: `56 available / 89 conditional / 15 unavailable`
- Publication: `145 review-required / 15 withheld`
- Catalog artifact-tree SHA-256:
  `0f2a848d0163fd2d2dbba4ddd1a35b5a37e8c158d28ababd5e07b17241f6a398`
- Real localhost FastAPI list: HTTP 200, exact count 160
- Detail/catalog parity: 160/160; exact final Batch 16 parity: 10/10
- Calculator GET parity: 160/160
- Calculator POST: 145 numeric HTTP 200; 15 Withheld HTTP 400
- Private leaks: 0
- API receipt SHA-256:
  `84fb87c8e3c3965bf47af717197650ad49650354af1a2d4f62648e0587958595`

The API used an isolated untracked catalog, local test-only auth harness, and `save=false`. Arelle
remained outside the serving process. Tracked serving roots remained unchanged.

## Bookkeeping and confirmation gate

The authorized attempts are consumed and recorded:

- Recovery Learning Watchlist: **104** — 89 Conditional / 15 post-recovery Withheld
- Watchlist SHA-256:
  `fe1d78b420b63f9c7185e3a673b93d77430321e55c354fb3af7b67ce459638f2`
- Cumulative withheld register: **19**, including all six Batch 16 recovery companies
- Withheld-register SHA-256:
  `28bcfdd2985f3f3d87320e9e780aac630923510d0e46c614d9cfb5035e19f3ec`

The user authorized an exceptional whole-batch repair before confirming this strict result. Audit
82 now owns the active user-confirmation gate; this audit remains the immutable attempt history.
