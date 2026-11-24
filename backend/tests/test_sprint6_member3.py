
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.services import fairness_persistence_service as service


def test_rejects_unknown_decision_state():

    with pytest.raises(ValueError, match="Unsupported"):

        service.save_placement_decision(
            uuid4(),
            "officer@example.edu",
            "REJECTED",
        )


def test_requires_rationale_for_final_decision():

    with pytest.raises(ValueError, match="rationale"):

        service.save_placement_decision(
            uuid4(),
            "officer@example.edu",
            "REJECTED_BY_OFFICER",
            "too short",
        )


def test_rejects_score_outside_range():

    with pytest.raises(ValueError, match="between 0 and 100"):

        service.save_placement_decision(
            uuid4(),
            "officer@example.edu",
            "PENDING_OFFICER_REVIEW",
            automated_score=101,
        )


def test_validates_fairness_audit_data():

    with pytest.raises(ValueError, match="JSON object"):

        service.save_fairness_audit(
            uuid4(),
            [],
            False,
        )

    with pytest.raises(ValueError, match="list"):

        service.save_fairness_audit(
            uuid4(),
            {},
            False,
            "not-a-list",
        )


def test_validates_audit_log_limit():

    with pytest.raises(ValueError, match="limit"):

        service.get_fairness_audit_logs(
            limit=0,
        )


def test_decision_metrics_calculation():

    conn = MagicMock()

    conn.execute.return_value.fetchone.return_value = (
        10,
        4,
        3,
        1,
        2,
    )

    with patch.object(
        service,
        "get_connection",
    ) as get_connection:

        get_connection.return_value.__enter__.return_value = conn

        result = service.get_decision_metrics()

    assert result["total_decisions"] == 10

    assert result["shortlisted"] == 4

    assert result["rejected"] == 3

    assert result["referred_for_manual_evaluation"] == 1

    assert result["potential_overrides"] == 2

    assert result["potential_override_rate_percent"] == 20.0
