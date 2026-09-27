# 6. Identify and Resolve Conflicts

## 6.1 Purpose

Requirements collected from different stakeholders may not always agree with each other. For this project, the main conflicts were identified by comparing stakeholder needs, requirements, and user stories.

Each conflict is recorded using the following structure:

**Stakeholders Involved → Conflicting Needs → Why It's a Conflict → Resolution → Requirements/User Stories Affected**

---

## 6.2 Conflict Log

### C-01 — Detailed Feedback vs. Processing Time

**Stakeholders:** Students vs. Students / Recruiters

**Conflicting Needs:**

- Students want clear explanations for their resume score and recommendations.
- Students and recruiters also expect the analysis to complete within a reasonable time.

**Why It's a Conflict:**

Providing more detailed explanations can require additional processing. If the system tries to show a detailed explanation for every result immediately, it may increase the time required to generate the result.

**Resolution:**

The system should show a short explanation along with the main result. More detailed information can be shown when the user asks for it, for example through a "Why this score?" option. This keeps the main result simple while still providing additional details when required.

**Affects:** US-06, US-09, FR-05, FR-11, NFR-02, NFR-05

---

### C-02 — Staff Access vs. Student Data Privacy

**Stakeholders:** Placement Officers / Faculty Counselors vs. Data Privacy Reviewer

**Conflicting Needs:**

- Placement officers and counselors need access to student resume analysis for guidance and placement-related activities.
- Student resume and personal information should only be visible to authorised users and only when required.

**Why It's a Conflict:**

Providing staff with more student information can make counselling easier, but unnecessary access to personal information can create privacy concerns.

**Resolution:**

Role-based access will be used so that users can access only the information allowed for their role. Individual student information should be available only to authorised staff. Placement dashboards should mainly provide summary information where individual resume details are not required.

**Affects:** US-13, US-14, US-15, US-16, FR-12, FR-13, FR-15, NFR-03, NFR-07, NFR-09, DR-07, DR-08

---

### C-03 — Automated Recommendations vs. Human Decision-Making

**Stakeholders:** Recruiters / Hiring Managers vs. Placement and Fairness Requirements

**Conflicting Needs:**

- Recruiters may want automated results to reduce the time required to review many resumes.
- The system should not make the final hiring or placement decision automatically.

**Why It's a Conflict:**

More automation can reduce manual effort, but using the system's score or match as the final decision could remove the need for human review.

**Resolution:**

The system will provide scores, matches, and recommendations as supporting information. Results can be sorted or grouped by relevance, but the system should not automatically reject or make the final hiring or placement decision. An authorised human should remain responsible for the final decision.

**Affects:** US-11, US-12, US-17, US-18, FR-09, FR-10, DR-04, DR-06, DR-09

---

### C-04 — Desired Features vs. Project Scope

**Stakeholders:** Students, Recruiters, College Management vs. Development Team

**Conflicting Needs:**

- Stakeholders may expect additional features such as job portal integration, advanced analytics, and personalised career guidance.
- The development team has limited time and resources and needs to keep the project within the planned scope.

**Why It's a Conflict:**

Trying to implement every requested feature may make the project too large and reduce the time available for the core features.

**Resolution:**

The core features such as resume upload, parsing, skill extraction, scoring, suggestions, and job matching are given higher priority. Staff dashboards are treated as a lower priority feature. Features such as advanced analytics, career roadmaps, and direct job-portal integration can be considered for future versions.

**Affects:** Sprints 1–7, especially the feature prioritisation and future-scope decisions

---

### C-05 — Candidate Filtering vs. Human Review

**Stakeholders:** Recruiters / Employers vs. Candidates and Placement Staff

**Conflicting Needs:**

- Recruiters want to quickly identify resumes that are more relevant to a particular job.
- Candidates should still have the possibility of human review and should not be permanently rejected only because of an automated result.

**Why It's a Conflict:**

Strict automatic filtering can make the screening process faster, but it may also prevent some candidates from being reviewed by a human.

**Resolution:**

The system can use scores and matching results to organise or prioritise the results, but these results should not permanently remove a candidate from consideration. An authorised recruiter or placement officer should be able to review the available resume information when required.

