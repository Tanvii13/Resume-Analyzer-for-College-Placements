# Resume Analyser — Conflict Identification and Resolution

## 1. Purpose

Requirements collected from different stakeholders during elicitation do not always agree with each other. This document identifies the conflicts found across stakeholders, EPICs, and user stories, explains why each conflict exists, and records how the team resolved it. This is Step 6 of the project instructions and builds directly on the stakeholders (Step 1), elicitation results (Step 2–3), user stories (Step 4), and EPICs/Sprints (Step 5) already produced for the Resume Analyser.

Each conflict is logged in the same style as requirement traceability:

**Stakeholders Involved → Conflicting Needs → Why It's a Conflict → Resolution → Requirements/User Stories Affected**

---

## 2. Conflict Log

### C-01 — Detailed Transparency vs. Processing Speed

**Stakeholders:** Students (US-09, FR-11, NFR-05) vs. Students/Recruiters (NFR-02)

**Conflicting Needs:**
- Students want full, understandable explanations for every score and recommendation (FR-11, NFR-05).
- Students and recruiters also expect analysis to complete within an acceptable response time (NFR-02).

**Why It's a Conflict:** Generating detailed, per-result explanations (via the GenAI/LLM pipeline) adds extra processing and inference time on top of parsing, scoring, and matching. Maximizing explanation depth works against minimizing response time.

**Resolution:** Provide a short, always-shown explanation summary (1–2 lines) generated inline with the score, and make a deeper explanation available on demand ("Why this score?") rather than generating full detail for every result by default. This keeps default response times low while still satisfying FR-11/NFR-05 for students who want more detail.

**Affects:** US-06, US-09, FR-05, FR-11, NFR-02, NFR-05

---

### C-02 — Staff Visibility vs. Student Data Privacy

**Stakeholders:** Placement Cell / Faculty Counselors (US-13, US-14, FR-12, FR-13) vs. Data Privacy Reviewer (US-16, NFR-03, NFR-09, DR-08)

**Conflicting Needs:**
- Placement officers and counselors want to view individual student resume analysis to give guidance and plan training (FR-12, FR-13).
- The privacy reviewer requires that resume data and personal information be exposed only to the extent necessary, with restricted access (NFR-03, NFR-09, DR-08).

**Why It's a Conflict:** "View student analysis for guidance" and "minimize exposure of personal information" pull in opposite directions — more visibility helps counseling, but more visibility increases privacy risk.

**Resolution:** Apply role-based access control (FR-15, NFR-07) so only staff explicitly assigned to a student (or acting with student consent) can view that student's full analysis. Placement-wide dashboards (US-14) show aggregated/batch-level data only — no individually identifiable resume content — satisfying the placement cell's planning need without violating NFR-09.

**Affects:** US-13, US-14, US-15, US-16, FR-12, FR-13, FR-15, NFR-03, NFR-07, NFR-09, DR-07, DR-08

---

### C-03 — Automated Efficiency vs. Human-in-the-Loop Decisions

**Stakeholders:** Recruiters / Hiring Managers (screening efficiency needs) vs. Bias/Fairness Reviewer and Placement domain rules (DR-06, US-18)

**Conflicting Needs:**
- Recruiters want the system to reduce manual screening effort by reliably ranking/shortlisting candidates.
- DR-06 and US-18 require that automated scores and matches remain *supporting* information, with final hiring/placement decisions left to a human.

**Why It's a Conflict:** The more the system is trusted to rank and filter automatically, the less manual screening effort recruiters spend — but the domain requirement explicitly forbids the system from making the final call, which limits how much automation can replace human screening.

**Resolution:** The system produces a ranked shortlist and explanation (satisfying the efficiency need), but never auto-rejects a candidate outright — low-scoring or filtered-out resumes remain visible/retrievable by a human reviewer on request (see C-05). This is treated as a "must support, not replace" boundary rather than a feature to trade away.

**Affects:** US-11, US-12, US-17, US-18, FR-09, FR-10, DR-04, DR-06, DR-09

---

### C-04 — Feature Scope: Student/Recruiter Wishlist vs. Development Team Feasibility

**Stakeholders:** Students, Recruiters, College Management (feature requests from Survey/Interviews) vs. Development Team (Brainstorming outcome, course timeline)

**Conflicting Needs:**
- Stakeholders raised several desirable features: direct job-portal integration, advanced placement analytics, personalized career roadmaps, advanced fairness analysis.
- The development team, working within a course project timeline with a small team, needs a scope that is actually buildable in the available sprints.

**Why It's a Conflict:** Stakeholder wish-lists exceed what a beginner-scoped, single-semester group project can deliver reliably; building everything risks delivering nothing well.

**Resolution:** Applied MoSCoW prioritization during the Requirements Workshop (Section 3.3-G). Core features (upload, parsing, skill extraction, scoring, suggestions, job matching) were fixed as "Must Have" for Sprints 1–4. Staff dashboards were scoped as "Should Have" (Sprint 5). Job-portal integration, advanced analytics, and career roadmaps were explicitly deferred to "Could Have" / future work, and NFR-11 was added so the system degrades gracefully if external job-data integration is attempted but unavailable.

