# PSE financial-summary snapshot comparison — internal pilot

Date: 2026-09-26. Scope: AP, BPI, RCR, RLC. Status: implemented and locally verified; user acceptance and real PSE snapshot inputs remain pending. No live PSE fetch, polling installation, approval, or activation.

## What was exercised

- A saved structured snapshot is matched to the frozen PSE EDGE company-summary URL, reporting period, currency, unit, consolidation scope, and numeric facts. The economic digest ignores observation time and JSON formatting; a new period or changed same-period facts creates a pending signal. A first same-period observation is a baseline. Stale or invalid files are held.
- Offline mode bypasses all external index fetching, even if a source flag were later enabled. It accepts only a one-tick CLI invocation. A pending signal alone produces no new valuation.
- A hash-pinned reviewed receipt must cover the changed period. An amended summary additionally needs an `amended_filing` receipt. The existing four-model runner stages supported changes as provisional and leaves unchanged artifacts intact. RLC remains a forced hold.
- Synthetic 2026-Q2 summary signals for all four pilot tickers were fed into the real runner with the previously reviewed RCR local receipt. Only RCR recalculated; AP, BPI, and RLC stayed pending. The staged 282-entry catalog served through authenticated list and all four detail API routes. RCR's provisional base was PHP 5.310705882352938 per share; inherited RLC bytes matched the active artifact. A second identical tick did not restage.

## Verification evidence

- Focused offline snapshot and CLI tests: 8 passed.
- Complete backend suite: 486 passed, one existing `passlib` deprecation warning.
- Frontend production build: passed; Vite emitted its existing large-chunk advisory.
- Active pointer SHA-256 remained `50652bb9490f77d73d8cddb8b98058197910a0271c935d6685339370e0f7da92`.
- No actual PSE financial-summary snapshot file was present in the workspace. The signals in this exercise are synthetic **triggers**; they are not new source evidence for RCR or any other issuer. The RCR receipt is the pre-existing reviewed issuer-source workpaper and its result remains provisional.

## Still outside this gate

No live PSE EDGE watcher, authorized automatic retrieval/storage, four-issuer filing reconciliation, source-rights clearance, analyst approval, or active-catalog switch. To run a real offline comparison, first supply authorized saved PSE summary snapshots with period-tagged fact keys, then obtain model-complete reviewed receipts for any changed issuer. The summary page is not a substitute for cash-flow, distribution, capital, or property-owner evidence.
