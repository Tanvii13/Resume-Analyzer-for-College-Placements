
from uuid import UUID

from psycopg.types.json import Jsonb

from app.database import get_connection


class ResumeNotFoundError(Exception):
    """Resume does not exist or does not belong to the user."""


class ExtractionNotFoundError(Exception):
    """No saved extraction exists for this resume."""


REQUIRED_FIELDS = ("skills", "education", "projects", "experience")


def _validate_extracted_data(extracted_data):
    """Check that extracted data contains the required lists."""
    if not isinstance(extracted_data, dict):
        raise ValueError("Extracted data must be a dictionary.")

    for field in REQUIRED_FIELDS:
        if field not in extracted_data:
            raise ValueError(f"Missing field: {field}")

        if not isinstance(extracted_data[field], list):
            raise ValueError(f"{field} must be a list.")


def save_extraction(resume_id, user_id, extracted_data):
    """
    Save or replace structured resume information.

    The resume must belong to the given user.
    Re-extraction updates the existing record.
    """
    _validate_extracted_data(extracted_data)

    resume_id = UUID(str(resume_id))
    user_id = UUID(str(user_id))

    query = """
        INSERT INTO resume_extractions (
            resume_id,
            skills,
            education,
            projects,
            experience
        )
        SELECT
            r.id,
            %s,
            %s,
            %s,
            %s
        FROM resumes AS r
        WHERE r.id = %s
          AND r.user_id = %s
        ON CONFLICT (resume_id)
        DO UPDATE SET
            skills = EXCLUDED.skills,
            education = EXCLUDED.education,
            projects = EXCLUDED.projects,
            experience = EXCLUDED.experience,
            updated_at = NOW()
        RETURNING resume_id;
    """

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                query,
                (
                    Jsonb(extracted_data["skills"]),
                    Jsonb(extracted_data["education"]),
                    Jsonb(extracted_data["projects"]),
                    Jsonb(extracted_data["experience"]),
                    resume_id,
                    user_id,
                ),
            )

            result = cursor.fetchone()

            if result is None:
                raise ResumeNotFoundError(
                    "Resume not found or access denied."
                )

    return {
        "resume_id": str(resume_id),
        "message": "Extraction saved successfully",
    }


def get_extraction(resume_id, user_id):
    """Retrieve saved extraction for a resume owned by the user."""
    resume_id = UUID(str(resume_id))
    user_id = UUID(str(user_id))

    query = """
        SELECT
            e.resume_id,
            e.skills,
            e.education,
            e.projects,
            e.experience
        FROM resume_extractions AS e
        JOIN resumes AS r
            ON r.id = e.resume_id
        WHERE e.resume_id = %s
          AND r.user_id = %s;
    """

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, (resume_id, user_id))
            result = cursor.fetchone()

    if result is None:
        raise ExtractionNotFoundError(
            "Saved extraction not found or access denied."
        )

    return {
        "resume_id": str(result[0]),
        "skills": result[1],
        "education": result[2],
        "projects": result[3],
        "experience": result[4],
    }
