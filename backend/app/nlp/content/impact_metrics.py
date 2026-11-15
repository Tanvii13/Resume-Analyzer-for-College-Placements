"""
Measurable impact and quantifiable outcome detector for Sprint 3 Module C.

Detects evidence of verified measurable outcomes across:
- Percentages and proportional gains (e.g. 35%, 15 percent, 99.9%)
- Performance multipliers and speedups (e.g. 2.4x, 3-fold)
- Time savings and latency reductions (e.g. 120ms, sub-25ms, saved 15 hrs/week)
- User, client, and audience scale (e.g. 200 students, 10k users, 5,000 active sessions)
- Throughput and data volumes (e.g. 15,000 requests/sec, 1.2M records, 500 QPS)
- Accuracy, precision, and competitive benchmarks (e.g. 92% accuracy, top 1%, rank 12)
- Resource, memory, and cost savings (e.g. saved $5,000, 35% disk storage)

Strictly filters out non-impact numeric values:
- Calendar years (e.g. 2021, 2024, 2025)
- Port numbers (e.g. port 8080, port 3000)
- Software version numbers (e.g. Python 3.11, React 18, OAuth 2.0, HTML5)
- HTTP status codes (e.g. 200 OK, 404, 500)
- AI model names (e.g. GPT-4, ResNet-50, VGG-16, YOLOv8)
- Course identifiers (e.g. CS 101, CS50)
"""

import re
from typing import List, Set, Tuple
from app.nlp.content.schemas import ImpactMetricMatch

# -----------------------------------------------------------------------------
# False-Positive / Non-Impact Filters
# -----------------------------------------------------------------------------
NON_IMPACT_NUMERIC_PATTERNS = [
    # Calendar Years: 1990-2035
    re.compile(r"\b(?:19|20)\d{2}(?:\s*-\s*(?:19|20)?\d{2})?\b"),
    # Port Numbers: port 8080, :3000
    re.compile(r"\bport\s+\d{2,5}\b", re.IGNORECASE),
    re.compile(r":\d{4,5}\b"),
    # Language / Framework Versions: Python 3.11, React 18, Angular 16, Java 17
    re.compile(
        r"\b(?:python|react|node(?:\.js)?|angular|vue(?:\.js)?|java|c\+\+|go|ruby|php|scala|django|fastapi)\s+v?\d+(?:\.\d+)*\b",
        re.IGNORECASE,
    ),
    # Protocol & Spec Versions: OAuth 2.0, HTTP/2, HTML5, CSS3, TLS 1.3, IPv4, IPv6
    re.compile(
        r"\b(?:oauth|http\/?|html|css|tls|ssl|ip|ecma|es|pci[- ]?dss)\s*v?\d+(?:\.\d+)*\b",
        re.IGNORECASE,
    ),
    # Machine Learning Model Names: GPT-4, ResNet-50, VGG-16, YOLOv8, BERT-base, LLaMA-2
    re.compile(
        r"\b(?:gpt|resnet|vgg|yolo(?:v\d+)?|bert|densenet|llama|mobilenet|inception)[-_ ]?\d+[a-z]?\b",
        re.IGNORECASE,
    ),
    # HTTP Status Codes: HTTP 200, HTTP 404, 200 OK, 404 Not Found
    re.compile(r"\b(?:https?|status\s+code)\s*(?:200|201|204|400|401|403|404|500|502|503)\b", re.IGNORECASE),
    re.compile(r"\b(?:200\s+ok|404\s+not\s+found|500\s+internal\s+(?:server\s+)?error)\b", re.IGNORECASE),
    # Academic Course Codes: CS 101, CS-50, CSE-401
    re.compile(r"\b(?:cs|cse|ece|it|math|phys|engg)[-_ ]?\d{2,4}\b", re.IGNORECASE),
]

