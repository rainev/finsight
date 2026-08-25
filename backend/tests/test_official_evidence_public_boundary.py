"""FOD4 contracts keeping private official-evidence diagnostics out of public APIs."""

from __future__ import annotations

from app.us_valuation.artifacts import sanitize_public_artifact
from app.us_valuation.evidence_router import route_evidence_model


def _private_artifact() -> dict[str, object]:
    return {
        "ticker": "TEST",
        "review": {"publication_state": "review_required"},
        "models": {"residual_income": {"publication_state": "review_required"}},
        "official_evidence": {
            "decisions": [{"source_url": "https://www.sec.gov/private", "reason_codes": ["PRIVATE"]}],
            "specialist_packet": {"rssd": "1039502", "lei": "7H6GLXDRUGQFU57RNE97"},
        },
    }


def test_public_sanitizer_drops_official_evidence_trace_without_changing_public_shape() -> None:
    private = _private_artifact()
    baseline = {key: value for key, value in private.items() if key != "official_evidence"}
    public = sanitize_public_artifact(private)

    assert "official_evidence" not in public
    assert public == sanitize_public_artifact(baseline)


def test_list_and_detail_public_contracts_remain_unchanged_when_private_trace_is_present() -> None:
    private = _private_artifact()
    list_row = sanitize_public_artifact({"ticker": private["ticker"], "official_evidence": private["official_evidence"]})
    list_baseline = sanitize_public_artifact({"ticker": private["ticker"]})
    detail = sanitize_public_artifact(private)
    detail_baseline = sanitize_public_artifact({key: value for key, value in private.items() if key != "official_evidence"})

    assert list_row == list_baseline
    assert detail == detail_baseline


def test_specialist_evidence_routes_to_declared_model_and_never_hardcodes_fcff() -> None:
    route = route_evidence_model(
        {"family": "bank_residual_income", "model": "residual_income"},
        source_kind="fr_y9c",
    )

    assert route.model == "residual_income"
    assert route.model != "fcff_dcf"
