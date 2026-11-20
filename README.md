# Resume Analyser for College Placements
**Upload it, understand it, improve it, get placed!**

**Subject:** IT314 – Software Engineering  
**Instructor:** Prof. Saurabh Tiwari  
**Mentor:** Dhruvil Mehta

## Team Members

| Name | Student ID |
|---|---:|
| Nakum Tanvi Dhiren (Team Leader) | 202401262 |
| Sujal Balva | 202401216 |
| Tanishk Dhawan | 202401224 |
| Topaliya Shlok Ashokbhai | 202401229 |
| Trivedi Atharv | 202401230 |
| Vamja Krish Pravinbhai | 202401239 |
| Solanki Taniskumar Mehulbhai | 202401264 |
| Tejot Harshil Rajendrabhai | 202401265 |
| Krish Hitendrakumar Paghadar | 202401429 |
| Prerak Patel | 202401452 |

## 1. Project Overview

The **Resume Analyser for College Placements** is a proposed tool that helps college students prepare for placements and internships. It analyses resume formatting and skill relevance, then compares student profiles with job and internship clusters based on profile similarity. It also provides feedback and practical suggestions to help students improve their resumes.

The platform aims to make resume evaluation more structured and understandable. Students can review their resume analysis, identify missing skills, and learn which areas may need improvement. The system may also support placement officers and career counsellors by providing useful summaries, with access controlled according to user roles.

## 2. Problem Statement

Students may find it difficult to assess the quality of their resumes, identify areas that need improvement, or understand how well their skills match specific job and internship opportunities. General resume templates can help with formatting, but they do not always explain which skills are missing or how closely a resume matches a particular job description.

Reviewing a large number of student resumes manually can also be time-consuming for placement officers and recruiters. This project aims to make resume analysis more organized and understandable by providing a score, explaining the main factors behind the result, and suggesting practical improvements.

## 3. Proposed Tentative Solution

The proposed system will allow students to upload their resumes, extract relevant information, analyse formatting and skills, and receive a score with feedback and improvement suggestions. Students will also be able to compare their profiles with job or internship requirements and identify matching and missing skills.

The system is intended to support placement preparation. Automated scores and recommendations should assist users, not replace human judgement or final placement decisions.

## 4. Project Objectives and Key Features

- **Resume upload and validation:** Accept supported resume files and provide clear messages for invalid or unreadable files.
- **Resume information extraction:** Extract available details such as education, skills, projects, and experience.
- **Resume analysis and scoring:** Evaluate resumes against defined criteria and provide an overall score.
- **Feedback and improvement suggestions:** Highlight strengths and areas that need improvement, with understandable explanations.
- **Job and internship matching:** Compare resume information with job descriptions and identify matching, missing, required, and preferred skills where the information is available.
- **Placement staff support:** Provide relevant summaries to authorized placement staff while protecting students' personal information.
- **Responsible use:** Keep automated analysis transparent and use it as supporting information rather than as the sole basis for placement or recruitment decisions.

## 5. How the System Works

The following flow describes the proposed user journey:

```mermaid
flowchart TD
    A([Start]) --> B[User logs in]
    B --> C[Upload resume]
    C --> D{Is the file valid?}
    D -- No --> E[Show an error and allow retry]
    E --> C
    D -- Yes --> F[Extract resume information]
    F --> G{Was the information extracted correctly?}
    G -- No --> H[Show extraction issue]
    H --> I[Review or upload another resume]
    I --> C
    G -- Yes --> J[Analyse resume and calculate score]
    J --> K[Show strengths and improvement suggestions]
    K --> L[Compare with job description]
    L --> M[Show matching and missing skills]
    M --> N{Does the user want to improve the resume?}
    N -- Yes --> O[Update resume and analyse again]
    O --> C
    N -- No --> P[Save or download results, if supported]
    P --> Q([End])
```

**Main workflow:** Upload → Extract → Analyse → Explain → Match → Improve.

Resume extraction may not always be completely accurate, so the system should provide a way to report or review unreadable or incorrectly extracted information.


### Component Responsibilities

| Component | Responsibility |
|---|---|
| Frontend | Provides resume upload, analysis results, feedback, and job-matching views. |
| Backend API | Handles requests, validation, authentication, and communication between components. |
| Resume Parser | Extracts readable text and relevant sections from uploaded files. |
| Skill Extraction | Identifies and normalises skills from resume content. |
| Scoring and Feedback | Evaluates resumes against defined criteria and explains the results. |
| Matching Engine | Compares extracted resume information with job requirements. |
| Database | Stores necessary user, analysis, and job-related information. |
| Access Control | Restricts access to data and features according to user roles. |

This diagram represents the intended design. Actual component behaviour and integrations will be documented as implementation progresses.

## 7. Technology Stack

The technology stack is tentative and may change as the project develops. The final choices will depend on what the team can implement, test, and maintain.

| Layer | Proposed Technology | Purpose |
|---|---|---|
| Frontend | Python, Javascript, CSS, HTML | User interface for resume upload, feedback, and job matching. |
| Backend | FastAPI, Python 3.10+, Uvicorn | REST API, authentication, validation, and resume management. |
| Resume Processing | `pypdf`, `python-docx` | Structured text extraction, document validation, and metadata processing. |
| NLP and Profile Matching | Python NLP tooling | Parsing, skill extraction, and scoring in subsequent sprints. |
| Database | PostgreSQL (`psycopg`) | Persistent storage for users, resume metadata, and analysis results. |
| Version Control | Git and GitHub | Manage source code and support team collaboration. |
| Testing | `pytest`, `httpx` | Automated backend testing and parser verification. |
| Deployment | Container / Cloud (Planned) | Production deployment. |

