# Resume Analyser for College Placements — User Stories / Product Backlog

## 1. Introduction

This document contains the Product Backlog for the Resume Analyser for College Placements, written as user stories. Each requirement identified in *Apply Elicitation Techniques.md* (FR-01–FR-15, NFR-01–NFR-11, DR-01–DR-10) has been converted into a user story with a front of the card (role, goal, benefit) and a back of the card (acceptance criteria).



## 2. Product Backlog Table

| Story ID | Requirement ID(s) | Role | User Story (short) | Type | Priority | Elicitation Source |
|---|---|---|---|---|---|---|
| US-01 | FR-01 | Student | Upload my resume | FR | Must Have | Survey, Observation |
| US-02 | FR-02 | Student | Have my resume parsed | FR | Must Have | Interview, Brainstorming |
| US-03 | FR-14 | Student | Be told clearly if my resume can't be processed | FR | Must Have | Observation, Prototype |
| US-04 | FR-03 | Student | Have skills extracted from my resume | FR | Must Have | Survey, Recruiter Interview |
| US-05 | FR-04, DR-01 | Student | Have my resume analysed against defined criteria | FR + DR | Must Have | Survey, Interview, Placement Discussion |
| US-06 | FR-05 | Student | See a resume score | FR | Must Have | Survey, Interview |
| US-07 | FR-06 | Student | Know the key areas I need to improve | FR | Must Have | Survey, Observation |
| US-08 | FR-07 | Student | Get improvement suggestions | FR | Must Have | Survey, Faculty Interview |
| US-09 | FR-11 | Student | Understand why I got a score/recommendation | FR | Must Have | Faculty Interview, Prototype |
| US-10 | FR-08, DR-02, DR-04 | Student | Compare my skills with a job's requirements | FR + DR | Must Have | Recruiter Interview, Document Analysis |
| US-11 | FR-09, DR-02 | Student | See suitable job/internship matches | FR + DR | Must Have | Survey, Recruiter Interview |
| US-12 | FR-10, DR-03, DR-04 | Student | See matching/missing skills, required vs preferred | FR + DR | Must Have | Recruiter Interview, Document Analysis |
| US-13 | FR-12 | Placement Officer / Faculty-Counselor | View authorized student resume analysis | FR | Should Have | Placement Officer Interview, Faculty Interview |
| US-14 | FR-13, DR-05 | Placement Officer | View placement dashboards/reports | FR + DR | Should Have | Placement Interview, Workshop, Placement Documents |
| US-15 | FR-15, NFR-07, DR-07 | System Administrator | Enforce role-based access to student data | FR + NFR + DR | Must Have | Privacy / System Admin Discussion |
| US-16 | NFR-03, NFR-09, DR-08 | Data Privacy Reviewer | Protect and minimize exposure of resume data | NFR + DR | Must Have | Privacy Discussion, Policy Analysis |
| US-17 | DR-06 | Hiring Manager | Keep automated output advisory, not decisive | DR | Must Have | Placement / Recruiter Discussion |
| US-18 | DR-09 | Bias / Fairness Reviewer | Have scoring/matching reviewed for fairness | DR | Must Have | Fairness Discussion |
| US-19 | NFR-10 | Development Team | Keep parsing/scoring/matching maintainable | NFR | Should Have | Brainstorming |




## 3. User Story Cards

### US-01 — Upload Resume
**Requirement ID(s):** FR-01 (NFR-01 as AC) | **Type:** Functional | **Role:** Student / Job Seeker | **Priority:** Must Have | **Source:** Survey, Observation

**Front of Card**
> As a student, I want to upload my resume to the system, so that it can be analysed and I can get feedback on it.

**Back of Card — Acceptance Criteria**
1. Given a student is on the upload screen, when they select a resume file in a supported format, then the file is accepted and an upload confirmation is shown.
2. Given a resume upload is in progress, when the student checks the screen, then clear upload progress/status is displayed.
3. Given the upload succeeds, when the student is redirected, then they are taken to the analysis flow without needing further instructions.

---

### US-02 — Parse Uploaded Resume
**Requirement ID(s):** FR-02 | **Type:** Functional | **Role:** Student / Job Seeker | **Priority:** Must Have | **Source:** Interview, Brainstorming

**Front of Card**
> As a student, I want my uploaded resume to be parsed, so that its content is available for analysis and I can review what the system extracted.

**Back of Card — Acceptance Criteria**
1. Given a successfully uploaded, supported resume, when parsing runs, then the resume's sections (education, skills, experience) are identified and stored for analysis.
2. Given parsing has completed, when the student views their resume in the system, then the extracted content is available to be shown for review.
3. Given the resume is only partially readable, when parsing completes, then the parts that could not be reliably parsed are flagged rather than silently dropped.

