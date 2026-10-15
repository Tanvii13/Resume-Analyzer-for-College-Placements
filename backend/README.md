# Resume Analyzer for College Placements — Backend

## 1. Project Overview

The backend of the **Resume Analyzer for College Placements** project handles user authentication, resume uploads, file validation, and resume text extraction.

It provides the foundation for analyzing resumes and supporting students during the college placement process.

## 2. Sprint 1 Scope

The backend focuses on the following user stories:

- **US-01 — Account Access:** Handle user authentication and account-related operations.
- **US-02 — Resume Upload:** Accept resume files and validate uploaded documents.
- **US-03 — Resume Parsing:** Extract readable text from supported resume files.
- **US-04 — Error Handling:** Handle invalid or unreadable files and return appropriate error messages.

Advanced resume scoring, skill-gap analysis, and job-description matching are planned for later development stages.

## 3. Technology Stack

- **Language:** Python
- **Backend Framework:** FastAPI
- **Database:** PostgreSQL
- **Testing:** pytest
- **Version Control:** Git and GitHub

## 4. Project Structure

```text
backend/
├── app/
│   ├── routers/
│   ├── services/
│   └── database.py
├── tests/
├── main.py
├── requirements.txt
└── README.md
```

The routers handle API requests, services contain application logic, and the tests help verify backend functionality.

## 5. Setup and Installation

### Prerequisites

- Python installed
- PostgreSQL configured if required by the application
- Git installed

### Install Dependencies

From the repository root, run:

```bash
python -m pip install -r backend/requirements.txt
```

### Run the Backend

From the repository root, run:

```bash
python -m uvicorn backend.main:app --reload
```

Once the server starts, open the following URL to access the FastAPI documentation:

```text
http://127.0.0.1:8000/docs
```

If the project uses a different entry point or configuration, adjust the command accordingly.

## 6. Resume Upload and Validation

The resume-processing workflow is designed to:

- Accept supported resume formats, such as PDF and DOCX.
- Validate uploaded files before processing.
- Extract readable text from supported documents.
- Handle unsupported, empty, or unreadable files with appropriate errors.

File-size limits, accepted formats, and error responses should follow the actual backend implementation.

## 7. Testing

Run the backend tests from the repository root:

```bash
python -m pytest backend/tests -v
```

Review the test results to confirm which authentication, upload, parsing, and error-handling cases pass.

## 8. Security and Data Privacy

- Never store plain-text passwords; use secure password hashing.
- Validate uploaded files before processing them.
- Do not commit passwords, API keys, database credentials, or other secrets to GitHub.
- Store uploaded resumes securely and restrict access to authorized users.
- Avoid exposing sensitive resume information in application logs or error messages.

## 9. Future Enhancements

Planned enhancements may include:

- Resume scoring with explainable feedback
- Skill extraction and missing-skill identification
- Resume comparison with job descriptions
- Additional placement-support features


