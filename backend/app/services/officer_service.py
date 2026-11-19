"""
Placement officer and career counselor services for US-14.
"""

from pathlib import Path
from uuid import UUID

from fastapi import HTTPException

from app.database import get_connection
from app.services.persistence_service import (
    get_extraction,
    ExtractionNotFoundError,
    ResumeNotFoundError,
)
from app.services.upload_service import extract_resume_text
from app.services.placement_analyzer import analyze_placement_readiness


STORAGE_DIR = Path(__file__).resolve().parents[2] / "storage" / "resumes"


def inspect_student_resume(student_id: str, staff_email: str) -> dict:
    """
    Retrieve and analyze the latest resume belonging to a student.

    Only call this function after staff-role authorization succeeds.
    """

    try:
        parsed_student_id = UUID(student_id)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=400,
            detail="Invalid student ID format.",
        )

    with get_connection() as conn:
        student = conn.execute(
            """
            SELECT u.id, u.full_name, u.email
            FROM users AS u
            JOIN user_roles AS ur ON ur.user_id = u.id
            JOIN roles AS r ON r.id = ur.role_id
            WHERE u.id = %s
              AND u.is_active = TRUE
              AND r.name = 'student'
            """,
            (parsed_student_id,),
        ).fetchone()

        if student is None:
            raise HTTPException(
                status_code=404,
                detail="Student not found.",
            )

        staff = conn.execute(
            """
            SELECT id
            FROM users
            WHERE email = %s AND is_active = TRUE
            """,
            (staff_email,),
        ).fetchone()

        if staff is None:
            raise HTTPException(
                status_code=401,
                detail="Staff account not found or inactive.",
            )

        resume = conn.execute(
            """
            SELECT id, original_filename, storage_key, file_type,
                   status, uploaded_at
            FROM resumes
            WHERE user_id = %s
            ORDER BY uploaded_at DESC
            LIMIT 1
            """,
            (parsed_student_id,),
        ).fetchone()

        if resume is None:
            raise HTTPException(
                status_code=404,
                detail="No resume has been uploaded by this student.",
            )

        staff_id = staff[0]

    (
        resume_id,
        original_filename,
        storage_key,
        file_type,
        resume_status,
        uploaded_at,
    ) = resume

    if Path(storage_key).name != storage_key:
        raise HTTPException(
            status_code=400,
            detail="Invalid resume storage path.",
        )

    stored_path = STORAGE_DIR / storage_key

    if not stored_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Uploaded resume file not found.",
        )

    try:
        extracted_data = get_extraction(resume_id, parsed_student_id)
    except (ResumeNotFoundError, ExtractionNotFoundError):
        extracted_data = None

    raw_text = extract_resume_text(
        stored_path.read_bytes(),
        f".{file_type.lower()}",
    )

    if not isinstance(extracted_data, dict):
        extracted_data = {}

    # The current extractor stores skills together.
    # Do not incorrectly classify all skills as technical or soft skills.
    resume_data = {
        "academic_profile": extracted_data.get("education", []),
        "projects": extracted_data.get("projects", []),
        "experience": extracted_data.get("experience", []),
        "achievements": extracted_data.get("achievements", []),
    }

    analysis = analyze_placement_readiness(
        resume_data=resume_data,
        raw_text=raw_text,
    )

    # Preserve the combined extracted skills for staff inspection.
    unclassified_skills = extracted_data.get("skills", [])

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO staff_resume_access_log (
                staff_user_id,
                student_user_id,
                resume_id,
                access_type
            )
            VALUES (%s, %s, %s, %s)
            """,
            (
                staff_id,
                parsed_student_id,
                resume_id,
                "view_analysis",
            ),
        )

    return {
        "student": {
            "id": str(student[0]),
            "full_name": student[1],
            "email": student[2],
        },
        "resume": {
            "id": str(resume_id),
            "original_filename": original_filename,
            "file_type": file_type,
            "status": resume_status,
            "uploaded_at": uploaded_at,
        },
        "extracted_skills": unclassified_skills,
        "analysis": analysis,
        "notice": (
            "This is a criterion-wise placement-readiness assessment. "
            "No overall score is calculated. Combined skills are shown "
            "without assuming whether they are technical or non-technical."
        ),
    }
