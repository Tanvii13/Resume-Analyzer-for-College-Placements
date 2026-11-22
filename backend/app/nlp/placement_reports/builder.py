"""
Placement Reports and Insights builder.

Sprint 5 Module D (US-15: placement dashboard and reports).

Aggregates existing per-student NLP results (Sprint 2 profile, Sprint 3 analysis, Sprint 4
job matching and/or the Sprint 5 Module A staff analysis) into one PlacementReport:

- readiness statistics, score-label distribution, weakest score components
- department breakdown with small-group suppression
- common skill gaps (from Sprint 4 job comparisons) and common demonstrated skills
- frequent resume weaknesses (from Sprint 3 improvement areas)
- training / workshop recommendations from `training_catalog`, each with its evidence
- evidence-backed insights with a confidence level
- limitations computed from the data actually supplied

Counting rules: every statistic counts students, not resumes or comparisons; each student
is counted at most once per issue or skill. Weakness percentages use students with a resume
analysis as the denominator; skill-gap percentages use students with job comparisons.

Privacy: only aggregates are produced. Before returning, the serialized report is checked
for every student's name, email, phone, reference id and filename; if any appear, a
PrivacyViolationError is raised instead of returning the report.

Deterministic, no I/O, no database, no LLM. Never mutates its inputs.
"""

from __future__ import annotations

import re
import statistics
from collections import Counter, defaultdict
from collections.abc import Iterable

from app.nlp.analysis.explainability import COMPONENT_INFO
from app.nlp.job_matching import normalize_skill
from app.nlp.placement_reports.schemas import (
    DEFAULT_MIN_GROUP_SIZE,
    PLACEMENT_REPORT_VERSION,
    ComponentAverage,
    ConfidenceLevel,
    DataCoverage,
    GroupSummary,
    Insight,
    InsightType,
    LabelShare,
    PlacementReport,
    Priority,
    PrivacySummary,
    ReadinessSummary,
    ScoreStatistics,
    SkillGapStat,
    SkillPresence,
    StudentRecord,
    TrainingRecommendation,
    WeaknessStat,
)
from app.nlp.placement_reports.training_catalog import WEAKNESS_PROGRAMS, program_for_skill

TRIGGER_PERCENTAGE = 20.0  # recommend a program when at least this share of students need it
TRIGGER_MIN_STUDENTS = 2  # ... and at least this many students
HIGH_PRIORITY_PERCENTAGE = 50.0
MEDIUM_PRIORITY_PERCENTAGE = 30.0
LOW_EXTRACTION_CONFIDENCE = 0.6
LARGE_COHORT = 30
MEDIUM_COHORT = 10
TOP_N = 10
SCORE_LABEL_ORDER = ("Excellent", "Good", "Fair", "Needs Improvement")


class PrivacyViolationError(RuntimeError):
    """Raised if personal data would appear in an aggregated report."""


