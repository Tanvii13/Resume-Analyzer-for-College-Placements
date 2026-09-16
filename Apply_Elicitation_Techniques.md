# 3. Apply Elicitation Techniques

## 3.1 Objective

After identifying the stakeholders, we selected suitable elicitation techniques for the **Resume Analyser for College Placements** system.

The main purpose of this activity was to understand the following information which is important to know :

- What different stakeholders expect from the system.
- Problems faced by students during resume preparation.
- How resumes are reviewed and matched with job requirements.
- What the system should do (**Functional Requirements**).
- What qualities the system should have (**Non-Functional Requirements**).
- What rules and constraints come from the college placement and recruitment domain (**Domain Requirements**).

Instead of directly assuming the features, we connected stakeholder needs with specific elicitation activities and used the findings to derive requirements.

---

# 3.2 Elicitation Process

We followed the following flow during requirement elicitation:

**Stakeholder → Elicitation Technique → Questions / Activity → Finding → Requirement → Requirement Type**

### Example

**Student**  
↓  
**Survey / Interview**  
↓  
Students want to know which skills are missing from their resume.  
↓  
**Requirement:** The system should identify missing or recommended skills.  
↓  
**Type:** Functional Requirement

We used different techniques because each one gives a different kind of information.

| Technique | Main Purpose |
|---|---|
| Survey / Questionnaire | Collect common opinions from a larger group of students |
| Interview | Understand detailed requirements and ask follow-up questions |
| Observation | Identify actual user behaviour and usability problems |
| Document Analysis | Identify existing placement rules and job requirements |
| Brainstorming | Generate possible features and discuss project scope |
| Requirements Workshop | Discuss, prioritize and resolve different requirements |
| Focus Group | Understand common opinions and differences among users |
| Prototyping | Collect feedback on the proposed system and interface |

---

# 3.3 Application of Elicitation Techniques

## A. Survey / Questionnaire

### Stakeholders

- Students / Job Seekers
- Rejected Candidates, where accessible
- Employer-related feedback through the Placement Cell

### Purpose

Students are the main users of the Resume Analyser. Since students can have different expectations and problems, a questionnaire helps us identify common issues and features that are frequently needed.

The survey mainly covered the following areas:

- Resume preparation
- Resume analysis
- Resume scoring
- Skill gaps
- Job matching
- Improvement suggestions
- Explainability
- Privacy

### Questions Used

1. How do you currently check whether your resume is suitable for a job or internship?
2. What problems do you usually face while preparing your resume?
3. Would you use a system that automatically analyses your resume?
4. What information would you expect after uploading your resume?
5. Would a resume score be useful to you?
6. What factors should be considered while calculating the score?
7. Would you like the system to identify missing skills?
8. Would suggestions for improving your resume be useful?
9. Would matching your resume with suitable jobs or internships be useful?
10. Would you like to know why a particular score or recommendation was given?
11. Should the system identify formatting or keyword-related problems?
12. Would you like to correct information if the system extracts it incorrectly?
13. What concerns would you have about uploading your resume?
14. What would make you trust or distrust an automated recommendation?

### Information Collected from the Survey

From the survey, we can identify:

- Common resume preparation problems.
- Features students find useful.
- Need for resume scoring.
- Need for skill extraction.
- Need for missing-skill identification.
- Need for job matching.
- Preferred feedback format.
- Privacy concerns.

### Requirements Derived

#### Functional Requirements

- The system should allow students to upload their resumes.
- The system should analyse the uploaded resume.
- The system should extract relevant skills.
- The system should identify missing or recommended skills.
- The system should provide resume improvement suggestions.
- The system should generate a resume score.
- The system should provide suitable job or internship matches.
- The system should provide reasons for important recommendations.

#### Non-Functional Requirements

- The interface should be easy for students to understand.
- Results should be presented clearly.
- Resume analysis should provide results within an acceptable time.
- Uploaded resume information should be protected.

#### Domain Requirements

- Resume analysis should focus on information useful for college placements.
- Job matching should consider skills related to the target role.
- Recommendations should be relevant to the selected job or internship.

---

## B. Semi-Structured Interviews

### Stakeholders

- Placement Officers
- Faculty / Placement Coordinators
- Career Counselors
- Recruiters / HR Professionals
- Hiring Managers
- System Administrator
- Product Owner / Project Manager
- Academic Supervisor

