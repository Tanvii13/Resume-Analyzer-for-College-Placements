import logging
from typing import List, Dict, Any

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)

from app.database import get_connection
from app.routers.auth import UserResponse, get_current_user
from app.services.opportunity_matcher import OpportunityMatcherService
from app.services.persistence_service import get_extraction
from app.schemas.opportunity_schemas import (
    OpportunityRecommendationsResponse,
    OpportunityMatchCard,
    SingleOpportunityMatchRequest,
)

router = APIRouter(
    prefix="/opportunities",
    tags=["Opportunities & Job Matching"],
)

logger = logging.getLogger(__name__)
matcher_service = OpportunityMatcherService()

# Standard Campus Placement Opportunities Pool (Fallback & Baseline Drives)
CAMPUS_OPPORTUNITIES_POOL: List[Dict[str, Any]] = [
    {
        "id": "opp-101",
        "title": "Graduate Backend Developer Intern",
        "company": "TCS Innovations",
        "location": "Ahmedabad / Gandhinagar",
        "opportunity_type": "Internship",
        "required_skills": ["Python", "FastAPI", "PostgreSQL", "SQL"],
        "preferred_skills": ["Docker", "Git", "Redis"],
        "min_cgpa": 7.0,
    },
    {
        "id": "opp-102",
        "title": "Junior Frontend Engineer",
        "company": "Infosys Labs",
        "location": "Pune / Remote",
        "opportunity_type": "Full-time",
        "required_skills": ["JavaScript", "TypeScript", "React", "HTML5", "CSS3"],
        "preferred_skills": ["Next.js", "Tailwind", "Git"],
        "min_cgpa": 6.5,
    },
    {
        "id": "opp-103",
        "title": "Cloud & DevOps Trainee",
        "company": "LTIMindtree",
        "location": "Bangalore / Hybrid",
        "opportunity_type": "Full-time",
        "required_skills": ["Linux", "Git", "Docker", "Python"],
        "preferred_skills": ["Kubernetes", "AWS", "CI/CD"],
        "min_cgpa": 7.0,
    },
    {
        "id": "opp-104",
        "title": "Data Science & ML Intern",
        "company": "Cognizant AI Hub",
        "location": "Mumbai / On-site",
        "opportunity_type": "Internship",
        "required_skills": ["Python", "SQL", "Pandas", "NumPy", "Scikit-learn"],
        "preferred_skills": ["Machine Learning", "Deep Learning", "NLP"],
        "min_cgpa": 7.5,
    },
]


def get_student_resume_skills(current_user: UserResponse) -> List[str]:
    """Helper to fetch the authenticated student's extracted skills."""
    with get_connection() as conn:
        user = conn.execute(
            """
            SELECT id
            FROM users
            WHERE email = %s
            AND is_active = TRUE
            """,
            (current_user.email,),
        ).fetchone()

        if user is None:
            raise HTTPException(
                status_code=401,
                detail="User account not found or inactive.",
            )

        user_id = user[0]

        # Fetch latest resume
        resume = conn.execute(
            """
            SELECT id
            FROM resumes
            WHERE user_id = %s
            ORDER BY id DESC
            LIMIT 1
            """,
            (user_id,),
        ).fetchone()

    if resume is None:
        # If no resume uploaded yet, return empty list
        return []

    resume_id = resume[0]

    try:
        extracted = get_extraction(resume_id, user_id)
        if isinstance(extracted, dict):
            return extracted.get("skills", [])
        return getattr(extracted, "skills", [])
    except Exception:
        return []


# ==================================================
# 1. GET RECOMMENDED OPPORTUNITIES (US-12 & US-13)
# ==================================================

@router.get(
    "/recommended",
    response_model=OpportunityRecommendationsResponse,
    status_code=status.HTTP_200_OK,
)
def get_recommended_opportunities(
    current_user: UserResponse = Depends(get_current_user),
):
    """
    US-12: Evaluates active campus placement opportunities against the student's
    resume skills, ranking them in descending order by relevance.
    """
    try:
        resume_skills = get_student_resume_skills(current_user)

        # In case user has no extracted skills yet, fallback to a starter list for demo
        if not resume_skills:
            resume_skills = ["Python", "FastAPI", "SQL", "Git"]

        ranked_result = matcher_service.rank_opportunities_for_student(
            resume_skills=resume_skills,
            opportunities_pool=CAMPUS_OPPORTUNITIES_POOL,
            min_threshold_pct=25.0,
        )

        return OpportunityRecommendationsResponse(**ranked_result)

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to calculate recommended opportunities.")
        raise HTTPException(
            status_code=500,
            detail="Unable to generate opportunity recommendations.",
        ) from exc


# ==================================================
# 2. EVALUATE SINGLE OPPORTUNITY MATCH (US-13)
# ==================================================

@router.post(
    "/evaluate-match",
    response_model=OpportunityMatchCard,
    status_code=status.HTTP_200_OK,
)
def evaluate_single_match(
    payload: SingleOpportunityMatchRequest,
    current_user: UserResponse = Depends(get_current_user),
):
    """
    US-13: Compares student resume skills against a specific opportunity's
    required and preferred skill sets, returning detailed gaps and affinity matches.
    """
    try:
        resume_skills = get_student_resume_skills(current_user)
        if not resume_skills:
            resume_skills = ["Python", "FastAPI", "PostgreSQL", "Git"]

        # Search in campus pool or use provided skills in payload
        matched_opp = next(
            (opp for opp in CAMPUS_OPPORTUNITIES_POOL if opp["id"] == payload.opportunity_id),
            None,
        )

        if matched_opp is None:
            matched_opp = {
                "id": payload.opportunity_id,
                "title": "Custom Opportunity",
                "company": "Recruiter Listing",
                "location": "Campus Drive",
                "opportunity_type": "Placement",
                "required_skills": payload.required_skills,
                "preferred_skills": payload.preferred_skills,
            }

        card = matcher_service.evaluate_single_opportunity(
            resume_skills=resume_skills,
            opportunity=matched_opp,
        )

        return OpportunityMatchCard(**card)

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to evaluate single opportunity match.")
        raise HTTPException(
            status_code=500,
            detail="Unable to evaluate opportunity match.",
        ) from exc
