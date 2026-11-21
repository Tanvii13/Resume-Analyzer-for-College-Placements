"""
Skill Normalization and Controlled Equivalence Engine.

Sprint 4 Module B (NLP-JobMatching).

Provides deterministic skill normalization, canonicalization, alias resolution,
symbol-safe token parsing, and a controlled equivalence / relatedness / prerequisite
reasoning engine for both CandidateProfile skills and Job Description requirements.
"""

import re
from typing import Any

from app.nlp.job_matching.schemas import JobSkillRequirement
from app.nlp.job_matching.skill_normalization_schemas import (
    EquivalenceEvaluation,
    EquivalenceRule,
    NormalizedSkill,
    SkillMatchMethod,
    SkillRelationshipType,
    SkillSetComparison,
)
from app.nlp.preprocessing import split_bullet
from app.nlp.schemas import SkillItem
from app.nlp.taxonomy import (
    _build_canonical_skill_map,
    get_all_canonical_skills,
    get_skill_category,
    load_skill_aliases,
    load_skill_equivalences,
)

ENGINE_VERSION = "1.0.0"

# Curated set of short abbreviations and acronyms
KNOWN_ABBREVIATIONS: set[str] = {
    "js", "ts", "py", "cpp", "c#", "golang", "k8s", "k8", "kube",
    "aws", "gcp", "azure", "ml", "dl", "ai", "genai", "nlp", "cv",
    "llm", "llms", "tf", "svm", "svms", "cnn", "cnns", "rnn", "rnns",
    "lstm", "gan", "gans", "pca", "automl", "elk", "lxc", "gke",
    "ec2", "s3", "gql", "psql", "bs", "mui", "d3", "rwd", "wasm",
    "ror", "asm", "vba", "rb", "sh", "pwsh", "drf", "ci/cd", "cicd",
    "ci cd", "rest", "db", "rdbms", "nosql", "ui", "ux", "ui/ux",
}

# Ambiguous single-letter or short terms requiring context protection
AMBIGUOUS_SHORT_NAMES: set[str] = {"c", "r", "go"}

# Words falsely preceding ambiguous single-letter tokens (e.g. "Vitamin C", "Grade C")
NON_TECH_PREFIX_WORDS: set[str] = {
    "section", "grade", "vitamin", "room", "schedule", "appendix", "part",
    "level", "class", "group", "category", "block", "floor", "tier",
    "phase", "step", "type", "table", "figure", "fig", "exhibit", "register",
}

# Words following Go that indicate normal English verb usage ("Go to", "Go ahead")
NON_TECH_POST_WORDS: set[str] = {
    "to", "for", "through", "ahead", "forward", "away", "back", "beyond",
    "off", "up", "down", "around", "about", "over", "into", "from", "as",
    "at", "by", "out",
}

# Leading bullet / numbering patterns
_LEADING_BULLET_RE = re.compile(r"^[\s\-\*\•\d\.\)\(\]]+\s*")

# Surrounding quotes / brackets
_SURROUNDING_PUNCT_RE = re.compile(r"^[\(\[\{\"\']+|[\)\]\}\"\']+$")

# Trailing punctuation (strip only if not protected dot in .NET or .js)
_TRAILING_PUNCT_RE = re.compile(r"[\s,;:!]+$")