### Purpose

We used interviews when detailed information was needed from a stakeholder.

In a semi-structured interview, we prepare a basic set of questions and ask additional questions whenever an answer needs clarification.

This is useful for placement officers and recruiters because their requirements are closely related to the actual placement and screening process.

---

## B.1 Interview with Placement Officer

### Questions

1. How is resume quality currently checked during placement preparation?
2. What common resume problems do students have?
3. What information would be useful to placement officers?
4. Would a dashboard showing common student problems be useful?
5. Should placement staff be able to see individual student analysis?
6. Should they also be able to view overall batch-level information?
7. Which information should not be visible to every user?
8. Which decisions should remain with the placement team?
9. What type of reports are useful during placement activities?

### Requirements Identified from the Interview

**Functional Requirements**

- Authorized placement staff should be able to view relevant student analysis.
- The system should provide placement-related reports or dashboard information.
- The system should help identify common resume problems among students.

**Non-Functional Requirements**

- Student information should be accessible only to authorized users.
- Dashboard information should be easy to understand.
- Sensitive student information should not be unnecessarily displayed.

**Domain Requirements**

- The system should follow the college's placement process.
- The system should support placement staff rather than automatically make placement decisions.

---

## B.2 Interview with Faculty / Career Counselor

### Questions

1. What type of resume feedback do students usually need?
2. Is a numerical score alone sufficient?
3. What explanation should be given along with a score?
4. Which resume problems should be shown first?
5. Should students be able to track their improvement?
6. Should counselors be able to review the generated feedback?
7. What terminology would be easier for students to understand?

### Requirements Identified from the Interview

**Functional Requirements**

- The system should highlight important areas for improvement.
- The system should provide understandable explanations for recommendations.
- Authorized counselors should be able to review student feedback.

**Non-Functional Requirements**

- Feedback should be easy for students to understand.
- Recommendations should be practical and actionable.
- Important scores should not be shown without useful explanation.

**Domain Requirements**

- Resume guidance should support college placement preparation.
- Automated feedback should support the counselor's role rather than completely replace it.

---

## C. Recruiter / HR Interview and Screening Observation

### Why Both Techniques Are Useful

Recruiters can explain what they expect from a resume, while observing the screening process can reveal additional requirements that may not be mentioned during an interview.

Therefore, where possible, we can combine recruiter interviews with observation of a resume-screening activity.

### Interview Questions

1. Which parts of a resume are most important during initial screening?
2. Which skills are mandatory for a particular role?
3. How are required and preferred skills differentiated?
4. How should similar or equivalent skills be treated?
5. What type of mismatch in automated job matching would be problematic?
6. Should the system explain why a candidate matches a job?
7. Which candidate information should not affect matching?
8. Should the system make the final hiring decision automatically?

### Requirements Identified from the Interview

**Functional Requirements**

- The system should extract relevant skills from a resume.
- The system should compare resume skills with job requirements.
- The system should identify matching and missing skills.
- The system should provide a job-match result.
- The system should explain important matching results.

**Non-Functional Requirements**

- Skill extraction should be sufficiently accurate for the intended use.
- The same input should produce consistent results under the same configuration.
- Results should be understandable.
- Irrelevant personal information should not unnecessarily affect screening.

**Domain Requirements**

- Job matching should be based on job-specific requirements.
- Required and preferred skills should be treated differently when the job description provides this information.
- Similar or equivalent skills may need to be considered during matching.
- Final hiring decisions should remain under human control.

---

## D. Observation / Shadowing

### Stakeholders

- Students
- Faculty / Career Counselors
- Recruiters / HR Professionals

### Purpose

Observation is useful because users may not always mention their actual difficulties while answering questions.

For example, a student may say that a system is simple, but during actual use the student may:

- Spend time finding the reason behind a score.
- Not understand a technical term.
- Have difficulty finding missing skills.
- Want to correct an incorrectly extracted skill.
- Feel confused when too much information is shown together.

### Student Observation Activity

**Upload Resume → View Analysis → Check Score → Review Skills → Check Job Matches → Read Suggestions**

The following points can be observed:

