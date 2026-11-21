
import json
from uuid import UUID

from app.database import get_connection


class ResumeNotFoundError(Exception):
    """Resume does not exist or does not belong to the user."""


class ExtractionNotFoundError(Exception):
    """No saved extraction exists for this resume."""


REQUIRED_FIELDS = ("skills", "education", "projects", "experience")


def _validate_extracted_data(extracted_data):
    """Validate extracted resume data before saving."""

    if not isinstance(extracted_data, dict):
        raise ValueError("Extracted data must be a dictionary.")

    for field in REQUIRED_FIELDS:
        if field not in extracted_data:
            raise ValueError(f"Missing field: {field}")

        if not isinstance(extracted_data[field], list):
            raise ValueError(f"{field} must be a list.")

    for skill in extracted_data["skills"]:
        if not isinstance(skill, str) or not skill.strip():
            raise ValueError("Every skill must be a non-empty string.")


def save_extraction(resume_id, user_id, extracted_data):
    """
    Save extracted resume information using the project database schema.
    Preserve manually added skills and replace previous extracted skills.
    """

    _validate_extracted_data(extracted_data)

    resume_id = UUID(str(resume_id))
    user_id = UUID(str(user_id))

    # Remove duplicate skills while preserving their original order.
    unique_skills = list(
        dict.fromkeys(
            skill.strip()
            for skill in extracted_data["skills"]
        )
    )

    with get_connection() as connection:
        with connection.transaction():

            # Verify that the resume belongs to the current user.
            resume = connection.execute(
                """
                SELECT id
                FROM resumes
                WHERE id = %s AND user_id = %s
                FOR UPDATE
                """,
                (resume_id, user_id),
            ).fetchone()

            if resume is None:
                raise ResumeNotFoundError(
                    "Resume not found or access denied."
                )

            # Save education, projects, and experience sections.
            for section_name in ("education", "projects", "experience"):
                section_content = json.dumps(
                    extracted_data[section_name],
                    ensure_ascii=False,
                )

                connection.execute(
                    """
                    INSERT INTO resume_sections (
                        resume_id,
                        section_name,
                        content
                    )
                    VALUES (%s, %s, %s)
                    ON CONFLICT (resume_id, section_name)
                    DO UPDATE SET
                        content = EXCLUDED.content
                    """,
                    (resume_id, section_name, section_content),
                )

            # Delete previous extracted skills.
            # Manually added skills remain untouched.
            connection.execute(
                """
                DELETE FROM resume_skills
                WHERE resume_id = %s
                  AND source = 'extracted'
                """,
                (resume_id,),
            )

            # Save unique skills and link them to the resume.
            for skill_name in unique_skills:

                connection.execute(
                    """
                    INSERT INTO skills (name)
                    VALUES (%s)
                    ON CONFLICT (name) DO NOTHING
                    """,
                    (skill_name,),
                )

                skill_row = connection.execute(
                    """
                    SELECT id
                    FROM skills
                    WHERE name = %s
                    """,
                    (skill_name,),
                ).fetchone()

                if skill_row is None:
                    raise RuntimeError(
                        f"Unable to find skill: {skill_name}"
                    )

                # Do not overwrite an existing manual skill link.
                connection.execute(
                    """
                    INSERT INTO resume_skills (
                        resume_id,
                        skill_id,
                        source,
                        confidence
                    )
                    VALUES (%s, %s, 'extracted', NULL)
                    ON CONFLICT (resume_id, skill_id)
                    DO NOTHING
                    """,
                    (resume_id, skill_row[0]),
                )

            # Mark the resume as successfully processed.
            connection.execute(
                """
                UPDATE resumes
                SET status = 'processed',
                    error_message = NULL,
                    processed_at = NOW()
                WHERE id = %s AND user_id = %s
                """,
                (resume_id, user_id),
            )

    return {
        "resume_id": str(resume_id),
        "message": "Extraction saved successfully",
    }


def get_extraction(resume_id, user_id):
    """Retrieve saved extraction data for the resume owner."""

    resume_id = UUID(str(resume_id))
    user_id = UUID(str(user_id))

    with get_connection() as connection:

        # Verify resume ownership.
        resume = connection.execute(
            """
            SELECT id
            FROM resumes
            WHERE id = %s AND user_id = %s
            """,
            (resume_id, user_id),
        ).fetchone()

        if resume is None:
            raise ResumeNotFoundError(
                "Resume not found or access denied."
            )

        # Retrieve extracted and manually added skills.
        skills = connection.execute(
            """
            SELECT s.name
            FROM resume_skills AS rs
            JOIN skills AS s
                ON s.id = rs.skill_id
            WHERE rs.resume_id = %s
            ORDER BY s.name
            """,
            (resume_id,),
        ).fetchall()

        # Retrieve saved resume sections.
        sections = connection.execute(
            """
            SELECT section_name, content
            FROM resume_sections
            WHERE resume_id = %s
            """,
            (resume_id,),
        ).fetchall()

    section_data = {
        section_name: json.loads(content)
        for section_name, content in sections
    }

    if not skills and not section_data:
        raise ExtractionNotFoundError(
            "Saved extraction not found."
        )

    return {
        "resume_id": str(resume_id),
        "skills": [row[0] for row in skills],
        "education": section_data.get("education", []),
        "projects": section_data.get("projects", []),
        "experience": section_data.get("experience", []),
    }
