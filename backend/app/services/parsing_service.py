"""
Decoupled Resume Parsing Subsystem (US-20 AC-1).

Accepts raw file bytes and produces a structured ParsedDocument
without depending on HTTP routers, databases, or scoring engines.
"""

from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path
import time
from typing import Any, Dict, Optional, Set
from zipfile import BadZipFile

from docx import Document
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.core.exceptions import (
    CorruptFileError,
    EmptyFileError,
    EncryptedFileError,
    FileSizeLimitExceededError,
    InvalidFileTypeError,
    UnreadableContentError,
)
from app.services.resume_section_extractor import extract_resume_sections


# ---------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------

MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB

SUPPORTED_EXTENSIONS: Set[str] = {".pdf", ".docx"}

ALLOWED_MIME_TYPES: Dict[str, Set[str]] = {
    ".pdf": {
        "application/pdf",
        "application/x-pdf",
    },
    ".docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/octet-stream",
    },
}

PDF_MAGIC_BYTES = b"%PDF-"
ZIP_MAGIC_BYTES = b"PK\x03\x04"


# ---------------------------------------------------------
# STRUCTURED PARSING OUTPUT
# ---------------------------------------------------------

@dataclass
class ParsedDocument:
    """Standardized structured output produced by the parsing engine."""

    filename: str
    extension: str
    mime_type: Optional[str]
    size_bytes: int
    page_count: int
    raw_text: str
    word_count: int
    sections: Dict[str, Any] = field(default_factory=dict)
    parse_duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert the parsed document into a serializable dictionary."""

        return {
            "filename": self.filename,
            "extension": self.extension,
            "mime_type": self.mime_type,
            "size_bytes": self.size_bytes,
            "page_count": self.page_count,
            "raw_text": self.raw_text,
            "word_count": self.word_count,
            "sections": self.sections,
            "parse_duration_ms": self.parse_duration_ms,
        }


# ---------------------------------------------------------
# DECOUPLED PARSING SERVICE
# ---------------------------------------------------------

class ParsingService:
    """
    Standalone document parsing engine.

    Pipeline:
        Validate -> Extract Text -> Segment Sections -> Return ParsedDocument
    """

    def __init__(
        self,
        max_size_bytes: int = MAX_UPLOAD_SIZE_BYTES,
    ):
        if max_size_bytes <= 0:
            raise ValueError("Maximum upload size must be positive.")

        self.max_size_bytes = max_size_bytes

    # -----------------------------------------------------
    # FILE VALIDATION
    # -----------------------------------------------------

    def validate_file(
        self,
        raw_bytes: bytes,
        filename: str,
        content_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Validate filename, extension, size, MIME type and magic bytes."""

        if not isinstance(raw_bytes, bytes):
            raise TypeError("File content must be supplied as bytes.")

        if not filename or not filename.strip():
            raise InvalidFileTypeError(
                message="A valid filename is required.",
            )

        clean_name = Path(filename).name.strip()
        extension = Path(clean_name).suffix.lower()

        if extension not in SUPPORTED_EXTENSIONS:
            raise InvalidFileTypeError(
                message=(
                    f"Unsupported file format '{extension or 'none'}'. "
                    "Only PDF and DOCX resumes are accepted."
                ),
                details={
                    "extension": extension,
                    "supported": sorted(SUPPORTED_EXTENSIONS),
                },
            )

        if not raw_bytes:
            raise EmptyFileError(
                message="The uploaded file is empty (0 bytes).",
                details={"filename": clean_name},
            )

        size_bytes = len(raw_bytes)

        if size_bytes > self.max_size_bytes:
            raise FileSizeLimitExceededError(
                message=(
                    f"File size ({size_bytes} bytes) exceeds the maximum "
                    f"allowed limit of {self.max_size_bytes // (1024 * 1024)} MB."
                ),
                details={
                    "size_bytes": size_bytes,
                    "max_size_bytes": self.max_size_bytes,
                },
            )

        # Validate MIME type when the caller provides one.
        if content_type:
            normalized_mime = (
                content_type.split(";")[0].strip().lower()
            )

            allowed_for_extension = ALLOWED_MIME_TYPES[extension]

            if normalized_mime not in allowed_for_extension:
                raise InvalidFileTypeError(
                    message=(
                        f"MIME type '{normalized_mime}' does not match "
                        f"the expected type for '{extension}' files."
                    ),
                    details={
                        "mime_type": normalized_mime,
                        "expected_mime_types": sorted(
                            allowed_for_extension
                        ),
                    },
                )

        # Verify file signatures to detect renamed or spoofed files.
        if (
            extension == ".pdf"
            and not raw_bytes.startswith(PDF_MAGIC_BYTES)
        ):
            raise CorruptFileError(
                message="File header does not match a valid PDF signature.",
                details={"filename": clean_name},
            )

        if (
            extension == ".docx"
            and not raw_bytes.startswith(ZIP_MAGIC_BYTES)
        ):
            raise CorruptFileError(
                message="File header does not match a valid DOCX archive signature.",
                details={"filename": clean_name},
            )

        return {
            "filename": clean_name,
            "extension": extension,
            "size_bytes": size_bytes,
        }

    # -----------------------------------------------------
    # PDF TEXT EXTRACTION
    # -----------------------------------------------------

    def _extract_pdf(self, raw_bytes: bytes) -> tuple[str, int]:
        """Extract readable text and page count from PDF bytes."""

        try:
            reader = PdfReader(BytesIO(raw_bytes), strict=True)

            if reader.is_encrypted:
                raise EncryptedFileError(
                    message=(
                        "Password-protected PDFs cannot be processed. "
                        "Please upload an unlocked PDF."
                    ),
                )

            pages_text = []

            for page in reader.pages:
                pages_text.append(page.extract_text() or "")

            full_text = "\n".join(pages_text).strip()
            page_count = len(reader.pages)

        except EncryptedFileError:
            raise

        except (PdfReadError, ValueError, KeyError, OSError) as exc:
            raise CorruptFileError(
                message="Unable to read PDF file. The file appears corrupted.",
            ) from exc

        if not full_text:
            raise UnreadableContentError(
                message=(
                    "No readable text could be extracted from this PDF. "
                    "It may be a scanned image."
                ),
            )

        return full_text, page_count

    # -----------------------------------------------------
    # DOCX TEXT EXTRACTION
    # -----------------------------------------------------

    def _extract_docx(self, raw_bytes: bytes) -> tuple[str, int]:
        """Extract text from DOCX paragraphs and tables."""

        try:
            document = Document(BytesIO(raw_bytes))

            text_parts = []

            # Extract paragraph text.
            for paragraph in document.paragraphs:
                if paragraph.text.strip():
                    text_parts.append(paragraph.text.strip())

            # Extract table text as well.
            for table in document.tables:
                for row in table.rows:
                    for cell in row.cells:
                        if cell.text.strip():
                            text_parts.append(cell.text.strip())

            full_text = "\n".join(text_parts).strip()

        except (BadZipFile, ValueError, KeyError, OSError) as exc:
            raise CorruptFileError(
                message="Unable to read DOCX file. The file appears corrupted.",
            ) from exc

        if not full_text:
            raise UnreadableContentError(
                message="No readable text could be extracted from this DOCX file.",
            )

        # DOCX does not reliably expose physical page count.
        # Estimate using approximately 450 words per page.
        word_count = len(full_text.split())
        approximate_pages = max(1, (word_count + 449) // 450)

        return full_text, approximate_pages

    # -----------------------------------------------------
    # COMPLETE PARSING PIPELINE
    # -----------------------------------------------------

    def parse(
        self,
        raw_bytes: bytes,
        filename: str,
        content_type: Optional[str] = None,
    ) -> ParsedDocument:
        """
        Execute the complete parsing pipeline.

        1. Validate file.
        2. Extract PDF or DOCX text.
        3. Identify resume sections.
        4. Calculate word count and parsing duration.
        5. Return a structured ParsedDocument.
        """

        start_time = time.perf_counter()

        metadata = self.validate_file(
            raw_bytes=raw_bytes,
            filename=filename,
            content_type=content_type,
        )

        extension = metadata["extension"]

        if extension == ".pdf":
            raw_text, page_count = self._extract_pdf(raw_bytes)
        else:
            raw_text, page_count = self._extract_docx(raw_bytes)

        sections = extract_resume_sections(raw_text)
        word_count = len(raw_text.split())

        elapsed_ms = round(
            (time.perf_counter() - start_time) * 1000.0,
            2,
        )

        return ParsedDocument(
            filename=metadata["filename"],
            extension=extension,
            mime_type=content_type,
            size_bytes=metadata["size_bytes"],
            page_count=page_count,
            raw_text=raw_text,
            word_count=word_count,
            sections=sections,
            parse_duration_ms=elapsed_ms,
        )


# Shared service instance for convenient imports.
parsing_service = ParsingService()
