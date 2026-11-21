import logging
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)

from app.database import get_connection
from app.routers.auth import UserResponse, get_current_user

from app.schemas.extraction import (
    ExtractionData,
    SkillExtractionResult,
)
from app.schemas.sprint3_schemas import (
    BulletAuditRequest,
    BulletAuditResponse,
    ResumeSuggestionsResponse,
    JDCompareRequest,
    JDCompareResponse,
    SectionSuggestion,
    JDMetadata,
    ImprovementAreasResponse,
    ImprovementAreaItem,
)

from app.schemas.privacy_schemas import (
    AnonymizedResumeResponse,
    DirectMaskRequest,
    DirectMaskResponse,
)

from app.services.upload_service import (
    validate_resume,
    extract_resume_text,
)

from app.services.skill_extractor import SkillExtractor
from app.services.resume_section_extractor import extract_resume_sections

from app.services.persistence_service import (
    save_extraction,
    get_extraction,
    ResumeNotFoundError,
    ExtractionNotFoundError,
)

from app.services.suggestion_service import SuggestionService
from app.services.jd_matcher import JDMatcherService
from app.services.jd_parser import JDParser
from app.services.improvement_detector import ImprovementDetector
from app.services.privacy_masking_service import PrivacyMaskingService


router = APIRouter(
    prefix="/resumes",
    tags=["Resume Upload"],
)

logger = logging.getLogger(__name__)

STORAGE_DIR = (
    Path(__file__).resolve().parents[2]
    / "storage"
    / "resumes"
)


suggestion_service = SuggestionService()
jd_matcher_service = JDMatcherService()
skill_extractor_service = SkillExtractor()
jd_parser_service = JDParser()
improvement_detector_service = ImprovementDetector()


# ==================================================
# HELPER: VERIFY RESUME OWNERSHIP AND GET DATA
# ==================================================

def get_owned_resume_data(
    resume_id: str,
    current_user: UserResponse,
):
    try:
        parsed_resume_id = UUID(resume_id)

    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid resume ID format.",
        )

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

        resume = conn.execute(
            """
            SELECT storage_key, file_type
            FROM resumes
            WHERE id = %s
            AND user_id = %s
            """,
            (parsed_resume_id, user_id),
        ).fetchone()

    if resume is None:
        raise HTTPException(
            status_code=404,
            detail="Resume not found.",
        )

    storage_key, file_type = resume

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

    # Safe extraction retrieval with fallback
    try:
        extracted_data = get_extraction(
            parsed_resume_id,
            user_id,
        )
    except (ResumeNotFoundError, ExtractionNotFoundError):
        extracted_data = None

    resume_text = extract_resume_text(
        stored_path.read_bytes(),
        f".{file_type.lower()}",
    )

    return extracted_data, resume_text


# ==================================================
# 1. UPLOAD RESUME API
# ==================================================

@router.post("/upload")
async def upload_resume(
    file: UploadFile = File(...),
    current_user: UserResponse = Depends(get_current_user),
):
    """
    Validate, store, and register an uploaded resume.
    Supports PDF and DOCX files.
    """

    validated_file = await validate_resume(file)

    storage_key = f"{uuid4().hex}{validated_file['extension']}"

    STORAGE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    stored_path = STORAGE_DIR / storage_key

    try:
        with stored_path.open("xb") as stored_file:
            stored_file.write(validated_file["content"])

        with get_connection() as conn:
            with conn.transaction():

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

                resume = conn.execute(
                    """
                    INSERT INTO resumes (
                        user_id,
                        original_filename,
                        storage_key,
                        file_type,
                        file_size_bytes,
                        status,
                        processed_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, NULL)
                    RETURNING id
                    """,
                    (
                        user[0],
                        validated_file["filename"],
                        storage_key,
                        validated_file["extension"].lstrip("."),
                        validated_file["size_bytes"],
                        "uploaded",
                    ),
                ).fetchone()

                resume_id = resume[0]

    except Exception as exc:

        try:
            stored_path.unlink(missing_ok=True)

        except OSError:
            logger.exception(
                "Could not remove uploaded resume file."
            )

        if isinstance(exc, HTTPException):
            raise

        logger.exception(
            "Error while uploading resume."
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to save the resume. Please try again.",
        ) from exc

    return {
        "message": "Resume uploaded successfully.",
        "status": "success",
        "resume_id": str(resume_id),
        "filename": validated_file["filename"],
        "file_type": validated_file["extension"],
        "size_bytes": validated_file["size_bytes"],
        "parsing": {
            "status": "pending",
            "message": "Resume is ready for skill extraction.",
        },
    }


# ==================================================
# 2. EXTRACT RESUME INFORMATION API
# ==================================================

