"""
Placement officer and career counselor endpoints for US-14.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.routers.auth import UserResponse
from app.dependencies.roles import (
    require_staff_or_counselor,
    require_career_counselor,
)
from app.services.officer_service import inspect_student_resume
from app.services.officer_review_service import (
    create_counselor_review,
    get_counselor_review_history,
)


router = APIRouter(
    prefix="/officer",
    tags=["Placement Officer"],
)


class CounselorReviewRequest(BaseModel):
    status: str = Field(
        ...,
        description="Pending Review, Approved for Placement, or Revision Needed",
    )
    notes: str | None = Field(
        default=None,
        max_length=5000,
    )


@router.get("/students/{student_id}/resume-analysis")
def get_student_resume_analysis(
    student_id: str,
    current_user: UserResponse = Depends(require_staff_or_counselor),
):
    """Inspect a student's latest resume and placement-readiness analysis."""

    return inspect_student_resume(
        student_id=student_id,
        staff_email=current_user.email,
    )


@router.post("/students/{student_id}/resumes/{resume_id}/reviews")
def submit_counselor_review(
    student_id: str,
    resume_id: str,
    request: CounselorReviewRequest,
    current_user: UserResponse = Depends(require_career_counselor),
):
    """Submit a persistent counselor review for a student's resume."""

    return create_counselor_review(
        student_id=student_id,
        resume_id=resume_id,
        reviewer_email=current_user.email,
        review_status=request.status,
        notes=request.notes,
    )


@router.get("/students/{student_id}/resumes/{resume_id}/reviews")
def get_student_review_history(
    student_id: str,
    resume_id: str,
    current_user: UserResponse = Depends(require_staff_or_counselor),
):
    """Retrieve the counselor review history for a student's resume."""

    return {
        "student_id": student_id,
        "resume_id": resume_id,
        "reviews": get_counselor_review_history(
            student_id=student_id,
            resume_id=resume_id,
        ),
    }
