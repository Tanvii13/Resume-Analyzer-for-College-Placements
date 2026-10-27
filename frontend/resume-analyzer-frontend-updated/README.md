# Resume Analyzer for College Placements

IT314 Software Engineering · Group 26

## Sprint 1 — User Access & Resume Upload

**EPIC 1:** User Access & Resume Upload
**Goal:** Students can securely access the system, upload their resumes, have the content processed, and get a clear explanation when a file is invalid or unreadable.
**User stories:** US-01 User login and account access · US-02 Upload resume · US-03 Parse uploaded resume · US-04 Handle invalid resume
**Requirement IDs covered:** FR-16, FR-01, NFR-01, FR-02, FR-14, NFR-06

## Run it

```bash
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000 to see the landing page, then click **Get Started** or **Log In**.

| Account | Email | Password | Role tab |
|---|---|---|---|
| Student | alex.rivera@dau.ac.in | Password@123 | Student |
| Placement officer | officer@dau.ac.in | Password@123 | Placement Officer |

## Run the tests

```bash
pytest -v
```

35 acceptance tests, grouped by user story. They use the files in `sample_resumes/`.

## Project structure

```
├── app.py                # Routes: landing, register, login, logout, dashboard, upload, view resume
├── resume_parser.py      # Validate file → extract text → split into sections
├── requirements.txt      # Python dependencies
├── pytest.ini            # Test settings (lets tests import app.py)
├── templates/            # HTML pages (Jinja2)
│   ├── base.html         # common layout every page extends (font, background, toasts)
│   ├── landing.html      # public landing page at /
│   ├── login.html        # US-01
│   ├── register.html     # US-01
│   ├── dashboard.html    # US-02 upload panel + US-04 error panel + history table
│   ├── resume.html       # US-03 parsed sections and contact details
│   ├── error.html        # 403 / 404 pages
│   └── _*.html           # small reusable pieces (logo, nav, role tabs)
├── static/
│   ├── css/style.css     # layout and components shared by every page
│   ├── css/landing.css   # landing page only
│   ├── css/liquid.css    # the Liquid Glass look, loaded last on every page
 the teal wallpaper the glass blurs and bends
