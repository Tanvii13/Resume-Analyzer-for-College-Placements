
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
