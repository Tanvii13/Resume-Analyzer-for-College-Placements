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


def find_resume(resume_id):
    """Look only inside the logged-in user's own resumes, so nobody can open someone else's."""
    for r in RESUMES.get(session["user_email"], []):
        if r["id"] == resume_id:
            return r
    return None


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


@app.context_processor
def inject_globals():
    """Variables every template can use."""
    return {"user": current_user(), "roles": ROLES, "max_mb": MAX_FILE_SIZE // (1024 * 1024)}


# ---------------------------------------------------------------------------
# 4. Routes
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return redirect(url_for("dashboard" if current_user() else "login"))


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
            return render_template("login.html", error="Invalid email or password. Please try again.",
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
    resumes = RESUMES.get(session["user_email"], [])
    latest = next((r for r in resumes if r["status"] == "Parsed"), None)
    return render_template("dashboard.html", resumes=resumes, latest=latest)


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


@app.route("/resume/<resume_id>")
@login_required
def view_resume(resume_id):
    resume = find_resume(resume_id)
    if resume is None or resume["status"] != "Parsed":
        abort(404)
    return render_template("resume.html", resume=resume, p=resume["parsed"])


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


if __name__ == "__main__":
    app.run(debug=True)