---

### US-03 — Handle Invalid or Unsupported Resume Input
**Requirement ID(s):** FR-14 (NFR-06 as AC) | **Type:** Functional | **Role:** Student / Job Seeker | **Priority:** Must Have | **Source:** Observation, Prototype

**Front of Card**
> As a student, I want to be told clearly when my resume cannot be processed, so that I know what went wrong and can fix it.

**Back of Card — Acceptance Criteria**
1. Given a student uploads a file in an unsupported format, when the system attempts to process it, then upload is rejected and a specific, plain-language error message is shown.
2. Given a student uploads a corrupted or empty resume file, when parsing fails, then the student is told parsing failed and what to do next.
3. Given an error has been shown, when the student re-uploads a valid resume, then the previous error is cleared and processing proceeds normally.

---

### US-04 — Extract Skills from Resume
**Requirement ID(s):** FR-03 | **Type:** Functional | **Role:** Student / Job Seeker | **Priority:** Must Have | **Source:** Survey, Recruiter Interview

**Front of Card**
> As a student, I want the system to extract the relevant skills from my resume, so that I can see how my skills are being read and used for analysis and matching.

**Back of Card — Acceptance Criteria**
1. Given a parsed resume, when skill extraction runs, then a list of identified skills is produced and stored against the student's resume.
2. Given a resume that lists skills in a dedicated section as well as within experience descriptions, when extraction runs, then skills from both locations are captured.
3. Given the extracted skill list is generated, when the student views their analysis, then the extracted skills are visible to them.

---

### US-05 — Analyse Resume Against Defined Criteria
**Requirement ID(s):** FR-04, DR-01 (NFR-02, NFR-04 as AC) | **Type:** Functional + Domain | **Role:** Student / Job Seeker | **Priority:** Must Have | **Source:** Survey, Interview, Placement Discussion

**Front of Card**
> As a student, I want my resume analysed against defined criteria relevant to college placements, so that I get feedback that is actually useful for placement preparation.

**Back of Card — Acceptance Criteria**
1. Given an uploaded and parsed resume, when analysis runs, then the resume is evaluated only against criteria relevant to college placement/internship preparation.
2. Given analysis is triggered, when the student waits for results, then results are returned within an acceptable response time.
3. Given the same resume and the same system configuration, when analysis is run more than once, then the same analysis results are produced.

---

### US-06 — View Resume Score
**Requirement ID(s):** FR-05 (NFR-04, NFR-08 as AC) | **Type:** Functional | **Role:** Student / Job Seeker | **Priority:** Must Have | **Source:** Survey, Interview

**Front of Card**
> As a student, I want to see a resume score after analysis, so that I have a clear indicator of my current resume quality.

**Back of Card — Acceptance Criteria**
1. Given resume analysis has completed, when the student views their results, then a resume score is displayed in a readable, accessible format.
2. Given the same resume and configuration, when the score is recalculated, then the score value stays the same.
3. Given the score is displayed, when the student looks for context, then the score is presented alongside the explanation described in US-09, not as a bare number.

---

### US-07 — Identify Key Improvement Areas
**Requirement ID(s):** FR-06 (NFR-08 as AC) | **Type:** Functional | **Role:** Student / Job Seeker | **Priority:** Must Have | **Source:** Survey, Observation

**Front of Card**
> As a student, I want the system to highlight the most important areas I need to improve, so that I know where to focus my effort.

**Back of Card — Acceptance Criteria**
1. Given completed analysis, when the student views results, then the top improvement areas are presented as a distinct, clearly labelled section.
2. Given multiple issues exist in a resume, when improvement areas are shown, then they are ordered or grouped so the most important issues are easy to find first.
3. Given a resume has no significant issues in a category, when results are shown, then that category is not listed as an improvement area.

---

### US-08 — Receive Improvement Suggestions
**Requirement ID(s):** FR-07 (NFR-05 as AC) | **Type:** Functional | **Role:** Student / Job Seeker | **Priority:** Must Have | **Source:** Survey, Faculty Interview

**Front of Card**
> As a student, I want concrete suggestions on how to improve my resume, so that I can act on the feedback.

**Back of Card — Acceptance Criteria**
1. Given improvement areas have been identified (US-07), when results are shown, then each improvement area is paired with an actionable suggestion.
2. Given a suggestion is displayed, when the student reads it, then it uses understandable, non-technical language.
3. Given the resume has an identified missing or weak skill, when suggestions are generated, then the suggestion names the skill or issue it relates to.

