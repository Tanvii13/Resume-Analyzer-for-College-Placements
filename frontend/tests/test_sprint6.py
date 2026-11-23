"""
Sprint 6 acceptance tests — EPIC 6: Security, Privacy & Responsible Use
One test group per user story. Run with:  pytest -v

  US-16  Manage Role-Based Access                         (FR-15, NFR-07, DR-07)
  US-17  Protect Student Resume Data                      (NFR-03, NFR-09, DR-08)
  US-18  Keep Automated Results as Supporting Information (DR-06)
  US-19  Check Scoring and Matching for Fairness          (DR-09)
"""

import html
import io
import json
import os
import re
from datetime import datetime, timedelta

import pytest
from werkzeug.security import generate_password_hash

import app as app_module
import fairness
from app import (app, USERS, RESUMES, PERMISSIONS, ACCESS_LOG, AUDIT_LOG, REVIEWS,
                 FAIRNESS_ISSUES, OPPORTUNITIES, analyze_resume, compare_skills)
from resume_parser import extract_text

SAMPLES = os.path.join(os.path.dirname(__file__), "..", "sample_resumes")
PW = "Password@123"
STUDENT, OFFICER, ADMIN = "alex.rivera@dau.ac.in", "officer@dau.ac.in", "admin@dau.ac.in"
ROLE_OF = {STUDENT: "student", OFFICER: "officer", ADMIN: "admin"}


@pytest.fixture
def client(tmp_path):
    app.config.update(TESTING=True, UPLOAD_FOLDER=str(tmp_path))
    RESUMES.clear()
    saved = {email: dict(u) for email, u in USERS.items()}
    USERS[STUDENT].pop("consent_at", None)          # every test starts before the student has agreed
    with app.test_client() as c:
        yield c
    USERS.clear()
    USERS.update(saved)


def login(client, email, role=None):
    client.get("/logout")
    return client.post("/login", data={"email": email, "password": PW, "role": role or ROLE_OF[email]})


def upload(client, filename="sample_resume.pdf", consent=True):
    with open(os.path.join(SAMPLES, filename), "rb") as f:
        data = {"resume": (io.BytesIO(f.read()), filename)}
    if consent:
        data["consent"] = "on"
    return client.post("/upload", data=data, content_type="multipart/form-data")


def student_resume(client):
    """Log in as the student, upload the sample, and return the resume record."""
    login(client, STUDENT)
    upload(client)
    return RESUMES[STUDENT][0]


def text_of(name):
    return extract_text(os.path.join(SAMPLES, name), name.rsplit(".", 1)[1])[0]


