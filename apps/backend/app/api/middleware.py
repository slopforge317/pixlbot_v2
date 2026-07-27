"""FastAPI middleware for request logging and correlation."""

import time

from core.logging import generate_request_id, set_request_id, set_user_id
from fastapi import Request, Response
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging HTTP requests with correlation IDs.

    Features:
    - Generates unique request_id for each request
    - Logs request start (method, path, query, client_ip)
    - Logs request end (status_code, duration_ms)
    - Adds X-Request-ID to response headers
    """

    # Paths to skip logging (health checks, metrics, etc.)
    SKIP_PATHS = {"/health", "/metrics", "/favicon.ico"}

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Skip logging for certain paths
        if request.url.path in self.SKIP_PATHS:
            return await call_next(request)

        # Generate and set request ID
        request_id = generate_request_id()
        set_request_id(request_id)
        set_user_id(None)  # Will be set by auth dependency

        # Get client IP (handle proxies)
        client_ip = request.headers.get("X-Forwarded-For")
        if client_ip:
            client_ip = client_ip.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"

        # Build query string for logging (truncate if too long)
        query_str = str(request.url.query) if request.url.query else ""
        if len(query_str) > 100:
            query_str = query_str[:97] + "..."

        # Log request start
        logger.debug(
            f"Request started: {request.method} {request.url.path}"
            + (f"?{query_str}" if query_str else "")
            + f" from {client_ip}"
        )

        # Process request and measure time
        start_time = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                f"Request failed: {request.method} {request.url.path} "
                f"after {duration_ms:.1f}ms"
            )
            # Re-raise to let FastAPI handle the exception
            raise
        finally:
            # Reset context
            set_request_id(None)
            set_user_id(None)

        duration_ms = (time.perf_counter() - start_time) * 1000

        # Log request completion
        log_msg = (
            f"Request completed: {request.method} {request.url.path} "
            f"status={response.status_code} duration={duration_ms:.1f}ms"
        )

        if response.status_code >= 500:
            logger.error(log_msg)
        elif response.status_code >= 400:
            logger.warning(log_msg)
        else:
            logger.info(log_msg)

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id

        return response
