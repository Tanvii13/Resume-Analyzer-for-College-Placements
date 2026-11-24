# NLP Sprint 6 Module A: Privacy Boundaries

This document describes the NLP-layer contract for Sprint 6. It implements the
NLP responsibilities of US-16 and US-17, and supports DR-06 through explicit,
reviewable analysis outputs. It does not implement authentication, role checks,
routes, database permissions, encryption, or retention jobs.

## Data boundaries

`ResumeNLPPipeline.process(text, filename, resume_id)` receives extracted
resume text only after the backend has validated the caller and ownership.
The text is required only for extraction and optional formatting analysis.
`resume_id` and `filename` are correlation inputs; they are not used to infer
skills, scores, or recommendations.

The student-specific `CandidateProfile` can contain the contact information
needed for the student-owned resume workflow. It must stay within the backend's
authorised, record-specific workflow. Missing values remain `None` or empty
collections; NLP components do not derive them from other fields.

`build_staff_analysis(profile, analysis, job_matches)` is the staff-safe NLP
projection. Its output contains readiness, skills, improvement evidence, and
job-fit evidence only. It excludes name, email, phone, profile links, filename,
resume identifier, and raw resume text. The builder refuses an output if it
contains a direct identity value or unmasked email/phone pattern.

`build_placement_report(records)` remains the aggregate-only pathway from
Sprint 5. It produces counts and percentages, suppresses small groups, and
performs its existing personal-data audit.

| NLP operation | Minimum student input | Permitted NLP output |
| --- | --- | --- |
| Profile extraction | Extracted resume text; filename only for internal compatibility; optional opaque resume id | `CandidateProfile` for the authorised record workflow; absent fields stay absent |
| Resume scoring and recommendations | Existing profile; raw text only when formatting analysis is requested | Scores, reasons, confidence, and improvement guidance |
| Job matching and opportunity ranking | Existing profile and job requirements | Skill/qualification fit, gaps, scores, and explanations |
| Staff analysis | Existing profile and already-produced analysis/match results | De-identified readiness, skills, improvement, and job-fit evidence |
| Placement reporting | Opaque student reference plus existing analysis results | Aggregated, small-group-suppressed statistics only |

## Backend integration requirements

The backend must enforce role and ownership checks before passing data to NLP.
Associate a staff analysis with a student in backend-controlled response
metadata, not by adding identifiers to `StaffAnalysisResult`. Provide the
smallest permitted input: use a profile for existing analysis, and pass raw
text only when parsing or formatting analysis is actually requested. Do not
log request bodies or persist raw NLP diagnostics.

Automated scores, match results, and staff summaries are decision support only.
They must not be used as an automatic rejection or final placement decision.
Their component scores, evidence, confidence, and limitations remain available
for human and fairness review.

## Logging and errors

NLP pipeline failures now record only the module and exception type. Raw
exception messages and validation messages are not logged or returned because
they may embed resume text. Existing shared contact-redaction rules are reused
for staff-output auditing rather than duplicated.
