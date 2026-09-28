# User Stories – Resume Analyser for College Placements

## 3. User Story Cards

### US-01 – User Login and Account Access

**Requirement ID(s):** FR-16  
**Type:** Functional Requirement  
**Role:** Student / Job Seeker  
**Priority:** Must Have  
**Source:** System Access Requirements  

#### Front of Card

> As a student/job seeker, I want to log in to the system, so that I can securely access my resume analysis and related features.

#### Back of Card — Acceptance Criteria

1. Given valid login credentials, when the user logs in, then access should be granted.
2. Given invalid credentials, when the user tries to log in, then an appropriate error message should be shown.
3. The system should show features according to the user's role.
4. The user should be able to log out securely.

---

### US-02 – Upload Resume

**Requirement ID(s):** FR-01, NFR-01  
**Type:** Functional Requirement  
**Role:** Student / Job Seeker  
**Priority:** Must Have  
**Source:** Survey, Observation  

#### Front of Card

> As a student/job seeker, I want to upload my resume, so that the system can analyse it.

#### Back of Card — Acceptance Criteria

1. Given a supported resume file, when the user uploads it, then the system should accept the file.
2. The system should show the upload status clearly.
3. After a successful upload, the user should be able to continue to resume analysis.

---

### US-03 – Parse Uploaded Resume

**Requirement ID(s):** FR-02  
**Type:** Functional Requirement  
**Role:** Student / Job Seeker  
**Priority:** Must Have  
**Source:** Interview, Brainstorming  

#### Front of Card

> As a student/job seeker, I want the system to extract information from my resume, so that I do not have to enter the information manually.

#### Back of Card — Acceptance Criteria

1. The system should identify information such as education, skills, projects, and experience where available.
2. Extracted information should be organized into understandable sections.
3. The system should indicate information that could not be read or extracted properly.

---

### US-04 – Handle Invalid Resume

**Requirement ID(s):** FR-14, NFR-06  
**Type:** Functional Requirement  
**Role:** Student / Job Seeker  
**Priority:** Must Have  
**Source:** Observation, Prototype  

#### Front of Card

> As a student/job seeker, I want to know when my resume cannot be processed, so that I can correct the problem and try again.

#### Back of Card — Acceptance Criteria

1. The system should reject unsupported, empty, corrupted, or unreadable files.
2. A clear error message should be displayed.
3. The user should be given an option to upload another file.

---

### US-05 – Extract Skills from Resume

**Requirement ID(s):** FR-03  
**Type:** Functional Requirement  
**Role:** Student / Job Seeker  
**Priority:** Must Have  
**Source:** Survey, Recruiter Discussion  

#### Front of Card

> As a student/job seeker, I want the system to identify skills from my resume, so that I can understand which skills are visible in my resume.

#### Back of Card — Acceptance Criteria

1. The system should identify relevant technical and non-technical skills where possible.
2. Skills should be identified from relevant resume sections.
3. Extracted skills should be displayed clearly to the user.

---

### US-06 – Analyse Resume for Placement Preparation

**Requirement ID(s):** FR-04, DR-01  
**Type:** Functional Requirement  
**Role:** Student / Job Seeker  
**Priority:** Must Have  
**Source:** Survey, Interview, Placement Discussion  

#### Front of Card

> As a student/job seeker, I want my resume to be analysed against placement-related criteria, so that I can understand its strengths and weaknesses.

#### Back of Card — Acceptance Criteria

1. The system should evaluate the resume using defined analysis criteria.
2. The analysis result should be shown clearly.
3. The system should provide consistent results when the same resume and criteria are used.

---

### US-07 – Get an Overall Resume Score

**Requirement ID(s):** FR-05, NFR-04, NFR-08  
**Type:** Functional Requirement  
**Role:** Student / Job Seeker  
**Priority:** Must Have  
**Source:** Survey, Interview  

#### Front of Card

> As a student/job seeker, I want an overall resume score, so that I can quickly understand how well my resume meets the defined criteria.

#### Back of Card — Acceptance Criteria

1. The system should display an overall resume score.
2. The score should be calculated using defined evaluation criteria.
3. Recalculating the same resume using the same criteria should produce consistent results.
4. The score should be supported by useful information rather than being shown alone.

---

### US-08 – Identify Areas That Need Improvement

**Requirement ID(s):** FR-06, NFR-08  
**Type:** Functional Requirement  
**Role:** Student / Job Seeker  
**Priority:** Must Have  
**Source:** Survey, Observation  

#### Front of Card

> As a student/job seeker, I want to know which areas of my resume need improvement, so that I can focus on the most important changes.

#### Back of Card — Acceptance Criteria

