---
name: unavailable-is-not-a-stale-numeric-template
description: Withheld refresh records must clear stale assumptions as well as numbers while retaining recovery state privately.
metadata: { type: gotcha }
---
Changing only the review state and sanitizing a previous numeric artifact left
old assumptions and source attribution visible as if they described the new
cutoff. Build the current unavailable record explicitly: clear numeric models,
scenarios, sensitivities and normalization; validate any current filing reference
against SEC submission identity, dates and cutoff. Otherwise label the old
reference historical, never current or successfully refreshed.

Keep the previous numeric artifact and recipe in immutable history/private retry
state so later valid evidence can recover the valuation. Exercise unavailable
and recovery through the actual API, not just the sanitizer. Acquisition failure
is different: keep the prior dated estimate with failed-refresh status.