Any library or service adopted should be evaluated for accuracy, compatibility, privacy, and maintainability.

## 8. Backend & NLP Sprint 1: Resume Parsing, Validation & Running Locally

### 8.1 Scope & Implemented Features (Sprint 1)

Sprint 1 delivers the core document parsing, validation, and structured error handling for the Resume Analyser:

- **Supported Formats:** PDF (`.pdf`) and Microsoft Word (`.docx`).
- **File Validation Rules:**
  - Maximum upload file size: **5 MB** (`MAX_FILE_SIZE = 5 * 1024 * 1024`).
  - Empty or zero-byte document detection (`EMPTY_FILE`).
  - Extension and magic byte verification (`%PDF-` for PDF, `PK\x03\x04` for DOCX) preventing file-extension/content mismatches.
  - Verification that `.docx` files are valid OpenXML Word documents containing `word/document.xml`, rejecting arbitrary renamed ZIP archives.
  - Detection of encrypted/password-protected PDFs (`ENCRYPTED_FILE`).
  - Detection of corrupt or structurally invalid documents (`CORRUPTED_FILE`).
  - Verification that extractable text contains readable alphanumeric content (`NO_READABLE_TEXT`).
- **Text Extraction:**
  - **PDF (`pypdf`):** Iterates over document pages, extracts page text, joins logical pages with clean paragraph separation, and records page count.
  - **DOCX (`python-docx`):** Extracts section headers (where candidate contact details commonly reside), paragraphs, Content Controls (`w:sdt`), and tables in document order, deduplicating merged table cells and preserving tabular reading flow.
  - **Whitespace Normalization:** Normalizes Unicode whitespace (NFKC), removes zero-width characters and soft hyphens, collapses excessive blank lines (`\n\n\n+` to `\n\n`), and cleans intra-line spacing while preserving meaningful structure.
- **Known Limitations:**
  - **No OCR:** Image-only or scanned PDFs without text layers are detected and returned as `NO_READABLE_TEXT`. Optical Character Recognition (OCR) is explicitly outside Sprint 1 scope.
  - **No fabricated page count for DOCX:** Word documents do not store fixed page counts internally; `page_count` is set to `None` for DOCX.
  - **No AI scoring/skill matching:** Resume analysis and scoring belong to Sprint 2+.

### 8.2 Parser Interface & Error Codes

The parser provides a reusable, pure-Python interface callable independently of FastAPI:

```python
from app.services.resume_parser import parse_resume, ResumeParseResult

result: ResumeParseResult = parse_resume(file_bytes=content, filename="resume.pdf")
print(result.filename)    # "resume.pdf"
print(result.file_type)   # ".pdf"
print(result.text)        # Extracted and normalized text
print(result.page_count)  # 2 (for PDF) or None (for DOCX)
print(result.word_count)  # Total word count
print(result.char_count)  # Total character count
```

**Stable Error Codes:**
- `EMPTY_FILE`: File is empty (0 bytes).
- `UNSUPPORTED_FORMAT`: Extension is not `.pdf` or `.docx`.
- `FILE_TOO_LARGE`: Exceeds the 5 MB limit.
- `INVALID_FILE`: Missing filename, mismatched signature, or non-DOCX ZIP archive.
- `CORRUPTED_FILE`: Structurally corrupt or unreadable archive/stream.
- `ENCRYPTED_FILE`: Password-protected PDF or DOCX file.
- `NO_READABLE_TEXT`: Document contains no readable/alphanumeric text.
- `PARSER_ERROR`: Unexpected parsing/extraction failure.

### 8.3 Backend Integration Endpoints

The parser integrates cleanly with the existing FastAPI backend routes in `app/routers/resumes.py`:

- `POST /resumes/upload`: Uploads and stores the resume document, creates a database record with `status: "uploaded"`, and preserves the existing backend contract.
- `POST /resumes/{resume_id}/parse`: Parses a previously uploaded resume for the authenticated student, updates database status to `status: "parsed"` and sets `processed_at`, or marks `status: "failed"` upon error.
- `POST /resumes/parse`: Direct multipart upload endpoint to validate and parse a resume file immediately.

### 8.4 Setup & Testing Instructions

1. **Install Dependencies:**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. **Run Tests:**
   ```bash
   cd backend
   pytest tests/test_resume_parser.py -v
   ```
   To run the full backend test suite:
   ```bash
   pytest tests/ -v
   ```

3. **Run Backend Server:**
   ```bash
   cd backend
   uvicorn main:app --reload --port 8000
   ```


## 9. Team Contributions

See [documents/contributions.md](Documents/Contributions.md) for details of individual team contributions.

## 10. Future Scope

After the core system has been implemented and evaluated, possible extensions include:

- Improving resume parsing for different layouts and document formats.
- Enhancing skill extraction with NLP and domain-specific skill dictionaries.
- Improving semantic matching between resume content and job descriptions.
- Adding resume version history and comparison.
- Providing guidance tailored to different roles and industries.
- Integrating with placement portals, subject to API availability and institutional approval.
- Improving placement analytics while maintaining appropriate privacy controls.
- Expanding testing for accessibility, fairness, and performance.

These extensions will depend on the project's scope, available data, time, and evaluation results.
