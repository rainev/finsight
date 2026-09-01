# Batch 15 Withheld Recovery Result

Status: **user confirmed on 2026-08-30**. The user authorized the one
permitted recovery attempt for LH, ISRG, and ALGN. No Batch 16, tracked serving promotion, merge,
push, or deployment was performed.

## Outcome

- Attempted: **3/3** — LH, ISRG, ALGN
- Recovered Pass: **0/3**
- Recovered Conditional: **0/3**
- Remaining Withheld: **3/3** — LH, ISRG, ALGN
- Final Batch 15: **Pass 4 / Conditional 3 / Withheld 3**
- Final Batch 15 numeric coverage: **7/10**
- Cumulative through 150 issuers: **54 Pass / 87 Conditional / 9 Withheld**
- Cumulative numeric coverage: **141/150**

No company was denied merely because prediction is difficult. Each still has at least one current,
specifically described material claim for which the issuer supplies no amount, allocated reserve,
insurance ceiling, or total loss range.

## LH — DOJ subclaim closed; total legal gate remains open

The official DOJ announcement and agreement close the original missing fact:

- settlement principal: **$14.5M**;
- interest: **4.5% annually beginning 2025-05-14**;
- restitution component: **$8.286M**;
- cutoff arithmetic: 457 days of simple interest = **$816,965.75**;
- principal plus cutoff interest = **$15,316,965.75**;
- principal / $8.6068B reported equity = **0.1685%**.

That amount is immaterial and finite, but it does not cover the rest of the current claim set:

- Ravgen: $272M initial, $100M enhanced, and $2.6M supplemental damages are known, but future
  $100-per-test royalties, pre/post-judgment interest, fees, and other relief lack a filed cutoff
  balance or schedule;
- AMCA multidistrict settlement and Meta Pixel settlement: agreements exist, but no amounts or
  ranges are disclosed;
- Davis/Vargas certified ADA class action and Raymond Eugenio derivative action: damages/relief
  remain unquantified.

The filing's remote/nonmaterial assessment for “other” proceedings is retained but is not used to
erase these specifically described matters. Final blocker: `CLAIMS_UNBOUNDED`.

## ISRG — reserve and insurance do not bound current claims

The corrected owner-cash model and $8.6255B aggregate cash/securities remain economically usable.
Recovery nevertheless fails because the filing states that product-liability losses may materially
exceed recognized amounts and gives no excess-loss range. The SIS appeal, certified da Vinci
antitrust class action, and Restore appeal also have no estimable range.

The $445.5M aggregate current “other accrued liabilities” balance mixes legal and nonlegal items;
assigning a legal portion would be guessing. Current insurance limits and product-claim count are
not disclosed. Old reserves/policies cannot bound 2026 exposure. Final blocker:
`CLAIMS_UNBOUNDED`.

## ALGN — one regulatory cap is not a total-claims cap

Known operating and bridge facts are usable: $1.103B cash, zero revolver borrowings, $31.8M accrued
legal settlements, and $37.514M UK VAT exposure.

The European Commission opened case `AT.40900` on 2026-06-30. Article 23's 10%-of-turnover rule
creates an indicative **$403.4964M** reference using 2025 revenue, but only for a Commission
administrative fine. It does not cap:

- City Smiles and Misty Snow antitrust class appeals seeking treble damages, interest, fees, and
  injunctions;
- Straumann money-damage/post-trial appeal risk;
- EU follow-on private litigation;
- patent/IP remedies across the EU, China, and US ITC;
- future indemnification exposure.

Private-investment upside is not used to offset claims, and unused revolver capacity is not treated
as debt. Final blocker: `CLAIMS_UNBOUNDED`.

## Independent challenge

The first xhigh challenge found three Important evidence-completeness gaps and no Critical defect:

1. LH needed the Davis/Vargas and Raymond Eugenio matters plus the scope of management's “other
   proceedings” assessment.
