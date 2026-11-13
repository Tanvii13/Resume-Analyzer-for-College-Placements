"""
Action-verb dictionary, categorizer, and detection engine for Sprint 3 Module C.

Provides:
- Curated, configurable dictionary of high-impact technical and leadership verbs.
- Multiform inflection mapping (base, past, gerund, 3rd person).
- Categorization into functional domains (Engineering, Optimization, Automation, Analysis, Leadership, Creation).
- Detection of leading action verbs versus passive/weak phrases.
"""

import re
from typing import Dict, List, Optional, Set, Tuple
from app.nlp.content.schemas import ActionVerbMatch, VerbCategory

# Curated mapping of canonical base verb lemma -> (VerbCategory, Set of inflected forms)
ACTION_VERB_TAXONOMY: Dict[str, Tuple[VerbCategory, Set[str]]] = {
    # -------------------------------------------------------------------------
    # Engineering & Technical Construction
    # -------------------------------------------------------------------------
    "develop": (VerbCategory.ENGINEERING, {"develop", "developed", "developing", "develops"}),
    "architect": (VerbCategory.ENGINEERING, {"architect", "architected", "architecting", "architects"}),
    "engineer": (VerbCategory.ENGINEERING, {"engineer", "engineered", "engineering", "engineers"}),
    "build": (VerbCategory.ENGINEERING, {"build", "built", "building", "builds"}),
    "design": (VerbCategory.ENGINEERING, {"design", "designed", "designing", "designs"}),
    "implement": (VerbCategory.ENGINEERING, {"implement", "implemented", "implementing", "implements"}),
    "construct": (VerbCategory.ENGINEERING, {"construct", "constructed", "constructing", "constructs"}),
    "program": (VerbCategory.ENGINEERING, {"program", "programmed", "programming", "programs"}),
    "code": (VerbCategory.ENGINEERING, {"code", "coded", "coding", "codes"}),
    "refactor": (VerbCategory.ENGINEERING, {"refactor", "refactored", "refactoring", "refactors"}),
    "rewrite": (VerbCategory.ENGINEERING, {"rewrite", "rewrote", "rewritten", "rewriting", "rewrites"}),
    "prototype": (VerbCategory.ENGINEERING, {"prototype", "prototyped", "prototyping", "prototypes"}),
    "debug": (VerbCategory.ENGINEERING, {"debug", "debugged", "debugging", "debugs"}),
    "model": (VerbCategory.ENGINEERING, {"model", "modeled", "modelled", "modeling", "modelling", "models"}),
    "structure": (VerbCategory.ENGINEERING, {"structure", "structured", "structuring", "structures"}),

    # -------------------------------------------------------------------------
    # Optimization & Performance
    # -------------------------------------------------------------------------
    "optimize": (VerbCategory.OPTIMIZATION, {"optimize", "optimized", "optimizing", "optimizes", "optimise", "optimised", "optimising"}),
    "accelerate": (VerbCategory.OPTIMIZATION, {"accelerate", "accelerated", "accelerating", "accelerates"}),
    "reduce": (VerbCategory.OPTIMIZATION, {"reduce", "reduced", "reducing", "reduces"}),
    "cut": (VerbCategory.OPTIMIZATION, {"cut", "cutting", "cuts"}),
    "boost": (VerbCategory.OPTIMIZATION, {"boost", "boosted", "boosting", "boosts"}),
    "enhance": (VerbCategory.OPTIMIZATION, {"enhance", "enhanced", "enhancing", "enhances"}),
    "improve": (VerbCategory.OPTIMIZATION, {"improve", "improved", "improving", "improves"}),
    "streamline": (VerbCategory.OPTIMIZATION, {"streamline", "streamlined", "streamlining", "streamlines"}),
    "scale": (VerbCategory.OPTIMIZATION, {"scale", "scaled", "scaling", "scales"}),
    "maximize": (VerbCategory.OPTIMIZATION, {"maximize", "maximized", "maximizing", "maximizes", "maximise", "maximised"}),
    "minimize": (VerbCategory.OPTIMIZATION, {"minimize", "minimized", "minimizing", "minimizes", "minimise", "minimised"}),
    "compress": (VerbCategory.OPTIMIZATION, {"compress", "compressed", "compressing", "compresses"}),

    # -------------------------------------------------------------------------
    # Automation & DevOps
    # -------------------------------------------------------------------------
    "automate": (VerbCategory.AUTOMATION, {"automate", "automated", "automating", "automates"}),
    "deploy": (VerbCategory.AUTOMATION, {"deploy", "deployed", "deploying", "deploys"}),
    "containerize": (VerbCategory.AUTOMATION, {"containerize", "containerized", "containerizing", "containerizes", "containerise", "containerised"}),
    "orchestrate": (VerbCategory.AUTOMATION, {"orchestrate", "orchestrated", "orchestrating", "orchestrates"}),
    "configure": (VerbCategory.AUTOMATION, {"configure", "configured", "configuring", "configures"}),
    "integrate": (VerbCategory.AUTOMATION, {"integrate", "integrated", "integrating", "integrates"}),
    "provision": (VerbCategory.AUTOMATION, {"provision", "provisioned", "provisioning", "provisions"}),
    "pipeline": (VerbCategory.AUTOMATION, {"pipeline", "pipelined", "pipelining", "pipelines"}),
    "migrate": (VerbCategory.AUTOMATION, {"migrate", "migrated", "migrating", "migrates"}),
    "release": (VerbCategory.AUTOMATION, {"release", "released", "releasing", "releases"}),
    "dockerize": (VerbCategory.AUTOMATION, {"dockerize", "dockerized", "dockerizing", "dockerizes"}),
    "maintain": (VerbCategory.AUTOMATION, {"maintain", "maintained", "maintaining", "maintains"}),

    # -------------------------------------------------------------------------
    # Analysis & Evaluation
    # -------------------------------------------------------------------------
    "analyze": (VerbCategory.ANALYSIS, {"analyze", "analyzed", "analyzing", "analyzes", "analyse", "analysed", "analysing", "analyses"}),
    "evaluate": (VerbCategory.ANALYSIS, {"evaluate", "evaluated", "evaluating", "evaluates"}),
    "benchmark": (VerbCategory.ANALYSIS, {"benchmark", "benchmarked", "benchmarking", "benchmarks"}),
    "audit": (VerbCategory.ANALYSIS, {"audit", "audited", "auditing", "audits"}),
    "profile": (VerbCategory.ANALYSIS, {"profile", "profiled", "profiling", "profiles"}),
    "test": (VerbCategory.ANALYSIS, {"test", "tested", "testing", "tests"}),
    "investigate": (VerbCategory.ANALYSIS, {"investigate", "investigated", "investigating", "investigates"}),
    "measure": (VerbCategory.ANALYSIS, {"measure", "measured", "measuring", "measures"}),
    "identify": (VerbCategory.ANALYSIS, {"identify", "identified", "identifying", "identifies"}),
    "diagnose": (VerbCategory.ANALYSIS, {"diagnose", "diagnosed", "diagnosing", "diagnoses"}),
    "validate": (VerbCategory.ANALYSIS, {"validate", "validated", "validating", "validates"}),
    "verify": (VerbCategory.ANALYSIS, {"verify", "verified", "verifying", "verifies"}),
    "assess": (VerbCategory.ANALYSIS, {"assess", "assessed", "assessing", "assesses"}),
    "monitor": (VerbCategory.ANALYSIS, {"monitor", "monitored", "monitoring", "monitors"}),

    # -------------------------------------------------------------------------
    # Leadership & Collaboration
    # -------------------------------------------------------------------------
    "lead": (VerbCategory.LEADERSHIP, {"lead", "led", "leading", "leads"}),
    "spearhead": (VerbCategory.LEADERSHIP, {"spearhead", "spearheaded", "spearheading", "spearheads"}),
    "coordinate": (VerbCategory.LEADERSHIP, {"coordinate", "coordinated", "coordinating", "coordinates"}),
    "mentor": (VerbCategory.LEADERSHIP, {"mentor", "mentored", "mentoring", "mentors"}),
    "collaborate": (VerbCategory.LEADERSHIP, {"collaborate", "collaborated", "collaborating", "collaborates"}),
    "manage": (VerbCategory.LEADERSHIP, {"manage", "managed", "managing", "manages"}),
    "guide": (VerbCategory.LEADERSHIP, {"guide", "guided", "guiding", "guides"}),
    "direct": (VerbCategory.LEADERSHIP, {"direct", "directed", "directing", "directs"}),
    "deliver": (VerbCategory.LEADERSHIP, {"deliver", "delivered", "delivering", "delivers"}),
    "supervise": (VerbCategory.LEADERSHIP, {"supervise", "supervised", "supervising", "supervises"}),

    # -------------------------------------------------------------------------
    # Creation & Innovation
    # -------------------------------------------------------------------------
    "create": (VerbCategory.CREATION, {"create", "created", "creating", "creates"}),
    "author": (VerbCategory.CREATION, {"author", "authored", "authoring", "authors"}),
    "devise": (VerbCategory.CREATION, {"devise", "devised", "devising", "devises"}),
    "formulate": (VerbCategory.CREATION, {"formulate", "formulated", "formulating", "formulates"}),
    "launch": (VerbCategory.CREATION, {"launch", "launched", "launching", "launches"}),
    "establish": (VerbCategory.CREATION, {"establish", "established", "establishing", "establishes"}),
    "introduce": (VerbCategory.CREATION, {"introduce", "introduced", "introducing", "introduces"}),
    "pioneer": (VerbCategory.CREATION, {"pioneer", "pioneered", "pioneering", "pioneers"}),
    "invent": (VerbCategory.CREATION, {"invent", "invented", "inventing", "invents"}),
}

