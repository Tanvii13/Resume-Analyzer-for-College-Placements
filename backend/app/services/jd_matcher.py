
import json
import re
from pathlib import Path
from typing import Dict, List, Set, Any

from app.services.skill_extractor import SkillExtractor


TAXONOMY_PATH = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "skills_taxonomy.json"
)


class JDMatcherService:

    def __init__(self, taxonomy_path: str = str(TAXONOMY_PATH)):
        self.skill_extractor = SkillExtractor(
            taxonomy_path=taxonomy_path
        )

        self.aliases = self._load_aliases(taxonomy_path)

        taxonomy = self.skill_extractor.taxonomy

        self.canonical_skills = (
            taxonomy.get("technical_skills", [])
            + taxonomy.get("soft_skills", [])
        )

    def _load_aliases(self, path: str) -> Dict[str, str]:
        """Load skill aliases from the taxonomy."""

        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)

        aliases = data.get("aliases", {})

        return {
            str(alias).strip().lower(): canonical
            for alias, canonical in aliases.items()
        }

    def normalize_skill(self, skill_name: str) -> str:
        """Convert aliases into standard skill names."""

        clean = skill_name.strip()

        if not clean:
            return clean

        normalized = self.aliases.get(clean.lower())

        if normalized:
            return normalized

        for skill in self.canonical_skills:
            if skill.lower() == clean.lower():
                return skill

        return clean

    def extract_jd_skills(self, jd_text: str) -> List[str]:
        """
        Extract technical and soft skills from a job description.
        Also recognizes aliases defined in the taxonomy.
        """

        if not isinstance(jd_text, str):
            raise TypeError("Job description must be a string.")

        if not jd_text.strip():
            return []

        extracted = self.skill_extractor.extract_skills(jd_text)

        all_skills = (
            extracted.get("technical_skills", [])
            + extracted.get("soft_skills", [])
        )

        normalized = {
            self.normalize_skill(skill)
            for skill in all_skills
        }

        # Detect aliases directly from the job description.
        for alias, canonical in self.aliases.items():

            pattern = (
                r"(?<![A-Za-z0-9#+])"
                + re.escape(alias).replace(r"\ ", r"\s+")
                + r"(?![A-Za-z0-9#+])"
            )

            if re.search(pattern, jd_text, re.IGNORECASE):
                normalized.add(canonical)

        return sorted(normalized)

    def match_resume_with_jd(
        self,
        resume_skills: List[str],
        jd_text: str
    ) -> Dict[str, Any]:
        """
        Compare resume skills with job description requirements.
        Calculate matched skills, missing skills and match percentage.
        """

        if not isinstance(resume_skills, list):
            raise TypeError("Resume skills must be a list.")

        jd_skills = self.extract_jd_skills(jd_text)

        normalized_resume_skills: Set[str] = {
            self.normalize_skill(skill)
            for skill in resume_skills
            if isinstance(skill, str) and skill.strip()
        }

        normalized_jd_skills: Set[str] = set(jd_skills)

        # Find matched and missing skills.
        matched_set = (
            normalized_resume_skills.intersection(
                normalized_jd_skills
            )
        )

        missing_set = (
            normalized_jd_skills.difference(
                normalized_resume_skills
            )
        )

        matched_list = sorted(matched_set)
        missing_list = sorted(missing_set)

        # Calculate match percentage.
        total_jd_count = len(normalized_jd_skills)
       if total_jd_count == 0:
    match_percentage = 0.0
else:
    match_percentage = round(
        (len(matched_list) / total_jd_count) * 100.0,
        1
    )
       

        # Generate skill gap recommendations.
        gap_recommendations = []

        if missing_list:

            top_missing = missing_list[:4]

            gap_recommendations.append(
                f"High-priority missing skills for this role: "
                f"{', '.join(top_missing)}. "
                "Highlight relevant coursework, side-projects, "
                "or certifications for these tools if you have exposure."
            )

        else:

            gap_recommendations.append(
                "Excellent alignment: Your resume covers all "
                "required skills detected in this job description."
            )

        return {
            "total_jd_skills_found": total_jd_count,
            "matched_skills_count": len(matched_list),
            "missing_skills_count": len(missing_list),
            "match_percentage": match_percentage,
            "matched_skills": matched_list,
            "missing_skills": missing_list,
            "gap_recommendations": gap_recommendations
        }
