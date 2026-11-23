"""
Unified Domain Exception Hierarchy & Global Error Boundaries (US-20 AC-2).

Provides standardized JSON error responses for parsing and application errors.
"""

import logging
from typing import Any, Dict, Optional

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class ResumeAnalyzerError(Exception):
    """Base domain exception for all Resume Analyzer errors."""

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code: str = "INTERNAL_DOMAIN_ERROR"

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message

        if status_code is not None:
            self.status_code = status_code

        if error_code is not None:
            self.error_code = error_code

        self.details = details or {}


class ParsingError(ResumeAnalyzerError):
    """Base exception for document parsing and ingestion failures."""

    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    error_code = "PARSING_ERROR"


class EmptyFileError(ParsingError):
    """Raised when an uploaded file has zero bytes."""

    status_code = status.HTTP_400_BAD_REQUEST
    error_code = "EMPTY_FILE"


class InvalidFileTypeError(ParsingError):
    """Raised when the file extension or MIME type is unsupported."""

    status_code = status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
    error_code = "INVALID_FILE_TYPE"


class FileSizeLimitExceededError(ParsingError):
    """Raised when an uploaded file exceeds the configured size limit."""

    status_code = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
    error_code = "FILE_SIZE_LIMIT_EXCEEDED"


class CorruptFileError(ParsingError):
    """Raised when a PDF or DOCX file is damaged or spoofed."""

    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    error_code = "CORRUPT_FILE"


class EncryptedFileError(ParsingError):
    """Raised when a password-protected PDF cannot be processed."""

    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    error_code = "ENCRYPTED_FILE"


class UnreadableContentError(ParsingError):
    """Raised when a document contains no extractable readable text."""

    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    error_code = "UNREADABLE_CONTENT"


def build_error_payload(
    error_code: str,
    message: str,
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build the standardized API error response."""

    return {
        "status": "error",
        "error_code": error_code,
        "message": message,
        "details": details or {},
    }


def register_exception_handlers(app: FastAPI) -> None:
    """Register centralized domain and unexpected-error handlers."""

    @app.exception_handler(ResumeAnalyzerError)
    async def domain_exception_handler(
        request: Request,
        exc: ResumeAnalyzerError,
    ) -> JSONResponse:
        logger.warning(
            "Domain error [%s] on %s: %s",
            exc.error_code,
            request.url.path,
            exc.message,
        )

        return JSONResponse(
            status_code=exc.status_code,
            content=build_error_payload(
                error_code=exc.error_code,
                message=exc.message,
                details=exc.details,
            ),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        logger.exception("Unhandled error on %s", request.url.path)

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=build_error_payload(
                error_code="INTERNAL_SERVER_ERROR",
                message="An unexpected internal error occurred. Please try again later.",
            ),
        )
