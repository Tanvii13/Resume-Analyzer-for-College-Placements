# User Stories – Resume Analyser for College Placements

This section converts the requirements collected through elicitation into user stories. Each story describes what a user needs from the system and why it is useful. The acceptance criteria define when the story can be considered complete.

---

## 3. User Story Cards

### US-01 — Upload Resume

**Requirement ID(s):** FR-01 (NFR-01 as AC) | **Type:** Functional | **Role:** Student / Job Seeker | **Priority:** Must Have | **Source:** Survey, Observation

**Front of Card**

> As a student, I want to upload my resume to the system, so that I can get it analysed and receive useful feedback.

**Back of Card — Acceptance Criteria**

1. Given a student is on the upload screen, when they select a resume in a supported format, then the file is accepted and the upload is confirmed.
2. Given the resume is being uploaded, when the student checks the screen, then the upload status is clearly shown.
3. Given the upload is successful, when processing starts, then the student is taken to the resume analysis flow.

---

### US-02 — Parse Uploaded Resume

**Requirement ID(s):** FR-02 | **Type:** Functional | **Role:** Student / Job Seeker | **Priority:** Must Have | **Source:** Interview, Brainstorming

**Front of Card**

> As a student, I want my uploaded resume to be parsed, so that its content can be used for analysis and I can review what the system has extracted.

**Back of Card — Acceptance Criteria**

1. Given a supported resume has been uploaded, when parsing starts, then important sections such as education, skills and experience are identified.
2. Given parsing is complete, when the extracted information is viewed, then it is available for review and further analysis.
3. Given some part of the resume cannot be read properly, when parsing finishes, then that part is flagged instead of being silently ignored.

---

### US-03 — Handle Invalid or Unsupported Resume Input

**Requirement ID(s):** FR-14 (NFR-06 as AC) | **Type:** Functional | **Role:** Student / Job Seeker | **Priority:** Must Have | **Source:** Observation, Prototype

**Front of Card**

> As a student, I want to know when my resume cannot be processed, so that I can understand the problem and try again.

**Back of Card — Acceptance Criteria**

1. Given a student uploads an unsupported file, when the system checks it, then the upload is rejected and a clear error message is shown.
2. Given a resume file is empty or corrupted, when parsing fails, then the student is informed about the problem and what to do next.
3. Given an error has been shown, when the student uploads a valid resume, then the system allows processing to continue normally.

---

### US-04 — Extract Skills from Resume

**Requirement ID(s):** FR-03 | **Type:** Functional | **Role:** Student / Job Seeker | **Priority:** Must Have | **Source:** Survey, Recruiter Interview

**Front of Card**

> As a student, I want the system to identify relevant skills from my resume, so that I can see which skills are being considered during the analysis.

**Back of Card — Acceptance Criteria**

1. Given a resume has been parsed, when skill extraction is performed, then relevant skills mentioned in the resume are identified.
2. Given skills appear in different sections of the resume, when extraction is performed, then relevant skills from those sections are considered.
3. Given the skill extraction is complete, when the student views the results, then the identified skills are clearly displayed.

---

### US-05 — Analyse Resume Against Placement Criteria

**Requirement ID(s):** FR-04, DR-01 | **Type:** Functional + Domain | **Role:** Student / Job Seeker | **Priority:** Must Have | **Source:** Survey, Interview, Placement Discussion

**Front of Card**

> As a student, I want my resume to be analysed using criteria relevant to college placements, so that I receive feedback that is useful for placement preparation.

**Back of Card — Acceptance Criteria**

1. Given the resume has been uploaded and parsed, when analysis starts, then the resume is checked against the defined placement-related criteria.
2. Given the analysis is in progress, when the student waits for the result, then the system completes the analysis within the expected time.
3. Given the same resume and analysis settings are used again, then the system produces consistent results.

---

### US-06 — View Resume Score

**Requirement ID(s):** FR-05 (NFR-04, NFR-08 as AC) | **Type:** Functional | **Role:** Student / Job Seeker | **Priority:** Must Have | **Source:** Survey, Interview

