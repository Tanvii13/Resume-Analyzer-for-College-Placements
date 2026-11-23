"""
Resume Analyzer for College Placements — Sprint 1
IT314 Software Engineering · Group 26

EPIC 1: User Access & Resume Upload
  US-01  User login and account access   -> /register, /login, /logout
  US-02  Upload resume                    -> /upload
  US-03  Parse uploaded resume            -> resume_parser.py, /resume/<id>
  US-04  Handle invalid resume            -> ResumeParseError + error panel + Retry

Sprint 6 — EPIC 6: Security, Privacy & Responsible Use (FR-15, NFR-03, NFR-07, NFR-09, DR-06–DR-09)
  US-16  Manage role-based access          -> PERMISSIONS, permission_required, /admin/access
  US-17  Protect student resume data       -> consent, /privacy, access log, data download, retention, /admin/data
  US-18  Automated results are supporting  -> _assist_note.html, officer review (human decision)
  US-19  Fairness of scoring and matching  -> fairness.py, /admin/fairness, "Report a concern"

How this file is organised:
  1. App setup and configuration
  2. Temporary in-memory storage (the database comes in a later sprint)
  3. Helpers (login_required, student_required)
  4. Routes
"""

import json
import os
import re
import secrets
import uuid
from datetime import datetime, timedelta
from functools import wraps

from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, abort,
)
from markupsafe import Markup
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from resume_parser import validate_file, parse_resume, ResumeParseError, MAX_FILE_SIZE
import fairness


# ---------------------------------------------------------------------------
# 1. App setup
# ---------------------------------------------------------------------------
app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get("SECRET_KEY", "dev-only-change-me"),  # signs the session cookie
    SESSION_COOKIE_HTTPONLY=True,       # JavaScript can't read the session cookie
    SESSION_COOKIE_SAMESITE="Lax",      # basic protection against cross-site requests
    PERMANENT_SESSION_LIFETIME=timedelta(days=7),  # "Remember this device"
    UPLOAD_FOLDER=os.path.join(app.root_path, "uploads"),  # private, not inside /static
    MAX_CONTENT_LENGTH=MAX_FILE_SIZE + 512 * 1024,  # Flask rejects anything far bigger
    # Sprint 6
    SESSION_COOKIE_SECURE=os.environ.get("HTTPS", "0") == "1",   # set HTTPS=1 when deployed with HTTPS
    IDLE_TIMEOUT=timedelta(minutes=30),     # without "Remember this device": log out after 30 idle minutes
    CSRF_ENABLED=True,                      # every form must send back this session's secret token
    RETENTION_DAYS=int(os.environ.get("RETENTION_DAYS", "365")),  # uploads older than this are deleted
)
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

ROLES = {"student": "Student", "officer": "Placement Officer", "admin": "Admin"}


# ---------------------------------------------------------------------------
# 2. Temporary in-memory storage
#    Data resets when the server restarts. Sprint 2 replaces this with a database.
# ---------------------------------------------------------------------------
# Starting staff accounts (sign-up only creates students). Students register themselves.
USERS = {
    "officer@dau.ac.in": {
        "name": "Priya Shah",
        "email": "officer@dau.ac.in",
        "password_hash": generate_password_hash("Password@123"),
        "role": "officer",
    },
    "admin@dau.ac.in": {                       # Sprint 6 (US-16): the system administrator
        "name": "Tanvi Nakum",
        "email": "admin@dau.ac.in",
        "password_hash": generate_password_hash("Password@123"),
        "role": "admin",
    },
}

RESUMES = {}  # email -> list of resume records (newest first)

# ----- Sprint 6 storage -----
ACCESS_LOG = []      # US-17: every time staff open a student's analysis (shown to that student)
AUDIT_LOG = []       # US-16/17: admin actions (role changes, account status, data deletion)
REVIEWS = {}         # US-18: resume id -> the officer's own review (the human decision)
FAIRNESS_ISSUES = [] # US-19: differences found by the check, and concerns people report
FAIRNESS_RUNS = []   # US-19: past fairness check results, newest first
LOGIN_FAILS = {}     # US-16: email -> times of recent wrong passwords
LAST_PURGE = {"at": datetime.min}

