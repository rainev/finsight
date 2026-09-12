# Batch 43 DVN/NEM/LYB Recovery Result

Date: 2026-09-07
Status: verified one-attempt recovery result; user-confirmed and recorded.

## Outcome

The one authorized recovery attempt covered exactly **DVN, NEM and LYB**. None can be promoted without inventing a
load-bearing cash-flow or claim assumption. Final Batch 43 remains **Pass 0 / Conditional 7 / Withheld 3**, numeric
**7/10**.

| Ticker | Initial | Recovery | Final | Exact remaining gate |
| --- | --- | --- | --- | --- |
| DVN | Withheld | Not recovered | Withheld | Current pro-forma table has revenue/earnings but no pro-forma OCF, capex, interest or working-capital cash |
| NEM | Withheld | Not recovered | Withheld | Project fair values, assumed liabilities, final NGM ownership and confidential settlement economics are unavailable |
| LYB | Withheld | Not recovered | Withheld | Segment earnings exist, but continuing-company OCF, working-capital cash and capex are unavailable |

## Source-exhaustive recovery findings

### DVN

The controlling 10-Q supplies issuer-filed unaudited pro-forma revenue and net earnings as though Coterra had closed on
2025-01-01: Q2 revenue $8.150B/$6.240B and H1 revenue $13.894B/$12.586B for 2026/2025; H1 net earnings
$2.464B/$2.138B. It also reports $1.3B revenue and $230M earnings from Coterra since the actual 2026-05-07 close.

The filing supplies no corresponding pro-forma OCF, capex, interest or working-capital schedule. Applying legacy Devon
cash-conversion margins to Coterra, converting pro-forma earnings into cash flow, or including the $1B forward synergy
target would invent the cash engine. The reported $5.095B TTM cash-FCFF remains a private partial-combination diagnostic.

### NEM

The filed NGM/Fourmile documents prove a $1.950B Newmont payment after Fourmile contribution, a $1.950B deemed Newmont
contribution, an approximately $3.114935B deemed Barrick contribution, and illustrative 61.5%/38.5% interests before
recalculation. They do not quantify final project fair values, assumed project liabilities, final ownership after the
valuation procedure, retained royalties or the confidential settlement.

Deducting only $1.950B would falsely imply it caps the transaction. Treating deemed contributions as fair value would
also be unsupported. Unknown values remain `null` privately; they never become zero.

### LYB

The current filing proves a $734M sale loss, $310M cash contribution to sold European businesses and $27M H1
discontinued-operation loss, and the earnings materials provide segment EBITDA. It does not provide continuing-company
OCF, working-capital cash or capex after the European sale and refinery discontinuation. Segment EBITDA cannot become
FCFF without unreported tax, capex and working-capital allocations. The reported consolidated $2.020B TTM cash-FCFF
therefore remains a private diagnostic only.

## Challenge and verification

Two Luna High reviewers independently challenged the source and model release gates. Both concluded all three should
remain Withheld. Sol verified the exact pro-forma/event facts, rejected diagnostics, missing-value treatment and public
boundary.

- Initial report pin: `bd0a6b8337bed9adbe22433c12bb894d33992513c1181c9fa8be896506e6bdda`.
- Recovery candidates: `output/batch-43-recovery-run-a-20260907` and
  `output/batch-43-recovery-run-b-20260907`; reports and all private/public artifacts are byte-identical.
- Recovery tree SHA-256: `c4ef3a2875493715a05d8d85915ca118e3759778aa875d8c7de0939d0eeb34f2`.
- Recovery report SHA-256: `a799c2a17874d74a9992c410c342a3411feb734e1c27975178be94a4dba40ad1`.
- Focused Batch 43 initial/recovery tests: **15 passed**.
- Complete backend regression: **1,715 passed, 3 skipped, 1 warning**. The warning is the existing Python `crypt`
  deprecation in passlib.
- Frontend production build: passed, **1,694 modules**.
- Deterministic recovery catalog: **430 companies — 116 available / 294 conditional / 20 unavailable**;
  **410 review-required / 20 withheld**. All 420 predecessor artifacts and all ten final Batch 43 artifacts match
  exactly.
- Catalog artifact-tree SHA-256: `b74f17a983a117890dff9f2829f6a3f424d08a983b1577b043b9ef962aa24e37`.
- Catalog manifest SHA-256: `ddaef526ac4aadea92693d5a4d63da284afe7c4c4e4687428f0eb5828a73b32d`.
- Real cumulative API: **430/430** list/details and **430/430** calculator defaults, exact parity, zero private leaks
  and zero forbidden serving imports.
- Calculator API receipt SHA-256: `8fc33a216cdc6a7ddbf883da8e89d4b6ee9584f6620791010a19c7ded51cde3c`.
- Exact API/import receipt SHA-256: `8d7db4a15ca39b73e66628739b7509121ee9b29f7c8a1ff4b0f2b3718d4d2723`.

## Confirmation and bookkeeping boundary

The confirmed Batch 42 recovery predecessor plus this recovery result remains **430 companies: 116 Pass / 294
Conditional / 20 Withheld**, with **410/430 numeric**. The ten Batch 43 companies are added to the Recovery Learning
Watchlist, and DVN/NEM/LYB to the cumulative withheld register, following user confirmation of this recovery outcome.

The user confirmed the exact result. Bookkeeping is now recorded: the Recovery Learning Watchlist contains **314**
entries (**294 Conditional / 20 Withheld**) with SHA-256
`c714fdf4b4b10ca0584d8f864fc208603c8b11f2cf898920e1369c77a014cbc4`; the cumulative withheld register contains
**30** entries with SHA-256 `05b0a130bbfd3c4acd4568e396e9eaf7da7a1287f1bd81441b504b257cf1265f`.

Existing serving artifacts remain unchanged. Batch 44, merge, push and deployment remain untouched.
