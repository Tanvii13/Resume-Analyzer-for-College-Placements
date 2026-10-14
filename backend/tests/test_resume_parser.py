"""
Automated test suite for Resume Parsing, Validation, and Error Handling (Sprint 1).

Covers:
- PDF and DOCX text extraction
- DOCX paragraphs and tables reading order
- DOCX content controls (w:sdt) and section headers
- Unicode and special character handling
- Whitespace normalization
- Multi-page PDF handling and page count metadata
- Empty, unsupported, missing, and oversized files
- Corrupted PDF and DOCX documents
- DOCX files that are arbitrary ZIP archives (missing document.xml)
- Extension/content mismatches
- Documents with no readable text (scanned/empty)
- Password-protected / encrypted PDFs and DOCX files
- Proper error code mappings and structured error responses
- Reusable parser interface independent of FastAPI
- Integration with upload service and backend routes
- Thread safety and absence of request state leakage
"""

import io
import os
import sys
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

# Ensure backend root is on sys.path and test environment is configured
backend_dir = str(Path(__file__).resolve().parents[1])
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

os.environ.setdefault(
    "AUTH_SECRET_KEY",
    "test-secret-key-for-testing-at-least-32-chars-long!",
)

import pytest
from docx import Document
from docx.oxml import parse_xml
from fastapi.testclient import TestClient
from pypdf import PdfWriter

from main import app
from app.services.resume_parser import (
    MAX_FILE_SIZE,
    SUPPORTED_EXTENSIONS,
    CorruptedFileError,
    EmptyFileError,
    EncryptedFileError,
    ExtractionFailureError,
    FileTooLargeError,
    InvalidFileError,
    NoReadableTextError,
    ResumeExtractionError,
    ResumeParseResult,
    ResumeParsingError,
    ResumeParsingErrorCode,
    ResumeValidationError,
    UnsupportedFormatError,
    extract_text_from_docx,
    extract_text_from_pdf,
    has_readable_text,
    normalize_whitespace,
    parse_resume,
    validate_resume_metadata,
    validate_resume_structure,
)

client = TestClient(app)


# ============================================================================
# Test Fixture Generators
# ============================================================================

def make_pdf_with_text(pages: list[str]) -> bytes:
    """Generate a valid PDF byte string containing the given pages of text."""
    num_pages = len(pages)
    font_obj_id = 3 + 2 * num_pages
    objects: dict[int, bytes] = {}

    # Catalog
    objects[1] = b"<< /Type /Catalog /Pages 2 0 R >>"

    # Pages
    kids = " ".join(f"{3 + 2 * i} 0 R" for i in range(num_pages))
    objects[2] = f"<< /Type /Pages /Kids [{kids}] /Count {num_pages} >>".encode("latin-1")

    # Page & Contents stream objects
    for i, page_text in enumerate(pages):
        page_obj_id = 3 + 2 * i
        contents_obj_id = 4 + 2 * i

        objects[page_obj_id] = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 {font_obj_id} 0 R >> >> "
            f"/Contents {contents_obj_id} 0 R >>"
        ).encode("latin-1")

        lines = page_text.splitlines() if page_text else [""]
        stream_cmds = ["BT", "/F1 12 Tf", "50 720 Td"]
        first = True
        for line in lines:
            escaped = (
                line.replace("\\", "\\\\")
                .replace("(", "\\(")
                .replace(")", "\\)")
            )
            if first:
                stream_cmds.append(f"({escaped}) Tj")
                first = False
            else:
                stream_cmds.append("0 -14 Td")
                stream_cmds.append(f"({escaped}) Tj")
        stream_cmds.append("ET")
        stream_bytes = "\n".join(stream_cmds).encode("latin-1", errors="replace")

        objects[contents_obj_id] = (
            f"<< /Length {len(stream_bytes)} >>\nstream\n".encode("latin-1")
            + stream_bytes
            + b"\nendstream"
        )

    # Standard Helvetica Font
    objects[font_obj_id] = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"

    total_objects = font_obj_id
    header = b"%PDF-1.4\n"
    body_parts = [header]
    offsets: dict[int, int] = {}

    current_offset = len(header)
    for obj_id in range(1, total_objects + 1):
        offsets[obj_id] = current_offset
        obj_content = objects[obj_id]
        part = f"{obj_id} 0 obj\n".encode("latin-1") + obj_content + b"\nendobj\n"
        body_parts.append(part)
        current_offset += len(part)

    xref_start = current_offset
    xref_lines = [f"xref\n0 {total_objects + 1}\n", "0000000000 65535 f \n"]
    for obj_id in range(1, total_objects + 1):
        xref_lines.append(f"{offsets[obj_id]:010d} 00000 n \n")

    body_parts.append("".join(xref_lines).encode("latin-1"))
    trailer = (
        f"trailer\n<< /Size {total_objects + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_start}\n%%EOF\n"
    ).encode("latin-1")
    body_parts.append(trailer)

    return b"".join(body_parts)


