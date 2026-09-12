---
name: cash-receipt-date-is-not-gain-date
description: CF recognized the Orica gain in March but received cash in April; rolling cash windows must use the receipt date.
metadata: { type: gotcha }
---
CF filing 0001324404-26-000019 recognizes the $170M Orica settlement gain in
March 2026 but explicitly reports cash received April 30. Q1 cash normalization
must not deduct that later receipt; a subsequent rolling TTM window can contain
the cash even after the recognition period has rolled out.

Extract amount, actual cash date and OCF classification independently, pin HTML
and structural hashes, and retain immutable event history. A logical event key
must not include its amount: otherwise a corrected amount becomes a second
event and is double counted. Repeated disclosures do not create new receipts.
The filing does not support a separate tax reversal, so the adjustment remains
explicitly gross cash. The event store/normalizer are exercised against the
real capture a587eafaa664f46d3971d383f81d4290a6aa1a83fa14d507c405ccab5fcedab0.