@router.post(
    "/extract/{resume_id}",
    response_model=SkillExtractionResult,
)
async def extract_resume(
    resume_id: str,
    current_user: UserResponse = Depends(get_current_user),
):
    """
    Extract skills, education, projects, and experience
    from an uploaded resume and save them in PostgreSQL.
    """

    try:
        resume_id = UUID(resume_id)

    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid resume ID format.",
        )

    user_id = None

    try:
        with get_connection() as conn:
            with conn.transaction():

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

                resume = conn.execute(
                    """
                    SELECT storage_key, file_type
                    FROM resumes
                    WHERE id = %s
                    AND user_id = %s
                    """,
                    (resume_id, user_id),
                ).fetchone()

                if resume is None:
                    raise HTTPException(
                        status_code=404,
                        detail="Resume not found.",
                    )

                storage_key, file_type = resume

                conn.execute(
                    """
                    UPDATE resumes
                    SET status = 'processing',
                        error_message = NULL
                    WHERE id = %s
                    AND user_id = %s
                    """,
                    (resume_id, user_id),
                )

        if Path(storage_key).name != storage_key:
            raise ValueError(
                "Invalid resume storage path."
            )

        stored_path = STORAGE_DIR / storage_key

        if not stored_path.is_file():
            raise HTTPException(
                status_code=404,
                detail="Uploaded resume file not found.",
            )

        content = stored_path.read_bytes()

        resume_text = extract_resume_text(
            content,
            f".{file_type.lower()}",
        )

        extractor = SkillExtractor()

        skill_result = extractor.extract_skills(
            resume_text
        )

        all_skills = list(
            dict.fromkeys(
                skill_result["technical_skills"]
                + skill_result["soft_skills"]
            )
        )

        section_result = extract_resume_sections(
            resume_text
        )

        extracted_data = {
            "skills": all_skills,
            "education": section_result["education"],
            "projects": section_result["projects"],
            "experience": section_result["experience"],
        }

        save_extraction(
            resume_id,
            user_id,
            extracted_data,
        )

        return SkillExtractionResult(
            technical_skills=skill_result["technical_skills"],
            soft_skills=skill_result["soft_skills"],
            total_count=skill_result["total_count"],
        )

    except HTTPException as exc:

        if user_id is not None:
            try:
                with get_connection() as conn:
                    conn.execute(
                        """
                        UPDATE resumes
                        SET status = 'failed',
                            error_message = %s
                        WHERE id = %s
                        AND user_id = %s
                        """,
                        (
                            str(exc.detail)[:1000],
                            resume_id,
                            user_id,
                        ),
                    )

            except Exception:
                logger.exception(
                    "Could not update failed resume status."
                )

        raise

    except Exception as exc:

        logger.exception(
            "Resume extraction failed."
        )

        if user_id is not None:
            try:
                with get_connection() as conn:
                    conn.execute(
                        """
                        UPDATE resumes
                        SET status = 'failed',
                            error_message = %s
                        WHERE id = %s
                        AND user_id = %s
                        """,
                        (
                            "Resume extraction failed.",
                            resume_id,
                            user_id,
                        ),
                    )

            except Exception:
                logger.exception(
                    "Could not update failed resume status."
                )

        raise HTTPException(
            status_code=500,
            detail="Resume extraction failed. Please try again.",
        ) from exc


# ==================================================
# 3. GET SAVED EXTRACTION API
# ==================================================

@router.get(
    "/extraction/{resume_id}",
    response_model=ExtractionData,
)
async def retrieve_extraction(
    resume_id: str,
    current_user: UserResponse = Depends(get_current_user),
):
    """
    Retrieve previously saved extraction data
    for the authenticated user.
    """

    try:
        resume_id = UUID(resume_id)

    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid resume ID format.",
        )

    try:
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

        extracted_data = get_extraction(
            resume_id,
            user_id,
        )

        return extracted_data

    except ResumeNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Resume not found.",
        )

    except ExtractionNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Extraction data not found for this resume.",
        )

    except HTTPException:
        raise

    except Exception as exc:
        logger.exception(
            "Unable to retrieve extraction data."
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve extraction data.",
        ) from exc


# ==================================================
# 4. BULLET POINT AUDIT API - US-09
# ==================================================

@router.post(
    "/feedback/bullet-audit",
    response_model=BulletAuditResponse,
    status_code=status.HTTP_200_OK,
)
def audit_single_bullet(
    payload: BulletAuditRequest,
):
    """
    US-09: Evaluates a single resume bullet point
    against the STAR formula and returns suggestions.
    """

    try:
        result = suggestion_service.analyze_bullet_point(
            payload.bullet_text
        )

        return BulletAuditResponse(**result)

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )


# ==================================================
# 5. RESUME SUGGESTIONS API - US-09
# ==================================================