- Where the student gets confused.
- Which information is checked first.
- Whether the score is understandable.
- Whether the reason for the score can be found easily.
- Whether the suggestions are clear.
- Whether the upload process is simple.

### Requirements Identified from the Interview

**Functional Requirements**

- The system should provide a simple resume upload process.
- Analysis results should be divided into understandable sections.
- Extracted skills should be visible to the user.
- Important extracted information should be correctable if required.

**Non-Functional Requirements**

- Navigation should be simple.
- The interface should be easy to understand.
- Error messages should explain the problem clearly.
- Results should be readable.

---

## E. Document Analysis

### Documents / Sources

The following types of documents can be analysed:

- College placement guidelines
- Placement forms
- Resume guidelines
- Job descriptions
- Screening criteria
- College policies
- Privacy and data-handling policies
- Job portal documentation and terms
- Project / course guidelines

### Purpose

Some requirements are already defined in documents used by the placement team or recruiters.

By analysing these documents, we can identify the relevant rules and convert them into system requirements.

### Example: Job Description Analysis

Suppose a job description contains:

| Skill | Requirement |
|---|---|
| Python | Required |
| SQL | Required |
| Git | Preferred |
| Machine Learning | Preferred |

**Functional Requirement**

> The system should compare resume skills with the skills mentioned in a job description.

**Domain Requirement**

> Required and preferred skills should be distinguished when this information is available in the job description.

### Example: Placement Guidelines

If the college placement guidelines specify eligibility conditions for a placement drive:

**Domain Requirement**

> Placement eligibility information should follow the rules defined by the relevant placement process.

### Example: Privacy Policy

Privacy-related documents can help us identify:

- Who can access resume information.
- What information can be stored.
- How long information can be retained.
- Whether user consent is required.
- Whether users can request deletion.

These points can then be converted into security and privacy-related requirements.

---

# F. Brainstorming

### Participants

- Development Team

### Purpose

We used brainstorming to discuss possible features and technical ideas before finalizing the project scope.

### Topics Discussed

- Resume upload
- Resume parsing
- Skill extraction
- Resume scoring
- Job matching
- Recommendation generation
- Student dashboard
- Placement dashboard
- Authentication
- Access control
- Resume storage
- Error handling
- Explainability
- Privacy
- Fairness
- External job-data integration

### Result

The discussion helped us separate the features into **core features** and **future features**.

### Core Features

1. Resume upload
2. Resume parsing
3. Skill extraction
4. Resume analysis
5. Resume score
6. Improvement suggestions
7. Job matching

### Possible Future Features

1. Direct job-portal integration
2. Advanced placement analytics
3. Personalized career roadmap
4. Advanced fairness analysis

---

# G. Requirements Workshop

### Participants

- Placement Officers
- Faculty / Career Counselors
- Development Team
- Product Owner / Project Manager

### Purpose

Different stakeholders can have different expectations from the system.

**Student:**  
"I want detailed feedback about my resume."

**Placement Officer:**  
"I need a simple view of placement-related information."

**Recruiter:**  
"I need relevant and reliable job matching."

The workshop helps us discuss these differences and decide which requirements should be included in the initial version.

### Discussion Points

- Which features are essential?
- Which information should each role be able to access?
- Which requirements conflict with each other?
- Which features can be postponed?
- How should requirements be prioritized?
- What should be considered a successful result?

### Initial Prioritization

| Requirement | Priority | Reason |
|---|---|---|
| Resume Upload | Must Have | Required to start the analysis |
| Resume Parsing | Must Have | Required to process resume content |
| Skill Extraction | Must Have | Required for analysis and matching |
| Resume Score | Must Have | Important part of resume analysis |
| Improvement Suggestions | Must Have | Direct benefit to students |
| Job Matching | Must Have | Supports placement preparation |
| Placement Dashboard | Should Have | Useful for placement staff |
| Advanced Analytics | Could Have | Can be added later |
| External Portal Integration | Could Have | Depends on external access / API |

---

# H. Focus Group Discussion

### Participants

- Students
- Faculty / Career Counselors

### Purpose

We used the focus group to understand common opinions as well as differences between users.

### Discussion Topics

1. What makes a resume difficult to improve?
2. What information should be shown after analysis?
3. Is a score alone useful?
4. What type of suggestions are actually helpful?
5. Should the system show missing skills?
6. What information should be kept private?
7. How much information should be shown on one screen?

