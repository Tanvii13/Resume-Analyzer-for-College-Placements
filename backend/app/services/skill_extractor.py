
import json
import re
from pathlib import Path
from typing import Dict, List, Optional


class SkillExtractor:
    """
    Extract technical and soft skills from resume text
    using the project's skills taxonomy.
    """

    def __init__(self, taxonomy_path: Optional[str] = None):

        if taxonomy_path is None:
            taxonomy_path = (
                Path(__file__).resolve().parent.parent
                / "data"
                / "skills_taxonomy.json"
            )

        self.taxonomy = self._load_taxonomy(taxonomy_path)

    def _load_taxonomy(self, path) -> dict:
        """Load skills from the JSON taxonomy."""

        with open(path, "r", encoding="utf-8") as file:
            taxonomy = json.load(file)

        if not isinstance(taxonomy, dict):
            raise ValueError("Invalid skills taxonomy format.")

        return taxonomy

    def _is_skill_present(self, skill: str, text: str) -> bool:
        """Match complete skill names."""

        escaped_skill = re.escape(skill)
        escaped_skill = escaped_skill.replace(r"\ ", r"\s+")

        pattern = (
            r"(?<![A-Za-z0-9#+])"
            + escaped_skill
            + r"(?![A-Za-z0-9#+])"
        )

        return bool(
            re.search(pattern, text, re.IGNORECASE)
        )

    def _get_technical_skills(self) -> List[str]:
        """Get technical skills from the taxonomy."""

        technical = self.taxonomy.get("technical_skills", [])

        if isinstance(technical, list):
            return technical

        if isinstance(technical, dict):
            skills = []

            for skill_list in technical.values():
                if isinstance(skill_list, list):
                    skills.extend(skill_list)

            return skills

        return []

    def extract_skills(self, text: str) -> Dict[str, List[str]]:
        """Extract technical and soft skills from resume text."""

        if not isinstance(text, str):
            raise TypeError("Resume text must be a string.")

        if not text.strip():
            return {
                "technical_skills": [],
                "soft_skills": [],
                "total_count": 0
            }

        technical_skills = self._get_technical_skills()
        soft_skills = self.taxonomy.get("soft_skills", [])

        found_technical = []
        found_soft = []

        for skill in technical_skills:
            if self._is_skill_present(skill, text):
                found_technical.append(skill)

        for skill in soft_skills:
            if self._is_skill_present(skill, text):
                found_soft.append(skill)

        found_technical = list(dict.fromkeys(found_technical))
        found_soft = list(dict.fromkeys(found_soft))

        return {
            "technical_skills": found_technical,
            "soft_skills": found_soft,
            "total_count": len(found_technical) + len(found_soft)
        }
