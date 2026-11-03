import logging
from pathlib import Path
from uuid import UUID, uuid4

import psycopg
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.database import get_connection
from app.routers.auth import UserResponse, get_current_user
from app.schemas.extraction import SkillExtractionResult
from app.services.upload_service import (
    validate_resume,
    extract_resume_text,
)
from app.services.skill_extractor import SkillExtractor
from app.services.persistence_service import save_extraction


router = APIRouter(prefix="/resumes", tags=["Resume Upload"])

logger = logging.getLogger(__name__)

STORAGE_DIR = Path(__file__).resolve().parents[2] / "storage" / "resumes"


# --------------------------------------------------
# 1. UPLOAD RESUME API
# --------------------------------------------------

@router.post("/upload")
async def upload_resume(
    file: UploadFile = File(...),
    current_user: UserResponse = Depends(get_current_user),
):
    """Validate, store, and register an uploaded resume."""

    validated_file = await validate_resume(file)

    storage_key = f"{uuid4().hex}{validated_file['extension']}"

    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
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
                    WHERE email = %s AND is_active = TRUE
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
            logger.exception("Could not remove uploaded resume file.")

        if isinstance(exc, HTTPException):
            raise

        logger.exception("Error while uploading resume.")

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
    }


# --------------------------------------------------
# 2. EXTRACT RESUME SKILLS API
# --------------------------------------------------

@router.post(
    "/extract/{resume_id}",
    response_model=SkillExtractionResult,
)
async def extract_resume(
    resume_id: str,
    current_user: UserResponse = Depends(get_current_user),
):
    """Extract technical and soft skills from an uploaded resume."""

    try:
        resume_id = UUID(resume_id)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid resume ID format.",
        )

    user_id = None

    try:

        # Verify user and resume ownership.
        with get_connection() as conn:
            with conn.transaction():

                user = conn.execute(
                    """
                    SELECT id
                    FROM users
                    WHERE email = %s AND is_active = TRUE
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
                    WHERE id = %s AND user_id = %s
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
                    WHERE id = %s AND user_id = %s
                    """,
                    (resume_id, user_id),
                )

        # Validate storage path.
        if Path(storage_key).name != storage_key:
            raise ValueError("Invalid resume storage path.")

        stored_path = STORAGE_DIR / storage_key

        if not stored_path.is_file():
            raise HTTPException(
                status_code=404,
                detail="Uploaded resume file not found.",
            )

        # Read uploaded resume.
        content = stored_path.read_bytes()

        # Extract text from PDF or DOCX.
        resume_text = extract_resume_text(
            content,
            f".{file_type.lower()}",
        )

        # Extract skills using taxonomy.
        extractor = SkillExtractor()

        skill_result = extractor.extract_skills(resume_text)

        all_skills = list(
            dict.fromkeys(
                skill_result["technical_skills"]
                + skill_result["soft_skills"]
            )
        )

        # Save extracted information.
        extracted_data = {
            "skills": all_skills,
            "education": [],
            "projects": [],
            "experience": [],
        }

        save_extraction(
            resume_id,
            user_id,
            extracted_data,
        )

        # Return validated API response.
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
                        WHERE id = %s AND user_id = %s
                        """,
                        (
                            str(exc.detail)[:1000],
                            resume_id,
                            user_id,
                        ),
                    )
            except Exception:
                logger.exception("Could not update failed resume status.")

        raise

    except Exception as exc:

        logger.exception("Resume extraction failed.")

        if user_id is not None:
            try:
                with get_connection() as conn:
                    conn.execute(
                        """
                        UPDATE resumes
                        SET status = 'failed',
                            error_message = %s
                        WHERE id = %s AND user_id = %s
                        """,
                        (
                            "Resume extraction failed.",
                            resume_id,
                            user_id,
                        ),
                    )
            except Exception:
                logger.exception("Could not update failed resume status.")

        raise HTTPException(
            status_code=500,
            detail="Resume extraction failed. Please try again.",
        ) from exc