---

### US-09 — Understand Why a Score or Recommendation Was Given
**Requirement ID(s):** FR-11 (NFR-05 as AC) | **Type:** Functional | **Role:** Student / Job Seeker | **Priority:** Must Have | **Source:** Faculty Interview, Prototype

**Front of Card**
> As a student, I want an explanation for important scores and recommendations, so that I understand why I received them and can act on them.

**Back of Card — Acceptance Criteria**
1. Given a resume score or a key recommendation is shown, when the student requests more detail, then a plain-language explanation of the main contributing factors is displayed.
2. Given an explanation is shown, when a faculty/counselor reviews it with the student, then it is understandable without requiring technical background.
3. Given no explanation can be generated for a particular result, when that result is displayed, then it is not shown without any supporting context.

---

### US-10 — Compare Resume Skills with Job Requirements
**Requirement ID(s):** FR-08, DR-02, DR-04 | **Type:** Functional + Domain | **Role:** Student / Job Seeker | **Priority:** Must Have | **Source:** Recruiter Interview, Document Analysis

**Front of Card**
> As a student, I want my resume's skills compared against a specific job or internship's requirements, so that I know how well I fit that role.

**Back of Card — Acceptance Criteria**
1. Given a student selects a job/internship, when comparison runs, then the comparison is based on the skills and requirements defined for that target role.
2. Given the student has a skill that is a close equivalent to a required skill, when comparison runs, then the related/equivalent skill is considered rather than counted as fully missing.
3. Given comparison completes, when results are shown, then the student sees which of their skills matched and which did not.

---

### US-11 — View Suitable Job/Internship Matches
**Requirement ID(s):** FR-09, DR-02 | **Type:** Functional + Domain | **Role:** Student / Job Seeker | **Priority:** Must Have | **Source:** Survey, Recruiter Interview

**Front of Card**
> As a student, I want to see job or internship opportunities that suit my resume, so that I can discover roles worth applying to.

**Back of Card — Acceptance Criteria**
1. Given a student's resume has been analysed, when they request matches, then a list of suitable job/internship opportunities is returned, ranked or grouped by suitability.
2. Given the list of matches is generated, when matches are ranked, then ranking reflects fit with the skills/requirements of each target role.
3. Given no suitable matches exist for the student's current skill set, when they request matches, then the system states that no strong matches were found rather than showing irrelevant results.

---

### US-12 — View Matching and Missing Skills for a Selected Job
**Requirement ID(s):** FR-10, DR-03, DR-04 | **Type:** Functional + Domain | **Role:** Student / Job Seeker | **Priority:** Must Have | **Source:** Recruiter Interview, Document Analysis

**Front of Card**
> As a student, I want to see which skills I match and which I'm missing for a selected job, and whether they are required or preferred, so that I can prioritize what to learn or highlight.

**Back of Card — Acceptance Criteria**
1. Given a student selects a specific job, when the skill comparison is shown, then matching skills and missing skills are both listed separately.
2. Given the job description distinguishes required and preferred skills, when missing skills are shown, then each missing skill is labelled as required or preferred.
3. Given a missing skill has a close equivalent the student already has, when results are shown, then the equivalent skill is noted rather than the skill simply being marked as missing.

---

### US-13 — View Authorized Student Resume Analysis (Placement Staff)
**Requirement ID(s):** FR-12 | **Type:** Functional | **Role:** Placement Cell / Placement Officers, Faculty / Career Counselors | **Priority:** Should Have | **Source:** Placement Officer Interview, Faculty Interview

**Front of Card**
> As a placement officer / career counselor, I want to view a student's resume analysis when authorized, so that I can guide the student and discuss the results with them.

**Back of Card — Acceptance Criteria**
1. Given a placement officer or counselor has an authorized role, when they open a specific student's record, then that student's resume analysis, score, and suggestions are visible to them.
2. Given a staff member does not have an authorized role for a given student, when they attempt to view that student's data, then access is denied.
3. Given a counselor views a student's analysis, when they discuss it with the student, then the explanation shown (US-09) is understandable enough to walk through together.

---

### US-14 — View Placement Dashboards / Reports
**Requirement ID(s):** FR-13, DR-05 | **Type:** Functional + Domain | **Role:** Placement Cell / Placement Officers | **Priority:** Should Have | **Source:** Placement Interview, Workshop, Placement Documents

**Front of Card**
> As a placement officer, I want a dashboard/report of resume analysis trends across students, so that I can identify common problems and plan placement training accordingly.

