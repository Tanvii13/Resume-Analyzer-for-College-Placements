"""
Tests for Sprint 2 - Module E1: Curated Skill Taxonomy & Aliases (NLP-04).

Validates:
- Skills taxonomy size (>= 500 skills across 15 categories)
- Zero duplicates
- Inclusion of all 25 PostgreSQL seed skills
- Alias mapping consistency (0 orphaned aliases)
- Key alias resolutions (js, ts, k8s, postgres, py, ml, dl, node, etc.)
- Degree taxonomy structure and resolution (B.Tech, M.Tech, Ph.D., 12th, 10th)
- Taxonomy helper functions and in-memory caching
"""

import json
from pathlib import Path
import pytest

from app.nlp.taxonomy import (
    DEGREES_FILE,
    SKILL_ALIASES_FILE,
    SKILLS_TAXONOMY_FILE,
    TAXONOMY_DIR,
    get_all_canonical_skills,
    get_all_categories,
    get_all_degree_levels,
    get_canonical_skill,
    get_skill_category,
    get_skills_by_category,
    is_valid_skill,
    load_degrees,
    load_skill_aliases,
    load_skills_taxonomy,
    resolve_degree,
)

# Required 15 categories as specified in Module E1 requirements
EXPECTED_CATEGORIES = [
    "Programming Languages",
    "Frontend Development",
    "Backend Development",
    "Databases",
    "Cloud Computing",
    "DevOps",
    "Machine Learning",
    "Artificial Intelligence",
    "Data Science",
    "Cybersecurity",
    "Software Engineering",
    "Testing & QA",
    "Tools & Frameworks",
    "Operating Systems",
    "Soft Skills",
]

# The 25 seed skills from database/schema.sql
DB_SEED_SKILLS = [
    "C++",
    "C",
    "Python",
    "Java",
    "JavaScript",
    "TypeScript",
    "SQL",
    "PostgreSQL",
    "MySQL",
    "MongoDB",
    "DBMS",
    "Data Structures",
    "Algorithms",
    "Git",
    "GitHub",
    "Linux",
    "Docker",
    "React",
    "Node.js",
    "FastAPI",
    "Spring Boot",
    "Machine Learning",
    "Deep Learning",
    "Computer Networks",
    "Operating Systems",
]


class TestSkillsTaxonomy:
    """Test suite for skills_taxonomy.json and related taxonomy functions."""

    def test_taxonomy_files_exist(self):
        """Verify that all required taxonomy JSON files exist."""
        assert SKILLS_TAXONOMY_FILE.is_file(), "skills_taxonomy.json must exist"
        assert SKILL_ALIASES_FILE.is_file(), "skill_aliases.json must exist"
        assert DEGREES_FILE.is_file(), "degrees.json must exist"

    def test_skills_count_meets_minimum_requirement(self):
        """Taxonomy must contain at least 500 distinct skills."""
        data = load_skills_taxonomy()
        total = data.get("total_skills", 0)
        skills_list = data.get("skills", [])
        assert total >= 500, f"Expected >= 500 skills, found {total}"
        assert len(skills_list) >= 500, f"Expected >= 500 items in skills list, found {len(skills_list)}"

    def test_taxonomy_version_present(self):
        """Taxonomy file must contain version metadata."""
        data = load_skills_taxonomy()
        assert "version" in data
        assert isinstance(data["version"], str)

    def test_all_15_categories_present_and_non_empty(self):
        """Taxonomy must contain all 15 required categories with at least one skill each."""
        data = load_skills_taxonomy()
        categories = data.get("categories", [])
        
        # Check all 15 expected categories are present
        for cat in EXPECTED_CATEGORIES:
            assert cat in categories, f"Missing category: {cat}"

        # Check each category has skills
        skills_by_cat = {}
        for s in data.get("skills", []):
            skills_by_cat.setdefault(s["category"], []).append(s["name"])

        for cat in EXPECTED_CATEGORIES:
            assert cat in skills_by_cat, f"No skills found in category: {cat}"
            assert len(skills_by_cat[cat]) >= 10, f"Category '{cat}' should have at least 10 skills"

    def test_no_duplicate_canonical_skills(self):
        """All skill names must be unique (case-insensitively)."""
        data = load_skills_taxonomy()
        seen = {}
        duplicates = []
        for s in data.get("skills", []):
            lower_name = s["name"].strip().lower()
            if lower_name in seen:
                duplicates.append((s["name"], seen[lower_name]))
            else:
                seen[lower_name] = s["name"]

        assert not duplicates, f"Found duplicate canonical skills: {duplicates}"

    def test_all_25_db_seed_skills_present(self):
        """Ensure all 25 skills from database/schema.sql are present in the taxonomy."""
        all_skills = set(s.strip().lower() for s in get_all_canonical_skills())
        missing = []
        for seed_skill in DB_SEED_SKILLS:
            canonical = get_canonical_skill(seed_skill)
            if not canonical or canonical.strip().lower() not in all_skills:
                missing.append(seed_skill)

        assert not missing, f"Missing PostgreSQL seed skills: {missing}"