# ---------------------------------------------------------------------------
# US-16: who may do what. One table, used by the code (permission_required), shown on the
# admin's Access page, and checked by tests/test_sprint6.py for every role.
# ---------------------------------------------------------------------------
PERMISSIONS = {
    "upload_resume":   ("Upload resumes and see their own analysis",   {"student"}),
    "job_match":       ("Compare their resume with jobs",              {"student"}),
    "view_reports":    ("See the placement dashboard and reports",     {"officer", "admin"}),
    "view_students":   ("See students' resume analysis",               {"officer", "admin"}),
    "review_students": ("Record their own review of a student",        {"officer", "admin"}),
    "manage_access":   ("Change roles and turn accounts on or off",    {"admin"}),
    "review_fairness": ("Run the fairness check and review issues",    {"admin"}),
    "manage_data":     ("See the access log and delete expired data",  {"admin"}),
}

LOGIN_LIMIT, LOGIN_WINDOW = 5, timedelta(minutes=10)   # 5 wrong passwords -> wait 10 minutes

# US-18: the human decision options. None of them is "reject": the tool never decides.
REVIEW_OPTIONS = ["Not reviewed yet", "Ready for placement drives", "Needs support before drives", "Follow up with student"]

# Curated sample opportunities for the Sprint 4 prototype. Replace with a verified feed later.
OPPORTUNITIES = [
    {"id": "intern-python", "title": "Software Engineering Intern", "company": "Campus Technology Lab", "type": "Internship", "location": "Hybrid · Ahmedabad", "description": "Build Python services and REST APIs. Work with SQL, Git, testing, and a small collaborative team. JavaScript experience is a plus."},
    {"id": "analyst-data", "title": "Junior Data Analyst", "company": "Student Analytics Co.", "type": "Full-time", "location": "On-site · Ahmedabad", "description": "Use Python, SQL, pandas, Excel, and Power BI to clean data and communicate insights. Strong problem solving and teamwork required."},
    {"id": "frontend-intern", "title": "Frontend Developer Intern", "company": "BrightWeb Studio", "type": "Internship", "location": "Remote · India", "description": "Create accessible web interfaces using JavaScript, TypeScript, React, HTML, CSS, and Git. Collaborate with designers and backend engineers."},
]


# ---------------------------------------------------------------------------
# 3. Helpers
# ---------------------------------------------------------------------------
def current_user():
    return USERS.get(session.get("user_email"))


def login_required(view):
    """Only logged-in users may open this page (US-01)."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if current_user() is None:
            flash("Please log in to continue.", "error")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def can(user, permission):
    """US-16: True if this user's role has this permission (see PERMISSIONS)."""
    return user is not None and user.get("active", True) and user["role"] in PERMISSIONS[permission][1]


def permission_required(permission):
    """US-16: checked on the server for every request, not just hidden in the menus."""
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if current_user() is None:
                flash("Please log in to continue.", "error")
                return redirect(url_for("login"))
            if not can(current_user(), permission):
                abort(403)
            return view(*args, **kwargs)
        return wrapped
    return decorator


# The Sprint 1–5 names, now backed by the permissions table
student_required = permission_required("upload_resume")
staff_required = permission_required("view_students")


def audit(action, detail=""):
    """US-16/17: record an admin action. Names only, never resume content."""
    user = current_user()
    AUDIT_LOG.insert(0, {"when": datetime.now().strftime("%b %d, %Y · %H:%M"),
                         "who": user["name"] if user else "System", "action": action, "detail": detail})
    del AUDIT_LOG[500:]


def log_access(student, resume):
    """US-17: when staff open a student's analysis, record who, whose and when (shown to the student)."""
    viewer = current_user()
    ACCESS_LOG.insert(0, {"when": datetime.now().strftime("%b %d, %Y · %H:%M"), "who": viewer["name"],
                          "role": ROLES[viewer["role"]], "student": student["email"],
                          "student_name": student["name"], "file": resume["filename"]})
    del ACCESS_LOG[2000:]


def purge_expired():
    """US-17: delete uploads (file and analysis) older than RETENTION_DAYS. Returns how many."""
    cutoff = datetime.now() - timedelta(days=app.config["RETENTION_DAYS"])
    removed = 0
    for resumes in RESUMES.values():
        old = [r for r in resumes if datetime.fromisoformat(r.get("uploaded_at", datetime.now().isoformat())) < cutoff]
        for r in old:
            delete_resume_record(resumes, r)
        removed += len(old)
    return removed


def delete_resume_record(resumes, resume):
    """Remove one resume: its stored file, its record and its review."""
    if resume.get("stored_name"):
        path = os.path.join(app.config["UPLOAD_FOLDER"], resume["stored_name"])
        if os.path.exists(path):
            os.remove(path)
    resumes.remove(resume)
    REVIEWS.pop(resume["id"], None)


def csrf_token():
    """US-16: a secret for this session. Forms send it back, so other websites can't post as you."""
    if "csrf" not in session:
        session["csrf"] = secrets.token_urlsafe(32)
    return session["csrf"]