class SkillNormalizer:
    """
    Deterministic Normalizer for Technical & Soft Skills.

    Transforms raw skill strings, CandidateProfile SkillItem instances,
    or JobSkillRequirement objects into canonicalized NormalizedSkill representations.
    Preserves raw mentions, distinguishes exact matches from aliases/abbreviations,
    and protects technical symbols (C++, C#, .NET, Node.js, CI/CD).
    """

    def __init__(self) -> None:
        self._canonical_skills: set[str] = set(get_all_canonical_skills())
        self._canonical_lower_map: dict[str, str] = _build_canonical_skill_map()
        alias_data = load_skill_aliases()
        self._aliases: dict[str, str] = {
            k.strip().lower(): v for k, v in alias_data.get("aliases", {}).items()
        }

    def _extract_raw_string(
        self,
        skill_input: str | SkillItem | JobSkillRequirement | Any,
    ) -> str:
        """Extract a string representation from various input types."""
        if isinstance(skill_input, str):
            return skill_input
        if isinstance(skill_input, SkillItem):
            return skill_input.canonical_name or skill_input.matched_alias
        if isinstance(skill_input, JobSkillRequirement):
            return getattr(skill_input, "canonical_name", None) or getattr(skill_input, "matched_alias", None) or getattr(skill_input, "skill_name", "") or ""
        if hasattr(skill_input, "canonical_name") and skill_input.canonical_name:
            return str(skill_input.canonical_name)
        if hasattr(skill_input, "name") and skill_input.name:
            return str(skill_input.name)
        return str(skill_input) if skill_input is not None else ""

    def _clean_token(self, raw: str) -> str:
        """
        Symbol-safe cleaning of a raw skill token.
        Preserves C++, C#, .NET, Node.js, CI/CD while removing bullets,
        surrounding parentheses/quotes, and trailing commas/colons.
        """
        cleaned = raw.strip()
        if not cleaned:
            return ""

        # Remove leading bullet points or numbered lists using repo's split_bullet
        marker, content = split_bullet(cleaned)
        if marker is not None and content:
            cleaned = content.strip()

        # Remove surrounding brackets/quotes e.g. "(AWS)" -> "AWS", "[Docker]" -> "Docker"
        # Protect .NET from having leading dot stripped
        if cleaned.startswith("(") and cleaned.endswith(")") or cleaned.startswith("[") and cleaned.endswith("]") or cleaned.startswith("{") and cleaned.endswith("}") or cleaned.startswith('"') and cleaned.endswith('"') or cleaned.startswith("'") and cleaned.endswith("'"):
            cleaned = cleaned[1:-1].strip()

        # Remove trailing commas, semicolons, colons, exclamation marks
        cleaned = re.sub(r"[\s,;:!]+$", "", cleaned).strip()

        # If it ends with a dot and is not just a single dot
        if cleaned.endswith(".") and len(cleaned) > 1:
            # e.g., "Python." -> "Python", "Node.js." -> "Node.js", ".NET." -> ".NET"
            cleaned = cleaned[:-1].strip()

        # Collapse internal multi-spaces
        cleaned = re.sub(r"\s+", " ", cleaned)

        return cleaned

    def _is_ambiguous_false_positive(self, cleaned: str) -> bool:
        """
        Detect if a phrase falsely triggers ambiguous tokens (C, Go, R).
        e.g., 'Vitamin C', 'Grade C', 'Go to', 'Go back'.
        """
        tokens = cleaned.lower().split()
        if len(tokens) >= 2:
            # Check prefix words like "Vitamin C", "Grade C", "Section C"
            if tokens[-1] in {"c", "r"} and any(t in NON_TECH_PREFIX_WORDS for t in tokens[:-1]):
                return True
            # Check following words like "Go to", "Go ahead"
            if tokens[0] == "go" and any(t in NON_TECH_POST_WORDS for t in tokens[1:]):
                return True
        return False

    def normalize_skill(
        self,
        skill_input: str | SkillItem | JobSkillRequirement | Any,
    ) -> NormalizedSkill:
        """
        Normalize a raw skill mention into a canonical NormalizedSkill object.

        Args:
            skill_input: String mention, SkillItem, or JobSkillRequirement.

        Returns:
            NormalizedSkill containing canonical name, match method, confidence, and provenance.
        """
        raw_mention = self._extract_raw_string(skill_input)
        if not raw_mention or not raw_mention.strip():
            return NormalizedSkill(
                raw_mention=raw_mention,
                canonical_name=None,
                category=None,
                is_recognized=False,
                matched_alias=None,
                match_method=SkillMatchMethod.UNRECOGNIZED,
                confidence=0.0,
                evidence="Empty or whitespace-only skill input",
            )

        cleaned = self._clean_token(raw_mention)
        if not cleaned:
            return NormalizedSkill(
                raw_mention=raw_mention,
                canonical_name=None,
                category=None,
                is_recognized=False,
                matched_alias=None,
                match_method=SkillMatchMethod.UNRECOGNIZED,
                confidence=0.0,
                evidence="Token emptied after symbol-safe cleaning",
            )

        # Check for ambiguous false positive phrases (e.g. "Vitamin C", "Go to")
        if self._is_ambiguous_false_positive(cleaned):
            return NormalizedSkill(
                raw_mention=raw_mention,
                canonical_name=None,
                category=None,
                is_recognized=False,
                matched_alias=None,
                match_method=SkillMatchMethod.UNRECOGNIZED,
                confidence=0.0,
                evidence=f"Ambiguous non-technical phrase rejected: '{cleaned}'",
            )

        # 1. Exact canonical match (verbatim case)
        if cleaned in self._canonical_skills:
            category = get_skill_category(cleaned)
            return NormalizedSkill(
                raw_mention=raw_mention,
                canonical_name=cleaned,
                category=category,
                is_recognized=True,
                matched_alias=None,
                match_method=SkillMatchMethod.EXACT_CANONICAL,
                confidence=1.0,
                evidence=f"Exact verbatim canonical match in taxonomy: '{cleaned}'",
            )

        lower_clean = cleaned.lower()

        # 2. Case-normalized canonical match (e.g. 'python' -> 'Python', 'c++' -> 'C++')
        if lower_clean in self._canonical_lower_map:
            canon = self._canonical_lower_map[lower_clean]
            category = get_skill_category(canon)
            return NormalizedSkill(
                raw_mention=raw_mention,
                canonical_name=canon,
                category=category,
                is_recognized=True,
                matched_alias=None,
                match_method=SkillMatchMethod.SYMBOL_NORMALIZED,
                confidence=1.0,
                evidence=f"Case-normalized match to canonical '{canon}'",
            )

        # 3. Taxonomy alias table lookup (e.g. 'js' -> 'JavaScript', 'k8s' -> 'Kubernetes')
        if lower_clean in self._aliases:
            canon_alias = self._aliases[lower_clean]
            # Resolve through canonical map in case alias target casing differs
            resolved_canon = self._canonical_lower_map.get(canon_alias.lower(), canon_alias)
            category = get_skill_category(resolved_canon)

            # Determine whether this is an abbreviation or standard alias
            is_abbrev = (
                lower_clean in KNOWN_ABBREVIATIONS
                or (len(cleaned) <= 4 and (cleaned.isupper() or cleaned.islower()))
            )
            match_method = (
                SkillMatchMethod.ABBREVIATION if is_abbrev else SkillMatchMethod.ALIAS
            )

            return NormalizedSkill(
                raw_mention=raw_mention,
                canonical_name=resolved_canon,
                category=category,
                is_recognized=True,
                matched_alias=cleaned,
                match_method=match_method,
                confidence=1.0,
                evidence=f"Resolved via {match_method.value} '{cleaned}' to canonical '{resolved_canon}'",
            )

        # 4. Variation normalization (e.g. 'react-js' -> 'React', 'ci - cd' -> 'CI/CD')
        # Try replacing hyphens/underscores with spaces or slashes
        variants = [
            lower_clean.replace("-", " "),
            lower_clean.replace("_", " "),
            lower_clean.replace("-", ""),
            lower_clean.replace(" ", ""),
        ]
        # Specific normalization for CI/CD variants like "ci - cd", "ci-cd"
        if re.match(r"^ci\s*[-/ ]\s*cd$", lower_clean):
            variants.insert(0, "ci/cd")

        for var in variants:
            if var in self._canonical_lower_map:
                canon = self._canonical_lower_map[var]
                return NormalizedSkill(
                    raw_mention=raw_mention,
                    canonical_name=canon,
                    category=get_skill_category(canon),
                    is_recognized=True,
                    matched_alias=var,
                    match_method=SkillMatchMethod.SYMBOL_NORMALIZED,
                    confidence=0.98,
                    evidence=f"Punctuation/space-normalized variant '{var}' resolved to canonical '{canon}'",
                )
            if var in self._aliases:
                canon_target = self._aliases[var]
                resolved_canon = self._canonical_lower_map.get(canon_target.lower(), canon_target)
                return NormalizedSkill(
                    raw_mention=raw_mention,
                    canonical_name=resolved_canon,
                    category=get_skill_category(resolved_canon),
                    is_recognized=True,
                    matched_alias=var,
                    match_method=SkillMatchMethod.SYMBOL_NORMALIZED,
                    confidence=0.98,
                    evidence=f"Variant '{var}' matched alias to canonical '{resolved_canon}'",
                )

        # 5. Unrecognized skill
        return NormalizedSkill(
            raw_mention=raw_mention,
            canonical_name=None,
            category=None,
            is_recognized=False,
            matched_alias=None,
            match_method=SkillMatchMethod.UNRECOGNIZED,
            confidence=0.0,
            evidence=f"Skill '{raw_mention}' not recognized in curated taxonomy or aliases",
        )

    def normalize_skills(
        self,
        skills: list[str | SkillItem | JobSkillRequirement | Any],
    ) -> list[NormalizedSkill]:
        """Normalize a collection of skill inputs."""
        return [self.normalize_skill(s) for s in skills]


