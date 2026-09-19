# WG40 — BIIB appealed judgment and post-Apellis operating-cash scope

Started 2026-09-19 after WG39's two candidate result was user-confirmed. Cached
evidence only, Batches 01–44. This is a verified blocked-update gate, not a
current BIIB successor or pipeline release.

## Acceptance status

| Item | Result |
|---|---|
| $273.5M recognized acquisition claim | VERIFIED SOURCE-BOUND ONCE |
| $124.3M Genentech appealed judgment scope | VERIFIED BLOCKER |
| Apellis transaction cash/funding/current bridge | VERIFIED PARTIAL LEDGER |
| Comparable post-Apellis operating cash | BLOCKED — not filed |
| Apellis integration cash | BLOCKED — payments are not exclusively scoped |
| Pending RayThera cutoff status | BLOCKED — narrative not machine-bound |
| Frozen workers, independent challenge, regression and isolated API | VERIFIED; CONFIRMATION PENDING |

## Genentech legal result

The controlling 10-Q is accession `0000875045-26-000075`, period
`2026-06-30`, filed `2026-07-29`; raw structural SHA256
`0192005db66f4df7762a6707586217e55e0b6fcc7c6b0b76fc9939df6ab4cdf7`.

The filing reports a **$124.3M** November 2025 judgment and says the appeal is
pending. The XBRL fact is disclosure-only
`LossContingencyDamagesSoughtValue`, context `c-801`, Genentech litigation
member. It is not a balance-sheet liability or payment.

The current filing supplies no separately scoped:

- Genentech carrying accrual;
- judgment interest;
- legal cash payment;
- insurance recovery/receivable;
- indemnification asset; or
- appeal probability or possible-loss range.

The H1 $4.3M litigation expense is aggregate and cannot be assigned to
Genentech. Generic accrued liabilities and indemnification language cannot fill
the gap.

The prior judgment sensitivity is therefore retired from current refresh logic:

| Scenario | Old legal overlay | Source support |
|---|---:|---|
| Bear | $124.3M | Judgment amount exists, but current carrying treatment does not |
| Base | $62.15M | Unsupported 50% probability |
| Bull | $0 | Unsupported 0% probability |

The $124.3M remains private exposure evidence. It is neither probability-
weighted nor promoted to a current claim.

## Acquisition claim and current bridge

The acquisition liability is separate and source-bound:

- current contingent-consideration total: **$273.5M**;
- narrower Level-3 balance: **$269.4M**;
- Apellis purchase addition inside the total: **$4.1M**; and
- legal judgment not added.

BIIB now has an explicit common-equity/preferred-zero proof. Parent equity
$18.848B reconciles exactly from common stock, APIC, retained earnings, AOCI and
treasury stock; preferred is **$0**. Compiled scenarios source preferred from
that bridge and subtract the $273.5M acquisition claim once. Historical mixed
preferred-slot values remain history diagnostics only and cannot double count.

Current bridge:

| Component | Amount |
|---|---:|
| Cash | $1.285B |
| Current / noncurrent AFS securities | $0 / $0 |
| Current secured debt | $800M |
| Noncurrent notes/term loan | $7.2903B |
| Total debt | **$8.0903B** |
| Preferred / NCI | $0 / $0 |

The historical recipe stored $7.2903B debt; a future source-bound successor must
use the complete $8.0903B bridge.

## Apellis transaction and operating scope

| Evidence | Amount |
|---|---:|
| Total consideration | $5.4101B |
| Cash consideration paid/payable | $5.406B |
| Cash acquired | $310.7M |
| Reported net acquisition cash | $5.0651B |
| Consideration timing difference | $30.2M |
| New term-loan funding | $2.0B |
| Revolver funding | $400M |
| SYFOVRE / EMPAVELI reported revenue | $97.4M / $30.4M |
| Apellis integration charge | $153.2M |
| Current workforce restructuring payments | $153.5M |