### Information Obtained from the Discussion

The discussion can help identify:

- Common expectations among students.
- Differences between student and counselor expectations.
- Preferred feedback style.
- Concerns about automated recommendations.
- Usability issues that should be considered in the prototype.

---

# 3.4 Prototyping / Prototype Evaluation

### Stakeholders

- Students
- Faculty / Career Counselors
- Hiring Managers
- UI/UX-related participants

### Purpose

Some requirements become easier to understand when stakeholders can see a basic version of the proposed system.

For example, a low-fidelity prototype can contain:

**Upload Resume → Analysis Dashboard → Resume Score → Skills → Job Matches → Suggestions**

### Evaluation Questions

1. Is the information easy to understand?
2. What information should appear first?
3. Is the resume score clear?
4. Can the user understand why the score was given?
5. Are the suggestions useful?
6. Is any important information missing?
7. Is too much information displayed?
8. Can the user understand why a particular job was recommended?

### Requirements Identified from the Interview

**Functional Requirements**

- The system should display resume analysis results.
- The system should display extracted skills.
- The system should display job matches.
- The system should display improvement suggestions.
- The system should explain important results.

**Non-Functional Requirements**

- The interface should be intuitive.
- Important information should be easy to find.
- Error messages should be clear.
- The interface should be readable and accessible.

---

# 3.5 Consolidated Functional Requirements

After applying the different elicitation techniques, we consolidated the major functional requirements as follows:

| ID | Functional Requirement | Main Elicitation Source |
|---|---|---|
| FR-01 | The system should allow students to upload a resume. | Survey, Observation |
| FR-02 | The system should parse the uploaded resume. | Interview, Brainstorming |
| FR-03 | The system should extract relevant skills from the resume. | Survey, Recruiter Interview |
| FR-04 | The system should analyse the resume using defined criteria. | Survey, Interview |
| FR-05 | The system should generate a resume score. | Survey, Interview |
| FR-06 | The system should identify important areas for improvement. | Survey, Observation |
| FR-07 | The system should provide improvement suggestions. | Survey, Faculty Interview |
| FR-08 | The system should compare resume skills with job requirements. | Recruiter Interview, Document Analysis |
| FR-09 | The system should provide suitable job/internship matches. | Survey, Recruiter Interview |
| FR-10 | The system should show matching and missing skills for a selected job. | Recruiter Interview |
| FR-11 | The system should provide explanations for important results. | Faculty Interview, Prototype |
| FR-12 | Authorized placement staff should be able to view relevant placement information. | Placement Officer Interview |
| FR-13 | The system should provide appropriate dashboards/reports for authorized users. | Placement Interview, Workshop |
| FR-14 | The system should handle invalid or unsupported resume input. | Observation, Prototype |
| FR-15 | The system should restrict access to information according to user roles. | Privacy / System Administration Discussion |

---

# 3.6 Consolidated Non-Functional Requirements

| ID | Non-Functional Requirement | Main Elicitation Source |
|---|---|---|
| NFR-01 | The system should be easy to use for students with different levels of technical knowledge. | Survey, Observation |
| NFR-02 | Resume analysis should provide results within an acceptable response time. | Survey, Recruiter Interview |
| NFR-03 | Resume information should be protected from unauthorized access. | Privacy Discussion, Document Analysis |
| NFR-04 | The system should provide consistent results for the same input and configuration. | Technical Discussion |
| NFR-05 | Recommendations and important results should be understandable. | Faculty Interview, Prototype |
| NFR-06 | The system should provide clear error messages for invalid input. | Observation, Prototype |
| NFR-07 | The system should support role-based access control. | System Administration / Privacy Discussion |
| NFR-08 | The interface should be readable and accessible. | Observation, Prototype |
| NFR-09 | The system should avoid unnecessary collection and exposure of personal information. | Privacy Discussion |
| NFR-10 | The system should be maintainable so that parsing, scoring and matching components can be updated. | Brainstorming |
| NFR-11 | The system should handle failures in external job-data sources gracefully, if such integration is implemented. | Document Analysis / Technical Discussion |

---

# 3.7 Consolidated Domain Requirements

