from psycopg.types.json import Jsonb

from app.database import get_connection


class ResumeNotFoundError(Exception):
    pass


class ExtractionNotFoundError(Exception):
    pass


def save_extraction(resume_id, user_id, extracted_data):
    """
    Save or update extracted resume information.
    """

    if not isinstance(extracted_data, dict):
        raise ValueError("Extracted data must be a dictionary")

    skills = extracted_data.get("skills", [])
    education = extracted_data.get("education", [])
    projects = extracted_data.get("projects", [])
    experience = extracted_data.get("experience", [])

    with get_connection() as conn:
        with conn.cursor() as cur:

            # Verify resume ownership
            cur.execute(
                """
                SELECT id
                FROM resumes
                WHERE id = %s AND user_id = %s
                """,
                (resume_id, user_id),
            )

            if not cur.fetchone():
                raise ResumeNotFoundError("Resume not found")

            cur.execute(
                """
                INSERT INTO resume_extractions (
                    resume_id,
                    skills,
                    education,
                    projects,
                    experience,
                    created_at,
                    updated_at
                )
                VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
                ON CONFLICT (resume_id)
                DO UPDATE SET
                    skills = EXCLUDED.skills,
                    education = EXCLUDED.education,
                    projects = EXCLUDED.projects,
                    experience = EXCLUDED.experience,
                    updated_at = NOW()
                """,
                (
                    resume_id,
                    Jsonb(skills),
                    Jsonb(education),
                    Jsonb(projects),
                    Jsonb(experience),
                ),
            )

    return {
        "message": "Resume extraction saved successfully",
        "resume_id": str(resume_id),
    }


def get_extraction(resume_id, user_id):
    """
    Retrieve extracted resume information for an owned resume.
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    e.skills,
                    e.education,
                    e.projects,
                    e.experience
                FROM resume_extractions e
                JOIN resumes r
                    ON r.id = e.resume_id
                WHERE e.resume_id = %s
                  AND r.user_id = %s
                """,
                (resume_id, user_id),
            )

            row = cur.fetchone()

    if not row:
        raise ExtractionNotFoundError(
            "Resume extraction not found"
        )

    return {
        "skills": row[0] or [],
        "education": row[1] or [],
        "projects": row[2] or [],
        "experience": row[3] or [],
    }