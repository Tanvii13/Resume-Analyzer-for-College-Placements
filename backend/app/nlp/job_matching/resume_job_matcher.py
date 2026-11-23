"""
Resume-Job Description Matching Engine.

Sprint 4 Module C (NLP-JobMatching).

Deterministic, explainable matching engine that evaluates:
- Technical Skills (required, preferred, equivalent, related)
- Soft Skills (explicit & inferred from experiences/projects)
- Experience (job, internship, fresher eligibility, project substitution)
- Education & Eligibility (degree level, field of study, CGPA cutoffs)
- Relevant Projects (technology alignment, practical execution)
"""

import re
from typing import Any

from app.nlp.job_matching.matcher_schemas import (
    MATCHER_ENGINE_VERSION,
    ComponentScore,
    EvidenceSource,
    JobMatchResult,
    MatchCategory,
    MatchingWeights,
    RequirementMatch,
    RequirementType,
)
from app.nlp.job_matching.schemas import (
    EducationRequirement,
    ExperienceRequirement,
    JobSkillRequirement,
    ParsedJobDescription,
)
from app.nlp.job_matching.skill_engine import (
    SkillEquivalenceEngine,
    SkillNormalizer,
    get_equivalence_engine,
    get_skill_normalizer,
)
from app.nlp.versioning import build_version_metadata
from app.nlp.job_matching.skill_normalization_schemas import (
    SkillRelationshipType,
)
from app.nlp.schemas import (
    CandidateProfile,
    ConfidenceLevel,
    ProjectEntry,
)


def calculate_text_similarity(text_a: str, text_b: str) -> float:
    """
    Deterministic word token overlap / Jaccard similarity.
    Runs 100% locally with zero external APIs or dependencies.
    """
    if not text_a or not text_b:
        return 0.0
    tokens_a = set(re.findall(r"\b\w{3,}\b", text_a.lower()))
    tokens_b = set(re.findall(r"\b\w{3,}\b", text_b.lower()))
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = tokens_a.intersection(tokens_b)
    if not intersection:
        return 0.0
    return round(len(intersection) / len(tokens_a.union(tokens_b)), 3)


