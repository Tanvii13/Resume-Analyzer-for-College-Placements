"""Resume scoring API. Mount in main.py and adapt auth dependency if needed."""
from fastapi import APIRouter, Depends, HTTPException
from app.routers.auth import get_current_user
from app.services.persistence_service import get_extraction, ExtractionNotFoundError
from app.services.scoring_service import score_resume
from app.services.matching_repository import save_improvement_log, ResourceNotFoundError

router = APIRouter(prefix="/resumes", tags=["Resume Analysis"])

def _user_id(user):
    if isinstance(user, dict):
        return user.get("id") or user.get("user_id")
    return getattr(user, "id", None) or getattr(user, "user_id", None)

@router.post("/{resume_id}/analyze")
def analyze_resume(resume_id: str, current_user=Depends(get_current_user)):
    uid = _user_id(current_user)
    try:
        extracted = get_extraction(resume_id, uid)
        result = score_resume(extracted)
        saved = save_improvement_log(resume_id, uid, result)
        return {**result, "saved_log": saved}
    except ExtractionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except (ValueError, ResourceNotFoundError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
