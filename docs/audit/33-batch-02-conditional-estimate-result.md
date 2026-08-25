# Batch 02 conditional-estimate result

**Valuation date:** 2026-08-14

**Policy:** user-authorized decision-support estimates. Reported SEC facts and governed hypothetical
states are separated privately; every result is `review_required`, Low reliability, and explicitly
not a reported fact, probability-weighted expected value, recommendation, or ordinary
source-bounded intrinsic value.

## Exact result

| Ticker | Low | Base | High | Interpretation |
| --- | ---: | ---: | ---: | --- |
| OMC | $40.5267 | $70.0124 | $100.9724 | Post-combination normalized cash scenarios |
| TTWO | $12.3253 | $79.6947 | $193.1780 | Weak/normal/strong major-release outcomes |
| CHTR | $0.0000 | $0.0000 | $246.2753 | Standalone equity at risk; bear/base residuals are negative, so $0 is a limited-liability floor |
| CMCSA | $1.3214 | $28.7396 | $55.7813 | Current consolidated company only, not post-separation entities |
| META | $164.5074 | $411.9880 | $710.2491 | AI-capex and cash-conversion scenarios with claims/dilution reserves |
| WBD | $0.0000 | $0.3187 | $14.7039 | Standalone normalization only; $0 is an equity floor |

WBD's filed contractual cash consideration is shown separately: **$31.00/share** if closed by
2026-09-30 plus **$0.00277778/day** thereafter; **$31.68611166/share** is a calendar illustration
for 2027-06-04 if the formula remains unchanged. It is not inside the standalone range and is not
probability weighted or labeled intrinsic value.

Under this conditional policy, the six holdouts are conditional-numeric Low and Batch 02 displays
10/10 numeric results. Under the previously approved source-bounded intrinsic policy, the original
4/10 numeric and 6/10 withheld decision remains unchanged comparison evidence.

## Implementation and public safety

- Added public model identity `conditional_estimate` and output field
  `conditional_value_per_share`; no intrinsic-value alias is used.
- Added issuer-specific private sources, exact fact periods, reported inputs, hypothetical
  assumptions, rationales, invalidation triggers, arithmetic, dilution, and claim reserves.
- CHTR's public range is one coherent standalone model; pending transaction terms are excluded.
- WBD's standalone range and contractual consideration are separate public objects.
- Missing facts are not silently converted to zero. CHTR/WBD zero endpoints are explicitly tagged
  limited-liability equity floors.
- The cumulative withheld register remains byte-unchanged pending user approval, SHA-256
  `6ec0e5774a476bee297f609d852b30dbb480b551077d76079428cd3be8d69ec2`.
- Protected serving roots remain unchanged.

## Challenge history

The first Luna-High adversarial review rejected the initial candidate because it mixed incompatible
economic objects and retained an intrinsic-value field name. A second review found annual/current
source-period, derived-claim, and cash-anchor wording gaps. All Critical and Important findings were
resolved. Final independent verdict on `verified-run-e`: **PASS**.

## Verification evidence

- Two complete runs (`verified-run-e` and `verified-run-f`) are byte-identical, tree SHA-256
  `1f27b04dc71f444235059d5f74ed4aa5ed78e676c9921df9357040546a9dcb1b`.
- Conditional report SHA-256:
  `dc49929f49dab3981ff244db96c52e69c4aaef2f0ffb6ad48b119cc6d8732574`.
- Focused conditional/sanitizer suite: **107 passed**.
- Complete backend suite: **1,189 passed, 3 skipped, 1 warning**.
- `git diff --check`: passed.
- Real FastAPI: list HTTP 200/count 10; details 10/10 HTTP 200 with exact staged parity;
  private leaks 0; forbidden serving imports 0.
- API receipt SHA-256:
  `1b8854f4d3edb1dcddce9d2a7d8eb901bdc914ba47f5db8a9d8cfda2e7839dd3`.

## Gate

Technically verified; user confirmation is still required. No serving write, withheld-register
removal, promotion, Batch 03 work, merge, or deployment has occurred.

