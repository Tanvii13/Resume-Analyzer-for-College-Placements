"""
Sprint 7 - Member 1 Tests
Parsing subsystem, unified error boundaries and ingestion middleware.
"""

from io import BytesIO

import pytest
from docx import Document
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.exceptions import (
    CorruptFileError,
    EmptyFileError,
    FileSizeLimitExceededError,
    InvalidFileTypeError,
    ResumeAnalyzerError,
    UnreadableContentError,
    register_exception_handlers,
)
from app.core.middleware import (
    ExecutionTimingMiddleware,
    UploadSafeguardMiddleware,
)
from app.services.parsing_service import (
    MAX_UPLOAD_SIZE_BYTES,
    ParsedDocument,
    ParsingService,
)


# ---------------------------------------------------------
# TEST HELPERS
# ---------------------------------------------------------

def make_docx(text="John Doe\nEducation\nBachelor of Technology\nProjects\nResume Analyzer\nExperience\nSoftware Developer"):
    """Create a valid DOCX document in memory."""

    document = Document()

    for line in text.split("\n"):
        document.add_paragraph(line)

    output = BytesIO()
    document.save(output)
    return output.getvalue()


@pytest.fixture
def parsing_service():
    return ParsingService()


@pytest.fixture
def middleware_app():
    """Create a small isolated FastAPI app for middleware tests."""

    app = FastAPI()

    register_exception_handlers(app)
    app.add_middleware(UploadSafeguardMiddleware)
    app.add_middleware(ExecutionTimingMiddleware)

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.post("/upload-check")
    async def upload_check():
        return {"status": "received"}

    @app.get("/domain-error")
    async def domain_error():
        raise ResumeAnalyzerError(
            message="Test domain error",
            status_code=409,
            error_code="TEST_DOMAIN_ERROR",
        )

    @app.get("/unexpected-error")
    async def unexpected_error():
        raise RuntimeError("Internal test exception")

    return app


# ---------------------------------------------------------
# PARSING ENGINE TESTS
# ---------------------------------------------------------

def test_parse_valid_docx(parsing_service):
    content = make_docx()

    result = parsing_service.parse(
        raw_bytes=content,
        filename="resume.docx",
        content_type=(
            "application/vnd.openxmlformats-officedocument."
            "wordprocessingml.document"
        ),
    )

    assert isinstance(result, ParsedDocument)
    assert result.filename == "resume.docx"
    assert result.extension == ".docx"
    assert result.size_bytes == len(content)
    assert result.page_count >= 1
    assert result.word_count > 0
    assert "John Doe" in result.raw_text
    assert result.parse_duration_ms >= 0
    assert isinstance(result.sections, dict)


def test_parsed_document_to_dict(parsing_service):
    result = parsing_service.parse(
        raw_bytes=make_docx(),
        filename="resume.docx",
    )

    data = result.to_dict()

    assert isinstance(data, dict)
    assert data["filename"] == "resume.docx"
    assert "raw_text" in data
    assert "sections" in data
    assert "parse_duration_ms" in data


def test_empty_file_is_rejected(parsing_service):
    with pytest.raises(EmptyFileError):
        parsing_service.parse(
            raw_bytes=b"",
            filename="empty.docx",
        )


def test_unsupported_extension_is_rejected(parsing_service):
    with pytest.raises(InvalidFileTypeError):
        parsing_service.parse(
            raw_bytes=b"some content",
            filename="resume.txt",
        )


def test_mismatched_mime_type_is_rejected(parsing_service):
    with pytest.raises(InvalidFileTypeError):
        parsing_service.validate_file(
            raw_bytes=make_docx(),
            filename="resume.docx",
            content_type="application/pdf",
        )


def test_file_above_10mb_is_rejected(parsing_service):
    oversized_content = b"PK\x03\x04" + (
        b"A" * MAX_UPLOAD_SIZE_BYTES
    )

    with pytest.raises(FileSizeLimitExceededError):
        parsing_service.validate_file(
            raw_bytes=oversized_content,
            filename="resume.docx",
        )


def test_spoofed_pdf_signature_is_rejected(parsing_service):
    with pytest.raises(CorruptFileError):
        parsing_service.validate_file(
            raw_bytes=b"This is not a PDF file",
            filename="resume.pdf",
            content_type="application/pdf",
        )


def test_corrupted_docx_is_rejected(parsing_service):
    with pytest.raises(CorruptFileError):
        parsing_service.parse(
            raw_bytes=b"PK\x03\x04this-is-not-a-valid-docx",
            filename="corrupted.docx",
        )


def test_blank_docx_is_rejected(parsing_service):
    blank_document = Document()
    output = BytesIO()
    blank_document.save(output)

    with pytest.raises(UnreadableContentError):
        parsing_service.parse(
            raw_bytes=output.getvalue(),
            filename="blank.docx",
        )


# ---------------------------------------------------------
# GLOBAL EXCEPTION HANDLER TESTS
# ---------------------------------------------------------

def test_domain_exception_returns_standardized_response(middleware_app):
    client = TestClient(
        middleware_app,
        raise_server_exceptions=False,
    )

    response = client.get("/domain-error")

    assert response.status_code == 409
    assert response.json()["status"] == "error"
    assert response.json()["error_code"] == "TEST_DOMAIN_ERROR"
    assert response.json()["message"] == "Test domain error"
    assert "details" in response.json()


def test_unexpected_exception_returns_generic_500(middleware_app):
    client = TestClient(
        middleware_app,
        raise_server_exceptions=False,
    )

    response = client.get("/unexpected-error")

    assert response.status_code == 500
    assert response.json()["status"] == "error"
    assert response.json()["error_code"] == "INTERNAL_SERVER_ERROR"
    assert "unexpected internal error" in response.json()["message"].lower()


# ---------------------------------------------------------
# MIDDLEWARE TESTS
# ---------------------------------------------------------

def test_execution_timing_header_is_added(middleware_app):
    client = TestClient(middleware_app)

    response = client.get("/health")

    assert response.status_code == 200
    assert "X-Process-Time-Ms" in response.headers
    assert float(response.headers["X-Process-Time-Ms"]) >= 0


def test_upload_safeguard_rejects_oversized_request(middleware_app):
    client = TestClient(middleware_app)

    response = client.post(
        "/upload-check",
        content=b"x",
        headers={
            "Content-Length": str(MAX_UPLOAD_SIZE_BYTES + 1),
        },
    )

    assert response.status_code == 413
    assert response.json()["error_code"] == "FILE_SIZE_LIMIT_EXCEEDED"
    assert "X-Process-Time-Ms" in response.headers


def test_upload_safeguard_allows_small_request(middleware_app):
    client = TestClient(middleware_app)

    response = client.post(
        "/upload-check",
        content=b"small request",
    )

    assert response.status_code == 200
    assert response.json()["status"] == "received"


def test_invalid_content_length_is_rejected(middleware_app):
    client = TestClient(middleware_app)

    response = client.post(
        "/upload-check",
        content=b"x",
        headers={"Content-Length": "invalid"},
    )

    assert response.status_code == 400
    assert response.json()["error_code"] == "INVALID_CONTENT_LENGTH"
    assert "X-Process-Time-Ms" in response.headers
