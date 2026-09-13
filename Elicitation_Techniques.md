# Resume Analyser - Final Elicitation Plan for Stakeholders and End Users

It is a companion to **Stakeholders_and_End_Users.md**. For each stakeholder it gives: the technique(s) to use, why that combination (and not another) is the right fit, and what concrete information each session should walk away with. Sections 6 and 7 then turn the table into something you can actually schedule: a recommended order of operations, and a cross-reference showing which sessions can be run once and serve multiple stakeholders.

---

## 1. End Users

People who directly use the system or work with its results.

| Stakeholder | Recommended Technique(s) | Why This Combination Is Chosen | What This Elicitation Should Establish |
|---|---|---|---|
| **Students / Job Seekers** | Surveys/Questionnaires; Semi-Structured Interviews; Observation (think-aloud); Prototype Evaluation | Students are the largest and most varied group, so reach (survey) and depth (interviews) are both needed. Much of what a student needs — clarity, trust in a score, what to fix first — is tacit and only shows up while they're actually using the system, which is why think-aloud observation and a prototype walkthrough are included rather than relying on stated preferences alone. | Resume formats accepted, feedback depth/tone preferred, trust in automated scoring, job/internship matching expectations, accessibility needs. |
| **Placement Cell / Placement Officers** | Semi-Structured Interviews; Document Analysis (existing reports/spreadsheets); Requirements Workshop (JAD, co-run with faculty) | Officers hold real authority over what a readiness report must contain, so an interview extracts their explicit requirements; reviewing what they already produce anchors the new dashboard in a format they trust; a joint workshop with faculty resolves overlapping reporting needs in one sitting instead of reconciling separate interviews later. | How placement readiness is measured today, required reports/dashboards, data-access permissions, which decisions must stay human-only. |
| **Faculty / Placement Coordinators / Career Counselors** | Focus Groups; Observation of counselor-student interaction (during actual advising sessions); Prototype Evaluation of the feedback interface | "Explainable feedback" is a shared, debated concept across coordinators, which is exactly what a focus group surfaces. Observing a counseling session shows how a counselor handles different student scenarios and if they are actually efficient in helping the students. Reacting to an early prototype confirms the feedback actually supports a real conversation, not just a score. | Level of explanation needed per recommendation, preferred language/tone, ability to override or annotate system feedback, progress-tracking needs. |
| **Recruiters / HR Professionals** | Structured Interviews; Observation/Shadowing of live screening; Document Analysis (job descriptions, ATS/screening rubrics) | Shadowing reveals the tacit shortlisting logic recruiters apply but rarely state outright when simply asked. Interviews then clarify matching expectations (must-have vs. nice-to-have skills). Reviewing real job descriptions and rubrics grounds the skill-extraction and matching rules in artifacts that already exist, rather than assumptions. | Required resume fields, extraction-accuracy expectations, matching thresholds, handling of synonym/equivalent skills, how match explanations should read. |
| **Hiring Managers** | Scenario-Based Interviews ("would you trust this summary enough to shortlist on it?"); Document Analysis of existing hiring criteria; Prototype/Demo Review of candidate summaries | Hiring managers care about outcome and trust, not process, so a scenario built around a real decision surfaces genuine trust criteria far better than an abstract question would. Reviewing their current hiring criteria separates real selection requirements from information that shouldn't influence a decision. Reacting to an early demo gives them something concrete to point at when a summary feels unreliable or biased. | Information required for final review, fairness expectations, evidence needed to trust a recommendation, decisions that must never be made by the system alone. |

---

## 2. Internal / Technical Stakeholders

People who build, test, run, and evaluate the system.

