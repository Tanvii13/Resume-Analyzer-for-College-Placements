import logging
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status

from app.routers.auth import UserResponse, get_current_user
from app.routers.resumes import get_owned_resume_data
from app.schemas.fairness_schemas import (
    ScoreFactorBreakdown,
    FairnessAuditRequest,
    FairnessAuditReport,
)
from app.services.fairness_audit_service import FairnessAuditService
from app.services.skill_extractor import SkillExtractor

router = APIRouter(
    prefix="/fairness",
    tags=["Algorithmic Fairness & Governance"],
)

logger = logging.getLogger(__name__)
skill_extractor_service = SkillExtractor()


@router.get(
    "/factors/{resume_id}",
    response_model=ScoreFactorBreakdown,
    status_code=status.HTTP_200_OK,
)
def get_scoring_factor_breakdown(
    resume_id: str,
    current_user: UserResponse = Depends(get_current_user),
):
    """
    US-19: Returns identifiable scoring factor breakdown for a resume,
    deconstructing the composite score into technical, experience, and project factors.
    """
    try:
        parsed_id = UUID(resume_id)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid resume ID format.",
        )

    try:
        extracted_data, raw_text = get_owned_resume_data(
            resume_id,
            current_user,
        )

        skills = []
        if extracted_data is not None:
            if isinstance(extracted_data, dict):
                skills = extracted_data.get("skills", [])
            else:
                skills = getattr(extracted_data, "skills", [])

        if not skills and raw_text:
            extracted_skills_dict = skill_extractor_service.extract_skills(raw_text)
            tech = extracted_skills_dict.get("technical_skills", [])
            soft = extracted_skills_dict.get("soft_skills", [])
            skills = list(dict.fromkeys(tech + soft))

        breakdown = FairnessAuditService.compute_factor_attribution(
            resume_id=str(parsed_id),
            skills=skills,
            raw_text=raw_text or " ".join(skills),
        )

        return breakdown

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to retrieve scoring factor breakdown.")
        raise HTTPException(
            status_code=500,
            detail="Unable to generate scoring factor breakdown.",
        ) from exc


@router.post(
    "/audit",
    response_model=FairnessAuditReport,
    status_code=status.HTTP_200_OK,
)
def audit_scoring_fairness(
    payload: FairnessAuditRequest,
    current_user: UserResponse = Depends(get_current_user),
):
    """
    US-19: Evaluates resume text for demographic neutrality and records
    potential fairness issues or scoring disparities.
    """
    try:
        report = FairnessAuditService.generate_fairness_audit(
            raw_text=payload.raw_text,
            skills=payload.extracted_skills,
        )
        return report

    except Exception as exc:
        logger.exception("Fairness audit execution failed.")
        raise HTTPException(
            status_code=500,
            detail="Unable to complete fairness audit.",
        ) from exc