Domain requirements come from the **college placement and recruitment domain** rather than only from software implementation.

| ID | Domain Requirement | Main Elicitation Source |
|---|---|---|
| DR-01 | Resume analysis should focus on information relevant to college placement and internship preparation. | Placement Discussion |
| DR-02 | Job matching should consider the skills and requirements of the target role. | Recruiter Interview, Job Description |
| DR-03 | Required and preferred skills should be distinguished when specified in the job description. | Document Analysis |
| DR-04 | Related or equivalent skills may need to be considered during skill matching. | Recruiter Interview |
| DR-05 | Placement eligibility should follow the rules of the relevant placement process. | Placement Documents |
| DR-06 | Automated recommendations should support rather than replace important human placement or hiring decisions. | Placement / Recruiter Discussion |
| DR-07 | Student placement information should be accessible only to authorized roles. | Placement / Privacy Discussion |
| DR-08 | Resume information should be handled according to applicable institutional privacy rules. | Policy Analysis |
| DR-09 | Irrelevant candidate characteristics should not unfairly influence scoring or matching. | Fairness Discussion |
| DR-10 | External job information should be used according to the applicable rules and restrictions of the source. | Job Portal Documentation |

---

# 3.8 Requirement Traceability

We used requirement traceability to connect each requirement with the elicitation activities from which it was identified.

### Example 1 – Student Requirement

**Stakeholder:** Student  
↓  
**Technique:** Survey + Observation  
↓  
**Finding:** Students need to understand what is wrong with their resume.  
↓  
**Requirement:** The system should provide actionable improvement suggestions.  
↓  
**Type:** Functional Requirement

### Example 2 – Recruiter Requirement

**Stakeholder:** Recruiter  
↓  
**Technique:** Interview + Document Analysis  
↓  
**Finding:** Resume screening depends on the requirements of the particular job.  
↓  
**Requirement:** The system should compare resume skills with job requirements.  
↓  
**Type:** Functional + Domain Requirement

### Example 3 – Explainability Requirement

**Stakeholder:** Student + Faculty  
↓  
**Technique:** Survey + Interview + Prototype Evaluation  
↓  
**Finding:** A score without an explanation may not tell the student how to improve.  
↓  
**Requirement:** The system should provide understandable explanations for important scores and recommendations.  
↓  
**Type:** Non-Functional Requirement

### Example 4 – Privacy Requirement

**Stakeholder:** Placement Staff + Privacy / System Administration  
↓  
**Technique:** Interview + Document Analysis  
↓  
**Finding:** Resumes contain personal information and should not be available to every user.  
↓  
**Requirement:** The system should enforce appropriate access control for resume information.  
↓  
**Type:** Non-Functional Requirement

---

# 3.9 Summary of Elicitation Results

The different elicitation techniques helped us understand the system from different perspectives.

| Technique | Main Information Obtained |
|---|---|
| Survey / Questionnaire | Student expectations and common resume problems |
| Interviews | Detailed placement, recruitment, privacy and system requirements |
| Observation | Actual user behaviour and usability problems |
| Document Analysis | Placement rules, job requirements and policy constraints |
| Brainstorming | Possible features, technical ideas and project scope |
| Requirements Workshop | Requirement discussion, prioritization and conflict resolution |
| Focus Group | Common opinions and differences among students and counselors |
| Prototyping | Usability, presentation and feedback requirements |

The collected requirements were grouped into the following three categories:

- **Functional Requirements**
- **Non-Functional Requirements**
- **Domain Requirements**

These requirements will be used in the next stages of the project to prepare **User Stories, EPICs, Product Backlog items and Sprint Planning** for the Agile SCRUM process.

---

# 3.10 Evidence of Elicitation Activities

| Technique | Evidence to Keep |
|---|---|
| Survey | Questionnaire and response summary |
| Interview | Questions, stakeholder role and interview notes |
| Observation | Activity observed, problems noticed and findings |
| Document Analysis | Document name and relevant information extracted |
| Brainstorming | Meeting notes, ideas and final decisions |
| Requirements Workshop | Participants, discussion points and agreed requirements |
| Focus Group | Participants, questions and common findings |
| Prototype Evaluation | Prototype screenshots, feedback and changes made |
| Traceability | Requirement ID → Stakeholder → Technique → Finding |