class SkillEquivalenceEngine:
    """
    Controlled Equivalence & Relationship Reasoning Engine.

    Evaluates skill pairs for equivalence, relatedness, and prerequisites based on
    strict curated rules. Distinguishes exact matches, aliases, drop-in equivalents,
    related stack companions, and foundational prerequisites.
    """

    def __init__(self, normalizer: SkillNormalizer | None = None) -> None:
        self.normalizer = normalizer or SkillNormalizer()
        self.version = ENGINE_VERSION
        self._rules: list[EquivalenceRule] = []
        self._rule_lookup: dict[tuple[str, str], EquivalenceRule] = {}
        self._equivalents_by_skill: dict[str, list[str]] = {}
        self._related_by_skill: dict[str, list[str]] = {}
        self._prerequisites_by_skill: dict[str, list[str]] = {}
        self._dependents_by_skill: dict[str, list[str]] = {}

        self._load_curated_rules()

    def _load_curated_rules(self) -> None:
        """Load and index curated rules from skill_equivalences.json."""
        data = load_skill_equivalences()
        for raw_rule in data.get("relationships", []):
            try:
                rule = EquivalenceRule(
                    canonical_skill=raw_rule["canonical_skill"],
                    equivalent_skill=raw_rule["equivalent_skill"],
                    relationship_type=SkillRelationshipType(raw_rule["relationship_type"]),
                    confidence=float(raw_rule.get("confidence", 1.0)),
                    bidirectional=bool(raw_rule.get("bidirectional", True)),
                    source=raw_rule.get("source", "curated"),
                    rationale=raw_rule.get("rationale", ""),
                    version=raw_rule.get("version", "1.0.0"),
                )
                self.register_rule(rule)
            except (KeyError, ValueError):
                continue

    def register_rule(self, rule: EquivalenceRule) -> None:
        """
        Register a new EquivalenceRule into the lookup tables.

        Args:
            rule: EquivalenceRule instance.
        """
        self._rules.append(rule)
        key_fwd = (rule.canonical_skill.strip().lower(), rule.equivalent_skill.strip().lower())
        self._rule_lookup[key_fwd] = rule

        if rule.bidirectional:
            key_rev = (rule.equivalent_skill.strip().lower(), rule.canonical_skill.strip().lower())
            self._rule_lookup[key_rev] = rule

        canon_lower = rule.canonical_skill.strip().lower()
        equiv_lower = rule.equivalent_skill.strip().lower()

        if rule.relationship_type in {
            SkillRelationshipType.EQUIVALENT,
            SkillRelationshipType.EXACT_ALIAS,
        }:
            self._equivalents_by_skill.setdefault(canon_lower, []).append(rule.equivalent_skill)
            if rule.bidirectional:
                self._equivalents_by_skill.setdefault(equiv_lower, []).append(rule.canonical_skill)

        elif rule.relationship_type == SkillRelationshipType.RELATED:
            self._related_by_skill.setdefault(canon_lower, []).append(rule.equivalent_skill)
            if rule.bidirectional:
                self._related_by_skill.setdefault(equiv_lower, []).append(rule.canonical_skill)

        elif rule.relationship_type == SkillRelationshipType.PREREQUISITE:
            # canonical_skill is prerequisite FOR equivalent_skill
            self._prerequisites_by_skill.setdefault(equiv_lower, []).append(rule.canonical_skill)
            self._dependents_by_skill.setdefault(canon_lower, []).append(rule.equivalent_skill)

    def _lookup_rule(
        self,
        key_a: str,
        key_b: str,
    ) -> tuple[EquivalenceRule, bool] | None:
        """
        Look up a rule between two skill keys.
        Returns tuple (rule, is_reversed).
        """
        ka = key_a.strip().lower()
        kb = key_b.strip().lower()

        if (ka, kb) in self._rule_lookup:
            return self._rule_lookup[(ka, kb)], False
        if (kb, ka) in self._rule_lookup:
            rule = self._rule_lookup[(kb, ka)]
            return rule, True
        return None

    def evaluate_equivalence(
        self,
        skill_a: str | SkillItem | JobSkillRequirement | Any,
        skill_b: str | SkillItem | JobSkillRequirement | Any,
    ) -> EquivalenceEvaluation:
        """
        Evaluate the relationship between two skills.

        Distinguishes:
        - EXACT_MATCH: identical canonical skill.
        - EXACT_ALIAS: alias/abbreviation resolving to same canonical skill.
        - EQUIVALENT: explicitly configured drop-in equivalent skills (e.g. MariaDB <=> MySQL).
        - RELATED: explicitly configured ecosystem companions (e.g. Docker <=> Kubernetes).
        - PREREQUISITE: explicitly configured foundational dependency (e.g. Python -> Django).
        - UNRELATED: no equivalence or relationship rule configured.

        Args:
            skill_a: First skill mention (candidate skill).
            skill_b: Second skill mention (job requirement).

        Returns:
            EquivalenceEvaluation with classification, similarity score, confidence, and rationale.
        """
        norm_a = self.normalizer.normalize_skill(skill_a)
        norm_b = self.normalizer.normalize_skill(skill_b)

        raw_a = norm_a.raw_mention
        raw_b = norm_b.raw_mention
        canon_a = norm_a.canonical_name
        canon_b = norm_b.canonical_name

        # 1. Both resolved to the same canonical skill in taxonomy
        if canon_a and canon_b and canon_a.lower() == canon_b.lower():
            # Check whether raw mentions were identical
            raw_clean_a = self.normalizer._clean_token(raw_a).lower()
            raw_clean_b = self.normalizer._clean_token(raw_b).lower()

            if raw_clean_a == raw_clean_b:
                return EquivalenceEvaluation(
                    skill_a=raw_a,
                    skill_b=raw_b,
                    canonical_a=canon_a,
                    canonical_b=canon_b,
                    is_equivalent=True,
                    is_related=False,
                    relationship_type=SkillRelationshipType.EXACT_MATCH,
                    similarity_score=1.0,
                    confidence=1.0,
                    rationale=f"Exact canonical match: '{canon_a}'",
                    evidence=f"{norm_a.evidence} | {norm_b.evidence}",
                    version=self.version,
                )
            else:
                return EquivalenceEvaluation(
                    skill_a=raw_a,
                    skill_b=raw_b,
                    canonical_a=canon_a,
                    canonical_b=canon_b,
                    is_equivalent=True,
                    is_related=False,
                    relationship_type=SkillRelationshipType.EXACT_ALIAS,
                    similarity_score=1.0,
                    confidence=1.0,
                    rationale=f"Exact alias resolution: '{raw_a}' and '{raw_b}' both resolve to canonical '{canon_a}'",
                    evidence=f"{norm_a.evidence} | {norm_b.evidence}",
                    version=self.version,
                )

        # 2. Both uncanonical, but raw strings are identical
        if not canon_a and not canon_b:
            raw_clean_a = self.normalizer._clean_token(raw_a).lower()
            raw_clean_b = self.normalizer._clean_token(raw_b).lower()
            if raw_clean_a and raw_clean_a == raw_clean_b:
                return EquivalenceEvaluation(
                    skill_a=raw_a,
                    skill_b=raw_b,
                    canonical_a=None,
                    canonical_b=None,
                    is_equivalent=True,
                    is_related=False,
                    relationship_type=SkillRelationshipType.EXACT_MATCH,
                    similarity_score=1.0,
                    confidence=0.85,
                    rationale=f"Exact verbatim match for uncanonical skill: '{raw_a}'",
                    evidence="Verbatim text equality between uncanonical skills",
                    version=self.version,
                )

        # 3. Check explicit configured equivalence rules
        # Test candidate keys: canonical names if available, else raw cleaned mentions
        key_a = canon_a if canon_a else self.normalizer._clean_token(raw_a)
        key_b = canon_b if canon_b else self.normalizer._clean_token(raw_b)

        rule_match = self._lookup_rule(key_a, key_b)
        if not rule_match and (raw_a != key_a or raw_b != key_b):
            # Fallback check on raw cleaned mentions
            rule_match = self._lookup_rule(
                self.normalizer._clean_token(raw_a),
                self.normalizer._clean_token(raw_b),
            )

        if rule_match:
            rule, is_reversed = rule_match

            if rule.relationship_type in {
                SkillRelationshipType.EQUIVALENT,
                SkillRelationshipType.EXACT_ALIAS,
            }:
                return EquivalenceEvaluation(
                    skill_a=raw_a,
                    skill_b=raw_b,
                    canonical_a=canon_a or rule.canonical_skill,
                    canonical_b=canon_b or rule.equivalent_skill,
                    is_equivalent=True,
                    is_related=False,
                    relationship_type=rule.relationship_type,
                    similarity_score=rule.confidence,
                    confidence=rule.confidence,
                    rationale=f"Configured equivalence: {rule.rationale}",
                    evidence=f"Equivalence rule v{rule.version} from {rule.source}",
                    version=rule.version,
                )

            elif rule.relationship_type == SkillRelationshipType.RELATED:
                return EquivalenceEvaluation(
                    skill_a=raw_a,
                    skill_b=raw_b,
                    canonical_a=canon_a or rule.canonical_skill,
                    canonical_b=canon_b or rule.equivalent_skill,
                    is_equivalent=False,
                    is_related=True,
                    relationship_type=SkillRelationshipType.RELATED,
                    similarity_score=rule.confidence,
                    confidence=rule.confidence,
                    rationale=f"Related ecosystem skill: {rule.rationale}",
                    evidence=f"Relationship rule v{rule.version} from {rule.source}",
                    version=rule.version,
                )

            elif rule.relationship_type == SkillRelationshipType.PREREQUISITE:
                # rule.canonical_skill is prerequisite FOR rule.equivalent_skill
                if not is_reversed:
                    rationale = (
                        f"Prerequisite dependency: '{rule.canonical_skill}' is a foundational prerequisite for '{rule.equivalent_skill}'. "
                        f"{rule.rationale}"
                    )
                else:
                    rationale = (
                        f"Prerequisite dependency: '{rule.equivalent_skill}' requires foundational knowledge in '{rule.canonical_skill}'. "
                        f"{rule.rationale}"
                    )

                return EquivalenceEvaluation(
                    skill_a=raw_a,
                    skill_b=raw_b,
                    canonical_a=canon_a or rule.canonical_skill,
                    canonical_b=canon_b or rule.equivalent_skill,
                    is_equivalent=False,
                    is_related=True,
                    relationship_type=SkillRelationshipType.PREREQUISITE,
                    similarity_score=rule.confidence,
                    confidence=rule.confidence,
                    rationale=rationale,
                    evidence=f"Prerequisite rule v{rule.version} from {rule.source}",
                    version=rule.version,
                )

        # 4. No configured equivalence or relationship rule exists.
        # Strict rule: unrelated skills (even within the same taxonomy category) are UNRELATED.
        # Python and JavaScript are not equivalent just because both are programming languages.
        return EquivalenceEvaluation(
            skill_a=raw_a,
            skill_b=raw_b,
            canonical_a=canon_a,
            canonical_b=canon_b,
            is_equivalent=False,
            is_related=False,
            relationship_type=SkillRelationshipType.UNRELATED,
            similarity_score=0.0,
            confidence=1.0,
            rationale=f"No equivalence, relatedness, or prerequisite rule configured between '{canon_a or raw_a}' and '{canon_b or raw_b}'.",
            evidence="Strict rule-based evaluation: unlinked skills are treated as unrelated",
            version=self.version,
        )

    def get_equivalent_skills(self, skill: str) -> list[str]:
        """Return all explicitly configured equivalent skills for a skill."""
        norm = self.normalizer.normalize_skill(skill)
        target = (norm.canonical_name or skill).strip().lower()
        return list(dict.fromkeys(self._equivalents_by_skill.get(target, [])))

    def get_related_skills(self, skill: str) -> list[str]:
        """Return all explicitly configured related skills for a skill."""
        norm = self.normalizer.normalize_skill(skill)
        target = (norm.canonical_name or skill).strip().lower()
        return list(dict.fromkeys(self._related_by_skill.get(target, [])))

    def get_prerequisites(self, skill: str) -> list[str]:
        """Return foundational prerequisites required by this skill."""
        norm = self.normalizer.normalize_skill(skill)
        target = (norm.canonical_name or skill).strip().lower()
        return list(dict.fromkeys(self._prerequisites_by_skill.get(target, [])))

    def get_dependents(self, skill: str) -> list[str]:
        """Return skills that depend on this skill as a prerequisite."""
        norm = self.normalizer.normalize_skill(skill)
        target = (norm.canonical_name or skill).strip().lower()
        return list(dict.fromkeys(self._dependents_by_skill.get(target, [])))

    def compare_skill_sets(
        self,
        candidate_skills: list[str | SkillItem | Any],
        job_required_skills: list[str | JobSkillRequirement | Any],
        job_preferred_skills: list[str | JobSkillRequirement | Any] | None = None,
    ) -> SkillSetComparison:
        """
        Compare a Candidate's skills against Job Description requirements.

        Performs deterministic equivalence matching, categorizes matches into
        exact/equivalent matches, missing requirements, related matches, and candidate extras.
        Calculates required coverage ratio and overall coverage ratio.
        """
        preferred_skills = job_preferred_skills or []

        # Deduplicate candidate skills by canonical name / cleaned token
        cand_normalized = [self.normalizer.normalize_skill(s) for s in candidate_skills]
        seen_cand: set[str] = set()
        unique_cand: list[NormalizedSkill] = []
        for ns in cand_normalized:
            key = (ns.canonical_name or ns.raw_mention).strip().lower()
            if key and key not in seen_cand:
                seen_cand.add(key)
                unique_cand.append(ns)

        matched_required: list[EquivalenceEvaluation] = []
        missing_required: list[str] = []
        matched_preferred: list[EquivalenceEvaluation] = []
        missing_preferred: list[str] = []
        related_matches: list[EquivalenceEvaluation] = []
        matched_cand_indices: set[int] = set()

        # Evaluate Job Required Skills
        for req in job_required_skills:
            req_str = self.normalizer._extract_raw_string(req)
            best_eval: EquivalenceEvaluation | None = None
            best_cand_idx: int | None = None

            for idx, c_norm in enumerate(unique_cand):
                evaluation = self.evaluate_equivalence(c_norm, req)
                if evaluation.is_equivalent:
                    if best_eval is None or evaluation.similarity_score > best_eval.similarity_score:
                        best_eval = evaluation
                        best_cand_idx = idx
                elif evaluation.is_related and (
                    best_eval is None
                    or (not best_eval.is_equivalent and evaluation.similarity_score > best_eval.similarity_score)
                ):
                    best_eval = evaluation
                    best_cand_idx = idx

            if best_eval and best_eval.is_equivalent:
                matched_required.append(best_eval)
                if best_cand_idx is not None:
                    matched_cand_indices.add(best_cand_idx)
            else:
                missing_required.append(req_str)
                if best_eval and best_eval.is_related:
                    related_matches.append(best_eval)
                    if best_cand_idx is not None:
                        matched_cand_indices.add(best_cand_idx)

        # Evaluate Job Preferred Skills
        for pref in preferred_skills:
            pref_str = self.normalizer._extract_raw_string(pref)
            best_eval: EquivalenceEvaluation | None = None
            best_cand_idx: int | None = None

            for idx, c_norm in enumerate(unique_cand):
                evaluation = self.evaluate_equivalence(c_norm, pref)
                if evaluation.is_equivalent:
                    if best_eval is None or evaluation.similarity_score > best_eval.similarity_score:
                        best_eval = evaluation
                        best_cand_idx = idx
                elif evaluation.is_related and (
                    best_eval is None
                    or (not best_eval.is_equivalent and evaluation.similarity_score > best_eval.similarity_score)
                ):
                    best_eval = evaluation
                    best_cand_idx = idx

            if best_eval and best_eval.is_equivalent:
                matched_preferred.append(best_eval)
                if best_cand_idx is not None:
                    matched_cand_indices.add(best_cand_idx)
            else:
                missing_preferred.append(pref_str)
                if best_eval and best_eval.is_related:
                    related_matches.append(best_eval)
                    if best_cand_idx is not None:
                        matched_cand_indices.add(best_cand_idx)

        # Identify unmatched candidate skills
        unmatched_candidate: list[str] = [
            c_norm.raw_mention
            for idx, c_norm in enumerate(unique_cand)
            if idx not in matched_cand_indices
        ]

        # Calculate coverage ratios
        total_req = len(job_required_skills)
        total_pref = len(preferred_skills)

        req_coverage = len(matched_required) / total_req if total_req > 0 else 1.0

        total_weights = (total_req * 1.0) + (total_pref * 0.5)
        earned_weights = (len(matched_required) * 1.0) + (len(matched_preferred) * 0.5)
        overall_coverage = earned_weights / total_weights if total_weights > 0 else 1.0

        return SkillSetComparison(
            candidate_skills=[c.raw_mention for c in unique_cand],
            job_required_skills=[self.normalizer._extract_raw_string(r) for r in job_required_skills],
            job_preferred_skills=[self.normalizer._extract_raw_string(p) for p in preferred_skills],
            matched_required=matched_required,
            matched_preferred=matched_preferred,
            missing_required=missing_required,
            missing_preferred=missing_preferred,
            related_matches=related_matches,
            unmatched_candidate=unmatched_candidate,
            required_coverage_ratio=round(req_coverage, 3),
            overall_coverage_ratio=round(overall_coverage, 3),
        )