| Stakeholder | Recommended Technique(s) | Why This Combination Is Chosen | What This Elicitation Should Establish |
|---|---|---|---|
| **Development Team (us)** | Brainstorming; Requirements Workshop / Backlog Refinement; Document & Interface Analysis (parsing libraries, NLP models, job-portal APIs) | Brainstorming generates the full range of technical approaches without early judgment; a workshop converts that into one shared, feasible requirement list; reviewing the actual libraries and APIs in play surfaces real constraints before they're designed around blindly. | Functional and non-functional requirements, system boundaries, parsing/scoring assumptions, dependencies and risks, acceptance criteria. |
| **UI/UX Designer** | Prototyping (low-fi → hi-fi); Observation/Usability Testing with real students; Card Sorting | Designers think in visual artifacts, not written briefs, so iterative prototypes tested directly on students produce far more precise UI requirements than a text brief. Card sorting resolves exactly how results (score, skills, matches, tips) should be grouped and labelled — a requirement that's nearly impossible to state verbally. | Upload/correction flow, result hierarchy and terminology, accessibility requirements, error-state handling. |
| **QA / Testers** | Document Analysis of the specification; Use-Case / Scenario Workshops; Testability Review (decision-table analysis for combinatorial scoring/matching rules) | Testers need requirements as unambiguous, testable acceptance criteria. Converting each requirement into a use case in a joint workshop exposes vague or untestable items before development starts, when it's cheap to fix. Decision tables suit the many combinations of parsing, scoring, and eligibility rules this system has. | Expected behaviour for valid/invalid resumes, boundary conditions, reproducibility requirements, fairness test scenarios, regression criteria. |
| **System Administrator** | Structured/Technical Interviews; Document Analysis of existing IT/security policy; Data-Flow / Threat-Modeling Workshop | The sysadmin's concerns are almost entirely non-functional, so a focused interview plus review of the college's existing IT policy captures explicit, verifiable requirements fast. A short threat-modeling session walking through the actual data flow surfaces concrete access-control and retention requirements a general policy document won't spell out. | Authentication/access control, backup frequency and recovery targets, retention/deletion rules, incident-response responsibilities. |
| **Product Owner / Project Manager** | Requirements Workshop (JAD); MoSCoW Prioritization Workshop; Interviews with a representative of each stakeholder group | The PO's job is reconciling competing asks into one feasible, prioritized scope — a negotiated group decision, which JAD and MoSCoW workshops are built for, rather than a list stitched together afterward from separate interviews. | Minimum viable scope, release priorities, dependencies and milestones, success metrics. |
| **Academic Supervisor / Professor** | Document Analysis of the rubric/project guidelines; Milestone Review Meetings (structured interviews) | The professor's requirements are largely already codified in the grading rubric, so document analysis is the primary source; short milestone reviews then re-confirm the project still satisfies "original work" and the stated objectives as it evolves, instead of risking a single end-of-project surprise. | Evaluation criteria, documentation standards, originality expectations, definition of a satisfactory final system. |

---

## 3. Privacy and Fairness Stakeholders

Our system stores personal data and uses AI to score people. These two roles are not extras — they create real requirements for us.

| Stakeholder | Recommended Technique(s) | Why This Combination Is Chosen | What This Elicitation Should Establish |
|---|---|---|---|
| **Data Privacy Reviewer** | Document Analysis of applicable regulation/policy (e.g., India's DPDP Act, 2023, and the college's data-handling policy); Structured Interviews; Data-Flow / Threat-Modeling Workshop | Privacy requirements are grounded in regulation and institutional policy far more than personal opinion, so document analysis is the primary source; an interview clarifies how it applies to this specific system; walking through the actual data flow (upload → storage → who can view → retention) in a workshop surfaces concrete requirements a policy document alone won't. | Consent and lawful basis, data minimization, retention/deletion periods, access permissions, audit logging, breach response. |
| **Bias / Fairness Reviewer** | Delphi Technique (anonymous, iterative rounds with a small expert panel); Algorithmic/Output Audit (score-distribution analysis across proxies like gender-coded words or college name); Scenario Testing with edge-case resumes | Fairness is contested and value-laden, not a fact to simply report, so the Delphi technique reaches a defensible, agreed definition without one voice dominating. An output audit demonstrates bias empirically rather than by opinion. Testing deliberately crafted edge-case resumes (same resume, different college name) turns the abstract fairness requirement into something concrete and verifiable. | Fairness definitions and prohibited/sensitive features for this context, audit frequency and thresholds, explanation and appeal mechanisms, escalation to human review. |

---

## 4. External Stakeholders

Outside parties the system depends on for data or services.

| Stakeholder | Recommended Technique(s) | Why This Combination Is Chosen | What This Elicitation Should Establish |
|---|---|---|---|
| **Job Portals / Job Data Sources** (e.g. LinkedIn, Naukri, Indeed) | Document Analysis of API documentation and terms of service; Interface Analysis of sample API responses | These are external commercial entities with no obligation to be interviewed, so their requirements — really, constraints the system must respect — can only come from reading what they've published and inspecting real sample data to see what's actually usable. | Authorized access method, available fields, rate limits, licensing/attribution rules, fallback behaviour if the source is unavailable. |

