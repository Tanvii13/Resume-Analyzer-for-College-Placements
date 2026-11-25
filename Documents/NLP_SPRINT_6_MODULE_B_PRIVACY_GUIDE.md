# NLP Sprint 6 Module B: Student Resume Data Privacy

## Scope and requirements

This NLP-only module implements the data-minimisation aspects of US-17
(NFR-03, NFR-09 and DR-08). It does not perform authentication, authorisation,
file/database security, encryption, record retention, or deletion.

## Data flow and safeguards

Raw text enters NLP through `ResumeNLPPipeline` only for extraction and, when
requested, formatting analysis. Segmented text and extractor evidence are
in-memory processing data. The NLP layer has no database, file, network,
telemetry, external AI, or LLM calls; resume data is not sent to an external
service.

`CandidateProfile` retains existing structured fields for authorised backend
workflows, including evidence fields used by current scoring rules. To avoid
an unnecessary additional copy, pipelines do not persist raw text themselves.
The backend owns any persistence, retention and erasure decisions; this module
does not create a retention policy or period.

Personal data in processing inputs is excluded from Pydantic debug
representations: requests, contact data, filenames, opaque resume identifiers,
profile evidence and free-text lists do not appear in `repr()`. This protects
against accidental debug logging while preserving existing `model_dump()`
contracts for authorised backend storage/workflows.

Job-matching and opportunity-ranking outputs omit candidate identity. Their
scores, gaps and explanations use only skills, qualifications and job-related
evidence. A backend that needs to associate a result with a student must do so
outside the NLP response after enforcing role and ownership checks.

All NLP pipeline, analysis and job-workflow failures expose only a stage/module
and exception type. Raw exception text and Pydantic validation messages are
not returned or logged because they can contain resume content.

Aggregate placement reports remain count/percentage-only, suppress small
groups, and run the existing identity-leak audit before return.

## Remaining backend dependencies

The backend must enforce access control before supplying resume text, avoid
logging request bodies or serialized profiles, and decide retention/deletion
under the project policy. It must also associate de-identified NLP outputs
with records without adding names, contact details, or filenames back into
staff/aggregate payloads.
