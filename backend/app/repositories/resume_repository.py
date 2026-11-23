
"""Repository for resume-related database operations."""

from uuid import UUID

from app.database import get_connection


class ResumeNotFoundError(Exception):
    """Resume does not exist or does not belong to the user."""


class UserNotFoundError(Exception):
    """User does not exist or is inactive."""


class ResumeRepository:

    @staticmethod
    def get_active_user_id(email):
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT id
                FROM users
                WHERE email = %s AND is_active = TRUE
                """,
                (email,),
            ).fetchone()

        if row is None:
            raise UserNotFoundError("User account not found or inactive.")

        return row[0]

    @staticmethod
    def create_resume(
        user_id,
        filename,
        storage_key,
        file_type,
        file_size_bytes,
    ):
        with get_connection() as conn:
            row = conn.execute(
                """
                INSERT INTO resumes (
                    user_id,
                    original_filename,
                    storage_key,
                    file_type,
                    file_size_bytes,
                    status,
                    processed_at
                )
                VALUES (%s, %s, %s, %s, %s, 'uploaded', NULL)
                RETURNING id
                """,
                (
                    UUID(str(user_id)),
                    filename,
                    storage_key,
                    file_type,
                    file_size_bytes,
                ),
            ).fetchone()

        return row[0]

    @staticmethod
    def get_resume_file(resume_id, user_id):
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT storage_key, file_type
                FROM resumes
                WHERE id = %s AND user_id = %s
                """,
                (UUID(str(resume_id)), UUID(str(user_id))),
            ).fetchone()

        if row is None:
            raise ResumeNotFoundError("Resume not found.")

        return {
            "storage_key": row[0],
            "file_type": row[1],
        }

    @staticmethod
    def update_status(
        resume_id,
        user_id,
        new_status,
        error_message=None,
    ):
        with get_connection() as conn:
            row = conn.execute(
                """
                UPDATE resumes
                SET status = %s,
                    error_message = %s
                WHERE id = %s AND user_id = %s
                RETURNING id
                """,
                (
                    new_status,
                    error_message,
                    UUID(str(resume_id)),
                    UUID(str(user_id)),
                ),
            ).fetchone()

        if row is None:
            raise ResumeNotFoundError("Resume not found.")

        return True

    @staticmethod
    def get_latest_resume_id(user_id):
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT id
                FROM resumes
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (UUID(str(user_id)),),
            ).fetchone()

        return row[0] if row else None

    @staticmethod
    def get_resume_storage_key(resume_id, user_id):
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT storage_key
                FROM resumes
                WHERE id = %s AND user_id = %s
                """,
                (UUID(str(resume_id)), UUID(str(user_id))),
            ).fetchone()

        if row is None:
            raise ResumeNotFoundError("Resume not found.")

        return row[0]

    @staticmethod
    def delete_resume_records(resume_id, user_id):
        """Delete resume-related rows and the resume record atomically."""
        resume_id = UUID(str(resume_id))
        user_id = UUID(str(user_id))

        with get_connection() as conn:
            with conn.transaction():
                row = conn.execute(
                    """
                    SELECT id
                    FROM resumes
                    WHERE id = %s AND user_id = %s
                    FOR UPDATE
                    """,
                    (resume_id, user_id),
                ).fetchone()

                if row is None:
                    raise ResumeNotFoundError("Resume not found.")

                conn.execute(
                    "DELETE FROM resume_sections WHERE resume_id = %s",
                    (resume_id,),
                )
                conn.execute(
                    "DELETE FROM resume_skills WHERE resume_id = %s",
                    (resume_id,),
                )
                conn.execute(
                    """
                    DELETE FROM resumes
                    WHERE id = %s AND user_id = %s
                    """,
                    (resume_id, user_id),
                )

        return True

    @staticmethod
    def get_telemetry_counts():
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT
                    COUNT(*) AS total_resumes,
                    COUNT(*) FILTER (
                        WHERE status = 'processed'
                    ) AS processed_resumes
                FROM resumes
                """
            ).fetchone()

        return {
            "total_resumes": row[0] or 0,
            "processed_resumes": row[1] or 0,
        }

    @staticmethod
    def get_active_user_count():
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*)
                FROM users
                WHERE is_active = TRUE
                """
            ).fetchone()

        return row[0] or 0

    @staticmethod
    def get_storage_bytes():
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT COALESCE(SUM(file_size_bytes), 0)
                FROM resumes
                """
            ).fetchone()

        return int(row[0] or 0)
