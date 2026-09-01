---
name: xbrl-alias-additions-can-change-selection-precedence
description: Add XBRL aliases only after checking selection precedence on previously verified issuers; scope ambiguous concepts when necessary.
metadata: { type: gotcha }
---
A standard XBRL concept can be valid for one issuer and still be unsafe as a global alias. Adding
`InterestIncomeExpenseNet` globally repaired ZBH's current interest history but changed the selected
interest path for YUM and SYY, failing their existing value/status contracts.

**Why:** the normalizer chooses among ordered concept candidates. Expanding that set changes which
otherwise-valid fact wins; this is a semantic precedence change, not merely broader extraction.

**How to detect / apply:** after adding any concept alias, run the full historical valuation suite
and compare previously confirmed outputs, not only the target issuer. If one concept is appropriate
only for a specific filing pattern, pass a scoped concept configuration to that repair/model path
instead of changing global precedence. Never update old expected values merely to accommodate an
unintended selector change.
