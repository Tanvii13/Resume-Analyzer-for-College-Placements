"""
Role-based access control dependencies for Sprint 4 (US-14).
"""

from fastapi import Depends, HTTPException, status

from app.routers.auth import UserResponse, get_current_user


AUTHORIZED_STAFF_ROLES = {
    "placement_officer",
    "career_counselor",
}


def require_staff_or_counselor(
    current_user: UserResponse = Depends(get_current_user),
) -> UserResponse:
    """
    Allow only placement officers and career counselors to access
    protected student inspection and review functionality.
    """

    normalized_role = (current_user.role or "").strip().lower()

    if normalized_role not in AUTHORIZED_STAFF_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: Placement staff or career counselor role required.",
        )

    return current_user


def require_career_counselor(
    current_user: UserResponse = Depends(get_current_user),
) -> UserResponse:
    """Allow only career counselors to submit formal resume reviews."""

    if (current_user.role or "").strip().lower() != "career_counselor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only career counselors can submit resume reviews.",
        )

    return current_user