# the teal wallpaper the glass blurs and bends
│   └── js/main.js        # form helpers, landing animations, glass refraction + pointer light
├── sample_resumes/       # demo files and test fixtures (see below)
└── tests/test_sprint1.py # acceptance tests, grouped by user story
```

`uploads/` is created automatically when the app starts. It holds uploaded resumes, is private (not served to the browser), and is ignored by Git.

## Traceability: user story → code → tests

| Story | What was built | Where in the code | Tests (`tests/test_sprint1.py`) |
|---|---|---|---|
| **US-01** User login and account access | Sign-up, login with role tabs, logout, protected pages, hashed passwords, generic error on wrong email/password, "Remember this device" | `app.py`: `register()`, `login()`, `logout()`, `login_required`; `login.html`, `register.html` | `TestUS01Login` (14) |
| **US-02** Upload resume | Drag-and-drop upload, PDF/DOCX only, 5 MB limit, private storage under a random file name, only students can upload | `app.py`: `upload()`, `student_required`; `resume_parser.validate_file()`; `dashboard.html` | `TestUS02Upload` (5) |
| **US-03** Parse uploaded resume | Text extraction from PDF and DOCX, section detection, contact details, missing-section warning, parsed-resume page | `resume_parser.py`: `extract_text()`, `split_sections()`, `extract_contact()`; `app.py`: `view_resume()`; `resume.html` | `TestUS03Parse` (5) |
| **US-04** Handle invalid resume | Each failure gets an error code and a plain-English reason in the upload panel; failed attempt is listed with a Retry button; unreadable files are deleted | `resume_parser.ResumeParseError`; `app.py`: `upload_failed()`; error panel in `dashboard.html` | `TestUS04Invalid` (11) |

## Invalid-file cases (US-04)

| Error code | When it happens | Message shown to the student |
|---|---|---|
| `ERR_NO_FILE` | Upload pressed with no file | Please choose a file to upload. |
| `ERR_FILE_TYPE` | Not .pdf or .docx | Not supported. Please upload a PDF or DOCX file. |
| `ERR_EMPTY_FILE` | 0-byte file | This file is empty. |
| `ERR_FILE_TOO_LARGE` | Over 5 MB | Larger than 5 MB. Please compress it and try again. |
| `ERR_FILE_CORRUPT` | Renamed file (content doesn't match extension) | Content is not a valid PDF/DOCX. It may be corrupted or renamed. |
| `ERR_PASSWORD_PROTECTED` | Encrypted PDF | Please remove the password and upload again. |
| `ERR_UNREADABLE` | Damaged file the library can't open | We couldn't read this file. Try exporting it again. |
| `ERR_NO_TEXT` | Scanned/image-only resume | No readable text was found. Upload a text-based PDF or DOCX. |

## Sample resumes

Used by the tests and for the live demo. Do not delete.

| File | Expected result |
|---|---|
| `sample_resume.pdf` | Parsed: 6 sections, contact details found |
| `sample_resume.docx` | Parsed: same content as the PDF |
| `scanned_resume.pdf` | `ERR_NO_TEXT` (image only, no text layer) |
| `fake_resume.pdf` | `ERR_FILE_CORRUPT` (text file renamed to .pdf) |
| `protected_resume.pdf` | `ERR_PASSWORD_PROTECTED` |

## Demo script (≈3 minutes)

1. Open `/dashboard` without logging in → redirected to login (**US-01**).
2. Log in with a wrong password → "Invalid email or password" (**US-01**).
3. Log in as `alex.rivera@dau.ac.in` / `Password@123`.
4. Upload `sample_resumes/scanned_resume.pdf` → "No readable text" error with Retry (**US-04**).
5. Upload `sample_resumes/fake_resume.pdf` → "corrupted or renamed" error (**US-04**).
6. Click Retry, upload `sample_resumes/sample_resume.pdf` (**US-02**) → parsed sections and contact details (**US-03**).
7. Log out (**US-01**).

## How it works (viva notes)

**Flask and templates**
- Flask is a Python web framework. Each `@app.route` function handles one URL and returns a page.
- Jinja2 templates put Python data into HTML: `{{ user.name }}`, `{% for r in resumes %}`.
- Every page `extends "base.html"`, so the shared layout is written once.

**US-01 — Login**
- After login the email is stored in `session`, a cookie signed with `SECRET_KEY` so users can't edit it.
- `@login_required` is a decorator that redirects to the login page if no one is logged in.
- Passwords are stored as hashes (`generate_password_hash`), never as plain text.
- Wrong email and wrong password give the same message so attackers can't find out which accounts exist.
- Sign-up always creates a student. Officer and admin accounts would be created by the placement cell.

**US-02 — Upload**
- `@student_required` blocks other roles on the server (hiding a button isn't security).
- The file is saved with a random UUID name in `uploads/`, which is not a public folder.

**US-03 — Parsing** (`resume_parser.py`)
1. `validate_file()` checks extension, size, empty file, and the file's first bytes (a real PDF starts with `%PDF-`, a DOCX with `PK`), which catches renamed files.
2. `extract_text()` uses `pypdf` for PDF and `python-docx` for DOCX.
3. `split_sections()` goes line by line. A short line matching a known heading (e.g. "Technical Skills") starts a new section; the following lines belong to it.
4. `extract_contact()` uses regular expressions to find email, phone and LinkedIn/GitHub links.

**US-04 — Invalid files**
- Any problem raises `ResumeParseError(code, message)`.
- `upload_failed()` records the attempt as Failed, deletes the file, and flashes the message, which the dashboard shows with a Retry button.

**Design language: Liquid Glass (like iOS)**
- **The material** (`liquid.css`): every surface is frosted glass over a deep night background (blue and teal glows, faint dot grid) — `backdrop-filter: blur() saturate()`, a faint white tint, a bright **specular rim** where light hits the top-left edge, and a thin **rainbow edge** like light through a prism.
- **Refraction:** on Chrome, Edge, Opera and Brave, the nav bar, the phone tab bar, the sign-in sheet and notifications bend the wallpaper at their edges, like a lens. `main.js` draws a small *displacement map* for each one (red/green pixels = how far to shift the picture behind) and the browser applies it with an SVG `feDisplacementMap` inside `backdrop-filter`. Safari and Firefox don't support that yet, so they show the same frosted glass without bending. Idea from the MIT-licensed [GlassiFy](https://github.com/Saviru/GlassiFy) and [nopde/liquid-glass](https://github.com/nopde/liquid-glass) projects (found via [github.com/topics/liquid-glass-effect](https://github.com/topics/liquid-glass-effect)); re-implemented here, no code copied.
- **Motion:** buttons and cards use a real spring curve (CSS `linear()` easing) so they overshoot slightly and settle; a soft light follows the pointer across glass; the role switcher's lens stretches while it slides; sheets float in with a blur-to-sharp entrance.
- **Font:** San Francisco on Apple devices (the system font), Inter elsewhere. 17px body text, Apple's type scale.
- **Components:** a bright milky-glass primary button with dark text (like iOS "Done"), clear-glass secondary buttons, recessed glass text fields, glass icon tiles, a segmented control for roles, inset grouped lists, and a floating glass tab bar on phones.
- **Signature:** the yellow highlighter, used only on resume content (section names, "Get placed."), like a marker on paper.
- **Demo:** the resume-scanning animation is a small timeline in `main.js`: each element has `data-at="N"`, and every step switches on the elements whose number has been reached. It pauses when scrolled off-screen.

**Why the animations don't lag**
- Animations only change `transform` and `opacity`, which the GPU handles without recalculating layout.
- The wallpaper never moves, so the glass never has to re-blur a changing picture. The expensive refraction is only on the few floating bars; big cards are frosted only.
- Refraction maps are drawn once and redrawn only when an element changes size.
- Scroll effects share one listener that updates at most once per frame (`requestAnimationFrame`); reveals use `IntersectionObserver`. Measured: ~60 fps while scrolling and while the demo plays.
- One Chrome gotcha we fixed: a parent that keeps a finished opacity animation (`animation-fill-mode: both`) stops the glass inside it from seeing what's behind, so those animations use `backwards`.

**Accessibility**
- Text contrast was measured on the real glass (screenshot of the page with the text hidden, then text colour vs the actual pixels behind it): body and secondary text meet WCAG AA (4.5:1). Text that sits straight on the wallpaper gets a soft shadow or a small glass chip.
- Font sizes are in `rem`, so text grows with the browser's text-size setting. Every page fits a phone screen at 150% and 200% text size.
- "Reduce transparency" turns the glass solid and switches refraction off, "increase contrast" removes the rainbow edge and deepens the tint, and "reduce motion" stops the animations.
- Everything works with the keyboard alone, including choosing a resume file. Status always uses a symbol and a word, never colour alone. Error notifications stay until dismissed.

**Security summary:** hashed passwords, signed HTTP-only session cookie, server-side role checks, file-signature validation, size limit, random private file names, and students can only open their own resumes (others get 404).

## Definition of Done (Sprint 1)

- [x] All four user stories implemented and demoable
- [x] Automated tests for every story (35 passing: `pytest -v`)
- [x] Passwords hashed; pages protected on the server, not just hidden in the UI
- [x] Uploaded files stored outside the public folder under random names
- [x] Works on desktop and phone screens
- [x] README explains how to run it

## Out of scope / next sprints

- Scoring and explanations: Sprints 2–3
- Job-description matching and the placement-staff dashboard: Sprints 4–5
- Database and deployment: later sprints

Data is currently kept in memory (`USERS`, `RESUMES` in `app.py`) and resets when the server restarts. Scoring, feedback and job matching will build on the `parsed` data that `resume_parser.parse_resume()` already returns.
