"""Logging configuration with context tracking and sensitive data filtering."""

import logging
import re
import sys
import time
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, TypeVar

from core.config import settings
from loguru import logger

if TYPE_CHECKING:
    from loguru import Record

# Context variables for request/operation tracking
request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
user_id_var: ContextVar[int | None] = ContextVar("user_id", default=None)
job_id_var: ContextVar[int | None] = ContextVar("job_id", default=None)

# Patterns for sensitive data filtering
SENSITIVE_PATTERNS = [
    (re.compile(r"(api[_-]?key)[\"']?\s*[:=]\s*[\"']?[\w-]+", re.I), r"\1=***"),
    (re.compile(r"(token)[\"']?\s*[:=]\s*[\"']?[\w.-]+", re.I), r"\1=***"),
    (re.compile(r"(password)[\"']?\s*[:=]\s*[\"']?[^\s,}\"']+", re.I), r"\1=***"),
    (re.compile(r"(secret)[\"']?\s*[:=]\s*[\"']?[\w-]+", re.I), r"\1=***"),
    (re.compile(r"(Authorization)[\"']?\s*[:=]\s*[\"']?[^\s,}\"']+", re.I), r"\1=***"),
    (re.compile(r"(Bearer)\s+[\w.-]+", re.I), r"\1 ***"),
]

F = TypeVar("F", bound=Callable[..., Any])


def generate_request_id() -> str:
    """Generate a short unique request ID (12 hex chars)."""
    return uuid.uuid4().hex[:12]


def get_request_id() -> str | None:
    """Get current request ID from context."""
    return request_id_var.get()


def set_request_id(request_id: str | None) -> None:
    """Set request ID in context."""
    request_id_var.set(request_id)


def get_user_id() -> int | None:
    """Get current user ID from context."""
    return user_id_var.get()


def set_user_id(user_id: int | None) -> None:
    """Set user ID in context."""
    user_id_var.set(user_id)


def get_job_id() -> int | None:
    """Get current job ID from context."""
    return job_id_var.get()


def set_job_id(job_id: int | None) -> None:
    """Set job ID in context."""
    job_id_var.set(job_id)


def filter_sensitive_data(message: str) -> str:
    """Remove sensitive data from log message."""
    for pattern, replacement in SENSITIVE_PATTERNS:
        message = pattern.sub(replacement, message)
    return message


def context_format(record: "Record") -> str:
    """Format log record with context information."""
    # Add context to extra
    record["extra"]["request_id"] = request_id_var.get() or "-"
    record["extra"]["user_id"] = user_id_var.get() or "-"
    record["extra"]["job_id"] = job_id_var.get() or "-"

    # Filter sensitive data from message
    record["message"] = filter_sensitive_data(record["message"])

    # Build format string
    fmt = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{extra[request_id]}</cyan> | "
        "u:{extra[user_id]} | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>\n"
    )
    return fmt


def context_format_file(record: "Record") -> str:
    """Format log record for file output with context information."""
    # Add context to extra
    record["extra"]["request_id"] = request_id_var.get() or "-"
    record["extra"]["user_id"] = user_id_var.get() or "-"
    record["extra"]["job_id"] = job_id_var.get() or "-"

    # Filter sensitive data from message
    record["message"] = filter_sensitive_data(record["message"])

    # Build format string for file (no colors)
    fmt = (
        "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | "
        "{extra[request_id]} | u:{extra[user_id]} | "
        "{name}:{function}:{line} - {message}\n"
    )
    return fmt


def context_format_json(record: "Record") -> str:
    """Format log record as JSON for production."""
    import json

    # Filter sensitive data from message
    message = filter_sensitive_data(record["message"])

    log_entry = {
        "timestamp": record["time"].isoformat(),
        "level": record["level"].name,
        "request_id": request_id_var.get(),
        "user_id": user_id_var.get(),
        "job_id": job_id_var.get(),
        "logger": record["name"],
        "function": record["function"],
        "line": record["line"],
        "message": message,
    }

    # Add exception info if present
    if record["exception"]:
        log_entry["exception"] = {
            "type": (
                record["exception"].type.__name__ if record["exception"].type else None
            ),
            "value": (
                str(record["exception"].value) if record["exception"].value else None
            ),
        }

    # Escape curly braces so loguru doesn't interpret them as format placeholders
    json_str = json.dumps(log_entry)
    return json_str.replace("{", "{{").replace("}", "}}") + "\n"


