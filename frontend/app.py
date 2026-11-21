"""
Resume Analyzer for College Placements — Sprint 1
IT314 Software Engineering · Group 26

EPIC 1: User Access & Resume Upload
  US-01  User login and account access   -> /register, /login, /logout
  US-02  Upload resume                    -> /upload
  US-03  Parse uploaded resume            -> resume_parser.py, /resume/<id>
  US-04  Handle invalid resume            -> ResumeParseError + error panel + Retry

How this file is organised:
  1. App setup and configuration
  2. Temporary in-memory storage (the database comes in a later sprint)
  3. Helpers (login_required, student_required)
  4. Routes
"""

import os
import re
import uuid
from datetime import datetime, timedelta
from functools import wraps

from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, abort,
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from resume_parser import validate_file, parse_resume, ResumeParseError, MAX_FILE_SIZE


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
)
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

ROLES = {"student": "Student", "officer": "Placement Officer", "admin": "Admin"}


# ---------------------------------------------------------------------------
# 2. Temporary in-memory storage
#    Data resets when the server restarts. Sprint 2 replaces this with a database.
# ---------------------------------------------------------------------------
USERS = {
    "alex.rivera@dau.ac.in": {
        "name": "Alex Rivera",
        "email": "alex.rivera@dau.ac.in",
        "password_hash": generate_password_hash("Password@123"),
        "role": "student",
    },
    "officer@dau.ac.in": {
        "name": "Priya Shah",
        "email": "officer@dau.ac.in",
        "password_hash": generate_password_hash("Password@123"),
        "role": "officer",
    },
}

RESUMES = {}  # email -> list of resume records (newest first)

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


def student_required(view):
    """Only students may upload resumes. Checked on the server, not just hidden in the UI."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if current_user()["role"] != "student":
            abort(403)
        return view(*args, **kwargs)
    return wrapped

def staff_required(view):
    """Allow placement officers and admins to access staff pages."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = current_user()

        if user is None:
            flash("Please log in to continue.", "error")
            return redirect(url_for("login"))

        if user["role"] not in ("officer", "admin"):
            abort(403)

        return view(*args, **kwargs)

    return wrapped


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
    return {"user": current_user(), "roles": ROLES, "max_mb": MAX_FILE_SIZE // (1024 * 1024)}


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

        user = USERS.get(email)
        # Same message for wrong email or wrong password, so attackers can't tell which accounts exist
        if not user or not check_password_hash(user["password_hash"], password):
            return render_template("login.html", error="That email and password don't match. Check both and try again.",
                                   error_code="ERR_AUTH_401", email=email, role=role), 401
        if user["role"] != role:
            return render_template("login.html",
                                   error=f"This account isn't registered as {ROLES.get(role, role)}. "
                                         f"Choose the {ROLES[user['role']]} tab.",
                                   error_code="ERR_AUTH_403", email=email, role=role), 403

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

    if user["role"] in ("officer", "admin"):
        return redirect(url_for("staff_dashboard"))

    resumes = RESUMES.get(session["user_email"], [])
    latest = next(
        (r for r in resumes if r["status"] == "Parsed"),
        None
    )

    return render_template(
        "dashboard.html",
        resumes=resumes,
        latest=latest
    )


# ----- US-02, US-03, US-04: upload, parse, handle invalid files -------------
@app.route("/upload", methods=["POST"])
@login_required
@student_required
def upload():
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
        "status": "Parsed",
        "parsed": parsed,
    }
    RESUMES.setdefault(session["user_email"], []).insert(0, resume)
    flash("Resume uploaded and parsed successfully.", "success")
    return redirect(url_for("view_resume", resume_id=resume["id"]))


@app.route("/matching", methods=["GET", "POST"])
@login_required
@student_required
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
    return render_template("resume.html", resume=resume, p=resume["parsed"], analysis=analysis)
# ---------------------------------------------------------
# Sprint 5 - US-15: Placement Dashboard and Reports
# ---------------------------------------------------------

@app.route("/staff/dashboard")
@staff_required
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

    return render_template(
        "staff_analysis.html",
        student=student,
        resume=resume,
        analysis=analyze_resume(resume["parsed"])
    )


# ----- Error pages ----------------------------------------------------------
@app.errorhandler(413)
def file_too_large(_):
    if current_user() is None:
        return redirect(url_for("login"))
    return upload_failed(None, ResumeParseError(
        "ERR_FILE_TOO_LARGE", "This file is larger than 5 MB. Please compress it and try again."))


@app.errorhandler(403)
def forbidden(_):
    return render_template("error.html", code=403, title="Access denied",
                           message="Your role doesn't have permission to do this."), 403


@app.errorhandler(404)
def not_found(_):
    return render_template("error.html", code=404, title="Page not found",
                           message="This page doesn't exist or you don't have access to it."), 404


DESIGN_VERSION = "Liquid Glass design (v8, highlighter)"

if __name__ == "__main__":
    # Printed once at startup so you can see exactly which copy of the project is running.
    if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        print(f"\n  Resume Analyzer · {DESIGN_VERSION}")
        print(f"  Running from: {app.root_path}")
        print("  Open http://127.0.0.1:5000  (stop with Ctrl+C)\n")
    app.run(debug=True)   # if port 5000 is busy, another copy is still running: close it first




 