The $153.5M payments use a generic workforce-reduction dimension and cannot be
assigned solely to Apellis. The filing says the short post-close Apellis impact
was immaterial and therefore omits pro-forma operations. It reports no acquired
OCF, capex or FCFF and no quantified synergy amount. Immaterial six-week
contribution does not prove immaterial future cash or make pre-close annual
history comparable.

RayThera's proposed transaction remains narrative-only and its cutoff-close
status is not captured. The initially inspected $225M/$775M XBRL rows use TJ Bio
dimensions, so WG40 correctly removed them from RayThera machine provenance;
numeric fields remain null until a correctly hashed narrative rule exists.

## Company result

| Company | Historical low / base / high | WG40 successor | Exact official change |
|---|---:|---:|---:|
| BIIB | 30.820572961480448 / 122.45052291592471 / 272.12004639095767 | None | 0 / 0 / 0 |

The historical Low range remains available as dated history, not a current
successor. Current calculator publication remains blocked.

GILD and INCY preserve their exact WG39 candidate ranges:

- GILD `50.84725647933317 / 90.53884458037521 / 155.4654607530073`;
- INCY `49.655920876512866 / 96.2418217177929 / 150.63899303483984`.

## Verification

Private WG40 receipt:
`output/us-refresh-runtime/biib-scope/BIIB.json`, file SHA256
`f31b668aab3c4b6ecbf66a40166ec56d94caf3e24f252cc02d6000eb66a1b131`,
internal receipt hash
`5261ef73bdc3d7864d95581b72cb47da4d2604a22c1befe7aa5437a9090ef7f3`.

Frozen two-worker report:
`output/us-refresh-group-verification/1b4a3324e9778951201b565fc9c1d3e838abaedddd90132a75fb8f4fb17e2fd1/report.json`.
It deterministically reproduces one BIIB source/economic review plus the two WG39
candidates; file SHA256
`ea70247a578ba66fa7911522063339de5fbadee49c87249660d5ef37ee3fd078`.
Policy SHA256 `bb9d4ab16e2113734ef216b78c07b34e5d272ba02bad024bd1bc0828300e1885`.

Direct source-validation report:
`output/us-refresh-runtime/source-validation/3a947cdb8dbf5bdc23c52a45a224b6c6bb3462f4f70e4bb54a5499ba8071efd0/report.json`.

- Primary focused suite: **134 passed**.
- Independent final Luna High challenge: **25 passed, 2 deselected**, final PASS
  after the preferred-zero and RayThera-lineage defects were corrected.
- Broad refresh/Batch-14 suite: **811 passed**, one existing Passlib `crypt`
  deprecation warning, 262.22s.

Isolated real API evidence:
`output/us-refresh-runtime/wg40-blocked-preservation-api-evidence.json`, SHA256
`2d19ebd0d66498638a942f24dcaf8ca9c54374a6e7ca9d3e4d14985d58c4c089`.
The real FastAPI process and isolated PostgreSQL UAT database served 440 records
and exact historical detail/calculator parity for BIIB, GILD, INCY and the prior
HON/HCA/MCK/LHX/INTC/JBL blockers. No candidate or production catalog activated.
No UI/save behavior changed, so browser and saved-run checks were not repeated.

## Counts and boundary

Current register: 440 companies, 419 recipes, 285 compiled, 134 coding gaps,
197 financial flags, 169 source flags, 437 needing recheck, 21 prior unavailable,
2 current-version source-bound candidates and zero successive-period proofs.
The 382 accumulated source reports are non-composable and counts overlap.

All HON, HCA, MCK, LHX, lease, portability and hardening requirements remain.
No network, paid source, parameter tuning, family adapter, production activation,
scheduling, merge, push or deployment occurred.

## Following group, not started

The highest-reuse current blocker is the common operating-company bridge absence
pattern affecting eleven companies. A small next tranche should inspect CTAS,
FAST and JBHT, retaining only genuinely shared cash/securities/debt/lease/NCI
absence proofs.
