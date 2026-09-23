# User Stories – Resume Analyser for College Placements

The following user stories are prepared from the requirements collected during the elicitation process. Each story describes what a user expects from the system and why the feature is useful. The acceptance criteria define the expected behaviour of the system.

---

## 3. User Story Cards

### US-01 — Upload Resume

**Requirement ID(s):** FR-01 (NFR-01 as AC) | **Type:** Functional | **Role:** Student / Job Seeker | **Priority:** Must Have | **Source:** Survey, Observation

**Front of Card**

> As a student, I want to upload my resume to the system, so that I can have it analysed and get useful feedback.

**Back of Card — Acceptance Criteria**

1. **Given** the student is on the resume upload page, **when** a supported resume file is selected, **then** the system should accept the file and confirm the upload.
2. **Given** the resume is being uploaded, **when** the upload is in progress, **then** the system should show the current upload status.
3. **Given** the upload is successful, **when** processing begins, **then** the student should be able to continue to the analysis stage.

---

### US-02 — Parse Uploaded Resume

**Requirement ID(s):** FR-02 | **Type:** Functional | **Role:** Student / Job Seeker | **Priority:** Must Have | **Source:** Interview, Brainstorming

**Front of Card**

> As a student, I want the system to read and organise the information in my uploaded resume, so that it can be used for further analysis.

**Back of Card — Acceptance Criteria**

1. **Given** a supported resume has been uploaded, **when** processing starts, **then** the system should identify important sections such as education, skills, projects and experience.
2. **Given** the resume has been processed, **when** the extracted information is displayed, **then** the student should be able to review the main details.
3. **Given** some information cannot be read properly, **when** processing is completed, **then** the system should indicate the unclear information where possible.

---

### US-03 — Handle Invalid Resume

**Requirement ID(s):** FR-14 (NFR-06 as AC) | **Type:** Functional | **Role:** Student / Job Seeker | **Priority:** Must Have | **Source:** Observation, Prototype

**Front of Card**

> As a student, I want to know when my resume cannot be processed, so that I can fix the problem and try again.

**Back of Card — Acceptance Criteria**

1. **Given** the uploaded file is not supported, **when** the system validates it, **then** the upload should be rejected with a clear message.
2. **Given** the uploaded file is empty, corrupted or unreadable, **when** processing fails, **then** the system should explain the problem.
3. **Given** an invalid file was rejected, **when** the student selects a valid file, **then** the system should allow the upload process to continue.

---

### US-04 — Extract Skills from Resume

**Requirement ID(s):** FR-03 | **Type:** Functional | **Role:** Student / Job Seeker | **Priority:** Must Have | **Source:** Survey, Recruiter Interview

**Front of Card**

> As a student, I want the system to identify the skills mentioned in my resume, so that I can understand which skills are considered during the analysis.

**Back of Card — Acceptance Criteria**

1. **Given** the resume has been processed, **when** skill extraction is performed, **then** relevant skills mentioned in the resume should be identified.
2. **Given** skills are mentioned in different sections, **when** the system extracts skills, **then** relevant skills from those sections should also be considered.
3. **Given** skill extraction is complete, **when** the student views the result, **then** the identified skills should be displayed clearly.

---

### US-05 — Analyse Resume for Placement Preparation

**Requirement ID(s):** FR-04, DR-01 | **Type:** Functional + Domain | **Role:** Student / Job Seeker | **Priority:** Must Have | **Source:** Survey, Interview, Placement Discussion

**Front of Card**

> As a student, I want my resume to be analysed using placement-related criteria, so that I can understand how well it is prepared for college placement opportunities.

**Back of Card — Acceptance Criteria**

1. **Given** the resume has been uploaded and processed, **when** analysis starts, **then** the system should evaluate it using the defined placement criteria.
2. **Given** the analysis is running, **when** the student waits for the result, **then** the system should complete the analysis within the expected response time.
3. **Given** the same resume and analysis criteria are used again, **then** the system should produce consistent results.

---

### US-06 — Get an Overall Resume Score

