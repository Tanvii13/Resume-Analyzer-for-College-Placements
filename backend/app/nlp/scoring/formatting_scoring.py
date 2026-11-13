"""
Formatting and readability evaluator for Sprint 3 Module A.

Evaluates:
- Section heading consistency and organization.
- Bullet point structuring versus unstructured walls of text.
- Detectable formatting anomalies (excessive whitespace, broken lines).
- Machine extractability and ATS readability signals (confidence, parsing warnings).

Guarantees:
- Completely deterministic rule-based evaluation.
- Does not claim to inspect visual layout unavailable in extracted text.
- Personal attributes NEVER affect score.
"""

import re
from typing import List, Set, Tuple
from app.nlp.schemas import CandidateProfile, ConfidenceLevel
from app.nlp.scoring.schemas import ComponentScore, ScoreDeduction
from app.nlp.scoring.weights import COMPONENT_FORMATTING_READABILITY


class FormattingReadabilityScorer:
    """Evaluates resume structure, bullet point formatting, and ATS extractability."""

    def __init__(self, max_score: float = 18.75):
        self.max_score = max_score

    def score(self, profile: CandidateProfile) -> Tuple[ComponentScore, List[ScoreDeduction], List[str]]:
        earned_score = 0.0
        deductions: List[ScoreDeduction] = []
        strengths: List[str] = []
        evidence: List[str] = []
        improvements: List[str] = []

        # ---------------------------------------------------------------------
        # 1. Section Structure and Heading Organization (35% of max_score)
        # ---------------------------------------------------------------------
        sec_weight = self.max_score * 0.35
        identified_sections = profile.section_summary.identified_sections or []
        num_sections = len(identified_sections)

        if num_sections >= 4:
            sec_score = sec_weight
            evidence.append(f"Well-structured resume with {num_sections} clearly delineated sections ({', '.join(identified_sections[:4])}).")
            strengths.append(f"Clear document architecture with {num_sections} identifiable standard resume sections.")
        elif num_sections == 3:
            sec_score = sec_weight * 0.75
            evidence.append(f"Recognized {num_sections} sections: {', '.join(identified_sections)}.")
            improvements.append("Ensure distinct section headings (e.g. 'Education', 'Projects', 'Technical Skills', 'Experience').")
        elif num_sections == 2:
            sec_score = sec_weight * 0.50
            evidence.append(f"Recognized only {num_sections} sections: {', '.join(identified_sections)}.")
            deductions.append(
                ScoreDeduction(
                    component=COMPONENT_FORMATTING_READABILITY,
                    rule_id="FMT_FEW_SECTIONS",
                    points_deducted=round(sec_weight * 0.50, 2),
                    reason=f"Only {num_sections} standard sections identified. Use standard headings for clarity.",
                    evidence=f"Sections found: {', '.join(identified_sections)}",
                )
            )
            improvements.append("Organize content into standard placement sections: Education, Skills, Projects, Experience.")
        elif num_sections == 1:
            sec_score = sec_weight * 0.20
            deductions.append(
                ScoreDeduction(
                    component=COMPONENT_FORMATTING_READABILITY,
                    rule_id="FMT_POOR_SEGMENTATION",
                    points_deducted=round(sec_weight * 0.80, 2),
                    reason="Only 1 section recognized. Resume appears as an unsegmented document.",
                    evidence=f"Single section found: {identified_sections[0]}",
                )
            )
            improvements.append("Use standard, prominent uppercase or bold section headers so ATS parsers can segment your resume.")
        else:
            sec_score = 0.0
            deductions.append(
                ScoreDeduction(
                    component=COMPONENT_FORMATTING_READABILITY,
                    rule_id="FMT_NO_SECTIONS_IDENTIFIED",
                    points_deducted=round(sec_weight, 2),
                    reason="No standard section headings could be confidently recognized.",
                    evidence="identified_sections list is empty",
                )
            )
            improvements.append("Add explicit standard section headers (EDUCATION, TECHNICAL SKILLS, PROJECTS, EXPERIENCE).")

        # Check for missing critical section boundaries
        missing_crit = profile.section_summary.missing_critical_sections or []
        if missing_crit and num_sections > 0:
            crit_penalty = min(2.0, len(missing_crit) * 0.60)
            sec_score = max(0.0, sec_score - crit_penalty)
            deductions.append(
                ScoreDeduction(
                    component=COMPONENT_FORMATTING_READABILITY,
                    rule_id="FMT_AMBIGUOUS_SECTION_BOUNDARIES",
                    points_deducted=round(crit_penalty, 2),
                    reason=f"Missing explicit boundaries for core sections: {', '.join(missing_crit)}.",
                    evidence=f"Missing critical sections: {', '.join(missing_crit)}",
                )
            )

        earned_score += sec_score

        # ---------------------------------------------------------------------
        # 2. Bullet Point Formatting & Text Density (35% of max_score)
        # ---------------------------------------------------------------------
        bullet_weight = self.max_score * 0.35

        # Gather bullet items from projects and experience
        all_bullet_items: List[str] = []
        raw_text_blocks: List[str] = []

        for p in (profile.projects or []):
            if p.highlights:
                all_bullet_items.extend(p.highlights)
            if p.description:
                all_bullet_items.append(p.description)
            if p.raw_text:
                raw_text_blocks.append(p.raw_text)

        for exp in (profile.experience or []):
            if exp.responsibilities:
                all_bullet_items.extend(exp.responsibilities)
            if exp.raw_text:
                raw_text_blocks.append(exp.raw_text)

        for exp in (profile.internships or []):
            if exp.responsibilities:
                all_bullet_items.extend(exp.responsibilities)
            if exp.raw_text:
                raw_text_blocks.append(exp.raw_text)

        for edu in (profile.education or []):
            if edu.raw_text:
                raw_text_blocks.append(edu.raw_text)

        # Check for walls of text (>120 words in a single block without linebreaks)
        wall_of_text_detected = False
        excessive_whitespace_detected = False

        for block in raw_text_blocks + all_bullet_items:
            # Word count in single continuous paragraph
            paragraphs = [p.strip() for p in block.split("\n") if p.strip()]
            for para in paragraphs:
                word_count = len(para.split())
                if word_count > 120:
                    wall_of_text_detected = True
                    break

            # Check excessive blank lines (e.g. 4+ empty lines in sequence)
            if re.search(r"(?:\r?\n\s*){4,}", block):
                excessive_whitespace_detected = True

        has_entries = bool(profile.projects or profile.experience or profile.internships)

        if not has_entries:
            # Neutral credit for empty/fresher profile with guidance
            bullet_score = bullet_weight * 0.40
            improvements.append("Use concise bullet points (15-30 words each) when writing project and experience descriptions.")
        else:
            total_bullets = len(all_bullet_items)
            if total_bullets >= 4 and not wall_of_text_detected:
                bullet_score = bullet_weight
                evidence.append(f"Effective bullet-point formatting ({total_bullets} structured bullet items detected).")
                strengths.append("Information is cleanly formatted into concise, readable bullet points.")
            elif total_bullets >= 2:
                bullet_score = bullet_weight * 0.70
                evidence.append(f"Moderate bullet usage ({total_bullets} items).")
                improvements.append("Structure each project and experience with 2-4 distinct bullet points.")
            else:
                bullet_score = bullet_weight * 0.40
                deductions.append(
                    ScoreDeduction(
                        component=COMPONENT_FORMATTING_READABILITY,
                        rule_id="FMT_FEW_BULLETS",
                        points_deducted=round(bullet_weight * 0.60, 2),
                        reason="Descriptions lack bullet point structure, making content harder to scan quickly.",
                        evidence=f"Detected {total_bullets} bullet items across all projects and experience",
                    )
                )
                improvements.append("Format all project and role descriptions as bullet points starting with action verbs.")

            if wall_of_text_detected:
                wall_penalty = min(2.5, bullet_weight * 0.35)
                bullet_score = max(0.0, bullet_score - wall_penalty)
                deductions.append(
                    ScoreDeduction(
                        component=COMPONENT_FORMATTING_READABILITY,
                        rule_id="FMT_WALL_OF_TEXT",
                        points_deducted=round(wall_penalty, 2),
                        reason="Unstructured wall of text detected (>120 words without breaks). Recruiters skim in seconds; break into bullet points.",
                        evidence="Paragraph exceeding 120 words detected in descriptions",
                    )
                )
                improvements.append("Break dense paragraphs into bullet points highlighting specific actions and results.")

            if excessive_whitespace_detected:
                ws_penalty = 1.0
                bullet_score = max(0.0, bullet_score - ws_penalty)
                deductions.append(
                    ScoreDeduction(
                        component=COMPONENT_FORMATTING_READABILITY,
                        rule_id="FMT_EXCESSIVE_WHITESPACE",
                        points_deducted=ws_penalty,
                        reason="Excessive blank lines or whitespace gaps detected, reducing resume page efficiency.",
                        evidence="Repetitive blank line patterns found in text",
                    )
                )
                improvements.append("Eliminate redundant blank lines and maintain consistent 1-line paragraph spacing.")

        earned_score += bullet_score

        # ---------------------------------------------------------------------
        # 3. Extractability and ATS Machine-Readability Signals (30% of max_score)
        # ---------------------------------------------------------------------
        ats_weight = self.max_score * 0.30
        metadata = profile.metadata
        overall_conf = metadata.overall_confidence if metadata else 1.0
        warnings = metadata.warnings if metadata else []

        if overall_conf >= 0.85 or (metadata and metadata.confidence_level == ConfidenceLevel.HIGH):
            ats_score = ats_weight
            evidence.append(f"High ATS extractability signal (confidence: {overall_conf:.2f}).")
            strengths.append("High machine readability; clean layout allows accurate automated parsing.")
        elif overall_conf >= 0.60 or (metadata and metadata.confidence_level == ConfidenceLevel.MEDIUM):
            ats_score = ats_weight * 0.70
            evidence.append(f"Moderate ATS extractability signal (confidence: {overall_conf:.2f}).")
            improvements.append("Use standard single-column formatting and standard fonts to ensure perfect ATS parsing.")
        else:
            ats_score = ats_weight * 0.40
            deductions.append(
                ScoreDeduction(
                    component=COMPONENT_FORMATTING_READABILITY,
                    rule_id="FMT_LOW_ATS_CONFIDENCE",
                    points_deducted=round(ats_weight * 0.60, 2),
                    reason=f"Low automated extraction confidence ({overall_conf:.2f}). Multi-column layouts, tables, or complex formatting may confuse ATS systems.",
                    evidence=f"Pipeline extraction confidence: {overall_conf:.2f}",
                )
            )
            improvements.append("Switch to a clean single-column layout without tables, graphics, or nested text boxes.")

        # Check parsing warnings
        if warnings:
            warn_penalty = min(2.0, len(warnings) * 0.75)
            ats_score = max(0.0, ats_score - warn_penalty)
            deductions.append(
                ScoreDeduction(
                    component=COMPONENT_FORMATTING_READABILITY,
                    rule_id="FMT_EXTRACTION_WARNINGS",
                    points_deducted=round(warn_penalty, 2),
                    reason=f"Pipeline encountered {len(warnings)} formatting anomalies during extraction.",
                    evidence=f"Warnings: {'; '.join(warnings[:2])}",
                )
            )
            improvements.append("Resolve formatting issues such as non-standard characters, unusual bullet symbols, or table artifacts.")

        earned_score += ats_score

        # Final Clamp
        final_score = round(max(0.0, min(self.max_score, earned_score)), 2)

        # Generate summary reason
        if final_score >= self.max_score * 0.85:
            reason = f"Excellent formatting and readability ({final_score:.1f}/{self.max_score:.1f}). Clear sections, concise bullets, and high ATS compatibility."
        elif final_score >= self.max_score * 0.65:
            reason = f"Good formatting and readability ({final_score:.1f}/{self.max_score:.1f}). Readable layout; minor improvements in bullet structure recommended."
        elif final_score >= self.max_score * 0.40:
            reason = f"Fair formatting and readability ({final_score:.1f}/{self.max_score:.1f}). Inconsistent headings or long text blocks impact scan speed."
        else:
            reason = f"Formatting needs improvement ({final_score:.1f}/{self.max_score:.1f}). Missing clear section boundaries or poor ATS extractability."

        component_score = ComponentScore(
            component=COMPONENT_FORMATTING_READABILITY,
            score=final_score,
            max_score=self.max_score,
            weight=self.max_score,
            evidence=evidence,
            reason=reason,
            how_to_improve=improvements,
        )

        return component_score, deductions, strengths
