
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.dependencies.roles import require_admin
from app.routers.auth import UserResponse
from app.services.rbac_service import (
    InvalidRoleError,
    UnauthorizedActorError,
    UserNotFoundError,
    update_user_role,
)
from app.services.retention_service import (
    DEFAULT_RETENTION_DAYS,
    get_retention_summary,
    get_expired_resume_ids,
)

router = APIRouter(prefix="/admin", tags=["Admin"])


class RoleUpdateRequest(BaseModel):
    role: str = Field(min_length=1, max_length=40)


@router.put("/users/{user_id}/role")
def change_user_role(
    user_id: str,
    request: RoleUpdateRequest,
    admin: UserResponse = Depends(require_admin),
):
    try:
        return update_user_role(
            user_id,
            request.role,
            admin.email,
        )

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format.",
        )

    except UnauthorizedActorError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        )

    except InvalidRoleError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    except UserNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


@router.get("/retention/audit")
def retention_audit(
    admin: UserResponse = Depends(require_admin),
):
    """View institutional resume-retention metrics."""

    try:
        summary = get_retention_summary()
        expired_ids = get_expired_resume_ids(limit=100)

        return {
            "policy": {
                "retention_days": DEFAULT_RETENTION_DAYS,
                "expiry_field": "resumes.retention_expires_at",
            },
            "summary": summary,
            "expired_resume_ids": expired_ids,
            "expired_ids_limit": 100,
        }

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to generate retention audit.",
        ) from exc
