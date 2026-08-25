import json
from pathlib import Path
import sys

import pytest

from app.us_valuation.batch_02_recovery import RECOVERY_TICKERS
from app.us_valuation.batch_02_revision_retry import REVISION_RETRY_DECISIONS

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from run_batch_02_revision_retry import _evidence_summary, _validate_inputs


def test_revision_retry_is_exactly_six_and_clears_no_release_condition() -> None:
    assert tuple(row.ticker for row in REVISION_RETRY_DECISIONS) == RECOVERY_TICKERS
    assert all(row.prior_blocker_cleared is False for row in REVISION_RETRY_DECISIONS)
    assert all(row.remaining_release_condition for row in REVISION_RETRY_DECISIONS)
    assert all(row.evidence_improvement for row in REVISION_RETRY_DECISIONS)


def test_evidence_summary_preserves_zero_range_and_unresolved_without_coercion() -> None:
    issuer = {
        "ticker": "TEST",
        "decisions": [
            {
                "request": {"required_field": "preferred_equity", "request_id": "a"},
                "status": "explicit_zero",
                "selected_source": "companyfacts_current",
                "selected_value": 0.0,
                "selected_range": None,
                "reason_codes": ["REPORTED_REPORTED"],
            },
            {
                "request": {"required_field": "leases", "request_id": "b"},
                "status": "bounded_estimate",
                "selected_source": "annual_carry_forward",
                "selected_value": None,
                "selected_range": [10.0, 20.0],
                "reason_codes": ["BOUNDED"],
            },
            {
                "request": {"required_field": "shares", "request_id": "c"},
                "status": "unresolved",
                "selected_source": None,
                "selected_value": None,
                "selected_range": None,
                "reason_codes": ["NO_CANDIDATE"],
            },
        ],
    }
    result = _evidence_summary(issuer)
    assert result["status_counts"] == {
        "bounded_estimate": 1,
        "explicit_zero": 1,
        "unresolved": 1,
    }
    by_field = {row["required_field"]: row for row in result["decisions"]}
    assert by_field["preferred_equity"]["selected_value"] == 0.0
    assert by_field["leases"]["selected_range"] == [10.0, 20.0]
    assert by_field["shares"]["selected_value"] is None


def test_retry_rejects_nondeterministic_policy_inputs(tmp_path: Path) -> None:
    prior = tmp_path / "prior"
    prior.mkdir()
    policy_a = tmp_path / "a.json"
    policy_b = tmp_path / "b.json"
    replay = tmp_path / "replay.json"
    policy_a.write_text("{}")
    policy_b.write_text('{"different": true}')
    replay.write_text("{}")
    with pytest.raises(ValueError, match="not deterministic"):
        _validate_inputs(prior, policy_a, policy_b, replay, tmp_path / "out")

