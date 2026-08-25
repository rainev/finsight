---
name: universe-reset-one-recovery-then-register
description: Each reset batch reports initial withholds, attempts recovery once, then appends only remaining withholds to a cumulative register.
metadata: { type: feedback }
---
The user confirmed the controlled reset is a two-stop workflow: first process and report all ten;
then, only after a second signal, attempt each withheld company once and report again. Companies
still withheld are appended to the cumulative reset register and receive no further automatic
attempt. **Why:** this preserves visibility, prevents endless recovery loops, and keeps batch
boundaries user-controlled. **How to detect / apply:** never recover during the initial batch
signal; never append an initial withhold before its one recovery attempt; stop before the next
batch.