def make_encrypted_pdf() -> bytes:
    """Create a password-encrypted PDF in-memory using pypdf."""
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=300)
    writer.encrypt("user_secret_password", "owner_secret_password")
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def make_docx_document(
    paragraphs: list[str] | None = None,
    tables: list[list[list[str]]] | None = None,
) -> bytes:
    """Create a valid DOCX document in-memory using python-docx."""
    doc = Document()
    if paragraphs:
        for p in paragraphs:
            doc.add_paragraph(p)
    if tables:
        for tbl_data in tables:
            if not tbl_data:
                continue
            rows = len(tbl_data)
            cols = max(len(r) for r in tbl_data)
            table = doc.add_table(rows=rows, cols=cols)
            for r_idx, row in enumerate(tbl_data):
                for c_idx, cell_text in enumerate(row):
                    table.cell(r_idx, c_idx).text = cell_text
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def make_arbitrary_zip() -> bytes:
    """Create a valid ZIP archive that does not contain DOCX structure."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("notes.txt", "This is an arbitrary text archive, not a docx.")
    return buf.getvalue()


# ============================================================================
# Valid Document Processing Tests
# ============================================================================

def test_parse_valid_pdf_single_page():
    pdf_bytes = make_pdf_with_text(["Jane Doe\nSoftware Engineer\nSkills: Python, FastAPI"])
    result = parse_resume(pdf_bytes, "jane_resume.pdf")

    assert isinstance(result, ResumeParseResult)
    assert result.filename == "jane_resume.pdf"
    assert result.file_type == ".pdf"
    assert result.page_count == 1
    assert "Jane Doe" in result.text
    assert "Software Engineer" in result.text
    assert "Python, FastAPI" in result.text
    assert result.word_count > 0
    assert result.char_count == len(result.text)


def test_parse_valid_pdf_multi_page():
    pdf_bytes = make_pdf_with_text([
        "Page 1: Education and Profile\nB.Tech in Computer Science",
        "Page 2: Work Experience\nBackend Developer Intern",
        "Page 3: Projects and Certifications\nMachine Learning Pipeline",
    ])
    result = parse_resume(pdf_bytes, "multipage_resume.pdf")

    assert result.page_count == 3
    assert "Education and Profile" in result.text
    assert "Work Experience" in result.text
    assert "Projects and Certifications" in result.text


def test_parse_valid_docx_paragraphs():
    docx_bytes = make_docx_document(
        paragraphs=[
            "Alex Smith",
            "Full Stack Developer",
            "Education: BS in Computer Engineering",
            "Skills: Python, React, PostgreSQL",
        ]
    )
    result = parse_resume(docx_bytes, "alex_resume.docx")

    assert result.file_type == ".docx"
    assert result.page_count is None  # Page count for DOCX must remain unavailable
    assert "Alex Smith" in result.text
    assert "Full Stack Developer" in result.text
    assert "Python, React, PostgreSQL" in result.text
    assert result.word_count > 0


def test_parse_docx_with_tables():
    docx_bytes = make_docx_document(
        paragraphs=["Education Details:"],
        tables=[
            [
                ["Degree", "Institution", "Year", "CGPA"],
                ["B.Tech CSE", "ABC University", "2024", "8.9"],
                ["High School", "XYZ School", "2020", "92%"],
            ]
        ],
    )
    result = parse_resume(docx_bytes, "table_resume.docx")

    assert result.page_count is None
    assert "Education Details:" in result.text
    assert "Degree" in result.text
    assert "B.Tech CSE" in result.text
    assert "ABC University" in result.text
    assert "8.9" in result.text


def test_parse_docx_with_sdt_content_controls():
    """Verify that text inside DOCX Content Controls (w:sdt) is properly extracted."""
    doc = Document()
    sdt_xml = parse_xml(
        '<w:sdt xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        '  <w:sdtContent>'
        '    <w:p><w:r><w:t>Header Candidate in SDT</w:t></w:r></w:p>'
        '  </w:sdtContent>'
        '</w:sdt>'
    )
    doc.element.body.append(sdt_xml)
    doc.add_paragraph("Body Paragraph outside SDT")

    buf = io.BytesIO()
    doc.save(buf)
    result = parse_resume(buf.getvalue(), "sdt_resume.docx")

    assert "Header Candidate in SDT" in result.text
    assert "Body Paragraph outside SDT" in result.text


def test_parse_docx_with_header():
    """Verify that candidate contact info in section headers is extracted."""
    doc = Document()
    section = doc.sections[0]
    header = section.header
    header.paragraphs[0].text = "Jane Doe | jane.doe@example.com | (555) 019-2831"
    doc.add_paragraph("Education: B.S. in Computer Science")

    buf = io.BytesIO()
    doc.save(buf)
    result = parse_resume(buf.getvalue(), "header_resume.docx")

    assert "Jane Doe | jane.doe@example.com" in result.text
    assert "Education: B.S. in Computer Science" in result.text


def test_unicode_and_special_characters():
    docx_bytes = make_docx_document(
        paragraphs=[
            "José González – Senior Développeur",
            "Specialized in: C++, C#, & Python 3.11",
            "Achievements: Delivered “high-impact” feature with 99.9% uptime",
            "• Bullet point item with bullet symbol",
            "Non-breaking space test: Hello\u00a0World",
            "Soft-hyphen test: Multi\u00adthreading",
        ]
    )
    result = parse_resume(docx_bytes, "unicode_resume.docx")

    assert "José González" in result.text
    assert "Développeur" in result.text
    assert "C++" in result.text
    assert "Hello World" in result.text
    assert "•" in result.text
    assert "Multithreading" in result.text


def test_whitespace_normalization():
    messy_text = (
        "  John    Doe   \t\t\n"
        "\n\n\n\n"
        "   Software    Engineer   \n"
        "\n"
        "Skills:   Python ,   FastAPI  \n\n\n"
    )
    normalized = normalize_whitespace(messy_text)

    # Consecutive blank lines should be collapsed to at most \n\n
    assert "\n\n\n" not in normalized
    # Horizontal tabs and consecutive spaces should be collapsed to single spaces
    assert "    " not in normalized
    assert "John Doe" in normalized
    assert "Software Engineer" in normalized
    assert not normalized.startswith(" ")
    assert not normalized.endswith(" ")


def test_has_readable_text_helper():
    assert has_readable_text("John Doe") is True
    assert has_readable_text("123") is True
    assert has_readable_text("A") is True
    assert has_readable_text("") is False
    assert has_readable_text("   \n\t  ") is False
    assert has_readable_text("... --- !!!") is False
    assert has_readable_text(None) is False


# ============================================================================
# Validation and Error Handling Tests
# ============================================================================

def test_empty_file_raises_empty_file_error():
    with pytest.raises(EmptyFileError) as exc_info:
        parse_resume(b"", "empty.pdf")

    assert exc_info.value.error_code == ResumeParsingErrorCode.EMPTY_FILE
    assert exc_info.value.status_code == 400
    assert "empty" in exc_info.value.message.lower()


def test_missing_or_blank_filename():
    with pytest.raises(InvalidFileError) as exc_info:
        parse_resume(b"dummy bytes", "")

    assert exc_info.value.error_code == ResumeParsingErrorCode.INVALID_FILE
    assert exc_info.value.status_code == 400

    with pytest.raises(InvalidFileError):
        parse_resume(b"dummy bytes", "   ")


def test_missing_stem_filename():
    with pytest.raises(InvalidFileError) as exc_info:
        parse_resume(b"dummy bytes", ".pdf")

    assert exc_info.value.error_code == ResumeParsingErrorCode.INVALID_FILE
    assert exc_info.value.status_code == 400


def test_unsupported_file_extension():
    for ext in [".txt", ".png", ".jpg", ".odt", ".rtf", ".exe"]:
        with pytest.raises(UnsupportedFormatError) as exc_info:
            parse_resume(b"some content", f"resume{ext}")
        assert exc_info.value.error_code == ResumeParsingErrorCode.UNSUPPORTED_FORMAT
        assert exc_info.value.status_code == 415


def test_file_size_limit_exceeded():
    oversized = b"%PDF-" + b"0" * (MAX_FILE_SIZE + 10)
    with pytest.raises(FileTooLargeError) as exc_info:
        parse_resume(oversized, "large.pdf")

    assert exc_info.value.error_code == ResumeParsingErrorCode.FILE_TOO_LARGE
    assert exc_info.value.status_code == 413
    assert "5 mb" in exc_info.value.message.lower()


def test_invalid_pdf_content_wrong_magic():
    with pytest.raises(InvalidFileError) as exc_info:
        parse_resume(b"not a valid pdf header", "resume.pdf")

    assert exc_info.value.error_code == ResumeParsingErrorCode.INVALID_FILE
    assert exc_info.value.status_code == 400


def test_corrupted_pdf_content():
    corrupted_pdf = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ncorrupted bytes"
    with pytest.raises(CorruptedFileError) as exc_info:
        parse_resume(corrupted_pdf, "corrupted.pdf")

    assert exc_info.value.error_code == ResumeParsingErrorCode.CORRUPTED_FILE
    assert exc_info.value.status_code == 400


def test_invalid_docx_content_wrong_magic():
    with pytest.raises(InvalidFileError) as exc_info:
        parse_resume(b"plain text not zip", "resume.docx")

    assert exc_info.value.error_code == ResumeParsingErrorCode.INVALID_FILE
    assert exc_info.value.status_code == 400


def test_corrupted_docx_content():
    corrupted_docx = b"PK\x03\x04corrupted_payload_that_is_not_valid_zip"
    with pytest.raises(CorruptedFileError) as exc_info:
        parse_resume(corrupted_docx, "corrupted.docx")

    assert exc_info.value.error_code == ResumeParsingErrorCode.CORRUPTED_FILE
    assert exc_info.value.status_code == 400


def test_arbitrary_zip_renamed_to_docx():
    fake_docx = make_arbitrary_zip()
    with pytest.raises(InvalidFileError) as exc_info:
        parse_resume(fake_docx, "arbitrary_archive.docx")

    assert exc_info.value.error_code == ResumeParsingErrorCode.INVALID_FILE
    assert exc_info.value.status_code == 400


def test_extension_content_mismatch_pdf_named_docx():
    pdf_content = make_pdf_with_text(["Valid PDF Content"])
    with pytest.raises(InvalidFileError) as exc_info:
        parse_resume(pdf_content, "actually_pdf.docx")

    assert exc_info.value.error_code == ResumeParsingErrorCode.INVALID_FILE
    assert exc_info.value.status_code == 400


def test_extension_content_mismatch_docx_named_pdf():
    docx_content = make_docx_document(paragraphs=["Valid DOCX Content"])
    with pytest.raises(InvalidFileError) as exc_info:
        parse_resume(docx_content, "actually_docx.pdf")

    assert exc_info.value.error_code == ResumeParsingErrorCode.INVALID_FILE
    assert exc_info.value.status_code == 400


def test_pdf_no_extractable_text():
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=300)
    buf = io.BytesIO()
    writer.write(buf)
    blank_pdf = buf.getvalue()

    with pytest.raises(NoReadableTextError) as exc_info:
        parse_resume(blank_pdf, "scanned_or_blank.pdf")

    assert exc_info.value.error_code == ResumeParsingErrorCode.NO_READABLE_TEXT
    assert exc_info.value.status_code == 400
    assert "ocr" in exc_info.value.message.lower() or "readable" in exc_info.value.message.lower()


def test_docx_no_extractable_text():
    empty_docx = make_docx_document(paragraphs=["   ", "\t\t\n"])
    with pytest.raises(NoReadableTextError) as exc_info:
        parse_resume(empty_docx, "empty_content.docx")

    assert exc_info.value.error_code == ResumeParsingErrorCode.NO_READABLE_TEXT
    assert exc_info.value.status_code == 400


def test_encrypted_pdf_detection():
    encrypted_pdf = make_encrypted_pdf()
    with pytest.raises(EncryptedFileError) as exc_info:
        parse_resume(encrypted_pdf, "password_protected.pdf")

    assert exc_info.value.error_code == ResumeParsingErrorCode.ENCRYPTED_FILE
    assert exc_info.value.status_code == 400
    assert "password" in exc_info.value.message.lower()


def test_password_protected_docx_detection():
    """Verify that password-protected Office compound binary DOCX documents are detected."""
    ole_header = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 32 + b"EncryptedPackage" + b"\x00" * 200
    with pytest.raises(EncryptedFileError) as exc_info:
        parse_resume(ole_header, "password_protected.docx")

    assert exc_info.value.error_code == ResumeParsingErrorCode.ENCRYPTED_FILE
    assert exc_info.value.status_code == 400


def test_unexpected_extraction_failure_pdf(monkeypatch):
    """Verify that unexpected extraction failures in PDF parsing raise ExtractionFailureError."""
    pdf_bytes = make_pdf_with_text(["Valid text candidate"])

    def broken_extract(self):
        raise RuntimeError("Low-level internal C-extension failure")

    with patch("pypdf._page.PageObject.extract_text", broken_extract):
        with pytest.raises(ExtractionFailureError) as exc_info:
            parse_resume(pdf_bytes, "broken_extract.pdf")

    assert exc_info.value.error_code == ResumeParsingErrorCode.PARSER_ERROR
    assert exc_info.value.status_code == 422


def test_unexpected_extraction_failure_docx():
    """Verify that unexpected extraction failures in DOCX parsing raise ExtractionFailureError."""
    docx_bytes = make_docx_document(paragraphs=["Valid candidate"])

    with patch("app.services.resume_parser.extract_text_from_docx", side_effect=RuntimeError("Unexpected error")):
        with pytest.raises(ExtractionFailureError) as exc_info:
            parse_resume(docx_bytes, "broken.docx")

    assert exc_info.value.error_code == ResumeParsingErrorCode.PARSER_ERROR
    assert exc_info.value.status_code == 422


def test_no_data_leakage_between_separate_requests():
    """Verify that multiple parsing invocations are isolated with no shared state."""
    doc1 = make_pdf_with_text(["Candidate One\nPython Developer"])
    doc2 = make_pdf_with_text(["Candidate Two\nJava Architect"])

    res1 = parse_resume(doc1, "candidate1.pdf")
    res2 = parse_resume(doc2, "candidate2.pdf")

    assert "Candidate One" in res1.text
    assert "Candidate Two" not in res1.text

    assert "Candidate Two" in res2.text
    assert "Candidate One" not in res2.text


# ============================================================================
# API Route Integration Tests
# ============================================================================

def make_mock_auth_user():
    from app.routers.auth import UserResponse
    return UserResponse(email="teststudent@example.com", role="student")


def test_direct_parse_endpoint_success():
    from app.routers.auth import get_current_user

    pdf_bytes = make_pdf_with_text(["Test API Candidate\nFastAPI Engineer"])
    app.dependency_overrides[get_current_user] = make_mock_auth_user

    try:
        response = client.post(
            "/resumes/parse",
            files={"file": ("test_resume.pdf", pdf_bytes, "application/pdf")},
        )
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["status"] == "success"
        assert data["filename"] == "test_resume.pdf"
        assert data["file_type"] == ".pdf"
        assert data["page_count"] == 1
        assert "Test API Candidate" in data["text"]
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_direct_parse_endpoint_invalid_file():
    from app.routers.auth import get_current_user

    app.dependency_overrides[get_current_user] = make_mock_auth_user

    try:
        response = client.post(
            "/resumes/parse",
            files={"file": ("invalid.txt", b"plain text", "text/plain")},
        )
        assert response.status_code == 415
        data = response.json()
        assert "unsupported" in data["detail"].lower()
        assert data["error_code"] == ResumeParsingErrorCode.UNSUPPORTED_FORMAT
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_direct_parse_endpoint_empty_file():
    from app.routers.auth import get_current_user

    app.dependency_overrides[get_current_user] = make_mock_auth_user

    try:
        response = client.post(
            "/resumes/parse",
            files={"file": ("empty.pdf", b"", "application/pdf")},
        )
        assert response.status_code == 400
        data = response.json()
        assert "empty" in data["detail"].lower()
        assert data["error_code"] == ResumeParsingErrorCode.EMPTY_FILE
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_direct_parse_endpoint_unreadable_pdf():
    from app.routers.auth import get_current_user

    writer = PdfWriter()
    writer.add_blank_page(width=300, height=300)
    buf = io.BytesIO()
    writer.write(buf)
    blank_pdf = buf.getvalue()

    app.dependency_overrides[get_current_user] = make_mock_auth_user

    try:
        response = client.post(
            "/resumes/parse",
            files={"file": ("blank.pdf", blank_pdf, "application/pdf")},
        )
        assert response.status_code == 400
        data = response.json()
        assert "readable" in data["detail"].lower() or "ocr" in data["detail"].lower()
        assert data["error_code"] == ResumeParsingErrorCode.NO_READABLE_TEXT
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_parse_by_id_endpoint_success(monkeypatch, tmp_path):
    from app.routers.auth import get_current_user
    import app.routers.resumes as resumes_router

    # Prepare storage directory and test file
    test_storage_dir = tmp_path / "storage" / "resumes"
    test_storage_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(resumes_router, "STORAGE_DIR", test_storage_dir)

    storage_key = "test_key_123.pdf"
    file_path = test_storage_dir / storage_key
    file_path.write_bytes(make_pdf_with_text(["John Placement Candidate\nData Scientist"]))

    # Mock database connection
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    # Mock user query return, then resume query return
    mock_cursor.fetchone.side_effect = [
        (1,),  # user_id
        ("res-id-1", "placement.pdf", storage_key, "pdf"),  # resume
    ]
    mock_conn.execute.return_value = mock_cursor
    mock_conn.__enter__.return_value = mock_conn

    monkeypatch.setattr(resumes_router, "get_connection", lambda: mock_conn)
    app.dependency_overrides[get_current_user] = make_mock_auth_user

    try:
        response = client.post("/resumes/res-id-1/parse")
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["status"] == "success"
        assert data["resume_id"] == "res-id-1"
        assert data["filename"] == "placement.pdf"
        assert "Data Scientist" in data["text"]

        # Verify database update to 'parsed' was called
        calls = [str(call) for call in mock_conn.execute.mock_calls]
        assert any("status = 'parsed'" in call for call in calls)
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_parse_by_id_endpoint_unreadable_marks_status_failed(monkeypatch, tmp_path):
    from app.routers.auth import get_current_user
    import app.routers.resumes as resumes_router

    test_storage_dir = tmp_path / "storage" / "resumes"
    test_storage_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(resumes_router, "STORAGE_DIR", test_storage_dir)

    storage_key = "blank_key.pdf"
    file_path = test_storage_dir / storage_key

    writer = PdfWriter()
    writer.add_blank_page(width=300, height=300)
    buf = io.BytesIO()
    writer.write(buf)
    file_path.write_bytes(buf.getvalue())

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.side_effect = [
        (1,),  # user_id
        ("res-id-2", "blank.pdf", storage_key, "pdf"),  # resume
    ]
    mock_conn.execute.return_value = mock_cursor
    mock_conn.__enter__.return_value = mock_conn

    monkeypatch.setattr(resumes_router, "get_connection", lambda: mock_conn)
    app.dependency_overrides[get_current_user] = make_mock_auth_user

    try:
        response = client.post("/resumes/res-id-2/parse")
        assert response.status_code == 400
        data = response.json()
        assert data["error_code"] == ResumeParsingErrorCode.NO_READABLE_TEXT

        # Verify database update to 'failed' was called
        calls = [str(call) for call in mock_conn.execute.mock_calls]
        assert any("status = 'failed'" in call for call in calls)
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_upload_service_rejects_arbitrary_zip_file():
    """Verify that upload_service rejects arbitrary zip files renamed to .docx."""
    from app.services.upload_service import validate_resume
    from fastapi import UploadFile

    fake_docx_bytes = make_arbitrary_zip()
    upload_file = UploadFile(
        filename="fake.docx",
        file=io.BytesIO(fake_docx_bytes),
    )

    with pytest.raises(InvalidFileError) as exc_info:
        import asyncio
        asyncio.run(validate_resume(upload_file))

    assert exc_info.value.error_code == ResumeParsingErrorCode.INVALID_FILE
    assert "valid docx" in exc_info.value.message.lower()


def test_upload_service_rejects_empty_file():
    from app.services.upload_service import validate_resume
    from fastapi import UploadFile

    upload_file = UploadFile(
        filename="empty.pdf",
        file=io.BytesIO(b""),
    )

    with pytest.raises(EmptyFileError) as exc_info:
        import asyncio
        asyncio.run(validate_resume(upload_file))

    assert exc_info.value.error_code == ResumeParsingErrorCode.EMPTY_FILE