@router.get(
    "/{resume_id}/suggestions",
    response_model=ResumeSuggestionsResponse,
    status_code=status.HTTP_200_OK,
)
def get_resume_suggestions(
    resume_id: str,
    current_user: UserResponse = Depends(get_current_user),
):
    """
    US-09: Returns contextual improvement suggestions
    for a specific authenticated user's resume.
    """

    try:
        extracted_data, raw_text = get_owned_resume_data(
            resume_id,
            current_user,
        )

        dynamic_skills = skill_extractor_service.extract_skills(raw_text)

        raw_suggestions = (
            suggestion_service.generate_resume_suggestions(
                extracted_skills=dynamic_skills,
                raw_text=raw_text,
            )
        )

        priority_counts = {
            "High": 0,
            "Medium": 0,
            "Low": 0,
        }

        for suggestion in raw_suggestions:
            priority = suggestion.get(
                "priority",
                "Medium",
            )

            priority_counts[priority] = (
                priority_counts.get(priority, 0) + 1
            )

        formatted_suggestions = [
            SectionSuggestion(**suggestion)
            for suggestion in raw_suggestions
        ]

        return ResumeSuggestionsResponse(
            resume_id=UUID(resume_id),
            suggestions_count=len(formatted_suggestions),
            priority_breakdown=priority_counts,
            suggestions=formatted_suggestions,
        )

    except HTTPException:
        raise

    except Exception as exc:
        logger.exception(
            "Failed to generate resume suggestions."
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to generate resume suggestions.",
        ) from exc


# ==================================================
# 6. JOB DESCRIPTION COMPARISON API - US-11
# ==================================================

@router.post(
    "/{resume_id}/compare-jd",
    response_model=JDCompareResponse,
    status_code=status.HTTP_200_OK,
)
def compare_resume_with_job_description(
    resume_id: str,
    payload: JDCompareRequest,
    current_user: UserResponse = Depends(get_current_user),
):
    """
    US-11: Sanitizes and parses a job description,
    extracts its metadata, and compares its skills
    against the authenticated user's resume.
    """

    try:
        extracted_data, raw_text = get_owned_resume_data(
            resume_id,
            current_user,
        )

        resume_skills = []

        if extracted_data is not None:
            if isinstance(extracted_data, dict):
                resume_skills = extracted_data.get("skills", [])
            else:
                resume_skills = getattr(
                    extracted_data,
                    "skills",
                    [],
                )

        if not resume_skills and raw_text:
            extracted = skill_extractor_service.extract_skills(
                raw_text
            )

            resume_skills = (
                extracted.get("technical_skills", [])
                + extracted.get("soft_skills", [])
            )

        parsed_jd = jd_parser_service.parse_job_description(
            payload.jd_text
        )

        match_result = jd_matcher_service.match_resume_with_jd(
            resume_skills=resume_skills,
            jd_text=parsed_jd.clean_text,
        )

        target_role = (
            payload.target_role.strip()
            if payload.target_role and payload.target_role.strip()
            else parsed_jd.title
        )

        return JDCompareResponse(
            resume_id=UUID(resume_id),
            target_role=target_role,
            jd_metadata=JDMetadata(
                title=parsed_jd.title,
                experience_level=parsed_jd.experience_level,
                minimum_experience_years=parsed_jd.minimum_experience_years,
                required_degrees=parsed_jd.required_degrees,
                required_disciplines=parsed_jd.required_disciplines,
                word_count=parsed_jd.word_count,
                clean_text=parsed_jd.clean_text,
            ),
            **match_result,
        )

    except HTTPException:
        raise

    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except Exception as exc:
        logger.exception(
            "Job description comparison failed."
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to compare resume with job description.",
        ) from exc
# 9. IMPROVEMENT AREAS API - US-08
# ==================================================

@router.get(
    "/{resume_id}/improvement-areas",
    response_model=ImprovementAreasResponse,
    status_code=status.HTTP_200_OK,
)
def get_resume_improvement_areas(
    resume_id: str,
    current_user: UserResponse = Depends(get_current_user),
):
    """
    US-08: Detect weak and missing resume areas,
    explain their importance, and rank them by priority.
    """

    try:
        extracted_data, raw_text = get_owned_resume_data(
            resume_id,
            current_user,
        )

        structured_data = None

        if extracted_data is not None:
            if isinstance(extracted_data, dict):
                structured_data = extracted_data
            else:
                structured_data = (
                    extracted_data.model_dump()
                    if hasattr(extracted_data, "model_dump")
                    else None
                )

        report = improvement_detector_service.detect_improvements(
            raw_text=raw_text,
            structured_data=structured_data,
        )

        return ImprovementAreasResponse(
            resume_id=UUID(resume_id),
            total_issues_count=report.total_issues,
            priority_breakdown=report.priority_breakdown,
            improvement_areas=[
                ImprovementAreaItem(
                    id=issue.id,
                    section=issue.section,
                    priority=issue.priority,
                    issue=issue.issue,
                    reason=issue.reason,
                    remediation=issue.remediation,
                )
                for issue in report.improvement_areas
            ],
        )

    except HTTPException:
        raise

    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except Exception as exc:
        logger.exception("Failed to detect resume improvement areas.")

        raise HTTPException(
            status_code=500,
            detail="Unable to detect resume improvement areas.",
        ) from exc