**Requirement ID(s):** FR-05 (NFR-04, NFR-08 as AC) | **Type:** Functional | **Role:** Student / Job Seeker | **Priority:** Must Have | **Source:** Survey, Interview

**Front of Card**

> As a student, I want to see an overall score for my resume, so that I can quickly understand its current performance.

**Back of Card — Acceptance Criteria**

1. **Given** resume analysis is complete, **when** the student opens the results, **then** an overall resume score should be displayed.
2. **Given** the same resume and analysis criteria are used, **when** the score is calculated again, **then** the result should remain consistent.
3. **Given** a score is displayed, **when** the student reviews it, **then** supporting feedback should also be available.

---

### US-07 — Identify Areas That Need Improvement

**Requirement ID(s):** FR-06 (NFR-08 as AC) | **Type:** Functional | **Role:** Student / Job Seeker | **Priority:** Must Have | **Source:** Survey, Observation

**Front of Card**

> As a student, I want the system to highlight weak or missing areas in my resume, so that I know where I should focus my improvements.

**Back of Card — Acceptance Criteria**

1. **Given** the resume has been analysed, **when** the results are displayed, **then** important weak or missing areas should be highlighted.
2. **Given** multiple issues are found, **when** the results are shown, **then** the main areas requiring attention should be easy to identify.
3. **Given** an area does not have a significant issue, **then** it should not be unnecessarily presented as a weakness.

---

### US-08 — Get Resume Improvement Suggestions

**Requirement ID(s):** FR-07 (NFR-05 as AC) | **Type:** Functional | **Role:** Student / Job Seeker | **Priority:** Must Have | **Source:** Survey, Faculty Interview

**Front of Card**

> As a student, I want to receive useful suggestions for improving my resume, so that I can make specific changes based on the analysis.

**Back of Card — Acceptance Criteria**

1. **Given** improvement areas have been identified, **when** the analysis results are shown, **then** relevant suggestions should be provided.
2. **Given** a suggestion is displayed, **when** the student reads it, **then** it should be clear and easy to understand.
3. **Given** a particular section or skill needs improvement, **when** a suggestion is generated, **then** it should be related to that issue.

---

### US-09 — Understand the Score and Recommendations

**Requirement ID(s):** FR-11 (NFR-05 as AC) | **Type:** Functional | **Role:** Student / Job Seeker | **Priority:** Must Have | **Source:** Faculty Interview, Prototype

**Front of Card**

> As a student, I want to understand why I received a particular score or recommendation, so that I know what led to the result and what I can improve.

**Back of Card — Acceptance Criteria**

1. **Given** a score or recommendation is displayed, **when** the student views its details, **then** the main reasons behind it should be shown.
2. **Given** an explanation is provided, **when** the student reads it, **then** it should be understandable without technical knowledge.
3. **Given** the system cannot properly explain a result, **then** it should provide suitable context instead of presenting it as an unexplained conclusion.

---

### US-10 — Compare Resume with a Job Description

**Requirement ID(s):** FR-08, DR-02, DR-04 | **Type:** Functional + Domain | **Role:** Student / Job Seeker | **Priority:** Must Have | **Source:** Recruiter Interview, Document Analysis

**Front of Card**

> As a student, I want to compare my resume with a specific job description, so that I can understand how well my profile matches the role.

**Back of Card — Acceptance Criteria**

1. **Given** the student provides a job description, **when** the comparison starts, **then** the system should compare the resume with the stated job requirements.
2. **Given** a resume skill is closely related to a job requirement, **when** the comparison is performed, **then** the relationship should be considered appropriately.
3. **Given** the comparison is complete, **when** the results are displayed, **then** the main matching and missing areas should be clearly shown.

---

### US-11 — Find Relevant Job or Internship Opportunities

**Requirement ID(s):** FR-09, DR-02 | **Type:** Functional + Domain | **Role:** Student / Job Seeker | **Priority:** Must Have | **Source:** Survey, Recruiter Interview

**Front of Card**

> As a student, I want to find job or internship opportunities that match my profile, so that I can focus on opportunities relevant to my skills.

**Back of Card — Acceptance Criteria**

