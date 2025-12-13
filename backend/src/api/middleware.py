"""API middleware for request processing."""

import re
import time
from typing import Callable
from uuid import uuid4

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from src.logging_config import get_logger

logger = get_logger(__name__)

# Patterns that should be rejected (potential injection attacks)
DANGEROUS_PATTERNS = [
    r"<script.*?>.*?</script>",  # XSS script tags
    r"javascript:",  # JavaScript protocol
    r"on\w+\s*=",  # Event handlers
    r"--",  # SQL comment
    r";.*drop\s+",  # SQL drop
    r";.*delete\s+",  # SQL delete
    r"union\s+select",  # SQL union injection
]

# Compiled patterns for efficiency
COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in DANGEROUS_PATTERNS]


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging requests and responses."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate request ID
        request_id = str(uuid4())[:8]
        request.state.request_id = request_id

        # Log request
        start_time = time.time()
        logger.info(
            f"Request started",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "query": str(request.query_params),
            },
        )

        # Process request
        response = await call_next(request)

        # Log response
        duration_ms = (time.time() - start_time) * 1000
        logger.info(
            f"Request completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 2),
            },
        )

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"

        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware for adding security headers."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = "default-src 'self'"

        return response


def sanitize_string(value: str) -> str:
    """Sanitize a string value to prevent injection attacks.

    Args:
        value: The string to sanitize

    Returns:
        Sanitized string with dangerous patterns removed
    """
    if not value:
        return value

    # Check for dangerous patterns
    for pattern in COMPILED_PATTERNS:
        if pattern.search(value):
            # Log the attempt and strip dangerous content
            logger.warning(f"Potentially dangerous input detected and sanitized")
            value = pattern.sub("", value)

    # Remove null bytes
    value = value.replace("\x00", "")

    return value


def sanitize_search_query(value: str, max_length: int = 200) -> str:
    """Sanitize a search query string for use in LIKE/ILIKE clauses.

    This function escapes special characters used in SQL LIKE patterns
    and removes potentially dangerous characters.

    Args:
        value: The search query to sanitize
        max_length: Maximum allowed length (default: 200)

    Returns:
        Sanitized search string safe for LIKE/ILIKE operations
    """
    if not value:
        return value

    # Truncate to max length
    value = value[:max_length]

    # Apply general sanitization first
    value = sanitize_string(value)

    # Escape LIKE pattern special characters (%, _, [, ])
    # These are the wildcards that could be used maliciously
    value = value.replace("\\", "\\\\")  # Escape backslash first
    value = value.replace("%", "\\%")
    value = value.replace("_", "\\_")
    value = value.replace("[", "\\[")
    value = value.replace("]", "\\]")

    # Remove any remaining problematic characters
    # Allow: alphanumeric, spaces, common punctuation
    allowed_pattern = re.compile(r"[^a-zA-Z0-9\s\-_.,@!?#$&*()+=:;<>/\\%]")
    value = allowed_pattern.sub("", value)

    # Strip leading/trailing whitespace
    value = value.strip()

    return value


def validate_urn(urn: str) -> bool:
    """Validate URN format.

    Args:
        urn: The URN to validate

    Returns:
        True if valid, False otherwise
    """
    # URN format: urn:dab:{source}:{type}:{namespace}:{name}
    urn_pattern = r"^urn:dab:[a-z]+:[a-z]+:[a-zA-Z0-9_.-]+:[a-zA-Z0-9_.-]+$"
    return bool(re.match(urn_pattern, urn))


def validate_uuid(uuid_str: str) -> bool:
    """Validate UUID format.

    Args:
        uuid_str: The UUID string to validate

    Returns:
        True if valid, False otherwise
    """
    uuid_pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
    return bool(re.match(uuid_pattern, uuid_str.lower()))


def validate_layer(layer: str) -> bool:
    """Validate architecture layer.

    Args:
        layer: The layer name to validate

    Returns:
        True if valid, False otherwise
    """
    valid_layers = {"bronze", "silver", "gold", "raw", "staging", "intermediate", "marts"}
    return layer.lower() in valid_layers


def validate_capsule_type(capsule_type: str) -> bool:
    """Validate capsule type.

    Args:
        capsule_type: The capsule type to validate

    Returns:
        True if valid, False otherwise
    """
    valid_types = {"model", "source", "seed", "snapshot", "analysis", "test"}
    return capsule_type.lower() in valid_types


def validate_severity(severity: str) -> bool:
    """Validate severity level.

    Args:
        severity: The severity level to validate

    Returns:
        True if valid, False otherwise
    """
    valid_severities = {"critical", "error", "warning", "info"}
    return severity.lower() in valid_severities


def validate_pagination(offset: int, limit: int, max_limit: int = 1000) -> tuple[int, int]:
    """Validate and normalize pagination parameters.

    Args:
        offset: The offset value
        limit: The limit value
        max_limit: Maximum allowed limit

    Returns:
        Tuple of (validated_offset, validated_limit)
    """
    validated_offset = max(0, offset)
    validated_limit = min(max(1, limit), max_limit)
    return validated_offset, validated_limit
