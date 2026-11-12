from fastapi import APIRouter

from app.services.suggestion_service import SuggestionService
from app.services.jd_matcher import JDMatcherService

from app.schemas.sprint3_schemas import (
    BulletAnalysisRequest,
    BulletAnalysisResponse,
    ResumeSuggestionRequest,
    ResumeSuggestionsResponse,
    JDMatchRequest,
    JDMatchResponse,
)


router = APIRouter(
    prefix="/resume-insights",
    tags=["Resume Insights"]
)

suggestion_service = SuggestionService()
jd_matcher_service = JDMatcherService()


@router.post(
    "/analyze-bullet",
    response_model=BulletAnalysisResponse
)
def analyze_bullet(request: BulletAnalysisRequest):
    """Analyze a resume bullet point using STAR principles."""

    result = suggestion_service.analyze_bullet_point(
        request.bullet
    )

    return result


@router.post(
    "/suggestions",
    response_model=ResumeSuggestionsResponse
)
def generate_suggestions(request: ResumeSuggestionRequest):
    """Generate contextual resume improvement suggestions."""

    weak_areas = (
        [
            area.model_dump()
            for area in request.weak_areas
        ]
        if request.weak_areas
        else None
    )

    suggestions = suggestion_service.generate_resume_suggestions(
        extracted_skills=request.extracted_skills,
        raw_text=request.raw_text,
        weak_areas=weak_areas
    )

    return {
        "suggestions": suggestions
    }


@router.post(
    "/match-job-description",
    response_model=JDMatchResponse
)
def match_job_description(request: JDMatchRequest):
    """Compare resume skills with job description requirements."""

    result = jd_matcher_service.match_resume_with_jd(
        resume_skills=request.resume_skills,
        jd_text=request.jd_text
    )

    return result

   
