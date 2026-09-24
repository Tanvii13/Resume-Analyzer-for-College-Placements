# 5. EPICs

An EPIC groups related user stories that deliver one coherent piece of the system. Grouping the backlog this way is what lets us generate Sprints in the next section — each EPIC becomes (roughly) one sprint's worth of work, in dependency order.

---

## EPIC 1 — Resume Upload & Processing

**Goal:** Get a resume safely into the system as clean, structured data before any analysis can begin.

**Stories:**

- **US-01:** Upload Resume
- **US-02:** Parse Uploaded Resume
- **US-03:** Handle Invalid Resume

**Requirement IDs covered:** FR-01, FR-02, FR-14, NFR-01, NFR-06

**Why grouped together:** All three stories happen at the very start of the pipeline — accept the file, read it, and fail cleanly if it's unreadable. Nothing else in the system can run until this EPIC works.

---

## EPIC 2 — Resume Scoring & Analysis

**Goal:** Turn the parsed resume into a placement-relevant evaluation.

**Stories:**

- **US-04:** Extract Skills from Resume
- **US-05:** Analyse Resume for Placement Preparation
- **US-06:** Get an Overall Resume Score

**Requirement IDs covered:** FR-03, FR-04, FR-05, DR-01, NFR-04, NFR-08

**Why grouped together:** Skill extraction feeds directly into the analysis engine, and the analysis engine produces the score — these three are one continuous computation, not separable features.

---

## EPIC 3 — Feedback & Explainability

**Goal:** Make the score and analysis actually useful and trustworthy to the student.

**Stories:**

- **US-07:** Identify Areas That Need Improvement
- **US-08:** Get Resume Improvement Suggestions
- **US-09:** Understand the Score and Recommendations

**Requirement IDs covered:** FR-06, FR-07, FR-11, NFR-05, NFR-08

**Why grouped together:** A raw score alone isn't enough — students asked (survey/faculty interview) for *what's wrong*, *what to do about it*, and *why*. These three are the "explain yourself" layer sitting on top of EPIC 2's output.

---

## EPIC 4 — Job / Internship Matching

**Goal:** Connect the analysed resume to real opportunities.

**Stories:**

- **US-10:** Compare Resume with a Job Description
- **US-11:** Find Relevant Job or Internship Opportunities
- **US-12:** View Matching and Missing Skills

**Requirement IDs covered:** FR-08, FR-09, FR-10, DR-02, DR-03, DR-04

**Why grouped together:** All three depend on skill extraction (EPIC 2) being done first, and together they form the full matching experience: compare → discover → see the gap.

---

## EPIC 5 — Placement Staff Access & Reporting

**Goal:** Give placement officers and counselors role-appropriate visibility into student data.

**Stories:**

- **US-13:** View Student Resume Analysis
- **US-14:** View Placement Dashboard and Reports

**Requirement IDs covered:** FR-12, FR-13, DR-05

**Why grouped together:** Both are staff-facing views built on top of data that EPICs 2–4 already generate — this EPIC adds no new analysis, just new (permissioned) ways to look at it.

---

## EPIC 6 — Security, Privacy & Governance

**Goal:** Make sure access, data handling, and automated decisions stay safe, consented, and fair.

**Stories:**

- **US-15:** Manage Role-Based Access
- **US-16:** Protect Student Resume Data
- **US-17:** Keep Automated Results as Supporting Information
- **US-18:** Check Scoring and Matching for Fairness

**Requirement IDs covered:** FR-15, NFR-03, NFR-07, NFR-09, DR-06, DR-07, DR-08, DR-09

**Why grouped together:** None of these are user-facing "features" — they're constraints that must wrap around every other EPIC (who can see what, how data is retained, that a score never auto-decides someone's placement, and that scoring doesn't discriminate).

---

## EPIC 7 — System Quality & Maintainability

**Goal:** Keep the codebase changeable as the team grows the system sprint over sprint.

**Stories:**

- **US-19:** Keep Core Components Maintainable

**Requirement IDs covered:** NFR-10

**Why its own EPIC:** It's a cross-cutting engineering concern (parsing/scoring/matching stay decoupled) rather than a user-facing capability, so it doesn't belong inside any of the feature EPICs above — but it still needs to show up on the backlog so it gets sprint time (code review discipline, module boundaries, docs) instead of being silently skipped.

---

## 5.1 EPIC Summary Table

| EPIC | Title | Stories | Priority Mix |
|---|---|---|---|
| 1 | Resume Upload & Processing | US-01, US-02, US-03 | Must Have |
| 2 | Resume Scoring & Analysis | US-04, US-05, US-06 | Must Have |
| 3 | Feedback & Explainability | US-07, US-08, US-09 | Must Have |
| 4 | Job / Internship Matching | US-10, US-11, US-12 | Must Have |
| 5 | Placement Staff Access & Reporting | US-13, US-14 | Should Have |
| 6 | Security, Privacy & Governance | US-15, US-16, US-17, US-18 | Must Have |
| 7 | System Quality & Maintainability | US-19 | Should Have |

## 5.2 Dependency Order

**EPIC 1 → EPIC 2 → EPIC 3 and EPIC 4 in parallel → EPIC 5**

- **EPIC 1** comes first because the system must accept and process resumes.
- **EPIC 2** depends on the processed resume data from EPIC 1.
- **EPIC 3** and **EPIC 4** can run in parallel because both depend on EPIC 2.
- **EPIC 5** depends on EPICs 2–4 having real data.
- **EPIC 6** and **EPIC 7** run **throughout**, not as a single later sprint, since access control and maintainability apply to every EPIC from day one.
- EPIC 6 and EPIC 7 also get a dedicated hardening pass once the core flow (EPICs 1–4) works end to end.