class ResumeJobMatcher:
    """
    Deterministic, explainable engine comparing CandidateProfile against ParsedJobDescription.
    """

    def __init__(
        self,
        weights: MatchingWeights | None = None,
        equivalence_engine: SkillEquivalenceEngine | None = None,
        normalizer: SkillNormalizer | None = None,
    ) -> None:
        self.weights = weights or MatchingWeights()
        self.normalizer = normalizer or get_skill_normalizer()
        self.equivalence_engine = equivalence_engine or get_equivalence_engine()
        self.version = MATCHER_ENGINE_VERSION

    def match(
        self,
        candidate: CandidateProfile,
        job: ParsedJobDescription,
    ) -> JobMatchResult:
        """
        Evaluate candidate profile against a job description.

        Args:
            candidate: Existing Sprint 2 CandidateProfile.
            job: Structured ParsedJobDescription from Module A.

        Returns:
            JobMatchResult containing overall score, component breakdown,
            evidence for every match, and explainability narratives.
        """
        all_matches: list[RequirementMatch] = []
        scoring_explanations: list[str] = []

        # 1. Evaluate Technical Skills (Required and Preferred)
        req_tech_matches = self._match_technical_skills(
            candidate, job.required_technical_skills, is_required=True
        )
        pref_tech_matches = self._match_technical_skills(
            candidate, job.preferred_technical_skills, is_required=False
        )
        all_matches.extend(req_tech_matches)
        all_matches.extend(pref_tech_matches)

        # 2. Evaluate Soft Skills
        soft_matches = self._match_soft_skills(candidate, job.soft_skills)
        all_matches.extend(soft_matches)

        # 3. Evaluate Experience
        exp_matches = self._match_experience(candidate, job.experience)
        all_matches.extend(exp_matches)

        # 4. Evaluate Education and Placement Eligibility
        edu_matches = self._match_education(candidate, job.education, job.eligibility)
        all_matches.extend(edu_matches)

        # 5. Evaluate Relevant Projects
        proj_matches = self._match_projects(candidate, job)
        all_matches.extend(proj_matches)

        # Categorize matches
        matched_reqs: list[RequirementMatch] = [
            m for m in all_matches if m.category in {
                MatchCategory.EXACT_MATCH,
                MatchCategory.ALIAS_MATCH,
                MatchCategory.EQUIVALENT_MATCH,
            }
        ]
        partial_reqs: list[RequirementMatch] = [
            m for m in all_matches if m.category == MatchCategory.RELATED_MATCH
        ]
        missing_reqs: list[RequirementMatch] = [
            m for m in all_matches if m.category == MatchCategory.MISSING
        ]
        uncertain_reqs: list[RequirementMatch] = [
            m for m in all_matches if m.category == MatchCategory.UNCERTAIN
        ]

        # Calculate Component Scores and Overall Score
        overall_score, confidence, conf_level, comp_scores, explanations = self._aggregate_scores(
            candidate=candidate,
            job=job,
            req_tech_matches=req_tech_matches,
            pref_tech_matches=pref_tech_matches,
            soft_matches=soft_matches,
            exp_matches=exp_matches,
            edu_matches=edu_matches,
            proj_matches=proj_matches,
        )
        scoring_explanations.extend(explanations)

        # Candidate name from contact if available
        cand_name = getattr(candidate.contact, "full_name", None)

        return JobMatchResult(
            job_id=job.job_id,
            job_title=job.title,
            candidate_name=cand_name,
            overall_score=round(overall_score, 2),
            confidence=round(confidence, 2),
            confidence_level=conf_level,
            component_scores=comp_scores,
            matched_requirements=matched_reqs,
            partially_matched_requirements=partial_reqs,
            missing_requirements=missing_reqs,
            uncertain_requirements=uncertain_reqs,
            all_matches=all_matches,
            scoring_explanations=scoring_explanations,
            matching_engine_version=self.version,
            version_metadata=build_version_metadata(("profile_extraction", "job_parser", "skill_matching", "job_matching")),
        )

    # ------------------------------------------------------------------------
    # Dimension A: Technical Skills Matching
    # ------------------------------------------------------------------------

    def _match_technical_skills(
        self,
        candidate: CandidateProfile,
        requirements: list[JobSkillRequirement],
        is_required: bool,
    ) -> list[RequirementMatch]:
        """Match required or preferred technical skills against candidate profile."""
        matches: list[RequirementMatch] = []
        req_type = (
            RequirementType.REQUIRED_TECHNICAL_SKILL
            if is_required
            else RequirementType.PREFERRED_TECHNICAL_SKILL
        )

        for req in requirements:
            req_name = req.canonical_name or req.matched_alias

            # Low confidence extraction in JD
            if req.confidence < 0.60:
                matches.append(
                    RequirementMatch(
                        requirement_name=req_name,
                        requirement_type=req_type,
                        category=MatchCategory.UNCERTAIN,
                        matched_value=None,
                        score=0.0,
                        confidence=req.confidence,
                        is_satisfied=False,
                        evidence_source=EvidenceSource.NONE,
                        evidence=req.evidence,
                        rationale=f"Skill '{req_name}' extracted from job description with low confidence ({req.confidence:.2f})",
                    )
                )
                continue

            best_match: RequirementMatch | None = None

            # 1. Search candidate explicit technical skills
            for cand_skill in candidate.technical_skills:
                eval_res = self.equivalence_engine.evaluate_equivalence(cand_skill, req)
                if eval_res.relationship_type == SkillRelationshipType.EXACT_MATCH:
                    best_match = RequirementMatch(
                        requirement_name=req_name,
                        requirement_type=req_type,
                        category=MatchCategory.EXACT_MATCH,
                        matched_value=cand_skill.canonical_name,
                        score=1.0,
                        confidence=1.0,
                        is_satisfied=True,
                        evidence_source=EvidenceSource.EXPLICIT_SKILLS_SECTION,
                        evidence=f"CandidateProfile.technical_skills: '{cand_skill.canonical_name}' (section: '{cand_skill.source_section or 'skills'}')",
                        rationale=f"Exact canonical match for '{req_name}' in candidate skills section",
                    )
                    break
                elif eval_res.relationship_type == SkillRelationshipType.EXACT_ALIAS:
                    best_match = RequirementMatch(
                        requirement_name=req_name,
                        requirement_type=req_type,
                        category=MatchCategory.ALIAS_MATCH,
                        matched_value=cand_skill.canonical_name,
                        score=1.0,
                        confidence=1.0,
                        is_satisfied=True,
                        evidence_source=EvidenceSource.EXPLICIT_SKILLS_SECTION,
                        evidence=f"CandidateProfile.technical_skills: '{cand_skill.matched_alias}' resolves to '{cand_skill.canonical_name}'",
                        rationale=f"Alias match: candidate's '{cand_skill.matched_alias}' corresponds to required '{req_name}'",
                    )
                    break
                elif eval_res.relationship_type == SkillRelationshipType.EQUIVALENT:
                    if best_match is None or best_match.category in {MatchCategory.RELATED_MATCH, MatchCategory.MISSING}:
                        best_match = RequirementMatch(
                            requirement_name=req_name,
                            requirement_type=req_type,
                            category=MatchCategory.EQUIVALENT_MATCH,
                            matched_value=cand_skill.canonical_name,
                            score=eval_res.similarity_score,
                            confidence=eval_res.confidence,
                            is_satisfied=True,
                            evidence_source=EvidenceSource.EXPLICIT_SKILLS_SECTION,
                            evidence=f"CandidateProfile.technical_skills: '{cand_skill.canonical_name}' (equivalent to '{req_name}')",
                            rationale=eval_res.rationale,
                        )
                elif (
                    eval_res.relationship_type in {SkillRelationshipType.RELATED, SkillRelationshipType.PREREQUISITE}
                    and best_match is None
                ):
                    best_match = RequirementMatch(
                            requirement_name=req_name,
                            requirement_type=req_type,
                            category=MatchCategory.RELATED_MATCH,
                            matched_value=cand_skill.canonical_name,
                            score=eval_res.similarity_score,
                            confidence=eval_res.confidence,
                            is_satisfied=False,
                            evidence_source=EvidenceSource.EXPLICIT_SKILLS_SECTION,
                            evidence=f"CandidateProfile.technical_skills: '{cand_skill.canonical_name}'",
                            rationale=eval_res.rationale,
                        )

            # 2. If no exact/alias/equivalent in explicit skills, search candidate projects
            if best_match is None or not best_match.is_satisfied:
                for idx, proj in enumerate(candidate.projects):
                    # Check project technologies list
                    for tech in proj.technologies:
                        tech_eval = self.equivalence_engine.evaluate_equivalence(tech, req)
                        if tech_eval.is_equivalent:
                            best_match = RequirementMatch(
                                requirement_name=req_name,
                                requirement_type=req_type,
                                category=MatchCategory.EXACT_MATCH,
                                matched_value=tech,
                                score=0.95,
                                confidence=1.0,
                                is_satisfied=True,
                                evidence_source=EvidenceSource.PROJECT_TECHNOLOGIES,
                                evidence=f"CandidateProfile.projects[{idx}]: '{proj.title}' (technologies: {proj.technologies})",
                                rationale=f"Demonstrated practical implementation of '{req_name}' in project '{proj.title}'",
                            )
                            break
                    if best_match and best_match.is_satisfied:
                        break

            # 3. If still not satisfied, search candidate work experience & internships
            if best_match is None or not best_match.is_satisfied:
                all_exp = candidate.experience + candidate.internships
                for idx, exp in enumerate(all_exp):
                    for tech in exp.technologies_used:
                        tech_eval = self.equivalence_engine.evaluate_equivalence(tech, req)
                        if tech_eval.is_equivalent:
                            src = EvidenceSource.INTERNSHIP_TECHNOLOGIES if exp.is_internship else EvidenceSource.EXPERIENCE_TECHNOLOGIES
                            best_match = RequirementMatch(
                                requirement_name=req_name,
                                requirement_type=req_type,
                                category=MatchCategory.EXACT_MATCH,
                                matched_value=tech,
                                score=1.0,
                                confidence=1.0,
                                is_satisfied=True,
                                evidence_source=src,
                                evidence=f"CandidateProfile.{'internships' if exp.is_internship else 'experience'}[{idx}]: '{exp.company_name or 'Company'}' - '{exp.job_title or 'Role'}' (technologies: {exp.technologies_used})",
                                rationale=f"Professional hands-on experience applying '{req_name}' in industry role",
                            )
                            break
                    if best_match and best_match.is_satisfied:
                        break

            # 4. If still not satisfied, check project descriptions (inferred text evidence)
            if best_match is None or not best_match.is_satisfied:
                for idx, proj in enumerate(candidate.projects):
                    combined_text = f"{proj.title or ''} {proj.description or ''} {' '.join(proj.highlights)}"
                    if req_name.lower() in combined_text.lower() and re.search(
                        rf"\b{re.escape(req_name)}\b", combined_text, re.IGNORECASE
                    ):
                        best_match = RequirementMatch(
                            requirement_name=req_name,
                            requirement_type=req_type,
                            category=MatchCategory.EXACT_MATCH,
                            matched_value=req_name,
                            score=0.85,
                            confidence=0.90,
                            is_satisfied=True,
                            evidence_source=EvidenceSource.PROJECT_DESCRIPTION,
                            evidence=f"CandidateProfile.projects[{idx}]: '{proj.title}' description references '{req_name}'",
                            rationale=f"Inferred project evidence: '{req_name}' cited in description for project '{proj.title}'",
                        )
                        break

            # 5. Default to MISSING if no match of any kind found
            if best_match is None:
                best_match = RequirementMatch(
                    requirement_name=req_name,
                    requirement_type=req_type,
                    category=MatchCategory.MISSING,
                    matched_value=None,
                    score=0.0,
                    confidence=1.0,
                    is_satisfied=False,
                    evidence_source=EvidenceSource.NONE,
                    evidence=f"No evidence of skill '{req_name}' found in candidate profile",
                    rationale=f"Required skill '{req_name}' was not found in candidate skills, projects, or experience",
                )

            matches.append(best_match)

        return matches

    # ------------------------------------------------------------------------
    # Dimension B: Soft Skills Matching
    # ------------------------------------------------------------------------

    def _match_soft_skills(
        self,
        candidate: CandidateProfile,
        soft_skill_reqs: list[JobSkillRequirement],
    ) -> list[RequirementMatch]:
        """Match soft skill requirements against candidate profile."""
        matches: list[RequirementMatch] = []

        for req in soft_skill_reqs:
            req_name = req.canonical_name or req.matched_alias
            found_match: RequirementMatch | None = None

            # 1. Explicit soft skills
            for cand_ss in candidate.soft_skills:
                eval_res = self.equivalence_engine.evaluate_equivalence(cand_ss, req)
                if eval_res.is_equivalent:
                    found_match = RequirementMatch(
                        requirement_name=req_name,
                        requirement_type=RequirementType.SOFT_SKILL,
                        category=MatchCategory.EXACT_MATCH,
                        matched_value=cand_ss.canonical_name,
                        score=1.0,
                        confidence=1.0,
                        is_satisfied=True,
                        evidence_source=EvidenceSource.EXPLICIT_SKILLS_SECTION,
                        evidence=f"CandidateProfile.soft_skills: '{cand_ss.canonical_name}'",
                        rationale=f"Explicit soft skill '{req_name}' listed in candidate profile",
                    )
                    break

            # 2. Inferred evidence in project highlights or experience responsibilities
            if not found_match:
                # Check experience responsibilities
                for idx, exp in enumerate(candidate.experience + candidate.internships):
                    resp_text = " ".join(exp.responsibilities)
                    if re.search(rf"\b{re.escape(req_name)}\b", resp_text, re.IGNORECASE):
                        found_match = RequirementMatch(
                            requirement_name=req_name,
                            requirement_type=RequirementType.SOFT_SKILL,
                            category=MatchCategory.EXACT_MATCH,
                            matched_value=req_name,
                            score=0.85,
                            confidence=0.85,
                            is_satisfied=True,
                            evidence_source=EvidenceSource.EXPERIENCE_RESPONSIBILITIES,
                            evidence=f"CandidateProfile.experience[{idx}].responsibilities references '{req_name}'",
                            rationale=f"Demonstrated soft skill '{req_name}' in practical work responsibilities",
                        )
                        break

            # 3. Missing soft skill
            if not found_match:
                found_match = RequirementMatch(
                    requirement_name=req_name,
                    requirement_type=RequirementType.SOFT_SKILL,
                    category=MatchCategory.MISSING,
                    matched_value=None,
                    score=0.0,
                    confidence=1.0,
                    is_satisfied=False,
                    evidence_source=EvidenceSource.NONE,
                    evidence=f"No evidence of soft skill '{req_name}' found in candidate profile",
                    rationale=f"Soft skill '{req_name}' not evidenced in candidate profile",
                )

            matches.append(found_match)

        return matches

    # ------------------------------------------------------------------------
    # Dimension C: Experience Matching
    # ------------------------------------------------------------------------

    def _match_experience(
        self,
        candidate: CandidateProfile,
        exp_req: ExperienceRequirement,
    ) -> list[RequirementMatch]:
        """Match candidate work and internship experience against job requirements."""
        # Check if experience was specified in JD
        is_specified = (
            exp_req.min_years is not None
            or exp_req.is_fresher_eligible
            or bool(exp_req.raw_text)
        )

        if not is_specified:
            return []

        # Calculate candidate experience duration
        total_exp_months = sum(e.duration_months or 0 for e in candidate.experience)
        total_int_months = sum(e.duration_months or 0 for e in candidate.internships)
        total_years = (total_exp_months + total_int_months) / 12.0
        num_internships = len(candidate.internships)
        num_projects = len(candidate.projects)

        # Case 1: Fresher eligible role
        if exp_req.is_fresher_eligible or (exp_req.min_years is not None and exp_req.min_years == 0):
            if num_internships > 0 or num_projects > 0:
                return [
                    RequirementMatch(
                        requirement_name="Fresher Eligibility & Experience",
                        requirement_type=RequirementType.EXPERIENCE,
                        category=MatchCategory.EXACT_MATCH,
                        matched_value=f"{num_internships} internships, {num_projects} projects",
                        score=1.0,
                        confidence=1.0,
                        is_satisfied=True,
                        evidence_source=EvidenceSource.INTERNSHIP_TECHNOLOGIES if num_internships > 0 else EvidenceSource.PROJECT_TECHNOLOGIES,
                        evidence=f"Candidate has {num_internships} internships and {num_projects} technical projects",
                        rationale="Candidate meets fresher criteria with relevant practical project/internship portfolio",
                    )
                ]
            else:
                return [
                    RequirementMatch(
                        requirement_name="Fresher Eligibility",
                        requirement_type=RequirementType.EXPERIENCE,
                        category=MatchCategory.EXACT_MATCH,
                        matched_value="Fresher",
                        score=0.80,
                        confidence=0.90,
                        is_satisfied=True,
                        evidence_source=EvidenceSource.NONE,
                        evidence="Candidate profile has no recorded experience or projects",
                        rationale="Candidate meets fresher criteria, though practical evidence is limited",
                    )
                ]

        # Case 2: Minimum years required
        min_years = exp_req.min_years or 0.0

        if total_years >= min_years:
            return [
                RequirementMatch(
                    requirement_name=f"Minimum {min_years} Years Experience",
                    requirement_type=RequirementType.EXPERIENCE,
                    category=MatchCategory.EXACT_MATCH,
                    matched_value=f"{total_years:.1f} years",
                    score=1.0,
                    confidence=1.0,
                    is_satisfied=True,
                    evidence_source=EvidenceSource.EXPERIENCE_TECHNOLOGIES,
                    evidence=f"Candidate has {total_years:.1f} years total experience across {len(candidate.experience)} roles and {num_internships} internships",
                    rationale=f"Candidate exceeds required experience threshold ({total_years:.1f} years >= {min_years} years)",
                )
            ]
        elif total_years > 0:
            score = round(min(0.90, total_years / min_years), 2)
            return [
                RequirementMatch(
                    requirement_name=f"Minimum {min_years} Years Experience",
                    requirement_type=RequirementType.EXPERIENCE,
                    category=MatchCategory.RELATED_MATCH,
                    matched_value=f"{total_years:.1f} years",
                    score=score,
                    confidence=0.90,
                    is_satisfied=False,
                    evidence_source=EvidenceSource.EXPERIENCE_TECHNOLOGIES,
                    evidence=f"Candidate has {total_years:.1f} years total experience vs {min_years} years required",
                    rationale=f"Partial experience match: {total_years:.1f} of {min_years} required years fulfilled",
                )
            ]
        else:
            # 0 years experience: check if strong projects provide partial substitution
            if num_projects >= 2:
                return [
                    RequirementMatch(
                        requirement_name=f"Minimum {min_years} Years Experience",
                        requirement_type=RequirementType.EXPERIENCE,
                        category=MatchCategory.RELATED_MATCH,
                        matched_value=f"{num_projects} projects (0 professional years)",
                        score=0.50,
                        confidence=0.85,
                        is_satisfied=False,
                        evidence_source=EvidenceSource.PROJECT_TECHNOLOGIES,
                        evidence=f"Candidate demonstrates hands-on implementation across {num_projects} technical projects",
                        rationale=f"Candidate lacks professional experience ({min_years} years required), but demonstrates relevant hands-on project work",
                    )
                ]
            else:
                return [
                    RequirementMatch(
                        requirement_name=f"Minimum {min_years} Years Experience",
                        requirement_type=RequirementType.EXPERIENCE,
                        category=MatchCategory.MISSING,
                        matched_value="0 years",
                        score=0.0,
                        confidence=1.0,
                        is_satisfied=False,
                        evidence_source=EvidenceSource.NONE,
                        evidence=f"Candidate has 0 professional years and lacks required {min_years} years of experience",
                        rationale=f"Candidate has 0 professional years and lacks required {min_years} years of experience",
                    )
                ]

    # ------------------------------------------------------------------------
    # Dimension D: Education and Placement Eligibility Matching
    # ------------------------------------------------------------------------

    def _match_education(
        self,
        candidate: CandidateProfile,
        edu_req: EducationRequirement,
        eligibility: Any,
    ) -> list[RequirementMatch]:
        """Match academic qualifications and campus placement criteria."""
        matches: list[RequirementMatch] = []

        is_specified = (
            bool(edu_req.degrees)
            or bool(edu_req.degree_levels)
            or bool(edu_req.fields_of_study)
            or getattr(eligibility, "min_cgpa", None) is not None
            or getattr(eligibility, "min_percentage", None) is not None
        )

        if not is_specified:
            return []

        # 1. Degree / Degree Level Evaluation
        if edu_req.degrees or edu_req.degree_levels:
            req_degrees_lower = {d.lower() for d in edu_req.degrees}
            req_levels_lower = {lvl.lower() for lvl in edu_req.degree_levels}
            deg_matched = False

            for idx, edu in enumerate(candidate.education):
                cand_deg = (edu.degree or "").strip()
                cand_lvl = (edu.degree_level or "").strip().lower()

                # Check direct degree name or degree level
                if (
                    cand_deg.lower() in req_degrees_lower
                    or cand_lvl in req_levels_lower
                    or any(req_deg in cand_deg.lower() for req_deg in req_degrees_lower)
                ):
                    matches.append(
                        RequirementMatch(
                            requirement_name=f"Degree: {', '.join(edu_req.degrees or edu_req.degree_levels)}",
                            requirement_type=RequirementType.EDUCATION,
                            category=MatchCategory.EXACT_MATCH,
                            matched_value=cand_deg or cand_lvl,
                            score=1.0,
                            confidence=1.0,
                            is_satisfied=True,
                            evidence_source=EvidenceSource.EDUCATION_RECORD,
                            evidence=f"CandidateProfile.education[{idx}]: '{cand_deg}' ({cand_lvl}) at '{edu.institution or 'University'}'",
                            rationale=f"Candidate qualification '{cand_deg}' satisfies required degree level",
                        )
                    )
                    deg_matched = True
                    break

            if not deg_matched:
                if candidate.education:
                    # Candidate has education, but degree level mismatch
                    edu_first = candidate.education[0]
                    matches.append(
                        RequirementMatch(
                            requirement_name=f"Degree: {', '.join(edu_req.degrees or edu_req.degree_levels)}",
                            requirement_type=RequirementType.EDUCATION,
                            category=MatchCategory.RELATED_MATCH,
                            matched_value=edu_first.degree or edu_first.degree_level,
                            score=0.40,
                            confidence=0.85,
                            is_satisfied=False,
                            evidence_source=EvidenceSource.EDUCATION_RECORD,
                            evidence=f"CandidateProfile.education[0]: '{edu_first.degree}' ({edu_first.degree_level})",
                            rationale=f"Candidate degree '{edu_first.degree}' does not match required {', '.join(edu_req.degrees or edu_req.degree_levels)}",
                        )
                    )
                else:
                    matches.append(
                        RequirementMatch(
                            requirement_name=f"Degree: {', '.join(edu_req.degrees or edu_req.degree_levels)}",
                            requirement_type=RequirementType.EDUCATION,
                            category=MatchCategory.MISSING,
                            matched_value=None,
                            score=0.0,
                            confidence=1.0,
                            is_satisfied=False,
                            evidence_source=EvidenceSource.NONE,
                            evidence=f"Candidate has no education records matching required {', '.join(edu_req.degrees or edu_req.degree_levels)}",
                            rationale=f"Candidate has no education records matching required {', '.join(edu_req.degrees or edu_req.degree_levels)}",
                        )
                    )

        # 2. Field of Study Evaluation
        if edu_req.fields_of_study:
            field_matched = False
            for idx, edu in enumerate(candidate.education):
                cand_field = (edu.field_of_study or "").lower()
                for req_field in edu_req.fields_of_study:
                    if req_field.lower() in cand_field or cand_field in req_field.lower():
                        matches.append(
                            RequirementMatch(
                                requirement_name=f"Field of Study: {', '.join(edu_req.fields_of_study)}",
                                requirement_type=RequirementType.EDUCATION,
                                category=MatchCategory.EXACT_MATCH,
                                matched_value=edu.field_of_study,
                                score=1.0,
                                confidence=1.0,
                                is_satisfied=True,
                                evidence_source=EvidenceSource.EDUCATION_RECORD,
                                evidence=f"CandidateProfile.education[{idx}].field_of_study: '{edu.field_of_study}'",
                                rationale=f"Candidate major '{edu.field_of_study}' matches required field",
                            )
                        )
                        field_matched = True
                        break
                if field_matched:
                    break

            if not field_matched and candidate.education:
                matches.append(
                    RequirementMatch(
                        requirement_name=f"Field of Study: {', '.join(edu_req.fields_of_study)}",
                        requirement_type=RequirementType.EDUCATION,
                        category=MatchCategory.RELATED_MATCH,
                        matched_value=candidate.education[0].field_of_study,
                        score=0.60,
                        confidence=0.85,
                        is_satisfied=False,
                        evidence_source=EvidenceSource.EDUCATION_RECORD,
                        evidence=f"CandidateProfile.education[0].field_of_study: '{candidate.education[0].field_of_study}'",
                        rationale="Related academic field, but does not match required discipline exactly",
                    )
                )

        # 3. Placement Eligibility (CGPA / Percentage Cutoff)
        min_cgpa = getattr(eligibility, "min_cgpa", None)
        if min_cgpa is not None:
            cgpa_matched = False
            for idx, edu in enumerate(candidate.education):
                if edu.cgpa is not None:
                    if edu.cgpa >= min_cgpa:
                        matches.append(
                            RequirementMatch(
                                requirement_name=f"Minimum CGPA Cutoff: {min_cgpa}",
                                requirement_type=RequirementType.ELIGIBILITY,
                                category=MatchCategory.EXACT_MATCH,
                                matched_value=f"CGPA {edu.cgpa}",
                                score=1.0,
                                confidence=1.0,
                                is_satisfied=True,
                                evidence_source=EvidenceSource.EDUCATION_RECORD,
                                evidence=f"CandidateProfile.education[{idx}].cgpa: {edu.cgpa} >= cutoff {min_cgpa}",
                                rationale=f"Candidate CGPA {edu.cgpa} satisfies placement eligibility cutoff {min_cgpa}",
                            )
                        )
                        cgpa_matched = True
                        break
                    else:
                        matches.append(
                            RequirementMatch(
                                requirement_name=f"Minimum CGPA Cutoff: {min_cgpa}",
                                requirement_type=RequirementType.ELIGIBILITY,
                                category=MatchCategory.MISSING,
                                matched_value=f"CGPA {edu.cgpa}",
                                score=0.0,
                                confidence=1.0,
                                is_satisfied=False,
                                evidence_source=EvidenceSource.EDUCATION_RECORD,
                                evidence=f"CandidateProfile.education[{idx}].cgpa: {edu.cgpa} < cutoff {min_cgpa}",
                                rationale=f"Candidate CGPA {edu.cgpa} does not satisfy placement cutoff {min_cgpa}",
                            )
                        )
                        cgpa_matched = True
                        break

            if not cgpa_matched:
                matches.append(
                    RequirementMatch(
                        requirement_name=f"Minimum CGPA Cutoff: {min_cgpa}",
                        requirement_type=RequirementType.ELIGIBILITY,
                        category=MatchCategory.UNCERTAIN,
                        matched_value=None,
                        score=0.50,
                        confidence=0.50,
                        is_satisfied=False,
                        evidence_source=EvidenceSource.NONE,
                        evidence=f"CGPA cutoff {min_cgpa} specified, but candidate profile does not record CGPA",
                        rationale=f"CGPA cutoff {min_cgpa} specified, but candidate profile does not record CGPA",
                    )
                )

        return matches

    # ------------------------------------------------------------------------
    # Dimension E: Relevant Projects Matching
    # ------------------------------------------------------------------------

    def _match_projects(
        self,
        candidate: CandidateProfile,
        job: ParsedJobDescription,
    ) -> list[RequirementMatch]:
        """Evaluate candidate project portfolio against job role requirements."""
        # If job specifies no technical skills and no responsibilities, project alignment is unstated
        if not job.required_technical_skills and not job.preferred_technical_skills and not job.responsibilities:
            return []

        required_skill_names = {
            (req.canonical_name or req.matched_alias).lower()
            for req in job.required_technical_skills
        }
        all_job_skill_names = required_skill_names.union(
            {(req.canonical_name or req.matched_alias).lower() for req in job.preferred_technical_skills}
        )

        num_projects = len(candidate.projects)

        if num_projects == 0:
            # Check if professional experience compensates
            if len(candidate.experience) >= 1:
                return [
                    RequirementMatch(
                        requirement_name="Relevant Technical Projects",
                        requirement_type=RequirementType.PROJECT,
                        category=MatchCategory.EXACT_MATCH,
                        matched_value="Professional Experience Substitution",
                        score=0.85,
                        confidence=0.90,
                        is_satisfied=True,
                        evidence_source=EvidenceSource.EXPERIENCE_TECHNOLOGIES,
                        evidence=f"Candidate has {len(candidate.experience)} professional roles compensating for standalone projects",
                        rationale="Candidate demonstrates practical software engineering via industry experience",
                    )
                ]
            else:
                return [
                    RequirementMatch(
                        requirement_name="Relevant Technical Projects",
                        requirement_type=RequirementType.PROJECT,
                        category=MatchCategory.MISSING,
                        matched_value="0 projects",
                        score=0.0,
                        confidence=1.0,
                        is_satisfied=False,
                        evidence_source=EvidenceSource.NONE,
                        evidence="Candidate profile contains no academic or personal project records",
                        rationale="Candidate profile contains no academic or personal project records",
                    )
                ]

        # Count projects utilizing required/preferred technologies
        relevant_projects: list[tuple[ProjectEntry, int]] = []
        for proj in candidate.projects:
            proj_techs_lower = {t.lower() for t in proj.technologies}
            matched_techs = proj_techs_lower.intersection(all_job_skill_names)
            if matched_techs:
                relevant_projects.append((proj, len(matched_techs)))

        if len(relevant_projects) >= 2:
            top_titles = [p[0].title or "Project" for p in relevant_projects[:3]]
            return [
                RequirementMatch(
                    requirement_name="Relevant Technical Projects",
                    requirement_type=RequirementType.PROJECT,
                    category=MatchCategory.EXACT_MATCH,
                    matched_value=f"{len(relevant_projects)} aligned projects",
                    score=1.0,
                    confidence=1.0,
                    is_satisfied=True,
                    evidence_source=EvidenceSource.PROJECT_TECHNOLOGIES,
                    evidence=f"Aligned projects: {', '.join(top_titles)}",
                    rationale=f"Candidate showcases {len(relevant_projects)} projects directly employing job tech stack",
                )
            ]
        elif len(relevant_projects) == 1:
            proj_title = relevant_projects[0][0].title or "Project"
            return [
                RequirementMatch(
                    requirement_name="Relevant Technical Projects",
                    requirement_type=RequirementType.PROJECT,
                    category=MatchCategory.EXACT_MATCH,
                    matched_value="1 aligned project",
                    score=0.85,
                    confidence=0.95,
                    is_satisfied=True,
                    evidence_source=EvidenceSource.PROJECT_TECHNOLOGIES,
                    evidence=f"Aligned project: '{proj_title}' ({relevant_projects[0][0].technologies})",
                    rationale=f"Candidate demonstrates relevant hands-on work in project '{proj_title}'",
                )
            ]
        else:
            # Projects exist, but technologies differ
            return [
                RequirementMatch(
                    requirement_name="Relevant Technical Projects",
                    requirement_type=RequirementType.PROJECT,
                    category=MatchCategory.RELATED_MATCH,
                    matched_value=f"{num_projects} general projects",
                    score=0.50,
                    confidence=0.90,
                    is_satisfied=False,
                    evidence_source=EvidenceSource.PROJECT_TECHNOLOGIES,
                    evidence=f"Candidate has {num_projects} projects with other technologies: {[p.title for p in candidate.projects[:2]]}",
                    rationale="Candidate demonstrates software building capability, but tech stack differs from job requirements",
                )
            ]

    # ------------------------------------------------------------------------
    # Scoring Aggregation & Explainability
    # ------------------------------------------------------------------------

    def _aggregate_scores(
        self,
        candidate: CandidateProfile,
        job: ParsedJobDescription,
        req_tech_matches: list[RequirementMatch],
        pref_tech_matches: list[RequirementMatch],
        soft_matches: list[RequirementMatch],
        exp_matches: list[RequirementMatch],
        edu_matches: list[RequirementMatch],
        proj_matches: list[RequirementMatch],
    ) -> tuple[float, float, ConfidenceLevel, dict[str, ComponentScore], list[str]]:
        """
        Compute weighted overall score, component scores, confidence, and explanations.
        """
        comp_scores: dict[str, ComponentScore] = {}
        explanations: list[str] = []

        # Helper to compute a dimension's earned score and count
        def _calc_dim(matches: list[RequirementMatch], dim_name: str, weight: float) -> tuple[float, float, ComponentScore]:
            total = len(matches)
            if total == 0:
                # Dimension was unstated by JD -> neutralized
                comp = ComponentScore(
                    category=dim_name,
                    earned_score=1.0,
                    max_score=1.0,
                    weight=0.0,
                    weighted_score=0.0,
                    percentage=100.0,
                    matched_count=0,
                    total_count=0,
                    explanation=f"No {dim_name} specified in job description",
                )
                return 0.0, 0.0, comp

            earned = sum(m.score for m in matches)
            max_s = float(total)
            matched_c = sum(1 for m in matches if m.is_satisfied)
            pct = round((earned / max_s) * 100.0, 1) if max_s > 0 else 0.0
            w_score = (earned / max_s) * weight

            expl = f"{matched_c}/{total} requirements satisfied ({pct}%)"
            comp = ComponentScore(
                category=dim_name,
                earned_score=round(earned, 2),
                max_score=round(max_s, 2),
                weight=weight,
                weighted_score=round(w_score, 4),
                percentage=pct,
                matched_count=matched_c,
                total_count=total,
                explanation=expl,
            )
            return w_score, weight, comp

        # 1. Required Technical Skills (Weight: 0.40)
        w_req, act_req, comp_req = _calc_dim(req_tech_matches, "required_technical_skills", self.weights.required_skills_weight)
        comp_scores["required_technical_skills"] = comp_req

        # 2. Preferred Technical Skills (Weight: 0.15)
        w_pref, act_pref, comp_pref = _calc_dim(pref_tech_matches, "preferred_technical_skills", self.weights.preferred_skills_weight)
        comp_scores["preferred_technical_skills"] = comp_pref

        # 3. Experience (Weight: 0.15)
        w_exp, act_exp, comp_exp = _calc_dim(exp_matches, "relevant_experience", self.weights.experience_weight)
        comp_scores["relevant_experience"] = comp_exp

        # 4. Relevant Projects (Weight: 0.15)
        w_proj, act_proj, comp_proj = _calc_dim(proj_matches, "relevant_projects", self.weights.projects_weight)
        comp_scores["relevant_projects"] = comp_proj

        # 5. Education & Eligibility (Weight: 0.10)
        w_edu, act_edu, comp_edu = _calc_dim(edu_matches, "education_alignment", self.weights.education_weight)
        comp_scores["education_alignment"] = comp_edu

        # 6. Soft Skills (Weight: 0.05)
        w_soft, act_soft, comp_soft = _calc_dim(soft_matches, "soft_skills", self.weights.soft_skills_weight)
        comp_scores["soft_skills"] = comp_soft

        # Compute dynamic normalized overall score
        total_earned_weighted = w_req + w_pref + w_exp + w_proj + w_edu + w_soft
        total_active_weight = act_req + act_pref + act_exp + act_proj + act_edu + act_soft

        if total_active_weight > 0:
            overall_score = (total_earned_weighted / total_active_weight) * 100.0
        else:
            overall_score = 0.0

        # Confidence calculation
        confidence = 0.95
        conf_level = ConfidenceLevel.HIGH

        # Insufficient JD information detection
        jd_len = job.metadata.raw_text_length if job.metadata else 0
        total_jd_reqs = len(req_tech_matches) + len(pref_tech_matches) + len(soft_matches)

        if total_jd_reqs == 0 or (jd_len > 0 and jd_len < 100):
            confidence = 0.40
            conf_level = ConfidenceLevel.LOW
            explanations.append(
                "Limited confidence: Job description provides minimal structured requirements; match score should be interpreted cautiously."
            )
        elif len(req_tech_matches) == 0:
            confidence = 0.65
            conf_level = ConfidenceLevel.MEDIUM
            explanations.append(
                "Moderate confidence: No core required technical skills were detected in the job description."
            )

        # Candidate profile completeness check
        if not candidate.technical_skills and not candidate.projects and not candidate.experience:
            confidence = min(confidence, 0.50)
            conf_level = ConfidenceLevel.LOW
            explanations.append(
                "Limited confidence: Candidate profile has empty skills, projects, and experience sections."
            )

        explanations.append(
            f"Overall match score: {overall_score:.1f}% (Required skills: {comp_req.percentage}%, Preferred skills: {comp_pref.percentage}%, Experience: {comp_exp.percentage}%, Projects: {comp_proj.percentage}%, Education: {comp_edu.percentage}%)"
        )

        return overall_score, confidence, conf_level, comp_scores, explanations


# Global convenience function
def match_resume_to_job(
    candidate: CandidateProfile,
    job: ParsedJobDescription,
    weights: MatchingWeights | None = None,
) -> JobMatchResult:
    """
    Convenience function to match a CandidateProfile against a ParsedJobDescription.
    """
    return ResumeJobMatcher(weights=weights).match(candidate, job)


__all__ = [
    "ResumeJobMatcher",
    "calculate_text_similarity",
    "match_resume_to_job",
]