1. The system should highlight weak or missing areas where applicable.
2. Important improvement areas should be clearly distinguishable.
3. The system should not incorrectly identify a properly included section as a missing or weak area.

---

### US-09 – Get Resume Improvement Suggestions

**Requirement ID(s):** FR-07, NFR-05  
**Type:** Functional Requirement  
**Role:** Student / Job Seeker  
**Priority:** Must Have  
**Source:** Survey, Faculty Interview  

#### Front of Card

> As a student/job seeker, I want suggestions for improving my resume, so that I can make relevant changes before applying for placements.

#### Back of Card — Acceptance Criteria

1. The system should provide suggestions related to identified issues.
2. Suggestions should be clear and understandable.
3. Suggestions should be relevant to the resume content and identified improvement areas.

---

### US-10 – Understand the Score and Recommendations

**Requirement ID(s):** FR-11, NFR-05  
**Type:** Functional Requirement  
**Role:** Student / Job Seeker  
**Priority:** Must Have  
**Source:** Faculty Interview, Prototype  

#### Front of Card

> As a student/job seeker, I want to understand why a score or recommendation was given, so that I can decide what changes to make.

#### Back of Card — Acceptance Criteria

1. The system should show the main reasons behind the score or recommendation.
2. Explanations should use simple and understandable language.
3. The system should provide suitable context when an explanation may not be reliable.

---

### US-11 – Compare Resume with a Job Description

**Requirement ID(s):** FR-08, DR-02, DR-04  
**Type:** Functional Requirement  
**Role:** Student / Job Seeker  
**Priority:** Must Have  
**Source:** Recruiter Discussion, Document Analysis  

#### Front of Card

> As a student/job seeker, I want to compare my resume with a job description, so that I can understand how well my profile matches the opportunity.

#### Back of Card — Acceptance Criteria

1. The system should compare resume information with the requirements stated in the job description.
2. Related or equivalent skills should be considered where appropriate.
3. The system should show matching and missing requirements clearly.

---

### US-12 – Find Relevant Job or Internship Opportunities

**Requirement ID(s):** FR-09, DR-02  
**Type:** Functional Requirement  
**Role:** Student / Job Seeker  
**Priority:** Must Have  
**Source:** Survey, Recruiter Discussion  

#### Front of Card

> As a student/job seeker, I want to see relevant job or internship opportunities, so that I can identify opportunities that match my profile.

#### Back of Card — Acceptance Criteria

1. The system should display opportunities relevant to the user's profile where data is available.
2. Opportunities should be organized based on their relevance.
3. If no suitable opportunity is found, the system should clearly inform the user.

---

### US-13 – View Matching and Missing Skills

**Requirement ID(s):** FR-10, DR-03, DR-04  
**Type:** Functional Requirement  
**Role:** Student / Job Seeker  
**Priority:** Must Have  
**Source:** Recruiter Discussion, Document Analysis  

#### Front of Card

> As a student/job seeker, I want to see matching and missing skills for a job, so that I can understand what I already have and what I need to improve.

#### Back of Card — Acceptance Criteria

1. Matching and missing skills should be shown separately.
2. Required and preferred skills should be distinguished where the job description provides this information.
3. Related skills should be handled appropriately instead of being treated as completely unrelated skills.

---

### US-14 – View Student Resume Analysis

**Requirement ID(s):** FR-12  
**Type:** Functional Requirement  
**Role:** Placement Cell / Placement Officer, Faculty / Career Counselor  
**Priority:** Should Have  
**Source:** Placement Officer Interview, Faculty Interview  

#### Front of Card

> As a placement officer or career counselor, I want to view student resume analysis, so that I can support students during placement preparation.

#### Back of Card — Acceptance Criteria

1. Only authorized staff should be able to view student analysis.
2. Unauthorized users should not be able to access student resume information.
3. The analysis should be presented in an understandable format.

---

### US-15 – View Placement Dashboard and Reports

**Requirement ID(s):** FR-13, DR-05  
**Type:** Functional Requirement  
**Role:** Placement Officer  
**Priority:** Should Have  
**Source:** Placement Interview, Workshop, Placement Documents  

#### Front of Card

> As a placement officer, I want to view placement-related summaries and reports, so that I can understand overall student placement preparation.

#### Back of Card — Acceptance Criteria

1. The dashboard should provide useful summary information.
2. Sensitive personal information should not be unnecessarily exposed.
3. Reports should follow applicable institutional rules for student data.

---

### US-16 – Manage Role-Based Access

**Requirement ID(s):** FR-15, NFR-07, DR-07  
**Type:** Functional Requirement  
**Role:** System Administrator  
**Priority:** Must Have  
**Source:** Privacy / System Admin Discussion  