# ==========================================================================
# US-16: Manage Role-Based Access
# ==========================================================================
class TestUS16Access:
    # One real request per permission. True = the role was allowed to do it.
    def attempt(self, client, permission, resume):
        url = f"/staff/students/{STUDENT}/resumes/{resume['id']}"
        if permission == "upload_resume":
            r = upload(client)
            return r.status_code == 302 and "/resume/" in r.location
        if permission == "job_match":
            return client.get("/matching").status_code == 200
        if permission == "view_reports":
            return client.get("/staff/dashboard").status_code == 200
        if permission == "view_students":
            return client.get("/staff/students").status_code == 200 and client.get(url).status_code == 200
        if permission == "review_students":
            client.post(url + "/review", data={"decision": "Follow up with student"})
            return resume["id"] in REVIEWS
        if permission == "manage_access":
            return client.get("/admin/access").status_code == 200
        if permission == "review_fairness":
            return client.get("/admin/fairness").status_code == 200
        if permission == "manage_data":
            return client.get("/admin/data").status_code == 200
        raise AssertionError(f"Add a test for the new permission '{permission}'")

    @pytest.mark.parametrize("permission", list(PERMISSIONS))
    @pytest.mark.parametrize("email", [STUDENT, OFFICER, ADMIN])
    def test_each_role_gets_exactly_its_permissions(self, client, permission, email):
        """Criterion 1 and 2: the table in app.py is what the server actually enforces."""
        resume = student_resume(client)
        login(client, email)
        expected = ROLE_OF[email] in PERMISSIONS[permission][1]
        assert self.attempt(client, permission, resume) == expected

    def test_every_private_page_needs_login(self, client):
        public = {"index", "register", "login", "logout", "privacy", "static"}
        checked = 0
        for rule in app.url_map.iter_rules():
            if rule.endpoint in public:
                continue
            url = re.sub(r"<(?:path:)?\w+>", "x", rule.rule)
            r = client.open(url, method="POST" if "POST" in rule.methods else "GET")
            assert r.status_code == 302 and "/login" in r.location, rule.rule
            checked += 1
        assert checked >= 15

    def test_role_change_applies_immediately(self, client):
        """Criterion 3: an officer made a student loses staff pages on the next click."""
        login(client, OFFICER)
        assert client.get("/staff/students").status_code == 200
        with app.test_client() as admin:
            login(admin, ADMIN)
            admin.post(f"/admin/access/{OFFICER}", data={"role": "student", "active": "on"})
        assert USERS[OFFICER]["role"] == "student"
        assert client.get("/staff/students").status_code == 403
        assert AUDIT_LOG[0]["action"] == "Changed role"

    def test_turning_an_account_off_logs_it_out(self, client):
        login(client, STUDENT)
        with app.test_client() as admin:
            login(admin, ADMIN)
            admin.post(f"/admin/access/{STUDENT}", data={"role": "student", "active": "off"})
        r = client.get("/dashboard")
        assert r.status_code == 302 and "/login" in r.location
        assert login(client, STUDENT).status_code == 403

    def test_admin_cannot_lock_themselves_out(self, client):
        login(client, ADMIN)
        client.post(f"/admin/access/{ADMIN}", data={"role": "student", "active": "on"})
        assert USERS[ADMIN]["role"] == "admin"

    def test_navigation_matches_the_role(self, client):
        login(client, STUDENT)
        page = client.get("/dashboard").data.decode()
        assert 'href="/matching"' in page and 'href="/admin/access"' not in page and 'href="/staff/students"' not in page
        login(client, OFFICER)
        page = client.get("/staff/dashboard").data.decode()
        assert 'href="/staff/students"' in page and 'href="/matching"' not in page and 'href="/admin/access"' not in page
        login(client, ADMIN)
        page = client.get("/staff/dashboard").data.decode()
        assert all(f'href="/admin/{p}"' in page for p in ("access", "fairness", "data"))

    def test_form_without_token_is_refused(self, client):
        app.config["CSRF_ENABLED"] = True
        r = client.post("/login", data={"email": STUDENT, "password": PW, "role": "student"})
        assert r.status_code == 400 and b"This form has expired" in r.data

    def test_form_with_token_works(self, client):
        app.config["CSRF_ENABLED"] = True
        token = re.search(r'name="csrf_token" value="([^"]+)"', client.get("/login").data.decode()).group(1)
        r = client.post("/login", data={"email": STUDENT, "password": PW, "role": "student", "csrf_token": token})
        assert r.status_code == 302

    def test_every_form_carries_the_token(self):
        folder = os.path.join(app.root_path, "templates")
        for name in os.listdir(folder):
            page = open(os.path.join(folder, name), encoding="utf-8").read()
            for tag in re.findall(r"<form\b[^>]*>", page, re.S):
                if re.search(r'method="post"', tag, re.I):
                    assert "csrf_field()" in page[page.index(tag) + len(tag):][:30], f"{name}: {tag}"

    def test_login_limit(self, client):
        for _ in range(5):
            client.post("/login", data={"email": STUDENT, "password": "wrong", "role": "student"})
        r = login(client, STUDENT)
        assert r.status_code == 429 and b"Too many wrong passwords" in r.data

    def test_idle_session_ends(self, client):
        login(client, STUDENT)
        with client.session_transaction() as s:
            s["last_seen"] = (datetime.now() - timedelta(minutes=31)).isoformat()
        assert "/login" in client.get("/dashboard").location

    def test_security_headers(self, client):
        login(client, STUDENT)
        r = client.get("/dashboard")
        assert r.headers["X-Frame-Options"] == "DENY" and r.headers["X-Content-Type-Options"] == "nosniff"
        assert "frame-ancestors 'none'" in r.headers["Content-Security-Policy"]
        assert r.headers["Cache-Control"] == "no-store"


