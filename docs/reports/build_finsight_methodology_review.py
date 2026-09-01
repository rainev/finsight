from __future__ import annotations

from html import escape
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "docs" / "reports" / "FinSight_Valuation_Methodology_Review_2026-08-26.pdf"

NAVY = colors.HexColor("#17324D")
BLUE = colors.HexColor("#2C6EAA")
TEAL = colors.HexColor("#138A8A")
INK = colors.HexColor("#1F2933")
MUTED = colors.HexColor("#5D6B78")
LIGHT = colors.HexColor("#F3F6F8")
PALE_BLUE = colors.HexColor("#EAF2F8")
PALE_TEAL = colors.HexColor("#E8F6F4")
PALE_AMBER = colors.HexColor("#FFF5DC")
RULE = colors.HexColor("#D9E1E7")

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="CoverTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=28, leading=33, textColor=NAVY, spaceAfter=12))
styles.add(ParagraphStyle(name="CoverSub", parent=styles["Normal"], fontName="Helvetica", fontSize=13, leading=18, textColor=MUTED, spaceAfter=5))
styles.add(ParagraphStyle(name="H1x", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=18, leading=22, textColor=NAVY, spaceBefore=7, spaceAfter=9))
styles.add(ParagraphStyle(name="H2x", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=11.5, leading=14, textColor=BLUE, spaceBefore=8, spaceAfter=5))
styles.add(ParagraphStyle(name="Bodyx", parent=styles["BodyText"], fontName="Helvetica", fontSize=9.2, leading=13.2, textColor=INK, spaceAfter=6))
styles.add(ParagraphStyle(name="Smallx", parent=styles["BodyText"], fontName="Helvetica", fontSize=7.7, leading=10.2, textColor=MUTED, spaceAfter=3))
styles.add(ParagraphStyle(name="Tablex", parent=styles["BodyText"], fontName="Helvetica", fontSize=7.35, leading=9.4, textColor=INK, spaceAfter=0))
styles.add(ParagraphStyle(name="TableHeadx", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=7.55, leading=9.5, textColor=colors.white, spaceAfter=0))
styles.add(ParagraphStyle(name="Calloutx", parent=styles["BodyText"], fontName="Helvetica", fontSize=10, leading=14, textColor=INK, spaceAfter=0))
styles.add(ParagraphStyle(name="Formula", parent=styles["BodyText"], fontName="Courier", fontSize=8, leading=11, textColor=NAVY, backColor=LIGHT, borderPadding=5, spaceBefore=3, spaceAfter=7))
styles.add(ParagraphStyle(name="Sourcex", parent=styles["BodyText"], fontName="Helvetica", fontSize=7.4, leading=10, textColor=INK, leftIndent=8, firstLineIndent=-8, spaceAfter=4))


def p(text: str, style: str = "Bodyx") -> Paragraph:
    return Paragraph(text, styles[style])


def bullet(text: str) -> Paragraph:
    return p(f"<font color='{BLUE.hexval()}'>&bull;</font> {text}")


def link(label: str, url: str) -> Paragraph:
    return p(f"<link href='{escape(url)}' color='{BLUE.hexval()}'>{escape(label)}</link>", "Sourcex")


def table(rows, widths, header=True):
    converted = []
    for r, row in enumerate(rows):
        converted.append([
            cell if isinstance(cell, Paragraph) else p(str(cell), "TableHeadx" if header and r == 0 else "Tablex")
            for cell in row
        ])
    t = Table(converted, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
    commands = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.35, RULE),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    if header:
        commands.append(("BACKGROUND", (0, 0), (-1, 0), NAVY))
        for i in range(1, len(rows)):
            if i % 2 == 0:
                commands.append(("BACKGROUND", (0, i), (-1, i), LIGHT))
    t.setStyle(TableStyle(commands))
    return t