def find_resume(resume_id):
    """Look only inside the logged-in user's own resumes, so nobody can open someone else's."""
    for r in RESUMES.get(session["user_email"], []):
        if r["id"] == resume_id:
            return r
    return None


SKILL_KEYWORDS = {
    "Programming": ["python", "java", "javascript", "typescript", "c++", "c#", "go", "sql", "html", "css"],
    "Frameworks & tools": ["react", "angular", "vue", "node.js", "flask", "django", "git", "docker", "aws", "figma"],
    "Data & AI": ["machine learning", "deep learning", "pandas", "numpy", "tensorflow", "pytorch", "power bi", "tableau", "excel"],
    "Professional": ["communication", "leadership", "teamwork", "problem solving", "project management"],
}


def analyze_resume(parsed):
    """Create a transparent, rule-based Sprint 2 snapshot from parsed resume text."""
    content = "\n".join(section["content"] for section in parsed["sections"]).lower()
    groups = []
    skills = []
    for category, terms in SKILL_KEYWORDS.items():
        found = [term for term in terms if re.search(r"(?<![a-z0-9])" + re.escape(term) + r"(?![a-z0-9])", content)]
        if found:
            groups.append({"name": category, "skills": found})
            skills.extend(found)

    section_keys = {section["key"] for section in parsed["sections"]}
    criteria = [
        ("Core resume sections", "education" in section_keys and "skills" in section_keys, "Education and skills sections are present." if {"education", "skills"} <= section_keys else "Add clear Education and Skills sections."),
        ("Projects", "projects" in section_keys, "Projects section gives recruiters evidence of applied work." if "projects" in section_keys else "Add a Projects section with your role and outcomes."),
        ("Experience", "experience" in section_keys, "Experience or internship history is included." if "experience" in section_keys else "Add relevant work, internship, volunteering, or practical experience."),
        ("Contact details", bool(parsed["contact"].get("email") and parsed["contact"].get("phone")), "Email and phone are available." if parsed["contact"].get("email") and parsed["contact"].get("phone") else "Make sure your email and phone number are easy to find."),
        ("Relevant skills", len(skills) >= 3, f"{len(skills)} recognizable skills were found." if skills else "Add a clearly labeled Skills section with specific tools and technologies."),
    ]
    score = round(sum(20 for _, passed, _ in criteria if passed))
    summary = "Strong foundations" if score >= 80 else "Good starting point" if score >= 60 else "Several areas to strengthen"
    return {
        "skills": groups,
        "skill_count": len(skills),
        "criteria": [{"title": title, "passed": passed, "detail": detail} for title, passed, detail in criteria],
        "score": score,
        "summary": summary,
        "method_note": "A preliminary checklist based on readable resume text and section headings; it is not a hiring decision.",
    }


def upload_failed(original_name, error):
    """US-04: record the failed attempt and show the reason with a Retry option."""
    RESUMES.setdefault(session["user_email"], []).insert(0, {
        "id": uuid.uuid4().hex[:10],
        "filename": original_name or "Unnamed file",
        "size": None,
        "uploaded": datetime.now().strftime("%b %d, %Y · %H:%M"),
        "uploaded_at": datetime.now().isoformat(),
        "status": "Failed",
        "error_code": error.code,
        "error_message": error.message,
        "parsed": None,
    })
    flash(f"{error.code}|{error.message}", "upload-error")
    return redirect(url_for("dashboard") + "#upload")


@app.url_defaults
def add_static_version(endpoint, values):
    """Add ?v=<file timestamp> to CSS/JS links, so the browser always loads the latest version
    after a file changes instead of showing an old cached copy."""
    if endpoint == "static" and "filename" in values:
        path = os.path.join(app.static_folder, values["filename"])
        if os.path.exists(path):
            values["v"] = int(os.path.getmtime(path))


@app.context_processor
def inject_globals():
    """Variables every template can use."""
    return {"user": current_user(), "roles": ROLES, "max_mb": MAX_FILE_SIZE // (1024 * 1024),
            "can": lambda permission: can(current_user(), permission),
            "csrf_field": lambda: Markup(f'<input type="hidden" name="csrf_token" value="{csrf_token()}">'),
            "retention_days": app.config["RETENTION_DAYS"]}