# ==========================================================================
# US-17: Protect Student Resume Data
# ==========================================================================
class TestUS17Privacy:
    def test_consent_before_the_first_upload(self, client):
        login(client, STUDENT)
        assert 'name="consent"' in client.get("/dashboard").data.decode()
        upload(client, consent=False)
        assert RESUMES[STUDENT][0]["error_code"] == "ERR_CONSENT_REQUIRED"

    def test_consent_is_asked_once(self, client):
        login(client, STUDENT)
        upload(client)
        assert USERS[STUDENT]["consent_at"] and RESUMES[STUDENT][0]["status"] == "Parsed"
        assert 'name="consent"' not in client.get("/dashboard").data.decode()
        upload(client, consent=False)
        assert RESUMES[STUDENT][0]["status"] == "Parsed"

    def test_students_cannot_open_each_other(self, client):
        """Criterion 1: only authorised users."""
        resume = student_resume(client)
        USERS["other@dau.ac.in"] = {"name": "Other", "email": "other@dau.ac.in",
                                    "password_hash": generate_password_hash(PW), "role": "student"}
        client.get("/logout")
        client.post("/login", data={"email": "other@dau.ac.in", "password": PW, "role": "student"})
        assert client.get(f"/resume/{resume['id']}").status_code == 404
        assert client.get(f"/staff/students/{STUDENT}/resumes/{resume['id']}").status_code == 403

    def test_staff_see_only_what_they_need(self, client):
        """Criterion 2: the analysis, not the phone number, links or full text."""
        resume = student_resume(client)
        login(client, OFFICER)
        page = client.get(f"/staff/students/{STUDENT}/resumes/{resume['id']}").data.decode()
        assert "Skills Identified" in page
        assert "98765 43210" not in page and "github.com/alexrivera" not in page
        assert "Campus Event Finder" not in page                 # a line of the resume text

    def test_staff_views_are_shown_to_the_student(self, client):
        resume = student_resume(client)
        login(client, OFFICER)
        client.get(f"/staff/students/{STUDENT}/resumes/{resume['id']}")
        login(client, STUDENT)
        page = client.get("/dashboard").data.decode()
        assert "Who has seen your analysis" in page and "Priya Shah · Placement Officer" in page

    def test_logs_never_hold_resume_text(self, client):
        resume = student_resume(client)
        login(client, OFFICER)
        client.get(f"/staff/students/{STUDENT}/resumes/{resume['id']}")
        assert "Campus Event Finder" not in json.dumps(ACCESS_LOG + AUDIT_LOG)

    def test_student_can_delete_a_resume(self, client, tmp_path):
        resume = student_resume(client)
        stored = tmp_path / resume["stored_name"]
        assert stored.exists()
        client.post(f"/resume/{resume['id']}/delete")
        assert not stored.exists() and RESUMES[STUDENT] == []

    def test_download_my_data(self, client):
        student_resume(client)
        r = client.get("/my-data.json")
        data = json.loads(r.data)
        assert "attachment" in r.headers["Content-Disposition"]
        assert data["account"]["email"] == STUDENT and data["resumes"][0]["filename"] == "sample_resume.pdf"
        assert "password" not in json.dumps(data)

    def test_retention(self, client, tmp_path):
        """Criterion 3: uploads past the retention period are deleted."""
        resume = student_resume(client)
        resume["uploaded_at"] = (datetime.now() - timedelta(days=app.config["RETENTION_DAYS"] + 1)).isoformat()
        assert app_module.purge_expired() == 1
        assert RESUMES[STUDENT] == [] and not (tmp_path / resume["stored_name"]).exists()

    def test_no_demo_accounts_or_passwords_shown(self, client):
        """The finished site shows no demo logins, and ships with no demo student."""
        for url in ("/", "/login", "/register", "/privacy"):
            page = client.get(url).data.decode()
            assert "Password@123" not in page and "Demo student" not in page, url
            assert "IT314" not in page and "Group 26" not in page, url       # no course or team labels
        source = open(os.path.join(app.root_path, "app.py"), encoding="utf-8").read()
        starting_accounts = source[source.index("USERS = {"):source.index("RESUMES = {}")]
        assert '"role": "student"' not in starting_accounts

    def test_privacy_page_is_public(self, client):
        page = html.unescape(client.get("/privacy").data.decode())
        for heading in ["What we store, and why", "Who can see it", "How long it's kept", "How results are worked out"]:
            assert heading in page
        assert 'href="/privacy"' in client.get("/").data.decode()