def callout(title: str, body: str, bg=PALE_BLUE):
    content = Table([[p(f"<b>{title}</b><br/>{body}", "Calloutx")]], colWidths=[7.0 * inch])
    content.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("BOX", (0, 0), (-1, -1), 0.7, TEAL if bg == PALE_TEAL else BLUE),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
    ]))
    return content


def footer(canvas, doc):
    canvas.saveState()
    width, _ = letter
    canvas.setStrokeColor(RULE)
    canvas.setLineWidth(0.5)
    canvas.line(0.55 * inch, 0.42 * inch, width - 0.55 * inch, 0.42 * inch)
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(MUTED)
    canvas.drawString(0.55 * inch, 0.25 * inch, "FinSight Valuation Methodology Review | 26 August 2026")
    canvas.drawRightString(width - 0.55 * inch, 0.25 * inch, f"Page {doc.page}")
    canvas.restoreState()


story = []

# Cover
story += [Spacer(1, 0.55 * inch), p("FINSIGHT", "Smallx"), p("Valuation Methodology Review", "CoverTitle")]
story += [p("What valuation models assume, how FinSight currently works, and how it compares with practical platforms.", "CoverSub")]
story += [Spacer(1, 0.22 * inch), callout("Overall assessment: 7.0 / 10", "A credible, safety-first decision-support system with sound core mathematics. Its main gap is not the basic formulas; it is calibration, specialist coverage, and proving that its confidence labels match real-world outcomes.", PALE_TEAL)]
story += [Spacer(1, 0.28 * inch), p("Prepared for external stakeholders", "H2x"), p("Review date: 26 August 2026<br/>Scope: FinSight's Philippine valuation workbench and the newer U.S. filing-first valuation pipeline. The evidence section focuses on the U.S. pipeline because that is where the current batch protocols and launch-first tests are recorded.", "Bodyx")]
story += [Spacer(1, 0.24 * inch), p("Bottom line", "H2x"), p("FinSight is mathematically credible and unusually transparent about what it knows, estimates, and withholds. Compared with AlphaSpread and GuruFocus, it is currently less mature in coverage and confidence calibration, but stronger in source lineage and safety discipline. It is close to a useful baseline product, provided it is positioned as decision support - not as a precise price target or a promise of returns.", "Bodyx"), PageBreak()]

# Executive summary
story += [p("1. Executive summary", "H1x")]
story += [p("A valuation is not a fact pulled from a filing. It is a reasoned estimate of what a business may be worth under a set of assumptions. The professional standard is therefore not perfect certainty; it is a model that is economically appropriate, internally consistent, transparent about assumptions, and tested against outcomes.")]
story += [callout("What FinSight gets right", "It uses standard valuation families, routes banks away from ordinary enterprise-value logic, keeps filing evidence and policy assumptions separate, uses low/base/high scenarios, and blocks identity, currency, share-count, contradiction, and public-safety failures. These are real strengths.")]
story += [Spacer(1, 8), callout("What still limits FinSight", "The U.S. system uses governed archetype assumptions and policy-calibrated discount rates. Those are acceptable for a baseline, but they are not yet validated enough to justify strong confidence labels. The current staged numeric values are broadly available, but the batch reports label them Low or Conditional Low. That is safe, but it can make the product appear less useful than it is.", PALE_AMBER)]
story += [Spacer(1, 8), p("Recommended launch position", "H2x")]
for text in [
    "Launch as a transparent baseline decision-support tool, with a clear range and a short explanation of the main assumptions.",
    "Keep the internal price comparison private and publish only the derived premium/discount percentage and date, subject to the vendor permission already obtained.",
    "Do not promise that every number is equally reliable. Instead, make the reliability label explain the amount of judgment in the estimate.",
    "Run a point-in-time backtest before changing the 5%, 20%, or 40% reliability thresholds or claiming that High reliability predicts better results.",
]:
    story.append(bullet(text))

