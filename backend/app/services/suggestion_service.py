import re


class SuggestionService:

    def __init__(self):
        self.weak_verbs = [
            "helped",
            "worked on",
            "responsible for",
            "assisted",
            "participated",
            "involved in",
            "did",
            "made",
            "handled",
            "used",
        ]

        self.power_verbs = {
            "development": [
                "developed",
                "built",
                "created",
                "implemented",
                "designed",
                "engineered",
            ],
            "leadership": [
                "led",
                "managed",
                "coordinated",
                "mentored",
                "supervised",
            ],
            "achievement": [
                "achieved",
                "improved",
                "increased",
                "reduced",
                "optimized",
                "delivered",
            ],
            "analysis": [
                "analyzed",
                "evaluated",
                "researched",
                "identified",
                "investigated",
            ],
        }

        # Helper pattern: matches plain digits (500), decimals (99.9), 
        # comma-separated thousands (1,000 or 1,500,000), and optional '+' suffix (1,000+)
        num_pattern = r"(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?\+?"

        # Detect measurable impact metrics (excludes inventory counts like '3 projects').
        self.metric_pattern = re.compile(
            rf"""
            (?:
                \b{num_pattern}\s*%
                |
                \b{num_pattern}\s*(?:percent|percentage)\b
                |
                \b{num_pattern}\s*(?:x|times)\b
                |
                \b{num_pattern}\s*(?:k|m|million|billion)\b
                |
                \b{num_pattern}\s*(?:ms|milliseconds|seconds|minutes|hours|days|weeks|months|years)\b
                |
                \b{num_pattern}\s*(?:users|requests|records|queries|clients|customers|employees|transactions|downloads|stars)\b
            )
            """,
            re.IGNORECASE | re.VERBOSE
        )

    def analyze_bullet_point(self, bullet: str) -> dict:
        """Analyze a resume bullet point using STAR principles."""

        if not bullet or not bullet.strip():
            raise ValueError("Bullet point cannot be empty.")

        bullet = bullet.strip()
        lower_text = bullet.lower()

        # 1. Detect weak verbs.
        weak_verbs_found = [
            verb
            for verb in self.weak_verbs
            if re.search(
                r"\b" + re.escape(verb) + r"\b",
                lower_text
            )
        ]

        # 2. Collect all strong action verbs.
        all_power_verbs = [
            verb
            for verbs in self.power_verbs.values()
            for verb in verbs
        ]

        action_verb_used = None

        # Check whether the bullet starts with a strong action verb.
        for verb in all_power_verbs:
            if re.search(
                r"^\s*" + re.escape(verb) + r"\b",
                lower_text
            ):
                action_verb_used = verb
                break

        has_action_verb = action_verb_used is not None

        # 3. Detect quantified metrics.
        metric_match = self.metric_pattern.search(bullet)
        has_quantified_metric = metric_match is not None
        detected_metric = (
            metric_match.group(0).strip()
            if metric_match
            else None
        )

        # 4. Determine whether the bullet point is weak.
        is_weak = (
            bool(weak_verbs_found)
            or not has_action_verb
            or not has_quantified_metric
        )

        # 5. Generate improvement suggestions.
        if weak_verbs_found:
            suggestion = (
                "Replace weak verbs such as "
                + ", ".join(weak_verbs_found)
                + " with stronger action verbs."
            )
        elif not has_action_verb:
            suggestion = (
                "Start the bullet point with a strong action verb "
                "such as Developed, Implemented, or Improved."
            )
        elif not has_quantified_metric:
            suggestion = (
                "Add measurable results such as percentages, "
                "numbers, or time saved to demonstrate impact."
            )
        else:
            suggestion = (
                "Good bullet point. Consider adding more context "
                "about the task and its impact."
            )

        star_template_example = (
            "Action verb + Task/Project + Method/Technology "
            "+ Measurable Result"
        )

        return {
            "original_text": bullet,
            "is_weak": is_weak,
            "weak_verbs_found": weak_verbs_found,
            "has_action_verb": has_action_verb,
            "action_verb_used": action_verb_used,
            "has_quantified_metric": has_quantified_metric,
            "detected_metric": detected_metric,
            "suggestion": suggestion,
            "star_template_example": star_template_example,
        }

    def generate_resume_suggestions(
        self,
        extracted_skills: dict,
        raw_text: str,
        weak_areas: list = None
    ) -> list:
        """Generate contextual resume improvement suggestions."""

        suggestions = []

        technical_skills = extracted_skills.get(
            "technical_skills", []
        )
        soft_skills = extracted_skills.get(
            "soft_skills", []
        )

        # Technical skills check.
        if len(technical_skills) < 5:
            suggestions.append({
                "section": "Skills",
                "priority": "High",
                "issue": "Limited technical skills listed.",
                "recommendation": (
                    "Consider adding more relevant technical skills "
                    "based on your projects and target job roles."
                ),
            })

        # Soft skills check.
        if len(soft_skills) == 0:
            suggestions.append({
                "section": "Skills",
                "priority": "Medium",
                "issue": "No soft skills detected.",
                "recommendation": (
                    "Include relevant soft skills such as "
                    "communication, teamwork, and problem-solving "
                    "where supported by your experience."
                ),
            })

        # Weak action verbs check.
        lines = raw_text.split("\n")
        weak_bullet_count = 0

        for line in lines:
            if any(
                re.search(
                    r"\b" + re.escape(verb) + r"\b",
                    line.lower()
                )
                for verb in self.weak_verbs
            ):
                weak_bullet_count += 1

        if weak_bullet_count > 0:
            suggestions.append({
                "section": "Experience / Projects",
                "priority": "High",
                "issue": (
                    f"{weak_bullet_count} bullet points contain "
                    "weak action verbs."
                ),
                "recommendation": (
                    "Rewrite these bullet points using strong action "
                    "verbs and measurable achievements."
                ),
            })

        # Institutional email check.
        if "@dau.ac.in" not in raw_text.lower():
            suggestions.append({
                "section": "Contact Information",
                "priority": "Low",
                "issue": "Institutional email not detected.",
                "recommendation": (
                    "Consider including your college email address "
                    "for professional communication."
                ),
            })

        # GitHub profile check.
        if "github.com" not in raw_text.lower():
            suggestions.append({
                "section": "Projects",
                "priority": "Medium",
                "issue": "GitHub profile link not detected.",
                "recommendation": (
                    "Add your GitHub profile or relevant repository "
                    "links to showcase your projects."
                ),
            })

        # External weak areas.
        if weak_areas:
            for area in weak_areas:
                suggestions.append({
                    "section": area.get("section", "General"),
                    "priority": area.get("priority", "Medium"),
                    "issue": area.get("issue", ""),
                    "recommendation": area.get(
                        "remediation",
                        "Review and improve this section."
                    ),
                })

        return suggestions