**Affects:** All Sprints 1–7; specifically the Core Features vs. Future Features split in Section 3.3-F

---

### C-05 — Fair Screening for Rejected Candidates vs. Recruiter/Employer Efficiency

**Stakeholders:** Rejected Candidates (fair process, human review) vs. Recruiters / Employer Organizations (fast, filtered shortlists)

**Conflicting Needs:**
- Rejected candidates need assurance that a low score doesn't permanently and invisibly remove them, and that a human can still review their resume.
- Recruiters and employers want the system to filter down large applicant pools so they only review strong matches.

**Why It's a Conflict:** Strict automatic filtering (what employers want for efficiency) directly reduces the chance a rejected/low-scoring candidate is ever seen by a human (what fairness requires).

**Resolution:** Filtering affects *default sort order and visibility*, not permanent removal — all analyzed resumes remain queryable/reviewable by an authorized recruiter or placement officer, and DR-06/US-17 ensure the system never performs the final rejection itself. This gives recruiters the efficiency of a ranked view while preserving the possibility of human review for anyone screened out.

**Affects:** US-11, US-17, DR-06, DR-09

---

### C-06 — Long-Term Placement Analytics vs. Data Retention/Deletion Rules

**Stakeholders:** College/University Management, Placement Cell (batch-level trend reporting) vs. Data Privacy Reviewer (retention limits, deletion requests, DR-08)

**Conflicting Needs:**
- Management wants placement-readiness trends across batches over time, which requires keeping historical resume/analysis data.
- Privacy rules require limiting how long personal data is retained and honoring student deletion requests.

**Why It's a Conflict:** Useful year-over-year analytics depend on retaining data; privacy compliance pushes toward deleting or anonymizing it as soon as possible.

**Resolution:** Individually identifiable resume data is retained only per the institution's stated retention policy and deleted/anonymized on request (satisfying DR-08/US-16). Batch-level trend reporting for management is generated from aggregated, de-identified statistics that are retained separately from the identifiable source resumes, so deleting a student's resume does not remove them from historical aggregate counts already computed.

**Affects:** US-14, US-16, NFR-09, DR-08

---

### C-07 — Score Simplicity vs. Score Completeness

**Stakeholders:** Students (want a quick, simple score — Survey) vs. Faculty/Counselors (want a score that reflects nuanced, multi-factor evaluation — Interview)

**Conflicting Needs:**
- Focus group and survey feedback (Section 3.3-A, H) show students want a clear, simple headline number.
- Faculty want the underlying evaluation to be nuanced enough to support real counseling conversations, which pushes toward a multi-dimensional breakdown rather than one number.

**Why It's a Conflict:** A single simple score is easy for students to grasp but hides the detail counselors need; a fully broken-down multi-factor score is more useful for counseling but harder for students to read at a glance.

**Resolution:** Show one overall score by default (US-06) for students, with an expandable breakdown by category (e.g., skills, formatting, experience relevance) underneath it — the same underlying data serves both audiences, addressed as a UI layering decision rather than two competing scoring systems.

**Affects:** US-06, US-07, US-08, FR-05, FR-06, NFR-05, NFR-08

---

## 3. Conflict Resolution Summary Table

| ID | Conflict | Stakeholders | Resolution Approach |
|---|---|---|---|
| C-01 | Explanation depth vs. speed | Students, Recruiters | Default short explanation + on-demand detail |
| C-02 | Staff visibility vs. student privacy | Placement/Faculty, Privacy Reviewer | Role-based access + aggregated dashboards |
| C-03 | Automated ranking vs. human final decision | Recruiters/Hiring Managers, Fairness Reviewer | Rank & explain, never auto-reject |
| C-04 | Feature wishlist vs. feasible scope | Students/Recruiters/Management, Dev Team | MoSCoW prioritization, deferred "Could Have" items |
| C-05 | Efficient filtering vs. fair review | Recruiters/Employers, Rejected Candidates | Filter affects visibility/order, not permanent removal |
| C-06 | Analytics retention vs. data deletion | Management, Privacy Reviewer | Aggregated/de-identified analytics stored separately |
| C-07 | Simple score vs. detailed score | Students, Faculty/Counselors | Single score by default with expandable breakdown |

---

## 4. Process Used to Find These Conflicts

Conflicts were identified by comparing the "What They Need" column of the Stakeholder document against the Functional/Non-Functional/Domain requirements each stakeholder's elicitation session produced (Section 3.5–3.7 of the Elicitation document), and by re-reading the Requirements Workshop discussion points (Section 3.3-G), where competing expectations between students, placement officers, and recruiters were first raised explicitly. Any pair of requirements that could not both be fully satisfied at the same time was logged here, along with the design or process decision that lets both sides be reasonably served.
