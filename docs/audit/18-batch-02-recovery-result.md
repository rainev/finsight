# Batch 02 one-attempt recovery result

**Valuation date:** 2026-08-14

**Recovery denominator:** OMC, TTWO, CHTR, CMCSA, META, WBD

**Status:** verified — user confirmation needed

## Exact outcome

- Recovery attempted: **6/6**
- Newly numeric: **0/6**
- Still withheld: **6/6**
- Invalid: **0/6**
- Final Batch 02: **4 numeric Low / 6 withheld / 0 invalid**
- Cumulative universe-reset withheld register: **7 companies** — NEE plus the six Batch 02
  companies
- Serving promotions: **0**

Success was not treated as a quota. Each recovery stopped when the smallest intuitive workaround
still required a missing material fact.

## Public-method comparison

Only public practices were adopted:

- Alpha Spread says it selects operating models from company characteristics, uses historical
  performance/industry/analyst inputs, and matches WACC or cost of equity to the model. It also
  identifies its algorithm as proprietary, so no formula or displayed valuation was copied:
  `https://kb.alphaspread.com/hc/en-us/articles/18217888896017-What-is-DCF-Value`.
- GuruFocus permits EPS or FCF inputs but requires the matching growth rate and warns that low
  predictability makes fair value volatile:
  `https://static.gurufocus.com/download/GuruFocus%20User%20Manual%20DCF%202022.pdf`.

These practices support FinSight's model selection, aligned flow/growth inputs, scenario ranges,
and Low/withheld warnings. A competitor number does not supply missing issuer evidence.

## Company-by-company attempt

### OMC — predecessor-combined cash FCFF: withheld

The current filing says IPG enters Omnicom's statements only after the 2025-11-26 close and that
post-close operations, financial condition, and cash flows are not comparable to history. H1 2026
integration/acquisition costs are reported, but no combined pro forma cash-flow history exists.
Mechanically splicing legacy OMC and IPG would ignore eliminations, purchase accounting, stock
consideration, acquired claims, and integration scope.

Next valid trigger: a full post-close annual period or issuer-filed comparable combined pro forma
cash-flow history.

### TTWO — pipeline-aware software cash FCFF: withheld

The filing identifies GTA VI's 2026-11-19 release, current pre-orders, development assets, cash
investment, amortization, and impairment. It also says a few titles' release timing and commercial
success materially affect results. A release date is not a source-backed units/price/margin or
cash-conversion range; current normalized value remains nonpositive.

Next valid trigger: a post-release quarter plus issuer-supported bookings/revenue or realized cash
conversion covering the release period.

### CHTR — transaction-conditioned cable FCFF: withheld

Cox terms are source-fixed: `$4.15bn` cash, `$6bn` convertible preferred at 6.875%, about 33.6m
common units, and about `$12.4bn` assumed net debt/finance leases. The Liberty Broadband
combination is also pending. No filed combined Cox operating cash flow/capex or final closing
dilution exists, so a post-close enterprise/equity bridge cannot be completed without invention.

Next valid trigger: close/termination plus filed purchase accounting and pro forma cash evidence.

### CMCSA — post-separation two-company SOTP: withheld

The NBCUniversal/Sky spin remains subject to board approval, tax opinions, regulatory approval,
and financing; terms/timing are not assured. The retained stake may be up to 19.9% for up to one
year. Current statements do not give effect to the separation, and no standalone cash flows,
corporate-cost split, or debt/cash allocation is filed.

Next valid trigger: Form 10/pro forma standalone financials and final financing/distribution terms.

### META — commitment-aware growth FCFF: withheld

The filing reports `$349.31bn` non-cancelable commitments, including `$53.52bn` due in 2026 and
`$81.65bn` in 2027; `$278.99bn` of uncommenced leases; `$68bn` of additional July leases; and
`$10.80bn` restricted cash. It does not provide a mutually exclusive waterfall separating cloud,
equipment, owned infrastructure, and lease cash already represented in OCF/capex. Treating totals
as debt or adding them together would double count; ignoring them would omit material cash.

Next valid trigger: a filed schedule reconciling overlap, timing, and cash classification.

### WBD — standalone plus conditional transaction paths: withheld

The signed agreement specifies `$31.00` cash per share plus `$0.00277778` per day after
2026-09-30. That is retained privately as **conditional merger consideration**, not intrinsic
value. Litigation, regulatory clearance, termination rights, and an alternative separation still
create materially different issuer states. No close probability was invented.

Private illustration only: `$31.00` through 2026-09-30 and `$31.68611166` on 2027-06-04 if the
unchanged ticking formula applies. `published_as_intrinsic_value=false` and
`probability_weighted=false`.

Next valid trigger: close, termination, amendment, material court/agency action, or a finite filed
standalone/separation state.

## Challenge and provenance correction

The first recovery candidate had correct accessions but mistakenly used the structural parser's
latest extracted instant as the report period. Five of six period labels were wrong. The runner now
locates the exact accession in SEC submissions and uses its `reportDate`, while asserting CIK,
form, filing date, primary document, cutoff, and structural accession parity.

A six-company regression deliberately supplies misleading structural period values and proves the
submissions period wins. Candidate B passed independent Luna-High review with no remaining
Critical or Important finding. All six final receipts use period `2026-06-30`.

## Determinism, tests, API, and serving safety

- Verified recovery runs A/B: **21 files each**, byte-identical tree hash
  `6a46fe37c0421307ee1f2c22d1d5b5a56c5ae4a616ad5c8f25234c1a569ee7b6`.
- Recovery report SHA-256 A/B:
  `00cb240eeaadc1351b8312c29c9d9cbab13368a285981fb0dac56f05ddb61d20`.
- Focused recovery/policy/API suite: **40 passed**.
- Complete backend suite: **1107 passed, 3 skipped**, one existing Python `crypt` deprecation
  warning.
- Real Uvicorn staged API: list HTTP 200/count 10; details 10/10 HTTP 200; exact range/state/
  reliability parity; zero private recovery/source/policy fields leaked; clean shutdown.
- API receipt SHA-256:
  `332771b6e926d4c9b75e2fae0720b5bb32039c58ff296c36c301a0947827ed7c`.
- All ten public artifacts are byte-identical to the verified initial Batch 02 artifacts.
- Protected serving roots remained byte-identical; nothing was promoted.
- Cumulative register contains seven sorted, unique ticker/CIK entries; machine-readable register
  SHA-256: `880c82cfa5c8f0d2558ec93302dd0346fe3508b593bfeb5a9a787914083626a5`.

## Stop boundary

The six Batch 02 companies have consumed their one automatic recovery attempt and are now in the
cumulative withheld register. A future revisit requires explicit user instruction and the named
new evidence trigger. Batch 03 was not started; no merge or deployment occurred.
