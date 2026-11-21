"""Sprint 5 Module A: staff-facing analysis insights."""

from .builder import StaffAnalysisBuilder, UnsupportedSchemaVersionError, build_staff_analysis
from .schemas import STAFF_INSIGHTS_VERSION, StaffAnalysisResult

__all__ = ["STAFF_INSIGHTS_VERSION", "StaffAnalysisBuilder", "StaffAnalysisResult", "UnsupportedSchemaVersionError", "build_staff_analysis"]