**Front of Card**

> As a student, I want to receive an overall resume score, so that I can quickly understand how my resume performs against the defined criteria.

**Back of Card — Acceptance Criteria**

1. Given resume analysis is complete, when the student opens the results, then an overall resume score is displayed.
2. Given the same resume and analysis settings are used, when the score is calculated again, then the result remains consistent.
3. Given the score is displayed, when the student views it, then useful feedback is provided along with the score.

---

### US-07 — Identify Resume Improvement Areas

**Requirement ID(s):** FR-06 (NFR-08 as AC) | **Type:** Functional | **Role:** Student / Job Seeker | **Priority:** Must Have | **Source:** Survey, Observation

**Front of Card**

> As a student, I want the system to highlight the weak or missing areas in my resume, so that I know what I should improve.

**Back of Card — Acceptance Criteria**

1. Given the resume has been analysed, when the results are displayed, then important weak or missing areas are highlighted.
2. Given multiple issues are found, when the results are shown, then the main areas needing attention are easy to identify.
3. Given an area does not have a significant issue, then it should not be unnecessarily shown as a weakness.

---

### US-08 — Get Resume Improvement Suggestions

**Requirement ID(s):** FR-07 (NFR-05 as AC) | **Type:** Functional | **Role:** Student / Job Seeker | **Priority:** Must Have | **Source:** Survey, Faculty Interview

**Front of Card**

> As a student, I want to receive practical suggestions for improving my resume, so that I can make useful changes based on the analysis.

**Back of Card — Acceptance Criteria**

1. Given improvement areas have been identified, when the analysis results are shown, then relevant suggestions are provided.
2. Given a suggestion is displayed, when the student reads it, then it is clear and easy to understand.
3. Given a specific section or skill needs improvement, when a suggestion is generated, then it is related to that identified issue.

---

### US-09 — Understand Score and Recommendations

**Requirement ID(s):** FR-11 (NFR-05 as AC) | **Type:** Functional | **Role:** Student / Job Seeker | **Priority:** Must Have | **Source:** Faculty Interview, Prototype

**Front of Card**

> As a student, I want to understand why I received a particular score or recommendation, so that I know what led to the result and what I can improve.

**Back of Card — Acceptance Criteria**

1. Given a score or important recommendation is displayed, when the student views its details, then the main reasons behind it are shown.
2. Given an explanation is provided, when the student or counselor reads it, then it is understandable without requiring technical knowledge.
3. Given the system cannot provide enough information to explain a result, then the result should be shown with appropriate context rather than as an unexplained decision.

---

### US-10 — Compare Resume with Job Requirements

**Requirement ID(s):** FR-08, DR-02, DR-04 | **Type:** Functional + Domain | **Role:** Student / Job Seeker | **Priority:** Must Have | **Source:** Recruiter Interview, Document Analysis

**Front of Card**

> As a student, I want to compare my resume with a specific job or internship, so that I can understand how well my profile matches the role.

**Back of Card — Acceptance Criteria**

1. Given a student provides a job description, when the comparison is performed, then the system checks the resume against the job requirements.
2. Given a skill in the resume has a close or related meaning to a job requirement, when the comparison is performed, then the relationship is considered appropriately.
3. Given the comparison is complete, when the results are shown, then the main matching and missing areas are clearly displayed.

---

### US-11 — View Suitable Job or Internship Matches

**Requirement ID(s):** FR-09, DR-02 | **Type:** Functional + Domain | **Role:** Student / Job Seeker | **Priority:** Must Have | **Source:** Survey, Recruiter Interview

**Front of Card**

> As a student, I want to see job or internship opportunities that match my profile, so that I can identify opportunities that are relevant to my skills.

**Back of Card — Acceptance Criteria**

1. Given the student's resume has been analysed, when job matching is requested, then relevant job or internship opportunities are displayed.
2. Given multiple opportunities are available, when the results are shown, then they are presented according to their relevance to the student's profile.
3. Given no suitable match is found, when the student views the results, then the system clearly informs them instead of showing unrelated opportunities.

