
from io import BytesIO
from pathlib import Path
from zipfile import BadZipFile

from docx import Document
from fastapi import HTTPException, UploadFile
from pypdf import PdfReader
from pypdf.errors import PdfReadError

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
SUPPORTED_EXTENSIONS = {".pdf", ".docx"}


async def validate_resume(file: UploadFile) -> dict:
    """Validate the filename, size, and readability of a resume."""

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="Please select a resume file.",
        )

    filename = Path(file.filename).name.strip()
    extension = Path(filename).suffix.lower()

    if extension not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail="Unsupported file format. Please upload a PDF or DOCX file.",
        )

    content = await file.read()
    await file.seek(0)

    if not content:
        raise HTTPException(
            status_code=400,
            detail="The uploaded file is empty. Please choose another file.",
        )

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="The resume exceeds the 5 MB upload limit.",
        )

    try:
        if extension == ".pdf":
            if not content.startswith(b"%PDF-"):
                raise HTTPException(
                    status_code=400,
                    detail="The file does not appear to be a valid PDF.",
                )

            reader = PdfReader(BytesIO(content), strict=True)

            if reader.is_encrypted:
                raise HTTPException(
                    status_code=400,
                    detail="Password-protected PDFs are not supported.",
                )

            # Force the reader to inspect the document's page structure.
            _ = len(reader.pages)

        elif extension == ".docx":
            if not content.startswith(b"PK"):
                raise HTTPException(
                    status_code=400,
                    detail="The file does not appear to be a valid DOCX document.",
                )

            Document(BytesIO(content))

    except HTTPException:
        raise
    except (PdfReadError, BadZipFile, ValueError, KeyError, OSError) as exc:
        raise HTTPException(
            status_code=400,
            detail="The document is corrupted or unreadable. Please upload another file.",
        ) from exc

    return {
        "filename": filename,
        "extension": extension,
        "size_bytes": len(content),
        "content": content,
    }

   
def extract_resume_text(content: bytes, extension: str) -> str:
    """
    Extract readable text from PDF or DOCX resume files.
    """

    if not content:
        raise HTTPException(
            status_code=400,
            detail="Resume file is empty."
        )

    try:
        if extension == ".pdf":
            reader = PdfReader(BytesIO(content), strict=True)

            if reader.is_encrypted:
                raise HTTPException(
                    status_code=400,
                    detail="Password-protected PDFs are not supported."
                )

            text_parts = []

            for page in reader.pages:
                page_text = page.extract_text()

                if page_text:
                    text_parts.append(page_text)

            extracted_text = "\n".join(text_parts)

        elif extension == ".docx":
            document = Document(BytesIO(content))

            text_parts = []

            # Extract text from paragraphs.
            for paragraph in document.paragraphs:
                if paragraph.text.strip():
                    text_parts.append(paragraph.text)

            # Extract text from tables.
            for table in document.tables:
                for row in table.rows:
                    for cell in row.cells:
                        if cell.text.strip():
                            text_parts.append(cell.text)

            extracted_text = "\n".join(text_parts)

        else:
            raise HTTPException(
                status_code=415,
                detail="Unsupported resume format."
            )

        if not extracted_text.strip():
            raise HTTPException(
                status_code=422,
                detail="No readable text found in the resume."
            )

        return extracted_text.strip()

    except HTTPException:
        raise

    except (PdfReadError, BadZipFile, ValueError, KeyError, OSError) as exc:
        raise HTTPException(
            status_code=422,
            detail="Unable to extract text from the resume."
        ) from exc

