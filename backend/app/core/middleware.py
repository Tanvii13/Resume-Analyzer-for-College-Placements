"""
Application middleware for upload security and request timing (US-20).
"""

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.services.parsing_service import MAX_UPLOAD_SIZE_BYTES

logger = logging.getLogger(__name__)


class UploadSafeguardMiddleware(BaseHTTPMiddleware):
    """
    Reject oversized upload requests before the application processes them.

    Checks Content-Length for POST, PUT and PATCH requests.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.method in {"POST", "PUT", "PATCH"}:
            content_length = request.headers.get("content-length")

            if content_length is not None:
                try:
                    size_bytes = int(content_length)
                except (TypeError, ValueError):
                    return JSONResponse(
                        status_code=400,
                        content={
                            "status": "error",
                            "error_code": "INVALID_CONTENT_LENGTH",
                            "message": "Invalid Content-Length header.",
                            "details": {},
                        },
                    )

                if size_bytes < 0:
                    return JSONResponse(
                        status_code=400,
                        content={
                            "status": "error",
                            "error_code": "INVALID_CONTENT_LENGTH",
                            "message": "Content-Length cannot be negative.",
                            "details": {},
                        },
                    )

                if size_bytes > MAX_UPLOAD_SIZE_BYTES:
                    logger.warning(
                        "Rejected oversized request: %s bytes from %s",
                        size_bytes,
                        request.client.host if request.client else "unknown",
                    )

                    return JSONResponse(
                        status_code=413,
                        content={
                            "status": "error",
                            "error_code": "FILE_SIZE_LIMIT_EXCEEDED",
                            "message": "Request exceeds the maximum upload size of 10 MB.",
                            "details": {
                                "size_bytes": size_bytes,
                                "max_size_bytes": MAX_UPLOAD_SIZE_BYTES,
                            },
                        },
                    )

        return await call_next(request)


class ExecutionTimingMiddleware(BaseHTTPMiddleware):
    """
    Measure request execution time and attach it to the response.

    Response header:
        X-Process-Time-Ms
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.perf_counter()

        response = await call_next(request)

        elapsed_ms = (time.perf_counter() - start_time) * 1000

        response.headers["X-Process-Time-Ms"] = f"{elapsed_ms:.2f}"

        return response
