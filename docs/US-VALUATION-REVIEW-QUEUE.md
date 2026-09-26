# US Valuation Review Queue

This is a human review aid for the 206 generated US valuation artifacts. It is not an approval decision or investment advice.

## Start here: needs investigation now

`ADSK`, `CRM`, `DELL`, `MSFT`, `NET`, `NOW`, `STX`, `WDC`, `XYZ`

Rule: DCF-versus-EPV dispersion exceeds 40%. Reconcile the two methods, source data, terminal assumptions, and share count before any sign-off. `NET` is highest urgency because it also has an absent SEC source URL, negative EPV, and terminal value above 85%.

## Review buckets and rules

| Group | Rule | What it means |
| --- | --- | --- |
| Easy example | Direct model route; no fallback/error/special warning beyond the model's standard caveat | `BAC` (residual income), `AEP` (DDM), `AAPL` (FCFF) |
| Average example | Usable result with one added caveat: lower confidence, limited bridge gap, or a shorter horizon | `GS` (residual income), `ABBV` (DDM), `ANET` (FCFF) |
| Difficult example | Fallback with 3+ bridge gaps, DCF/EPV dispersion >=40%, terminal value >75%, proxy share data, or very low confidence combined with another issue | `UNP`, `CARR`, `NET` |
| Low classification confidence | Classification confidence <0.80 | 182 of 206. This is a triage signal, not a statement that the company is bad. Review the business archetype and model selection first. |
| Fallback model | The preferred FCFF route fell back to residual income or DDM | 107 of 206. Reconcile the missing bridge fields before relying on the result. |
| Manual override | Issuer-specific routing override exists in configuration or artifact | 63 served tickers. Confirm the override still matches the company's current economics. |
| Weak SEC information | No filed date and a generic SEC browse-company link instead of a precise filing URL | 192 of 206. This is a system-wide approval gate: repair provenance before broad sign-off. |
| Missing SEC information | No SEC source URL | `NET`, `XYZ`. Do not approve until the source filing is linked. |
| High value | Base value is above the global upper outlier threshold | `GS`, `EQIX`, `BLK`, `TDG`, `MSFT`, `DELL`, `ELV`, `PSA`, `CB`, `LMT`, `TRV`, `ALL`, `CI`, `COF`, `MTB`. Recheck units, shares, and terminal assumptions. |
| Low value | Lowest base value in the universe | `PCG` (0.2345). It is an attention point, not a mathematical outlier under the selected test. |

## Important warnings

- **Large DCF/EPV disagreement:** `ADSK`, `CRM`, `DELL`, `MSFT`, `NET`, `NOW`, `STX`, `WDC`, `XYZ`.
- **Terminal-value concentration:** `DELL`, `NET`, `PANW`; `NET` exceeds 85%.
- **Proxy or dilution-prone share count:** `AAPL`, `ADSK`, `ANET`, `CRM`, `DELL`, `FTNT`, `MSFT`, `NET`, `NOW`, `NTAP`, `PANW`, `STX`, `WDC`, `XYZ`.
- **FFO is a non-GAAP approximation:** `AMT`, `CBRE`, `CCI`, `DLR`, `EQIX`, `EXR`, `IRM`, `O`, `PLD`, `PSA`, `VTR`, `WELL`.
- **Potentially stale/odd period end:** `AVGO`, `BIIB`, `C`, `CARR`, `CSX`, `HSY`, `ITW`, `PEG`, `PSA`, `SO`, `SYK`, `UNH`, `WCN`, `WEC`.

## Model-specific approval rules

### Residual income

Confirm business archetype, book equity, ROE, average equity, preferred stock treatment, terminal ROE/payout, and any fallback bridge gaps. Single-period book/ROE is a normal model limitation, not automatic failure.

### Dividend discount model

Confirm the dividend baseline is sustainable, growth and discount-rate assumptions are defensible, terminal growth is conservative, and missing bridge fields do not change the result.

### FCFF DCF

Reconcile revenue and FCFF to filings, require DCF/EPV dispersion below 40% or an explicit explanation, investigate terminal value above 75% (especially 85%), and confirm diluted shares.

### FFO

Reconcile filing FFO, assess AFFO/maintenance capex, test the P/FFO multiple, and review NAV, leases, and property-specific risks. Treat the 12-company FFO group as a focused manual-review set rather than a fully automated approval group.

## Efficient order of work

1. Resolve `NET` and the remaining eight immediate-investigation names.
2. Repair missing/weak SEC provenance once for the system; do not manually duplicate that work 192 times.
3. Review fallback and override names by model family.
4. Finish high-value and warning-based sanity checks.
5. Record a clear approve / approve-with-caveat / reject decision with source links.
