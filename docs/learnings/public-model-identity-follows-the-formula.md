---
name: public-model-identity-follows-the-formula
description: Derive the public model identity from the calculation method, never from Pass versus Conditional status.
metadata: { type: gotcha }
---
Public `model_policy`, `models`, calculator family, and methodology must all name the formula that
actually produced the value. Availability is a publication classification, not a model selector.

**Why:** Batch 34's shared public builder mapped every Pass to FCFF even though USB and BRO were
calculated with residual income. Arithmetic and API parity still passed because both sides repeated
the same mislabeled artifact. Batch 35 exposed the inverse: all Conditional results were labeled
`conditional_estimate`, hiding nine residual-income models and one FCFF model. Their calculators
matched the stored headline only by applying a ratio around it, not by replaying the formula.

**How to detect / apply:** Assert the private method, public primary method, model key, calculator
family, and output type as one semantic contract. A Pass may use residual income, FCFF, NAV, or
another suitable model; never infer the model from availability alone. Keep explicit
`availability_type` independent, publish the actual base assumptions, and assert that the calculator's
default factor equals the valuation formula before testing overrides.

Reused public builders can also retain an old batch label, forecast horizon, history-period count,
or automated-review reason after the model itself is corrected. Check those fields against the
current private result, including withheld records. Regenerate the automated review after changing
model identity; compare persisted successor artifacts rather than only testing the builder in memory.
