# Batch 36 VLO Recovery Result

Date: 2026-09-05
Status: **user-confirmed on 2026-09-05**

## Outcome

VLO received its one authorized recovery attempt and remains **Withheld**.

- Attempted: **1/1 — VLO**
- Recovered to Conditional: **0/1**
- Still Withheld: **1/1 — VLO**
- Final Batch 36: **Pass 0 / Conditional 9 / Withheld 1 / Numeric 9**

## What the attempt recovered

The apparent capital-spending gap was resolved from the frozen cutoff-safe Companyfacts packet.
The correct current concept is `SegmentExpenditureAdditionToLongLivedAssets`, not the stale
`PaymentsToAcquireProductiveAssets` lineage:

- FY2023 `$1.916B`, FY2024 `$2.057B`, FY2025 `$1.885B`;
- H1 2026 `$798M` and comparative H1 2025 `$1.066B`;
- exact TTM capex: `$1.885B + $798M − $1.066B = $1.617B`.

Reported TTM revenue is `$139.397B`, OCF `$10.908B`, interest `$563M`, and normalized tax
`22.2553%`, producing a reported cash-FCFF diagnostic of `$9.7287B`. Because current cash flow is
unusually strong and Benicia completed idling in April 2026, it is not used as the scenario floor.
The private cycle model instead uses FY2025/FY2024/FY2023 cash-FCFF margins of
`3.5510% / 3.9097% / 5.3695%` across bear/base/bull.

The post-quarter `$100M` debt repayment reduces both cash and debt once: cash becomes `$7.774B`,
debt/finance leases `$11.249B`, and net debt is unchanged. NCI is `$3.267B`; preferred absence is
confirmed by a statement-scope check rather than a missing-value zero.

## Private diagnostic — not published

An eight-year refining-cycle FCFF replay produces the following values **before any Port Arthur
third-party or regulatory claim**:

| Scenario | Private pre-claim value/share |
| --- | ---: |
| Bear | $110.35 |
| Base | $171.18 |
| Bull | $316.83 |

This proves the operating business and bridge can produce a finite value. It does not prove the
common-equity value after the unresolved claim. These values remain private, are absent from the
public artifact, and are not a recommendation.

## Why recovery still failed

The controlling 10-Q states that Port Arthur lawsuits include personal-injury, property-damage,
nuisance, and proposed class claims; several seek unspecified damages above `$1M`. The full loss
cannot reasonably be estimated, and possible regulatory action is also unestimable.

The `$78M` insurance receivable, `$15M` repair cost, and `$250M` planned incident capital relate to
property repair/capital recovery. They do not cap third-party or regulatory liability. No local
cutoff-safe evidence supplies an insurance limit, self-insured retention, finite claim range, or
explicit immateriality conclusion. Substituting zero or inventing a reserve would violate the
bounded-uncertainty policy.

Release condition: revalue only after cutoff-safe evidence supplies finite low/base/high Port
Arthur third-party and regulatory claim bounds, or explicit evidence that the exposure is
immaterial to common-equity value.

## Independent challenge

Two `gpt-5.6-luna` reviewers ran under the FinSight Efficiency workflow:

- High reasoning verified source identity, custom-capex lineage, TTM arithmetic, claim exhaustion,
  preferred absence, repayment treatment, source hashes, and private/public separation.
- xhigh reasoning replayed all three eight-year DCFs, margin selection, Benicia treatment,
  sensitivities, model identity, sanitizer behavior, and the final withholding decision.

The model reviewer found one stale automated-review label naming `conditional_estimate`; final
successors recompute it from `fcff_dcf`, and a regression test prevents recurrence. Final reviewer
disposition: **0 Critical / 0 Important / 0 Minor**.

## Determinism and real verification

- Final recovery runs C/D: byte-identical; report SHA-256
  `1744827eef56d560fbfc90da44708ed654f386e3c0f982020bc7576bec77c659`.
- Final recovery tree SHA-256:
  `8f04f94e60e2dbad583b2e38051b906f66f3d3251c86a20220295d4ea00e2fa7`.
- Focused Batch 36 history/recovery tests: **15 passed**.
- Complete backend suite: **1,616 passed, 3 skipped, 1 warning**.
- Frontend production build: **1,694 modules**, passed.
- Isolated cumulative catalog: **360** — 116 available / 233 conditional / 11 unavailable;
  artifact tree `eb7e73ccaa8ec9b8c8d6e0d1aeeab26f269c0254af1ca90a9d9fc0128b8fa5d1`.
- Real API: **360 list, 360 detail, 360 calculator/default parity; zero private leaks**.
- Exact list/detail parity: true / **360 of 360**; forbidden serving imports: **0**.
- API receipt SHA-256:
  `eeb2c4fedc9e8be7dd49c23ba5947d0c2535d48c098db4d246e27e5286d2991d` and
  `ad263ed0fff9d2e12dc5a9bb56e0667a15461629d2ab53a64d9331af4c282f48`.
- Catalog manifest SHA-256:
  `060a0cf1e5aada4b469edc0b33f43d4234232376553186e96bd18c38bb9fc572`.

## Confirmation and bookkeeping

The user confirmed this exact recovery outcome with `y` on 2026-09-05. All ten non-Pass Batch 36
companies are now on the Recovery Learning Watchlist, and VLO is in the cumulative withheld register
with one consumed recovery attempt. The watchlist is **244 companies** — 233 Conditional and 11
Withheld. The cumulative automatic-withheld history contains **21 entries**. No second automatic VLO
recovery should occur during the reset.

Confirmed watchlist SHA-256:
`7027181b9bd2262e6c7e0d707a44ba3d4748d2ae44d50b7ed83ddafcaaa10b93`.
Confirmed withheld-register SHA-256:
`22fb28e93e84996d6b2fe1bd836d0cee3df746f3536aec26b57dfc1215751bb6`.
Post-bookkeeping watchlist/withheld/recovery verification: **12 passed**.

Tracked serving artifacts, merge, push, deployment, and Batch 37 remain untouched.
