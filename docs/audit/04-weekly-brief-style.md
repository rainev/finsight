# Weekly brief and FinSight color identity — 2026-09-07

User intent: newest-first dates spanning a week and a serious-but-playful original identity.

## Research and decisions

- [Linear's design refresh](https://linear.app/now/behind-the-latest-design-refresh): orientation should recede while task content gets prominence; consistent controls and warm neutral surfaces. Applied a shared teal selection color and softened paper-like surfaces.
- [Flighty, Apple Design Award for Interaction](https://developer.apple.com/design/awards/2023/): key information at the point of use, familiar domain conventions. Applied full-width dated tiles, matching directional arrows and scenario values on the scenario buttons.
- [Things](https://culturedcode.com/things/): powerful organization with a lightweight presentation. Applied bounded gestures, a Back to latest shortcut and subdued state feedback.

These choices are design judgments, not claims of measured engagement gains.

## Implementation and evidence

- Seven dates descend left-to-right from the valuation date. Left-arrow/newer and right-arrow/older match the strip; swiping left advances to the next older card. Bounds derive from one NEWS_DAYS constant.
- Removed lavender styling. Ink/ivory foundation, deep teal controls, amber news accents. No forecast or market data changes.
- Calendar spans full width; exploration progress remains per visit. Added Back to latest and comparison values within scenario buttons.
- ✔ Browser: 14,13,12,11,10,9,8 observed; Aug 8 disables Earlier; Back to latest restores Aug 14; left drag reaches Aug 13. Bull selection displays $123.16.
- August 8/9 retain explicit no-content preview states; no articles were invented for the added dates.
- ✔ Frontend production build passes. New theme review remains with the user.