class TestSkillAliases:
    """Test suite for skill_aliases.json and alias normalization."""

    def test_aliases_file_valid_and_non_empty(self):
        """Aliases file must load and contain significant alias count (>= 150)."""
        data = load_skill_aliases()
        aliases = data.get("aliases", {})
        assert len(aliases) >= 150, f"Expected >= 150 aliases, found {len(aliases)}"

    def test_zero_orphaned_aliases(self):
        """Every alias target must exist in the canonical skills taxonomy."""
        all_skills = set(s.strip().lower() for s in get_all_canonical_skills())
        alias_data = load_skill_aliases()
        aliases = alias_data.get("aliases", {})
        
        orphaned = {}
        for alias, target in aliases.items():
            if target.strip().lower() not in all_skills:
                orphaned[alias] = target

        assert not orphaned, f"Found orphaned aliases: {orphaned}"

    @pytest.mark.parametrize(
        "alias,expected_canonical",
        [
            ("js", "JavaScript"),
            ("JS", "JavaScript"),
            ("javascript", "JavaScript"),
            ("ts", "TypeScript"),
            ("k8s", "Kubernetes"),
            ("postgres", "PostgreSQL"),
            ("postgresql", "PostgreSQL"),
            ("py", "Python"),
            ("python3", "Python"),
            ("ml", "Machine Learning"),
            ("dl", "Deep Learning"),
            ("node", "Node.js"),
            ("nodejs", "Node.js"),
            ("node.js", "Node.js"),
            ("reactjs", "React"),
            ("react.js", "React"),
            ("vue", "Vue.js"),
            ("vuejs", "Vue.js"),
            ("cpp", "C++"),
            ("cplusplus", "C++"),
            ("c#", "C#"),
            ("csharp", "C#"),
            ("golang", "Go"),
            ("qa", "Quality Assurance"),
            ("dsa", "Data Structures"),
            ("oops", "Object-Oriented Programming (OOP)"),
            ("rhel", "Red Hat Enterprise Linux (RHEL)"),
        ],
    )
    def test_key_alias_resolutions(self, alias, expected_canonical):
        """Verify standard aliases resolve to their expected canonical names."""
        resolved = get_canonical_skill(alias)
        assert resolved == expected_canonical, f"Alias '{alias}' resolved to '{resolved}', expected '{expected_canonical}'"