@app.before_request
def security_checks():
    """Sprint 6: runs before every request.
    1. Delete uploads past the retention period (checked at most once an hour).       US-17
    2. A turned-off account, or 30 idle minutes without "Remember", ends the session.  US-16
    3. A form sent without this session's token is refused (CSRF).                     US-16"""
    if datetime.now() - LAST_PURGE["at"] > timedelta(hours=1):
        LAST_PURGE["at"] = datetime.now()
        purge_expired()
    user = current_user()
    if user is not None:
        last = session.get("last_seen")
        idle = not session.permanent and last and \
            datetime.now() - datetime.fromisoformat(last) > app.config["IDLE_TIMEOUT"]
        if not user.get("active", True) or idle:
            session.clear()
            flash("Your account has been turned off by the admin." if not user.get("active", True)
                  else "You were logged out after 30 minutes without activity. Please log in again.", "error")
            return redirect(url_for("login"))
        session["last_seen"] = datetime.now().isoformat(timespec="seconds")
    if request.method == "POST" and app.config["CSRF_ENABLED"]:
        sent = request.form.get("csrf_token", "")
        if not session.get("csrf") or not secrets.compare_digest(sent, session["csrf"]):
            return render_template("error.html", code=400, title="This form has expired",
                                   message="Go back, reload the page and try again."), 400


@app.after_request
def security_headers(response):
    """Sprint 6: browser protections on every response."""
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")              # can't be shown inside another site
    response.headers.setdefault("Referrer-Policy", "same-origin")
    response.headers.setdefault("Content-Security-Policy",
                                "frame-ancestors 'none'; object-src 'none'; base-uri 'self'; form-action 'self'")
    if current_user() is not None:
        response.headers["Cache-Control"] = "no-store"   # after logout, Back can't show someone's results
    return response


# ---------------------------------------------------------------------------
# 4. Routes
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    """Public landing page. Its buttons lead to sign-up, or to the dashboard if logged in."""
    return render_template("landing.html")


