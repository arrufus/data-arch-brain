"""API authentication middleware and dependencies."""

import fnmatch
import secrets
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import APIKeyHeader

from src.config import Settings, get_settings
from src.logging_config import get_logger

logger = get_logger(__name__)

# API Key header scheme
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


class AuthenticationError(HTTPException):
    """Authentication failed exception."""

    def __init__(self, detail: str = "Invalid or missing API key"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "ApiKey"},
        )


class AuthorizationError(HTTPException):
    """Authorization failed exception."""

    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )


def is_path_exempt(path: str, exempt_paths: list[str]) -> bool:
    """Check if a path is exempt from authentication.

    Args:
        path: The request path to check
        exempt_paths: List of exempt path patterns (supports * wildcards)

    Returns:
        True if the path is exempt, False otherwise
    """
    for pattern in exempt_paths:
        # Support wildcard matching
        if fnmatch.fnmatch(path, pattern):
            return True
        # Also check without trailing slash
        if fnmatch.fnmatch(path.rstrip("/"), pattern.rstrip("/")):
            return True
    return False


def verify_api_key(api_key: str, valid_keys: list[str]) -> bool:
    """Verify an API key against the list of valid keys.

    Uses constant-time comparison to prevent timing attacks.

    Args:
        api_key: The API key to verify
        valid_keys: List of valid API keys

    Returns:
        True if the key is valid, False otherwise
    """
    for valid_key in valid_keys:
        if secrets.compare_digest(api_key, valid_key):
            return True
    return False


async def get_api_key(
    request: Request,
    api_key: Optional[str] = Depends(api_key_header),
    settings: Settings = Depends(get_settings),
) -> Optional[str]:
    """Dependency to extract and validate API key.

    Args:
        request: The FastAPI request
        api_key: The API key from header (if present)
        settings: Application settings

    Returns:
        The validated API key, or None if auth is not required

    Raises:
        AuthenticationError: If authentication is required but fails
    """
    # Check if authentication is required
    if not settings.auth_required:
        return None

    # Check if path is exempt
    if is_path_exempt(request.url.path, settings.auth_exempt_paths):
        return None

    # Check if API key is provided
    if not api_key:
        logger.warning(
            "Authentication failed: No API key provided",
            extra={"path": request.url.path, "client_ip": request.client.host if request.client else "unknown"},
        )
        raise AuthenticationError("API key required. Provide via X-API-Key header.")

    # Validate API key
    if not verify_api_key(api_key, settings.api_keys):
        logger.warning(
            "Authentication failed: Invalid API key",
            extra={"path": request.url.path, "client_ip": request.client.host if request.client else "unknown"},
        )
        raise AuthenticationError("Invalid API key")

    logger.debug(
        "Authentication successful",
        extra={"path": request.url.path},
    )
    return api_key


async def require_api_key(
    api_key: Optional[str] = Depends(get_api_key),
) -> str:
    """Dependency that strictly requires a valid API key.

    Use this for endpoints that always require authentication,
    even if global auth is disabled.

    Args:
        api_key: The API key from get_api_key dependency

    Returns:
        The validated API key

    Raises:
        AuthenticationError: If no valid API key is provided
    """
    if api_key is None:
        raise AuthenticationError("API key required for this endpoint")
    return api_key


class APIKeyAuthMiddleware:
    """Middleware for API key authentication.

    This middleware checks for API key authentication on all requests
    unless the path is in the exempt list.
    """

    def __init__(self, app, settings: Optional[Settings] = None):
        """Initialize the middleware.

        Args:
            app: The ASGI application
            settings: Application settings (optional, uses get_settings if not provided)
        """
        self.app = app
        self._settings = settings

    @property
    def settings(self) -> Settings:
        """Get settings, using cached version or fetching from get_settings."""
        if self._settings is None:
            self._settings = get_settings()
        return self._settings

    async def __call__(self, scope, receive, send):
        """Process the request."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Check if auth is required
        if not self.settings.auth_required:
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")

        # Check if path is exempt
        if is_path_exempt(path, self.settings.auth_exempt_paths):
            await self.app(scope, receive, send)
            return

        # Extract API key from headers
        headers = dict(scope.get("headers", []))
        api_key_bytes = headers.get(self.settings.api_key_header.lower().encode())
        api_key = api_key_bytes.decode() if api_key_bytes else None

        # Validate API key
        if not api_key or not verify_api_key(api_key, self.settings.api_keys):
            # Return 401 Unauthorized
            response_body = b'{"error":{"code":"UNAUTHORIZED","message":"Invalid or missing API key"}}'
            await send({
                "type": "http.response.start",
                "status": 401,
                "headers": [
                    [b"content-type", b"application/json"],
                    [b"www-authenticate", b"ApiKey"],
                ],
            })
            await send({
                "type": "http.response.body",
                "body": response_body,
            })
            return

        # Continue with request
        await self.app(scope, receive, send)
