"""
Detection limitations and boundary contracts for the Formatting Quality Analyzer.

Guarantees:
- The input is extracted and normalized text, NOT a visual canvas or rendered PDF.
- The analyzer will never fabricate measurements of visual attributes (font sizes,
  exact margin millimeter distances, colors, or visual column coordinates) that are
  unavailable from plain extracted text streams.
- Multi-column layouts are evaluated for textual coherence and extractability,
  rather than being falsely classified as defective solely due to column reading order.
"""

from typing import List

DEFAULT_ANALYZER_LIMITATIONS: List[str] = [
    "Text-only inspection: Font sizes, font families, and typographic weights cannot be measured from plain extracted text without embedded PDF layout streams.",
    "Visual geometry: Physical page margins, line spacing (leading), and exact column coordinates are not determinable from linearized text.",
    "Colors and styling: Text colors, borders, shading, and background contrast are omitted during text extraction and are therefore unverified.",
    "Multi-column reading order: Two-column or hybrid layouts that flatten into sequential text are analyzed for textual coherence rather than visual column placement.",
    "Confidence thresholds: Structural findings without explicit delimiter tokens carry calibrated confidence values reflecting heuristic boundaries.",
]

__all__ = [
    "DEFAULT_ANALYZER_LIMITATIONS",
]
