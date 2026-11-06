"""
Symbol-Safe Skill Extraction Engine.

Module E2 (NLP-05) of Sprint 2 NLP pipeline.

Extracts canonical skills and aliases with symbol-safe boundaries (C++, C#, .NET, Node.js),
context-aware disambiguation for ambiguous tokens (C, Go, R), section-based confidence weighting,
and deduplication across resume sections.
"""

from dataclasses import dataclass, field
from functools import lru_cache
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from app.nlp.extractors.base import BaseExtractor
from app.nlp.preprocessing import SegmentedDocument
from app.nlp.sections import (
    SECTION_ACHIEVEMENTS,
    SECTION_CERTIFICATIONS,
    SECTION_EDUCATION,
    SECTION_EXPERIENCE,
    SECTION_EXTRACURRICULAR,
    SECTION_GENERAL_BODY,
    SECTION_INTERNSHIPS,
    SECTION_PERSONAL_INFO,
    SECTION_PROJECTS,
    SECTION_SOFT_SKILLS,
    SECTION_TECHNICAL_SKILLS,
    SectionMap,
)
from app.nlp.taxonomy import (
    get_all_canonical_skills,
    get_canonical_skill,
    get_skill_category,
    load_skill_aliases,
    load_skills_taxonomy,
)

# Section prioritization ordering (highest priority first)
SECTION_PRIORITY_ORDER = [
    SECTION_TECHNICAL_SKILLS,
    SECTION_PROJECTS,
    SECTION_EXPERIENCE,
    SECTION_INTERNSHIPS,
    SECTION_SOFT_SKILLS,
    SECTION_CERTIFICATIONS,
    SECTION_EDUCATION,
    SECTION_ACHIEVEMENTS,
    SECTION_EXTRACURRICULAR,
    SECTION_PERSONAL_INFO,
    SECTION_GENERAL_BODY,
]

# Base extraction confidence scores by section
SECTION_CONFIDENCE_WEIGHTS = {
    SECTION_TECHNICAL_SKILLS: 1.0,
    SECTION_PROJECTS: 0.90,
    SECTION_EXPERIENCE: 0.90,
    SECTION_INTERNSHIPS: 0.90,
    SECTION_SOFT_SKILLS: 0.95,
    SECTION_CERTIFICATIONS: 0.82,
    SECTION_EDUCATION: 0.78,
    SECTION_ACHIEVEMENTS: 0.75,
    SECTION_EXTRACURRICULAR: 0.70,
    SECTION_PERSONAL_INFO: 0.65,
    SECTION_GENERAL_BODY: 0.60,
}

# Technical sections where skills are expected
PRIMARY_TECHNICAL_SECTIONS = {
    SECTION_TECHNICAL_SKILLS,
    SECTION_PROJECTS,
    SECTION_EXPERIENCE,
    SECTION_INTERNSHIPS,
}

# Ambiguous single-letter or short terms requiring context checks
AMBIGUOUS_TERMS = {"C", "R", "Go"}

# Words that falsely precede C or R
NON_TECH_PREV_WORDS = {
    "section", "grade", "vitamin", "room", "schedule", "appendix", "part",
    "level", "class", "group", "category", "block", "floor", "tier",
    "phase", "step", "type", "table", "figure", "fig", "exhibit", "register",
}

# Words following Go that indicate normal English verb usage
GO_REJECT_FOLLOWING = {
    "to", "for", "through", "ahead", "forward", "away", "back", "beyond",
    "off", "up", "down", "around", "about", "over", "into", "from", "as",
    "at", "by", "out",
}