---

### US-12 — View Matching and Missing Skills

**Requirement ID(s):** FR-10, DR-03, DR-04 | **Type:** Functional + Domain | **Role:** Student / Job Seeker | **Priority:** Must Have | **Source:** Recruiter Interview, Document Analysis

**Front of Card**

> As a student, I want to see which skills match a selected job and which skills are missing, so that I can decide what to improve or highlight.

**Back of Card — Acceptance Criteria**

1. Given a student selects a specific job, when the skill comparison is shown, then matching and missing skills are listed separately.
2. Given the job description distinguishes required and preferred skills, when missing skills are shown, then they are labelled accordingly.
3. Given a missing skill has a close equivalent already present in the student's resume, when the results are shown, then the related skill is indicated instead of simply marking it as missing.

---

### US-13 — View Authorized Student Resume Analysis

**Requirement ID(s):** FR-12 | **Type:** Functional | **Role:** Placement Cell / Placement Officers, Faculty / Career Counselors | **Priority:** Should Have | **Source:** Placement Officer Interview, Faculty Interview

**Front of Card**

> As a placement officer or career counselor, I want to view a student's resume analysis when I am authorized to do so, so that I can guide the student and discuss the results with them.

**Back of Card — Acceptance Criteria**

1. Given a placement officer or counselor has the required access, when they open a student's record, then the student's resume analysis, score and suggestions are available.
2. Given a staff member does not have permission to view a student's data, when they try to access it, then access is denied.
3. Given a counselor views a student's analysis, when they discuss the result with the student, then the explanation is clear enough to support the discussion.

---

### US-14 — View Placement Dashboards and Reports

**Requirement ID(s):** FR-13, DR-05 | **Type:** Functional + Domain | **Role:** Placement Cell / Placement Officers | **Priority:** Should Have | **Source:** Placement Interview, Workshop, Placement Documents

**Front of Card**

> As a placement officer, I want to view summary information from resume analyses across students, so that I can identify common problems and plan placement support accordingly.

**Back of Card — Acceptance Criteria**

1. Given multiple students have completed resume analysis, when a placement officer opens the dashboard, then useful summary information such as common weak areas and average scores is displayed.
2. Given the dashboard contains student-related information, when it is displayed, then sensitive individual information is protected.
3. Given the dashboard includes placement-related information, when it is shown, then it follows the college's defined placement rules.

---

### US-15 — Enforce Role-Based Access to Student Data

**Requirement ID(s):** FR-15, NFR-07, DR-07 | **Type:** Functional + Non-Functional + Domain | **Role:** System Administrator | **Priority:** Must Have | **Source:** Privacy / System Admin Discussion

**Front of Card**

> As a system administrator, I want access to student and resume information to depend on the user's role, so that users can access only the data and features they are permitted to use.

**Back of Card — Acceptance Criteria**

1. Given different user roles are defined, when a user accesses the system, then only the features and data allowed for that role are available.
2. Given a user does not have permission to view another student's resume, when they try to access it, then access is denied.
3. Given an administrator changes a user's role or permissions, when that user accesses the system again, then the updated permissions are applied.

---

### US-16 — Protect and Minimise Exposure of Resume Data

**Requirement ID(s):** NFR-03, NFR-09, DR-08 | **Type:** Non-Functional + Domain | **Role:** Data Privacy Reviewer | **Priority:** Must Have | **Source:** Privacy Discussion, Policy Analysis

**Front of Card**

> As a data privacy reviewer, I want resume and personal information to be protected and only the necessary information to be shown, so that student data is handled safely.

**Back of Card — Acceptance Criteria**

1. Given resume data is stored, when an access attempt is made, then only authenticated and authorized users can retrieve it.
2. Given a screen or report displays student information, when it is generated, then only the information needed for that purpose is shown.
3. Given the college has rules for data handling, consent and retention, when resume data is stored or processed, then the system follows those rules.

---

### US-17 — Keep Automated Results as Recommendations

