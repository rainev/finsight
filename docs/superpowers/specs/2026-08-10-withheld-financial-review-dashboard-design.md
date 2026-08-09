# Withheld Financial Review Dashboard Design

**Date:** 2026-08-10  
**Status:** Approved by user

## Objective

Give the project owner a fast, private way to review the financial data behind all 125 withheld U.S. valuations. The deliverable is not part of the FinSight client application and will not expose private financial evidence to users.

The first version is read-only. It displays the data already captured by the valuation pipeline and creates an Excel workbook for recording human corrections without modifying source artifacts or published valuations.

## Deliverables

1. A self-contained local HTML dashboard that opens in a browser without a server.
2. An Excel workbook with one prefilled row per unresolved financial account.
3. A repeatable generator that rebuilds both artifacts from the current valuation files.
4. Automated checks for record counts, required columns, links, dropdown validation, and safe handling of incomplete review packets.

Generated review artifacts should live below a private/output directory and should not be bundled into the public frontend.

## Source Data and Selection

The generator begins with `backend/app/data/us_valuations/*.json` to identify the complete served universe and selects records whose publication state is withheld. This makes the expected company count independent of the presence of a private artifact.

For each withheld ticker, the generator looks for its corresponding private valuation and filing-evidence packet in the project output directories. The canonical bridge-recovery output is preferred, followed by the model-route rebuild output. If a withheld ticker has no private packet, the dashboard still includes it and displays a clear `private packet unavailable` state using the public-safe metadata that exists.

At design time, 123 private files cover 120 unique withheld companies because IDXX, ROK, and SHW each appear in two output runs. Five withheld companies currently have no private packet: AJG, HSY, MSFT, NOW, and PANW. These counts are diagnostic observations, not hard-coded behavior; the generator reconciles the files afresh on every run.

The generator does not query the internet. SEC links are taken from existing source metadata and filing-evidence captures. Missing links remain visibly missing rather than being guessed.

Source artifacts are read-only. The dashboard and workbook never rewrite them.

## Local Dashboard

### Queue View

The landing view contains one row per withheld company with:

- ticker and issuer name;
- sector and model route;
- controlling filing form, period end, and filed date;
- number of unresolved bridge fields;
- missing-account badges;
- principal withholding reason;
- evidence availability; and
- a link or control to open the company review panel.

The default order is designed for throughput: fewest unresolved fields first, then strongest available evidence, then oldest filing. Search and filters cover ticker/name, sector, model route, account, issue type, filing period, and evidence availability.

Summary counters show total withheld companies, companies with private packets, companies without private packets, and unresolved fields by account.

### Company Review Panel

Selecting a company opens an in-page panel so the reviewer does not lose queue position. It contains:

1. **Review summary** — withholding reasons, warnings, model route, controlling filing, and unresolved-field count.
2. **Missing and ambiguous accounts** — shown first, including current extracted value, unit, field state, source concept, and candidate evidence.
3. **Valuation bridge** — cash, current and noncurrent marketable securities, commercial paper, current and noncurrent debt, current and noncurrent finance leases, preferred equity, noncontrolling interests, and share-count fields.
4. **Income statement** — the normalized income-statement data available to the valuation model.
5. **Balance sheet** — the normalized balance-sheet data available to the valuation model.
6. **Cash-flow statement** — the normalized cash-flow data available to the valuation model.
7. **Source evidence** — filing excerpts, accession/form/period metadata, source selection rationale, and clickable SEC links when available.

The statement preview represents the normalized data FinSight sees. It does not attempt to reproduce every page or table from the SEC filing. A direct link opens the complete official filing where an exact review is necessary.

States are visually distinct: reported, governed filing fact, policy-verified zero, stale, ambiguous, missing, and unavailable. Missing or uncertain fields receive priority styling; valid reported fields remain visible for context.

### Review-Speed Features

