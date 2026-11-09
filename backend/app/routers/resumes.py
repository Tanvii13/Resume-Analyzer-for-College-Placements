import logging
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.database import get_connection
from app.routers.auth import UserResponse, get_current_user
from app.services.upload_service import validate_resume

router = APIRouter(prefix="/resumes", tags=["Resume Upload"])

logger = logging.getLogger(__name__)

STORAGE_DIR = (
    Path(__file__).resolve().parents[2]
    / "storage"
    / "resumes"
)


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

    storage_key = (
        f"{uuid4().hex}{validated_file['extension']}"
    )

    STORAGE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    stored_path = STORAGE_DIR / storage_key

    try:
        # Store uploaded resume.
        with stored_path.open("xb") as stored_file:
            stored_file.write(validated_file["content"])

        # Save resume information in database.
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

        # Remove stored file if database operation fails.
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
            "message": "Resume parsing is handled by the NLP team.",
        },
    }
