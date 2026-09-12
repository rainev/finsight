# WG5 post-filing events

Verified and user-confirmed 2026-09-09. Production and release boundaries
were untouched.

| Company | Event conclusion | Full result |
|---|---|---|
| AAPL | Routine captured event does not invalidate current financial binding | Source-bound candidate |
| MRK | $650M TARGAN acquisition is completed context; no post-event balance rollforward | Review |
| SNDK | August release supersedes named fields only; April claims/schedules persist separately | Review |
| VRTX | Pending Crinetics price/financing excluded from June standalone value | Review |
| LLY | July completed cash event lacks machine-bound cash/claim rollforward | Review |
| UHS | Completed and pending acquisitions lack one coherent current state | Prior unavailable |

MRK's current period claims are $50M + $100M Peloton contingent consideration
and $275M litigation reserve. Its $650M TARGAN price is not intrinsic value and
is not deducted from the June baseline without post-event cash, debt and shares.

Frozen group: `output/us-refresh-group-verification/4aec7870762677f37bea464f67f6acddf78db150fc0e07934eb2b78cfade9e3f/report.json`.
Report SHA `7a5ab7349bc2352f9e4a067b8f03e8b685fe121c27a45faf18b817471ec5023d`;
implementation `6789d5a3cfa34e20e9bce2c04c49c407186c445ada0388d9f0ec61b7ce343de6`;
policy `be78b3a635b49e8752844f6a08a1964eb713a6b58c7100497058717b82fe9176`.

AAPL candidate changes `79.80130329911236 / 103.3303976983317 / 123.1625608382377`
to `87.44317404534581 / 107.3745809737621 / 123.59698206267868`; this is the
existing current financial refresh, not value attributed to an event.

Real API evidence: `output/us-refresh-operational-uat-20260909-wg5-aapl/uat-report.json`
served baseline → candidate → rollback exactly, reloaded without restart, rejected
stale CAS, preserved 440 entries/419 recipes and left production untouched.
