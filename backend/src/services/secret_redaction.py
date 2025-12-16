"""Secret redaction utilities for protecting sensitive configuration data.

This module provides functionality to redact sensitive information (passwords, tokens,
API keys, etc.) from configuration dictionaries before they are persisted to the database.

This is a critical security feature to prevent credential leakage in ingestion job records.
"""

import copy
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Secret key patterns (case-insensitive matching)
SECRET_KEYS = {
    "token",
    "password",
    "secret",
    "authorization",
    "api_key",
    "apikey",
    "auth_token",
    "access_token",
    "refresh_token",
    "bearer_token",
    "private_key",
    "privatekey",
    "api_secret",
    "apisecret",
    "client_secret",
    "clientsecret",
}

# Value used to replace sensitive data
REDACTED_PLACEHOLDER = "[REDACTED]"


def redact_config(config: dict[str, Any]) -> dict[str, Any]:
    """
    Redact sensitive values from a configuration dictionary.

    This function creates a deep copy of the input config and replaces any values
    associated with secret keys (case-insensitive) with a redacted placeholder.

    Secret keys include: token, password, secret, authorization, api_key, and similar patterns.

    Args:
        config: Configuration dictionary that may contain sensitive data

    Returns:
        A new dictionary with sensitive values redacted

    Examples:
        >>> config = {"base_url": "https://api.example.com", "token": "secret123"}
        >>> redacted = redact_config(config)
        >>> redacted
        {'base_url': 'https://api.example.com', 'token': '[REDACTED]'}

        >>> nested = {"auth": {"password": "secret", "username": "user"}}
        >>> redact_config(nested)
        {'auth': {'password': '[REDACTED]', 'username': 'user'}}
    """
    if not isinstance(config, dict):
        logger.warning(f"redact_config received non-dict: {type(config)}")
        return config

    # Deep copy to avoid mutating the original
    redacted = copy.deepcopy(config)
    _redact_dict_recursive(redacted)

    return redacted


def _redact_dict_recursive(data: Any) -> None:
    """
    Recursively redact secrets in a nested data structure (in-place).

    Args:
        data: Dictionary or nested structure to redact
    """
    if isinstance(data, dict):
        for key, value in data.items():
            # Check if this key should be redacted (case-insensitive)
            if _is_secret_key(key):
                # Only redact if the value is not already redacted
                if value != REDACTED_PLACEHOLDER and value is not None:
                    data[key] = REDACTED_PLACEHOLDER
                    logger.debug(f"Redacted secret key: {key}")
            # Recursively process nested structures
            elif isinstance(value, dict):
                _redact_dict_recursive(value)
            elif isinstance(value, list):
                _redact_list_recursive(value)
    elif isinstance(data, list):
        _redact_list_recursive(data)


def _redact_list_recursive(data: list) -> None:
    """
    Recursively redact secrets in a list (in-place).

    Args:
        data: List that may contain nested dicts with secrets
    """
    for i, item in enumerate(data):
        if isinstance(item, dict):
            _redact_dict_recursive(item)
        elif isinstance(item, list):
            _redact_list_recursive(item)


def _is_secret_key(key: str) -> bool:
    """
    Check if a key name indicates it contains secret data (case-insensitive).

    Args:
        key: Dictionary key to check

    Returns:
        True if the key should be redacted, False otherwise
    """
    if not isinstance(key, str):
        return False

    key_lower = key.lower()

    # Check exact match
    if key_lower in SECRET_KEYS:
        return True

    # Check if key contains any secret pattern
    # This catches keys like "my_token", "user_password", "api_key_prod"
    for secret_pattern in SECRET_KEYS:
        if secret_pattern in key_lower:
            return True

    return False


def should_redact_field(field_name: str) -> bool:
    """
    Public API to check if a field should be redacted.

    This is useful for validation or UI logic that needs to know which
    fields are considered sensitive.

    Args:
        field_name: Name of the field to check

    Returns:
        True if the field should be redacted, False otherwise
    """
    return _is_secret_key(field_name)
