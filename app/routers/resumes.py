import os
import logging
from pathlib import Path
from uuid import UUID, uuid4

import psycopg
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.database import get_connection
from app.routers.auth import UserResponse, get_current_user
from app.services.upload_service import validate_resume

router = APIRouter(prefix="/resumes", tags=["Resume Upload"])

logger = logging.getLogger(__name__)

STORAGE_DIR = Path(__file__).resolve().parents[2] / "storage" / "resumes"


@router.post("/upload")
async def upload_resume(
    file: UploadFile = File(...),
    current_user: UserResponse = Depends(get_current_user),
):
    """Validate, store, and register an uploaded resume for NLP processing."""

    validated_file = await validate_resume(file)

    # Generate a safe, unique storage filename.
    storage_key = f"{uuid4().hex}{validated_file['extension']}"
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    stored_path = STORAGE_DIR / storage_key

    try:
        # Store the original file without parsing its contents.
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
                        detail="User account not found or inactive",
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
        # Remove the stored file if the database operation fails.
        try:
            stored_path.unlink(missing_ok=True)
        except OSError:
            logger.exception(
                "Could not remove a resume file after upload failure"
            )

        if isinstance(exc, HTTPException):
            raise

        if isinstance(exc, psycopg.Error):
            logger.exception("Database error while saving uploaded resume")
        else:
            logger.exception("Unexpected error while saving uploaded resume")

        raise HTTPException(
            status_code=500,
            detail="Unable to save the resume. Please try again.",
        ) from exc

    return {
        "message": "Resume uploaded successfully. Ready for NLP processing.",
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

@router.delete("/{resume_id}/erase")
def erase_resume(
    resume_id: str,
    current_user: UserResponse = Depends(get_current_user),
):
    """Permanently erase a resume owned by the authenticated student."""

    try:
        parsed_resume_id = UUID(resume_id)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=400,
            detail="Invalid resume ID format.",
        )

    staged_path = None
    original_path = None
    database_committed = False

    try:
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
                    SELECT storage_key
                    FROM resumes
                    WHERE id = %s AND user_id = %s
                    FOR UPDATE
                    """,
                    (parsed_resume_id, user[0]),
                ).fetchone()

                if resume is None:
                    raise HTTPException(
                        status_code=404,
                        detail="Resume not found.",
                    )

                storage_key = resume[0]

                if not storage_key or Path(storage_key).name != storage_key:
                    raise HTTPException(
                        status_code=500,
                        detail="Invalid stored resume path.",
                    )

                storage_root = STORAGE_DIR.resolve()
                original_path = (STORAGE_DIR / storage_key).resolve()

                if original_path.parent != storage_root:
                    raise HTTPException(
                        status_code=500,
                        detail="Stored resume path is outside storage.",
                    )

                if original_path.exists():
                    if not original_path.is_file():
                        raise HTTPException(
                            status_code=500,
                            detail="Stored resume is not a regular file.",
                        )

                    quarantine_dir = STORAGE_DIR / ".deletion_pending"
                    quarantine_dir.mkdir(parents=True, exist_ok=True)

                    staged_path = quarantine_dir / (
                        f"{parsed_resume_id}_{uuid4().hex}.pending"
                    )

                    os.replace(original_path, staged_path)

                conn.execute(
                    "DELETE FROM resume_sections WHERE resume_id = %s",
                    (parsed_resume_id,),
                )

                conn.execute(
                    "DELETE FROM resume_skills WHERE resume_id = %s",
                    (parsed_resume_id,),
                )

                deleted = conn.execute(
                    """
                    DELETE FROM resumes
                    WHERE id = %s AND user_id = %s
                    RETURNING id
                    """,
                    (parsed_resume_id, user[0]),
                ).fetchone()

                if deleted is None:
                    raise HTTPException(
                        status_code=404,
                        detail="Resume not found.",
                    )

        database_committed = True

        if staged_path and staged_path.exists():
            try:
                staged_path.unlink()
            except OSError:
                logger.critical(
                    "Resume database record deleted, but physical file "
                    "cleanup is pending: %s",
                    staged_path,
                    exc_info=True,
                )

                return {
                    "status": "erased",
                    "resume_id": str(parsed_resume_id),
                    "file_cleanup_pending": True,
                    "message": "Database deletion completed. Administrator cleanup required.",
                }

        return {
            "status": "erased",
            "resume_id": str(parsed_resume_id),
            "file_cleanup_pending": False,
            "message": "Resume and extracted data erased successfully.",
        }

    except HTTPException:
        if (
            not database_committed
            and staged_path
            and staged_path.exists()
            and original_path
        ):
            try:
                original_path.parent.mkdir(parents=True, exist_ok=True)
                os.replace(staged_path, original_path)
            except OSError:
                logger.exception(
                    "Could not restore staged resume file."
                )
        raise

    except Exception as exc:
        logger.exception("Resume erasure failed.")

        if (
            not database_committed
            and staged_path
            and staged_path.exists()
            and original_path
        ):
            try:
                original_path.parent.mkdir(parents=True, exist_ok=True)
                os.replace(staged_path, original_path)
            except OSError:
                logger.exception(
                    "Could not restore staged resume file."
                )

        raise HTTPException(
            status_code=500,
            detail="Resume erasure could not be completed.",
        ) from exc
