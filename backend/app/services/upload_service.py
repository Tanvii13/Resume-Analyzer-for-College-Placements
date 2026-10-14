"""
Resume upload validation service.

Integrates with the resume_parser service to validate uploaded files before storage.
"""

from fastapi import UploadFile

from app.services.resume_parser import (
    MAX_FILE_SIZE,
    SUPPORTED_EXTENSIONS,
    ResumeParsingError,
    validate_resume_metadata,
    validate_resume_structure,
)


async def validate_resume(file: UploadFile) -> dict:
    """Validate the filename, size, and readability of an uploaded resume."""
    content = await file.read()
    await file.seek(0)

    filename, extension = validate_resume_metadata(file.filename, content)
    validate_resume_structure(content, extension)

    return {
        "filename": filename,
        "extension": extension,
        "size_bytes": len(content),
        "content": content,
    }
