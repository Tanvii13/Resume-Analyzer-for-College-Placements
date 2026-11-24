"""Privacy utilities shared by NLP adapters and pipelines.

The NLP layer receives resume text only after the backend has authorised the
workflow.  It must not turn identifiers into analysis output or diagnostics.
This module deliberately reuses the backend's established contact-redaction
rules instead of maintaining a second set of PII regular expressions.
"""

from __future__ import annotations

import re
from typing import Iterable

from app.services.privacy_masking_service import PrivacyMaskingService


class PrivacyBoundaryError(ValueError):
    """Raised when a staff-safe NLP projection would disclose identity data."""


def safe_failure_message(module: str, exc: Exception) -> str:
    """Return a useful diagnostic without copying exception or resume content.

    Extractors may include an input line in an exception.  Keeping only its
    type lets callers distinguish failures without retaining raw resume data.
    """
    return f"{module} failed ({type(exc).__name__}); details withheld to protect resume data."


def assert_staff_safe(serialized_output: str, identity_values: Iterable[str | None]) -> None:
    """Reject staff output that contains direct identifiers or contact details.

    This is a boundary check, not access control: the backend still decides
    which authorised workflow may request this projection.
    """
    if not PrivacyMaskingService.is_properly_anonymized(serialized_output):
        raise PrivacyBoundaryError("Staff analysis would expose contact details; refusing to return it.")

    text = serialized_output.casefold()
    leaks: list[str] = []
    for value in identity_values:
        needle = (value or "").strip().casefold()
        if len(needle) < 4:
            continue
        if re.search(rf"(?<![a-z0-9]){re.escape(needle)}(?![a-z0-9])", text):
            leaks.append(needle)
    if leaks:
        raise PrivacyBoundaryError("Staff analysis would expose identifying data; refusing to return it.")


__all__ = ["PrivacyBoundaryError", "assert_staff_safe", "safe_failure_message"]
