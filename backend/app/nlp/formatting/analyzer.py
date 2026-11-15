"""
Formatting Quality Analyzer orchestrator for Sprint 3 Module B.

Provides:
- FormattingQualityAnalyzer: Standalone NLP service evaluating resume formatting and readability.
- analyze_formatting: Top-level convenience evaluation function.

Guarantees:
- Completely deterministic rule-based analysis.
- Consumes extracted text, Sprint 1 ResumeParseResult, and/or Sprint 2 CandidateProfile.
- Independent of scoring engine (no circular dependencies).
- Does not inspect inaccessible visual styling (fonts, margins, colors).
"""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel
from app.nlp.formatting.limitations import DEFAULT_ANALYZER_LIMITATIONS
from app.nlp.formatting.rules import (
    BulletStructureChecker,
    ResumeConsistencyChecker,
    SectionStructureChecker,
    TextReadabilityChecker,
)
from app.nlp.formatting.schemas import (
    FORMATTING_ANALYZER_VERSION,
    FindingSeverity,
    FormattingAnalysisResult,
    FormattingCategory,
    FormattingFinding,
)
from app.nlp.preprocessing import segment_text
from app.nlp.schemas import CandidateProfile
from app.nlp.sections import classify_sections


class FormattingQualityAnalyzer:
    """
    Evaluates resume formatting, readability, bullet structures, and cross-document consistency.
    """

    def __init__(self, version: str = FORMATTING_ANALYZER_VERSION):
        self.version = version
        self.section_checker = SectionStructureChecker()
        self.readability_checker = TextReadabilityChecker()
        self.bullet_checker = BulletStructureChecker()
        self.consistency_checker = ResumeConsistencyChecker()

    def analyze(
        self,
        text_or_result: Union[str, Any],
        profile: Optional[CandidateProfile] = None,
    ) -> FormattingAnalysisResult:
        """
        Analyze formatting quality from raw text or a ResumeParseResult object.

        Args:
            text_or_result: Raw string of resume text, or a Sprint 1 ResumeParseResult.
            profile: Optional Sprint 2 CandidateProfile for cross-referencing extracted sections.

        Returns:
            FormattingAnalysisResult containing score, itemized findings, strengths,
            documented limitations, and diagnostic metadata.
        """
        # Unpack input text and metadata
        if isinstance(text_or_result, str):
            raw_text = text_or_result
            page_count: Optional[int] = None
            filename: Optional[str] = getattr(profile, "filename", None) if profile else None
        else:
            # Handle ResumeParseResult or compatible duck-typed object
            raw_text = getattr(text_or_result, "text", str(text_or_result))
            page_count = getattr(text_or_result, "page_count", None)
            filename = getattr(text_or_result, "filename", None)

        # ---------------------------------------------------------------------
        # Edge Case: Empty or Whitespace-Only Resume Text
        # ---------------------------------------------------------------------
        if not raw_text or not raw_text.strip():
            empty_finding = FormattingFinding(
                issue_id="FMT_EMPTY_TEXT",
                category=FormattingCategory.TEXT_READABILITY,
                title="Empty or Unextractable Document",
                description="Resume contains no extractable text content. Verify file integrity or OCR conversion.",
                severity=FindingSeverity.CRITICAL,
                confidence=1.0,
                evidence="Empty string input",
                detection_rule="check_empty_document",
            )
            return FormattingAnalysisResult(
                formatting_score=0.0,
                max_score=100.0,
                findings=[empty_finding],
                strengths=[],
                limitations=list(DEFAULT_ANALYZER_LIMITATIONS),
                analyzer_version=self.version,
                metadata={
                    "total_lines": 0,
                    "total_blocks": 0,
                    "filename": filename,
                    "page_count": page_count,
                },
            )

        # ---------------------------------------------------------------------
        # Preprocessing & Classification
        # ---------------------------------------------------------------------
        doc = segment_text(raw_text)
        section_map = classify_sections(doc)

        all_findings: List[FormattingFinding] = []
        all_strengths: List[str] = []

        # 1. Section Structure
        sec_findings, sec_strengths = self.section_checker.check(
            doc, section_map, profile=profile
        )
        all_findings.extend(sec_findings)
        all_strengths.extend(sec_strengths)

        # 2. Text Readability
        read_findings, read_strengths = self.readability_checker.check(doc, raw_text)
        all_findings.extend(read_findings)
        all_strengths.extend(read_strengths)

        # 3. Bullet Structure
        bullet_findings, bullet_strengths = self.bullet_checker.check(
            doc, section_map, raw_text=raw_text
        )
        all_findings.extend(bullet_findings)
        all_strengths.extend(bullet_strengths)

        # 4. Resume Consistency
        cons_findings, cons_strengths = self.consistency_checker.check(
            doc, raw_text, profile=profile
        )
        all_findings.extend(cons_findings)
        all_strengths.extend(cons_strengths)

        # ---------------------------------------------------------------------
        # Scoring Calculation (Deductions from 100.0)
        # ---------------------------------------------------------------------
        base_score = 100.0
        total_deduction = 0.0

        for f in all_findings:
            if f.severity == FindingSeverity.CRITICAL:
                ded_val = 16.0 * f.confidence
            elif f.severity == FindingSeverity.WARNING:
                ded_val = 4.5 * f.confidence
            else:  # INFO
                ded_val = 1.5 * f.confidence
            total_deduction += ded_val

        earned_score = round(max(0.0, min(100.0, base_score - total_deduction)), 2)

        # Deduplicate strengths while preserving order
        unique_strengths: List[str] = []
        seen_s = set()
        for s in all_strengths:
            if s not in seen_s:
                seen_s.add(s)
                unique_strengths.append(s)

        # Diagnostic metadata
        metadata = {
            "total_lines": len(doc.lines),
            "non_empty_lines": len(doc.get_non_empty_lines()),
            "total_blocks": len(doc.blocks),
            "bullet_blocks_count": len(doc.get_bullet_blocks()),
            "identified_sections_count": len(section_map.sections),
            "identified_sections": section_map.section_names,
            "filename": filename,
            "page_count": page_count,
            "critical_findings_count": sum(
                1 for f in all_findings if f.severity == FindingSeverity.CRITICAL
            ),
            "warning_findings_count": sum(
                1 for f in all_findings if f.severity == FindingSeverity.WARNING
            ),
            "info_findings_count": sum(
                1 for f in all_findings if f.severity == FindingSeverity.INFO
            ),
        }

        return FormattingAnalysisResult(
            formatting_score=earned_score,
            max_score=100.0,
            findings=all_findings,
            strengths=unique_strengths,
            limitations=list(DEFAULT_ANALYZER_LIMITATIONS),
            analyzer_version=self.version,
            metadata=metadata,
        )


def analyze_formatting(
    text_or_result: Union[str, Any],
    profile: Optional[CandidateProfile] = None,
) -> FormattingAnalysisResult:
    """Convenience helper to analyze resume formatting quality."""
    analyzer = FormattingQualityAnalyzer()
    return analyzer.analyze(text_or_result, profile=profile)


__all__ = [
    "FormattingQualityAnalyzer",
    "analyze_formatting",
]
