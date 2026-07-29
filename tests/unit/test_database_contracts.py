"""Fast checks for database metadata and bounded repositories."""

import pytest

from app.database.models import Base
from app.database.repositories import _bounded


def test_metadata_contains_all_phase_three_tables() -> None:
    assert set(Base.metadata.tables) == {
        "machines",
        "sensor_readings",
        "maintenance_records",
        "incidents",
        "work_orders",
        "agent_sessions",
        "agent_feedback",
        "approval_actions",
    }


@pytest.mark.parametrize("limit", [0, 101])
def test_repository_limits_are_bounded(limit: int) -> None:
    with pytest.raises(ValueError, match="between 1 and 100"):
        _bounded(limit)


def test_repository_accepts_boundary_limits() -> None:
    assert _bounded(1) == 1
    assert _bounded(100) == 100
