# FinSight US valuation — production backlog

Deferred work: large-but-invisible, blocked, or out-of-scope. Each says *why* it's deferred and what would pull it into
the roadmap. Re-evaluate periodically — don't let items rot here.

## Deferred — large / out-of-scope

- **CW-AUTH · Fresh registration/password and Google sign-in acceptance.** Public entry and existing-session CTA are live verified; all success branches target AAPL. Creating a new persistent local test account was blocked by safety review. Unblocks with explicit test-account approval; Google also requires an available configured provider/session. Do not claim those journeys verified from source checks alone.
- **CW-PERF · Software-renderer performance follow-up.** Native Apple M2/Metal sample is approximately 60 FPS; forced SwiftShader showed p95 50ms and stalls. Reduced/static modes remain available. Broader device tuning needs additional representative hardware measurements, not a universal performance claim.
- **CW-DEPS · Dependency advisory review.** npm reported seven advisories during the required Three.js/test-tool installation. No broad dependency upgrades or audit fixes were included in this scoped UI change; review separately before a production release.

- **B1 · IFRS / 20-F foreign filers** (20 engine_errors: UL, NVO, AZN, SAP, NVS, SNY, INFY, BIDU…).
  *Why deferred:* they file **20-F on IFRS**, not 10-K on US-GAAP — the normalizer finds no us-gaap facts. This is a
  whole separate ingestion + IFRS-concept-mapping path, not a fix.
  *Unblocks when:* there's demand for foreign-filer coverage and appetite for an IFRS ingestion track.

- **B2 · Autos & parts archetype** (F, GM, TSLA, PCAR + parts).
  *Why deferred:* captive-finance arms put huge financing debt on the balance sheet; naive FCFF/industrial policy
  mis-values them, and n=3 comparables is too thin to calibrate. TSLA is also a growth outlier.
  *Unblocks when:* an industrial-vs-finance-arm split (segment data) is available, or a dedicated auto policy is
  calibrated on a wider set.

- **B3 · Full-500 publishable-AND-credible.**
  *Why deferred:* not an engineering milestone — it needs sustained **analyst review** of per-issuer assumptions,
  overrides, and candidate archetypes. Tracked as the ongoing F1 workflow, not a deliverable.
  *Unblocks when:* an analyst owns the ratification loop.

- **B4 · Too-few-annual-periods issuers** (13: CRWD, NTES, recently-listed / thin-history ADRs).
  *Why deferred:* genuinely insufficient us-gaap history for a multi-year forecast; forcing it would fabricate a trend.
  *Unblocks when:* a short-history policy (e.g., single-period/steady-state model) is designed, or the issuers age.

## Deferred — quality caveats to revisit (not blockers, but carry review flags)

- **B5 · Conservative fallbacks undervalue growth names.** Residual-income / DDM fallbacks (HD $155, MCD $121, WMT $42)
  are systematically conservative for low-payout / high-growth companies. Fine as `review_required` floors; revisit if
  they're surfaced as headline values.
- **B6 · Candidate archetype cohort contamination.** `specialty_chemicals` mixes industrial chem + household/personal
  care; `internet_digital_services` is META/GOOGL-heavy (n=5); `transportation` mixes rail/airline; `retail` mixes
  discount/franchise. Split + recalibrate before promoting to `pass`.
- **B7 · `sales_to_capital` and dividend-growth are governed policy, not per-issuer.** Documented; refine with
  per-issuer evidence before final publish.

## Notes
- Nothing here is a hidden blocker for the NOW phase. These are explicitly parked so the roadmap stays focused on the
  cheap, visible wins (ship + serve) and the genuinely high-value model work (insurance, REITs).

## Revised web UI follow-ups

- **WEB-B1 · Sector-aware operating Health Metrics.**
  *Why deferred:* the confirmed Batches 01–10 public catalog intentionally excludes the raw ratios needed to score
  Financial Strength, Profitability, Efficiency, and Growth. Deriving those scores from model confidence or forecast
  assumptions would be misleading. The UI currently labels and shows Evidence Health instead.
  *Unblocks when:* a versioned sector-score methodology is approved and the batch generator emits public-safe category
  evidence from verified private filing inputs.

- **WEB-B2 · US-specific news ingestion.**
  *Why deferred:* the current GNews integration is configured for the Philippine feed and no replacement US provider,
  commercial-use policy, or refresh query was approved. The revised News page fails safely with a functional empty state.
  *Unblocks when:* a US source and market-isolation policy are selected and configured.

## PSE V2 follow-ups

- **PSE-B28-SOURCES · Recover the three null-only Batch 28 cases only under separate review.** AAA needs a current attributable asset/liability and recovery bridge; EG needs period-matched common claims and current realizable NAV; PTT needs a parent-common residual, reconciliation of 800m listed versus 1.5bn outstanding shares, and financing/preferred claims. NXGEN's finite P/B screen is Low-reliability and does not replace project-level SOTP or licensed price data. Do not infer recovery from staged results confirmation.
- **PSE-B27-SUSPENDED · Recover only under separate issuer review.** AR/PNC/PORT/MGH/T need reconciled common claims; PNC also lacks a financial-summary period and equity figures. CYBR/MJIC/TUBIG need credible recovery or post-transaction attributable NAV; BMM has stale crop-cycle economics; SOC needs parent attribution and the unfiled FY2025 annual report. Keep all ten staged results blocked/null; no old book or suspended quote is a current valuation.
- **PSE-B26-SUSPENDED · Recover Batch 26 common-claim and filing gaps only under a separate review.** DHI needs a final post-merger exchange ratio; UNH/VLC/INFRA need reconciled listed/outstanding/common claims; PNX/ROX and HOME/STR need current financing and operating evidence; I needs a viable parent-common residual. MM's finite screen is historical only until reporting and suspension status are rechecked. Keep null outcomes and no current-upside claims in the staged Batch 26 results; do not infer recovery or activation from results confirmation.
- **PSE-B25-SOURCES · Review null-only Batch 25 recovery separately.** FYN still needs the preferred economic claim; MAH needs all common lines and a positive attributable residual; LTL needs post-listing reviewed financials/shares and property NAV; VLL/VREIT/ALLDY need current filings and suspension/financing review. ZHI needs recoverable asset economics before any positive screen. Do not infer recovery from Batch 25 results confirmation or local activation; preserve null outcomes until a separately authorized source review.
- **PSE-B20-SEARCH · Monitor PH search hydration after list performance fix.** During Batch 20 activation, two signed-in attempts showed a correct detail/footer but `0 · PSE V2` and no result; a later clean run passed. Batch 21 exposed and fixed a concrete quadratic list-path timeout: the live 218-record list fell from over 30 seconds to about 0.19 seconds, and search to PHA passed. The shared UI list requests were also isolated so a US-list failure cannot clear PH results. Monitor for any residual intermittent empty dropdown after future catalog growth; do not infer one from a transient `429` alone.
- **PSE-B21-PRECISION · Preserve distinct small per-share values in the PH display.** The shared formatter uses four decimals only below PHP0.01; LPC's exact PHP0.009020459 base and PHP0.012027278 high can appear close to an edited PHP0.010022732 base after two-decimal formatting. The immutable artifact/API retain full precision. Review a compact precision rule for values near one cent in a separately scoped UI change; the Batch 21 local activation proceeded with this caveat disclosed, not silently fixed.
