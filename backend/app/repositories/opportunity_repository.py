
"""Repository for opportunity and student-resume database lookups."""

from uuid import UUID

from app.database import get_connection


class OpportunityRepository:

    @staticmethod
    def get_student_latest_resume(user_email):
        with get_connection() as conn:
            user = conn.execute(
                """
                SELECT id
                FROM users
                WHERE email = %s
                  AND is_active = TRUE
                """,
                (user_email,),
            ).fetchone()

            if user is None:
                return None

            resume = conn.execute(
                """
                SELECT id
                FROM resumes
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (user[0],),
            ).fetchone()

        if resume is None:
            return None

        return {
            "resume_id": UUID(str(resume[0])),
            "user_id": UUID(str(user[0])),
        }

    @staticmethod
    def get_student_resume_context(user_email):
        """Return the latest resume and its owner ID."""
        return OpportunityRepository.get_student_latest_resume(
            user_email
        )
