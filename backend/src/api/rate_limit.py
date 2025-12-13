"""Rate limiting configuration and middleware."""

from typing import Callable, Optional

from fastapi import Request, Response
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.responses import JSONResponse

from src.config import Settings, get_settings
from src.logging_config import get_logger

logger = get_logger(__name__)


def get_client_identifier(request: Request) -> str:
    """Get a unique identifier for rate limiting.

    Uses API key if present, otherwise falls back to IP address.

    Args:
        request: The FastAPI request

    Returns:
        A string identifier for the client
    """
    settings = get_settings()

    # Try to get API key from header
    api_key = request.headers.get(settings.api_key_header)
    if api_key:
        # Use a hash prefix of the API key for privacy
        return f"key:{api_key[:8]}"

    # Fall back to IP address
    return f"ip:{get_remote_address(request)}"


def create_limiter(settings: Optional[Settings] = None) -> Limiter:
    """Create and configure the rate limiter.

    Args:
        settings: Application settings (optional)

    Returns:
        Configured Limiter instance
    """
    if settings is None:
        settings = get_settings()

    # Configure storage backend
    storage_uri = settings.rate_limit_storage_uri or "memory://"

    limiter = Limiter(
        key_func=get_client_identifier,
        default_limits=[settings.rate_limit_default],
        storage_uri=storage_uri,
        strategy="fixed-window",  # or "moving-window" for smoother limiting
        headers_enabled=True,  # Add rate limit headers to responses
    )

    return limiter


# Global limiter instance (lazy initialization)
_limiter: Optional[Limiter] = None


def get_limiter() -> Limiter:
    """Get the global limiter instance.

    Returns:
        The configured Limiter instance
    """
    global _limiter
    if _limiter is None:
        _limiter = create_limiter()
    return _limiter


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """Handle rate limit exceeded errors.

    Args:
        request: The FastAPI request
        exc: The rate limit exception

    Returns:
        JSON response with error details
    """
    logger.warning(
        "Rate limit exceeded",
        extra={
            "path": request.url.path,
            "client": get_client_identifier(request),
            "limit": str(exc.detail),
        },
    )

    # Parse retry-after from exception if available
    retry_after = getattr(exc, "retry_after", 60)

    return JSONResponse(
        status_code=429,
        content={
            "error": {
                "code": "RATE_LIMITED",
                "message": f"Rate limit exceeded: {exc.detail}",
                "retry_after": retry_after,
            }
        },
        headers={
            "Retry-After": str(retry_after),
            "X-RateLimit-Limit": str(exc.detail),
        },
    )


# Decorator factories for different rate limits
def default_limit() -> Callable:
    """Apply default rate limit to an endpoint.

    Returns:
        Rate limit decorator
    """
    settings = get_settings()
    limiter = get_limiter()
    return limiter.limit(settings.rate_limit_default)


def burst_limit() -> Callable:
    """Apply burst rate limit to an endpoint.

    Returns:
        Rate limit decorator
    """
    settings = get_settings()
    limiter = get_limiter()
    return limiter.limit(settings.rate_limit_burst)


def expensive_limit() -> Callable:
    """Apply expensive operation rate limit to an endpoint.

    Use this for computationally expensive operations like
    full conformance evaluation.

    Returns:
        Rate limit decorator
    """
    settings = get_settings()
    limiter = get_limiter()
    return limiter.limit(settings.rate_limit_expensive)


def custom_limit(limit_string: str) -> Callable:
    """Apply a custom rate limit to an endpoint.

    Args:
        limit_string: Rate limit string (e.g., "5/minute", "100/hour")

    Returns:
        Rate limit decorator
    """
    limiter = get_limiter()
    return limiter.limit(limit_string)


class RateLimitMiddleware:
    """Middleware wrapper for rate limiting.

    This provides a middleware-style interface for the rate limiter,
    allowing it to be easily added to the FastAPI app.
    """

    def __init__(self, app, settings: Optional[Settings] = None):
        """Initialize the middleware.

        Args:
            app: The ASGI application
            settings: Application settings (optional)
        """
        self.app = app
        self._settings = settings

    @property
    def settings(self) -> Settings:
        """Get settings."""
        if self._settings is None:
            self._settings = get_settings()
        return self._settings

    async def __call__(self, scope, receive, send):
        """Process the request.

        Note: The actual rate limiting is done by SlowAPI's state injection.
        This middleware mainly ensures the limiter is attached to the app.
        """
        await self.app(scope, receive, send)


def configure_rate_limiting(app) -> None:
    """Configure rate limiting for the FastAPI application.

    Args:
        app: The FastAPI application instance
    """
    settings = get_settings()

    if not settings.rate_limit_enabled:
        logger.info("Rate limiting is disabled")
        return

    limiter = get_limiter()

    # Attach limiter to app state
    app.state.limiter = limiter

    # Add exception handler for rate limit exceeded
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

    logger.info(
        "Rate limiting configured",
        extra={
            "default_limit": settings.rate_limit_default,
            "expensive_limit": settings.rate_limit_expensive,
        },
    )