---

## 5. Indirectly Affected Parties

They do not use the system directly, but the system's outputs affect them.

| Stakeholder | Recommended Technique(s) | Why This Combination Is Chosen | What This Elicitation Should Establish |
|---|---|---|---|
| **College / University Management** | Executive-Level Structured Interviews; Document Analysis of existing KPI/accreditation reports; Prototype Review of the management dashboard | Management is small, high-level, and time-scarce, so a brief interview with one or two senior representatives, backed by the KPIs the institution already reports, is enough to define "insights across batches" without demanding much of their time; a dashboard prototype confirms those insights are actually producible from the data collected. | Placement-readiness indicators, batch-level reporting needs, privacy limits on aggregate vs. individual data. |
| **Employer Organizations** | Document Analysis of published job postings/hiring criteria; Proxy Elicitation through Recruiter/HR interviews (Section 1); periodic Survey distributed via the Placement Cell | Direct access to hiring organizations isn't realistic for a student project, so their needs are elicited indirectly: through what they already publish, through recruiters who already sit inside this stakeholder list as their proxy, and through occasional surveys the placement cell can distribute on the team's behalf. | Expected candidate information, role-specific requirements, fairness expectations, a feedback loop for improving matches. |
| **Rejected Candidates** | Anonymous, Opt-In Surveys; Empathy Mapping / Persona-Based Elicitation (built from student-user data already gathered in Section 1) | This is the most vulnerable and least accessible stakeholder group, and directly soliciting them risks reopening a sensitive experience for no clear benefit to them. Anonymous surveys and a persona built from existing student data are the most ethical way to represent their need for a fair process and a human fallback, without singling anyone out. | Whether rejection reasons are understandable, availability of human review/appeal, safeguards against unexplained permanent exclusion. |

---

## 6. Recommended Elicitation Sequence

No single technique works for every stakeholder here, and running them in the wrong order wastes effort. Follow this sequence:

1. **Start with document analysis and broad interviews.** This is the cheapest, fastest pass: the course rubric, existing placement reports, job-portal API docs/ToS, and the applicable privacy regulation all already exist and need no scheduling.
2. **Run the group workshops and shadowing/observation sessions.** JAD sessions with the Placement Cell, Faculty, and Product Owner resolve overlapping needs in one sitting; shadowing recruiters and observing a live counseling session capture tacit knowledge that can't be gathered by asking.
3. **Validate uncertain or high-stakes requirements with scenarios and prototypes.** This covers the hiring-manager trust scenarios, the fairness edge-case testing, and prototype walkthroughs with students, faculty, and the UI/UX designer.
4. **Converge the one genuinely contested requirement — fairness — through the Delphi panel**, separate from the rest of the schedule, since it needs anonymous, iterative rounds rather than a single session.
5. **Record every requirement with traceability**: which stakeholder gave it, which technique/session produced it, and which validation activity (test case, audit, sign-off) will confirm it before release. This is what turns this table into requirements QA can actually test against.

---

## 7. Technique-to-Stakeholder Cross-Reference

Use this to batch sessions — several stakeholders can often be served by one well-run session of the same technique.

