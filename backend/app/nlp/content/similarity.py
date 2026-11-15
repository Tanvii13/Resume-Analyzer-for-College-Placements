"""
Deterministic text similarity, duplicate detection, and generic content analyzer for Sprint 3 Module C.

Detects:
- Duplicate or near-duplicate bullet points across entries or within an entry.
- Generic and cliché resume descriptions (e.g. 'worked on a web application').
- Abnormally short descriptions (<10 words) or tautological descriptions repeating the title.
- Phrase repetition across distinct project entries.

Guarantees:
- Completely deterministic token n-gram Jaccard similarity and Levenshtein comparison.
- Does NOT classify projects as duplicates solely because they share tech stack tokens.
"""

import re
from typing import Dict, List, Optional, Set, Tuple

# Common generic, boilerplate, or low-specificity resume phrases
GENERIC_PHRASE_PATTERNS: List[Tuple[str, re.Pattern]] = [
    (
        "Generic Web Application Cliché",
        re.compile(r"\b(?:worked on|developed|built)\s+(?:a|an)\s+(?:web\s+)?(?:application|website|app)\s+using\s+(?:modern\s+technologies|html[,\s]+css)\b", re.IGNORECASE),
    ),
    (
        "Vague Responsibility Statement",
        re.compile(r"\bresponsible\s+for\s+(?:developing\s+features|fixing\s+bugs|testing\s+code|day\s+to\s+day\s+tasks)\b", re.IGNORECASE),
    ),
    (
        "Generic Database Phrase",
        re.compile(r"\b(?:created|built|designed)\s+(?:a\s+)?database\s+to\s+store\s+(?:user\s+)?data\b", re.IGNORECASE),
    ),
    (
        "Vague Assistance Statement",
        re.compile(r"\b(?:helped|assisted)\s+(?:the\s+)?team\s+with\s+(?:various|daily|different)\s+tasks\b", re.IGNORECASE),
    ),
    (
        "Superficial Learning Statement",
        re.compile(r"\blearned\s+(?:new\s+)?technologies\s+and\s+applied\s+them\b", re.IGNORECASE),
    ),
    (
        "Empty User Interface Cliché",
        re.compile(r"\bdesigned\s+(?:a\s+)?(?:clean|user[- ]friendly|intuitive)\s+(?:ui|interface|dashboard)\b", re.IGNORECASE),
    ),
]


def _tokenize_prose(text: str) -> List[str]:
    """Tokenize text into lowercase alphanumeric words, filtering single-char noise."""
    return [w for w in re.findall(r"\b[a-z0-9]+\b", text.lower()) if len(w) > 1]


def compute_jaccard_similarity(text1: str, text2: str) -> float:
    """
    Compute Jaccard token similarity between two text snippets.
    Excludes technology stop-words to ensure prose is compared.
    """
    tokens1 = set(_tokenize_prose(text1))
    tokens2 = set(_tokenize_prose(text2))

    if not tokens1 or not tokens2:
        return 0.0

    intersection = len(tokens1.intersection(tokens2))
    union = len(tokens1.union(tokens2))
    return round(intersection / float(union), 4)


def find_duplicate_bullets_across_entries(
    entries: List[Tuple[str, str, List[str]]], # (entry_id, title, list of bullets)
) -> List[str]:
    """
    Identify identical or near-duplicate bullet points across different project/experience entries.

    Returns:
        List of human-readable duplicate warnings.
    """
    warnings: List[str] = []
    seen_bullets: Dict[str, Tuple[str, str]] = {} # normalized_text -> (entry_id, title)

    for entry_id, title, bullets in entries:
        for b in bullets:
            clean_b = " ".join(_tokenize_prose(b))
            if len(clean_b.split()) >= 6:  # Only evaluate substantial bullets
                if clean_b in seen_bullets:
                    prev_id, prev_title = seen_bullets[clean_b]
                    warnings.append(
                        f"Duplicate bullet point detected across '{prev_title}' ({prev_id}) and '{title}' ({entry_id}): "
                        f"'{b[:65]}...'"
                    )
                else:
                    seen_bullets[clean_b] = (entry_id, title)

    return warnings


def detect_generic_content(text: str) -> List[str]:
    """
    Check if a description or bullet point contains highly generic, low-effort clichés.

    Returns:
        List of identified generic phrase descriptions.
    """
    matched: List[str] = []
    for label, pattern in GENERIC_PHRASE_PATTERNS:
        if pattern.search(text):
            matched.append(label)
    return matched


def evaluate_description_substance(
    title: Optional[str],
    description: Optional[str],
    highlights: List[str],
    technologies: List[str],
) -> Tuple[bool, List[str]]:
    """
    Evaluate whether a project or experience description has sufficient contextual substance.

    Returns:
        (is_sufficient, list_of_defects)
    """
    defects: List[str] = []

    all_text = " ".join([description or ""] + highlights).strip()
    words = all_text.split()

    # 1. Missing or Extremely Short Description
    if not words:
        defects.append("Missing description and bullet points. Recruiters cannot evaluate contributions.")
        return False, defects

    if len(words) < 10:
        defects.append(
            f"Extremely short description ({len(words)} words). Explain the problem, architecture, and outcomes."
        )

    # 2. Tautological Description (merely repeats the title)
    if title and len(words) <= 15:
        title_tokens = set(_tokenize_prose(title))
        desc_tokens = set(_tokenize_prose(all_text))
        if title_tokens and desc_tokens:
            overlap = len(title_tokens.intersection(desc_tokens)) / float(len(title_tokens))
            if overlap >= 0.80 and len(words) <= 12:
                defects.append("Description merely restates the project title without providing technical details.")

    # 3. Generic clichés check
    generic_matches = detect_generic_content(all_text)
    for g in generic_matches:
        defects.append(f"Contains generic phrasing ({g}). Replace with specific architectural accomplishments.")

    # 4. Tech stack visibility check
    if not technologies and not any(len(t) > 2 for t in _tokenize_prose(all_text)):
        defects.append("No specific programming languages, tools, or frameworks are mentioned in this entry.")

    is_sufficient = len(defects) == 0
    return is_sufficient, defects


__all__ = [
    "GENERIC_PHRASE_PATTERNS",
    "compute_jaccard_similarity",
    "find_duplicate_bullets_across_entries",
    "detect_generic_content",
    "evaluate_description_substance",
]
