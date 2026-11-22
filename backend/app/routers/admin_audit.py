
"""Sprint 6 - Member 3
Institutional fairness and governance audit APIs.
"""

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
)

from app.dependencies.roles import require_admin
from app.routers.auth import UserResponse

from app.services.fairness_persistence_service import (
    get_decision_metrics,
    get_fairness_audit_logs,
)


router = APIRouter(
    prefix="/admin",
    tags=["Institutional Audit"],
)


@router.get("/fairness/audit-logs")
def fairness_audit_logs(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    bias_only: bool = False,
    admin: UserResponse = Depends(require_admin),
):
    """Retrieve institutional fairness audit records."""

    try:
        records = get_fairness_audit_logs(
            limit=limit,
            offset=offset,
            bias_only=bias_only,
        )

        return {
            "count": len(records),
            "limit": limit,
            "offset": offset,
            "bias_only": bias_only,
            "audit_logs": records,
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve fairness audit logs.",
        ) from exc


@router.get("/governance/decision-metrics")
def governance_decision_metrics(
    admin: UserResponse = Depends(require_admin),
):
    """Retrieve institutional human-decision statistics."""

    try:
        return get_decision_metrics()

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Unable to generate governance decision metrics.",
        ) from exc