1. **Given** the student's resume has been analysed, **when** job matching is requested, **then** relevant job or internship opportunities should be displayed.
2. **Given** several opportunities are available, **when** the results are shown, **then** they should be organised according to their relevance.
3. **Given** no suitable opportunity is found, **when** the student views the results, **then** the system should clearly inform them.

---

### US-12 — View Matching and Missing Skills

**Requirement ID(s):** FR-10, DR-03, DR-04 | **Type:** Functional + Domain | **Role:** Student / Job Seeker | **Priority:** Must Have | **Source:** Recruiter Interview, Document Analysis

**Front of Card**

> As a student, I want to see which skills match a selected job and which skills are missing, so that I can decide what to improve before applying.

**Back of Card — Acceptance Criteria**

1. **Given** a student selects a job, **when** skill comparison is completed, **then** matching and missing skills should be shown separately.
2. **Given** the job description contains required and preferred skills, **when** the comparison results are displayed, **then** they should be distinguished where possible.
3. **Given** a related skill is already present in the resume, **when** the comparison is performed, **then** it should be shown as a related skill rather than simply being marked as missing.

---

### US-13 — View Student Resume Analysis

**Requirement ID(s):** FR-12 | **Type:** Functional | **Role:** Placement Cell / Placement Officers, Faculty / Career Counselors | **Priority:** Should Have | **Source:** Placement Officer Interview, Faculty Interview

**Front of Card**

> As a placement officer or career counselor, I want to view a student's resume analysis when I am authorized to do so, so that I can provide more useful guidance.

**Back of Card — Acceptance Criteria**

1. **Given** the staff member has the required permission, **when** they open a student's record, **then** the relevant resume analysis should be available.
2. **Given** the staff member is not authorized, **when** they try to access the student's information, **then** access should be denied.
3. **Given** the analysis is available to an authorized counselor, **when** it is reviewed, **then** the score, identified issues and suggestions should be understandable.

---

### US-14 — View Placement Dashboard and Reports

**Requirement ID(s):** FR-13, DR-05 | **Type:** Functional + Domain | **Role:** Placement Cell / Placement Officers | **Priority:** Should Have | **Source:** Placement Interview, Workshop, Placement Documents

**Front of Card**

> As a placement officer, I want to view summary information from student resume analyses, so that I can identify common problems and plan placement support.

**Back of Card — Acceptance Criteria**

1. **Given** multiple students have completed resume analysis, **when** the placement officer opens the dashboard, **then** useful summary information should be available.
2. **Given** the dashboard contains student-related information, **when** it is displayed, **then** sensitive personal information should be protected.
3. **Given** placement information is presented, **then** it should follow the rules defined by the institution.

---

### US-15 — Manage Role-Based Access

**Requirement ID(s):** FR-15, NFR-07, DR-07 | **Type:** Functional + Non-Functional + Domain | **Role:** System Administrator | **Priority:** Must Have | **Source:** Privacy / System Admin Discussion

**Front of Card**

> As a system administrator, I want access to system features and student information to depend on the user's role, so that users can access only what they are permitted to use.

**Back of Card — Acceptance Criteria**

1. **Given** different user roles are defined, **when** a user logs in, **then** the system should provide access according to that role.
2. **Given** a user does not have permission to view a student's resume, **when** they try to access it, **then** access should be denied.
3. **Given** an administrator updates a user's role or permissions, **when** the user accesses the system again, **then** the updated permissions should be applied.

---

### US-16 — Protect Student Resume Data

**Requirement ID(s):** NFR-03, NFR-09, DR-08 | **Type:** Non-Functional + Domain | **Role:** Data Privacy Reviewer | **Priority:** Must Have | **Source:** Privacy Discussion, Policy Analysis

**Front of Card**

> As a data privacy reviewer, I want student resumes and personal information to be protected, so that sensitive information is not unnecessarily exposed.

**Back of Card — Acceptance Criteria**

1. **Given** resume data is stored, **when** an access request is made, **then** only authorized users should be able to access it.
2. **Given** student information is displayed in a screen or report, **when** it is shown, **then** only the information required for that purpose should be visible.
3. **Given** the institution has defined rules for data handling and retention, **when** resume data is processed, **then** those rules should be followed.