# ==========================================================================
# US-18: Keep Automated Results as Supporting Information
# ==========================================================================
class TestUS18Supporting:
    def test_results_say_they_are_supporting_information(self, client):
        resume = student_resume(client)
        assert "Supporting information, not a decision" in client.get(f"/resume/{resume['id']}").data.decode()
        login(client, OFFICER)
        for url in ("/staff/dashboard", "/staff/students", f"/staff/students/{STUDENT}/resumes/{resume['id']}"):
            assert "The final decision is yours" in client.get(url).data.decode(), url

    def test_a_low_score_never_hides_a_student(self, client):
        """Criterion 1: nobody is filtered out by a score."""
        USERS["low@dau.ac.in"] = {"name": "Low Score", "email": "low@dau.ac.in",
                                  "password_hash": generate_password_hash(PW), "role": "student", "consent_at": "x"}
        client.post("/login", data={"email": "low@dau.ac.in", "password": PW, "role": "student"})
        upload(client, "sample_resume.docx")
        RESUMES["low@dau.ac.in"][0]["parsed"]["sections"] = []      # score drops to the minimum
        login(client, OFFICER)
        assert "Low Score" in client.get("/staff/students").data.decode()

    def test_resume_page_uses_the_site_layout(self, client):
        """The resume page had lost its layout in an earlier merge; the notice must show with the nav."""
        resume = student_resume(client)
        page = client.get(f"/resume/{resume['id']}").data.decode()
        assert page.startswith("<!DOCTYPE html>") and 'class="app-nav"' in page

    def test_no_feature_rejects_anyone(self):
        assert not [r.rule for r in app.url_map.iter_rules() if re.search(r"reject|shortlist|hire|select", r.rule + r.endpoint)]
        assert not any("reject" in option.lower() for option in app_module.REVIEW_OPTIONS)

    def test_officer_records_the_decision(self, client):
        """Criterion 3: the decision is a person's, saved with their name."""
        resume = student_resume(client)
        login(client, OFFICER)
        url = f"/staff/students/{STUDENT}/resumes/{resume['id']}"
        client.post(url + "/review", data={"decision": "Needs support before drives", "note": "Add projects"})
        assert REVIEWS[resume["id"]]["by"] == "Priya Shah"
        assert "Needs support before drives" in client.get("/staff/students").data.decode()

    def test_students_cannot_record_reviews(self, client):
        resume = student_resume(client)
        url = f"/staff/students/{STUDENT}/resumes/{resume['id']}/review"
        assert client.post(url, data={"decision": "Ready for placement drives"}).status_code == 403


# ==========================================================================
# US-19: Check Scoring and Matching for Fairness
# ==========================================================================
class TestUS19Fairness:
    def test_factor_list_matches_the_code(self):
        """Criterion 1: the factors shown are exactly the ones analyze_resume() scores."""
        parsed = {"sections": [], "contact": {}}
        assert [c["title"] for c in analyze_resume(parsed)["criteria"]] == [f[0] for f in fairness.SCORING_FACTORS]
        assert sum(f[1] for f in fairness.SCORING_FACTORS) == 100

    @pytest.mark.parametrize("name", ["sample_resume.pdf", "sample_resume.docx"])
    def test_personal_details_never_change_score_or_match(self, name):
        """Criterion 2."""
        result = fairness.check_text(text_of(name), analyze_resume, compare_skills, OPPORTUNITIES)
        assert result["checks"] >= 8 and result["issues"] == []

    def test_every_variant_really_changes_the_resume(self):
        text = text_of("sample_resume.pdf")
        from resume_parser import parse_text
        for label, changed in fairness.variants(text, parse_text(text)):
            assert changed != text, label

    def test_a_biased_rule_would_be_caught(self):
        """If the score ever depended on a stated gender, the check must find it."""
        def biased(parsed):
            result = analyze_resume(parsed)
            text = "\n".join(s["content"] for s in parsed["sections"])
            return {**result, "score": result["score"] - (10 if "Female" in text else 0)}
        issues = fairness.check_text(text_of("sample_resume.pdf"), biased, compare_skills, OPPORTUNITIES)["issues"]
        assert [i["variant"] for i in issues] == ["Gender stated: female"]

    def test_admin_runs_the_check_and_issues_are_recorded(self, client, monkeypatch):
        """Criterion 3: differences become issues for review."""
        student_resume(client)
        login(client, ADMIN)
        client.post("/admin/fairness/run")
        run = app_module.FAIRNESS_RUNS[0]
        assert len(run["rows"]) == 3 and run["passed"] == run["checks"] and FAIRNESS_ISSUES == []
        real = app_module.analyze_resume
        monkeypatch.setattr(app_module, "analyze_resume", lambda p: {**real(p), "score": len(p["contact"].get("name") or "")})
        client.post("/admin/fairness/run")
        assert FAIRNESS_ISSUES and FAIRNESS_ISSUES[0]["source"] == "Automatic fairness check"

    def test_anyone_can_report_a_concern_and_admin_reviews_it(self, client):
        resume = student_resume(client)
        client.post("/fairness/report", data={"about": "Score for sample_resume.pdf", "concern": "My React skill wasn't counted",
                                              "next": f"/resume/{resume['id']}"})
        issue = FAIRNESS_ISSUES[0]
        assert issue["status"] == "Open" and "Alex Rivera" in issue["source"]
        login(client, ADMIN)
        assert "My React skill" in client.get("/admin/fairness").data.decode()
        client.post(f"/admin/fairness/{issue['id']}/resolve", data={"resolution": "React is counted under Frameworks"})
        assert issue["status"] == "Reviewed" and issue["reviewed_by"] == "Tanvi Nakum"

    def test_no_statistical_claim(self, client):
        login(client, ADMIN)
        assert "doesn't prove fairness across groups" in html.unescape(client.get("/admin/fairness").data.decode())