story += [Spacer(1, 8), p("FinSight scorecard", "H2x")]
score_rows = [
    ["Area", "Score", "Plain-English assessment"],
    ["Mathematical foundations", "8/10", "Uses recognized DCF, residual-income, dividend, FFO/AFFO, and normalized cash-flow ideas."],
    ["Model selection", "7/10", "Generally respects industry differences; specialist routes are still uneven."],
    ["Assumption governance", "6/10", "Assumptions are explicit and bounded, but many are policy-driven rather than empirically calibrated."],
    ["Data lineage and safety", "9/10", "Strong filing identity, period, unit, currency, share, sanitizer, and Arelle isolation controls."],
    ["Practical coverage", "8/10", "Launch-first work materially increased numeric coverage, especially in Batches 04-06."],
    ["User flexibility", "7/10", "The calculator direction is right; U.S. company-prefilled workflows are still being completed and promoted."],
    ["Backtesting and calibration", "5/10", "Strong deterministic and API evidence, but no completed point-in-time outcome backtest yet."],
    ["Overall", "7/10", "Good foundation for launch as baseline decision support; not yet a mature valuation authority."],
]
story.append(table(score_rows, [1.55*inch, 0.55*inch, 4.9*inch]))
story.append(Spacer(1, 7))
story.append(p("The score is relative to the research standard and practical competitors, not a claim that FinSight can predict market prices.", "Smallx"))

# What valuation is
story += [PageBreak(), p("2. What a good valuation must do", "H1x")]
story += [p("In simple terms, a valuation asks: <b>How much cash, profit, or asset value can this business reasonably create for shareholders, and what is that future value worth today?</b>")]
must_rows = [
    ["Question", "Why it matters"],
    ["What exactly are we valuing?", "The whole operating business, the common shareholders' claim, a bank's regulated equity, a REIT's property assets, or a collection of subsidiaries?"],
    ["Which cash flow belongs to that claim?", "FCFF belongs with WACC. FCFE, dividends, and residual income belong with cost of equity. Mixing them biases the answer."],
    ["Is the current year normal?", "A boom, recession, acquisition, spin-off, product launch, impairment, or restructuring can make the latest number a poor baseline."],
    ["Can growth be paid for?", "Growth requires reinvestment. High growth with low returns on that reinvestment may destroy value."],
    ["What happens after the forecast?", "The terminal value often drives most of a DCF. Terminal growth and steady-state margins must be realistic."],
    ["Who gets the value?", "Enterprise value must be bridged once for debt, cash, preferred equity, noncontrolling interests, leases, and diluted shares."],
    ["What is unknown?", "Unknowns should widen the range or lower confidence. They should not silently become zero or disappear from the arithmetic."],
]
story.append(table(must_rows, [2.05*inch, 4.95*inch]))
story += [Spacer(1, 10), p("The central professional rule", "H2x"), p("Use the cash-flow definition, discount rate, currency, growth pattern, and capital structure assumptions as one coherent package. The most common serious valuation error is to combine inputs that do not belong together.")]
story.append(p("FCFF -> WACC | FCFE / dividends / residual income -> cost of equity", "Formula"))
story += [p("Another important rule is to separate <b>reported facts</b> from <b>analyst assumptions</b>. A forecast can be useful even when it is estimated, but the user must be able to tell which part came from the filing and which part came from the model.")]

