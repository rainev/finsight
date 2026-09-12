---
name: binding-loop-variable-must-not-shadow-output-field
description: Additional source checks must not overwrite the outer binding field that selects the normalized output.
metadata: { type: gotcha }
---
The additional-capex verifier reused the name `field` inside its PP&E/software
loop. Python function scope then left `field=capital_expenditures`, so a valid
cash-margin binding requested an unsupported cash-history output. **Why:** the
source checks passed but changed control state used after the loop. **How to
detect / apply:** use a distinct `source_field` loop variable and include the
requested binding name/field in unsupported-output errors; exercise the real
source path because ordinary unit fixtures may not enter this branch.
