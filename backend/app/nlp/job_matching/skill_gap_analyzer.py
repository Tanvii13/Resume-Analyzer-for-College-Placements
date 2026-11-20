"""
Skill Gap Analysis Engine.

Sprint 4 Module D (US-13: view matching and missing skills).

Builds on the Module C JobMatchResult - it does not re-match skills - and adds:

1. Required / preferred / soft skills kept separate, each as matched, partial
   (related skill only) or missing, with the resume evidence for every match.
2. Either-or requirements. A JD line such as "Python or Java" or "SQL databases such as
   PostgreSQL or MySQL" is one requirement: if the candidate has any skill in the group,
   the others are marked `satisfied_by_alternative` instead of missing.
3. Skills only mentioned in the responsibilities text ("work with QA teams") are flagged
   as `from_responsibilities_only` and ranked as less important.
4. Importance-ranked gaps with student-facing advice. Advice never claims the student has
   a skill; it points out related skills they already have and how to show the new one.
5. Eligibility checks (CGPA / percentage, graduating batch, branch, degree, backlogs)
   against the JD rules - met, not met, or unknown when the resume lacks the data.

Deterministic, rule-based, no external services.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from app.nlp.job_matching.matcher_schemas import (
    EvidenceSource,
    JobMatchResult,
    MatchCategory,
    RequirementMatch,
    RequirementType,
)
from app.nlp.job_matching.schemas import JobSkillRequirement, ParsedJobDescription
from app.nlp.job_matching.skill_engine import (
    SkillEquivalenceEngine,
    SkillNormalizer,
    get_equivalence_engine,
    get_skill_normalizer,
)
from app.nlp.job_matching.skill_gap_schemas import (
    SKILL_GAP_ANALYZER_VERSION,
    AlternativeGroup,
    EligibilityCheck,
    EligibilityStatus,
    GapImportance,
    SkillCoverage,
    SkillGapItem,
    SkillGapReport,
    SkillGapStatus,
    SkillRequirementLevel,
)
from app.nlp.schemas import CandidateProfile, EducationEntry

SATISFIED_CATEGORIES = {MatchCategory.EXACT_MATCH, MatchCategory.ALIAS_MATCH, MatchCategory.EQUIVALENT_MATCH}
LEVEL_BASE_IMPORTANCE = {
    SkillRequirementLevel.REQUIRED: 0.85,
    SkillRequirementLevel.PREFERRED: 0.45,
    SkillRequirementLevel.SOFT_SKILL: 0.30,
}
CRITICAL_THRESHOLD = 0.80
IMPORTANT_THRESHOLD = 0.45
ALTERNATIVE_MARKERS = re.compile(r"\b(?:or|either)\b|\s/\s", re.IGNORECASE)

# Branch names as written in JDs and resumes -> one canonical key.
BRANCH_ALIASES: dict[str, str] = {
    "computer science": "cse",
    "computer science and engineering": "cse",
    "computer science & engineering": "cse",
    "computer engineering": "cse",
    "cse": "cse",
    "cs": "cse",
    "information technology": "it",
    "it": "it",
    "information and communication technology": "ict",
    "information & communication technology": "ict",
    "ict": "ict",
    "electronics and communication engineering": "ece",
    "electronics & communication engineering": "ece",
    "electronics and communication": "ece",
    "ece": "ece",
    "electrical engineering": "ee",
    "electrical and electronics engineering": "eee",
    "ee": "ee",
    "eee": "eee",
    "mechanical engineering": "me",
    "me": "me",
    "civil engineering": "ce",
    "chemical engineering": "che",
    "artificial intelligence and machine learning": "aiml",
    "artificial intelligence and data science": "aids",
    "aiml": "aiml",
    "ai&ds": "aids",
    "data science": "ds",
    "mathematics and computing": "mnc",
    "computer applications": "ca",
}
# Broad field skills that a specific tool on the resume clearly demonstrates. Used only to
# upgrade "missing" to "partial" (never to "matched"): the advice tells the student to name the
# skill explicitly. Kept deliberately small and conservative.
IMPLIED_BY: dict[str, list[str]] = {
    "machine learning": ["PyTorch", "TensorFlow", "scikit-learn", "Keras", "XGBoost"],
    "deep learning": ["PyTorch", "TensorFlow", "Keras"],
    "artificial intelligence": ["Machine Learning", "Deep Learning", "PyTorch", "TensorFlow",
                                "Natural Language Processing (NLP)", "Computer Vision"],
    "data analysis": ["Pandas", "Power BI", "Tableau"],
    "data visualization": ["Matplotlib", "Power BI", "Tableau"],
}

BRANCH_ALIASES.update({"electronics": "ece", "electrical": "ee", "mechanical": "me", "civil": "ce"})
KNOWN_BRANCH_KEYS = set(BRANCH_ALIASES.values())
CIRCUIT_BRANCHES = {"cse", "it", "ict", "ece", "ee", "eee", "aiml", "aids", "ds", "mnc"}
DEGREE_RANK = {"doctorate": 5, "masters": 4, "bachelors": 3, "diploma": 2, "secondary": 1}


def branch_key(name: str | None) -> str | None:
    if not name:
        return None
    cleaned = re.sub(r"\s+", " ", name.strip().lower().replace("b.tech in", "").replace("b.e. in", "")).strip(" .")
    if cleaned in BRANCH_ALIASES:
        return BRANCH_ALIASES[cleaned]
    for alias, key in sorted(BRANCH_ALIASES.items(), key=lambda kv: -len(kv[0])):
        if len(alias) > 3 and alias in cleaned:
            return key
    return cleaned


def main_degree(profile: CandidateProfile) -> EducationEntry | None:
    """The highest-level non-school qualification (the one placement rules refer to)."""
    candidates = [e for e in profile.education if (e.degree_level or "") != "secondary" and e.degree]
    if not candidates:
        return None
    return min(candidates, key=lambda e: (-DEGREE_RANK.get(e.degree_level or "", 0), -(e.graduation_year or 0)))


class SkillGapAnalyzer:
    """Turns a Module C JobMatchResult into a prioritized, explainable skill gap report."""

    def __init__(
        self,
        normalizer: SkillNormalizer | None = None,
        equivalence_engine: SkillEquivalenceEngine | None = None,
    ) -> None:
        self.normalizer = normalizer or get_skill_normalizer()
        self.equivalence_engine = equivalence_engine or get_equivalence_engine()
        self.version = SKILL_GAP_ANALYZER_VERSION

    # ------------------------------------------------------------------ API

    def analyze(
        self,
        candidate: CandidateProfile,
        job: ParsedJobDescription,
        match_result: JobMatchResult,
    ) -> SkillGapReport:
        candidate_skills = self._candidate_skill_names(candidate)
        listed_skills = self._listed_in_skills_section(candidate)
        jd_skills = self._jd_skill_index(job)
        responsibilities = [r.strip().lower() for r in job.responsibilities]

        items: list[SkillGapItem] = []
        for m in match_result.all_matches:
            level = self._level(m.requirement_type)
            if level is None:
                continue
            items.append(self._item(m, level, jd_skills.get((level, m.requirement_name.lower())),
                                    responsibilities, candidate_skills, listed_skills))

        groups = self._alternative_groups(items)
        items = [self._apply_group(i, groups) for i in items]

        report = SkillGapReport(
            job_id=job.job_id,
            job_title=job.title,
            company_name=job.company_name,
            alternative_groups=list(groups.values()),
            analyzer_version=self.version,
        )
        for item in items:
            self._file(report, item)

        report.priority_gaps = self._priority_gaps(items, groups)
        report.visibility_tips = [
            f"You used {i.skill} ({i.candidate_evidence or 'in your work'}) but it is not in your Skills section - list it there."
            for i in items
            if i.status == SkillGapStatus.MATCHED and not i.listed_in_skills_section and i.level != SkillRequirementLevel.SOFT_SKILL
        ]
        report.coverage = self._coverage(items, groups)
        report.experience_gap = self._experience_gap(candidate, job)
        report.eligibility_checks = self._eligibility(candidate, job)
        report.eligibility_status = self._overall_eligibility(report.eligibility_checks)
        if any(i.from_responsibilities_only for i in items if i.level == SkillRequirementLevel.REQUIRED):
            report.warnings.append(
                "Some required skills were only found in the responsibilities text and may not be hard requirements."
            )
        report.summary = self._summary(report)
        return report

    # ------------------------------------------------------------ building

    @staticmethod
    def _level(rtype: RequirementType) -> SkillRequirementLevel | None:
        return {
            RequirementType.REQUIRED_TECHNICAL_SKILL: SkillRequirementLevel.REQUIRED,
            RequirementType.PREFERRED_TECHNICAL_SKILL: SkillRequirementLevel.PREFERRED,
            RequirementType.SOFT_SKILL: SkillRequirementLevel.SOFT_SKILL,
        }.get(rtype)

    @staticmethod
    def _jd_skill_index(job: ParsedJobDescription) -> dict[tuple[SkillRequirementLevel, str], JobSkillRequirement]:
        index: dict[tuple[SkillRequirementLevel, str], JobSkillRequirement] = {}
        for level, skills in (
            (SkillRequirementLevel.REQUIRED, job.required_technical_skills),
            (SkillRequirementLevel.PREFERRED, job.preferred_technical_skills),
            (SkillRequirementLevel.SOFT_SKILL, job.soft_skills),
        ):
            for s in skills:
                index[(level, s.canonical_name.lower())] = s
        return index

    def _candidate_skill_names(self, candidate: CandidateProfile) -> dict[str, str]:
        """lower-case canonical name -> display name, from skills, projects and experience."""
        names: dict[str, str] = {}

        def add(raw: str) -> None:
            if not raw:
                return
            norm = self.normalizer.normalize_skill(raw)
            canonical = norm.canonical_name or raw
            names.setdefault(canonical.lower(), canonical)

        for s in list(candidate.technical_skills) + list(candidate.soft_skills):
            add(s.canonical_name)
        for entry in list(candidate.projects):
            for t in entry.technologies:
                add(t)
        for entry in list(candidate.experience) + list(candidate.internships):
            for t in entry.technologies_used:
                add(t)
        return names

    def _listed_in_skills_section(self, candidate: CandidateProfile) -> set[str]:
        listed: set[str] = set()
        for s in list(candidate.technical_skills) + list(candidate.soft_skills):
            if s.source_section in {"technical_skills", "skills", "soft_skills"}:
                listed.add((self.normalizer.normalize_skill(s.canonical_name).canonical_name or s.canonical_name).lower())
        return listed

    def _related_you_have(self, skill: str, candidate_skills: dict[str, str]) -> list[str]:
        related: list[str] = []
        for name in self.equivalence_engine.get_related_skills(skill) + self.equivalence_engine.get_prerequisites(skill):
            canonical = (self.normalizer.normalize_skill(name).canonical_name or name).lower()
            if canonical in candidate_skills and candidate_skills[canonical] not in related:
                related.append(candidate_skills[canonical])
        # Reverse direction: candidate skills that list this skill as related
        for lower, display in candidate_skills.items():
            if display in related or lower == skill.lower():
                continue
            rel = {r.lower() for r in self.equivalence_engine.get_related_skills(display)}
            if skill.lower() in rel:
                related.append(display)
        return sorted(related)[:4]

    def _item(
        self,
        m: RequirementMatch,
        level: SkillRequirementLevel,
        jd_skill: JobSkillRequirement | None,
        responsibilities: list[str],
        candidate_skills: dict[str, str],
        listed_skills: set[str],
    ) -> SkillGapItem:
        implied_by: str | None = None
        if m.category in SATISFIED_CATEGORIES:
            status = SkillGapStatus.MATCHED
        elif m.category == MatchCategory.RELATED_MATCH:
            status = SkillGapStatus.PARTIAL
        elif m.category == MatchCategory.UNCERTAIN:
            status = SkillGapStatus.UNCERTAIN
        else:
            status = SkillGapStatus.MISSING
            for tool in IMPLIED_BY.get(m.requirement_name.lower(), []):
                tool_key = (self.normalizer.normalize_skill(tool).canonical_name or tool).lower()
                if tool_key in candidate_skills:
                    status, implied_by = SkillGapStatus.PARTIAL, candidate_skills[tool_key]
                    m = m.model_copy(update={"matched_value": implied_by})
                    break

        jd_line = jd_skill.evidence if jd_skill else None
        jd_line_clean = (jd_line or "").strip().lstrip("-•* ").strip().lower()
        resp_only = bool(jd_line_clean) and any(jd_line_clean == r.lstrip("-•* ").strip() for r in responsibilities)

        score = LEVEL_BASE_IMPORTANCE[level]
        if jd_skill is not None and jd_skill.occurrences >= 2:
            score += 0.10
        if jd_line and re.search(r"\b(strong|must|essential|mandatory|proficien|solid)\w*", jd_line, re.IGNORECASE):
            score += 0.10
        if resp_only:
            score -= 0.40
        if status == SkillGapStatus.PARTIAL:
            score -= 0.10
        score = round(max(0.05, min(1.0, score)), 3)
        importance = (
            GapImportance.CRITICAL if score >= CRITICAL_THRESHOLD
            else GapImportance.IMPORTANT if score >= IMPORTANT_THRESHOLD
            else GapImportance.NICE_TO_HAVE
        )

        # Module C labels every profile skill as "explicit_skills_section", even ones the
        # Sprint 2 extractor found only in projects, so check the profile's own source section.
        matched_name = (self.normalizer.normalize_skill(m.matched_value).canonical_name or m.matched_value) if m.matched_value else None
        listed = bool(matched_name) and matched_name.lower() in listed_skills
        if m.evidence_source == EvidenceSource.EXPLICIT_SKILLS_SECTION and not listed and status != SkillGapStatus.MATCHED:
            listed = True
        source = m.evidence_source.value if m.evidence_source != EvidenceSource.NONE else None
        if source == EvidenceSource.EXPLICIT_SKILLS_SECTION.value and status == SkillGapStatus.MATCHED and not listed:
            source = "resume_outside_skills_section"
        related = [] if status == SkillGapStatus.MATCHED else self._related_you_have(m.requirement_name, candidate_skills)

        return SkillGapItem(
            skill=m.requirement_name,
            level=level,
            status=status,
            match_category=m.category.value,
            candidate_evidence=m.matched_value,
            evidence_source=source,
            listed_in_skills_section=listed,
            jd_evidence=jd_line,
            from_responsibilities_only=resp_only,
            importance=importance,
            importance_score=score,
            related_skills_you_have=related,
            explanation=(
                f"{m.requirement_name} is not named on your resume, but your work with {implied_by} shows it."
                if implied_by else self._explain(m, level, status, resp_only)
            ),
            how_to_improve=(
                f"Name {m.requirement_name} explicitly in your Skills section or project bullets - "
                f"your {implied_by} work already demonstrates it."
                if implied_by else self._advice(m, level, status, related, listed)
            ),
        )

    @staticmethod
    def _explain(m: RequirementMatch, level: SkillRequirementLevel, status: SkillGapStatus, resp_only: bool) -> str:
        what = {"required": "a required skill", "preferred": "a preferred skill", "soft_skill": "a soft skill"}[level.value]
        if status == SkillGapStatus.MATCHED:
            text = f"{m.requirement_name} is {what}; your resume shows {m.matched_value or m.requirement_name}."
        elif status == SkillGapStatus.PARTIAL:
            text = (f"{m.requirement_name} is {what}. Your resume shows the related skill {m.matched_value}, "
                    f"which helps but is not the same skill.")
        elif status == SkillGapStatus.UNCERTAIN:
            text = f"{m.requirement_name} could not be checked reliably: {m.rationale}"
        else:
            text = f"{m.requirement_name} is {what} and was not found anywhere in your resume."
        if resp_only:
            text += " It is only mentioned in the job responsibilities, so it may not be a strict requirement."
        return text

    @staticmethod
    def _advice(m, level, status, related, listed) -> str | None:
        skill = m.requirement_name
        if status == SkillGapStatus.MATCHED:
            if not listed and level != SkillRequirementLevel.SOFT_SKILL:
                return f"Add {skill} to your Skills section - you have used it but it is not listed."
            return None
        if level == SkillRequirementLevel.SOFT_SKILL:
            return (f"If you have shown {skill.lower()} (team projects, club roles, presentations), "
                    f"mention it in a bullet point with a concrete example.")
        if status == SkillGapStatus.PARTIAL:
            return (f"You already know {m.matched_value}. Use {skill} directly in a small project or assignment, "
                    f"then add it to your resume.")
        start = f" You already know {', '.join(related)}, which is a good starting point." if related else ""
        if level == SkillRequirementLevel.REQUIRED:
            return (f"Learn {skill} and use it in a project or coursework assignment; add it to your Skills section "
                    f"only once you have actually used it.{start}")
        return f"Optional: picking up {skill} would strengthen your application.{start}"

    # ---------------------------------------------------- either-or groups

    @staticmethod
    def _alternative_groups(items: list[SkillGapItem]) -> dict[str, AlternativeGroup]:
        by_line: dict[tuple[str, str], list[SkillGapItem]] = {}
        for i in items:
            if i.jd_evidence and i.level != SkillRequirementLevel.SOFT_SKILL and ALTERNATIVE_MARKERS.search(i.jd_evidence):
                by_line.setdefault((i.level.value, i.jd_evidence.strip()), []).append(i)
        groups: dict[str, AlternativeGroup] = {}
        for n, ((level, line), members) in enumerate(sorted(by_line.items())):
            if len(members) < 2:
                continue
            satisfied_by = [m.skill for m in members if m.status == SkillGapStatus.MATCHED]
            gid = f"ALT_{level.upper()}_{n + 1}"
            groups[gid] = AlternativeGroup(
                group_id=gid,
                level=SkillRequirementLevel(level),
                skills=[m.skill for m in members],
                jd_evidence=line,
                satisfied=bool(satisfied_by),
                satisfied_by=satisfied_by,
            )
        return groups

    @staticmethod
    def _apply_group(item: SkillGapItem, groups: dict[str, AlternativeGroup]) -> SkillGapItem:
        for g in groups.values():
            if item.skill in g.skills and item.level == g.level:
                update = {"alternative_group_id": g.group_id}
                if g.satisfied and item.status != SkillGapStatus.MATCHED:
                    others = ", ".join(g.satisfied_by)
                    update.update({
                        "status": SkillGapStatus.SATISFIED_BY_ALTERNATIVE,
                        "explanation": (f"The job accepts any of {', '.join(g.skills)} "
                                        f"(\"{g.jd_evidence.lstrip('-•* ')}\"); you have {others}, so {item.skill} is not required."),
                        "how_to_improve": None,
                        "importance": GapImportance.NICE_TO_HAVE,
                        "importance_score": min(item.importance_score, 0.2),
                    })
                return item.model_copy(update=update)
        return item

    # ---------------------------------------------------------- reporting

    @staticmethod
    def _priority_gaps(items: list[SkillGapItem], groups: dict[str, AlternativeGroup]) -> list[SkillGapItem]:
        """Missing/partial skills, most important first; an unmet either-or group appears once."""
        gaps = sorted(
            [i for i in items if i.status in {SkillGapStatus.MISSING, SkillGapStatus.PARTIAL}],
            key=lambda i: (-i.importance_score, i.status != SkillGapStatus.PARTIAL, i.level.value, i.skill),
        )
        out: list[SkillGapItem] = []
        seen: set[str] = set()
        for item in gaps:
            gid = item.alternative_group_id
            if gid is None:
                out.append(item)
                continue
            if gid in seen:
                continue
            seen.add(gid)
            options = groups[gid].skills
            out.append(item.model_copy(update={
                "explanation": f"The job asks for one of: {', '.join(options)}. " + item.explanation,
                "how_to_improve": (item.how_to_improve or "")
                + f" Any one of {', '.join(options)} satisfies this requirement.",
            }))
        return out

    @staticmethod
    def _file(report: SkillGapReport, item: SkillGapItem) -> None:
        if item.level == SkillRequirementLevel.SOFT_SKILL:
            report.soft_skills.append(item)
            return
        if item.status == SkillGapStatus.UNCERTAIN:
            report.uncertain.append(item)
            return
        prefix = "required" if item.level == SkillRequirementLevel.REQUIRED else "preferred"
        bucket = {
            SkillGapStatus.MATCHED: "matched",
            SkillGapStatus.SATISFIED_BY_ALTERNATIVE: "matched",
            SkillGapStatus.PARTIAL: "partial",
            SkillGapStatus.MISSING: "missing",
        }[item.status]
        getattr(report, f"{bucket}_{prefix}").append(item)

    @staticmethod
    def _coverage(items: list[SkillGapItem], groups: dict[str, AlternativeGroup]) -> SkillCoverage:
        """Alternative-aware coverage: an either-or group counts as one requirement."""
        cov = SkillCoverage()

        def units(level: SkillRequirementLevel) -> list[float]:
            values: list[float] = []
            seen_groups: set[str] = set()
            for i in items:
                if i.level != level or i.status == SkillGapStatus.UNCERTAIN:
                    continue
                if i.alternative_group_id:
                    if i.alternative_group_id in seen_groups:
                        continue
                    seen_groups.add(i.alternative_group_id)
                    members = [x for x in items if x.alternative_group_id == i.alternative_group_id]
                    if any(x.status == SkillGapStatus.MATCHED for x in members):
                        values.append(1.0)
                    elif any(x.status == SkillGapStatus.PARTIAL for x in members):
                        values.append(0.5)
                    else:
                        values.append(0.0)
                else:
                    values.append(1.0 if i.status == SkillGapStatus.MATCHED else 0.5 if i.status == SkillGapStatus.PARTIAL else 0.0)
            return values

        req, pref = units(SkillRequirementLevel.REQUIRED), units(SkillRequirementLevel.PREFERRED)
        soft = [i for i in items if i.level == SkillRequirementLevel.SOFT_SKILL]
        cov.required_total, cov.required_satisfied = len(req), sum(1 for v in req if v == 1.0)
        cov.required_partial = sum(1 for v in req if v == 0.5)
        cov.required_coverage = round(sum(req) / len(req), 3) if req else 1.0
        cov.preferred_total, cov.preferred_satisfied = len(pref), sum(1 for v in pref if v == 1.0)
        cov.preferred_partial = sum(1 for v in pref if v == 0.5)
        cov.preferred_coverage = round(sum(pref) / len(pref), 3) if pref else 1.0
        cov.soft_total = len(soft)
        cov.soft_satisfied = sum(1 for i in soft if i.status == SkillGapStatus.MATCHED)
        return cov

    @staticmethod
    def _experience_gap(candidate: CandidateProfile, job: ParsedJobDescription) -> str | None:
        exp = job.experience
        if exp.is_fresher_eligible or not exp.min_years:
            return None
        months = sum(e.duration_months or 0 for e in candidate.experience)
        years = months / 12
        if years >= exp.min_years:
            return None
        have = f"about {years:.1f} years" if months else "no full-time experience listed"
        return (f"The job asks for at least {exp.min_years:g} years of experience; your resume shows {have}. "
                f"Internships and projects may still be considered - check with the recruiter.")

    # ---------------------------------------------------------- eligibility

    def _eligibility(self, candidate: CandidateProfile, job: ParsedJobDescription) -> list[EligibilityCheck]:
        checks: list[EligibilityCheck] = []
        rules, edu_req = job.eligibility, job.education
        degree = main_degree(candidate)

        if rules.min_cgpa is not None:
            scale = rules.cgpa_scale or 10.0
            req = f"CGPA of at least {rules.min_cgpa:g}/{scale:g}"
            if degree is None or degree.cgpa is None:
                checks.append(EligibilityCheck(criterion="cgpa", requirement=req, status=EligibilityStatus.UNKNOWN,
                                               explanation="Your resume does not show a CGPA, so this cannot be checked."))
            else:
                value = degree.cgpa / (degree.cgpa_scale or 10.0) * scale
                ok = value + 1e-9 >= rules.min_cgpa
                checks.append(EligibilityCheck(
                    criterion="cgpa", requirement=req, candidate_value=f"{degree.cgpa:g}/{(degree.cgpa_scale or 10):g}",
                    status=EligibilityStatus.MET if ok else EligibilityStatus.NOT_MET,
                    explanation=("Your CGPA meets the cut-off." if ok else
                                 f"Your CGPA ({value:.2f}/{scale:g}) is below the cut-off of {rules.min_cgpa:g}."),
                ))

        if rules.min_percentage is not None:
            req = f"At least {rules.min_percentage:g}%"
            pct = degree.percentage if degree else None
            if pct is None:
                checks.append(EligibilityCheck(criterion="percentage", requirement=req, status=EligibilityStatus.UNKNOWN,
                                               explanation="No percentage found for your main degree."))
            else:
                ok = pct >= rules.min_percentage
                checks.append(EligibilityCheck(criterion="percentage", requirement=req, candidate_value=f"{pct:g}%",
                                               status=EligibilityStatus.MET if ok else EligibilityStatus.NOT_MET,
                                               explanation="Meets the percentage cut-off." if ok else "Below the percentage cut-off."))

        batches = sorted(set(rules.allowed_batches))
        if not batches and (edu_req.min_graduation_year or edu_req.max_graduation_year):
            lo = edu_req.min_graduation_year or edu_req.max_graduation_year
            hi = edu_req.max_graduation_year or edu_req.min_graduation_year
            batches = list(range(lo, hi + 1))
        if batches:
            req = "Graduating batch " + " / ".join(str(b) for b in batches)
            year = degree.graduation_year if degree else None
            if year is None:
                checks.append(EligibilityCheck(criterion="graduation_batch", requirement=req, status=EligibilityStatus.UNKNOWN,
                                               explanation="Your graduation year was not found on the resume."))
            else:
                ok = year in batches
                checks.append(EligibilityCheck(
                    criterion="graduation_batch", requirement=req, candidate_value=str(year),
                    status=EligibilityStatus.MET if ok else EligibilityStatus.NOT_MET,
                    explanation="Your batch is eligible." if ok else f"This opening is for the {req.split(' ', 2)[2]} batch; you graduate in {year}.",
                ))

        # Only trust values that are recognisable branch names; the JD parser sometimes puts
        # skill words (e.g. "Statistics" from a skills list) into fields_of_study.
        branches = [b for b in (rules.allowed_branches or edu_req.fields_of_study) if branch_key(b) in KNOWN_BRANCH_KEYS]
        any_branch = re.search(r"\bany (?:branch|discipline|stream)\b", " ".join(rules.raw_criteria + [edu_req.raw_text or ""]), re.IGNORECASE)
        if branches and not any_branch:
            req = "Branch: " + ", ".join(branches)
            field = degree.field_of_study if degree else None
            if not field:
                checks.append(EligibilityCheck(criterion="branch", requirement=req, status=EligibilityStatus.UNKNOWN,
                                               explanation="Your branch was not found on the resume."))
            else:
                allowed = {branch_key(b) for b in branches}
                mine = branch_key(field)
                ok = mine in allowed or ("circuit" in allowed and mine in CIRCUIT_BRANCHES)
                checks.append(EligibilityCheck(
                    criterion="branch", requirement=req, candidate_value=field,
                    status=EligibilityStatus.MET if ok else EligibilityStatus.NOT_MET,
                    explanation="Your branch is eligible." if ok else f"Your branch ({field}) is not in the eligible list.",
                ))

        if edu_req.degrees or edu_req.degree_levels:
            req = "Degree: " + ", ".join(edu_req.degrees or edu_req.degree_levels)
            if degree is None:
                checks.append(EligibilityCheck(criterion="degree", requirement=req, status=EligibilityStatus.UNKNOWN,
                                               explanation="Your degree was not found on the resume."))
            else:
                names = {d.lower().replace(".", "").replace(" ", "") for d in edu_req.degrees}
                mine = (degree.degree or "").lower().replace(".", "").replace(" ", "")
                ok = (not names or mine in names) and (
                    not edu_req.degree_levels or degree.degree_level in edu_req.degree_levels
                    or DEGREE_RANK.get(degree.degree_level or "", 0) >= max(DEGREE_RANK.get(lv, 0) for lv in edu_req.degree_levels)
                )
                checks.append(EligibilityCheck(
                    criterion="degree", requirement=req, candidate_value=degree.degree,
                    status=EligibilityStatus.MET if ok else EligibilityStatus.NOT_MET,
                    explanation="Your degree is eligible." if ok else f"Your degree ({degree.degree}) is not listed as eligible.",
                ))

        if rules.backlog_policy:
            checks.append(EligibilityCheck(
                criterion="backlogs", requirement=rules.backlog_policy, status=EligibilityStatus.UNKNOWN,
                explanation="Resumes do not usually list backlogs; confirm this with your placement cell.",
            ))
        return checks

    @staticmethod
    def _overall_eligibility(checks: Iterable[EligibilityCheck]) -> EligibilityStatus:
        checks = [c for c in checks if c.criterion != "backlogs"]
        if any(c.status == EligibilityStatus.NOT_MET for c in checks):
            return EligibilityStatus.NOT_MET
        if not checks or any(c.status == EligibilityStatus.UNKNOWN for c in checks):
            return EligibilityStatus.UNKNOWN
        return EligibilityStatus.MET

    @staticmethod
    def _summary(r: SkillGapReport) -> str:
        c = r.coverage
        role = r.job_title or "this job"
        parts = []
        if c.required_total:
            parts.append(f"You meet {c.required_satisfied} of {c.required_total} required skill requirements"
                         + (f" ({c.required_partial} partly)" if c.required_partial else "") + f" for {role}.")
        else:
            parts.append(f"The job description for {role} does not list required technical skills.")
        if c.preferred_total:
            parts.append(f"Preferred skills: {c.preferred_satisfied} of {c.preferred_total}.")
        critical = [g.skill for g in r.priority_gaps if g.importance == GapImportance.CRITICAL]
        if critical:
            parts.append("Most important to work on: " + ", ".join(critical[:3]) + ".")
        elif not r.priority_gaps:
            parts.append("No skill gaps were found.")
        if r.eligibility_status == EligibilityStatus.NOT_MET:
            failed = [x.criterion.replace("_", " ") for x in r.eligibility_checks if x.status == EligibilityStatus.NOT_MET]
            parts.append("You may not meet the eligibility rules (" + ", ".join(failed) + ").")
        elif r.eligibility_status == EligibilityStatus.UNKNOWN and r.eligibility_checks:
            parts.append("Some eligibility rules could not be checked from your resume.")
        return " ".join(parts)


def analyze_skill_gap(candidate: CandidateProfile, job: ParsedJobDescription, match_result: JobMatchResult) -> SkillGapReport:
    return SkillGapAnalyzer().analyze(candidate, job, match_result)


__all__ = ["BRANCH_ALIASES", "SkillGapAnalyzer", "analyze_skill_gap", "branch_key", "main_degree"]
