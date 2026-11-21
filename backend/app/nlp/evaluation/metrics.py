"""
Detection metrics for Sprint 3 Module G.

Partial-label confusion counting: each labelled case lists items that SHOULD be detected
(positives) and items that must NOT be detected (negatives). Items in neither list are
unlabelled and are excluded from precision/recall but reported for manual review.
"""

from dataclasses import dataclass, field
from typing import Iterable, List, Optional, Set


@dataclass
class ConfusionCounts:
    tp: int = 0
    fp: int = 0
    fn: int = 0
    tn: int = 0
    false_positives: List[str] = field(default_factory=list)
    false_negatives: List[str] = field(default_factory=list)
    unlabelled_detections: List[str] = field(default_factory=list)

    def add(
        self, case: str, detected: Iterable[str], expected: Iterable[str], forbidden: Iterable[str]
    ) -> None:
        detected, expected, forbidden = set(detected), set(expected), set(forbidden)
        overlap = expected & forbidden
        if overlap:
            raise ValueError(f"{case}: label lists overlap: {sorted(overlap)}")
        self.tp += len(detected & expected)
        self.fn += len(expected - detected)
        self.fp += len(detected & forbidden)
        self.tn += len(forbidden - detected)
        self.false_negatives += [f"{case}:{x}" for x in sorted(expected - detected)]
        self.false_positives += [f"{case}:{x}" for x in sorted(detected & forbidden)]
        self.unlabelled_detections += [
            f"{case}:{x}" for x in sorted(detected - expected - forbidden)
        ]

    @property
    def precision(self) -> Optional[float]:
        return safe_div(self.tp, self.tp + self.fp)

    @property
    def recall(self) -> Optional[float]:
        return safe_div(self.tp, self.tp + self.fn)

    @property
    def f1(self) -> Optional[float]:
        p, r = self.precision, self.recall
        if p is None or r is None or (p + r) == 0:
            return None
        return 2 * p * r / (p + r)

    @property
    def false_positive_rate(self) -> Optional[float]:
        return safe_div(self.fp, self.fp + self.tn)

    @property
    def support(self) -> int:
        return self.tp + self.fn

    def as_dict(self) -> dict:
        return {
            "tp": self.tp,
            "fp": self.fp,
            "fn": self.fn,
            "tn": self.tn,
            "precision": rnd(self.precision),
            "recall": rnd(self.recall),
            "f1": rnd(self.f1),
            "false_positive_rate": rnd(self.false_positive_rate),
            "support": self.support,
            "false_positives": self.false_positives,
            "false_negatives": self.false_negatives,
            "unlabelled_detections": self.unlabelled_detections,
        }


def safe_div(a: float, b: float) -> Optional[float]:
    return None if b == 0 else a / b


def rnd(x: Optional[float], digits: int = 3) -> Optional[float]:
    return None if x is None else round(x, digits)


def accuracy(pairs: Iterable[tuple]) -> Optional[float]:
    pairs = list(pairs)
    return safe_div(sum(1 for predicted, actual in pairs if predicted == actual), len(pairs))


def canonical_set(ids: Iterable[str], cluster_map: dict) -> Set[str]:
    return {cluster_map.get(i, i) for i in ids}


__all__ = ["ConfusionCounts", "accuracy", "canonical_set", "rnd", "safe_div"]
