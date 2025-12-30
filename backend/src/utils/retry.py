"""Retry utilities for handling transient failures."""

import asyncio
import logging
from functools import wraps
from typing import Any, Callable, Type, TypeVar, cast

logger = logging.getLogger(__name__)

T = TypeVar("T")


class RetryableError(Exception):
    """Base class for errors that should trigger retry."""
    pass


class NonRetryableError(Exception):
    """Base class for errors that should NOT trigger retry."""
    pass


def retry_with_exponential_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    retryable_exceptions: tuple[Type[Exception], ...] = (Exception,),
    non_retryable_exceptions: tuple[Type[Exception], ...] = (),
):
    """
    Decorator for retrying async functions with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts (default: 3)
        base_delay: Initial delay in seconds (default: 1.0)
        max_delay: Maximum delay in seconds (default: 60.0)
        exponential_base: Base for exponential backoff calculation (default: 2.0)
        retryable_exceptions: Tuple of exception types to retry on
        non_retryable_exceptions: Tuple of exception types to never retry on

    Example:
        @retry_with_exponential_backoff(max_retries=3, base_delay=1.0)
        async def fetch_data():
            return await api.get("/data")
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception: Exception | None = None

            for attempt in range(max_retries + 1):
                try:
                    result = await func(*args, **kwargs)
                    if attempt > 0:
                        logger.info(
                            f"Retry succeeded for {func.__name__} on attempt {attempt + 1}"
                        )
                    return result

                except non_retryable_exceptions as e:
                    logger.error(
                        f"Non-retryable error in {func.__name__}: {e}",
                        exc_info=True,
                    )
                    raise

                except retryable_exceptions as e:
                    last_exception = e

                    if attempt < max_retries:
                        # Calculate delay with exponential backoff
                        delay = min(
                            base_delay * (exponential_base ** attempt),
                            max_delay
                        )

                        logger.warning(
                            f"Attempt {attempt + 1}/{max_retries + 1} failed for {func.__name__}: {e}. "
                            f"Retrying in {delay:.2f}s..."
                        )

                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            f"All {max_retries + 1} attempts failed for {func.__name__}: {e}",
                            exc_info=True,
                        )

            # If we get here, all retries failed
            if last_exception:
                raise last_exception
            else:
                raise RuntimeError(f"{func.__name__} failed after {max_retries + 1} attempts")

        return cast(Callable[..., T], wrapper)

    return decorator


def is_retryable_snowflake_error(error: Exception) -> bool:
    """
    Determine if a Snowflake error is retryable.

    Args:
        error: The exception to check

    Returns:
        True if the error is retryable, False otherwise
    """
    error_str = str(error).lower()

    # Retryable error patterns
    retryable_patterns = [
        "connection reset",
        "connection refused",
        "connection timeout",
        "connection closed",
        "timed out",
        "timeout",
        "temporary failure",
        "service unavailable",
        "too many requests",
        "rate limit",
        "network error",
        "broken pipe",
        "connection aborted",
        "session expired",
        "authentication token expired",
    ]

    for pattern in retryable_patterns:
        if pattern in error_str:
            return True

    # Check for specific Snowflake error codes (if available)
    if hasattr(error, "errno"):
        # Common retryable Snowflake error codes
        retryable_codes = [
            390144,  # Session expired
            390189,  # Token expired
            606,     # Network error
            1704,    # Connection timeout
        ]
        if error.errno in retryable_codes:
            return True

    return False


def is_permission_error(error: Exception) -> bool:
    """
    Determine if an error is related to permissions.

    Args:
        error: The exception to check

    Returns:
        True if the error is a permission error, False otherwise
    """
    error_str = str(error).lower()

    permission_patterns = [
        "permission denied",
        "access denied",
        "insufficient privileges",
        "not authorized",
        "authorization error",
        "privilege",
        "role",
        "grant",
    ]

    for pattern in permission_patterns:
        if pattern in error_str:
            return True

    return False