**Affects:** US-11, US-17, US-18, FR-09, DR-06, DR-09

---

### C-06 — Placement Analytics vs. Data Retention

**Stakeholders:** College / Placement Cell vs. Data Privacy Reviewer

**Conflicting Needs:**

- Placement staff may want historical information to identify common trends across student batches.
- Student resume data should not be stored for longer than necessary.

**Why It's a Conflict:**

Keeping individual resume information for a long period can help with historical analysis, but it also increases the amount of personal data being retained.

**Resolution:**

Individual resume data should be retained according to the institution's data-handling rules. Where possible, long-term reports should use aggregated information instead of identifiable student data. This allows placement trends to be studied without unnecessarily retaining complete personal resumes.

**Affects:** US-14, US-16, NFR-09, DR-08

---

### C-07 — Simple Score vs. Detailed Evaluation

**Stakeholders:** Students vs. Faculty / Career Counselors

**Conflicting Needs:**

- Students want a simple score that can be understood quickly.
- Faculty and counselors may need more detailed information to explain the result and guide the student.

**Why It's a Conflict:**

A single score is easy to understand but does not provide enough detail for counselling. A highly detailed evaluation can be useful but may be difficult to understand at a glance.

**Resolution:**

The system should show one overall score first and provide a breakdown of the important areas below it. Students can quickly understand the overall result while counselors and students can view more details when required.

**Affects:** US-06, US-07, US-08, US-09, FR-05, FR-06, FR-07, NFR-05, NFR-08

---

### C-08 — AI Assistance vs. Requirements Accuracy

**Stakeholders:** Development Team, Domain Experts, Academic Supervisor, Privacy Reviewer

**Conflicting Needs:**

- The development team may use AI tools to help organise information and prepare requirement drafts.
- Requirements still need to be correct, understandable, and supported by actual stakeholder needs.
- Sensitive student or resume information should not be unnecessarily shared with external tools.

**Why It's a Conflict:**

AI-generated content may include assumptions or information that was not actually provided by stakeholders. There can also be privacy concerns if sensitive information is shared without proper care.

**Resolution:**

AI-generated content should be treated as a draft and reviewed by a team member before being included in the project. Requirements should be checked against the original elicitation information and their sources. Sensitive information should be removed or anonymised before using it with external AI tools.

**Affects:** Requirements engineering, traceability, privacy, and requirement validation

---

### C-09 — AI-Assisted Development vs. Code Understanding

**Stakeholders:** Development Team, Testers, Academic Supervisor

**Conflicting Needs:**

- Developers may use AI tools to speed up coding and debugging.
- The submitted code should still be understandable, testable, and maintainable by the development team.
- Team members should be able to explain the important parts of the implementation.

**Why It's a Conflict:**

Using generated code can save development time, but code that is copied without proper review may contain errors or may not be fully understood by the team.

**Resolution:**

AI-generated code should be reviewed and tested by the development team before it is used. Important changes should be understood by the team member making the change, and the code should follow the project's existing structure and coding practices.

**Affects:** NFR-10, maintainability, testing, and code review

---

### C-10 — Fast Development vs. Maintainable Design

**Stakeholders:** Development Team, QA/Testers, Future Maintainers

**Conflicting Needs:**

- The development team wants to complete features quickly within the project timeline.
- The system should remain organised so that individual components can be tested, fixed, and changed without affecting unrelated features.

**Why It's a Conflict:**

Putting too much functionality into a single component may make the first version faster to build, but it can make debugging and future changes more difficult.

**Resolution:**

The major parts of the system, such as resume processing, skill extraction, scoring, job matching, and result presentation, should be kept reasonably separate. This makes it easier to test individual parts and make changes without unnecessarily affecting the complete system.

**Affects:** US-19, NFR-10, maintainability, testing, and system design

---

## 6.3 Process Used to Find These Conflicts

The conflicts were identified by comparing the needs of different stakeholders with the functional, non-functional, and domain requirements collected during elicitation.

The requirements were then compared with the user stories and Sprint structure to identify situations where satisfying one requirement could affect another requirement.

Each identified conflict was given a practical resolution so that the main needs of the involved stakeholders could be addressed without unnecessarily increasing the project scope.
