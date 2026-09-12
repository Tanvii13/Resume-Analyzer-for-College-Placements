# Resume Analyser – Stakeholders and End Users

This document lists everyone who has a stake in the **Resume Analyser for College Placements** system. For each one, it explains their role and what they need from the system or how they are affected by it.

Knowing this before we collect requirements matters, because it stops us from designing only for the student uploading a resume and forgetting everyone else involved in the placement process.

---

## 1. End Users

People who directly use the system or work with its results.

| Stakeholder | Role | What They Need |
|---|---|---|
| **Students / Job Seekers** | The main users. They upload their resume to get it analysed and to prepare for placements. | Accurate resume scoring, skill analysis, job and internship matching, keyword and formatting suggestions, and clear tips on what to improve. |
| **Placement Cell / Placement Officers** | Run placement and internship activities, and use the system's results to see how ready students are. | Resume insights across students, a view of common mistakes, and information that helps them plan training and improve placement readiness. |
| **Faculty / Placement Coordinators / Career Counselors** | Guide students in building and improving their resumes and profiles. | Feedback that is clear and explainable, so they can sit with a student and discuss it — not just a raw number. |
| **Recruiters / HR Professionals** | Screen candidate resumes and shortlist people who fit a job. | Reliable skill extraction and good candidate-to-job matching, so manual screening effort goes down. |
| **Hiring Managers** | Review the shortlist and make the final hiring call. | Trustworthy and unbiased candidate summaries they can rely on for a decision. |

---

## 2. Internal / Technical Stakeholders

People who build, test, run, and evaluate the system.

| Stakeholder | Role | What They Need |
|---|---|---|
| **Development Team (us)** | Design, build, test, and maintain the system, including resume parsing and the scoring logic. | Clear requirements, regular stakeholder feedback, proper documentation, and requirements that are actually feasible to build. |
| **UI/UX Designer** | Designs the resume upload flow, the results screen, and the overall experience. | A design that is usable, accessible, and smooth from upload to results. |
| **QA / Testers** | Check that parsing, scoring, and recommendations work correctly and consistently. | Defined test cases, predictable system behaviour, and results that can be reproduced. |
| **System Administrator** | Manages accounts, permissions, uptime, and resume data storage and backups. | System stability, secure access control, and reliable backup and recovery. |
| **Product Owner / Project Manager** | Sets priorities, defines scope, and coordinates work across sprints. | The project delivered within the agreed scope, timeline, and resources. |
| **Academic Supervisor / Professor** | Evaluates the project for the course. | Original work, proper documentation, and a system that meets the stated project objectives. |

---

## 3. Privacy and Fairness Stakeholders

Our system stores personal data and uses AI to score people. These two roles are not extras — they create real requirements for us.

| Stakeholder | Role | What They Need |
|---|---|---|
| **Data Privacy Reviewer** | Makes sure resume data (name, contact details, personal information) is collected, stored, and used safely and with student consent. | Secure storage, restricted access, and clear rules on who can view a student's data and how long it is kept. |
| **Bias / Fairness Reviewer** | Checks that the scoring and matching logic does not unfairly favour or reject candidates based on things like gender-coded words, college name, or similar factors. | A scoring system that is checked for fairness, not only for accuracy. |

---

## 4. External Stakeholders

Outside parties the system depends on for data or services.

| Stakeholder | Role | What They Need |
|---|---|---|
| **Job Portals / Job Data Sources** (e.g. LinkedIn, Naukri, Indeed) | Supply job descriptions, roles, and required-skill data used for comparison and matching, if such integration is implemented. | Accurate and up-to-date job information, proper API usage, and compliance with their terms of service. |

---

## 5. Indirectly Affected Parties

They do not use the system directly, but the system's outputs affect them.

| Stakeholder | Role | What They Need |
|---|---|---|
| **College / University Management** | Cares about placement readiness and how well placement support is working overall. | Insights into student preparation, resume quality, and placement outcomes across batches. |
| **Employer Organizations** | The companies that ultimately hire students shortlisted through this system. | Fair and accurate shortlisting, so the right candidates reach them. |
| **Rejected Candidates** | Students whose resumes score low or get filtered out during screening. | A fair screening process, and ideally the chance for their resume to still be seen by a human reviewer. |

---

## 6. Overview

Putting it simply, the Resume Analyser touches the whole placement process:

- **Students** use it to analyse and improve their resumes.
- **Placement staff, faculty, and counselors** use the results to guide students.
- **Recruiters and hiring managers** use the analysis and matching during screening.
- **Our development and technical team** builds, tests, and maintains it, with the professor evaluating the outcome.
- **Privacy and fairness reviewers** keep the system safe to use and fair to the people it scores.
- **Job portals** supply the job and skill data used for matching.
- **College management, employers, and rejected candidates** are affected by the results even though they never open the app.