# Global singleton instances for direct convenience calls
_default_normalizer: SkillNormalizer | None = None
_default_engine: SkillEquivalenceEngine | None = None


def get_skill_normalizer() -> SkillNormalizer:
    """Return the global cached SkillNormalizer instance."""
    global _default_normalizer
    if _default_normalizer is None:
        _default_normalizer = SkillNormalizer()
    return _default_normalizer


def get_equivalence_engine() -> SkillEquivalenceEngine:
    """Return the global cached SkillEquivalenceEngine instance."""
    global _default_engine
    if _default_engine is None:
        _default_engine = SkillEquivalenceEngine(get_skill_normalizer())
    return _default_engine


def normalize_skill(skill_input: str | SkillItem | JobSkillRequirement | Any) -> NormalizedSkill:
    """Convenience helper to normalize a single skill."""
    return get_skill_normalizer().normalize_skill(skill_input)


def evaluate_skill_equivalence(
    skill_a: str | SkillItem | JobSkillRequirement | Any,
    skill_b: str | SkillItem | JobSkillRequirement | Any,
) -> EquivalenceEvaluation:
    """Convenience helper to evaluate equivalence between two skills."""
    return get_equivalence_engine().evaluate_equivalence(skill_a, skill_b)


def compare_candidate_to_job_skills(
    candidate_skills: list[str | SkillItem | Any],
    job_required_skills: list[str | JobSkillRequirement | Any],
    job_preferred_skills: list[str | JobSkillRequirement | Any] | None = None,
) -> SkillSetComparison:
    """Convenience helper to compare candidate skills to job requirements."""
    return get_equivalence_engine().compare_skill_sets(
        candidate_skills, job_required_skills, job_preferred_skills
    )


__all__ = [
    "AMBIGUOUS_SHORT_NAMES",
    "ENGINE_VERSION",
    "KNOWN_ABBREVIATIONS",
    "SkillEquivalenceEngine",
    "SkillNormalizer",
    "compare_candidate_to_job_skills",
    "evaluate_skill_equivalence",
    "get_equivalence_engine",
    "get_skill_normalizer",
    "normalize_skill",
]
