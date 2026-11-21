
import sys
from io import BytesIO
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import psycopg
from docx import Document
from fastapi.testclient import TestClient
from pypdf import PdfWriter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from main import app

client = TestClient(app)


def make_pdf() -> bytes:
    """Create a valid PDF for upload testing."""
    buffer = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=300)
    writer.write(buffer)
    return buffer.getvalue()


def make_docx() -> bytes:
    """Create a valid DOCX for upload testing."""
    buffer = BytesIO()
    document = Document()
    document.add_paragraph("Sample resume for upload testing.")
    document.save(buffer)
    return buffer.getvalue()


def get_auth_headers() -> dict:
    """Register a test user, log in, and return a bearer token."""
    email = f"upload-{uuid4().hex}@example.com"
    password = "TestPass123!"

    registration = client.post(
        "/auth/register",
        json={
            "full_name": "Upload Test Student",
            "email": email,
            "password": password,
        },
    )
    assert registration.status_code == 201, registration.text

    response = client.post(
        "/auth/login",
        data={
            "username": email,
            "password": password,
        },
    )
    assert response.status_code == 200, response.text

    return {
        "Authorization": f"Bearer {response.json()['access_token']}"
    }


def test_upload_valid_pdf():
    response = client.post(
        "/resumes/upload",
        headers=get_auth_headers(),
        files={"file": ("resume.pdf", make_pdf(), "application/pdf")},
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["file_type"] == ".pdf"
    assert data["status"] == "success"
    assert data["parsing"]["status"] == "pending"


def test_upload_valid_docx():
    response = client.post(
        "/resumes/upload",
        headers=get_auth_headers(),
        files={
            "file": (
                "resume.docx",
                make_docx(),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["file_type"] == ".docx"
    assert data["status"] == "success"
    assert data["parsing"]["status"] == "pending"


def test_upload_unsupported_extension():
    response = client.post(
        "/resumes/upload",
        headers=get_auth_headers(),
        files={"file": ("resume.txt", b"sample text", "text/plain")},
    )

    assert response.status_code == 415


def test_upload_empty_file():
    response = client.post(
        "/resumes/upload",
        headers=get_auth_headers(),
        files={"file": ("resume.pdf", b"", "application/pdf")},
    )

    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_upload_corrupted_pdf():
    response = client.post(
        "/resumes/upload",
        headers=get_auth_headers(),
        files={"file": ("resume.pdf", b"%PDF-1.4", "application/pdf")},
    )

    assert response.status_code == 400


def test_upload_wrong_pdf_signature():
    response = client.post(
        "/resumes/upload",
        headers=get_auth_headers(),
        files={"file": ("resume.pdf", b"not a pdf", "application/pdf")},
    )

    assert response.status_code == 400


def test_upload_file_too_large():
    oversized_content = b"%PDF-" + b"A" * (5 * 1024 * 1024)

    response = client.post(
        "/resumes/upload",
        headers=get_auth_headers(),
        files={
            "file": (
                "resume.pdf",
                oversized_content,
                "application/pdf",
            )
        },
    )

    assert response.status_code == 413


def test_upload_without_authentication():
    response = client.post(
        "/resumes/upload",
        files={"file": ("resume.pdf", make_pdf(), "application/pdf")},
    )

    assert response.status_code == 401


def test_upload_corrupted_docx_returns_client_error():
    response = client.post(
        "/resumes/upload",
        headers=get_auth_headers(),
        files={
            "file": (
                "corrupted_resume.docx",
                b"PK\x03\x04this-is-not-a-valid-docx",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )

    assert 400 <= response.status_code < 500, response.text


def test_upload_persists_resume_file_and_metadata():
    from app.database import get_connection
    from app.routers.resumes import STORAGE_DIR

    response = client.post(
        "/resumes/upload",
        headers=get_auth_headers(),
        files={
            "file": (
                "persistence_test.pdf",
                make_pdf(),
                "application/pdf",
            )
        },
    )

    assert response.status_code == 200, response.text
    data = response.json()

    with get_connection() as conn:
        resume = conn.execute(
            """
            SELECT
                original_filename,
                storage_key,
                file_type,
                file_size_bytes,
                status,
                processed_at
            FROM resumes
            WHERE id = %s
            """,
            (data["resume_id"],),
        ).fetchone()

    assert resume is not None
    assert resume[0] == "persistence_test.pdf"
    assert resume[2] == "pdf"
    assert resume[3] == len(make_pdf())
    assert resume[4] == "uploaded"
    assert resume[5] is None

    stored_file = Path(STORAGE_DIR) / resume[1]
    assert stored_file.is_file()
    assert stored_file.stat().st_size == resume[3]


def test_upload_database_failure_removes_new_file(monkeypatch):
    import app.routers.resumes as resumes_router

    created_paths = []
    original_open = Path.open

    def tracking_open(path, *args, **kwargs):
        result = original_open(path, *args, **kwargs)
        if (
            path.parent == Path(resumes_router.STORAGE_DIR)
            and args
            and "x" in args[0]
        ):
            created_paths.append(path)
        return result

    monkeypatch.setattr(Path, "open", tracking_open)

    with patch.object(
        resumes_router,
        "get_connection",
        side_effect=psycopg.OperationalError(
            "Simulated database failure"
        ),
    ):
        response = client.post(
            "/resumes/upload",
            headers=get_auth_headers(),
            files={
                "file": (
                    "failure_cleanup_test.pdf",
                    make_pdf(),
                    "application/pdf",
                )
            },
        )

    assert response.status_code == 500
    assert len(created_paths) == 1
    assert not created_paths[0].exists()
