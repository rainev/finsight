---
name: cutoff-bridge-includes-post-balance-financing
description: Reconcile acquisitions, financing, and material claims after the latest balance sheet but before the valuation cutoff.
metadata: { type: gotcha }
---
The controlling 10-K/10-Q anchors operating history and the latest reported balance sheet, but it
does not automatically define the valuation-date financing state. Batch 16's Agilent filing ended
April 30, while a cutoff-eligible June 25 8-K reported $600M of new notes issued at 99.968%.

**Why:** Ignoring the event understates both debt and cash. Adding only the debt invents a net-debt
increase; adding only proceeds invents surplus cash. Either error can materially move per-share
value even when every historical cash-flow formula is correct.

**How to detect / apply:** For every numeric issuer, scan cutoff-eligible subsequent 8-K/6-K/proxy
events between the balance-sheet date and valuation cutoff for debt issuance, repayment, equity,
dividends, acquisitions, and settlements. Add reported principal to claims and reported issuance
proceeds to cash exactly once; classify fees conservatively when not separately disclosed. Keep
the event accession/date/hash private and invalidate the value if the event changes.

Batch 17 adds the opposite boundary: AbbVie signed and filed a $10B underwriting agreement before
the cutoff, but the offering was expected to close on 2026-08-18, after the 2026-08-14 valuation
date. A signed-but-unclosed offering is a material pending event, not issued debt or available cash.
Record its principal, expected proceeds, purpose, and expected close date; keep the valuation in the
current pre-close state and make closing an invalidation trigger. Add debt and proceeds only when a
cutoff-eligible source says issuance/closing actually occurred.

Batch 23 extends this beyond securities issuance. AMETEK's June balance sheet preceded its August 3
$5.0B Indicor closing and reported $1.1B acquired annual sales; a legacy-company Pass therefore
valued an economic object that no longer existed at the August 14 cutoff. C.H. Robinson likewise
reported a July 23 $604M possible loss and only $155M maximum insurance recovery after its June
balance sheet. Both facts were inside the controlling filings as subsequent events.

**How to detect / apply:** Review every cutoff-eligible subsequent-event fact, not only later 8-Ks.
When a material acquisition closed before the valuation date, include the acquired operating scale
and bounded consideration/funding once, then cap the result Conditional until final funding and
acquired cash conversion are filed. When a material possible loss is bounded but unrecognized,
carry a transparent claim range and downgrade classification; do not treat an absent balance-sheet
accrual as zero. This scan happens after balance-sheet extraction and before declaring Pass.
