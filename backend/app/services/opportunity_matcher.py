import json
import os
from pathlib import Path
from typing import Dict, List, Set, Any, Tuple

from app.services.skill_extractor import SkillExtractor


TAXONOMY_PATH = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "skills_taxonomy.json"
)


class OpportunityMatcherService:

    def __init__(self, taxonomy_path: str = str(TAXONOMY_PATH)):
        self.skill_extractor = SkillExtractor(taxonomy_path=taxonomy_path)
        self.aliases, self.related_skills = self._load_taxonomy_extras(taxonomy_path)

    def _load_taxonomy_extras(self, path: str) -> Tuple[Dict[str, str], Dict[str, List[str]]]:
        """Loads aliases and related skill affinity groups safely from taxonomy."""
        file_path = Path(path)
        if not file_path.is_file():
            return {}, {}

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        aliases = {
            str(k).strip().lower(): str(v).strip()
            for k, v in data.get("aliases", {}).items()
        }

        related = {
            str(k).strip().lower(): [str(item).strip() for item in v]
            for k, v in data.get("related_skills", {}).items()
        }

        return aliases, related

    def normalize_skill(self, skill_name: str) -> str:
        """Converts skill aliases into standard canonical names."""
        clean = skill_name.strip()
        if not clean:
            return ""
        return self.aliases.get(clean.lower(), clean)

    def match_skills_against_tier(
        self,
        candidate_skills_lower: Set[str],
        tier_skills: List[str]
    ) -> Tuple[List[str], List[str], List[str]]:
        """
        Categorizes skills into:
        1. Exact Matched
        2. Related / Equivalent Alternative Matched (US-13 AC 3)
        3. Missing
        """
        matched = []
        related = []
        missing = []

        for skill in tier_skills:
            normalized = self.normalize_skill(skill)
            clean_lower = normalized.lower()

            if clean_lower in candidate_skills_lower:
                matched.append(normalized)
            else:
                # Check related skill affinity cluster
                alternatives = self.related_skills.get(clean_lower, [])
                found_alt = [alt for alt in alternatives if alt.lower() in candidate_skills_lower]

                if found_alt:
                    related.append(f"{normalized} (Alternative: {found_alt[0]})")
                else:
                    missing.append(normalized)

        return matched, related, missing

    def evaluate_single_opportunity(
        self,
        resume_skills: List[str],
        opportunity: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Evaluates match score and skill tier gaps for one opportunity (US-13)."""
        candidate_skills_lower: Set[str] = {
            self.normalize_skill(s).lower()
            for s in resume_skills
            if isinstance(s, str) and s.strip()
        }

        required = opportunity.get("required_skills", [])
        preferred = opportunity.get("preferred_skills", [])

        req_matched, req_related, req_missing = self.match_skills_against_tier(
            candidate_skills_lower, required
        )

        pref_matched, pref_related, pref_missing = self.match_skills_against_tier(
            candidate_skills_lower, preferred
        )

        # Weighted Scoring Formula: Required skills carry 75% weight, Preferred carry 25% weight
        # Related alternative skills receive 50% credit
        total_req = len(required)
        total_pref = len(preferred)

        req_score = ((len(req_matched) + 0.5 * len(req_related)) / total_req) if total_req > 0 else 1.0
        pref_score = ((len(pref_matched) + 0.5 * len(pref_related)) / total_pref) if total_pref > 0 else 1.0

        if total_req > 0 and total_pref > 0:
            overall_pct = round((req_score * 0.75 + pref_score * 0.25) * 100.0, 1)
        elif total_req > 0:
            overall_pct = round(req_score * 100.0, 1)
        else:
            overall_pct = round(pref_score * 100.0, 1)

        # Assign Relevance Tier
        if overall_pct >= 70.0:
            tier = "High Fit"
        elif overall_pct >= 40.0:
            tier = "Moderate Fit"
        else:
            tier = "Developing Fit"

        return {
            "opportunity_id": str(opportunity.get("id")),
            "title": str(opportunity.get("title")),
            "company": str(opportunity.get("company")),
            "location": str(opportunity.get("location", "Campus Placement")),
            "opportunity_type": str(opportunity.get("opportunity_type", "Internship")),
            "match_percentage": min(100.0, overall_pct),
            "relevance_tier": tier,
            "skills_breakdown": {
                "matched_required": req_matched,
                "related_required": req_related,
                "missing_required": req_missing,
                "matched_preferred": pref_matched,
                "related_preferred": pref_related,
                "missing_preferred": pref_missing,
            }
        }

    def rank_opportunities_for_student(
        self,
        resume_skills: List[str],
        opportunities_pool: List[Dict[str, Any]],
        min_threshold_pct: float = 25.0
    ) -> Dict[str, Any]:
        """
        Ranks placement opportunities in descending order by relevance score (US-12).
        Provides zero-match fallback guidance when no suitable openings exist (US-12 AC 3).
        """
        evaluated_cards = [
            self.evaluate_single_opportunity(resume_skills, opp)
            for opp in opportunities_pool
        ]

        # Sort in descending order of match_percentage
        evaluated_cards.sort(key=lambda card: card["match_percentage"], reverse=True)

        suitable_matches = [
            card for card in evaluated_cards
            if card["match_percentage"] >= min_threshold_pct
        ]

        has_suitable = len(suitable_matches) > 0
        guidance = None

        if not has_suitable:
            guidance = (
                "No placement opportunities currently match your profile above the 25% threshold. "
                "Review the missing required skills across top openings and consider adding coursework "
                "or projects in core languages (e.g., Python, SQL) to broaden your eligibility."
            )

        return {
            "total_opportunities_evaluated": len(opportunities_pool),
            "matched_opportunities_count": len(suitable_matches),
            "has_suitable_matches": has_suitable,
            "guidance_message": guidance,
            "recommended_opportunities": evaluated_cards
        }
