"""Export curated US valuation artifacts as Obsidian-friendly Markdown notes.

This exporter is deliberately local and deterministic. It does not call the SEC,
copy raw XBRL, or include private source payloads in the vault.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ARTIFACTS = ROOT / "backend" / "app" / "data" / "us_valuations"
DEFAULT_OUTPUT = ROOT / "Finsight" / "US Valuations"
SAFE_FILENAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


def _display_name(value: Any) -> str:
    text = str(value or "").strip()
    return text.replace("_", " ").replace("-", " ").title() or "Not reported"


def _value(value: Any, *, percent: bool = False) -> str:
    if value is None or isinstance(value, bool):
        return "Not reported"
    if isinstance(value, (int, float)):
        if not math.isfinite(value):
            return "Not reported"
        if percent:
            return f"{value:.2%}"
        return f"{value:,.2f}"
    return str(value)


def _bullet_items(values: Any) -> str:
    if not values:
        return "- None reported"
    if isinstance(values, (str, bytes)) or not isinstance(values, list):
        values = [values]
    return "\n".join(f"- {str(item).strip()}" for item in values if str(item).strip()) or "- None reported"


def _relative_link(output_dir: Path, target: Path) -> str:
    try:
        return Path(__import__("os").path.relpath(target.resolve(), output_dir.resolve())).as_posix()
    except ValueError:
        return target.as_posix()


def _model_section(models: dict[str, Any]) -> str:
    if not models:
        return "- None reported"
    lines: list[str] = []
    for name in sorted(models):
        model = models[name] or {}
        lines.append(
            f"- **{_display_name(name)}**: {_value(model.get('intrinsic_value_per_share'))} "
            f"per share; state `{model.get('publication_state', 'not_reported')}`"
        )
        warnings = model.get("warnings") or []
        for warning in warnings:
            lines.append(f"  - Warning: {warning}")
    return "\n".join(lines)


def render_valuation_note(artifact: dict[str, Any], artifact_path: Path, output_dir: Path | None = None) -> str:
    """Render only review-relevant, provenance-linked fields from one artifact."""

    issuer = artifact.get("issuer") or {}
    source = artifact.get("source_financial_statement") or {}
    policy = artifact.get("model_policy") or {}
    methodology = artifact.get("methodology") or {}
    assumptions = artifact.get("public_assumptions") or {}
    scenarios = artifact.get("scenario_range") or {}
    review = artifact.get("review") or {}
    automated_review = artifact.get("automated_review") or {}
    ticker = issuer.get("ticker") or artifact_path.stem.upper()
    output_dir = output_dir or artifact_path.parent
    local_artifact = _relative_link(output_dir, artifact_path)
    source_url = source.get("url") or ""
    source_link = f"[SEC filing]({source_url})" if source_url else "SEC filing URL not reported"

    scenario_lines = (
        f"- Low: {_value(scenarios.get('low'))}\n"
        f"- Base: {_value(scenarios.get('base'))}\n"
        f"- High: {_value(scenarios.get('high'))}\n"
        f"- Interpretation: {scenarios.get('label', 'Not reported')}"
    )

    return f"""---
title: {ticker} — US valuation review
ticker: {ticker}
market: {artifact.get('market', 'US')}
valuation_date: {artifact.get('valuation_date', 'not_reported')}
publication_state: {review.get('publication_state', 'not_reported')}
tags:
  - finsight
  - valuation/us-equities
  - review-required
---

# {ticker} — {issuer.get('issuer_name', 'Unknown issuer')}

> Curated from the local SEC/XBRL-derived valuation artifact. This note is a review aid, not an investment recommendation.

## Identity

- Company: {issuer.get('issuer_name', 'Not reported')}
- CIK: `{issuer.get('cik', 'Not reported')}`
- Sector: {issuer.get('finsight_sector', 'Not reported')}
- Primary archetype: `{issuer.get('primary_archetype', 'Not reported')}`
- Classification confidence: {_value(issuer.get('classification_confidence'), percent=True)}

## SEC source

- Form: `{source.get('form', 'Not reported')}`
- Period end: `{source.get('period_end', 'Not reported')}`
- Filed date: `{source.get('filed_date', 'Not reported')}`
- Accession: `{source.get('accession', 'Not reported')}`
- Link: {source_link}
- Local artifact: [`{artifact_path.name}`]({local_artifact})
- Source policy: {methodology.get('source_policy', 'Not reported')}

## Model