@dataclass
class ExtractedSkill:
    """Represents a single extracted skill with full provenance and confidence."""
    canonical_name: str
    category: str
    matched_text: str
    source_section: Optional[str] = None
    confidence: float = 1.0
    extraction_method: str = "exact"  # 'exact', 'alias', 'symbol_regex', 'contextual'
    occurrences: int = 1
    sections: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert extracted skill into a serializable dictionary."""
        return {
            "canonical_name": self.canonical_name,
            "category": self.category,
            "matched_text": self.matched_text,
            "source_section": self.source_section,
            "confidence": round(self.confidence, 3),
            "extraction_method": self.extraction_method,
            "occurrences": self.occurrences,
            "sections": self.sections,
        }


@dataclass
class SkillProfile:
    """Aggregated skills profile for a candidate."""
    technical_skills: List[ExtractedSkill] = field(default_factory=list)
    soft_skills: List[ExtractedSkill] = field(default_factory=list)
    skills_by_category: Dict[str, List[str]] = field(default_factory=dict)
    total_skills: int = 0
    all_skills: List[ExtractedSkill] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert skill profile into a serializable dictionary."""
        return {
            "total_skills": self.total_skills,
            "technical_skills": [s.to_dict() for s in self.technical_skills],
            "soft_skills": [s.to_dict() for s in self.soft_skills],
            "skills_by_category": self.skills_by_category,
            "all_skills": [s.to_dict() for s in self.all_skills],
        }


@dataclass
class _SkillPattern:
    """Internal pattern entry for skill matching."""
    term: str
    canonical_name: str
    category: str
    is_alias: bool
    is_ambiguous: bool
    pattern: re.Pattern
    match_length: int
    extraction_method: str


def _compile_term_pattern(term: str, case_sensitive: bool = False) -> re.Pattern:
    """
    Compile a symbol-safe regular expression pattern with strict boundaries.

    Handles symbols such as +, #, ., -, /, (, ) while preventing false substring matches.
    """
    if term == "C++":
        escaped = r"C\+\+(?:11|14|17|20|23)?"
    else:
        escaped = re.escape(term)
        escaped = re.sub(r'\\\s+', r'\\s+', escaped)
        escaped = re.sub(r'\\-', r'[- ]', escaped)

    first_char = term[0]
    last_char = term[-1]

    # Left boundary: if starting with alnum, forbid preceding word chars or #/+
    if first_char.isalnum():
        left_bound = r'(?<![A-Za-z0-9_#+])'
    else:
        left_bound = r'(?<![A-Za-z0-9_])'

    # Right boundary: if ending with alnum, forbid following word chars or #/+
    if last_char.isalnum():
        right_bound = r'(?![A-Za-z0-9_#+])'
    else:
        right_bound = r'(?![A-Za-z0-9_#+])'

    flags = 0 if case_sensitive else re.IGNORECASE
    return re.compile(f"{left_bound}{escaped}{right_bound}", flags)