#### Front of Card

> As a system administrator, I want to manage role-based access, so that users can access only the features and data allowed for their role.

#### Back of Card — Acceptance Criteria

1. The system should provide different access levels for different roles.
2. Unauthorized users should be prevented from accessing restricted student resume data.
3. Changes to user permissions should be applied correctly.

---

### US-17 – Protect Student Resume Data

**Requirement ID(s):** NFR-03, NFR-09, DR-08  
**Type:** Non-Functional Requirement  
**Role:** Data Privacy Reviewer  
**Priority:** Must Have  
**Source:** Privacy Discussion, Policy Analysis  

#### Front of Card

> As a data privacy reviewer, I want student resume data to be protected, so that personal information is handled securely and only when required.

#### Back of Card — Acceptance Criteria

1. Only authorized users should be able to access protected resume information.
2. The system should display only the information necessary for a particular task.
3. Data handling and retention should follow defined privacy rules.

---

### US-18 – Keep Automated Results as Supporting Information

**Requirement ID(s):** DR-06  
**Type:** Domain Requirement  
**Role:** Hiring Manager / Placement Officer / Recruiter  
**Priority:** Must Have  
**Source:** Placement / Recruiter Discussion  

#### Front of Card

> As a placement or recruitment decision-maker, I want automated analysis to act as supporting information, so that final decisions remain under human control.

#### Back of Card — Acceptance Criteria

1. The system should not automatically reject a candidate only because of an automated score.
2. Automated results should be presented as supporting information.
3. Final placement or recruitment decisions should remain with the responsible human decision-maker.

---

### US-19 – Check Scoring and Matching for Fairness

**Requirement ID(s):** DR-09  
**Type:** Domain Requirement  
**Role:** Fairness Reviewer  
**Priority:** Must Have  
**Source:** Fairness Discussion  

#### Front of Card

> As a fairness reviewer, I want scoring and matching factors to be reviewable, so that the system can be checked for unfair or unjustified results.

#### Back of Card — Acceptance Criteria

1. The main factors used for scoring and matching should be identifiable.
2. The system should avoid unjustified differences based on characteristics that are not relevant to the job requirements.
3. Potential fairness issues should be recorded for review.

---

### US-20 – Keep Core Components Maintainable

**Requirement ID(s):** NFR-10  
**Type:** Non-Functional Requirement  
**Role:** Development Team  
**Priority:** Should Have  
**Source:** Brainstorming  

#### Front of Card

> As a developer, I want the main system components to be organized separately, so that the system can be updated and maintained more easily.

#### Back of Card — Acceptance Criteria

1. Resume parsing, scoring, and job matching should be organized as separate components.
2. Changes to one component should not unnecessarily affect unrelated features.
3. The code and basic documentation should be understandable for future development.

---

## 4. User Story Summary

| User Story | Main Requirement | Role | Priority |
|---|---|---|---|
| US-01 | User Login and Account Access | Student / Job Seeker | Must Have |
| US-02 | Upload Resume | Student / Job Seeker | Must Have |
| US-03 | Parse Uploaded Resume | Student / Job Seeker | Must Have |
| US-04 | Handle Invalid Resume | Student / Job Seeker | Must Have |
| US-05 | Extract Skills from Resume | Student / Job Seeker | Must Have |
| US-06 | Analyse Resume for Placement Preparation | Student / Job Seeker | Must Have |
| US-07 | Get an Overall Resume Score | Student / Job Seeker | Must Have |
| US-08 | Identify Areas That Need Improvement | Student / Job Seeker | Must Have |
| US-09 | Get Resume Improvement Suggestions | Student / Job Seeker | Must Have |
| US-10 | Understand the Score and Recommendations | Student / Job Seeker | Must Have |
| US-11 | Compare Resume with a Job Description | Student / Job Seeker | Must Have |
| US-12 | Find Relevant Job or Internship Opportunities | Student / Job Seeker | Must Have |
| US-13 | View Matching and Missing Skills | Student / Job Seeker | Must Have |
| US-14 | View Student Resume Analysis | Placement Cell / Career Counselor | Should Have |
| US-15 | View Placement Dashboard and Reports | Placement Officer | Should Have |
| US-16 | Manage Role-Based Access | System Administrator | Must Have |
| US-17 | Protect Student Resume Data | Data Privacy Reviewer | Must Have |
| US-18 | Keep Automated Results as Supporting Information | Hiring Manager / Placement Officer / Recruiter | Must Have |
| US-19 | Check Scoring and Matching for Fairness | Fairness Reviewer | Must Have |
| US-20 | Keep Core Components Maintainable | Development Team | Should Have |
