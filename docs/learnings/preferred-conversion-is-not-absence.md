---
name: preferred-conversion-is-not-absence
description: PG's diluted denominator already includes preferred conversion; zero additional deduction is a model basis, not a zero reported balance.
metadata: { type: gotcha }
---
PG's FY2026 EPS table reconciles basic shares (2,333.7M), preferred conversion
(68.3M), and awards (20.5M) to 2,422.5M diluted shares. Its $756M preferred carrying value
must not also be deducted under that expressly assumed-conversion model.

Preserve the reported preferred amount diagnostically. Project only the model's
additional deduction to zero after current source share/class reconciliation;
do not label it reported absence. Unknown/new preferred classes or unsupported
conversion require review, and resolving this field must not clear unrelated
cash/debt/lease blockers.

The converse is equally important: KDP deliberately uses a current preferred
claim and therefore adds no conversion shares, while MCHP's retained model uses
future conversion shares and dividend PV and therefore does not deduct the
liquidation preference. The policy must declare one basis and source-bind its
terms; a zero current conversion increment does not prove no future conversion.

A settled conversion requires the opposite proof. COHR's current zero carrying,
redemption and share balances are accepted only because the same filing reports
the preferred-share and value conversion roll-forward into common equity. Keep
the resulting common dilution in the source share denominator and keep NCI and
scenario cash stress in their own fields; never carry the old preferred claim
forward or add the conversion shares twice.
