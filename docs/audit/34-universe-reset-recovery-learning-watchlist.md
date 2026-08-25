# Universe Reset Recovery Learning Watchlist

**Short call name:** **Recovery Learning Watchlist**

**Purpose:** bookmark every company that was not fully recovered during the 50-batch universe
reset, even when FinSight can display a Low-reliability conditional number. After Batch 50, review
these companies as one learning corpus and turn repeated failure patterns into pipeline upgrades.

## Inclusion rule

Add a company only when it **failed the initial batch pass**, received its recovery attempt, and
then either condition is true:

1. it was not recovered and remains withheld; or
2. it was recovered only conditionally through a material event assumption, equity-floor
   convention, provisional claims allocation, or another unresolved economic-model dependency.

Do not add companies that passed the initial batch. Do not keep companies that later achieve a
fully source-bounded recovery.

A company is fully recovered only when it has a source-bounded numeric value through an
economically suitable model, no material unresolved event/claim/model gap, and a completed
independent challenge. A short disclaimer does not make a conditional estimate fully recovered.

## Current watchlist

| Batch | Ticker | Initial | Recovery | Current status | Why it remains on the watchlist |
| ---: | --- | --- | --- | --- | --- |
| 01 | NEE | Withheld | Withheld | Withheld | Bear/base mixed-utility FCFE remains nonpositive after complete borrowing |
| 02 | OMC | Withheld | Withheld | Conditional numeric Low | Combined post-IPG cash history is still short |
| 02 | TTWO | Withheld | Withheld | Conditional numeric Low | Positive value depends on hypothetical major-release outcomes |
| 02 | CHTR | Withheld | Withheld | Conditional numeric Low; equity at risk | Bear/base residual equity is negative and pending transaction economics are incomplete |
| 02 | CMCSA | Withheld | Withheld | Conditional numeric Low | Current consolidated value cannot allocate the future separation |
| 02 | META | Withheld | Withheld | Conditional numeric Low | Commitments, leases, and capex lack a mutually exclusive cash waterfall |
| 02 | WBD | Withheld | Withheld | Conditional numeric Low; equity at risk | Weak standalone normalization and conditional merger consideration remain distinct |
| 03 | LYV | Withheld | Conditional Low | Conditional numeric Low; equity at risk | Event cash, claims, and dilution remain assumption-driven |
| 03 | ECHO | Withheld | Withheld | Withheld | Deconsolidation and spectrum transition still lack one bounded continuing-company object |
| 03 | GOOGL | Withheld | Conditional Low | Conditional numeric Low | AI commitments remain absorbed through broad cash-conversion states |
| 03 | APP | Withheld | Conditional Low | Conditional numeric Low | Current capex remains assumption-derived after the disposal |
| 03 | FOXA | Withheld | Conditional Low | Conditional numeric Low | Rights obligations remain modeled through stressed cash margins |
| 03 | TKO | Withheld | Conditional Low | Conditional numeric Low; equity at risk | Rights cash, Class B conversion, and NCI remain specialist assumptions |
| 03 | PSKY | Withheld | Withheld | Withheld | Successor bear/base residual equity remains nonpositive |
| 04 | F | Withheld | Conditional Low | Conditional numeric Low | Normalized equity earnings are not a full Ford Credit SOTP |
| 04 | GPC | Withheld | Conditional Low | Conditional numeric Low; equity at risk | Working-capital/acquisition normalization; bear equity floor |
| 04 | HAS | Withheld | Conditional Low | Conditional numeric Low | Post-impairment and licensing transition assumptions |
| 04 | LOW | Withheld | Conditional Low | Conditional numeric Low | Housing-cycle and unresolved-claims ranges |
| 04 | MCD | Withheld | Conditional Low | Conditional numeric Low | Franchise/lease normalization and unresolved NCI |
| 04 | TJX | Withheld | Conditional Low | Conditional numeric Low | Alternate revenue mapping and inventory normalization |
| 04 | NKE | Withheld | Conditional Low | Conditional numeric Low | Turnaround, channel, inventory, China, and FX assumptions |
| 04 | HD | Withheld | Conditional Low | Conditional numeric Low | SRS integration and housing-cycle assumptions |
| 04 | ROST | Withheld | Conditional Low | Conditional numeric Low | Inventory, leases, investments, and claims ranges |
| 04 | MGM | Withheld | Conditional Low | Conditional numeric Low | Casino-cycle, JV/NCI, lease, and digital assumptions |
| 05 | WSM | Withheld | Conditional Low | Conditional numeric Low | Home-furnishing cycle, inventory, leases, and financing claims |
| 05 | CASY | Withheld | Conditional Low | Conditional numeric Low | Fuel mix, acquisitions, LIFO, land, and working-capital assumptions |
| 05 | CCL | Withheld | Conditional Low | Conditional numeric Low; equity at risk | Cruise cycle, ship capex, leverage, and a zero bear equity floor |
| 05 | PHM | Withheld | Conditional Low | Conditional numeric Low | Mortgage and land economics remain consolidated in an equity-earnings range |
| 05 | SBUX | Withheld | Conditional Low | Conditional numeric Low | Store turnaround, leases, inventory, and negative book equity |
| 05 | AZO | Withheld | Conditional Low | Conditional numeric Low | Supplier-financed inventory, leases, buybacks, and negative equity |
| 05 | DHI | Withheld | Conditional Low | Conditional numeric Low | Mortgage banking, land inventory, financing, and NCI remain consolidated |
| 05 | RCL | Withheld | Conditional Low | Conditional numeric Low; equity at risk | Cruise cycle, ship capex, leverage, and a zero bear equity floor |
| 05 | ORLY | Withheld | Conditional Low | Conditional numeric Low | Supplier-financed inventory, leases, buybacks, and negative equity |
| 05 | NVR | Withheld | Conditional Low | Conditional numeric Low | Lot options, land deposits, mortgage earnings, and housing-cycle assumptions |

## End-of-reset review

After Batch 50:

1. group entries by recurring learning theme;
2. count which extraction, accounting, model, event, or claims gaps recur most often;
3. design shared pipeline controls before issuer-specific patches;
4. replay this watchlist through the improved pipeline;
5. remove an entry only after source-bounded recovery, independent verification, and user
   confirmation.

The machine-readable source is
`backend/app/us_valuation/config/universe_reset_recovery_learning_watchlist.json`. The cumulative
withheld register remains separate because “withheld” and “not fully recovered” are not synonyms.
