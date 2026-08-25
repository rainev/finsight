# Audit 26 — FOD3 free official specialist-source result

Status: **verified with exact blockers — zero specialist packets promotable**

Reference: `docs/audit/21-specialist-official-sources.md` and PLAN Phase 3.

## Implemented

- Private specialist identity/bridge/fact/packet contracts enforce exact CIK/RSSD/LEI/FERC identity, separate valuation cutoff, period/filed dates, unit/range/sign policy, parent versus subsidiary authority, consolidation/allocation proof, official payload versus normalized hashes, and parser version.
- A checked-in JPM/BAC parent crosswalk maps SEC CIK, NIC RSSD, and GLEIF LEI with exact source URLs. Official GLEIF payloads are retained under untracked output and validate legal name plus active/issued status.
- FR Y-9C/Call Report parsers require the complete normalized capital/equity/RWA/ratio/credit set. Current FR Y-9C codes use MDRM series/derivations, including CET1 `BHCAP859|BHCWP859`, RWA `BHCAA223|BHCWA223`, and ratio `BHCAP793|BHCWP793`. Call Reports remain subsidiary corroboration and cannot promote to the parent.
- FERC parsers preserve regulated identity and require an exact source payload plus a passing ownership/allocation reconciliation before parent promotion.
- SEC Exhibit 99 discovery is cutoff-safe; REIT parsing identifies the current-period column, preserves raw signed adjustments and normalized economic magnitudes, retains issuer-defined AFFO, and records unexplained reconciliation residuals.
- Generic bank/utility/REIT Companyfacts fallbacks now require filed lineage and deterministically choose the latest eligible filing/amendment, never the largest numeric value.

## Real identity/source evidence and blockers

Final A/B specialist receipt: `output/specialist-sources/specialist-receipt-g.json` and `specialist-receipt-h.json`; SHA-256 `9eaf50d4c841ab2b5ccca5b5104c49efe01eeb0ee100fde2326b5b537a1a26b2`; byte comparison exact.

### JPM and BAC

- Parent crosswalks verified:
  - JPM: CIK `0000019617`, RSSD `1039502`, LEI `8I5DZWZKVSZI1NUHU748`.
  - BAC: CIK `0000070858`, RSSD `1073757`, LEI `9DJT3UXIJIZJI4WXO774`.
- Official GLEIF source hashes: JPM `d996b173…`; BAC `a9240483…`.
- Current requested period: 2026-06-30 FR Y-9C. The documented FFIEC/NIC distribution endpoint returned HTTPS 403 twice. Both cases are `source_access_blocked` with empty facts and `parent_promotable=false`.
- No subsidiary Call Report was combined into either parent because no verified subsidiary ownership/allocation packet was captured.

### NEE / FPL

- SEC public parent identity is verified, but FPL's FERC CID, current public Form 1/3-Q instance endpoint, and parent allocation bridge were not captured through the accessible official viewer/eLibrary surfaces.
- Outcome: `identity_and_payload_unresolved` with `FERC_CID_NOT_VERIFIED`, `FERC_PUBLIC_XBRL_PACKET_NOT_LOCALLY_RETRIEVABLE`, and `PARENT_ALLOCATION_BRIDGE_NOT_PROVEN`; no facts; non-promotable.

### Realty Income

- Exact pre-cutoff official filing: 2026-05-06 Form 8-K, accession `0000726728-26-000028`, Exhibit 99.2 `realtyincomeq12026supple.htm`, period 2026-03-31.
- Web-verified observations preserve the supplement's issuer-defined Q1 values: FFO 993,601; AFFO 1,057,553; straight-line rent/expenses raw `(39,510)`; recurring capex raw `(170)`; occupancy 98.9%; USD/shares in thousands as applicable.
- The normalized FFO-minus-two-adjustments calculation leaves an unexplained 103,632 residual because the full issuer reconciliation has additional adjustments. Status remains `unresolved_residual`.
- The original SEC attachment bytes were not locally captured because no monitored SEC contact is configured. The receipt labels the values `WEB_EXTRACTED_VALUES_NOT_SOURCE_PAYLOAD`, retains only an observation-fixture hash, and is non-promotable.

## Verification

- `56 passed in 0.14s` across specialist packet, bank, FERC, REIT, adapter, exact-fact selection, and routing/cutoff tests.
- Future-filed bank/FERC/REIT inputs, wrong regulatory codes/RSSD/units, unproven allocation, multi-period ambiguity, invalid ratios, and same-period largest-value selection all fail closed.
- Serving hashes are unchanged and `promotable_packet_count=0`.

Conclusion: the specialist pipeline mechanics and identity gates are implemented. The real representative outcome is zero usable packets due to exact source/payload/allocation blockers; no normalized row or web observation is misrepresented as official promotable evidence.