# Model library
story += [PageBreak(), p("3. Main valuation models and when to use them", "H1x")]
story += [p("No single model is best for every company. The correct model depends on the company's economics and on which inputs can be measured without distortion.")]
model_rows = [
    ["Model", "Best fit", "Main assumptions", "Main danger"],
    ["FCFF DCF", "Ordinary operating companies: software, retail, consumer, industrials, utilities where debt is financing.", "Revenue, margins, taxes, capex, working capital, WACC, terminal growth.", "Terminal value and long-term growth can dominate the result."],
    ["FCFE DCF", "Companies where leverage and borrowing policy are part of the equity cash flow.", "Net income, capex, working capital, net borrowing, cost of equity.", "Debt policy can make FCFE unstable or negative."],
    ["Dividend DCF", "Stable dividend payers with a durable payout policy.", "Dividend, payout, growth, cost of equity, terminal growth.", "A dividend may be below or above what the company can actually afford."],
    ["Residual income", "Banks, insurers, and firms with reliable book equity but weak or negative free cash flow.", "Book value, ROE, cost of equity, clean-surplus behavior, terminal ROE.", "Accounting quality and book-value adjustments matter."],
    ["Relative multiples", "A cross-check or practical estimate when good peers and normalized metrics exist.", "Peer set, metric definition, growth, margins, risk, and capital structure.", "A cheap peer group can make a weak company look cheap."],
    ["EPV / normalized earnings", "Mature or cyclical companies where current earnings are abnormal.", "Mid-cycle margin or earnings and a conservative discount rate.", "The chosen cycle window can be subjective."],
    ["NAV / RNAV", "REITs, property owners, land-rich firms, asset-heavy or liquidation-oriented cases.", "Property value, cap rates, debt, liabilities, shares, and discounts.", "Property values and cap rates are estimates; book value is not market value."],
    ["SOTP", "Conglomerates and holding companies with distinct subsidiaries.", "Value each segment separately, ownership, parent debt/cash, overhead, holdco discount.", "Consolidated numbers can double-count debt or hide value allocation."],
]
story.append(table(model_rows, [1.05*inch, 1.75*inch, 2.25*inch, 1.95*inch]))
story += [Spacer(1, 8), p("Special cases research highlights", "H2x")]
for text in [
    "Banks and insurers: debt is closer to operating raw material than ordinary financing, and regulatory capital constrains growth. Equity models are more appropriate than standard EV/EBITDA or FCFF.",
    "REITs: FFO and AFFO are useful operating measures, but AFFO is not standardized. NAV needs current property values and liabilities, not just accounting book value.",
    "Cyclicals and commodities: normalize margins or cash flow over a full cycle where possible. If the company changed size, use ratios such as margins or cash flow/revenue rather than a simple absolute average.",
    "R&amp;D-heavy companies: capitalizing R&amp;D can improve the interpretation of profitability and reinvestment, but it does not change current free cash flow. The important effect is on future forecast assumptions.",
    "High-growth or pre-profit companies: the model needs a credible path to positive cash flow or earnings. A wide range can be shown if the path is bounded; an unbounded path should remain withheld.",
]:
    story.append(bullet(text))

# Assumptions
story += [PageBreak(), p("4. Assumptions that drive the answer", "H1x")]
story += [p("The formula is usually not the hardest part. The value can change dramatically when a few assumptions change.")]
assumption_rows = [
    ["Assumption", "What a responsible model should do"],
    ["Starting cash flow", "Use current TTM performance when representative; otherwise normalize with a disclosed reason."],
    ["Growth", "Blend recent results, multi-year company history, and an industry anchor only when needed. Growth must be supported by reinvestment and returns."],
    ["Margins", "Do not extrapolate a temporary peak or trough forever. Fade toward a defensible steady state."],
    ["Reinvestment", "Connect growth to capex, depreciation, working capital, and an implied return on invested capital or equity."],
    ["Discount rate", "Match risk, currency, financing, and cash-flow type. Use sensitivity because small changes matter."],
    ["Terminal growth", "Keep it below the discount rate and generally near long-run economic growth."],
    ["Terminal value", "Show how much of the valuation comes from the terminal value and flag extreme dependence."],
    ["Share count", "Use a reliable diluted denominator and include material dilution such as SBC, convertibles, or buybacks when appropriate."],
    ["Bridge claims", "Include debt, cash, investments, preferred equity, NCI, and leases once and only once."],
    ["One-time events", "Separate acquisitions, divestitures, impairments, lawsuits, restructurings, and pending deals from normal operations."],
]
story.append(table(assumption_rows, [1.45*inch, 5.55*inch]))
story += [Spacer(1, 10), callout("Ceteris paribus is useful, but not a free pass", "Holding everything else constant is useful for understanding one assumption at a time. It does not make an economically important assumption irrelevant. For example, R&amp;D may not change today's reported cash flow, but it can change the expected growth, margin, reinvestment, and competitive position used in the forecast. A practical platform can make a simplifying assumption; it should still disclose it and show sensitivity.", PALE_AMBER)]