- Primary model: **{_display_name(policy.get('primary'))}**
- Supporting models: {_display_name(', '.join(policy.get('supporting') or [])) if policy.get('supporting') else 'None reported'}
- Selection reason: {policy.get('reason', 'Not reported')}
- Fallback from: `{policy.get('fallback_from') or 'None'}`
- Framework: `{methodology.get('sector_framework', 'Not reported')}`

### Model outputs

{_model_section(artifact.get('models') or {})}

## Key assumptions

- Cost of equity: {_value(assumptions.get('cost_of_equity'), percent=True)}
- Risk-free rate: {_value(assumptions.get('risk_free_rate'), percent=True)}
- Equity risk premium: {_value(assumptions.get('equity_risk_premium'), percent=True)}
- Policy beta: {_value(assumptions.get('policy_beta'))}
- Book value per share: {_value(assumptions.get('book_value_per_share'))}
- Current ROE: {_value(assumptions.get('current_roe'), percent=True)}
- Terminal ROE: {_value(assumptions.get('terminal_roe'), percent=True)}
- Terminal growth: {_value(assumptions.get('terminal_growth'), percent=True)}

## Scenario range

{scenario_lines}

## Review status

- Publication state: `{review.get('publication_state', 'not_reported')}`
- Confidence grade: `{review.get('confidence_grade', 'not_reported')}`

### Errors

{_bullet_items(review.get('errors'))}

### Warnings

{_bullet_items(review.get('warnings'))}

## Automated review

- Decision: `{automated_review.get('decision', 'not_reported')}`
- Evidence status: `{automated_review.get('evidence_status', 'not_reported')}`
- Blocking reasons:

{_bullet_items(automated_review.get('blocking_reasons'))}

- Repair actions:

{_bullet_items(automated_review.get('repair_actions'))}

- Repair attempts:

{_bullet_items([json.dumps(attempt, sort_keys=True) for attempt in automated_review.get('repair_attempts', [])])}

## Review links

- Source data is SEC/XBRL-derived; raw XBRL is intentionally not copied into this note.
- Re-run the local valuation assurance workflow before treating the result as sound.
"""


def _load_artifacts(artifact_dir: Path) -> tuple[list[tuple[Path, dict[str, Any]]], list[str]]:
    artifacts: list[tuple[Path, dict[str, Any]]] = []
    errors: list[str] = []
    for path in sorted(artifact_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict) or not isinstance(data.get("issuer"), dict):
                raise ValueError("missing issuer object")
            ticker = str(data["issuer"].get("ticker") or "").upper()
            if not SAFE_FILENAME.fullmatch(ticker):
                raise ValueError("issuer ticker is missing or unsafe")
            artifacts.append((path, data))
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
            errors.append(f"{path.name}: {exc}")
    return artifacts, errors


def export_valuations(artifact_dir: Path, output_dir: Path, *, dry_run: bool = False) -> dict[str, Any]:
    """Export local valuation artifacts to deterministic Obsidian notes."""

    artifact_dir = Path(artifact_dir)
    output_dir = Path(output_dir)
    artifacts, errors = _load_artifacts(artifact_dir)
    seen: set[str] = set()
    rendered: list[tuple[str, str]] = []
    for path, artifact in artifacts:
        ticker = str(artifact["issuer"]["ticker"]).upper()
        if ticker in seen:
            errors.append(f"{path.name}: duplicate ticker {ticker}")
            continue
        seen.add(ticker)
        rendered.append((ticker, render_valuation_note(artifact, path, output_dir)))

    if not dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)
        for ticker, note in rendered:
            (output_dir / f"{ticker}.md").write_text(note, encoding="utf-8")
        index = """---\ntitle: Finsight US valuation index\ntags:\n  - finsight\n  - valuation/us-equities\n---\n\n# Finsight US valuations\n\nCurated SEC/XBRL-derived valuation notes. Raw XBRL is kept outside the Obsidian vault.\n\n"""
        index += "\n".join(f"- [[{ticker}]]" for ticker, _ in rendered) or "- No valid valuation artifacts exported"
        (output_dir / "README.md").write_text(index + "\n", encoding="utf-8")

    return {"exported": len(rendered), "errors": errors, "output": str(output_dir), "dry_run": dry_run}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, default=DEFAULT_ARTIFACTS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    result = export_valuations(args.artifacts, args.output, dry_run=args.dry_run)
    print(json.dumps(result, indent=2))
    return 1 if result["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
