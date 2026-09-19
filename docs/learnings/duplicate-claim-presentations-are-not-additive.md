---
name: duplicate-claim-presentations-are-not-additive
description: Aggregate, Level-3 and acquisition-member views can report the same contingent liability and must be reconciled by scope rather than summed.
metadata: { type: gotcha }
---
CTSH and VRT report contingent consideration through multiple dimensional views.
CTSH's current aggregate and Level-3 rows are the same $25M liability. VRT's
issuer current total is independently corroborated by aggregate and Level-3
derivative views, while acquisition-specific GAAP rows are narrower slices.

**Why:** Summing every nonzero fact double-counts one claim and can also invent a
residual when a consolidated total and acquisition slices use different scopes.

**How to detect / apply:** Prefer a current issuer total only when another
authoritative presentation corroborates it. Require matching period, accession,
dimensions and positive totals; accept Level-1/2 zeros as diagnostics. Retain
acquisition-member rows, maxima and noncash changes separately and reject
conflicts.

WG16 adds two related scopes. DGX's $100M aggregate and Level-3 contingent
consideration are one carrying liability; measurement-input changes and $38M of
business-acquisition cash are not extra claims. EW's $9.9M aggregate Level-3
carrying value includes a $7.5M current portion, while its $132.5M acquisition-
date maximum is a possible outcome, not a current or scenario liability. When a
current portion, aggregate carrying value and contractual maximum coexist, bind
the aggregate once, retain the current portion as a subset, and keep the maximum
outside valuation arithmetic.

WG18 adds two more duplicate forms. MDT reports one $163M contingent-
consideration liability as a total, a typed $32M current plus $131M noncurrent
location split, and $141M plus $22M of Level-3 milestone components. All three
views reconcile to one claim. PFE reports $96M current and $2.163B noncurrent,
then repeats each amount under Level 3; the claim is $2.259B, not $4.518B.
Typed members must survive parsing because an axis marked only `typed` cannot
prove which amount is current. Reparse the hashed filing with the current
parser and fail closed when the member values are unavailable.

WG26 adds a narrower ownership-source distinction. LHX's preferred carrying
fact and temporary-parent equity fact are one book claim; the carrying fact's
label includes a DIFFERENT redemption amount that is not its numeric value.
MCK has a genuine carrying/dimensional-alias pair, but different redemption/
conversion economics. Share only explicit non-additive source-alias logic,
not an instrument valuation rule. A partial ownership proof never clears a
mixed legal/derivative/event stack or approves book value as intrinsic claim.

WG27 reconciled LHX's original preferred/derivative/program accounting allocation.
The $968M book host plus $130M/$186M current liabilities is an accounting sum,
not a source-approved intrinsic claim. Full contractual cash settlement or
conversion dilution must not ALSO deduct the bifurcated host/features; future
milestones/subsidiary capitalization are not supplied by current book values.
Funding proceeds already in cash and the noncash program asset are not extra
surplus cash. Current source URI is legacy harris.com; derive taxonomy mappings
from the filing rather than the company brand name.

WG31 MCK's $2.563B redeemable carrying already includes net sale proceeds and
$374M redemption movement ($293M MSS/$81M Core); those movements are not extra
claims. The approximately $1.25B Apollo investment is not the $1.238B net cash
proceeds, and the source does not prove a $12M expense bridge. Proceeds are an
issuer extension QName, not GAAP despite the familiar local name. Require the
parser's namespace-derived QName and validate every duplicate's statement role
before deduplication; checking only the first row can hide a contradictory view.
Current carrying and put cadence do not supply conversion/put value or first
exercise date. Preserve reported stocks without inventing intrinsic outcomes.