# Competitor comparison
story += [PageBreak(), p("5. Comparison with practical platforms", "H1x")]
story += [p("The comparison below uses public descriptions of AlphaSpread and GuruFocus. Their proprietary implementation details are not copied or assumed.")]
comp_rows = [
    ["Dimension", "AlphaSpread", "GuruFocus", "FinSight"],
    ["Primary style", "Automated intrinsic and relative valuation with broad coverage.", "User-editable DCF and other formula-based fair-value tools.", "Filing-first baseline valuation with explicit evidence and policy assumptions."],
    ["Model routing", "Publicly says the operating model is selected from company characteristics.", "Offers earnings- and FCF-based DCF variants; predictability warning is prominent.", "Uses archetype/model routing, with FCFF, residual income, dividend, FFO/AFFO, and practical conditional lanes."],
    ["Forecast inputs", "Publicly says it uses historical performance, industry base rates, and analyst estimates.", "Uses TTM EPS or FCF and lets the user change growth, terminal growth, years, and discount rate.", "Uses filings, TTM/annual history, governed archetype assumptions, and no paid analyst data in this phase."],
    ["Uncertainty", "Shows valuation gaps and method outputs; proprietary details limit auditability.", "Uses predictability rank and fair-value zones; users can change inputs.", "Shows low/base/high, availability, warnings, private reason codes, and hard withholding for unsafe cases."],
    ["Transparency", "Readable outputs; algorithm is proprietary.", "Readable calculator; assumptions are editable.", "Stronger source and arithmetic lineage, but more internal policy complexity."],
    ["Coverage", "Broader and more mature public coverage.", "Broad coverage and simple user workflow.", "Improving quickly, but specialist lanes and production promotion are still incomplete."],
    ["Validation", "Publishes a historical backtest methodology, with stated survivorship/look-ahead limitations.", "Publishes predictability warnings and methodology material.", "Has deterministic replays, API/browser checks, and batch challenges; a full point-in-time outcome backtest remains outstanding."],
]
story.append(table(comp_rows, [1.1*inch, 2.0*inch, 1.85*inch, 2.05*inch]))
story += [Spacer(1, 9), p("Interpretation", "H2x"), p("FinSight should emulate the competitors' <b>user experience and practical coverage</b>, not their opacity. The best combined position is: publish a useful baseline for normal cases, publish a clearly labeled range for bounded uncertainty, expose a calculator for user assumptions, and withhold only when the economic object or evidence is genuinely unsafe.")]

