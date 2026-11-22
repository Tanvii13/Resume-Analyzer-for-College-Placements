"""Job-description and resume matching API routes.

Mount this router in main.py and adapt get_current_user to your auth implementation.
The dependency is intentionally imported from the existing auth router.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from app.routers.auth import get_current_user
from app.services import matching_repository as repo
from app.services.jd_matching_service import calculate_jd_match
from app.services.scoring_service import score_resume
from app.services.persistence_service import get_extraction, ExtractionNotFoundError

router = APIRouter(prefix="/jobs", tags=["Jobs"])

class JobCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    company: str | None = None
    description: str = Field(min_length=1)
    required_skills: list[str] = Field(default_factory=list)
    optional_skills: list[str] = Field(default_factory=list)

def _user_id(user):
    if isinstance(user, dict):
        return user.get("id") or user.get("user_id")
    return getattr(user, "id", None) or getattr(user, "user_id", None)

@router.post("")
def create_job(payload: JobCreate, current_user=Depends(get_current_user)):
    try:
        return repo.save_job_description(_user_id(current_user), payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@router.get("")
def list_jobs(current_user=Depends(get_current_user)):
    return repo.get_all_job_descriptions(_user_id(current_user))

@router.get("/{job_id}")
def read_job(job_id: str, current_user=Depends(get_current_user)):
    try:
        return repo.get_job_description(job_id, _user_id(current_user))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except repo.ResourceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

@router.post("/{job_id}/resumes/{resume_id}/match")
def match_resume(job_id: str, resume_id: str, current_user=Depends(get_current_user)):
    uid = _user_id(current_user)
    try:
        job = repo.get_job_description(job_id, uid)
        extraction = get_extraction(resume_id, uid)
        result = calculate_jd_match(extraction, job)
        saved = repo.save_match_result(resume_id, job_id, uid, result)
        return {**result, **{"saved_match": saved}}
    except (ValueError, repo.ResourceNotFoundError) as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ExtractionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

@router.get("/resumes/{resume_id}/matches")
def list_resume_matches(resume_id: str, current_user=Depends(get_current_user)):
    try:
        return repo.get_match_results(resume_id, _user_id(current_user))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