class _InterceptHandler(logging.Handler):
    """Redirect standard logging to loguru."""

    def emit(self, record: logging.LogRecord) -> None:
        # Get corresponding loguru level
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where the logged message originated
        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def setup_logging() -> None:
    """Configure loguru logging with context support and async writing."""
    logger.remove()

    # Console output with context
    logger.add(
        sys.stdout,
        level=settings.log_level,
        format=context_format,
        enqueue=settings.log_enqueue,  # Async - doesn't block event loop
    )

    # File output with rotation
    log_path = Path(settings.log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # Choose format based on log_json setting
    file_format = context_format_json if settings.log_json else context_format_file

    logger.add(
        log_path / "app.log",
        level=settings.log_level,
        format=file_format,
        rotation=settings.log_rotation,
        retention=settings.log_retention,
        enqueue=settings.log_enqueue,  # Async - doesn't block event loop
    )

    # Intercept standard logging (uvicorn, sqlalchemy, etc.) into loguru
    intercept = _InterceptHandler()
    for name in ("uvicorn", "uvicorn.error", "sqlalchemy.engine"):
        stdlib_logger = logging.getLogger(name)
        stdlib_logger.handlers = [intercept]
        stdlib_logger.propagate = False

    # Disable uvicorn access log — middleware already logs requests with context
    logging.getLogger("uvicorn.access").handlers = []
    logging.getLogger("uvicorn.access").propagate = False


@contextmanager
def log_operation(operation: str, level: str = "DEBUG", **context: Any):
    """Context manager for logging operation timing.

    Args:
        operation: Name of the operation being performed
        level: Log level for the messages (default: DEBUG)
        **context: Additional context to include in log messages

    Example:
        with log_operation("fetch_user_data", user_id=123):
            # do work
            pass
    """
    context_str = ", ".join(f"{k}={v}" for k, v in context.items())
    start_msg = f"{operation} started"
    if context_str:
        start_msg += f" ({context_str})"

    log_func = getattr(logger, level.lower())
    log_func(start_msg)

    start_time = time.perf_counter()
    try:
        yield
    except Exception as e:
        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.error(f"{operation} failed after {duration_ms:.1f}ms: {e}")
        raise
    else:
        duration_ms = (time.perf_counter() - start_time) * 1000
        end_msg = f"{operation} completed in {duration_ms:.1f}ms"

        # Log slow operations at WARNING level
        if duration_ms > settings.log_slow_query_ms:
            logger.warning(f"{end_msg} (slow)")
        else:
            log_func(end_msg)


def log_repository(method: F) -> F:
    """Decorator for auto-logging repository methods.

    Logs method entry (DEBUG) and exit with timing.
    Logs slow queries as WARNING.

    Example:
        class UserRepository:
            @log_repository
            async def get_by_id(self, user_id: int) -> User | None:
                ...
    """

    @wraps(method)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        # Get class name from self
        class_name = args[0].__class__.__name__ if args else "Unknown"
        method_name = method.__name__

        # Build args string (skip self)
        arg_strs = [repr(a) for a in args[1:]]
        kwarg_strs = [f"{k}={v!r}" for k, v in kwargs.items()]
        params = ", ".join(arg_strs + kwarg_strs)

        # Truncate long params
        if len(params) > 100:
            params = params[:97] + "..."

        logger.debug(f"{class_name}.{method_name}({params})")

        start_time = time.perf_counter()
        try:
            result = await method(*args, **kwargs)
            duration_ms = (time.perf_counter() - start_time) * 1000

            if duration_ms > settings.log_slow_query_ms:
                logger.warning(
                    f"{class_name}.{method_name} "
                    f"completed in {duration_ms:.1f}ms (slow)"
                )
            else:
                logger.debug(
                    f"{class_name}.{method_name} completed in {duration_ms:.1f}ms"
                )

            return result
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                f"{class_name}.{method_name} failed after {duration_ms:.1f}ms: {e}"
            )
            raise

    return wrapper  # type: ignore[return-value]