# Reverse lookup table: inflected_word -> (lemma, VerbCategory)
_INFLECTION_LOOKUP: Dict[str, Tuple[str, VerbCategory]] = {}
for lemma, (cat, forms) in ACTION_VERB_TAXONOMY.items():
    for f in forms:
        _INFLECTION_LOOKUP[f.lower()] = (lemma, cat)

# Weak, passive, or vague introductory phrases
WEAK_PHRASES: List[Tuple[str, re.Pattern]] = [
    ("worked on", re.compile(r"^\s*(?:[•\-*]\s*)?worked\s+on\b", re.IGNORECASE)),
    ("helped with", re.compile(r"^\s*(?:[•\-*]\s*)?helped\s+with\b", re.IGNORECASE)),
    ("responsible for", re.compile(r"^\s*(?:[•\-*]\s*)?responsible\s+for\b", re.IGNORECASE)),
    ("assisted with/in", re.compile(r"^\s*(?:[•\-*]\s*)?assisted\s+(?:in|with)\b", re.IGNORECASE)),
    ("participated in", re.compile(r"^\s*(?:[•\-*]\s*)?participated\s+in\b", re.IGNORECASE)),
    ("handled", re.compile(r"^\s*(?:[•\-*]\s*)?handled\b", re.IGNORECASE)),
    ("involved in", re.compile(r"^\s*(?:[•\-*]\s*)?involved\s+in\b", re.IGNORECASE)),
    ("tasked with", re.compile(r"^\s*(?:[•\-*]\s*)?tasked\s+with\b", re.IGNORECASE)),
]


