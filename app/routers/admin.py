from fastapi import APIRouter, Depends, HTTPException, status

from app.routers.auth import UserResponse, get_current_user
from app.services.retention_service import (
    get_retention_summary,
    get_expired_resume_ids,
)

router = APIRouter(
    prefix="/admin",
    tags=["Retention Administration"],
)


def require_admin(
    current_user: UserResponse = Depends(get_current_user),
) -> UserResponse:
    if (current_user.role or "").strip().lower() != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access required.",
        )
    return current_user


@router.get("/retention/audit")
def retention_audit(
    current_user: UserResponse = Depends(require_admin),
):
    """View institutional resume-retention metrics."""

    try:
        summary = get_retention_summary()
        expired_ids = get_expired_resume_ids(limit=100)

        return {
            "policy": {
                "retention_days": 365,
                "expiry_field": "resumes.retention_expires_at",
            },
            "summary": summary,
            "expired_resume_ids": expired_ids,
            "expired_ids_limit": 100,
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Unable to generate retention audit.",
        ) from exc