---

### US-17 — Keep Automated Results as Supporting Information

**Requirement ID(s):** DR-06 | **Type:** Domain | **Role:** Hiring Manager / Placement Officer / Recruiter | **Priority:** Must Have | **Source:** Placement / Recruiter Discussion

**Front of Card**

> As a hiring manager, I want the system's scores and recommendations to support my decision, so that the final placement or hiring decision remains with a human.

**Back of Card — Acceptance Criteria**

1. **Given** a student receives a low score or poor job match, **when** the result is displayed, **then** the system should not automatically reject the student.
2. **Given** a recruiter or placement officer reviews a recommendation, **when** they view the result, **then** it should be presented as supporting information rather than a final decision.
3. **Given** an automated result needs further review, **when** an authorized person evaluates it, **then** the final decision can be made by that person.

---

### US-18 — Check Scoring and Matching for Fairness

**Requirement ID(s):** DR-09 | **Type:** Domain | **Role:** Bias / Fairness Reviewer | **Priority:** Must Have | **Source:** Fairness Discussion

**Front of Card**

> As a fairness reviewer, I want the scoring and matching process to be checked for unfair factors, so that irrelevant personal characteristics do not unnecessarily affect the results.

**Back of Card — Acceptance Criteria**

1. **Given** the scoring and matching rules are defined, **when** they are reviewed, **then** the factors used by the system should be identifiable.
2. **Given** two test resumes differ only in an irrelevant characteristic, **when** they are analysed, **then** there should not be an unjustified difference in their results.
3. **Given** a possible fairness issue is found, **when** it is reported, **then** it should be recorded for further review.

---

### US-19 — Keep Core Components Maintainable

**Requirement ID(s):** NFR-10 | **Type:** Non-Functional | **Role:** Development Team | **Priority:** Should Have | **Source:** Brainstorming

**Front of Card**

> As a member of the development team, I want the main components of the system to be easy to maintain, so that changes or fixes can be made without unnecessarily affecting other parts.

**Back of Card — Acceptance Criteria**

1. **Given** parsing, scoring and matching are separate components, **when** one component is changed, **then** the other components should continue to work normally.
2. **Given** a component has been modified, **when** the system is tested, **then** unrelated features should continue to work as expected.
3. **Given** a new team member joins the project, **when** they review the code and documentation, **then** the purpose of the main components should be clear.

---

## 4. User Story Summary

| ID | User Story | Role | Priority |
|---|---|---|---|
| US-01 | Upload Resume | Student / Job Seeker | Must Have |
| US-02 | Parse Uploaded Resume | Student / Job Seeker | Must Have |
| US-03 | Handle Invalid Resume | Student / Job Seeker | Must Have |
| US-04 | Extract Skills from Resume | Student / Job Seeker | Must Have |
| US-05 | Analyse Resume for Placement Preparation | Student / Job Seeker | Must Have |
| US-06 | Get an Overall Resume Score | Student / Job Seeker | Must Have |
| US-07 | Identify Areas That Need Improvement | Student / Job Seeker | Must Have |
| US-08 | Get Resume Improvement Suggestions | Student / Job Seeker | Must Have |
| US-09 | Understand the Score and Recommendations | Student / Job Seeker | Must Have |
| US-10 | Compare Resume with a Job Description | Student / Job Seeker | Must Have |
| US-11 | Find Relevant Job or Internship Opportunities | Student / Job Seeker | Must Have |
| US-12 | View Matching and Missing Skills | Student / Job Seeker | Must Have |
| US-13 | View Student Resume Analysis | Placement Staff / Counselor | Should Have |
| US-14 | View Placement Dashboard and Reports | Placement Officer | Should Have |
| US-15 | Manage Role-Based Access | System Administrator | Must Have |
| US-16 | Protect Student Resume Data | Data Privacy Reviewer | Must Have |
| US-17 | Keep Automated Results as Supporting Information | Recruiter / Placement Officer | Must Have |
| US-18 | Check Scoring and Matching for Fairness | Fairness Reviewer | Must Have |
| US-19 | Keep Core Components Maintainable | Development Team | Should Have |
