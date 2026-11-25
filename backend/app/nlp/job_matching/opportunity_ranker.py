"""
Job / Internship Relevance Ranking Engine.

Sprint 4 Module E (US-12: find relevant job or internship opportunities).

For each opening:
  1. Build a ParsedJobDescription - parse the description text with Module A and add the
     structured skill lists / CGPA cut-off the backend stores (normalized with Module B).
  2. Score it with the Module C matcher.
  3. Analyze gaps and eligibility with Module D.
  4. Relevance = 0.6 x Module C match score + 0.4 x alternative-aware required-skill coverage
     (preferred coverage when the JD lists no required skills). The coverage term corrects
     Module C for "X or Y" requirements. If the JD has no readable skills at all, relevance is
     capped below Moderate Fit (Module C scores empty dimensions as full marks). A JD asking
     for more years of experience than the resume shows costs 15 points.

Ordering (deterministic): eligible / unknown eligibility before not eligible, then relevance,
required coverage, preferred coverage, title, id.

Fit tiers (same names as the backend's OpportunityMatchCard): High Fit >= 70,
Moderate Fit >= 50, else Developing Fit. An opening is "suitable" when it is at least a
Moderate Fit, the candidate is not known to be ineligible, its skills could be read, and it
does not ask for more full-time experience than the resume shows. When nothing is suitable, the
report says so clearly and names the closest opening and what is missing (US-12 AC 3).

One opening failing to parse never stops the ranking: it is listed in `errors`.
"""

from __future__ import annotations

import time
from collections import defaultdict
from collections.abc import Iterable
from typing import Any

from app.nlp.job_matching.job_description_parser import JobDescriptionParser
from app.nlp.job_matching.ranking_schemas import (
    RANKER_VERSION,
    CommonGap,
    FilteredOpportunity,
    FitTier,
    JobOpportunity,
    OpportunityRankingReport,
    RankedOpportunity,
    RankingPreferences,
)
from app.nlp.job_matching.resume_job_matcher import ResumeJobMatcher
from app.nlp.job_matching.schemas import (
    EligibilityCriteria,
    JobSkillRequirement,
    JobType,
    LocationRequirement,
    ParsedJobDescription,
)
from app.nlp.job_matching.skill_engine import SkillNormalizer, get_skill_normalizer
from app.nlp.job_matching.skill_gap_analyzer import SkillGapAnalyzer
from app.nlp.job_matching.skill_gap_schemas import (
    EligibilityStatus,
    GapImportance,
    SkillGapReport,
    SkillGapStatus,
)
from app.nlp.schemas import CandidateProfile

MATCH_WEIGHT = 0.6
COVERAGE_WEIGHT = 0.4
HIGH_FIT = 70.0
MODERATE_FIT = 50.0
MIN_DESCRIPTION_CHARS = 40
EXPERIENCE_GAP_PENALTY = 15.0
ELIGIBILITY_ORDER = {EligibilityStatus.MET: 0, EligibilityStatus.UNKNOWN: 0, EligibilityStatus.NOT_MET: 1}

JOB_TYPE_WORDS = {
    "intern": JobType.INTERNSHIP,
    "full": JobType.FULL_TIME,
    "part": JobType.PART_TIME,
    "contract": JobType.CONTRACT,
}


def fit_tier(score: float) -> FitTier:
    if score >= HIGH_FIT:
        return FitTier.HIGH
    if score >= MODERATE_FIT:
        return FitTier.MODERATE
    return FitTier.DEVELOPING


def job_type_from_text(value: str | None) -> JobType:
    text = (value or "").lower()
    for word, jt in JOB_TYPE_WORDS.items():
        if word in text:
            return jt
    return JobType.UNKNOWN