| Technique | Stakeholders It Serves |
|---|---|
| Surveys / Questionnaires | Students, Employer Organizations (via Placement Cell), Rejected Candidates (anonymous) |
| Structured / Semi-Structured Interviews | Students, Placement Officers, Recruiters, System Administrator, Product Owner/PM, Academic Supervisor, Data Privacy Reviewer, College Management |
| Focus Groups | Faculty / Career Counselors |
| Requirements Workshop (JAD) | Placement Officers, Development Team, Product Owner/PM |
| Brainstorming | Development Team |
| Observation / Shadowing | Students (think-aloud), Recruiters, UI/UX Designer (usability testing), Faculty/Counselors (interaction with students) |
| Scenario-Based Elicitation | Hiring Managers, Bias/Fairness Reviewer (edge-case testing) |
| Prototyping / Prototype Evaluation | Students, Faculty/Counselors, UI/UX Designer, Hiring Managers (demo review), College Management (dashboard) |
| Document Analysis | Placement Officers, Recruiters, Hiring Managers, Development Team, QA, System Administrator, Academic Supervisor, Data Privacy Reviewer, Job Portals, College Management, Employer Organizations |
| Interface Analysis | Development Team, Job Portals |
| Card Sorting | UI/UX Designer |
| MoSCoW Prioritization Workshop | Product Owner/PM |
| Data-Flow / Threat-Modeling Workshop | System Administrator, Data Privacy Reviewer |
| Delphi Technique | Bias / Fairness Reviewer |
| Algorithmic / Output Audit | Bias / Fairness Reviewer |
| Testability Review / Decision-Table Analysis | QA / Testers |
| Empathy Mapping / Persona-Based Elicitation | Rejected Candidates |
| Proxy Elicitation (via another stakeholder's session) | Employer Organizations |

---

## 8. Overview

- **Students** are reached through surveys for scale, interviews for depth, and observation and prototypes for the tacit, hands-on needs a survey can't surface.
- **Placement staff and faculty/counselors** are engaged through interviews, focus groups, workshops, and observation, because their needs centre on explainability and shared, negotiated reporting formats.
- **Recruiters and hiring managers** are best studied through shadowing, scenario-based sessions, and their own existing documents, because their real screening criteria are largely tacit.
- **The development, design, QA, sysadmin, and PM roles** rely on workshops, prototyping, and document/interface analysis, because technical requirements must be precise, feasible, and testable.
- **The academic supervisor** is engaged through rubric review and short milestone check-ins, since the requirements are already largely defined by the course.
- **Privacy and fairness reviewers** rely on regulation/policy analysis, structured interviews, and — uniquely for the contested question of fairness — a Delphi expert panel and an empirical output audit.
- **Job portals**, being external and non-collaborative, are handled purely through document and interface analysis.
- **College management, employer organizations, and rejected candidates** — all indirectly affected — are reached through lightweight, low-burden, and in some cases proxy techniques, since none of them can be engaged as directly as an end user.

---

## 9. Elicitation Technique Reference

A short glossary for anyone reading this without a requirements-engineering background.

| Technique | What It Is |
|---|---|
| **Structured / Semi-Structured Interview** | A one-on-one conversation with prepared questions, allowing some follow-up beyond the script. |
| **Survey / Questionnaire** | A written set of questions sent to a large group, used when reach matters more than depth per person. |
| **Focus Group** | A guided group discussion, used when the requirement is a shared or debated view among several people. |
| **Requirements Workshop (JAD)** | A facilitated session bringing several stakeholders together to agree on requirements in one sitting. |
| **Brainstorming** | An unstructured, judgment-free session for generating a wide range of ideas quickly. |
| **Observation / Contextual Inquiry / Job Shadowing** | Watching a stakeholder do their actual task, to surface tacit needs they wouldn't think to state directly. |
| **Scenario-Based Elicitation** | Walking through a realistic situation or decision to see how a stakeholder actually responds to it. |
| **Prototyping / Prototype Evaluation** | Building a rough or interactive mock-up and watching stakeholders react to or use it. |
| **Document Analysis** | Reviewing existing reports, policies, forms, or regulations that already encode a stakeholder's requirements. |
| **Interface Analysis** | Inspecting an external system's actual data or API output to determine what it provides, when its owner can't be interviewed. |
| **Card Sorting** | Having stakeholders group and rank items to reveal an implicit priority or categorization structure. |
| **MoSCoW Prioritization Workshop** | A group session that sorts requirements into Must/Should/Could/Won't-have to agree on scope. |
| **Data-Flow / Threat-Modeling Workshop** | Walking through how data moves through the system to systematically surface security and privacy requirements. |
| **Delphi Technique** | Collecting judgments from an expert panel anonymously, over a few rounds, until their views converge — used for contested or subjective requirements. |
| **Algorithmic / Output Audit** | Statistically examining a system's actual outputs (e.g., scores across demographic proxies) to detect bias empirically rather than by opinion. |
| **Testability Review / Decision-Table Analysis** | Checking that each requirement is precise and measurable enough to test, and mapping combinations of rules into a table QA can execute against. |
| **Empathy Mapping / Persona-Based Elicitation** | Building a representative profile of a stakeholder from data already gathered about similar people, used when the real stakeholder is inaccessible or too vulnerable to approach directly. |
| **Proxy Elicitation** | Gathering a stakeholder's requirements indirectly, through another stakeholder or public artifact, when direct engagement isn't feasible. |

---