class _Student:
    """Facts extracted from one record. Never stored in the report."""

    def __init__(self, record: StudentRecord) -> None:
        self.record = record
        a, s, p = record.analysis, record.staff_analysis, record.profile
        self.department = (record.department or "").strip() or "Unspecified"
        self.score: float | None = None
        self.label: str | None = None
        self.components: dict[str, float] = {}
        self.issues: dict[str, tuple[str, str, str, str | None]] = {}
        self.skills: set[str] = set()
        self.missing_required: dict[str, set[str]] = defaultdict(set)  # skill -> role titles
        self.missing_preferred: dict[str, set[str]] = defaultdict(set)
        self.partial: set[str] = set()
        self.has_job_data = False
        self.low_confidence = False
        self.module_errors = False
        self.versions: dict[str, str] = {}

        if a is not None:
            self.score = a.overall_score
            self.label = getattr(a.score_label, "value", a.score_label)
            for name, comp in a.component_scores.items():
                if comp.max_score:
                    self.components[name] = 100.0 * comp.score / comp.max_score
            if a.improvement_areas:
                for i in a.improvement_areas.issues:
                    self.issues[i.issue_id] = (i.title, _v(i.category), _v(i.severity), i.related_score_component)
            conf = a.analysis_metadata.extraction_confidence
            self.low_confidence = conf is not None and conf < LOW_EXTRACTION_CONFIDENCE
            self.module_errors = bool(a.analysis_metadata.errors)
            self.versions["sprint3_analysis"] = a.analyzer_version
            if a.rule_version:
                self.versions["scoring_rules"] = a.rule_version
        elif s is not None:
            ov = s.resume_overview.overall_score
            self.score, self.label = ov.overall_score, ov.score_label
            imp = s.improvement_overview
            for item in (imp.critical_missing_sections + imp.weak_resume_sections + imp.content_issues
                         + imp.formatting_issues):
                self.issues.setdefault(item.item_id, (item.title, item.affected_section or "general",
                                                      (item.severity or "info").lower(), None))

        if s is not None:
            self.versions["staff_insights"] = s.adapter_version
            self.skills.update(x.name for x in s.skills_overview.technical_skills)
        if p is not None:
            self.skills.update(x.canonical_name for x in p.technical_skills)
            self.versions["candidate_profile"] = p.pipeline_version
            if p.metadata and p.metadata.overall_confidence is not None and a is None:
                self.low_confidence = p.metadata.overall_confidence < LOW_EXTRACTION_CONFIDENCE

        for fit in record.job_fits:
            if fit.metadata.errors:
                self.module_errors = True
            if fit.skill_gap is None:
                continue
            self.has_job_data = True
            role = (fit.job.title if fit.job else None) or "Unnamed role"
            g = fit.skill_gap
            for item in g.missing_required:
                if not item.from_responsibilities_only:
                    self.missing_required[item.skill].add(role)
            for item in g.missing_preferred:
                self.missing_preferred[item.skill].add(role)
            self.partial.update(i.skill for i in g.partial_required + g.partial_preferred)
            self.versions["job_matching"] = fit.workflow_version
        if record.ranking is not None and record.ranking.ranked_opportunities:
            self.has_job_data = True
            for opp in record.ranking.ranked_opportunities:
                role = opp.title or "Unnamed role"
                for skill in opp.missing_required:
                    self.missing_required[skill].add(role)
                for skill in opp.missing_preferred:
                    self.missing_preferred[skill].add(role)
                self.partial.update(opp.partial_required + opp.partial_preferred)
            self.versions["opportunity_ranking"] = record.ranking.ranker_version
        for skill in self.missing_required:
            self.missing_preferred.pop(skill, None)

    @property
    def analyzed(self) -> bool:
        return self.score is not None

    @property
    def usable(self) -> bool:
        return self.analyzed or bool(self.issues) or bool(self.skills) or self.has_job_data


def _v(x) -> str:
    return str(getattr(x, "value", x))


def _pct(part: int, whole: int) -> float:
    return round(100.0 * part / whole, 1) if whole else 0.0


def _category(skill: str) -> str:
    return normalize_skill(skill).category or "Other"