class SkillExtractor(BaseExtractor):
    """
    Symbol-Safe Skill Matching Engine.

    Identifies canonical skills and aliases with high precision, avoiding false
    positives for symbols (C++, C#, .NET, Node.js) and ambiguous single-letter
    words (C, R, Go).
    """

    def __init__(self) -> None:
        """Initialize the skill extractor and compile taxonomy patterns."""
        self.patterns: List[_SkillPattern] = self._build_patterns()

    def _build_patterns(self) -> List[_SkillPattern]:
        """Build and precompile all taxonomy skill and alias patterns."""
        taxonomy = load_skills_taxonomy()
        alias_data = load_skill_aliases()
        aliases = alias_data.get("aliases", {})

        compiled_patterns: List[_SkillPattern] = []
        registered_terms: Set[str] = set()

        # 1. Canonical skills from taxonomy
        for item in taxonomy.get("skills", []):
            name = item["name"]
            cat = item["category"]
            norm_term = name.strip()
            if not norm_term:
                continue

            registered_terms.add(norm_term.lower())
            is_ambig = norm_term in AMBIGUOUS_TERMS
            case_sens = is_ambig

            has_symbol = any(c in norm_term for c in "+#./-&()")
            if is_ambig:
                method = "contextual"
            elif has_symbol:
                method = "symbol_regex"
            else:
                method = "exact"

            pat = _compile_term_pattern(norm_term, case_sensitive=case_sens)
            compiled_patterns.append(
                _SkillPattern(
                    term=norm_term,
                    canonical_name=name,
                    category=cat,
                    is_alias=False,
                    is_ambiguous=is_ambig,
                    pattern=pat,
                    match_length=len(norm_term),
                    extraction_method=method,
                )
            )

            # If name contains parentheses like 'Amazon Web Services (AWS)',
            # register base name 'Amazon Web Services' as a pattern too
            if "(" in norm_term and norm_term.endswith(")"):
                base_name = norm_term.split("(")[0].strip()
                if base_name and base_name.lower() not in registered_terms:
                    registered_terms.add(base_name.lower())
                    compiled_patterns.append(
                        _SkillPattern(
                            term=base_name,
                            canonical_name=name,
                            category=cat,
                            is_alias=True,
                            is_ambiguous=False,
                            pattern=_compile_term_pattern(base_name, case_sensitive=False),
                            match_length=len(base_name),
                            extraction_method="alias",
                        )
                    )

        # 2. Curated aliases
        for alias, canonical_target in aliases.items():
            norm_alias = alias.strip()
            if not norm_alias or norm_alias.lower() in registered_terms:
                continue

            registered_terms.add(norm_alias.lower())
            cat = get_skill_category(canonical_target) or "Software Engineering"
            is_ambig = norm_alias in AMBIGUOUS_TERMS
            case_sens = is_ambig

            if is_ambig:
                method = "contextual"
            else:
                method = "alias"

            pat = _compile_term_pattern(norm_alias, case_sensitive=case_sens)
            compiled_patterns.append(
                _SkillPattern(
                    term=norm_alias,
                    canonical_name=canonical_target,
                    category=cat,
                    is_alias=True,
                    is_ambiguous=is_ambig,
                    pattern=pat,
                    match_length=len(norm_alias),
                    extraction_method=method,
                )
            )

        # Sort patterns: non-ambiguous first, then by match_length descending
        compiled_patterns.sort(
            key=lambda p: (not p.is_ambiguous, p.match_length),
            reverse=True,
        )
        return compiled_patterns

    def extract(
        self,
        sections: SectionMap,
        document: Optional[SegmentedDocument] = None,
    ) -> SkillProfile:
        """
        Extract and deduplicate skills across all classified resume sections.

        Args:
            sections: Classified SectionMap from Module B.
            document: Optional SegmentedDocument from Module A.

        Returns:
            SkillProfile with technical skills, soft skills, and category aggregation.
        """
        if not sections or not sections.sections:
            return SkillProfile()

        raw_extractions_by_canonical: Dict[str, List[ExtractedSkill]] = {}

        # Scan each section in the classified resume
        for section in sections.sections:
            sec_name = section.canonical_name
            sec_text = section.content
            if not sec_text or not sec_text.strip():
                continue

            extracted_in_sec = self._extract_skills_from_section_text(sec_text, sec_name)
            for skill in extracted_in_sec:
                raw_extractions_by_canonical.setdefault(skill.canonical_name, []).append(skill)

        # Merge and deduplicate across sections
        merged_skills: List[ExtractedSkill] = []
        for canonical_name, group in raw_extractions_by_canonical.items():
            merged = self._merge_skill_group(canonical_name, group)
            merged_skills.append(merged)

        return self._build_skill_profile(merged_skills)

    def extract_from_text(
        self,
        text: str,
        section_name: str = SECTION_TECHNICAL_SKILLS,
    ) -> List[ExtractedSkill]:
        """
        Extract skills directly from a raw string within a specific section context.

        Args:
            text: Resume text or section block.
            section_name: Canonical section name context (default: 'technical_skills').

        Returns:
            List of deduplicated ExtractedSkill instances.
        """
        if not text or not text.strip():
            return []

        raw_skills = self._extract_skills_from_section_text(text, section_name)
        grouped: Dict[str, List[ExtractedSkill]] = {}
        for s in raw_skills:
            grouped.setdefault(s.canonical_name, []).append(s)

        merged = [self._merge_skill_group(name, group) for name, group in grouped.items()]
        merged.sort(key=lambda s: (s.category, s.canonical_name))
        return merged

    def _extract_skills_from_section_text(
        self,
        text: str,
        section_name: str,
    ) -> List[ExtractedSkill]:
        """
        Extract all valid skill mentions from a text block with span protection.
        """
        claimed_spans: List[Tuple[int, int]] = []
        found_skills: List[ExtractedSkill] = []

        base_weight = SECTION_CONFIDENCE_WEIGHTS.get(section_name, 0.70)

        for pat_entry in self.patterns:
            for match in pat_entry.pattern.finditer(text):
                start, end = match.span()
                matched_token = match.group(0)

                # Skip if this span overlaps with an already-claimed longer pattern
                if self._overlaps_existing(start, end, claimed_spans):
                    continue

                # Contextual validation for ambiguous tokens
                if pat_entry.is_ambiguous:
                    if not self._is_valid_ambiguous_match(
                        text, start, end, section_name, pat_entry.term, matched_token
                    ):
                        continue

                # Validate short aliases in non-technical sections
                if pat_entry.is_alias and len(pat_entry.term) <= 2:
                    if not self._is_valid_short_alias(
                        pat_entry.term, text, start, end, section_name
                    ):
                        continue

                # Claim this character span
                claimed_spans.append((start, end))

                # Compute confidence score
                confidence = self._compute_confidence(
                    base_weight=base_weight,
                    category=pat_entry.category,
                    section_name=section_name,
                    extraction_method=pat_entry.extraction_method,
                )

                found_skills.append(
                    ExtractedSkill(
                        canonical_name=pat_entry.canonical_name,
                        category=pat_entry.category,
                        matched_text=matched_token,
                        source_section=section_name,
                        confidence=confidence,
                        extraction_method=pat_entry.extraction_method,
                        occurrences=1,
                        sections=[section_name],
                    )
                )

        return found_skills

    def _overlaps_existing(self, start: int, end: int, spans: List[Tuple[int, int]]) -> bool:
        """Check if an interval [start, end] overlaps with any already claimed interval."""
        for s, e in spans:
            if max(start, s) < min(end, e):
                return True
        return False

    def _compute_confidence(
        self,
        base_weight: float,
        category: str,
        section_name: str,
        extraction_method: str,
    ) -> float:
        """Compute contextual confidence score for an extracted skill."""
        conf = base_weight
        if extraction_method == "alias":
            conf *= 0.96
        elif extraction_method == "contextual":
            conf *= 0.94

        # Soft skills outside dedicated soft skills section get scaled confidence
        if category == "Soft Skills" and section_name != SECTION_SOFT_SKILLS:
            conf = min(conf, 0.85)

        return min(max(conf, 0.50), 1.0)

    def _merge_skill_group(
        self,
        canonical_name: str,
        skills: List[ExtractedSkill],
    ) -> ExtractedSkill:
        """Merge multiple mentions of the same canonical skill across sections."""
        if not skills:
            cat = get_skill_category(canonical_name) or "Software Engineering"
            return ExtractedSkill(canonical_name=canonical_name, category=cat, matched_text=canonical_name)

        # Aggregate total occurrences
        total_occurrences = sum(s.occurrences for s in skills)

        # Pick highest confidence
        best_skill = max(skills, key=lambda s: s.confidence)

        # Order sections by priority
        seen_sections: Set[str] = set()
        all_sections: List[str] = []
        for s in skills:
            for sec in s.sections:
                if sec and sec not in seen_sections:
                    seen_sections.add(sec)
                    all_sections.append(sec)

        # Sort sections according to SECTION_PRIORITY_ORDER
        all_sections.sort(
            key=lambda sec: SECTION_PRIORITY_ORDER.index(sec)
            if sec in SECTION_PRIORITY_ORDER
            else 999
        )
        primary_section = all_sections[0] if all_sections else best_skill.source_section

        return ExtractedSkill(
            canonical_name=canonical_name,
            category=best_skill.category,
            matched_text=best_skill.matched_text,
            source_section=primary_section,
            confidence=best_skill.confidence,
            extraction_method=best_skill.extraction_method,
            occurrences=total_occurrences,
            sections=all_sections,
        )

    def _build_skill_profile(self, skills: List[ExtractedSkill]) -> SkillProfile:
        """Partition extracted skills into technical, soft, and category maps."""
        technical: List[ExtractedSkill] = []
        soft: List[ExtractedSkill] = []
        by_category: Dict[str, List[str]] = {}

        for skill in skills:
            if skill.category == "Soft Skills":
                soft.append(skill)
            else:
                technical.append(skill)

            by_category.setdefault(skill.category, []).append(skill.canonical_name)

        # Sort alphabetically within each category
        for cat in by_category:
            by_category[cat] = sorted(list(set(by_category[cat])))

        technical.sort(key=lambda s: (s.category, s.canonical_name))
        soft.sort(key=lambda s: s.canonical_name)

        return SkillProfile(
            technical_skills=technical,
            soft_skills=soft,
            skills_by_category=by_category,
            total_skills=len(skills),
            all_skills=skills,
        )

    # -------------------------------------------------------------------------
    # Context-Aware Disambiguation Rules for C, Go, R, and Short Tokens
    # -------------------------------------------------------------------------

    def _is_valid_ambiguous_match(
        self,
        text: str,
        start: int,
        end: int,
        section_name: str,
        term: str,
        matched_token: str,
    ) -> bool:
        """Route ambiguous tokens to their respective contextual validators."""
        if term == "C":
            return self._is_valid_c_match(text, start, end, section_name)
        elif term == "Go":
            return self._is_valid_go_match(text, start, end, section_name, matched_token)
        elif term == "R":
            return self._is_valid_r_match(text, start, end, section_name)
        return True

    def _is_valid_c_match(self, text: str, start: int, end: int, section_name: str) -> bool:
        """Validate whether a standalone 'C' refers to the C programming language."""
        if text[start:end] != "C":
            return False

        before_text = text[:start].rstrip()
        after_text = text[end:].lstrip()

        # Reject bullets or initials like 'C.', 'C)', 'C-'
        if after_text.startswith((".", ")", "-", "suite", "Suite", "level", "Level")):
            return False

        # Reject common non-tech preceding qualifiers (Grade C, Section C, Vitamin C)
        before_words = before_text.split()
        if before_words:
            last_word = re.sub(r'[^a-zA-Z]', '', before_words[-1]).lower()
            if last_word in NON_TECH_PREV_WORDS:
                return False

        # Reject common non-tech following words (C grade, C section)
        after_words = after_text.split()
        if after_words:
            first_word = re.sub(r'[^a-zA-Z]', '', after_words[0]).lower()
            if first_word in {"grade", "level", "suite", "class", "section", "part", "deficiency"}:
                return False

        # In technical skills section, standalone C is valid
        if section_name in {SECTION_TECHNICAL_SKILLS, SECTION_SOFT_SKILLS}:
            return True

        # In projects, experience, or other sections, require positive programming context
        window = text[max(0, start - 50):min(len(text), end + 50)].lower()
        positive_indicators = [
            "c++", "c#", "programming", "language", "embedded", "ansi", "linux",
            "python", "java", "assembly", "written in", "developed in", "coded in",
            "compiler", "posix", "firmware", "device drivers", "rtos", "kernel",
        ]
        return any(ind in window for ind in positive_indicators)

    def _is_valid_go_match(
        self,
        text: str,
        start: int,
        end: int,
        section_name: str,
        matched_token: str,
    ) -> bool:
        """Validate whether 'Go' refers to the Go programming language."""
        if matched_token.lower() == "golang":
            return True

        # Lowercase 'go' in normal prose is never matched
        if matched_token == "go":
            return False

        before_text = text[:start].rstrip()
        after_text = text[end:].lstrip()

        # Reject common English verb following prepositions (Go to, Go for, Go through)
        after_words = after_text.split()
        if after_words:
            first_after = re.sub(r'[^a-zA-Z]', '', after_words[0]).lower()
            if first_after in GO_REJECT_FOLLOWING:
                return False

        if section_name in PRIMARY_TECHNICAL_SECTIONS:
            return True

        # In other sections, check for positive programming indicators
        before_words = before_text.split()
        last_before = re.sub(r'[^a-zA-Z]', '', before_words[-1]).lower() if before_words else ""
        first_after = re.sub(r'[^a-zA-Z]', '', after_words[0]).lower() if after_words else ""

        positive_before = {"in", "with", "using", "backend", "services", "written", "developed", "coded", "built"}
        positive_after = {"programming", "language", "developer", "code", "microservices", "backend", "service", "engineer", "api"}

        if last_before in positive_before or first_after in positive_after:
            return True

        # Adjacent to other technologies in comma-separated list
        window = text[max(0, start - 45):min(len(text), end + 45)].lower()
        tech_terms = ["python", "docker", "kubernetes", "rust", "java", "c++", "grpc", "redis", "postgres", "gin", "microservices"]
        return any(t in window for t in tech_terms)

    def _is_valid_r_match(self, text: str, start: int, end: int, section_name: str) -> bool:
        """Validate whether standalone 'R' refers to the R programming language."""
        if text[start:end] != "R":
            return False

        before_text = text[:start].rstrip()
        after_text = text[end:].lstrip()

        # Reject R., R), R&D, R-
        if after_text.startswith((".", ")", "&", "-", "/d", "/D")):
            return False
        if before_text.endswith("&"):
            return False

        before_words = before_text.split()
        if before_words:
            last_word = re.sub(r'[^a-zA-Z]', '', before_words[-1]).lower()
            if last_word in NON_TECH_PREV_WORDS:
                return False

        if section_name in PRIMARY_TECHNICAL_SECTIONS:
            return True

        # In non-technical sections, require data science or programming context
        window = text[max(0, start - 45):min(len(text), end + 45)].lower()
        ds_indicators = [
            "python", "sql", "tableau", "pandas", "statistics", "modeling",
            "data science", "programming", "language", "script", "analysis",
            "packages", "rstudio", "ggplot", "bioconductor",
        ]
        return any(ind in window for ind in ds_indicators)

    def _is_valid_short_alias(
        self,
        alias: str,
        text: str,
        start: int,
        end: int,
        section_name: str,
    ) -> bool:
        """Guard against false positives for two-character abbreviations in non-technical text."""
        norm_alias = alias.lower()

        # 'bs' in education or personal info is Bachelor of Science, not Bootstrap
        if norm_alias == "bs" and section_name in {SECTION_EDUCATION, SECTION_PERSONAL_INFO}:
            return False

        # 'cv' in personal info is Curriculum Vitae, not Computer Vision
        if norm_alias == "cv" and section_name in {SECTION_PERSONAL_INFO, SECTION_EDUCATION}:
            return False

        # 'sh' in non-technical sections is likely prose
        if norm_alias == "sh" and section_name not in PRIMARY_TECHNICAL_SECTIONS:
            return False

        # 'bi' in non-technical sections is likely prose
        if norm_alias == "bi" and section_name not in PRIMARY_TECHNICAL_SECTIONS:
            return False

        # 'es' in non-technical sections is likely Spanish or typo
        if norm_alias == "es" and section_name not in PRIMARY_TECHNICAL_SECTIONS:
            return False

        return True


__all__ = [
    "ExtractedSkill",
    "SkillProfile",
    "SkillExtractor",
    "SECTION_PRIORITY_ORDER",
    "SECTION_CONFIDENCE_WEIGHTS",
    "PRIMARY_TECHNICAL_SECTIONS",
]