# -----------------------------------------------------------------------------
# Impact Metric Pattern Definitions
# -----------------------------------------------------------------------------
# (Regex Pattern, Metric Type Label)
IMPACT_PATTERNS: List[Tuple[re.Pattern, str]] = [
    # 1. Percentages and Relative Improvements (e.g. 35%, 99.9%, 42.5 percent)
    (
        re.compile(r"\b\d+(?:\.\d+)?\s*(?:%|\bpercent\b)", re.IGNORECASE),
        "percentage",
    ),
    # 2. Speedup & Scaling Multipliers (e.g. 2.4x, 3x faster, 4-fold speedup)
    (
        re.compile(r"\b\d+(?:\.\d+)?\s*x(?!\w)(?:\s*(?:faster|speedup|reduction|increase|throughput|less))?", re.IGNORECASE),
        "speedup",
    ),
    (
        re.compile(r"\b\d+\s*-\s*fold\s*(?:increase|reduction|speedup|improvement)?\b", re.IGNORECASE),
        "speedup",
    ),
    # 3. Latency & Time Savings (e.g. 120ms, sub-20ms response, saved 15 hours/week)
    (
        re.compile(r"\b(?:sub[- ])?\d+(?:\.\d+)?\s*(?:ms|milliseconds|seconds|mins|minutes|hours)\b", re.IGNORECASE),
        "latency",
    ),
    (
        re.compile(r"\b(?:saved|reduced|cut|shaved)\s+[^.,\n]{1,30}?\s+by\s+\d+(?:\.\d+)?\s*(?:hours|days|weeks|ms|seconds)\b", re.IGNORECASE),
        "time_savings",
    ),
    # 4. User, Client, & Audience Scale (e.g. 200 students, 10,000+ users, 50k downloads)
    (
        re.compile(
            r"\b\d+(?:,\d{3})*\+?\s*(?:active\s+)?(?:users|students|clients|customers|visitors|participants|members|downloads|sessions|stars|forks|subscribers|tenants|accounts)\b",
            re.IGNORECASE,
        ),
        "user_scale",
    ),
    (
        re.compile(
            r"\b\d+(?:\.\d+)?\s*(?:k|m|million|thousand)\+?\s*(?:users|students|clients|customers|downloads|sessions|records)\b",
            re.IGNORECASE,
        ),
        "user_scale",
    ),
    # 5. Throughput & Data Volumes (e.g. 15,000 requests/sec, 500 QPS, 1.2M records)
    (
        re.compile(
            r"\b\d+(?:,\d{3})*\+?\s*(?:requests|events|transactions|messages|queries|calls|hits|tasks|jobs|qps|rps|ops|operations)\s*(?:per|\/)\s*(?:sec(?:ond)?|min(?:ute)?|hour|day)\b",
            re.IGNORECASE,
        ),
        "throughput",
    ),
    (
        re.compile(r"\b\d+(?:,\d{3})*\+?\s*(?:qps|rps|tps)\b", re.IGNORECASE),
        "throughput",
    ),
    (
        re.compile(
            r"\b\d+(?:\.\d+)?\s*(?:k|m|million|billion|gb|tb)\+?\s*(?:events|records|rows|data\s+points|documents|embeddings|tokens)\b",
            re.IGNORECASE,
        ),
        "data_volume",
    ),
    # 6. Accuracy, Benchmarks, & Competitive Ranks (e.g. 94.2% accuracy, 0.88 F1, top 1%, rank 12)
    (
        re.compile(
            r"\b\d+(?:\.\d+)?%\s*(?:accuracy|precision|recall|f1(?:-score)?|bleu|map|auc|roc|mrr)\b",
            re.IGNORECASE,
        ),
        "accuracy",
    ),
    (
        re.compile(
            r"\b(?:accuracy|precision|recall|f1(?:-score)?|bleu|map|auc|roc|mrr)\s*(?:of|reached|achieved|at|improved\s+to|equal\s+to)?\s*(?:to\s*)?\d+(?:\.\d+)?(?:%|\b)",
            re.IGNORECASE,
        ),
        "accuracy",
    ),
    (
        re.compile(
            r"\b(?:top\s+\d+%?|rank(?:ed)?\s+#?\d+|1st|2nd|3rd\s+place)\s*(?:out\s+of|\/)?\s*(?:\d+(?:,\d{3})*)?\b",
            re.IGNORECASE,
        ),
        "competitive_rank",
    ),
    # 7. Financial & Resource Savings / Volume (e.g. $200,000 in transactions, saved $5,000, cut memory by 40%)
    (
        re.compile(
            r"(?:[\$₹]|rs\.?|usd|eur)\s*\d+(?:,\d{3})*(?:\.\d+)?(?:\s*(?:in\s+)?(?:daily|monthly|annual|total)?\s*(?:transactions|revenue|sales|volume|spend|budget|savings|saved|cut))?",
            re.IGNORECASE,
        ),
        "cost_savings",
    ),
    (
        re.compile(
            r"\b(?:saving|reduced|cutting|saved)\s+\d+(?:\.\d+)?%\s*(?:memory|cpu|disk|bandwidth|storage|cost|cloud\s+spend)\b",
            re.IGNORECASE,
        ),
        "resource_savings",
    ),
]


def _is_covered_by_non_impact_filter(start: int, end: int, text: str) -> bool:
    """
    Check if a matched slice overlaps with an excluded non-impact pattern
    (e.g. year, port, version number).
    """
    for pattern in NON_IMPACT_NUMERIC_PATTERNS:
        for m in pattern.finditer(text):
            m_start, m_end = m.span()
            # Check overlap
            if not (end <= m_start or start >= m_end):
                return True
    return False


def detect_impact_metrics(text: str) -> List[ImpactMetricMatch]:
    """
    Identify and extract verifiable quantifiable outcomes and impact metrics from text,
    strictly ignoring version numbers, years, port numbers, and course codes.

    Args:
        text: Bullet point or description string.

    Returns:
        List of ImpactMetricMatch instances.
    """
    if not text or not text.strip():
        return []

    results: List[ImpactMetricMatch] = []
    seen_spans: Set[Tuple[int, int]] = set()

    for pattern, metric_type in IMPACT_PATTERNS:
        for m in pattern.finditer(text):
            start, end = m.span()

            # Check overlap with existing matches
            overlaps = any(
                not (end <= s or start >= e)
                for s, e in seen_spans
            )
            if overlaps:
                continue

            # Verify it is not an excluded non-impact numeric token
            if _is_covered_by_non_impact_filter(start, end, text):
                continue

            raw_matched = m.group(0).strip()

            # Extract window around match for explainable context
            ctx_start = max(0, start - 20)
            ctx_end = min(len(text), end + 20)
            context = text[ctx_start:ctx_end].strip()

            seen_spans.add((start, end))
            results.append(
                ImpactMetricMatch(
                    raw_match=raw_matched,
                    metric_type=metric_type,
                    context=context,
                )
            )

    return results


__all__ = [
    "NON_IMPACT_NUMERIC_PATTERNS",
    "IMPACT_PATTERNS",
    "detect_impact_metrics",
]