# FinSight audit
story += [PageBreak(), p("6. FinSight protocol audit", "H1x")]
story += [p("The audit reviewed the current U.S. valuation code, policy records, public-artifact rules, and controlled batch reports. The Philippine workbench remains a separate manual model layer; the U.S. pipeline is the newer filing-first system under the current launch-first program.")]
audit_rows = [
    ["Protocol area", "What FinSight currently does", "Assessment"],
    ["FCFF DCF", "Projects revenue, margins, NOPAT, reinvestment, FCFF, terminal value, and bridges enterprise value to equity value per share.", "Sound core structure. Needs continued calibration of growth, ROIC, WACC, terminal value, and bridge claims."],
    ["Banks", "Uses common-equity residual income rather than treating deposits as ordinary debt; includes DDM and justified P/B cross-check logic.", "Correct direction and economically appropriate. Regulatory capital and payout assumptions remain important."],
    ["REITs", "Uses FFO/AFFO-style practical routes and recognizes recurring maintenance costs and lease treatment.", "Good practical direction. NAV/property-value evidence is still less mature than the operating route."],
    ["Normalization", "Uses TTM plus annual history, normalized margins/cash conversion, cyclical ranges, and conditional estimates where uncertainty is bounded.", "Matches industry practice better than the old strict policy."],
    ["Discount rates", "Uses U.S. risk-free rate plus governed equity risk premium, archetype beta, debt spread, target weights, and optional small overlay.", "Defensible baseline policy, but explicitly not market-observed issuer-specific WACC."],
    ["Reliability", "Combines accounting impact, scenario movement, model cap, and source cap; current thresholds are 5%/20% and 20%/40%.", "Clear and deterministic. Current blanket Low rule for material provisional assumptions is conservative and suppresses higher labels."],
    ["Safety", "Withholds for identity, source, period, units, currency, shares, contradictions, unsupported models, unbounded claims/events, unusable values, or public-safety failures.", "Excellent guardrail. This should remain."],
    ["Public output", "Sanitizes public artifacts and keeps raw filing evidence, source manifests, policy records, and vendor data private. Arelle is kept outside the serving path.", "Major strength and a meaningful differentiator."],
    ["Calculator", "The launch-first work has staged company calculators with baseline agreement, assumption tests, and manual-price flow evidence.", "Correct product direction. Production promotion and broader U.S. integration remain separate gates."],
]
story.append(table(audit_rows, [1.15*inch, 3.0*inch, 2.85*inch]))
story += [Spacer(1, 9), p("Important distinction", "H2x"), p("FinSight's current Low labels do not mean every numeric valuation is mathematically bad. They mean the system sees meaningful judgment, range width, or model uncertainty and does not yet trust the result enough to call it Medium or High. That is a confidence-calibration issue, not automatically a formula failure.")]

# Batch evidence
story += [PageBreak(), p("7. What the batch evidence shows", "H1x")]
story += [p("The batch process is useful because it exposes errors early: stale periods, wrong units, double-counted debt or leases, missing share scales, unsupported transactions, and model mismatches. The results also show the trade-off between strict safety and practical coverage.")]
batch_rows = [
    ["Evidence set", "Numeric", "Withheld", "Reliability result"],
    ["Batches 01-03, launch-first staged replay", "27 / 30", "3 / 30", "11 conditional; numeric values remained Low/conditional under the v1.2 contract."],
    ["Batch 04", "10 / 10", "0 / 10", "10 / 10 Conditional Low."],
    ["Batch 05", "10 / 10", "0 / 10", "10 / 10 Conditional Low."],
    ["Batch 06", "10 / 10", "0 / 10", "10 / 10 Conditional Low; current audit record says user-confirmed."],
    ["Staged evidence through Batch 06", "57 / 60", "3 / 60", "All numeric batch results recorded as Low or Conditional Low."],
]
story.append(table(batch_rows, [2.35*inch, 0.8*inch, 0.8*inch, 3.05*inch]))
story += [Spacer(1, 9), callout("What this means", "The launch-first policy is working at its main job: it makes more companies usable without silently turning missing information into zero. The remaining weakness is communication and calibration: users need to see which part is reported, which part is normalized, and how much the assumptions move the value.", PALE_TEAL)]
story += [Spacer(1, 9), p("Evidence quality versus market accuracy", "H2x"), p("The reports show deterministic generation, focused and complete backend suites, real API list/detail parity, calculator behavior, public-artifact scrubbing, and independent challenge passes. Those are strong engineering controls. They do not yet prove that the valuation ranges predict future market returns. That requires a point-in-time backtest with no look-ahead data.")]