class PlacementReportBuilder:
    """Builds a privacy-safe, evidence-backed placement report from per-student NLP results."""

    def __init__(self, min_group_size: int = DEFAULT_MIN_GROUP_SIZE) -> None:
        if min_group_size < 1:
            raise ValueError("min_group_size must be at least 1")
        self.min_group_size = min_group_size

    # ------------------------------------------------------------------ API

    def build(
        self,
        records: Iterable[StudentRecord],
        title: str = "Placement preparation report",
        generated_at: str | None = None,
    ) -> PlacementReport:
        records = list(records)
        seen: set[str] = set()
        students: list[_Student] = []
        duplicates = 0
        for r in records:
            if r.student_ref in seen:
                duplicates += 1
                continue
            seen.add(r.student_ref)
            students.append(_Student(r))
        unusable = sum(1 for s in students if not s.usable)
        students = [s for s in students if s.usable]

        analyzed = [s for s in students if s.analyzed]
        with_issues = [s for s in students if s.issues or s.analyzed]
        with_jobs = [s for s in students if s.has_job_data]

        coverage = DataCoverage(
            students_in_input=len(records),
            students_analyzed=len(analyzed),
            students_with_job_matching=len(with_jobs),
            students_with_low_extraction_confidence=sum(s.low_confidence for s in students),
            students_with_module_errors=sum(s.module_errors for s in students),
            duplicate_records_ignored=duplicates,
            records_without_usable_data=unusable,
        )
        readiness = self._readiness(analyzed)
        weaknesses = self._weaknesses(with_issues)
        gaps = self._skill_gaps(with_jobs)
        departments, suppressed = self._departments(students)
        report = PlacementReport(
            title=title,
            batch_years=sorted({s.record.batch_year for s in students if s.record.batch_year is not None}),
            departments_included=len({s.department for s in students}),
            generated_at=generated_at,
            coverage=coverage,
            readiness=readiness,
            department_breakdown=departments,
            common_skill_gaps=gaps,
            resume_weaknesses=weaknesses,
            common_skills=self._common_skills(students),
            training_recommendations=self._training(with_issues, with_jobs),
            privacy=self._privacy(students, suppressed),
            source_versions=self._versions(students),
            configuration={
                "min_group_size": self.min_group_size,
                "trigger_percentage": TRIGGER_PERCENTAGE,
                "trigger_min_students": TRIGGER_MIN_STUDENTS,
                "low_extraction_confidence": LOW_EXTRACTION_CONFIDENCE,
                "report_version": PLACEMENT_REPORT_VERSION,
            },
        )
        report.insights = self._insights(report)
        report.limitations = self._limitations(report)
        self._assert_no_personal_data(report, records)
        return report

    # ------------------------------------------------------------ sections

    @staticmethod
    def _readiness(analyzed: list[_Student]) -> ReadinessSummary:
        scores = [s.score for s in analyzed]
        stats = ScoreStatistics(count=len(scores))
        if scores:
            stats.mean = round(statistics.fmean(scores), 2)
            stats.median = round(statistics.median(scores), 2)
            stats.minimum = round(min(scores), 2)
            stats.maximum = round(max(scores), 2)
            stats.std_dev = round(statistics.pstdev(scores), 2) if len(scores) > 1 else 0.0
        labels = Counter(s.label for s in analyzed if s.label)
        distribution = [LabelShare(label=lbl, students=labels[lbl], percentage=_pct(labels[lbl], len(analyzed)))
                        for lbl in SCORE_LABEL_ORDER if labels.get(lbl)]
        comp_values: dict[str, list[float]] = defaultdict(list)
        for s in analyzed:
            for name, pct in s.components.items():
                comp_values[name].append(pct)
        components = sorted(
            (ComponentAverage(component=name, label=COMPONENT_INFO.get(name, (name.replace("_", " ").title(), ""))[0],
                              average_percentage=round(min(100.0, statistics.fmean(v)), 1), students=len(v))
             for name, v in comp_values.items()),
            key=lambda c: (c.average_percentage, c.component),
        )
        return ReadinessSummary(score_statistics=stats, label_distribution=distribution, component_averages=components,
                                below_fair_count=labels.get("Needs Improvement", 0))

    @staticmethod
    def _weaknesses(students: list[_Student]) -> list[WeaknessStat]:
        counts: Counter[str] = Counter()
        meta: dict[str, Counter] = defaultdict(Counter)
        for s in students:
            for issue_id, info in s.issues.items():
                counts[issue_id] += 1
                meta[issue_id][info] += 1
        out = []
        for issue_id, n in counts.items():
            title, category, severity, component = meta[issue_id].most_common(1)[0][0]
            out.append(WeaknessStat(issue_id=issue_id, title=title, category=category, severity=severity,
                                    students_affected=n, percentage=_pct(n, len(students)),
                                    related_score_component=component))
        return sorted(out, key=lambda w: (-w.students_affected, w.issue_id))[:TOP_N]

    @staticmethod
    def _skill_gaps(students: list[_Student]) -> list[SkillGapStat]:
        out = []
        for level, attr in (("required", "missing_required"), ("preferred", "missing_preferred")):
            counts: Counter[str] = Counter()
            roles: dict[str, set[str]] = defaultdict(set)
            for s in students:
                for skill, rs in getattr(s, attr).items():
                    counts[skill] += 1
                    roles[skill].update(rs)
            for skill, n in counts.items():
                out.append(SkillGapStat(
                    skill=skill, category=_category(skill), level=level, students_missing=n,
                    students_partial=sum(1 for s in students if skill in s.partial),
                    percentage_of_matched_students=_pct(n, len(students)),
                    roles_requiring=sorted(roles[skill])[:5],
                ))
        return sorted(out, key=lambda g: (g.level != "required", -g.students_missing, g.skill))[:TOP_N]

    @staticmethod
    def _common_skills(students: list[_Student]) -> list[SkillPresence]:
        counts = Counter(skill for s in students for skill in s.skills)
        return [SkillPresence(skill=k, category=_category(k), students=n, percentage=_pct(n, len(students)))
                for k, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:TOP_N]]

    def _departments(self, students: list[_Student]) -> tuple[list[GroupSummary], int]:
        groups: dict[str, list[_Student]] = defaultdict(list)
        for s in students:
            groups[s.department].append(s)
        out, suppressed = [], 0
        for name in sorted(groups):
            members = groups[name]
            if len(members) < self.min_group_size:
                suppressed += 1
                out.append(GroupSummary(group=name, suppressed=True,
                                        suppression_reason=f"Fewer than {self.min_group_size} students; hidden to protect privacy."))
                continue
            scores = [m.score for m in members if m.analyzed]
            weak = Counter(i for m in members for i in m.issues)
            top = weak.most_common(1)
            title = None
            if top:
                title = next(m.issues[top[0][0]][0] for m in members if top[0][0] in m.issues)
            out.append(GroupSummary(group=name, students=len(members),
                                    average_score=round(statistics.fmean(scores), 2) if scores else None,
                                    most_common_weakness=title))
        return out, suppressed

    @staticmethod
    def _priority(pct: float, critical: bool) -> Priority:
        if pct >= HIGH_PRIORITY_PERCENTAGE or (critical and pct >= MEDIUM_PRIORITY_PERCENTAGE):
            return Priority.HIGH
        if pct >= MEDIUM_PRIORITY_PERCENTAGE:
            return Priority.MEDIUM
        return Priority.LOW

    def _training(self, with_issues: list[_Student], with_jobs: list[_Student]) -> list[TrainingRecommendation]:
        recs: list[TrainingRecommendation] = []
        for prog in WEAKNESS_PROGRAMS:
            affected = [s for s in with_issues if any(i in s.issues for i in prog.issue_ids)]
            soft_gap = [s for s in with_jobs if any(_category(k) in prog.skill_categories for k in s.missing_required)]
            affected_ids = {id(s) for s in affected} | {id(s) for s in soft_gap}
            n = len(affected_ids)
            denom = len({id(s) for s in with_issues} | {id(s) for s in soft_gap}) or 1
            pct = _pct(n, denom)
            if n < TRIGGER_MIN_STUDENTS or pct < TRIGGER_PERCENTAGE:
                continue
            per_issue = Counter(i for s in affected for i in s.issues if i in prog.issue_ids)
            evidence = [f"{issue}: {c} of {len(with_issues)} analysed students ({_pct(c, len(with_issues))}%)"
                        for issue, c in sorted(per_issue.items(), key=lambda kv: (-kv[1], kv[0]))]
            if soft_gap:
                evidence.append(f"{len(soft_gap)} of {len(with_jobs)} students compared with jobs lack a required soft skill")
            critical = any(s.issues[i][2] == "critical" for s in affected for i in prog.issue_ids if i in s.issues)
            recs.append(TrainingRecommendation(
                program_id=prog.program_id, title=prog.title, format=prog.format, description=prog.description,
                addresses=sorted(per_issue) + (sorted({k for s in soft_gap for k in s.missing_required
                                                      if _category(k) in prog.skill_categories})),
                students_affected=n, percentage=pct, priority=self._priority(pct, critical), evidence=evidence,
                rationale=f"{n} students ({pct}%) show the weaknesses this program addresses.",
            ))

        by_program: dict[str, tuple[object, set[int], Counter]] = {}
        for s in with_jobs:
            for skill in s.missing_required:
                prog = program_for_skill(skill, _category(skill))
                if prog is None or prog.program_id == "TRN_SOFT_SKILLS":
                    continue
                entry = by_program.setdefault(prog.program_id, (prog, set(), Counter()))
                entry[1].add(id(s))
                entry[2][skill] += 1
        for prog_id, (prog, ids, skills) in by_program.items():
            n, pct = len(ids), _pct(len(ids), len(with_jobs))
            if n < TRIGGER_MIN_STUDENTS or pct < TRIGGER_PERCENTAGE:
                continue
            top = sorted(skills.items(), key=lambda kv: (-kv[1], kv[0]))
            recs.append(TrainingRecommendation(
                program_id=prog_id, title=prog.title, format=prog.format, description=prog.description,
                addresses=[k for k, _ in top],
                students_affected=n, percentage=pct, priority=self._priority(pct, False),
                evidence=[f"{k}: missing for {c} of {len(with_jobs)} students compared with jobs ({_pct(c, len(with_jobs))}%)"
                          for k, c in top[:5]],
                rationale=f"{n} of {len(with_jobs)} students compared with job descriptions lack required skills it covers.",
            ))
        order = {Priority.HIGH: 0, Priority.MEDIUM: 1, Priority.LOW: 2}
        return sorted(recs, key=lambda r: (order[r.priority], -r.students_affected, r.program_id))

    @staticmethod
    def _versions(students: list[_Student]) -> dict[str, list[str]]:
        out: dict[str, set[str]] = defaultdict(set)
        for s in students:
            for k, v in s.versions.items():
                if v:
                    out[k].add(v)
        return {k: sorted(v) for k, v in sorted(out.items())}

    def _privacy(self, students: list[_Student], suppressed: int) -> PrivacySummary:
        small = 0 < len(students) < self.min_group_size
        notes = [
            "Only aggregated counts are included: no names, contact details, student ids, filenames or resume text.",
            f"Groups with fewer than {self.min_group_size} students are suppressed.",
            "Share this report only with authorised placement staff, following institutional data rules.",
        ]
        if small:
            notes.append(f"The whole cohort has fewer than {self.min_group_size} students, so even aggregate figures "
                         "could identify individuals.")
        return PrivacySummary(min_group_size=self.min_group_size, suppressed_groups=suppressed,
                              small_cohort_warning=small, notes=notes)

    # ------------------------------------------------------------ insights

    @staticmethod
    def _confidence(n: int, coverage: float = 1.0) -> ConfidenceLevel:
        if n >= LARGE_COHORT and coverage >= 0.8:
            return ConfidenceLevel.HIGH
        if n >= MEDIUM_COHORT:
            return ConfidenceLevel.MEDIUM
        return ConfidenceLevel.LOW

    def _insights(self, r: PlacementReport) -> list[Insight]:
        out: list[Insight] = []
        n = r.coverage.students_analyzed
        stats = r.readiness.score_statistics

        def add(kind: InsightType, statement: str, evidence: list[str], metrics: dict, conf: ConfidenceLevel):
            out.append(Insight(insight_id=f"INS_{len(out) + 1:02d}", type=kind, statement=statement,
                               evidence=evidence, metrics=metrics, confidence=conf))

        if n:
            needs = r.readiness.below_fair_count
            add(InsightType.CONCERN if needs / n >= 0.3 else InsightType.STRENGTH,
                f"Average resume readiness is {stats.mean:.1f}/100 (median {stats.median:.1f}); "
                f"{needs} of {n} students ({_pct(needs, n)}%) are rated 'Needs Improvement'.",
                [f"{s.label}: {s.students} students ({s.percentage}%)" for s in r.readiness.label_distribution],
                {"mean_score": stats.mean, "median_score": stats.median, "needs_improvement": needs, "students": n},
                self._confidence(n))
            comps = r.readiness.component_averages
            if len(comps) >= 2:
                weakest, strongest = comps[0], comps[-1]
                add(InsightType.CONCERN,
                    f"{weakest.label} is the weakest scoring area (average {weakest.average_percentage:.0f}% of its "
                    f"maximum), compared with {strongest.label} at {strongest.average_percentage:.0f}%.",
                    [f"{c.label}: {c.average_percentage}%" for c in comps],
                    {"weakest_average_pct": weakest.average_percentage, "strongest_average_pct": strongest.average_percentage},
                    self._confidence(n))
        if r.resume_weaknesses:
            w = r.resume_weaknesses[0]
            denom = max(1, round(w.students_affected * 100 / w.percentage)) if w.percentage else w.students_affected
            add(InsightType.CONCERN,
                f"The most frequent resume weakness is '{w.title}', affecting {w.students_affected} of {denom} "
                f"students ({w.percentage}%).",
                [f"{x.title}: {x.students_affected} students ({x.percentage}%)" for x in r.resume_weaknesses[:5]],
                {"students_affected": w.students_affected, "percentage": w.percentage},
                self._confidence(denom))
        jobs_n = r.coverage.students_with_job_matching
        required = [g for g in r.common_skill_gaps if g.level == "required"]
        if required:
            g = required[0]
            add(InsightType.CONCERN,
                f"{g.skill} is the most common missing required skill: {g.students_missing} of {jobs_n} students "
                f"compared with job descriptions lack it ({g.percentage_of_matched_students}%).",
                [f"{x.skill} ({x.category}): {x.students_missing} students" for x in required[:5]]
                + [f"Required by: {', '.join(g.roles_requiring)}"],
                {"students_missing": g.students_missing, "students_compared": jobs_n},
                self._confidence(jobs_n, jobs_n / max(1, r.coverage.students_in_input)))
        if r.common_skills:
            top = r.common_skills[:3]
            add(InsightType.STRENGTH,
                "Most commonly demonstrated skills: " + ", ".join(f"{s.skill} ({s.percentage}%)" for s in top) + ".",
                [f"{s.skill}: {s.students} students" for s in r.common_skills[:5]],
                {"top_skill_students": top[0].students}, self._confidence(n or len(r.common_skills)))
        shown = [d for d in r.department_breakdown if not d.suppressed and d.average_score is not None]
        if len(shown) >= 2:
            hi = max(shown, key=lambda d: (d.average_score, d.group))
            lo = min(shown, key=lambda d: (d.average_score, d.group))
            if hi.average_score - lo.average_score >= 10:
                add(InsightType.COMPARISON,
                    f"Average readiness differs by {hi.average_score - lo.average_score:.1f} points between "
                    f"{hi.group} ({hi.average_score:.1f}) and {lo.group} ({lo.average_score:.1f}).",
                    [f"{d.group}: {d.average_score} over {d.students} students" for d in shown],
                    {"difference": round(hi.average_score - lo.average_score, 2)},
                    self._confidence(min(hi.students or 0, lo.students or 0)))
        total = r.coverage.students_in_input
        if total and jobs_n / total < 0.5:
            add(InsightType.DATA_QUALITY,
                f"Only {jobs_n} of {total} students have been compared with job descriptions, so skill-gap findings "
                "may not represent the whole batch.",
                [f"Students with job comparisons: {jobs_n}"], {"students_compared": jobs_n, "students": total},
                ConfidenceLevel.HIGH)
        if r.coverage.students_with_low_extraction_confidence:
            k = r.coverage.students_with_low_extraction_confidence
            add(InsightType.DATA_QUALITY,
                f"{k} resumes could not be read reliably; their results may understate those students' profiles.",
                [f"Extraction confidence below {LOW_EXTRACTION_CONFIDENCE}: {k} students"], {"students": k},
                ConfidenceLevel.HIGH)
        return out

    def _limitations(self, r: PlacementReport) -> list[str]:
        c = r.coverage
        out = []
        if c.students_analyzed == 0:
            out.append("No analysed resumes were supplied, so no readiness statistics are available.")
        elif c.students_analyzed < LARGE_COHORT:
            out.append(f"Only {c.students_analyzed} students were analysed; with a small group, a few students can change "
                       "the percentages considerably.")
        if c.students_with_job_matching == 0:
            out.append("No job-description comparisons were supplied, so skill gaps and skill-training recommendations "
                       "are not available.")
        elif c.students_with_job_matching < c.students_in_input - c.duplicate_records_ignored:
            out.append(f"Skill gaps are based on the {c.students_with_job_matching} students who were compared with job "
                       "descriptions, not the whole batch.")
        if c.students_with_low_extraction_confidence:
            out.append(f"{c.students_with_low_extraction_confidence} resumes had low extraction confidence; missing items "
                       "for those students may be reading errors rather than real gaps.")
        if c.students_with_module_errors:
            out.append(f"Part of the analysis failed for {c.students_with_module_errors} students; their results are "
                       "incomplete.")
        if c.records_without_usable_data:
            out.append(f"{c.records_without_usable_data} records had no usable analysis and were left out.")
        if c.duplicate_records_ignored:
            out.append(f"{c.duplicate_records_ignored} duplicate records for the same student were ignored.")
        if r.privacy.suppressed_groups:
            out.append(f"{r.privacy.suppressed_groups} department groups were hidden because they had fewer than "
                       f"{r.privacy.min_group_size} students.")
        if any(len(v) > 1 for v in r.source_versions.values()):
            out.append("Results were produced by different analysis versions and may not be fully comparable.")
        if len(r.batch_years) > 1:
            out.append("The report combines several batch years.")
        out.append("Findings describe what resumes show. A 'missing' skill may simply not be written on the resume, "
                   "and skills outside the system's skill list are not recognised.")
        out.append("Training recommendations are rule-based suggestions from the detected patterns, not an assessment "
                   "of individual students.")
        return out

    # ------------------------------------------------------------ privacy

    @staticmethod
    def _assert_no_personal_data(report: PlacementReport, records: list[StudentRecord]) -> None:
        text = report.model_dump_json().lower()
        needles: set[str] = set()
        for r in records:
            needles.add(r.student_ref)
            p = r.profile
            if p is not None:
                needles.update(filter(None, [p.contact.full_name, p.contact.email, p.contact.phone, p.filename,
                                             p.contact.linkedin_url, p.contact.github_url]))
            if r.staff_analysis is not None:
                needles.update(filter(None, [r.staff_analysis.candidate_name, r.staff_analysis.filename]))
            if r.analysis is not None:
                needles.add(r.analysis.filename)
            needles.update(f.candidate_name for f in r.job_fits if f.candidate_name)
        leaks = []
        for n in needles:
            n = (n or "").strip().lower()
            if len(n) < 4:
                continue
            if re.search(rf"(?<![a-z0-9]){re.escape(n)}(?![a-z0-9])", text):
                leaks.append(n)
        if leaks:
            raise PrivacyViolationError(f"Report would expose {len(leaks)} personal value(s); refusing to return it.")


def build_placement_report(
    records: Iterable[StudentRecord],
    title: str = "Placement preparation report",
    generated_at: str | None = None,
    min_group_size: int = DEFAULT_MIN_GROUP_SIZE,
) -> PlacementReport:
    return PlacementReportBuilder(min_group_size=min_group_size).build(records, title=title, generated_at=generated_at)


__all__ = ["PlacementReportBuilder", "PrivacyViolationError", "build_placement_report"]