2. ALGN needed the City Smiles/Misty Snow appeals.
3. ALGN needed exact EU case/date/source provenance and “indicative reference” wording rather than
   implying a guaranteed total maximum.

All three were repaired. The final exact-candidate recheck found **no remaining Critical or
Important issue** and confirmed 0/3 recovered without invented values.

Finsight-efficiency delegation:

- LH research: `gpt-5.6-luna`, High — DOJ agreement plus complete LH claim inventory;
- ISRG research: `gpt-5.6-luna`, xhigh — current reserve/insurance/claim-count exhaustion;
- ALGN research and exact-candidate challenge: `gpt-5.6-luna`, xhigh — SEC/EU/private-claim scope;
- Sol parent: source reconciliation, implementation, deterministic replay, tests, catalog, API,
  bookkeeping, and final synthesis.

## Determinism and verification

- DOJ announcement SHA-256:
  `795f0f003ec869037793dee294aedd97ffb6ae69d997e089a12910eed29e78fa`
- DOJ agreement SHA-256:
  `e2f2883752ed358d285bc49056e03f18b22f5d2dcbd7e757107a760bbb58a2c1`
- Recovery-source receipt SHA-256:
  `3b0655c9104a6cc5c43dc6042d1370780dd883fa505fc02f820f6a1a82381612`
- Final-c/final-d full-tree SHA-256:
  `48af7ce00acd3d146c0dd96949db4a1984823616daf1e862d7a3d821cf756d4b`
- Generated-private tree SHA-256:
  `aca157d11d98b054dfc876ecc7334de5da59abc3930c438997e8d063a81960ed`
- Three recovery public artifacts SHA-256:
  `9e5c50fcfb55f668ad2da81e7938b35f6114e438ec5c1bae4ec0c021a895ea87`
- Exact ten-company final public tree SHA-256:
  `bb035bf21ca11f2122130086d8ca3dd819b645b2e27df6065916dd0847f60da3`
- Recovery report SHA-256:
  `5477c66fdd8bd8421b71c107e8234ea3b2bd22c6e42fdbf2b5e0ed1cce1cd6b7`
- Focused recovery tests: `5 passed`
- Full backend suite: `1,519 passed, 3 skipped, 1 warning`
- Frontend production build: passed (`1,694` modules transformed)

## Real consumer path

- Isolated cumulative catalog: `150` artifacts, Batches 01–15
- Availability: `54 available / 87 conditional / 9 unavailable`
- Publication: `141 review-required / 9 withheld`
- Catalog artifact-tree SHA-256:
  `4692caa4186381fd4a6b0babf7e85dcaa654830ef54c3a982e391d3bda6ad8e7`
- Real localhost FastAPI list: HTTP 200, exact count 150
- Detail/catalog parity: 150/150; exact final Batch 15 parity: 10/10
- Calculator GET parity: 150/150
- Calculator POST: 141 numeric HTTP 200; nine Withheld HTTP 400
- Private leaks: 0
- API receipt SHA-256:
  `7cc2b4756d99ec6dd3ed2ff6e99cd8d03183972a0a3ef440d13c2f0c51e52a55`

The API used an isolated untracked catalog, local auth harness, and `save=false`. Arelle remained
outside the serving process. Tracked serving roots remained unchanged.

## Bookkeeping and confirmation gate

The authorized attempts are consumed:

- Recovery Learning Watchlist: **96** — 87 Conditional / 9 post-recovery Withheld
- Watchlist SHA-256:
  `a1151a5c7c1f2a9856eaabcff0419a764b3e21323d8f01056e0576b5fe093605`
- Cumulative withheld register: **13**, including LH, ISRG, and ALGN
- Withheld-register SHA-256:
  `dd45d9014bf567511f346b52ff1bc5961a2258793a802f6056c4bd8f19880d5d`
- Focused recovery/watchlist/withheld checks after bookkeeping: `11 passed`

The user replied `y` and confirmed the recovery result on 2026-08-30. Batch 16 still requires the
separate signal `Start Universe Reset Batch 16`.
