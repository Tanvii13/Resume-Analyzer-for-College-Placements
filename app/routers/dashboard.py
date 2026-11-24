
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.dependencies.roles import require_staff_or_counselor
from app.services.dashboard_service import (
    calculate_batch_metrics,
    save_batch_statistics,
)

router = APIRouter(prefix="/dashboard", tags=["Placement Dashboard"])


class StatisticsRequest(BaseModel):
    batch_year: int = Field(ge=2000, le=2100)


@router.get("/overview")
def dashboard_overview(
    batch_year: int = Query(..., ge=2000, le=2100),
    current_user=Depends(require_staff_or_counselor),
):
    try:
        return calculate_batch_metrics(batch_year)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/skill-deficits")
def dashboard_skill_deficits(
    batch_year: int = Query(..., ge=2000, le=2100),
    current_user=Depends(require_staff_or_counselor),
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
    current_user=Depends(require_staff_or_counselor),
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
