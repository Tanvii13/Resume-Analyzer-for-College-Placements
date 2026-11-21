"""
Sprint 3 Module G: NLP evaluation utilities.

Exports Sprint3Evaluator / run_evaluation (labelled-fixture evaluation) and
ConfusionCounts (partial-label precision / recall / F1 / false-positive rate).
"""

from app.nlp.evaluation.evaluator import (
    CONTENT_BANDS,
    Sprint3Evaluator,
    content_band,
    run_evaluation,
)
from app.nlp.evaluation.metrics import ConfusionCounts, accuracy

__all__ = [
    "CONTENT_BANDS",
    "ConfusionCounts",
    "Sprint3Evaluator",
    "accuracy",
    "content_band",
    "run_evaluation",
]