**Requirement ID(s):** DR-06 | **Type:** Domain | **Role:** Hiring Manager / Placement Officer / Recruiter | **Priority:** Must Have | **Source:** Placement / Recruiter Discussion

**Front of Card**

> As a hiring manager, I want the system's scores, matches and recommendations to support my decision rather than make it for me, so that the final placement or hiring decision remains with a human.

**Back of Card — Acceptance Criteria**

1. Given a student receives a low score or poor job match, when the result is displayed, then the system does not automatically reject or shortlist the student.
2. Given a hiring manager or placement officer views a recommendation, when they review it, then it is shown as supporting information rather than a final decision.
3. Given a student disagrees with an automated result, when the result is reviewed, then an authorized human can make the final decision.

---

### US-18 — Review Scoring and Matching for Fairness

**Requirement ID(s):** DR-09 | **Type:** Domain | **Role:** Bias / Fairness Reviewer | **Priority:** Must Have | **Source:** Fairness Discussion

**Front of Card**

> As a fairness reviewer, I want the scoring and matching process to be checked for unfair factors, so that irrelevant personal characteristics do not unnecessarily affect the results.

**Back of Card — Acceptance Criteria**

1. Given the scoring and matching rules are defined, when they are reviewed, then the factors used in the results can be identified.
2. Given two test resumes differ only in an irrelevant characteristic, when they are analysed, then there should be no unjustified difference in their results.
3. Given a fairness issue is identified, when it is reported, then it is recorded and tracked for review by the development team.

---

### US-19 — Keep Core Components Maintainable

**Requirement ID(s):** NFR-10 | **Type:** Non-Functional | **Role:** Development Team | **Priority:** Should Have | **Source:** Brainstorming

**Front of Card**

> As a member of the development team, I want the parsing, scoring and matching parts of the system to be easy to maintain, so that we can update or fix one part without unnecessarily affecting the rest of the system.

**Back of Card — Acceptance Criteria**

1. Given parsing, scoring and matching are separate components, when one component needs to be changed, then the other components should continue to work normally.
2. Given a component is modified, when the system is tested, then unrelated functionality should continue to work as before.
3. Given a new team member joins the project, when they review the component structure, then the responsibility of each component should be clear from the project documentation.

---

## 4. User Story Summary

| User Story | Main User | Priority |
|---|---|---|
| US-01 — Upload Resume | Student / Job Seeker | Must Have |
| US-02 — Parse Uploaded Resume | Student / Job Seeker | Must Have |
| US-03 — Handle Invalid or Unsupported Resume Input | Student / Job Seeker | Must Have |
| US-04 — Extract Skills from Resume | Student / Job Seeker | Must Have |
| US-05 — Analyse Resume Against Placement Criteria | Student / Job Seeker | Must Have |
| US-06 — View Resume Score | Student / Job Seeker | Must Have |
| US-07 — Identify Resume Improvement Areas | Student / Job Seeker | Must Have |
| US-08 — Get Resume Improvement Suggestions | Student / Job Seeker | Must Have |
| US-09 — Understand Score and Recommendations | Student / Job Seeker | Must Have |
| US-10 — Compare Resume with Job Requirements | Student / Job Seeker | Must Have |
| US-11 — View Suitable Job or Internship Matches | Student / Job Seeker | Must Have |
| US-12 — View Matching and Missing Skills | Student / Job Seeker | Must Have |
| US-13 — View Authorized Student Resume Analysis | Placement Staff / Counselor | Should Have |
| US-14 — View Placement Dashboards and Reports | Placement Officer | Should Have |
| US-15 — Enforce Role-Based Access | System Administrator | Must Have |
| US-16 — Protect and Minimise Exposure of Resume Data | Data Privacy Reviewer | Must Have |
| US-17 — Keep Automated Results as Recommendations | Recruiter / Placement Officer | Must Have |
| US-18 — Review Scoring and Matching for Fairness | Fairness Reviewer | Must Have |
| US-19 — Keep Core Components Maintainable | Development Team | Should Have |
