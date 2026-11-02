"""
Curated Skill Taxonomy and Knowledge Base for Resume Analyzer.

Provides centralized, curated skills taxonomy, alias normalization,
and degree taxonomy loaders with in-memory caching.
"""

from functools import lru_cache
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

TAXONOMY_DIR = Path(__file__).resolve().parent
SKILLS_TAXONOMY_FILE = TAXONOMY_DIR / "skills_taxonomy.json"
SKILL_ALIASES_FILE = TAXONOMY_DIR / "skill_aliases.json"
DEGREES_FILE = TAXONOMY_DIR / "degrees.json"


@lru_cache(maxsize=1)
def load_skills_taxonomy() -> Dict[str, Any]:
    """
    Load the curated skills taxonomy JSON file.

    Returns:
        Dict with keys: 'version', 'total_skills', 'categories', 'skills'.
    """
    with open(SKILLS_TAXONOMY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def load_skill_aliases() -> Dict[str, Any]:
    """
    Load the skill aliases JSON file.

    Returns:
        Dict with keys: 'version', 'total_aliases', 'aliases'.
    """
    with open(SKILL_ALIASES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def load_degrees() -> Dict[str, Any]:
    """
    Load the academic degrees taxonomy JSON file.

    Returns:
        Dict with keys: 'version', 'levels'.
    """
    with open(DEGREES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def _build_canonical_skill_map() -> Dict[str, str]:
    """
    Build a case-insensitive map of canonical skill names: lower_name -> Canonical Name.
    """
    taxonomy = load_skills_taxonomy()
    lookup: Dict[str, str] = {}
    for item in taxonomy.get("skills", []):
        name = item["name"]
        lookup[name.strip().lower()] = name
    return lookup


@lru_cache(maxsize=1)
def _build_full_skill_resolution_map() -> Dict[str, str]:
    """
    Build a comprehensive resolution map covering both canonical names and aliases:
    lower(name_or_alias) -> Canonical Name.
    """
    canonical_map = _build_canonical_skill_map()
    resolution_map = dict(canonical_map)

    alias_data = load_skill_aliases()
    aliases = alias_data.get("aliases", {})
    for alias, canonical_target in aliases.items():
        norm_alias = alias.strip().lower()
        # Resolve target through canonical_map to preserve canonical casing
        canonical_target_norm = canonical_target.strip().lower()
        resolved_name = canonical_map.get(canonical_target_norm, canonical_target)
        resolution_map[norm_alias] = resolved_name

    return resolution_map


@lru_cache(maxsize=1)
def _build_skill_category_map() -> Dict[str, str]:
    """
    Build a mapping from canonical skill name -> category.
    """
    taxonomy = load_skills_taxonomy()
    cat_map: Dict[str, str] = {}
    for item in taxonomy.get("skills", []):
        cat_map[item["name"]] = item["category"]
    return cat_map


def get_canonical_skill(name_or_alias: str) -> Optional[str]:
    """
    Resolve a skill name or alias (case-insensitive) to its canonical skill name.

    Examples:
        get_canonical_skill("js") -> "JavaScript"
        get_canonical_skill("k8s") -> "Kubernetes"
        get_canonical_skill("python") -> "Python"
        get_canonical_skill("NonExistentSkill") -> None

    Args:
        name_or_alias: The skill string or alias to resolve.

    Returns:
        The canonical skill name, or None if not recognized.
    """
    if not name_or_alias or not isinstance(name_or_alias, str):
        return None
    cleaned = name_or_alias.strip().lower()
    resolution_map = _build_full_skill_resolution_map()
    return resolution_map.get(cleaned)


def is_valid_skill(name_or_alias: str) -> bool:
    """
    Check if a skill name or alias exists in the taxonomy.
    """
    return get_canonical_skill(name_or_alias) is not None


def get_skill_category(skill_name: str) -> Optional[str]:
    """
    Get the category for a skill. If given an alias, resolves to canonical first.

    Args:
        skill_name: Canonical skill name or alias.

    Returns:
        Category string (e.g., 'Programming Languages'), or None if not found.
    """
    canonical = get_canonical_skill(skill_name)
    if not canonical:
        return None
    category_map = _build_skill_category_map()
    return category_map.get(canonical)


@lru_cache(maxsize=1)
def get_all_canonical_skills() -> List[str]:
    """
    Return a list of all canonical skill names in the taxonomy.
    """
    taxonomy = load_skills_taxonomy()
    return [item["name"] for item in taxonomy.get("skills", [])]


@lru_cache(maxsize=1)
def get_all_categories() -> List[str]:
    """
    Return a list of all skill category names in the taxonomy.
    """
    taxonomy = load_skills_taxonomy()
    return list(taxonomy.get("categories", []))


def get_skills_by_category(category: str) -> List[str]:
    """
    Return all canonical skill names belonging to the specified category.

    Args:
        category: The category name (case-insensitive matching).

    Returns:
        List of canonical skill names in that category.
    """
    if not category or not isinstance(category, str):
        return []
    cat_lower = category.strip().lower()
    taxonomy = load_skills_taxonomy()
    return [
        item["name"]
        for item in taxonomy.get("skills", [])
        if item.get("category", "").strip().lower() == cat_lower
    ]


@lru_cache(maxsize=1)
def _build_degree_resolution_map() -> Dict[str, Dict[str, Any]]:
    """
    Build a resolution map from degree alias/name (lowercase) to degree metadata dict:
    {
        "name": "B.Tech",
        "full_name": "Bachelor of Technology",
        "level": "bachelors",
        "level_name": "Bachelor's Degree",
        "field_hints": [...]
    }
    """
    data = load_degrees()
    resolution: Dict[str, Dict[str, Any]] = {}
    levels = data.get("levels", {})

    for level_key, level_info in levels.items():
        level_name = level_info.get("canonical_name", level_key)
        for degree in level_info.get("degrees", []):
            deg_record = {
                "name": degree.get("name"),
                "full_name": degree.get("full_name"),
                "level": level_key,
                "level_name": level_name,
                "field_hints": degree.get("field_hints", []),
            }
            # Map canonical name
            if degree.get("name"):
                resolution[degree["name"].strip().lower()] = deg_record
            # Map full name
            if degree.get("full_name"):
                resolution[degree["full_name"].strip().lower()] = deg_record
            # Map aliases
            for alias in degree.get("aliases", []):
                resolution[alias.strip().lower()] = deg_record

    return resolution


def resolve_degree(degree_str: str) -> Optional[Dict[str, Any]]:
    """
    Resolve a degree string or alias to its degree metadata.

    Examples:
        resolve_degree("btech") -> {"name": "B.Tech", "full_name": "Bachelor of Technology", ...}
        resolve_degree("M.S.") -> {"name": "M.S.", "full_name": "Master of Science", ...}
        resolve_degree("12th") -> {"name": "Class XII", "full_name": "Higher Secondary Certificate (HSC)", ...}

    Args:
        degree_str: Raw degree string.

    Returns:
        Dict with degree metadata or None if unmapped.
    """
    if not degree_str or not isinstance(degree_str, str):
        return None
    cleaned = degree_str.strip().lower()
    degree_map = _build_degree_resolution_map()
    return degree_map.get(cleaned)


def get_all_degree_levels() -> List[str]:
    """
    Return all academic degree levels present in the degree taxonomy.
    """
    data = load_degrees()
    return list(data.get("levels", {}).keys())


__all__ = [
    "TAXONOMY_DIR",
    "SKILLS_TAXONOMY_FILE",
    "SKILL_ALIASES_FILE",
    "DEGREES_FILE",
    "load_skills_taxonomy",
    "load_skill_aliases",
    "load_degrees",
    "get_canonical_skill",
    "is_valid_skill",
    "get_skill_category",
    "get_all_canonical_skills",
    "get_all_categories",
    "get_skills_by_category",
    "resolve_degree",
    "get_all_degree_levels",
]
