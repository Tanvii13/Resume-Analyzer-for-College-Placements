"""
Content quality evaluator for Sprint 3 Module A.

Evaluates:
- Presence of meaningful technical action verbs (e.g., Developed, Engineered, Optimized).
- Detection of measurable outcomes and quantified metrics (e.g., 30%, 10k users, 120ms).
- Project and experience description depth, specificity, and technical clarity.
- Avoidance of passive, vague phrases (e.g., "worked on", "responsible for").

Guarantees:
- Completely deterministic regex-based signal detection.
- Does not reward fabricated metrics; checks only candidate-provided text.
"""

import re
from typing import List, Set, Tuple
from app.nlp.schemas import CandidateProfile
from app.nlp.scoring.schemas import ComponentScore, ScoreDeduction
from app.nlp.scoring.weights import COMPONENT_CONTENT_QUALITY

# Strong technical and leadership action verbs
STRONG_ACTION_VERBS = {
    "develop", "developed", "developing",
    "build", "built", "building",
    "engineer", "engineered", "engineering",
    "design", "designed", "designing",
    "implement", "implemented", "implementing",
    "optimize", "optimized", "optimizing",
    "architect", "architected", "architecting",
    "automate", "automated", "automating",
    "orchestrate", "orchestrated", "orchestrating",
    "lead", "led", "leading",
    "spearhead", "spearheaded", "spearheading",
    "analyze", "analyzed", "analyzing",
    "create", "created", "creating",
    "integrate", "integrated", "integrating",
    "deploy", "deployed", "deploying",
    "resolve", "resolved", "resolving",
    "enhance", "enhanced", "enhancing",
    "reduce", "reduced", "reducing",
    "increase", "increased", "increasing",
    "maintain", "maintained", "maintaining",
    "configure", "configured", "configuring",
    "train", "trained", "training",
    "evaluate", "evaluated", "evaluating",
    "construct", "constructed", "constructing",
    "accelerate", "accelerated", "accelerating",
    "refactor", "refactored", "refactoring",
    "devise", "devised", "devising",
    "benchmark", "benchmarked", "benchmarking",
}

# Weak, passive, or vague introductory phrases
WEAK_PHRASES = [
    r"\bworked\s+on\b",
    r"\bhelped\s+with\b",
    r"\bresponsible\s+for\b",
    r"\bassisted\s+(?:in|with)\b",
    r"\bparticipated\s+in\b",
    r"\bhandled\b",
]

# Quantified outcome patterns (percentages, scale, speed, benchmarks)
METRIC_PATTERNS = [
    re.compile(r"\b\d+(?:\.\d+)?%\b", re.IGNORECASE),                               # 25%, 99.9%
    re.compile(r"\b\d+\s*(?:x|fold)\s+(?:faster|speedup|reduction|increase)\b", re.IGNORECASE), # 3x faster
    re.compile(r"\b(?:reduced|improved|increased|boosted|saved|cut)\s+[^.,\n]{1,30}?\s+(?:by\s+)?\d+(?:\.\d+)?%?\b", re.IGNORECASE),
    re.compile(r"\b\d+(?:,\d{3})+\b", re.IGNORECASE),                               # 10,000, 100,000
    re.compile(r"\b\d+\+?\s*(?:users|clients|requests|qps|queries|rps|downloads|stars|records)\b", re.IGNORECASE), # 500+ users
    re.compile(r"\b\d+(?:\.\d+)?\s*(?:ms|milliseconds|seconds|minutes)\b", re.IGNORECASE), # 150ms
    re.compile(r"\b(?:top\s+\d+%?|rank(?:ed)?\s+#?\d+|1st|2nd|3rd\s+place)\b", re.IGNORECASE), # top 5%, rank 12
]