class TestDegreesTaxonomy:
    """Test suite for degrees.json and degree resolution."""

    def test_degrees_levels_present(self):
        """Degree taxonomy must contain standard academic levels."""
        levels = get_all_degree_levels()
        expected = ["bachelors", "masters", "doctorate", "diploma", "secondary"]
        for exp in expected:
            assert exp in levels, f"Missing degree level: {exp}"

    @pytest.mark.parametrize(
        "input_degree,expected_name,expected_level",
        [
            ("B.Tech", "B.Tech", "bachelors"),
            ("btech", "B.Tech", "bachelors"),
            ("b. tech", "B.Tech", "bachelors"),
            ("Bachelor of Technology", "B.Tech", "bachelors"),
            ("B.E.", "B.E.", "bachelors"),
            ("BCA", "BCA", "bachelors"),
            ("bca", "BCA", "bachelors"),
            ("B.Sc", "B.Sc", "bachelors"),
            ("M.Tech", "M.Tech", "masters"),
            ("mtech", "M.Tech", "masters"),
            ("MCA", "MCA", "masters"),
            ("M.S.", "M.S.", "masters"),
            ("Ph.D.", "Ph.D.", "doctorate"),
            ("phd", "Ph.D.", "doctorate"),
            ("Doctor of Philosophy", "Ph.D.", "doctorate"),
            ("Diploma in Computer Engineering", "Diploma", "diploma"),
            ("12th", "12th (HSC)", "secondary"),
            ("hsc", "12th (HSC)", "secondary"),
            ("10th", "10th (SSC)", "secondary"),
            ("ssc", "10th (SSC)", "secondary"),
        ],
    )
    def test_degree_resolution(self, input_degree, expected_name, expected_level):
        """Verify degree strings resolve accurately to canonical names and levels."""
        res = resolve_degree(input_degree)
        assert res is not None, f"Failed to resolve degree: '{input_degree}'"
        assert res["name"] == expected_name, f"Expected name '{expected_name}', got '{res['name']}'"
        assert res["level"] == expected_level, f"Expected level '{expected_level}', got '{res['level']}'"


class TestTaxonomyHelperFunctions:
    """Test helper functions in app.nlp.taxonomy."""

    def test_is_valid_skill(self):
        """Test skill validity checks."""
        assert is_valid_skill("Python") is True
        assert is_valid_skill("python") is True
        assert is_valid_skill("js") is True
        assert is_valid_skill("NonExistentSuperSkillXYZ123") is False
        assert is_valid_skill("") is False

    def test_get_skill_category(self):
        """Test retrieving category for skills and aliases."""
        assert get_skill_category("Python") == "Programming Languages"
        assert get_skill_category("py") == "Programming Languages"
        assert get_skill_category("React") == "Frontend Development"
        assert get_skill_category("reactjs") == "Frontend Development"
        assert get_skill_category("PostgreSQL") == "Databases"
        assert get_skill_category("postgres") == "Databases"
        assert get_skill_category("Docker") == "DevOps"
        assert get_skill_category("AWS") == "Cloud Computing"
        assert get_skill_category("Machine Learning") == "Machine Learning"
        assert get_skill_category("Problem Solving") == "Soft Skills"
        assert get_skill_category("unknown_xyz") is None

    def test_get_skills_by_category(self):
        """Test listing skills within a specific category."""
        cloud_skills = get_skills_by_category("Cloud Computing")
        assert len(cloud_skills) >= 15
        assert "Amazon Web Services (AWS)" in cloud_skills
        assert "Google Cloud Platform (GCP)" in cloud_skills
        assert "Microsoft Azure" in cloud_skills

        # Case-insensitive category lookup
        cloud_skills_lower = get_skills_by_category("cloud computing")
        assert len(cloud_skills_lower) == len(cloud_skills)

        # Invalid category returns empty list
        assert get_skills_by_category("NonExistentCategory") == []
        assert get_skills_by_category("") == []

    def test_get_all_canonical_skills(self):
        """Test listing all canonical skills."""
        all_skills = get_all_canonical_skills()
        assert len(all_skills) >= 500
        assert "Python" in all_skills
        assert "C++" in all_skills

    def test_get_all_categories(self):
        """Test listing all categories."""
        cats = get_all_categories()
        assert len(cats) == 15
        for exp in EXPECTED_CATEGORIES:
            assert exp in cats

    def test_resolve_degree_invalid(self):
        """Test resolving invalid degree inputs."""
        assert resolve_degree("NonExistentDegree12345") is None
        assert resolve_degree("") is None
        assert resolve_degree(None) is None

    def test_get_canonical_skill_invalid(self):
        """Test canonical skill lookup with invalid inputs."""
        assert get_canonical_skill("") is None
        assert get_canonical_skill(None) is None
        assert get_canonical_skill("   ") is None
