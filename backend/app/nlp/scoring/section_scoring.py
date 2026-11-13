"""
Section completeness evaluator for Sprint 3 Module A.

Evaluates:
- Presence of critical sections (education, technical_skills, projects).
- Completeness of academic/education records (degree, institution, graduation year, CGPA/percentage).
- Contact information completeness (name, email, phone, professional links).
- Practical work completeness (projects, experience, internships) with Fresher accommodation.
- Integration with section_summary.missing_critical_sections.

Guarantees:
- Personal attributes (name, gender, college identity, email domain, phone string) NEVER affect score.
- Freshers lacking industry experience are not penalized if they demonstrate solid projects.
"""

from typing import List, Tuple
from app.nlp.schemas import CandidateProfile
from app.nlp.scoring.schemas import ComponentScore, ScoreDeduction
from app.nlp.scoring.weights import COMPONENT_SECTION_COMPLETENESS


class SectionCompletenessScorer:
    """Evaluates the completeness of sections and mandatory placement resume attributes."""

    def __init__(self, max_score: float = 25.0):
        self.max_score = max_score

    def score(self, profile: CandidateProfile) -> Tuple[ComponentScore, List[ScoreDeduction], List[str]]:
        earned_score = 0.0
        deductions: List[ScoreDeduction] = []
        strengths: List[str] = []
        evidence: List[str] = []
        improvements: List[str] = []

        # ---------------------------------------------------------------------
        # 1. Critical Sections Presence (30% of max_score)
        # ---------------------------------------------------------------------
        crit_weight = self.max_score * 0.30
        missing_critical = list(profile.section_summary.missing_critical_sections or [])

        # Check explicit presence in profile objects as well
        has_edu_sec = bool(profile.education) or ("education" in profile.section_summary.identified_sections)
        has_skills_sec = bool(profile.technical_skills) or ("technical_skills" in profile.section_summary.identified_sections)
        has_proj_sec = bool(profile.projects) or ("projects" in profile.section_summary.identified_sections)

        missing_set = set(missing_critical)
        if not has_edu_sec:
            missing_set.add("education")
        if not has_skills_sec:
            missing_set.add("technical_skills")
        if not has_proj_sec:
            missing_set.add("projects")

        crit_fraction = (3 - len(missing_set)) / 3.0
        crit_points = max(0.0, crit_weight * crit_fraction)
        earned_score += crit_points

        if not missing_set:
            evidence.append("All critical sections present: education, technical skills, projects.")
            strengths.append("Contains all essential core sections required for placement shortlisting.")
        else:
            for missing_sec in sorted(list(missing_set)):
                sec_label = missing_sec.replace("_", " ").title()
                ded_pts = round(crit_weight / 3.0, 2)
                deductions.append(
                    ScoreDeduction(
                        component=COMPONENT_SECTION_COMPLETENESS,
                        rule_id=f"SEC_MISSING_{missing_sec.upper()}",
                        points_deducted=ded_pts,
                        reason=f"Missing critical section: {sec_label}.",
                        evidence=f"Section '{missing_sec}' was not identified in candidate profile.",
                    )
                )
                improvements.append(f"Add a clearly labeled '{sec_label}' section to your resume.")

        # ---------------------------------------------------------------------
        # 2. Contact Information Completeness (20% of max_score)
        # ---------------------------------------------------------------------
        contact_weight = self.max_score * 0.20
        contact = profile.contact

        # Neutral existence checks (NEVER value/identity checks)
        has_name = bool(contact.full_name and contact.full_name.strip())
        has_email = bool(contact.email and contact.email.strip())
        has_phone = bool(contact.phone and contact.phone.strip())
        has_links = bool(
            (contact.linkedin_url and contact.linkedin_url.strip())
            or (contact.github_url and contact.github_url.strip())
            or (contact.portfolio_url and contact.portfolio_url.strip())
            or bool(contact.coding_profiles)
        )

        contact_items = [has_name, has_email, has_phone, has_links]
        contact_fraction = sum(1 for item in contact_items if item) / 4.0
        contact_points = contact_weight * contact_fraction
        earned_score += contact_points

        if has_email and has_phone:
            evidence.append("Essential contact details (email and phone) are verified.")
        if has_links:
            evidence.append("Professional profile links (LinkedIn/GitHub/Portfolio/Coding profiles) detected.")
            strengths.append("Includes accessible professional and code portfolio links.")
        else:
            ded_pts = round(contact_weight * 0.25, 2)
            deductions.append(
                ScoreDeduction(
                    component=COMPONENT_SECTION_COMPLETENESS,
                    rule_id="SEC_MISSING_PROFILE_LINKS",
                    points_deducted=ded_pts,
                    reason="No professional online profile (GitHub, LinkedIn, or coding profile) identified.",
                    evidence="contact.linkedin_url and contact.github_url are empty.",
                )
            )
            improvements.append("Include active GitHub and LinkedIn profile links in your header.")

        if not has_email:
            ded_pts = round(contact_weight * 0.25, 2)
            deductions.append(
                ScoreDeduction(
                    component=COMPONENT_SECTION_COMPLETENESS,
                    rule_id="SEC_MISSING_EMAIL",
                    points_deducted=ded_pts,
                    reason="Primary email address is missing.",
                    evidence="contact.email is empty.",
                )
            )
            improvements.append("Add a primary professional email address.")

        if not has_phone:
            ded_pts = round(contact_weight * 0.25, 2)
            deductions.append(
                ScoreDeduction(
                    component=COMPONENT_SECTION_COMPLETENESS,
                    rule_id="SEC_MISSING_PHONE",
                    points_deducted=ded_pts,
                    reason="Contact phone number is missing.",
                    evidence="contact.phone is empty.",
                )
            )
            improvements.append("Add a valid 10-digit phone number with country code.")

        # ---------------------------------------------------------------------
        # 3. Education Information Completeness (25% of max_score)
        # ---------------------------------------------------------------------
        edu_weight = self.max_score * 0.25
        if not profile.education:
            # Already penalized under missing critical section, award 0 here with note
            deductions.append(
                ScoreDeduction(
                    component=COMPONENT_SECTION_COMPLETENESS,
                    rule_id="SEC_EDU_NO_ENTRIES",
                    points_deducted=round(edu_weight, 2),
                    reason="Education section has no parsed qualifications.",
                    evidence="profile.education list is empty.",
                )
            )
            improvements.append("Add your current degree, institution name, and academic performance.")
        else:
            primary_edu = profile.education[0]
            edu_has_degree = bool(primary_edu.degree and primary_edu.degree.strip())
            edu_has_inst = bool(primary_edu.institution and primary_edu.institution.strip())
            edu_has_year = bool(primary_edu.graduation_year or primary_edu.start_year)
            edu_has_score = bool(
                primary_edu.cgpa is not None or primary_edu.percentage is not None
            )

            edu_items = [edu_has_degree, edu_has_inst, edu_has_year, edu_has_score]
            edu_fraction = sum(1 for item in edu_items if item) / 4.0
            edu_points = edu_weight * edu_fraction
            earned_score += edu_points

            if edu_has_degree and edu_has_inst and edu_has_score:
                evidence.append("Academic record specifies degree qualification, institution, and CGPA/score.")
                strengths.append("Academic qualifications include clear degree, graduation year, and performance metrics.")

            if not edu_has_score:
                ded_pts = round(edu_weight * 0.25, 2)
                deductions.append(
                    ScoreDeduction(
                        component=COMPONENT_SECTION_COMPLETENESS,
                        rule_id="SEC_EDU_MISSING_CGPA",
                        points_deducted=ded_pts,
                        reason="Academic qualification lacks CGPA or percentage score.",
                        evidence="Neither cgpa nor percentage found in primary education entry.",
                    )
                )
                improvements.append("State your current CGPA (with scale, e.g. 8.5/10) or percentage for campus screening.")

            if not edu_has_year:
                ded_pts = round(edu_weight * 0.25, 2)
                deductions.append(
                    ScoreDeduction(
                        component=COMPONENT_SECTION_COMPLETENESS,
                        rule_id="SEC_EDU_MISSING_YEAR",
                        points_deducted=ded_pts,
                        reason="Education entry lacks graduation year or expected passing year.",
                        evidence="graduation_year is not specified.",
                    )
                )
                improvements.append("Indicate your graduation year (e.g. 2025 or Expected 2026).")

        # ---------------------------------------------------------------------
        # 4. Practical Work Completeness (Projects & Experience) (25% of max_score)
        # ---------------------------------------------------------------------
        prac_weight = self.max_score * 0.25
        num_projects = len(profile.projects)
        num_exp = len(profile.experience) + len(profile.internships)

        # Fresher accommodation rule:
        # If candidate has no industry experience, 2+ detailed projects yield full practical work credit.
        if num_exp > 0 and num_projects > 0:
            prac_fraction = 1.0
            evidence.append(f"Demonstrates both industry/internship experience ({num_exp} role(s)) and practical projects ({num_projects}).")
            strengths.append("Strong combination of industry/internship exposure and applied projects.")
        elif num_projects >= 2:
            # Fresher with solid project portfolio
            prac_fraction = 1.0
            evidence.append(f"Strong academic and personal project portfolio ({num_projects} projects) under fresher accommodation policy.")
            strengths.append("Comprehensive portfolio of applied projects demonstrating technical implementation skills.")
        elif num_projects == 1:
            if num_exp > 0:
                prac_fraction = 0.90
                evidence.append(f"Practical experience confirmed: 1 project and {num_exp} work experience entry.")
            else:
                prac_fraction = 0.65
                evidence.append("Single project detected with no internship experience.")
                deductions.append(
                    ScoreDeduction(
                        component=COMPONENT_SECTION_COMPLETENESS,
                        rule_id="SEC_FEW_PROJECTS",
                        points_deducted=round(prac_weight * 0.35, 2),
                        reason="Only 1 project found. Campus placement recruiters typically look for at least 2 distinct projects.",
                        evidence=f"projects count = {num_projects}, experience count = 0.",
                    )
                )
                improvements.append("Add a second substantial academic, capstone, or personal project.")
        elif num_exp > 0 and num_projects == 0:
            prac_fraction = 0.70
            evidence.append(f"Work experience present ({num_exp} role(s)), but lacks separate academic/technical projects.")
            deductions.append(
                ScoreDeduction(
                    component=COMPONENT_SECTION_COMPLETENESS,
                    rule_id="SEC_MISSING_PROJECTS",
                    points_deducted=round(prac_weight * 0.30, 2),
                    reason="No standalone technical projects listed.",
                    evidence="projects list is empty.",
                )
            )
            improvements.append("Include technical projects highlighting tools and architectures you built.")
        else:
            prac_fraction = 0.0
            deductions.append(
                ScoreDeduction(
                    component=COMPONENT_SECTION_COMPLETENESS,
                    rule_id="SEC_NO_PRACTICAL_WORK",
                    points_deducted=round(prac_weight, 2),
                    reason="No projects or internship experience found.",
                    evidence="Both projects and experience/internship lists are empty.",
                )
            )
            improvements.append("Add at least two technical projects showcasing your coding skills and problem-solving abilities.")

        earned_score += prac_weight * prac_fraction

        final_score = round(max(0.0, min(self.max_score, earned_score)), 2)

        reason = (
            f"Section completeness earned {final_score}/{self.max_score} points. "
            f"{'All core sections and contact details verified.' if not missing_set else f'Missing sections: {', '.join(sorted(missing_set))}.'}"
        )

        return (
            ComponentScore(
                component=COMPONENT_SECTION_COMPLETENESS,
                score=final_score,
                max_score=self.max_score,
                weight=self.max_score,
                evidence=evidence,
                reason=reason,
                how_to_improve=improvements,
            ),
            deductions,
            strengths,
        )


__all__ = ["SectionCompletenessScorer"]