class ContentQualityScorer:
    """Evaluates the linguistic strength, action orientation, and quantified impact of resume text."""

    def __init__(self, max_score: float = 31.25):
        self.max_score = max_score

    def score(self, profile: CandidateProfile) -> Tuple[ComponentScore, List[ScoreDeduction], List[str]]:
        earned_score = 0.0
        deductions: List[ScoreDeduction] = []
        strengths: List[str] = []
        evidence: List[str] = []
        improvements: List[str] = []

        # Collect all project and experience bullet/text segments
        text_segments: List[str] = []
        for p in profile.projects:
            if p.title:
                text_segments.append(p.title)
            if p.description:
                text_segments.append(p.description)
            for h in p.highlights:
                text_segments.append(h)
            if p.raw_text:
                text_segments.append(p.raw_text)

        for exp in profile.experience + profile.internships:
            if exp.job_title:
                text_segments.append(exp.job_title)
            for r in exp.responsibilities:
                text_segments.append(r)
            if exp.raw_text:
                text_segments.append(exp.raw_text)

        combined_text = " ".join(text_segments).lower()

        # ---------------------------------------------------------------------
        # 1. Action Verbs Evaluation (30% of max_score)
        # ---------------------------------------------------------------------
        verb_weight = self.max_score * 0.30
        words = set(re.findall(r"\b[a-z]{3,}\b", combined_text))
        matched_verbs: Set[str] = words.intersection(STRONG_ACTION_VERBS)

        matched_weak: List[str] = []
        for wp in WEAK_PHRASES:
            found = re.findall(wp, combined_text, re.IGNORECASE)
            matched_weak.extend(found)

        num_verbs = len(matched_verbs)
        if num_verbs >= 5:
            verb_fraction = 1.0
        elif num_verbs >= 3:
            verb_fraction = 0.80
        elif num_verbs >= 1:
            verb_fraction = 0.50
        else:
            verb_fraction = 0.15

        # Slight penalty if weak phrases dominate
        if matched_weak and verb_fraction > 0.20:
            verb_fraction = max(0.20, verb_fraction - 0.15)

        verb_points = verb_weight * verb_fraction
        earned_score += verb_points

        if num_verbs >= 3:
            sample_verbs = sorted(list(matched_verbs))[:5]
            evidence.append(f"Strong action verbs identified ({num_verbs} distinct): {', '.join(sample_verbs)}.")
            strengths.append(f"Demonstrates action-oriented communication using verbs like {', '.join(sample_verbs[:3])}.")
        else:
            ded_pts = round(verb_weight * (1.0 - verb_fraction), 2)
            deductions.append(
                ScoreDeduction(
                    component=COMPONENT_CONTENT_QUALITY,
                    rule_id="CONTENT_FEW_ACTION_VERBS",
                    points_deducted=ded_pts,
                    reason="Few or no strong action verbs detected in descriptions.",
                    evidence=f"Identified {num_verbs} action verbs across project/experience bullets.",
                )
            )
            improvements.append("Begin project and work experience bullets with strong action verbs (e.g. 'Engineered', 'Optimized', 'Automated').")

        if matched_weak:
            ded_pts = round(min(verb_weight * 0.20, 1.5), 2)
            deductions.append(
                ScoreDeduction(
                    component=COMPONENT_CONTENT_QUALITY,
                    rule_id="CONTENT_WEAK_PHRASES",
                    points_deducted=ded_pts,
                    reason=f"Found passive or vague phrasing ({len(matched_weak)} instance(s)): {', '.join(matched_weak[:2])}.",
                    evidence=f"Passive phrasing matched: {', '.join(matched_weak[:3])}",
                )
            )
            improvements.append("Replace passive phrases like 'worked on' or 'responsible for' with active contributions (e.g. 'Built', 'Implemented').")

        # ---------------------------------------------------------------------
        # 2. Measurable Outcomes & Metrics (35% of max_score)
        # ---------------------------------------------------------------------
        metric_weight = self.max_score * 0.35
        detected_metrics: List[str] = []

        for pat in METRIC_PATTERNS:
            matches = pat.findall(combined_text)
            detected_metrics.extend(matches)

        # Deduplicate while preserving order
        unique_metrics = list(dict.fromkeys([m.strip() for m in detected_metrics if isinstance(m, str)]))
        num_metrics = len(unique_metrics)

        if num_metrics >= 3:
            metric_fraction = 1.0
        elif num_metrics >= 2:
            metric_fraction = 0.85
        elif num_metrics == 1:
            metric_fraction = 0.55
        else:
            metric_fraction = 0.10

        metric_points = metric_weight * metric_fraction
        earned_score += metric_points

        if num_metrics >= 1:
            sample_m = unique_metrics[:4]
            evidence.append(f"Measurable outcomes and metrics verified ({num_metrics} found): {', '.join(sample_m)}.")
            strengths.append(f"Quantifies impact with measurable metrics (e.g. {', '.join(sample_m[:2])}).")
        else:
            ded_pts = round(metric_weight * (1.0 - metric_fraction), 2)
            deductions.append(
                ScoreDeduction(
                    component=COMPONENT_CONTENT_QUALITY,
                    rule_id="CONTENT_NO_METRICS",
                    points_deducted=ded_pts,
                    reason="No measurable quantitative outcomes (percentages, speedups, user scale) detected.",
                    evidence="No metrics matching percentage, scale, or benchmark patterns found.",
                )
            )
            improvements.append("Quantify project results using STAR format (e.g., 'reduced API response time by 35%', 'handled 5,000+ daily requests').")

        # ---------------------------------------------------------------------
        # 3. Project Depth & Technical Specificity (35% of max_score)
        # ---------------------------------------------------------------------
        depth_weight = self.max_score * 0.35
        projects = profile.projects

        if not projects:
            # 0 projects
            depth_points = 0.0
            deductions.append(
                ScoreDeduction(
                    component=COMPONENT_CONTENT_QUALITY,
                    rule_id="CONTENT_NO_PROJECT_DEPTH",
                    points_deducted=round(depth_weight, 2),
                    reason="No projects available to evaluate content depth.",
                    evidence="profile.projects is empty.",
                )
            )
        else:
            qualifying_projects = 0
            projects_with_tech = 0
            projects_with_links = 0

            for p in projects:
                p_text = f"{p.title or ''} {p.description or ''} {' '.join(p.highlights)}"
                word_count = len(re.findall(r"\b\w+\b", p_text))
                if word_count >= 15 or len(p.highlights) >= 2:
                    qualifying_projects += 1
                if p.technologies:
                    projects_with_tech += 1
                if p.project_url or p.github_url:
                    projects_with_links += 1

            depth_ratio = qualifying_projects / len(projects)
            tech_ratio = projects_with_tech / len(projects)

            combined_ratio = (depth_ratio * 0.6) + (tech_ratio * 0.4)
            depth_points = depth_weight * min(1.0, combined_ratio)
            earned_score += depth_points

            if qualifying_projects >= 2 and projects_with_tech >= 2:
                evidence.append(f"Project entries demonstrate detailed implementation descriptions and mapped technologies ({qualifying_projects} detailed projects).")
                strengths.append("Project descriptions provide solid technical depth with clear architecture and tool attribution.")
            elif qualifying_projects == 0:
                ded_pts = round(depth_weight * 0.50, 2)
                deductions.append(
                    ScoreDeduction(
                        component=COMPONENT_CONTENT_QUALITY,
                        rule_id="CONTENT_SHALLOW_PROJECTS",
                        points_deducted=ded_pts,
                        reason="Project descriptions are brief or lack technical depth (<15 words).",
                        evidence=f"Evaluated {len(projects)} project(s); none met depth threshold.",
                    )
                )
                improvements.append("Expand project descriptions with details about your architecture, database design, and key technical challenges.")

            if projects_with_links >= 1:
                evidence.append("Interactive repository or deployment links provide verifiable project evidence.")
                strengths.append("Provides clickable GitHub repository or live deployment links for applied projects.")

        final_score = round(max(0.0, min(self.max_score, earned_score)), 2)
        reason = (
            f"Content quality earned {final_score}/{self.max_score} points. "
            f"Evaluated {num_verbs} action verbs, {num_metrics} quantified metrics, and {len(projects)} project descriptions."
        )

        return (
            ComponentScore(
                component=COMPONENT_CONTENT_QUALITY,
                score=final_score,
                max_score=self.max_score,
                weight=self.max_score,
                evidence=evidence,
                reason=reason,
                how_to_improve=improvements,
            ),
            deductions,
            strengths,
        )


__all__ = ["ContentQualityScorer", "STRONG_ACTION_VERBS"]
