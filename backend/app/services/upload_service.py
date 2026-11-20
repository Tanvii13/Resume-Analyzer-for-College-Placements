"""
Resume upload validation service.

Integrates with the resume_parser service to validate uploaded files before storage.
"""

from io import BytesIO
from zipfile import BadZipFile

from docx import Document
from fastapi import HTTPException, UploadFile
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.services.resume_parser import (
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


def extract_resume_text(content: bytes, extension: str) -> str:
    """Extract readable text from PDF or DOCX resume files."""
    if not content:
        raise HTTPException(status_code=400, detail="Resume file is empty.")

    try:
        if extension == ".pdf":
            reader = PdfReader(BytesIO(content), strict=True)

            if reader.is_encrypted:
                raise HTTPException(
                    status_code=400,
                    detail="Password-protected PDFs are not supported.",
                )

            text_parts = []
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)

            extracted_text = "\n".join(text_parts)

        elif extension == ".docx":
            document = Document(BytesIO(content))
            text_parts = [
                paragraph.text
                for paragraph in document.paragraphs
                if paragraph.text.strip()
            ]

            for table in document.tables:
                for row in table.rows:
                    text_parts.extend(
                        cell.text for cell in row.cells if cell.text.strip()
                    )

            extracted_text = "\n".join(text_parts)

        else:
            raise HTTPException(
                status_code=415,
                detail="Unsupported resume format.",
            )

        if not extracted_text.strip():
            raise HTTPException(
                status_code=422,
                detail="No readable text found in the resume.",
            )

        return extracted_text.strip()

    except HTTPException:
        raise
    except (PdfReadError, BadZipFile, ValueError, KeyError, OSError) as exc:
        raise HTTPException(
            status_code=422,
            detail="Unable to extract text from the resume.",
        ) from exc
