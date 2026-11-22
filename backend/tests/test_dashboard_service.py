"""
Access-control tests for the Sprint 4 placement dashboard.

The dashboard originally had its own `require_placement_officer` check; commit a3d1be7
replaced it with the shared `require_staff_or_counselor` dependency, so these tests now
cover that dependency and confirm the dashboard routes use it.
"""

import pytest
from fastapi import HTTPException

from app.dependencies.roles import require_staff_or_counselor
from app.routers.auth import UserResponse
from app.routers.dashboard import router as dashboard_router


def test_placement_officer_is_allowed():
    user = UserResponse(email="officer@college.edu", role="placement_officer")

    assert require_staff_or_counselor(user) is user


def test_career_counselor_is_allowed():
    user = UserResponse(email="counselor@college.edu", role="career_counselor")

    assert require_staff_or_counselor(user) is user


def test_student_is_blocked():
    user = UserResponse(email="student@college.edu", role="student")

    with pytest.raises(HTTPException) as exc:
        require_staff_or_counselor(user)

    assert exc.value.status_code == 403


def test_missing_role_is_blocked():
    user = UserResponse(email="someone@college.edu", role="")

    with pytest.raises(HTTPException) as exc:
        require_staff_or_counselor(user)

    assert exc.value.status_code == 403


def test_every_dashboard_route_requires_staff():
    for route in dashboard_router.routes:
        dependencies = [d.call for d in route.dependant.dependencies]
        assert require_staff_or_counselor in dependencies, route.path
