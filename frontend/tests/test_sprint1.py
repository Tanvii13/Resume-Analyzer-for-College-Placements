"""
Sprint 1 acceptance tests — one test group per user story.
Run with:  pytest -v
"""

import io
import os
import pytest

from app import app, USERS, RESUMES

SAMPLES = os.path.join(os.path.dirname(__file__), "..", "sample_resumes")
STUDENT = {"email": "alex.rivera@dau.ac.in", "password": "Password@123", "role": "student"}


@pytest.fixture
def client(tmp_path):
    app.config.update(TESTING=True, UPLOAD_FOLDER=str(tmp_path))
    RESUMES.clear()
    with app.test_client() as c:
        yield c


def login(client, **overrides):
    return client.post("/login", data={**STUDENT, **overrides})


def upload(client, filename, data=None):
    if data is None:
        with open(os.path.join(SAMPLES, filename), "rb") as f:
            data = f.read()
    return client.post("/upload", data={"resume": (io.BytesIO(data), filename)},
                       content_type="multipart/form-data")


def last_resume():
    return RESUMES[STUDENT["email"]][0]


# --------------------------------------------------------------------------
# US-01  User login and account access
# --------------------------------------------------------------------------
class TestUS01Login:
    def test_dashboard_requires_login(self, client):
        r = client.get("/dashboard")
        assert r.status_code == 302 and "/login" in r.location

    def test_valid_login_opens_dashboard(self, client):
        r = login(client)
        assert r.status_code == 302 and r.location.endswith("/dashboard")
        assert b"Welcome, Alex" in client.get("/dashboard").data

    def test_wrong_password_shows_generic_error(self, client):
        r = login(client, password="wrong-password")
        assert r.status_code == 401
        assert b"Invalid email or password" in r.data

    def test_unknown_email_shows_same_error(self, client):
        r = login(client, email="nobody@dau.ac.in")
        assert r.status_code == 401
        assert b"Invalid email or password" in r.data

    def test_wrong_role_tab_is_rejected(self, client):
        r = login(client, role="admin")
        assert r.status_code == 403

    def test_register_then_login(self, client):
        r = client.post("/register", data={"name": "Neha Patel", "email": "neha@dau.ac.in",
                                           "password": "Strong@123", "confirm": "Strong@123"})
        assert r.status_code == 302
        assert USERS["neha@dau.ac.in"]["role"] == "student"
        assert USERS["neha@dau.ac.in"]["password_hash"] != "Strong@123"   # stored hashed
        assert login(client, email="neha@dau.ac.in", password="Strong@123").status_code == 302
        del USERS["neha@dau.ac.in"]

    @pytest.mark.parametrize("form, message", [
        ({"name": "", "email": "a@dau.ac.in", "password": "Strong@123", "confirm": "Strong@123"}, b"All fields are required"),
        ({"name": "A", "email": "not-an-email", "password": "Strong@123", "confirm": "Strong@123"}, b"valid university email"),
        ({"name": "A", "email": "a@dau.ac.in", "password": "short", "confirm": "short"}, b"at least 8 characters"),
        ({"name": "A", "email": "a@dau.ac.in", "password": "Strong@123", "confirm": "Other@123"}, b"do not match"),
        ({"name": "A", "email": "alex.rivera@dau.ac.in", "password": "Strong@123", "confirm": "Strong@123"}, b"already exists"),
    ])
    def test_register_validation(self, client, form, message):
        r = client.post("/register", data=form)
        assert r.status_code == 400 and message in r.data

    def test_logout_ends_session(self, client):
        login(client)
        client.get("/logout")
        assert client.get("/dashboard").status_code == 302


# --------------------------------------------------------------------------
# US-02  Upload resume
# --------------------------------------------------------------------------
class TestUS02Upload:
    def test_upload_requires_login(self, client):
        assert upload(client, "sample_resume.pdf").status_code == 302
        assert STUDENT["email"] not in RESUMES

    @pytest.mark.parametrize("name", ["sample_resume.pdf", "sample_resume.docx"])
    def test_valid_upload_is_accepted(self, client, name):
        login(client)
        r = upload(client, name)
        assert r.status_code == 302 and "/resume/" in r.location
        assert last_resume()["status"] == "Parsed"

    def test_file_saved_privately_with_random_name(self, client):
        login(client)
        upload(client, "sample_resume.pdf")
        stored = last_resume()["stored_name"]
        assert stored != "sample_resume.pdf"
        assert os.path.exists(os.path.join(app.config["UPLOAD_FOLDER"], stored))
        assert client.get(f"/uploads/{stored}").status_code == 404   # not publicly served

    def test_officer_cannot_upload(self, client):
        login(client, email="officer@dau.ac.in", role="officer")
        assert upload(client, "sample_resume.pdf").status_code == 403