# Gaps / roadmap
story += [PageBreak(), p("8. Highest-priority improvements", "H1x")]
priority_rows = [
    ["Priority", "Action", "Why it matters"],
    ["1", "Replace the blanket provisional-assumption Low cap with a calibrated confidence rule based on evidence quality and scenario width.", "Preserves safety while allowing defensible ordinary cases to reach Medium or High after validation."],
    ["2", "Make the model-routing ladder explicit: intrinsic model first, consolidated/normalized fallback second, conditional baseline third, relative/NAV/SOTP only when the evidence is suitable.", "Prevents both unnecessary withholding and economically wrong model use."],
    ["3", "Finish the U.S. company-prefilled calculator and manual-price workflow, keeping vendor EOD private and publishing only derived comparison output.", "Moves FinSight closer to the practical experience users expect from GuruFocus and AlphaSpread."],
    ["4", "Calibrate WACC, terminal growth, growth fade, and normalized margins by archetype using historical data and sensitivity checks.", "Policy assumptions are acceptable, but they need evidence that they behave sensibly across industries."],
    ["5", "Run the point-in-time backtest before changing reliability thresholds or making performance claims.", "Separates a useful range from a range that is merely plausible on paper."],
    ["6", "Keep hard withholding for identity, shares, currency, contradictions, unbounded events, unsupported models, and public-safety failures.", "This is the part that protects users and the brand."],
]
story.append(table(priority_rows, [0.45*inch, 3.75*inch, 2.8*inch]))
story += [Spacer(1, 10), p("What not to do", "H2x")]
for text in [
    "Do not force every company through ordinary FCFF. Banks, REITs, holding companies, captive finance, and transaction-affected companies need different economic objects.",
    "Do not treat a competitor's published number as proof that the number is correct. Competitors often trade strict evidence requirements for coverage and user usefulness.",
    "Do not publish a precise-looking single number when the model is actually a broad range. Show the range and the main reason for the width.",
    "Do not use more code or more tests as a substitute for empirical calibration. The next major proof is a point-in-time backtest and real user comprehension.",
]:
    story.append(bullet(text))

# Final conclusion
story += [PageBreak(), p("9. Conclusion", "H1x")]
story += [callout("Final rating: 7.0 / 10", "FinSight is good enough to become a useful baseline valuation product, provided it is presented honestly and the staged launch evidence is converted into a production release through the remaining gates.", PALE_TEAL)]
story += [Spacer(1, 10), p("In plain language", "H2x")]
for text in [
    "FinSight is not failing because the valuation formulas are fake. The core formulas are recognized and mostly matched to the right company types.",
    "FinSight was initially too strict. The launch-first policy is a sensible correction: it allows a broad, clearly labeled estimate when the uncertainty can be bounded.",
    "FinSight is now closer to AlphaSpread and GuruFocus in practical coverage, but it is more transparent about evidence and uncertainty.",
    "FinSight is not yet as mature as those platforms because the confidence labels, specialist coverage, U.S. calculator promotion, and long-run backtest are not finished.",
]:
    story.append(bullet(text))
story += [Spacer(1, 10), p("Stakeholder recommendation", "H2x"), p("Proceed toward a controlled launch as a <b>baseline decision-support product</b>. Keep the range, method, source date, assumptions, warnings, and reliability visible. Present the valuation as a structured starting point for investor judgment, not as a guaranteed fair price. The product's strongest market position is not pretending to know more than competitors; it is making its assumptions easier to understand and challenge.")]