def classify_word_as_action_verb(word: str) -> Optional[Tuple[str, VerbCategory]]:
    """
    Check if a word is recognized as an action verb.
    Returns (lemma, VerbCategory) if matched, else None.
    """
    cleaned = word.strip().lower().rstrip(".,;:!?")
    return _INFLECTION_LOOKUP.get(cleaned)


def check_leading_action_verb(text: str) -> Optional[ActionVerbMatch]:
    """
    Check if the first word or second word (if first is adverb like 'Successfully')
    of a bullet or sentence is a recognized action verb.
    """
    # Strip bullet markers and whitespace
    clean_line = re.sub(r"^\s*[-•●○▪■□*+>»]\s*", "", text).strip()
    words = clean_line.split()
    if not words:
        return None

    first_word = words[0].strip().lower().rstrip(".,;:!?")
    match = classify_word_as_action_verb(first_word)
    if match:
        lemma, cat = match
        return ActionVerbMatch(
            verb=first_word,
            lemma=lemma,
            category=cat,
            is_leading=True,
        )

    # Check for leading adverbs (e.g. "Successfully deployed", "Independently architected")
    if len(words) >= 2 and first_word.endswith("ly"):
        second_word = words[1].strip().lower().rstrip(".,;:!?")
        match_second = classify_word_as_action_verb(second_word)
        if match_second:
            lemma, cat = match_second
            return ActionVerbMatch(
                verb=second_word,
                lemma=lemma,
                category=cat,
                is_leading=True,
            )

    return None


def detect_weak_introductory_phrase(text: str) -> Optional[str]:
    """
    Detect if a bullet point opens with a weak or passive phrase (e.g. 'worked on', 'responsible for').
    """
    clean_line = text.strip()
    for name, pattern in WEAK_PHRASES:
        if pattern.search(clean_line):
            return name
    return None


def find_action_verbs_in_text(text: str) -> List[ActionVerbMatch]:
    """
    Find all action verbs present across a text snippet with position awareness.
    """
    results: List[ActionVerbMatch] = []
    seen_verbs: Set[str] = set()

    # Split into words keeping punctuation stripped
    tokens = re.findall(r"\b[A-Za-z]+(?:-[A-Za-z]+)?\b", text)
    leading_match = check_leading_action_verb(text)
    leading_word = leading_match.verb.lower() if leading_match else None

    for idx, token in enumerate(tokens):
        word_lower = token.lower()
        if word_lower in _INFLECTION_LOOKUP:
            lemma, cat = _INFLECTION_LOOKUP[word_lower]
            if word_lower not in seen_verbs:
                seen_verbs.add(word_lower)
                is_leading = (word_lower == leading_word and idx <= 1)
                results.append(
                    ActionVerbMatch(
                        verb=word_lower,
                        lemma=lemma,
                        category=cat,
                        is_leading=is_leading,
                    )
                )

    return results


__all__ = [
    "ACTION_VERB_TAXONOMY",
    "WEAK_PHRASES",
    "classify_word_as_action_verb",
    "check_leading_action_verb",
    "detect_weak_introductory_phrase",
    "find_action_verbs_in_text",
]
