# Catch policy-specific exceptions before their generic parent

When a policy exception subclasses `ValueError`, a preceding `except ValueError` intercepts it
before the policy can distinguish a bounded missing-detail fallback from a hard source failure.
Catch the specific exception first: an unavailable current segment table may use a consolidated
Low fallback, while an explicit future-dated or cutoff-invalid source must still withhold.