# Sources
story += [PageBreak(), p("Appendix A. Research sources", "H1x")]
story += [p("Primary and official sources reviewed on 26 August 2026. The report summarizes these sources; it does not reproduce proprietary formulas or paid data.", "Smallx")]
sources = [
    ("Aswath Damodaran - DCF model selection and model fit", "https://pages.stern.nyu.edu/adamodar/pdfiles/eqnotes/model.pdf"),
    ("Aswath Damodaran - DCF models and how to choose the right one", "https://pages.stern.nyu.edu/~adamodar/New_Home_Page/lectures/basics.html"),
    ("Aswath Damodaran - Valuation framework and cash-flow/discount-rate matching", "https://pages.stern.nyu.edu/~adamodar/New_Home_Page/lectures/val.html"),
    ("Aswath Damodaran - Financial service company characteristics", "https://pages.stern.nyu.edu/~adamodar/New_Home_Page/littlebook/financialsvccompanies.htm"),
    ("Aswath Damodaran - Commodity company normalization", "https://pages.stern.nyu.edu/adamodar/New_Home_Page/littlebook/commodityvaluedrivers.htm"),
    ("Aswath Damodaran - R&D capitalization and cash-flow interpretation", "https://pages.stern.nyu.edu/~adamodar/New_Home_Page/valquestions/R%26D.htm"),
    ("CFA Institute - Discounted Dividend Valuation", "https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/discounted-dividend-valuation"),
    ("CFA Institute - Residual Income Valuation", "https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/residual-income-valuation"),
    ("Nareit - Adjusted Funds from Operations (AFFO)", "https://www.reit.com/glossary/adjusted-funds-operations-affo"),
    ("Nareit - Net Asset Value (NAV)", "https://www.reit.com/glossary/net-asset-value"),
    ("AlphaSpread - What is DCF Value?", "https://kb.alphaspread.com/hc/en-us/articles/18217888896017-What-is-DCF-Value"),
    ("AlphaSpread - What is Intrinsic Value?", "https://kb.alphaspread.com/hc/en-us/articles/18213235146513-What-is-Intrinsic-Value"),
    ("AlphaSpread - Valuation backtest methodology", "https://www.alphaspread.com/stock-valuation-backtest"),
    ("GuruFocus - Behind the Numbers: The GuruFocus DCF Calculator", "https://www.gurufocus.com/news/1472279/behind-the-numbers-the-gurufocus-dcf-calculator"),
    ("GuruFocus - DCF User Manual", "https://static.gurufocus.com/download/GuruFocus%20User%20Manual%20DCF%202022.pdf"),
    ("SEC - EDGAR Application Programming Interfaces", "https://www.sec.gov/search-filings/edgar-application-programming-interfaces"),
]
for label, url in sources:
    story.append(link(label + " - " + url, url))

story += [Spacer(1, 10), p("Appendix B. FinSight evidence reviewed", "H1x")]
local_sources = [
    "docs/audit/37-finsight-baseline-decision-policy.md - launch-first policy and withholding rules",
    "docs/audit/44-launch-first-staged-confirmation.md - staged replay, API/browser, and calculator evidence",
    "docs/audit/46-controlled-batch-04-result.md - Batch 04 result",
    "docs/audit/47-controlled-batch-05-result.md - Batch 05 result",
    "docs/audit/48-controlled-batch-06-result.md - Batch 06 result",
    "backend/app/us_valuation/models.py - FCFF DCF and terminal-value implementation",
    "backend/app/valuation/bank.py - residual-income model and cross-checks",
    "backend/app/us_valuation/assumptions.py - policy-calibrated rates and forecast assumptions",
    "backend/app/us_valuation/practical_policy.py - hard safety and publication policy",
    "backend/app/us_valuation/reliability.py - reliability thresholds and label calculation",
    "docs/FINSIGHT.md and docs/PSE-Valuation-Framework.md - original Philippine model library and framework",
]
for item in local_sources:
    story.append(bullet(escape(item)))
story += [Spacer(1, 10), p("Scope note", "H2x"), p("This report is a methodology and product-readiness assessment. It is not a recommendation to buy or sell any security, and it is not an independent audit of every company-level valuation in the universe. The reported scores are professional judgment based on the cited research and the FinSight evidence reviewed.")]

doc = SimpleDocTemplate(
    str(OUTPUT), pagesize=letter, rightMargin=0.55*inch, leftMargin=0.55*inch,
    topMargin=0.55*inch, bottomMargin=0.58*inch,
    title="FinSight Valuation Methodology Review",
    author="FinSight review",
    subject="Valuation models, assumptions, FinSight protocol audit, and competitive assessment",
)
doc.build(story, onFirstPage=footer, onLaterPages=footer)
print(OUTPUT)