- Work by repeated account issue using account filters and counts.
- Keep missing/ambiguous fields above complete fields.
- Provide next/previous controls within the current filtered queue.
- Provide a `next best review` control that prioritizes companies nearest to becoming review-grade.
- Preserve the active filters and queue position while reviewing a company.
- Make filing links and evidence excerpts available beside the affected account.
- Use compact, consistently formatted monetary values while retaining raw values for copying.

The HTML contains its review dataset directly so it can be opened through `file://` without a local API or cross-origin setup.

## Excel Review Workbook

The workbook is the place where the owner records corrections. It does not apply them to FinSight.

### Review Queue Sheet

One row represents one unresolved account. Columns are:

| Column | Behavior |
| --- | --- |
| Ticker | Prefilled and protected |
| Issuer | Prefilled and protected |
| Period end | Prefilled and protected |
| Filing form | Prefilled and protected |
| Account | Prefilled and protected |
| Current extracted value | Prefilled and protected |
| Unit | Prefilled and protected |
| Current field state | Prefilled and protected |
| Correct value | Reviewer input |
| Decision | Reviewer dropdown |
| SEC source | Prefilled clickable hyperlink when available |
| Evidence excerpt | Prefilled and protected |
| Notes | Optional reviewer input |

The decision dropdown contains:

- `Confirmed reported value`
- `Confirmed zero`
- `Not disclosed`
- `Still uncertain`
- `Defer`

`Correct value` and `Decision` are the main reviewer inputs. A zero must be paired with `Confirmed zero`; an empty cell does not mean zero. SEC source and evidence are included for traceability but are not valuation-model inputs. Notes are optional.

### Workbook Usability

- Freeze headers and enable table filters.
- Apply number formats without changing underlying numeric values.
- Visually distinguish editable and protected columns.
- Add dropdown validation to the full decision column.
- Use clickable SEC hyperlinks already present in the source artifacts.
- Include an instructions sheet with the short review workflow and decision meanings.
- Include a summary sheet with company and unresolved-account counts.
- Protect structural cells against accidental edits without requiring a secret password.

Saving the workbook in Excel is supported. A later, separate import step can validate and transform completed rows before applying any override to FinSight.

## Privacy and Safety Boundaries

- The dashboard is local-only and is not added to FinSight navigation or public routes.
- Generated HTML and workbook files remain in a private/output location.
- No raw financial evidence is copied into public valuation artifacts.
- No correction is automatically applied to a valuation.
- No value is inferred when source data is missing.
- Every company remains visible even if its private review packet is incomplete.

## Error Handling

The generator reports, without aborting the entire build:

- withheld companies lacking private packets;
- malformed artifacts;
- missing filing URLs;
- missing statement sections;
- unsupported or unexpected field states; and
- duplicate candidate artifacts requiring deterministic precedence.

The output includes a generation summary and warnings so the reviewer knows whether the dashboard covers all 125 withheld companies.

## Verification and Acceptance Criteria

The implementation is acceptable when:

1. The dashboard contains exactly the withheld universe identified from the current public artifacts (expected: 125 at design time).
2. Every company can be searched and opened, including companies without a private packet.
3. Queue filters and next/previous navigation work entirely offline.
4. Financial-statement tabs show all normalized statement sections available in each private artifact.
5. Missing and ambiguous bridge fields are correctly highlighted and counted.
6. Existing SEC source URLs are clickable in both dashboard and workbook.
7. The workbook contains one row per unresolved account and valid decision dropdowns.
8. Protected source columns and editable reviewer columns are visually clear.
9. Source valuation artifacts have no modifications after generation.
10. Tests cover parsing, source precedence, count reconciliation, HTML generation, workbook structure, dropdowns, and incomplete packets.

## Explicitly Deferred

- Editing values inside the HTML dashboard.
- Importing workbook corrections into FinSight.
- Automatically rerunning or publishing valuations after review.
- Fetching new SEC data from the internet.
- Embedding the dashboard into the customer-facing application.