**Back of Card — Acceptance Criteria**
1. Given multiple students have completed resume analysis, when a placement officer opens the dashboard, then aggregate information (common weak areas, average scores) is displayed.
2. Given the dashboard shows batch-level information, when it is displayed, then it does not expose sensitive individual student information beyond what the officer is authorized to view.
3. Given the dashboard references any placement-eligibility-related information, when it is shown, then that information is consistent with the college's official placement-process rules.

---

### US-15 — Enforce Role-Based Access to Student and Resume Data
**Requirement ID(s):** FR-15, NFR-07, DR-07 | **Type:** Functional + Non-Functional + Domain | **Role:** System Administrator | **Priority:** Must Have | **Source:** Privacy / System Administration Discussion

**Front of Card**
> As a system administrator, I want access to student and resume information restricted according to user roles, so that only authorized people can see information they are entitled to see.

**Back of Card — Acceptance Criteria**
1. Given a defined set of roles (Student, Placement Officer, Recruiter, Admin), when any user accesses the system, then they only see data and functions permitted for their role.
2. Given a user without placement-staff privileges, when they attempt to view another student's resume analysis, then the request is denied.
3. Given a role's permissions are changed by an admin, when a user with that role next logs in, then their access reflects the updated permissions.

---

### US-16 — Protect and Minimize Exposure of Resume Data
**Requirement ID(s):** NFR-03, NFR-09, DR-08 | **Type:** Non-Functional + Domain | **Role:** Data Privacy Reviewer | **Priority:** Must Have | **Source:** Privacy Discussion, Document Analysis, Policy Analysis

**Front of Card**
> As a data privacy reviewer, I want resume and personal data protected from unauthorized access and not collected or exposed beyond what is necessary, so that students' personal information stays safe and compliant with institutional privacy rules.

**Back of Card — Acceptance Criteria**
1. Given resume data is stored, when any access attempt is made, then only authenticated, authorized users can retrieve it.
2. Given a screen or report displays student information, when it is generated, then it includes only the personal information necessary for that specific purpose.
3. Given the college's data-handling/privacy policy defines retention and consent rules, when resume data is stored or processed, then the system's handling of that data follows those rules.

---

### US-17 — Keep Automated Output Advisory, Not Decisive
**Requirement ID(s):** DR-06 | **Type:** Domain | **Role:** Hiring Manager, Placement Officer, Recruiter | **Priority:** Must Have | **Source:** Placement / Recruiter Discussion

**Front of Card**
> As a hiring manager, I want the system's scores, matches, and recommendations to support my decision rather than make it for me, so that I retain full control over placement/hiring outcomes.

**Back of Card — Acceptance Criteria**
1. Given a candidate has a low resume score or a poor job match, when results are shown, then the system does not automatically reject, shortlist, or finalize any placement/hiring decision.
2. Given a hiring manager or placement officer views a recommendation, when they review it, then the output is presented as a suggestion with supporting evidence, not a verdict.
3. Given a candidate disagrees with an automated result, when they raise it through the appropriate staff, then a human reviewer makes the final call.

---

### US-18 — Review Scoring and Matching Logic for Fairness
**Requirement ID(s):** DR-09 | **Type:** Domain | **Role:** Bias / Fairness Reviewer | **Priority:** Must Have | **Source:** Fairness Discussion

**Front of Card**
> As a bias/fairness reviewer, I want the resume scoring and job-matching logic checked so that irrelevant candidate characteristics don't unfairly affect results, so that the system treats all students fairly.

**Back of Card — Acceptance Criteria**
1. Given the scoring/matching logic is defined, when a fairness reviewer inspects it, then it can be shown which resume factors are used to compute scores/matches and which are explicitly excluded.
2. Given test resumes that differ only in an irrelevant characteristic, when they are scored, then the resulting scores/matches do not show an unjustified systematic difference.
3. Given a fairness issue is found during review, when it is reported, then it is logged and tracked for the development team to address.

---

### US-19 — Keep Parsing, Scoring, and Matching Components Maintainable
**Requirement ID(s):** NFR-10 | **Type:** Non-Functional | **Role:** Development Team | **Priority:** Should Have | **Source:** Brainstorming

**Front of Card**
> As a member of the development team, I want the parsing, scoring, and matching components to be maintainable, so that we can update or fix them across sprints without reworking the whole system.

**Back of Card — Acceptance Criteria**
1. Given the parsing, scoring, and matching logic exist as separable components, when one needs to change, then it can be updated without requiring changes to the other two.
2. Given a component is modified, when it is tested, then existing behaviour for unrelated components is unaffected.
3. Given a new team member joins, when they review the component structure, then each component's responsibility is documented clearly enough to be understood without asking the original author.

---