# --------------------------------------------------------------------------
# US-03  Parse uploaded resume
# --------------------------------------------------------------------------
class TestUS03Parse:
    @pytest.mark.parametrize("name", ["sample_resume.pdf", "sample_resume.docx"])
    def test_sections_are_detected(self, client, name):
        login(client)
        upload(client, name)
        parsed = last_resume()["parsed"]
        titles = {s["title"] for s in parsed["sections"]}
        assert {"Education", "Skills", "Projects", "Experience"} <= titles
        assert parsed["missing"] == []

    def test_contact_details_extracted(self, client):
        login(client)
        upload(client, "sample_resume.pdf")
        contact = last_resume()["parsed"]["contact"]
        assert contact["name"] == "Alex Rivera"
        assert contact["email"] == "alex.rivera@dau.ac.in"
        assert "98765" in contact["phone"]
        assert any("github.com" in l for l in contact["links"])

    def test_parsed_view_shows_sections(self, client):
        login(client)
        r = upload(client, "sample_resume.pdf")
        page = client.get(r.location).data
        assert b"Education" in page and b"Dhirubhai Ambani University" in page

    def test_cannot_view_another_students_resume(self, client):
        login(client)
        upload(client, "sample_resume.pdf")
        resume_id = last_resume()["id"]
        client.get("/logout")
        client.post("/register", data={"name": "Other", "email": "other@dau.ac.in",
                                       "password": "Strong@123", "confirm": "Strong@123"})
        login(client, email="other@dau.ac.in", password="Strong@123")
        assert client.get(f"/resume/{resume_id}").status_code == 404
        del USERS["other@dau.ac.in"]


# --------------------------------------------------------------------------
# US-04  Handle invalid resume
# --------------------------------------------------------------------------
class TestUS04Invalid:
    @pytest.mark.parametrize("filename, data, code", [
        ("resume.exe", b"MZ\x90\x00", "ERR_FILE_TYPE"),
        ("resume.txt", b"plain text", "ERR_FILE_TYPE"),
        ("empty.pdf", b"", "ERR_EMPTY_FILE"),
        ("fake_resume.pdf", None, "ERR_FILE_CORRUPT"),
        ("scanned_resume.pdf", None, "ERR_NO_TEXT"),
        ("protected_resume.pdf", None, "ERR_PASSWORD_PROTECTED"),
        ("broken.pdf", b"%PDF-1.4\n" + b"\x00garbage" * 50, None),   # damaged PDF
        ("big.pdf", b"%PDF-" + b"0" * (6 * 1024 * 1024), "ERR_FILE_TOO_LARGE"),
    ])
    def test_invalid_file_explained_and_recorded(self, client, filename, data, code):
        login(client)
        r = upload(client, filename, data)
        assert r.status_code == 302 and r.location.endswith("/dashboard#upload")
        record = last_resume()
        assert record["status"] == "Failed"
        if code:
            assert record["error_code"] == code
        else:
            assert record["error_code"] in ("ERR_UNREADABLE", "ERR_NO_TEXT")
        assert record["error_message"]

    def test_error_and_retry_shown_on_dashboard(self, client):
        login(client)
        upload(client, "fake_resume.pdf")
        page = client.get("/dashboard").data
        assert b"Upload failed" in page and b"ERR_FILE_CORRUPT" in page
        assert b"Retry" in page

    def test_failed_file_is_not_kept(self, client):
        login(client)
        upload(client, "scanned_resume.pdf")
        assert os.listdir(app.config["UPLOAD_FOLDER"]) == []

    def test_retry_after_failure_succeeds(self, client):
        login(client)
        upload(client, "scanned_resume.pdf")
        upload(client, "sample_resume.pdf")
        statuses = [r["status"] for r in RESUMES[STUDENT["email"]]]
        assert statuses == ["Parsed", "Failed"]
