
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.routers.dashboard import require_placement_officer


def test_placement_officer_is_allowed():
    user = SimpleNamespace(role="placement_officer")

    assert require_placement_officer(user) is user


def test_student_is_blocked():
    user = SimpleNamespace(role="student")

    with pytest.raises(HTTPException) as exc:
        require_placement_officer(user)

    assert exc.value.status_code == 403


def test_missing_role_is_blocked():
    user = SimpleNamespace()

    with pytest.raises(HTTPException) as exc:
        require_placement_officer(user)

    assert exc.value.status_code == 403
