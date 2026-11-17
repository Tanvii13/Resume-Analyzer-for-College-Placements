
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.routers.auth import get_current_user
from app.services.dashboard_service import (
    calculate_batch_metrics,
    save_batch_statistics,
)

router = APIRouter(prefix="/dashboard", tags=["Placement Dashboard"])


def _user_value(user, key):
    if isinstance(user, dict):
        return user.get(key)
    return getattr(user, key, None)


def require_placement_officer(user=Depends(get_current_user)):
    role = str(_user_value(user, "role") or "").lower()

    allowed_roles = {
        "placement_officer",
        "placement officer",
        "officer",
    }

    if role not in allowed_roles:
        raise HTTPException(
            status_code=403,
            detail="Placement officer access required",
        )

    return user


class StatisticsRequest(BaseModel):
    batch_year: int = Field(ge=2000, le=2100)


@router.get("/overview")
def dashboard_overview(
    batch_year: int = Query(..., ge=2000, le=2100),
    current_user=Depends(require_placement_officer),
):
    try:
        return calculate_batch_metrics(batch_year)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/skill-deficits")
def dashboard_skill_deficits(
    batch_year: int = Query(..., ge=2000, le=2100),
    current_user=Depends(require_placement_officer),
):
    try:
        metrics = calculate_batch_metrics(batch_year)
        return {
            "batch_year": batch_year,
            "top_missing_skills": metrics["top_missing_skills"],
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/refresh")
def refresh_dashboard_statistics(
    payload: StatisticsRequest,
    current_user=Depends(require_placement_officer),
):
    try:
        metrics = calculate_batch_metrics(payload.batch_year)
        save_batch_statistics(payload.batch_year, metrics)
        return {
            "message": "Dashboard statistics refreshed",
            "statistics": metrics,
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
