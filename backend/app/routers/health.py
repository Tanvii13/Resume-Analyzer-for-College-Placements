
"""Health, readiness, and operational telemetry endpoints."""

import logging
import os
import shutil
from pathlib import Path

from fastapi import APIRouter, HTTPException, status

from app.database import get_connection
from app.repositories.resume_repository import ResumeRepository


router = APIRouter(tags=["System Health"])
logger = logging.getLogger(__name__)

STORAGE_DIR = (
    Path(__file__).resolve().parents[2]
    / "storage"
    / "resumes"
)


@router.get("/health/live")
def health_live():
    """Confirm that the application process is running."""
    return {
        "status": "alive",
        "service": "resume-analyzer-backend",
    }


@router.get("/health/ready")
def health_ready():
    """Check database connectivity and resume storage readiness."""

    database_ready = False
    storage_ready = False

    try:
        with get_connection() as conn:
            conn.execute("SELECT 1")
        database_ready = True
    except Exception:
        logger.exception("Database readiness check failed.")

    try:
        storage_ready = (
            STORAGE_DIR.is_dir()
            and os.access(STORAGE_DIR, os.R_OK | os.W_OK)
        )
    except OSError:
        logger.exception("Storage readiness check failed.")

    ready = database_ready and storage_ready

    result = {
        "status": "ready" if ready else "not_ready",
        "database": "available" if database_ready else "unavailable",
        "file_storage": "available" if storage_ready else "unavailable",
    }

    if not ready:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=result,
        )

    return result


@router.get("/health/telemetry")
def health_telemetry():
    """Return basic operational counts and local storage utilization."""

    try:
        counts = ResumeRepository.get_telemetry_counts()
        active_users = ResumeRepository.get_active_user_count()
        database_storage_bytes = ResumeRepository.get_storage_bytes()

        if not STORAGE_DIR.exists():
            raise RuntimeError("Resume storage directory is unavailable.")

        disk = shutil.disk_usage(STORAGE_DIR)

        return {
            "status": "success",
            "total_resumes": counts["total_resumes"],
            "processed_resumes": counts["processed_resumes"],
            "active_users": active_users,
            "resume_file_bytes": database_storage_bytes,
            "storage": {
                "total_bytes": disk.total,
                "used_bytes": disk.used,
                "free_bytes": disk.free,
                "used_percent": round(
                    disk.used * 100 / disk.total, 2
                ) if disk.total else 0,
            },
        }

    except Exception as exc:
        logger.exception("Unable to collect system telemetry.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="System telemetry is temporarily unavailable.",
        ) from exc
