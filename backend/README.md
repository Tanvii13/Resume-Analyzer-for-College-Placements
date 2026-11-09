# Resume Analyzer for College Placements — Backend

## Overview
The backend powers resume processing and analysis for college placement preparation. It handles secure resume access, text extraction, and structured resume information processing.

## Sprint Progress

- **Sprint 1 — Foundation:** Authentication, resume upload, file validation, and text extraction.
- **Sprint 2 — Information Extraction:** NLP integration, skill extraction and normalization, structured output validation, and API integration.
- **Upcoming Sprints:** Resume scoring, feedback, job matching, and other planned features.

*Features are implemented incrementally; see the current code and sprint tasks for implementation status.*

## Technology Stack
- Python
- FastAPI
- PostgreSQL
- Pydantic
- pytest
- Git and GitHub

## Key API
- `POST /resumes/{resume_id}/extract` — Extract structured information from a resume.

*The endpoint and its behavior depend on the current backend implementation.*

## Setup
1. Install Python and the project dependencies.
2. Configure the required environment variables and database.
3. Run the backend using the project's configured entry point.
4. Open `/docs` on the local server to explore the API.

Refer to the project configuration and dependency files for the exact setup and run commands.

## Testing
Run the project's configured test suite with pytest.

## Security
- Verify user authentication and resume ownership.
- Validate uploaded files and extracted data.
- Keep credentials and personal resume information secure.
- Never commit secrets or private resumes.

## Development
Work on the appropriate feature branch, test changes, and open a pull request into the intended target branch.