# ----- US-01: account access ------------------------------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")

        error = None
        if not name or not email or not password:
            error = "All fields are required."
        elif "@" not in email or "." not in email.split("@")[-1]:
            error = "Please enter a valid university email."
        elif len(password) < 8:
            error = "Password must be at least 8 characters."
        elif password != confirm:
            error = "Passwords do not match."
        elif email in USERS:
            error = "An account with this email already exists."

        if error:
            return render_template("register.html", error=error, name=name, email=email), 400

        # New sign-ups are always students. Officer/admin accounts are created by an admin.
        USERS[email] = {
            "name": name,
            "email": email,
            "password_hash": generate_password_hash(password),  # never store plain passwords
            "role": "student",
        }
        flash("Account created. Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        role = request.form.get("role", "student")

        # US-16: after 5 wrong passwords, this account waits 10 minutes
        cutoff = datetime.now() - LOGIN_WINDOW
        fails = LOGIN_FAILS[email] = [t for t in LOGIN_FAILS.get(email, []) if t > cutoff]
        if len(fails) >= LOGIN_LIMIT:
            wait = int((fails[0] + LOGIN_WINDOW - datetime.now()).total_seconds() // 60) + 1
            return render_template("login.html", error=f"Too many wrong passwords. Try again in {wait} minute{'s' if wait != 1 else ''}.",
                                   error_code="ERR_AUTH_429", email=email, role=role), 429

        user = USERS.get(email)
        # Same message for wrong email or wrong password, so attackers can't tell which accounts exist
        if not user or not check_password_hash(user["password_hash"], password):
            fails.append(datetime.now())
            return render_template("login.html", error="That email and password don't match. Check both and try again.",
                                   error_code="ERR_AUTH_401", email=email, role=role), 401
        if user["role"] != role:
            return render_template("login.html",
                                   error=f"This account isn't registered as {ROLES.get(role, role)}. "
                                         f"Choose the {ROLES[user['role']]} tab.",
                                   error_code="ERR_AUTH_403", email=email, role=role), 403

        if not user.get("active", True):    # US-16: the admin turned this account off
            return render_template("login.html", error="This account has been turned off. Contact the placement cell.",
                                   error_code="ERR_AUTH_403", email=email, role=role), 403

        LOGIN_FAILS.pop(email, None)
        session.clear()                     # fresh session after login
        session["user_email"] = email
        session.permanent = bool(request.form.get("remember"))
        flash(f"Welcome back, {user['name'].split()[0]}!", "success")
        return redirect(url_for("dashboard"))

    return render_template("login.html", role="student")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    user = current_user()

    if can(user, "view_reports"):
        return redirect(url_for("staff_dashboard"))

    resumes = RESUMES.get(session["user_email"], [])
    latest = next(
        (r for r in resumes if r["status"] == "Parsed"),
        None
    )

    return render_template(
        "dashboard.html",
        resumes=resumes,
        latest=latest,
        views=[a for a in ACCESS_LOG if a["student"] == user["email"]][:10],   # Sprint 6, US-17
    )


# ----- US-02, US-03, US-04: upload, parse, handle invalid files -------------
@app.route("/upload", methods=["POST"])
@login_required
@student_required
def upload():
    user = current_user()
    if not user.get("consent_at"):          # Sprint 6, US-17: agree once before the first upload
        if request.form.get("consent") != "on":
            name = secure_filename(request.files["resume"].filename) if request.files.get("resume") else ""
            return upload_failed(name, ResumeParseError(
                "ERR_CONSENT_REQUIRED", "Please tick the box to agree to how your resume is used, then upload again."))
        user["consent_at"] = datetime.now().strftime("%b %d, %Y · %H:%M")
    file = request.files.get("resume")
    original = secure_filename(file.filename) if file and file.filename else ""
    data = file.read() if file else b""

    # Step 1 — validate (type, size, empty, real file signature)
    try:
        ext = validate_file(original, data)
    except ResumeParseError as e:
        return upload_failed(original, e)

    # Step 2 — save privately under a random name
    stored_name = f"{uuid.uuid4().hex}.{ext}"
    path = os.path.join(app.config["UPLOAD_FOLDER"], stored_name)
    with open(path, "wb") as f:
        f.write(data)

    # Step 3 — parse into sections
    try:
        parsed = parse_resume(path, ext)
    except ResumeParseError as e:
        os.remove(path)          # don't keep files we couldn't read
        return upload_failed(original, e)

    resume = {
        "id": uuid.uuid4().hex[:10],
        "filename": original,
        "stored_name": stored_name,
        "size": f"{max(1, len(data) // 1024)} KB",
        "uploaded": datetime.now().strftime("%b %d, %Y · %H:%M"),
        "uploaded_at": datetime.now().isoformat(),
        "status": "Parsed",
        "parsed": parsed,
    }
    RESUMES.setdefault(session["user_email"], []).insert(0, resume)
    flash("Resume uploaded and parsed successfully.", "success")
    return redirect(url_for("view_resume", resume_id=resume["id"]))


@app.route("/matching", methods=["GET", "POST"])
@login_required
@permission_required("job_match")
def matching():
    resumes = [r for r in RESUMES.get(session["user_email"], []) if r["status"] == "Parsed"]
    selected_id = request.values.get("resume_id", "")
    resume = next((r for r in resumes if r["id"] == selected_id), resumes[0] if resumes else None)
    result = None
    job_text = request.form.get("job_description", "").strip() if request.method == "POST" else ""
    if request.method == "POST":
        if not resume:
            flash("Upload a readable resume before comparing it with a role.", "error")
        elif not job_text:
            flash("Paste a job description to see your skill match.", "error")
        else:
            result = compare_skills(resume, job_text)
    opportunities = []
    if resume:
        for job in OPPORTUNITIES:
            match = compare_skills(resume, job["description"])
            opportunities.append({**job, **match})
        opportunities.sort(key=lambda item: (-item["match_percent"], item["title"]))
    return render_template("matching.html", resumes=resumes, resume=resume, result=result,
                           job_text=job_text, opportunities=opportunities)


def compare_skills(resume, description):
    """Compare transparent keyword sets from the selected parsed resume and role text."""
    parsed_text = "\n".join(section["content"] for section in resume["parsed"]["sections"]).lower()
    available = [term for terms in SKILL_KEYWORDS.values() for term in terms]
    required = [term for term in available if re.search(r"(?<![a-z0-9])" + re.escape(term) + r"(?![a-z0-9])", description.lower())]
    present = [term for term in required if re.search(r"(?<![a-z0-9])" + re.escape(term) + r"(?![a-z0-9])", parsed_text)]
    missing = [term for term in required if term not in present]
    return {"matched_skills": present, "missing_skills": missing, "required_skills": required,
            "match_percent": round(100 * len(present) / len(required)) if required else 0}


@app.route("/resume/<resume_id>")
@login_required
def view_resume(resume_id):
    resume = find_resume(resume_id)
    if resume is None or resume["status"] != "Parsed":
        abort(404)
    analysis = analyze_resume(resume["parsed"])
    return render_template("resume.html", resume=resume, p=resume["parsed"], analysis=analysis,
                           review=REVIEWS.get(resume["id"]))
# ---------------------------------------------------------
# Sprint 5 - US-15: Placement Dashboard and Reports
# ---------------------------------------------------------

@app.route("/staff/dashboard")
@permission_required("view_reports")
def staff_dashboard():
    students = [
        student for student in USERS.values()
        if student["role"] == "student"
    ]

    total_resumes = 0
    students_with_resumes = 0
    scores = []
    skill_counts = {}
    improvement_counts = {}

    for student in students:
        email = student["email"]

        parsed_resumes = [
            resume for resume in RESUMES.get(email, [])
            if resume["status"] == "Parsed"
            and resume.get("parsed") is not None
        ]

        total_resumes += len(parsed_resumes)

        if not parsed_resumes:
            continue

        students_with_resumes += 1

        # Use the student's latest successfully parsed resume
        latest = parsed_resumes[0]
        analysis = analyze_resume(latest["parsed"])

        scores.append(analysis["score"])

        for group in analysis["skills"]:
            for skill in set(group["skills"]):
                skill_counts[skill] = skill_counts.get(skill, 0) + 1

        for criterion in analysis["criteria"]:
            if not criterion["passed"]:
                area = criterion["title"]
                improvement_counts[area] = (
                    improvement_counts.get(area, 0) + 1
                )

    metrics = {
        "total_students": len(students),
        "students_with_resumes": students_with_resumes,
        "total_resumes": total_resumes,
        "average_score": (
            round(sum(scores) / len(scores), 1)
            if scores else None
        ),
    }

    common_skills = sorted(
        skill_counts.items(),
        key=lambda item: (-item[1], item[0])
    )[:10]

    improvement_areas = sorted(
        improvement_counts.items(),
        key=lambda item: (-item[1], item[0])
    )[:10]

    return render_template(
        "staff_dashboard.html",
        metrics=metrics,
        common_skills=common_skills,
        improvement_areas=improvement_areas
    )

@app.route("/staff/students")
@staff_required
def staff_students():
    students = []

    for email, student in USERS.items():
        if student["role"] != "student":
            continue

        parsed_resumes = [
            r for r in RESUMES.get(email, [])
            if r["status"] == "Parsed"
            and r.get("parsed") is not None
        ]

        latest = parsed_resumes[0] if parsed_resumes else None

        students.append({
            "name": student["name"],
            "email": email,
            "resume_count": len(parsed_resumes),
            "latest": latest,
            "score": analyze_resume(latest["parsed"])["score"]
                     if latest else None,
            "review": REVIEWS.get(latest["id"]) if latest else None,   # Sprint 6, US-18
        })

    students.sort(key=lambda s: s["name"].lower())

    return render_template(
        "staff_students.html",
        students=students
    )


@app.route("/staff/students/<student_email>/resumes/<resume_id>")
@staff_required
def staff_resume_analysis(student_email, resume_id):
    student = USERS.get(student_email)

    if student is None or student["role"] != "student":
        abort(404)

    resume = next(
        (
            r for r in RESUMES.get(student_email, [])
            if r["id"] == resume_id
            and r["status"] == "Parsed"
            and r.get("parsed") is not None
        ),
        None
    )

    if resume is None:
        abort(404)

    log_access(student, resume)            # Sprint 6, US-17: the student can see this view
    return render_template(
        "staff_analysis.html",
        student=student,
        resume=resume,
        analysis=analyze_resume(resume["parsed"]),
        review=REVIEWS.get(resume["id"]),
        review_options=REVIEW_OPTIONS,
    )


# ===========================================================================
# Sprint 6 — Security, Privacy & Responsible Use
# ===========================================================================

# ----- US-18: the decision stays with a person ------------------------------
@app.route("/staff/students/<student_email>/resumes/<resume_id>/review", methods=["POST"])
@permission_required("review_students")
def save_review(student_email, resume_id):
    """The officer records their own judgement. The score is shown next to it, never instead of it."""
    resume = next((r for r in RESUMES.get(student_email, []) if r["id"] == resume_id), None)
    if resume is None:
        abort(404)
    decision = request.form.get("decision", "")
    if decision not in REVIEW_OPTIONS:
        abort(400)
    REVIEWS[resume_id] = {"decision": decision, "note": request.form.get("note", "").strip()[:500],
                          "by": current_user()["name"], "when": datetime.now().strftime("%b %d, %Y · %H:%M")}
    flash("Your review was saved.", "success")
    return redirect(url_for("staff_resume_analysis", student_email=student_email, resume_id=resume_id))


# ----- US-17: the student's own data ---------------------------------------
@app.route("/resume/<resume_id>/delete", methods=["POST"])
@login_required
def delete_resume(resume_id):
    resume = find_resume(resume_id)
    if resume is None:
        abort(404)
    delete_resume_record(RESUMES[session["user_email"]], resume)
    flash("The resume and its analysis were deleted.", "success")
    return redirect(url_for("dashboard") + "#resumes")


@app.route("/my-data.json")
@login_required
def download_my_data():
    """Everything stored about you, in one file (never your password)."""
    user = current_user()
    data = {
        "account": {k: user.get(k) for k in ("name", "email", "role", "consent_at")},
        "resumes": [{"filename": r["filename"], "uploaded": r["uploaded"], "status": r["status"],
                     "sections": [s["title"] for s in r["parsed"]["sections"]] if r.get("parsed") else [],
                     "contact": r["parsed"]["contact"] if r.get("parsed") else None,
                     "review": REVIEWS.get(r["id"])} for r in RESUMES.get(user["email"], [])],
        "viewed_by_staff": [{k: a[k] for k in ("when", "who", "role", "file")}
                            for a in ACCESS_LOG if a["student"] == user["email"]],
    }
    response = app.response_class(json.dumps(data, indent=2, ensure_ascii=False), mimetype="application/json")
    response.headers["Content-Disposition"] = 'attachment; filename="my_resume_data.json"'
    return response


@app.route("/privacy")
def privacy():
    """Public privacy notice: what is stored, why, who sees it, how long, and how results are made."""
    return render_template("privacy.html", permissions=PERMISSIONS, roles=ROLES,
                           scoring=fairness.SCORING_FACTORS, matching_factors=fairness.MATCHING_FACTORS,
                           not_used=fairness.NOT_USED)


# ----- US-19: anyone can report a result they think is unfair ---------------
@app.route("/fairness/report", methods=["POST"])
@login_required
def report_concern():
    concern = request.form.get("concern", "").strip()[:600]
    if not concern:
        flash("Please describe what looks unfair.", "error")
    else:
        user = current_user()
        FAIRNESS_ISSUES.insert(0, {"id": uuid.uuid4().hex[:8], "when": datetime.now().strftime("%b %d, %Y · %H:%M"),
                                   "source": f"Reported by {user['name']} ({ROLES[user['role']]})",
                                   "about": request.form.get("about", "")[:120], "detail": concern,
                                   "status": "Open", "resolution": ""})
        flash("Thanks. Your concern was recorded for the admin to review.", "success")
    return redirect(request.form.get("next") if (request.form.get("next") or "").startswith("/") else url_for("dashboard"))


# ----- Admin pages ------------------------------------------------------------
@app.route("/admin/access")
@permission_required("manage_access")
def admin_access():
    """US-16: every account, its role and status, and what each role may do."""
    users = sorted(USERS.values(), key=lambda u: (u["role"] != "admin", u["role"] != "officer", u["name"].lower()))
    return render_template("admin_access.html", users=users, permissions=PERMISSIONS,
                           audit_log=[a for a in AUDIT_LOG if a["action"].startswith(("Changed", "Turned"))][:10])


@app.route("/admin/access/<path:email>", methods=["POST"])
@permission_required("manage_access")
def admin_update_user(email):
    """US-16 criterion 3: a change applies on the person's very next click (roles are read on every request)."""
    target = USERS.get(email)
    if target is None:
        abort(404)
    if email == session["user_email"]:
        flash("You can't change your own access. Ask another admin.", "error")
        return redirect(url_for("admin_access"))
    role, active = request.form.get("role", target["role"]), request.form.get("active", "on") == "on"
    if role not in ROLES:
        abort(400)
    admins = [u for u in USERS.values() if u["role"] == "admin" and u.get("active", True)]
    if target in admins and (role != "admin" or not active) and len(admins) == 1:
        flash("There must always be at least one active admin.", "error")
        return redirect(url_for("admin_access"))
    if role != target["role"]:
        audit("Changed role", f"{target['name']}: {ROLES[target['role']]} → {ROLES[role]}")
        target["role"] = role
    if active != target.get("active", True):
        audit("Turned account " + ("on" if active else "off"), target["name"])
        target["active"] = active
    flash(f"Access for {target['name']} was updated.", "success")
    return redirect(url_for("admin_access"))


@app.route("/admin/fairness")
@permission_required("review_fairness")
def admin_fairness():
    """US-19: the factors, the check, and every issue recorded for review."""
    return render_template("admin_fairness.html", scoring=fairness.SCORING_FACTORS,
                           matching_factors=fairness.MATCHING_FACTORS, not_used=fairness.NOT_USED,
                           run=FAIRNESS_RUNS[0] if FAIRNESS_RUNS else None, issues=FAIRNESS_ISSUES)


@app.route("/admin/fairness/run", methods=["POST"])
@permission_required("review_fairness")
def admin_run_fairness():
    """Re-run every analysed resume (and the sample resumes) with only personal details changed."""
    texts = []
    for name in ("sample_resume.pdf", "sample_resume.docx"):
        path = os.path.join(app.root_path, "sample_resumes", name)
        if os.path.exists(path):
            texts.append((name, "Test resume", parse_resume(path, name.rsplit(".", 1)[1])["text"]))
    for email, resumes in RESUMES.items():
        for r in resumes:
            if r["status"] == "Parsed" and r["parsed"].get("text"):
                texts.append((r["filename"], USERS[email]["name"] if email in USERS else email, r["parsed"]["text"]))
    rows = []
    for filename, owner, text in texts:
        result = fairness.check_text(text, analyze_resume, compare_skills, OPPORTUNITIES)
        rows.append({"file": filename, "owner": owner, **result})
        for issue in result["issues"]:          # criterion 3: recorded for review
            FAIRNESS_ISSUES.insert(0, {"id": uuid.uuid4().hex[:8], "when": datetime.now().strftime("%b %d, %Y · %H:%M"),
                                       "source": "Automatic fairness check", "about": f"{filename} ({owner})",
                                       "detail": f"“{issue['variant']}” changed {issue['field']}: {issue['before']} → {issue['after']}",
                                       "status": "Open", "resolution": ""})
    run = {"when": datetime.now().strftime("%b %d, %Y · %H:%M"), "rows": rows,
           "checks": sum(r["checks"] for r in rows), "passed": sum(r["passed"] for r in rows)}
    FAIRNESS_RUNS.insert(0, run)
    audit("Ran the fairness check", f"{run['passed']} of {run['checks']} checks passed")
    return redirect(url_for("admin_fairness") + "#check")


@app.route("/admin/fairness/<issue_id>/resolve", methods=["POST"])
@permission_required("review_fairness")
def admin_resolve_issue(issue_id):
    issue = next((i for i in FAIRNESS_ISSUES if i["id"] == issue_id), None)
    if issue is None:
        abort(404)
    issue.update(status="Reviewed", resolution=request.form.get("resolution", "").strip()[:500],
                 reviewed_by=current_user()["name"])
    audit("Reviewed a fairness issue", issue["about"])
    return redirect(url_for("admin_fairness") + "#issues")


@app.route("/admin/data")
@permission_required("manage_data")
def admin_data():
    """US-17: retention, who opened which student's analysis, and admin actions."""
    cutoff = datetime.now() - timedelta(days=app.config["RETENTION_DAYS"])
    uploads = [r for rs in RESUMES.values() for r in rs]
    students = [u for u in USERS.values() if u["role"] == "student"]
    return render_template("admin_data.html", uploads=len(uploads),
                           expired=sum(datetime.fromisoformat(r.get("uploaded_at", datetime.now().isoformat())) < cutoff for r in uploads),
                           consented=sum(bool(u.get("consent_at")) for u in students), students=len(students),
                           access_log=ACCESS_LOG[:50], audit_log=AUDIT_LOG[:50])


@app.route("/admin/data/purge", methods=["POST"])
@permission_required("manage_data")
def admin_purge():
    removed = purge_expired()
    audit("Deleted expired uploads", f"{removed} older than {app.config['RETENTION_DAYS']} days")
    flash(f"Deleted {removed} upload{'s' if removed != 1 else ''} past the retention period." if removed
          else "Nothing is past the retention period.", "success")
    return redirect(url_for("admin_data"))


# ----- Error pages ----------------------------------------------------------
@app.errorhandler(413)
def file_too_large(_):
    if current_user() is None:
        return redirect(url_for("login"))
    return upload_failed(None, ResumeParseError(
        "ERR_FILE_TOO_LARGE", "This file is larger than 5 MB. Please compress it and try again."))


@app.errorhandler(400)
def bad_request(_):
    return render_template("error.html", code=400, title="Something was wrong with that request",
                           message="Go back, reload the page and try again."), 400


@app.errorhandler(403)
def forbidden(_):
    return render_template("error.html", code=403, title="Access denied",
                           message="Your role doesn't have permission to do this."), 403


@app.errorhandler(404)
def not_found(_):
    return render_template("error.html", code=404, title="Page not found",
                           message="This page doesn't exist or you don't have access to it."), 404


DESIGN_VERSION = "Sprint 6 · Security, privacy & responsible use"

if __name__ == "__main__":
    # Printed once at startup so you can see exactly which copy of the project is running.
    if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        print(f"\n  Resume Analyzer · {DESIGN_VERSION}")
        print(f"  Running from: {app.root_path}")
        print("  Open http://127.0.0.1:5000  (stop with Ctrl+C)\n")
    app.run(debug=True)   # if port 5000 is busy, another copy is still running: close it first




 
