# WG31 independent subsidiary ownership/source-boundary challenge

Checked 2026-09-16 by `wg31_mck_instruments`, gpt-5.6-luna with high reasoning,
one read-only bounded reviewer. No network/edits; primary verified material
source/carrying/contract-inventory and QName/duplicate-role findings firsthand.

Current MCK 10-Q accession `0000927653-26-000234`, report 2026-06-30,
filed 2026-08-05. Raw SHA-256
`ae1dbb2b5240d1316869e75771565769fb61963e9dcf343d2bd1decc34bee502`;
structural SHA-256 `86ba2d2b34b9acbdbb369fc35f903292eafa6a62a25a7513f930e4798a224afc`;
visible text SHA-256 `0fae1fa41ddf31f652e20cb1df7610a4e49458e3b0bcdefb5e5d520b3bf09808`.
Package has29 resources/9,348,962 bytes, manifest SHA-256
`c5de8a5bb911285136e113736ae9b2e513713226805d6b62fd90da60d77dc4bb`.

Note 2 PRISM at visible offset46864: 80% purchased, prior20% includes25M
redeemable portion, not all20% RNI. Core48664–49323: 70% acquired/30% retained,
put everyfive years, no exercise date/formula. Apollo Note5 around60208:
approx13% subsidiary convertible preferred via approx1.25B, not parent dilution.
Note5 roll61597–62850: 943+9+1+374+1238−2=2563M; ordinary395+35−52−2=376M.
Redemption293M MMS+81M Core included in carrying, not extra stock/cash claims.
Net proceeds1238M are issuer extension cash-flow source, not GAAP concept or
equal to approximate1250M gross investment. No source-backed12M cost bridge.

Current package/index lacks executed Apollo/MMS security purchase and governing
LLC agreement, conversion/redemption/coupon/seniority formulas, PRISM put terms,
Core exact windows/valuation floors/caps and current per-instrument schedule.
Monte Carlo description provides no inputs/workpaper and cannot be reproduced.
Keep economic basis/first exercise date/parent conversion shares unknown;
current reported aggregate carrying is not independently derived intrinsic value.

Initial18 tests passed but reviewer found QName substitution and duplicate-role
holes in the helper. Primary reproduced the valid custom-namespace row with
GAAP QName still passing. Correction reuses parser _QNameCanonicalizer to require
exact namespace-derived QName on every candidate; cash_flow role every proceeds
row and balance_sheet role every parent-preferred row checked before dedup.
GAAP/arbitrary-prefix and contradictory duplicate-role negative tests added.
Final independent **21 passed in16.76s**, baseline accepted and mutations fail;
no material required correction remains within this bounded source/guard scope.
Primary corrected focused set59 passed in44.75s. Final stable broad739 passed,
one existing warning in817.40s; frozen repeat and isolated real API parity pass.
interrupted pre-correction546-check suite is not current acceptance.

Full MCK refresh and prior cash/funding/allocation/securities/legal-overlap and
LHX/leases/portability/HCA/HON/hardening gaps remain required, not waived.
[Current receipts/results](wg31-mck-subsidiary-ownership-scope.md).
