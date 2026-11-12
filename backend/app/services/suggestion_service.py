
import re
from typing import Dict, List, Any, Optional


class SuggestionService:
    def __init__(self):
        # Weak, passive, and vague verbs to discourage
        self.weak_verbs = [
            "worked on", "helped in", "helped with", "responsible for",
            "handled", "did", "assisted", "involved in",
            "participated in", "supported", "contributed to",
            "looked after", "tried to", "made", "used"
        ]

        # Categorized power action verbs for STAR/XYZ recommendations
        self.power_verbs = {
            "creation": [
                "Engineered", "Architected", "Developed",
                "Implemented", "Constructed", "Authored"
            ],
            "optimization": [
                "Optimized", "Accelerated", "Streamlined",
                "Automated", "Refactored", "Enhanced"
            ],
            "leadership": [
                "Spearheaded", "Directed", "Orchestrated",
                "Led", "Coordinated", "Mentored"
            ],
            "analysis": [
                "Evaluated", "Benchmarked", "Diagnosed",
                "Surveyed", "Investigated"
            ]
        }

        # Regex for numbers, percentages, durations, and metrics
        self.metric_pattern = re.compile(
            r'(\b\d+(\.\d+)?%|\b\d+x\b|'
            r'\b\d+\s*(ms|seconds|minutes|hours|days|weeks|months)\b|'
            r'\b\d+\s*(users|requests|records|queries|qps|stars|downloads|clients)\b|'
            r'\b\d+\s*(k|m|gb|mb|tb)\b)',
            re.IGNORECASE
        )

    def analyze_bullet_point(self, bullet: str) -> Dict[str, Any]:
        """
        Analyzes a single resume bullet point against the STAR/XYZ formula.
        """
        clean_text = bullet.strip()
        lower_text = clean_text.lower()

        # 1. Detect weak verbs
        weak_found = [
            wv for wv in self.weak_verbs
            if re.search(r'\b' + re.escape(wv) + r'\b', lower_text)
        ]

        # 2. Check for strong action verbs
        has_power_verb = False
        detected_power_verb = None

        for category, verbs in self.power_verbs.items():
            for pv in verbs:
                if re.search(
                    r'^\s*' + re.escape(pv),
                    clean_text,
                    re.IGNORECASE
                ):
                    has_power_verb = True
                    detected_power_verb = pv
                    break

            if has_power_verb:
                break

        # 3. Detect quantifiable metrics
        metric_match = self.metric_pattern.search(clean_text)
        has_metric = bool(metric_match)
        detected_metric = metric_match.group(0) if metric_match else None

        # 4. Determine overall weakness
        is_weak = (
            bool(weak_found)
            or (not has_power_verb)
            or (not has_metric)
        )

        # 5. Generate actionable suggestions
        suggestions = []

        if weak_found:
            replacement_verbs = ", ".join(
                [f"'{v}'" for v in self.power_verbs["creation"][:3]]
            )
            suggestions.append(
                f"Replace passive phrase '{weak_found[0]}' "
                f"with an impactful action verb such as {replacement_verbs}."
            )

        elif not has_power_verb:
            suggestions.append(
                "Begin your bullet point with a decisive action verb "
                "(e.g., 'Engineered', 'Architected', 'Optimized')."
            )

        if not has_metric:
            suggestions.append(
                "Add a quantifiable metric (e.g., latency reduction %, "
                "user scale, or queries handled) to prove measurable impact."
            )

        final_suggestion = (
            " ".join(suggestions)
            if suggestions
            else "Strong, impactful bullet point following the STAR format."
        )

        # 6. Build practical STAR template example
        star_template = (
            "Template: [Strong Action Verb] + "
            "[Specific Task / Technology] + [Result / Metric]. "
            "Example: 'Optimized PostgreSQL queries in FastAPI backend, "
            "reducing response time by 42% for 1,000+ daily active users.'"
        )

        return {
            "original_text": clean_text,
            "is_weak": is_weak,
            "weak_verbs_found": weak_found,
            "has_action_verb": has_power_verb,
            "action_verb_used": detected_power_verb,
            "has_quantified_metric": has_metric,
            "detected_metric": detected_metric,
            "suggestion": final_suggestion,
            "star_template_example": star_template
        }

    def generate_resume_suggestions(
        self,
        extracted_skills: Dict[str, List[str]],
        raw_text: str,
        weak_areas: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """
        Generates holistic and relevant resume improvement suggestions.
        """
        suggestions = []

        # A. Skills Section Feedback
        tech_skills = extracted_skills.get("technical_skills", [])
        soft_skills = extracted_skills.get("soft_skills", [])

        if len(tech_skills) < 5:
            suggestions.append({
                "section": "Skills",
                "priority": "High",
                "issue": "Low technical skill density detected (fewer than 5 skills).",
                "recommendation": (
                    "List core programming languages, frameworks, databases, "
                    "and development tools you have used in projects."
                )
            })

        elif len(soft_skills) == 0:
            suggestions.append({
                "section": "Skills",
                "priority": "Medium",
                "issue": "No soft skills or interpersonal competencies detected.",
                "recommendation": (
                    "Incorporate key competencies such as 'Problem Solving', "
                    "'Team Leadership', or 'Agile Collaboration' naturally "
                    "into your project descriptions."
                )
            })

        # B. Project Section Impact Check
        lines = [
            line.strip()
            for line in raw_text.split("\n")
            if len(line.strip()) > 30
        ]

        weak_bullet_count = 0

        for line in lines[:20]:
            if any(wv in line.lower() for wv in self.weak_verbs):
                weak_bullet_count += 1

        if weak_bullet_count > 0:
            suggestions.append({
                "section": "Projects & Experience",
                "priority": "High",
                "issue": (
                    f"Detected {weak_bullet_count} bullet points "
                    "using passive or weak wording."
                ),
                "recommendation": (
                    "Revise descriptions using the STAR formula: "
                    "Start with an action verb (Engineered, Implemented) "
                    "and quantify results with numbers or percentages."
                )
            })

        # C. Contact Information Check
        if "@dau.ac.in" not in raw_text.lower() and "@" in raw_text:
            suggestions.append({
                "section": "Contact Information",
                "priority": "Medium",
                "issue": (
                    "Personal email used instead of institutional college email."
                ),
                "recommendation": (
                    "For college placement registration, include your official "
                    "institutional email (@dau.ac.in) alongside your primary email."
                )
            })

        # D. Online Profiles Check
        if "github.com" not in raw_text.lower():
            suggestions.append({
                "section": "Online Profiles",
                "priority": "High",
                "issue": "GitHub profile link not found in resume.",
                "recommendation": (
                    "Add a clickable link to your active GitHub profile "
                    "displaying personal and academic project repositories."
                )
            })

        # E. External Weak Areas
        if weak_areas:
            for wa in weak_areas:
                suggestions.append({
                    "section": wa.get("section", "General"),
                    "priority": wa.get("priority", "Medium"),
                    "issue": wa.get("issue", "Identified defect in section."),
                    "recommendation": wa.get(
                        "remediation",
                        "Review and revise according to placement guidelines."
                    )
                })

        return suggestions