class OpportunityRanker:
    """Ranks openings for one candidate with explanations."""

    def __init__(
        self,
        parser: JobDescriptionParser | None = None,
        matcher: ResumeJobMatcher | None = None,
        gap_analyzer: SkillGapAnalyzer | None = None,
        normalizer: SkillNormalizer | None = None,
    ) -> None:
        self.parser = parser or JobDescriptionParser()
        self.matcher = matcher or ResumeJobMatcher()
        self.gap_analyzer = gap_analyzer or SkillGapAnalyzer()
        self.normalizer = normalizer or get_skill_normalizer()
        self.version = RANKER_VERSION

    # ------------------------------------------------------------------ API

    def to_parsed_job(self, opp: JobOpportunity | ParsedJobDescription) -> ParsedJobDescription:
        """Turn an opportunity record into the structured JD Modules C and D need."""
        if isinstance(opp, ParsedJobDescription):
            return opp
        text = (opp.description or "").strip()
        if len(text) >= MIN_DESCRIPTION_CHARS:
            job = self.parser.parse(text, job_id=opp.opportunity_id)
        else:
            job = ParsedJobDescription(job_id=opp.opportunity_id)

        update: dict[str, Any] = {}
        if opp.title:
            update["title"] = opp.title
        if opp.company:
            update["company_name"] = opp.company
        if opp.opportunity_type and job_type_from_text(opp.opportunity_type) != JobType.UNKNOWN:
            update["job_type"] = job_type_from_text(opp.opportunity_type)
        if opp.location and not job.location.raw_location:
            update["location"] = LocationRequirement(
                raw_location=opp.location, city=opp.location.split(",")[0].strip(),
                is_remote="remote" in opp.location.lower(),
            )
        if opp.min_cgpa is not None:
            update["eligibility"] = job.eligibility.model_copy(update={"min_cgpa": opp.min_cgpa, "cgpa_scale": 10.0}) \
                if job.eligibility else EligibilityCriteria(min_cgpa=opp.min_cgpa, cgpa_scale=10.0)

        required = list(job.required_technical_skills)
        preferred = list(job.preferred_technical_skills)
        self._merge_listed(required, opp.required_skills, is_required=True, other=preferred)
        self._merge_listed(preferred, opp.preferred_skills, is_required=False, other=required)
        update["required_technical_skills"] = required
        update["preferred_technical_skills"] = preferred
        return job.model_copy(update=update)

    def rank(
        self,
        candidate: CandidateProfile,
        opportunities: Iterable[JobOpportunity | ParsedJobDescription | dict[str, Any]],
        preferences: RankingPreferences | None = None,
        include_details: bool = False,
    ) -> OpportunityRankingReport:
        started = time.perf_counter()
        prefs = preferences or RankingPreferences()
        evaluated: list[tuple[RankedOpportunity, SkillGapReport]] = []
        filtered: list[FilteredOpportunity] = []
        errors: list[dict[str, str]] = []
        total = 0

        for raw in opportunities:
            total += 1
            try:
                opp = JobOpportunity.from_record(raw) if isinstance(raw, dict) else raw
                job = self.to_parsed_job(opp)
                oid = opp.opportunity_id if isinstance(opp, JobOpportunity) else (job.job_id or job.title or f"job-{total}")
                reason = self._filter_reason(opp, job, prefs)
                if reason:
                    filtered.append(FilteredOpportunity(opportunity_id=oid, title=job.title, reason=reason))
                    continue
                match = self.matcher.match(candidate, job)
                gap = self.gap_analyzer.analyze(candidate, job, match)
                item = self._ranked_item(oid, opp, job, match, gap, include_details)
                if item.relevance_score < prefs.min_relevance:
                    filtered.append(FilteredOpportunity(
                        opportunity_id=oid, title=job.title,
                        reason=f"Relevance {item.relevance_score:.1f} is below your minimum of {prefs.min_relevance:g}."))
                    continue
                if item.eligibility_status == EligibilityStatus.NOT_MET and not prefs.include_ineligible:
                    filtered.append(FilteredOpportunity(opportunity_id=oid, title=job.title,
                                                        reason="Not eligible: " + "; ".join(item.eligibility_issues)))
                    continue
                evaluated.append((item, gap))
            except Exception as exc:  # noqa: BLE001 - one bad record must not stop the ranking
                oid = str(raw.get("id") or raw.get("opportunity_id")) if isinstance(raw, dict) else getattr(raw, "opportunity_id", None) or getattr(raw, "job_id", None) or f"job-{total}"
                errors.append({"opportunity_id": str(oid), "error": f"{type(exc).__name__}: {exc}"})

        evaluated.sort(key=lambda pair: self._sort_key(pair[0]))
        if prefs.top_k:
            evaluated = evaluated[: prefs.top_k]

        ranked: list[RankedOpportunity] = []
        for i, (item, _gap) in enumerate(evaluated):
            reasons = list(item.ranking_reasons)
            if i > 0:
                reasons.append(self._compare(item, ranked[i - 1]))
            ranked.append(item.model_copy(update={"rank": i + 1, "ranking_reasons": reasons}))

        suitable = [r for r in ranked if r.is_suitable]
        report = OpportunityRankingReport(
            total_evaluated=total,
            suitable_count=len(suitable),
            has_suitable_matches=bool(suitable),
            guidance_message=self._guidance(ranked, suitable, total, filtered, errors),
            ranked_opportunities=ranked,
            filtered_out=filtered,
            common_gaps=self._common_gaps(evaluated),
            errors=errors,
            ranker_version=self.version,
        )
        report.processing_time_ms = round((time.perf_counter() - started) * 1000, 2)
        return report

    # ------------------------------------------------------------ helpers

    def _merge_listed(self, target: list[JobSkillRequirement], names: list[str], is_required: bool,
                      other: list[JobSkillRequirement]) -> None:
        existing = {s.canonical_name.lower() for s in target}
        for raw in names:
            if not raw or not raw.strip():
                continue
            norm = self.normalizer.normalize_skill(raw.strip())
            canonical = norm.canonical_name or raw.strip()
            key = canonical.lower()
            if key in existing:
                continue
            if is_required:
                # Explicitly listed as required wins over the parser's "preferred" guess
                other[:] = [s for s in other if s.canonical_name.lower() != key]
            elif any(s.canonical_name.lower() == key for s in other):
                continue
            existing.add(key)
            target.append(JobSkillRequirement(
                canonical_name=canonical,
                matched_alias=raw.strip(),
                category=norm.category or "Unrecognized",
                is_required=is_required,
                # Explicitly listed by the employer, so it is certainly required even when the
                # taxonomy does not know it (e.g. "Excel"); matching then falls back to the name.
                confidence=max(norm.confidence, 0.9) if norm.is_recognized else 0.9,
                evidence=f"Listed under {'required' if is_required else 'preferred'} skills: {raw.strip()}",
            ))

    @staticmethod
    def _filter_reason(opp, job: ParsedJobDescription, prefs: RankingPreferences) -> str | None:
        if prefs.job_types:
            wanted = {job_type_from_text(t) for t in prefs.job_types} - {JobType.UNKNOWN}
            if wanted and job.job_type != JobType.UNKNOWN and job.job_type not in wanted:
                return f"Job type is {job.job_type.value.replace('_', '-')}, not one you asked for."
        if prefs.locations:
            loc = " ".join(filter(None, [job.location.raw_location, job.location.city,
                                         getattr(opp, "location", None)])).lower()
            remote = job.location.is_remote or "remote" in loc
            if loc and not remote and not any(p.lower() in loc for p in prefs.locations):
                return f"Location ({job.location.raw_location or job.location.city or loc}) is not in your preferred locations."
        return None

    def _ranked_item(self, oid, opp, job, match, gap: SkillGapReport, include_details: bool) -> RankedOpportunity:
        cov = gap.coverage
        notes: list[str] = []
        # Coverage term: required skills, else preferred skills, else no skill evidence at all.
        if cov.required_total:
            coverage_term = cov.required_coverage
        elif cov.preferred_total:
            coverage_term = cov.preferred_coverage
        else:
            coverage_term = None
        if coverage_term is None:
            # Module C gives full marks to empty skill dimensions; without readable skills the
            # match cannot be trusted, so cap it below Moderate Fit and say why.
            relevance = min(match.overall_score * MATCH_WEIGHT, MODERATE_FIT - 0.01)
            notes.append("No technical skills could be read from this job description, so its relevance is uncertain.")
        else:
            relevance = MATCH_WEIGHT * match.overall_score + COVERAGE_WEIGHT * 100.0 * coverage_term
        if gap.experience_gap:
            relevance -= EXPERIENCE_GAP_PENALTY
        relevance = round(max(0.0, min(100.0, relevance)), 2)
        tier = fit_tier(relevance)
        issues = [c.explanation for c in gap.eligibility_checks if c.status == EligibilityStatus.NOT_MET]
        suitable = (tier != FitTier.DEVELOPING and gap.eligibility_status != EligibilityStatus.NOT_MET
                    and coverage_term is not None and not gap.experience_gap)

        names = lambda items: [i.skill for i in items]  # noqa: E731
        req_ok = [i.skill for i in gap.matched_required if i.status == SkillGapStatus.MATCHED]
        top_gaps = [g.skill for g in gap.priority_gaps if g.importance != GapImportance.NICE_TO_HAVE][:3]

        reasons: list[str] = []
        if cov.required_total:
            reasons.append(f"Meets {cov.required_satisfied}/{cov.required_total} required skill requirements"
                           + (f" (e.g. {', '.join(req_ok[:3])})" if req_ok else "") + ".")
        if gap.missing_required:
            reasons.append("Missing required: " + ", ".join(names(gap.missing_required)[:4]) + ".")
        if cov.preferred_total:
            reasons.append(f"Has {cov.preferred_satisfied}/{cov.preferred_total} preferred skills.")
        if issues:
            reasons.append("Eligibility: " + " ".join(issues))
        elif gap.eligibility_status == EligibilityStatus.UNKNOWN and gap.eligibility_checks:
            reasons.append("Some eligibility rules could not be checked from the resume.")
        if gap.experience_gap:
            reasons.append(gap.experience_gap + f" (-{EXPERIENCE_GAP_PENALTY:g} relevance)")
        reasons.extend(notes)

        summary = (f"{tier.value} ({relevance:.0f}/100) for {job.title or 'this opening'}"
                   + (f" at {job.company_name}" if job.company_name else "") + ". " + gap.summary)

        return RankedOpportunity(
            rank=1,
            opportunity_id=str(oid),
            title=job.title,
            company=job.company_name,
            location=(getattr(opp, "location", None) if isinstance(opp, JobOpportunity) else None)
            or job.location.raw_location or job.location.city,
            opportunity_type=(getattr(opp, "opportunity_type", None) if isinstance(opp, JobOpportunity) else None)
            or (job.job_type.value if job.job_type != JobType.UNKNOWN else None),
            relevance_score=relevance,
            fit_tier=tier,
            match_score=match.overall_score,
            required_coverage=cov.required_coverage if cov.required_total else 0.0,
            preferred_coverage=cov.preferred_coverage if cov.preferred_total else 0.0,
            eligibility_status=gap.eligibility_status,
            eligibility_issues=issues,
            is_suitable=suitable,
            matched_required=names(gap.matched_required),
            partial_required=names(gap.partial_required),
            missing_required=names(gap.missing_required),
            matched_preferred=names(gap.matched_preferred),
            partial_preferred=names(gap.partial_preferred),
            missing_preferred=names(gap.missing_preferred),
            top_gaps=top_gaps,
            ranking_reasons=reasons,
            summary=summary,
            match_result=match if include_details else None,
            skill_gap=gap if include_details else None,
        )

    @staticmethod
    def _sort_key(r: RankedOpportunity):
        return (ELIGIBILITY_ORDER[r.eligibility_status], -r.relevance_score, -r.required_coverage,
                -r.preferred_coverage, (r.title or "").lower(), r.opportunity_id)

    @staticmethod
    def _compare(item: RankedOpportunity, above: RankedOpportunity) -> str:
        label = above.title or above.opportunity_id
        if ELIGIBILITY_ORDER[item.eligibility_status] > ELIGIBILITY_ORDER[above.eligibility_status]:
            return f"Ranked below {label} because you may not meet this opening's eligibility rules."
        if abs(item.relevance_score - above.relevance_score) < 0.01:
            if item.required_coverage < above.required_coverage:
                return f"Same relevance as {label}, but you meet fewer of this opening's required skills."
            return f"Same relevance as {label}; listed after it only to keep the order stable."
        if item.required_coverage < above.required_coverage:
            return (f"Ranked below {label} because you meet fewer of its required skills "
                    f"({item.required_coverage:.0%} vs {above.required_coverage:.0%}).")
        return (f"Ranked below {label} because its overall match is lower "
                f"({item.match_score:.0f} vs {above.match_score:.0f}).")

    @staticmethod
    def _common_gaps(evaluated: list[tuple[RankedOpportunity, SkillGapReport]]) -> list[CommonGap]:
        """Required skills missing in 2+ openings that are not hopeless matches."""
        counts: dict[str, list[str]] = defaultdict(list)
        for item, gap in evaluated:
            if item.eligibility_status == EligibilityStatus.NOT_MET:
                continue
            for g in gap.priority_gaps:
                if g.level.value == "required" and g.status == SkillGapStatus.MISSING and not g.from_responsibilities_only:
                    counts[g.skill].append(item.title or item.opportunity_id)
        common = [CommonGap(skill=s, missing_in=len(t), opportunity_titles=t) for s, t in counts.items() if len(t) >= 2]
        return sorted(common, key=lambda c: (-c.missing_in, c.skill))[:10]

    @staticmethod
    def _guidance(ranked, suitable, total, filtered, errors) -> str:
        if total == 0:
            return "No opportunities are available to compare right now."
        if not ranked:
            why = " All openings were filtered out by your preferences." if filtered else ""
            why += " Some openings could not be read." if errors else ""
            return "No opportunities matched your profile." + why
        if suitable:
            best = suitable[0]
            return (f"{len(suitable)} of {total} opportunities are a good match for your profile. "
                    f"Best match: {best.title or best.opportunity_id} ({best.relevance_score:.0f}/100).")
        closest = ranked[0]
        gaps = ", ".join(closest.top_gaps or closest.missing_required[:3]) or "eligibility"
        return (f"No opportunity is a strong match for your current profile. The closest is "
                f"{closest.title or closest.opportunity_id} ({closest.relevance_score:.0f}/100); "
                f"working on {gaps} would improve your fit.")


def rank_opportunities(
    candidate: CandidateProfile,
    opportunities: Iterable[JobOpportunity | ParsedJobDescription | dict[str, Any]],
    preferences: RankingPreferences | None = None,
    include_details: bool = False,
) -> OpportunityRankingReport:
    return OpportunityRanker().rank(candidate, opportunities, preferences, include_details)


__all__ = ["OpportunityRanker", "fit_tier", "job_type_from_text", "rank_opportunities"]
