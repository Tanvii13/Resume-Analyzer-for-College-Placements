"""
Persistent counselor review services for Sprint 4 (US-14).
"""

from uuid import UUID

from fastapi import HTTPException

from app.database import get_connection


ALLOWED_REVIEW_STATUSES = {
    "Pending Review",
    "Approved for Placement",
    "Revision Needed",
}


def create_counselor_review(
    student_id: str,
    resume_id: str,
    reviewer_email: str,
    review_status: str,
    notes: str | None = None,
) -> dict:
    """Save a counselor's review of a specific student's resume."""

    try:
        parsed_student_id = UUID(student_id)
        parsed_resume_id = UUID(resume_id)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=400,
            detail="Invalid student ID or resume ID format.",
        )

    if review_status not in ALLOWED_REVIEW_STATUSES:
        raise HTTPException(
            status_code=422,
            detail="Invalid review status.",
        )

    if notes is not None and len(notes) > 5000:
        raise HTTPException(
            status_code=422,
            detail="Review notes cannot exceed 5000 characters.",
        )

    with get_connection() as conn:
        reviewer = conn.execute(
            """
            SELECT u.id
            FROM users AS u
            JOIN user_roles AS ur ON ur.user_id = u.id
            JOIN roles AS r ON r.id = ur.role_id
            WHERE u.email = %s
              AND u.is_active = TRUE
              AND r.name = 'career_counselor'
            """,
            (reviewer_email,),
        ).fetchone()

        if reviewer is None:
            raise HTTPException(
                status_code=403,
                detail="Only career counselors can submit reviews.",
            )

        student = conn.execute(
            """
            SELECT id
            FROM users
            WHERE id = %s
              AND is_active = TRUE
              AND EXISTS (
                  SELECT 1
                  FROM user_roles AS ur
                  JOIN roles AS r ON r.id = ur.role_id
                  WHERE ur.user_id = users.id
                    AND r.name = 'student'
              )
            """,
            (parsed_student_id,),
        ).fetchone()

        if student is None:
            raise HTTPException(
                status_code=404,
                detail="Student not found.",
            )

        resume = conn.execute(
            """
            SELECT id
            FROM resumes
            WHERE id = %s
              AND user_id = %s
            """,
            (parsed_resume_id, parsed_student_id),
        ).fetchone()

        if resume is None:
            raise HTTPException(
                status_code=404,
                detail="Resume not found for this student.",
            )

        review = conn.execute(
            """
            INSERT INTO counselor_resume_reviews (
                reviewer_user_id,
                student_user_id,
                resume_id,
                status,
                notes
            )
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, reviewer_user_id, student_user_id,
                      resume_id, status, notes, reviewed_at
            """,
            (
                reviewer[0],
                parsed_student_id,
                parsed_resume_id,
                review_status,
                notes,
            ),
        ).fetchone()

    return {
        "id": str(review[0]),
        "reviewer_user_id": str(review[1]),
        "student_user_id": str(review[2]),
        "resume_id": str(review[3]),
        "status": review[4],
        "notes": review[5],
        "reviewed_at": review[6],
    }


def get_counselor_review_history(
    student_id: str,
    resume_id: str,
) -> list[dict]:
    """Retrieve the review history for a student's specific resume."""

    try:
        parsed_student_id = UUID(student_id)
        parsed_resume_id = UUID(resume_id)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=400,
            detail="Invalid student ID or resume ID format.",
        )

    with get_connection() as conn:
        reviews = conn.execute(
            """
            SELECT cr.id, u.full_name, cr.status, cr.notes,
                   cr.reviewed_at
            FROM counselor_resume_reviews AS cr
            JOIN users AS u ON u.id = cr.reviewer_user_id
            WHERE cr.student_user_id = %s
              AND cr.resume_id = %s
            ORDER BY cr.reviewed_at DESC
            """,
            (parsed_student_id, parsed_resume_id),
        ).fetchall()

    return [
        {
            "id": str(row[0]),
            "reviewer_name": row[1],
            "status": row[2],
            "notes": row[3],
            "reviewed_at": row[4],
        }
        for row in reviews
    ]
