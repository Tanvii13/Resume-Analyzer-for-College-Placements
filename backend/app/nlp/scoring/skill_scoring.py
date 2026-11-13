"""
Skill visibility evaluator for Sprint 3 Module A.

Evaluates:
- Technical skill volume and depth.
- Skill categorization and diversity across domains (languages, frameworks, databases, cloud, etc.).
- Contextual verification (skills substantiated in projects, experience, or multiple occurrences).
- Soft skills visibility and presence.
- Redundancy and duplicate presentation detection.

Guarantees:
- Completely deterministic rule-based evaluation.
- No job-specific matching (reserved for Sprint 4).
- Personal attributes NEVER affect score.
"""

from typing import Dict, List, Set, Tuple
from app.nlp.schemas import CandidateProfile, SkillItem
from app.nlp.scoring.schemas import ComponentScore, ScoreDeduction
from app.nlp.scoring.weights import COMPONENT_SKILL_VISIBILITY

# Standard foundational college placement skill categories
CORE_CATEGORIES = {
    "languages",
    "frameworks_and_libraries",
    "databases",
    "cloud_and_devops",
    "core_cs",
    "tools_and_platforms",
    "ai_ml_data_science",
}


class SkillVisibilityScorer:
    """Evaluates technical and soft skill presence, categorization, and contextual backing."""

    def __init__(self, max_score: float = 25.0):
        self.max_score = max_score

    def score(self, profile: CandidateProfile) -> Tuple[ComponentScore, List[ScoreDeduction], List[str]]:
        earned_score = 0.0
        deductions: List[ScoreDeduction] = []
        strengths: List[str] = []
        evidence: List[str] = []
        improvements: List[str] = []

        tech_skills: List[SkillItem] = profile.technical_skills or []
        soft_skills: List[SkillItem] = profile.soft_skills or []
        skills_by_cat: Dict[str, List[str]] = profile.skills_by_category or {}

        # ---------------------------------------------------------------------
        # 1. Technical Skill Volume & Inventory (35% of max_score)
        # ---------------------------------------------------------------------
        vol_weight = self.max_score * 0.35
        unique_canonical_skills: Set[str] = {
            s.canonical_name.strip().lower() for s in tech_skills if s.canonical_name
        }
        num_skills = len(unique_canonical_skills)

        if num_skills >= 8:
            vol_score = vol_weight
            evidence.append(f"Strong technical skill inventory: {num_skills} unique skills recognized.")
            strengths.append(f"Extensive technical skill profile ({num_skills} verified technical skills).")
        elif num_skills >= 5:
            vol_score = vol_weight * 0.80
            evidence.append(f"Adequate technical skill inventory: {num_skills} skills recognized.")
            improvements.append("Expand technical skill list with tools, libraries, or frameworks used in coursework or projects.")
        elif num_skills >= 2:
            vol_score = vol_weight * 0.50
            evidence.append(f"Limited technical skill inventory: {num_skills} skills recognized.")
            deductions.append(
                ScoreDeduction(
                    component=COMPONENT_SKILL_VISIBILITY,
                    rule_id="SKILL_LIMITED_INVENTORY",
                    points_deducted=round(vol_weight * 0.50, 2),
                    reason=f"Resume lists only {num_skills} technical skills. Aim for 8+ skills covering languages, tools, and databases.",
                    evidence=f"Recognized skills: {', '.join(sorted(unique_canonical_skills))}",
                )
            )
            improvements.append("Add foundational technical skills such as Git, SQL, Python, or Web technologies.")
        elif num_skills == 1:
            vol_score = vol_weight * 0.20
            deductions.append(
                ScoreDeduction(
                    component=COMPONENT_SKILL_VISIBILITY,
                    rule_id="SKILL_VERY_LOW_INVENTORY",
                    points_deducted=round(vol_weight * 0.80, 2),
                    reason="Only 1 technical skill was recognized in the resume.",
                    evidence=f"Recognized skill: {list(unique_canonical_skills)[0]}",
                )
            )
            improvements.append("Dedicate a clear 'Skills' section listing languages, frameworks, developer tools, and databases.")
        else:
            vol_score = 0.0
            deductions.append(
                ScoreDeduction(
                    component=COMPONENT_SKILL_VISIBILITY,
                    rule_id="SKILL_NONE_DETECTED",
                    points_deducted=round(vol_weight, 2),
                    reason="No technical skills were recognized in the resume.",
                    evidence="technical_skills list is empty",
                )
            )
            improvements.append("Include an explicit 'Technical Skills' section categorizing your programming languages, tools, and databases.")

        earned_score += vol_score

        # ---------------------------------------------------------------------
        # 2. Skill Categorization & Domain Diversity (30% of max_score)
        # ---------------------------------------------------------------------
        div_weight = self.max_score * 0.30

        # Collect distinct populated categories
        active_categories: Set[str] = set()
        for cat, items in skills_by_cat.items():
            if items and cat.strip():
                active_categories.add(cat.strip().lower())
        for s in tech_skills:
            if s.category and s.category.strip():
                active_categories.add(s.category.strip().lower())

        num_categories = len(active_categories)

        if num_categories >= 4:
            div_score = div_weight
            evidence.append(f"Well-rounded skill distribution across {num_categories} domains: {', '.join(sorted(active_categories))}.")
            strengths.append(f"Demonstrates well-rounded technical breadth across {num_categories} domains (e.g. languages, databases, web/cloud).")
        elif num_categories == 3:
            div_score = div_weight * 0.80
            evidence.append(f"Good domain distribution across 3 categories: {', '.join(sorted(active_categories))}.")
        elif num_categories == 2:
            div_score = div_weight * 0.55
            evidence.append(f"Moderate domain diversity ({num_categories} categories).")
            improvements.append("Diversify skills across more categories, such as Databases, Developer Tools, or Cloud/DevOps.")
        elif num_categories == 1:
            div_score = div_weight * 0.30
            deductions.append(
                ScoreDeduction(
                    component=COMPONENT_SKILL_VISIBILITY,
                    rule_id="SKILL_POOR_DIVERSITY",
                    points_deducted=round(div_weight * 0.70, 2),
                    reason="Technical skills are concentrated in only 1 category. Placement recruiters favor well-rounded engineers.",
                    evidence=f"Active category: {list(active_categories)[0]}",
                )
            )
            improvements.append("Organize your skills section with subsections: Languages, Frameworks, Databases, and Developer Tools.")
        else:
            div_score = 0.0
            if num_skills > 0:
                deductions.append(
                    ScoreDeduction(
                        component=COMPONENT_SKILL_VISIBILITY,
                        rule_id="SKILL_UNCATEGORIZED",
                        points_deducted=round(div_weight, 2),
                        reason="Technical skills lack categorization into structured domains.",
                        evidence="0 categories detected",
                    )
                )

        earned_score += div_score

        # ---------------------------------------------------------------------
        # 3. Contextual Verification in Experience & Projects (20% of max_score)
        # ---------------------------------------------------------------------
        ctx_weight = self.max_score * 0.20

        # Gather technologies declared in projects and experience
        context_technologies: Set[str] = set()
        for p in (profile.projects or []):
            for t in (p.technologies or []):
                if t:
                    context_technologies.add(t.strip().lower())
        for exp in (profile.experience or []):
            for t in (exp.technologies_used or []):
                if t:
                    context_technologies.add(t.strip().lower())
        for exp in (profile.internships or []):
            for t in (exp.technologies_used or []):
                if t:
                    context_technologies.add(t.strip().lower())

        # Also skills that have occurrences > 1 or source_section outside 'skills'
        substantiated_skills: Set[str] = set()
        for s in tech_skills:
            cname = s.canonical_name.strip().lower()
            if cname in context_technologies:
                substantiated_skills.add(cname)
            elif s.occurrences > 1:
                substantiated_skills.add(cname)
            elif s.source_section and s.source_section.lower() in ("projects", "experience", "work_experience"):
                substantiated_skills.add(cname)

        if num_skills > 0:
            substantiated_ratio = len(substantiated_skills) / float(num_skills)
            if substantiated_ratio >= 0.40 or len(substantiated_skills) >= 4:
                ctx_score = ctx_weight
                evidence.append(f"{len(substantiated_skills)} skills substantiated with practical application in projects or work experience.")
                strengths.append("Key technical skills are practically demonstrated within project descriptions and work experience.")
            elif substantiated_ratio >= 0.20 or len(substantiated_skills) >= 2:
                ctx_score = ctx_weight * 0.70
                evidence.append(f"{len(substantiated_skills)} skills directly backed by project or experience descriptions.")
                improvements.append("Explicitly mention how your listed skills were applied within your project bullet points.")
            elif len(substantiated_skills) >= 1:
                ctx_score = ctx_weight * 0.40
                improvements.append("Connect more of your listed skills to specific project deliverables to substantiate your expertise.")
            else:
                ctx_score = 0.0
                deductions.append(
                    ScoreDeduction(
                        component=COMPONENT_SKILL_VISIBILITY,
                        rule_id="SKILL_UNSUBSTANTIATED",
                        points_deducted=round(ctx_weight, 2),
                        reason="Listed skills appear isolated without being mentioned in project or work experience bullet points.",
                        evidence="0 skills found in project/experience descriptions",
                    )
                )
                improvements.append("Integrate your listed skills (e.g. tools, frameworks) directly into project bullets showing real application.")
        else:
            ctx_score = 0.0

        earned_score += ctx_score

        # ---------------------------------------------------------------------
        # 4. Soft Skills Visibility (15% of max_score)
        # ---------------------------------------------------------------------
        soft_weight = self.max_score * 0.15
        unique_soft: Set[str] = {
            s.canonical_name.strip().lower() for s in soft_skills if s.canonical_name
        }
        num_soft = len(unique_soft)

        if num_soft >= 3:
            soft_score = soft_weight
            evidence.append(f"Identified {num_soft} soft/interpersonal skills: {', '.join(sorted(unique_soft))}.")
            strengths.append(f"Balances technical capabilities with key soft skills ({', '.join(sorted(unique_soft)[:3])}).")
        elif num_soft in (1, 2):
            soft_score = soft_weight * 0.65
            evidence.append(f"Identified {num_soft} soft skill(s): {', '.join(sorted(unique_soft))}.")
            improvements.append("Include 1-2 additional professional soft skills (e.g., Problem Solving, Team Collaboration, Agile).")
        else:
            soft_score = 0.0
            deductions.append(
                ScoreDeduction(
                    component=COMPONENT_SKILL_VISIBILITY,
                    rule_id="SKILL_NO_SOFT_SKILLS",
                    points_deducted=round(soft_weight, 2),
                    reason="No professional soft skills (e.g., Leadership, Communication, Problem Solving) were detected.",
                    evidence="soft_skills list is empty",
                )
            )
            improvements.append("Highlight soft skills such as Team Collaboration, Communication, and Agile Methodology.")

        earned_score += soft_score

        # ---------------------------------------------------------------------
        # 5. Redundancy & Duplicate Presentation Check (Penalty deduction)
        # ---------------------------------------------------------------------
        # Check if canonical skills have identical matched aliases repeated pointlessly
        seen_aliases: Dict[str, int] = {}
        for s in tech_skills:
            alias = s.matched_alias.strip().lower()
            seen_aliases[alias] = seen_aliases.get(alias, 0) + 1

        duplicates = [alias for alias, count in seen_aliases.items() if count > 2]
        if duplicates:
            penalty = min(2.0, len(duplicates) * 0.75)
            earned_score = max(0.0, earned_score - penalty)
            deductions.append(
                ScoreDeduction(
                    component=COMPONENT_SKILL_VISIBILITY,
                    rule_id="SKILL_DUPLICATE_PRESENTATION",
                    points_deducted=round(penalty, 2),
                    reason=f"Detected repetitive skill listings for: {', '.join(duplicates[:3])}.",
                    evidence=f"Repeated items: {', '.join(duplicates)}",
                )
            )
            improvements.append("Consolidate duplicate skill listings to keep your skills section concise.")

        # Final Clamp
        final_score = round(max(0.0, min(self.max_score, earned_score)), 2)

        # Generate summary reason
        if final_score >= self.max_score * 0.85:
            reason = f"Excellent skill visibility ({final_score:.1f}/{self.max_score:.1f}). Strong inventory across diverse domains with project substantiation."
        elif final_score >= self.max_score * 0.65:
            reason = f"Good skill visibility ({final_score:.1f}/{self.max_score:.1f}). Adequate skills present; can improve domain breadth or project linking."
        elif final_score >= self.max_score * 0.40:
            reason = f"Fair skill visibility ({final_score:.1f}/{self.max_score:.1f}). Limited inventory or weak categorization detected."
        else:
            reason = f"Skill visibility needs improvement ({final_score:.1f}/{self.max_score:.1f}). Missing critical technical and soft skill evidence."

        component_score = ComponentScore(
            component=COMPONENT_SKILL_VISIBILITY,
            score=final_score,
            max_score=self.max_score,
            weight=self.max_score,
            evidence=evidence,
            reason=reason,
            how_to_improve=improvements,
        )

        return component_score, deductions, strengths
