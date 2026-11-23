
import os
from datetime import datetime, timezone
from uuid import UUID

from app.database import get_connection


DEFAULT_RETENTION_DAYS = int(
    os.getenv("RESUME_RETENTION_DAYS", "365")
)


class RetentionConfigurationError(Exception):
    """Required retention schema is not available."""


def set_resume_retention(resume_id, retention_days=None):
    """
    Set the expiry date for a resume.

    Requires resumes.retention_expires_at, which must be added/confirmed
    by the database owner.
    """
    resume_id = UUID(str(resume_id))

    days = (
        DEFAULT_RETENTION_DAYS
        if retention_days is None
        else retention_days
    )

    if days <= 0:
        raise ValueError("Retention days must be greater than zero.")

    with get_connection() as conn:
        result = conn.execute(
            """
            UPDATE resumes
            SET retention_expires_at =
                NOW() + (%s * INTERVAL '1 day')
            WHERE id = %s
            RETURNING id, retention_expires_at
            """,
            (days, resume_id),
        ).fetchone()

    if result is None:
        return None

    return {
        "resume_id": str(result[0]),
        "retention_expires_at": result[1],
    }


def get_retention_summary():
    """Return counts for the institutional retention audit."""

    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT
                COUNT(*) AS total_resumes,
                COUNT(*) FILTER (
                    WHERE retention_expires_at IS NOT NULL
                ) AS resumes_with_policy,
                COUNT(*) FILTER (
                    WHERE retention_expires_at <= NOW()
                ) AS expired_resumes,
                COUNT(*) FILTER (
                    WHERE retention_expires_at > NOW()
                ) AS active_retention
            FROM resumes
            """
        ).fetchone()

    return {
        "total_resumes": row[0],
        "resumes_with_policy": row[1],
        "expired_resumes": row[2],
        "active_retention": row[3],
        "checked_at": datetime.now(timezone.utc),
    }


def get_expired_resume_ids(limit=100):
    """Return resume IDs whose retention period has expired."""

    if not 1 <= limit <= 1000:
        raise ValueError("Limit must be between 1 and 1000.")

    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id
            FROM resumes
            WHERE retention_expires_at IS NOT NULL
              AND retention_expires_at <= NOW()
            ORDER BY retention_expires_at ASC
            LIMIT %s
            """,
            (limit,),
        ).fetchall()

    return [str(row[0]) for row in rows]
