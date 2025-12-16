"""Tests for secret redaction utilities."""

import pytest
from src.services.secret_redaction import (
    redact_config,
    should_redact_field,
    REDACTED_PLACEHOLDER,
)


class TestRedactConfig:
    """Tests for redact_config function."""

    def test_redact_simple_token(self) -> None:
        """Test redaction of simple token field."""
        config = {"base_url": "https://api.example.com", "token": "secret123"}
        redacted = redact_config(config)

        assert redacted["base_url"] == "https://api.example.com"
        assert redacted["token"] == REDACTED_PLACEHOLDER

    def test_redact_password(self) -> None:
        """Test redaction of password field."""
        config = {"username": "user", "password": "super_secret"}
        redacted = redact_config(config)

        assert redacted["username"] == "user"
        assert redacted["password"] == REDACTED_PLACEHOLDER

    def test_redact_multiple_secrets(self) -> None:
        """Test redaction of multiple secret fields."""
        config = {
            "api_key": "key123",
            "secret": "secret456",
            "authorization": "Bearer token789",
            "public_field": "not_secret",
        }
        redacted = redact_config(config)

        assert redacted["api_key"] == REDACTED_PLACEHOLDER
        assert redacted["secret"] == REDACTED_PLACEHOLDER
        assert redacted["authorization"] == REDACTED_PLACEHOLDER
        assert redacted["public_field"] == "not_secret"

    def test_redact_nested_dict(self) -> None:
        """Test redaction in nested dictionaries."""
        config = {
            "database": {
                "host": "localhost",
                "password": "db_secret",
            },
            "auth": {
                "username": "admin",
                "api_key": "key456",
            },
        }
        redacted = redact_config(config)

        assert redacted["database"]["host"] == "localhost"
        assert redacted["database"]["password"] == REDACTED_PLACEHOLDER
        assert redacted["auth"]["username"] == "admin"
        assert redacted["auth"]["api_key"] == REDACTED_PLACEHOLDER

    def test_redact_list_with_dicts(self) -> None:
        """Test redaction in lists containing dictionaries."""
        config = {
            "connections": [
                {"name": "conn1", "token": "secret1"},
                {"name": "conn2", "token": "secret2"},
            ]
        }
        redacted = redact_config(config)

        assert redacted["connections"][0]["name"] == "conn1"
        assert redacted["connections"][0]["token"] == REDACTED_PLACEHOLDER
        assert redacted["connections"][1]["name"] == "conn2"
        assert redacted["connections"][1]["token"] == REDACTED_PLACEHOLDER

    def test_redact_deeply_nested(self) -> None:
        """Test redaction in deeply nested structures."""
        config = {
            "level1": {
                "level2": {
                    "level3": {
                        "password": "deep_secret",
                        "safe_field": "safe_value",
                    }
                }
            }
        }
        redacted = redact_config(config)

        assert redacted["level1"]["level2"]["level3"]["password"] == REDACTED_PLACEHOLDER
        assert redacted["level1"]["level2"]["level3"]["safe_field"] == "safe_value"

    def test_redact_case_insensitive(self) -> None:
        """Test case-insensitive redaction of secret keys."""
        config = {
            "TOKEN": "secret1",
            "Token": "secret2",
            "token": "secret3",
            "PASSWORD": "secret4",
            "Password": "secret5",
        }
        redacted = redact_config(config)

        assert all(v == REDACTED_PLACEHOLDER for v in redacted.values())

    def test_redact_pattern_matching(self) -> None:
        """Test redaction of keys containing secret patterns."""
        config = {
            "my_token": "secret1",
            "user_password": "secret2",
            "api_key_prod": "secret3",
            "bearer_token_refresh": "secret4",
            "client_secret_key": "secret5",
        }
        redacted = redact_config(config)

        assert all(v == REDACTED_PLACEHOLDER for v in redacted.values())

    def test_redact_all_secret_types(self) -> None:
        """Test redaction of all defined secret key types."""
        config = {
            "token": "s1",
            "password": "s2",
            "secret": "s3",
            "authorization": "s4",
            "api_key": "s5",
            "apikey": "s6",
            "auth_token": "s7",
            "access_token": "s8",
            "refresh_token": "s9",
            "bearer_token": "s10",
            "private_key": "s11",
            "privatekey": "s12",
            "api_secret": "s13",
            "apisecret": "s14",
            "client_secret": "s15",
            "clientsecret": "s16",
        }
        redacted = redact_config(config)

        assert all(v == REDACTED_PLACEHOLDER for v in redacted.values())

    def test_redact_none_values(self) -> None:
        """Test that None values are not redacted."""
        config = {"token": None, "password": None, "username": "user"}
        redacted = redact_config(config)

        # None values should remain None, not become REDACTED
        assert redacted["token"] is None
        assert redacted["password"] is None
        assert redacted["username"] == "user"

    def test_redact_already_redacted(self) -> None:
        """Test that already redacted values remain redacted."""
        config = {"token": REDACTED_PLACEHOLDER, "password": "secret"}
        redacted = redact_config(config)

        assert redacted["token"] == REDACTED_PLACEHOLDER
        assert redacted["password"] == REDACTED_PLACEHOLDER

    def test_redact_empty_dict(self) -> None:
        """Test redaction of empty dictionary."""
        config = {}
        redacted = redact_config(config)

        assert redacted == {}

    def test_redact_no_secrets(self) -> None:
        """Test dictionary with no secrets remains unchanged."""
        config = {
            "name": "test",
            "count": 42,
            "enabled": True,
            "items": ["a", "b", "c"],
        }
        redacted = redact_config(config)

        assert redacted == config

    def test_redact_preserves_structure(self) -> None:
        """Test that redaction preserves original structure."""
        config = {
            "string": "value",
            "number": 123,
            "boolean": True,
            "null": None,
            "list": [1, 2, 3],
            "dict": {"nested": "value"},
            "password": "secret",
        }
        redacted = redact_config(config)

        assert isinstance(redacted["string"], str)
        assert isinstance(redacted["number"], int)
        assert isinstance(redacted["boolean"], bool)
        assert redacted["null"] is None
        assert isinstance(redacted["list"], list)
        assert isinstance(redacted["dict"], dict)
        assert redacted["password"] == REDACTED_PLACEHOLDER

    def test_redact_does_not_mutate_original(self) -> None:
        """Test that redaction creates a copy and doesn't mutate original."""
        original = {"token": "secret", "username": "user"}
        redacted = redact_config(original)

        # Original should remain unchanged
        assert original["token"] == "secret"
        assert original["username"] == "user"

        # Redacted should have redacted values
        assert redacted["token"] == REDACTED_PLACEHOLDER
        assert redacted["username"] == "user"

    def test_redact_non_dict_input(self) -> None:
        """Test handling of non-dict input."""
        # Should handle gracefully and return input
        assert redact_config("not a dict") == "not a dict"
        assert redact_config(123) == 123
        assert redact_config(None) is None
        assert redact_config([1, 2, 3]) == [1, 2, 3]

    def test_redact_mixed_list(self) -> None:
        """Test redaction in lists with mixed types."""
        config = {
            "items": [
                "string",
                123,
                {"token": "secret"},
                ["nested", {"password": "secret"}],
            ]
        }
        redacted = redact_config(config)

        assert redacted["items"][0] == "string"
        assert redacted["items"][1] == 123
        assert redacted["items"][2]["token"] == REDACTED_PLACEHOLDER
        assert redacted["items"][3][0] == "nested"
        assert redacted["items"][3][1]["password"] == REDACTED_PLACEHOLDER


class TestShouldRedactField:
    """Tests for should_redact_field function."""

    def test_should_redact_standard_keys(self) -> None:
        """Test detection of standard secret keys."""
        assert should_redact_field("token")
        assert should_redact_field("password")
        assert should_redact_field("secret")
        assert should_redact_field("api_key")
        assert should_redact_field("authorization")

    def test_should_redact_case_insensitive(self) -> None:
        """Test case-insensitive detection."""
        assert should_redact_field("TOKEN")
        assert should_redact_field("Token")
        assert should_redact_field("PASSWORD")
        assert should_redact_field("Password")

    def test_should_redact_pattern_matching(self) -> None:
        """Test pattern matching in field names."""
        assert should_redact_field("my_token")
        assert should_redact_field("user_password")
        assert should_redact_field("api_key_prod")
        assert should_redact_field("bearer_token_refresh")

    def test_should_not_redact_safe_fields(self) -> None:
        """Test that safe fields are not marked for redaction."""
        assert not should_redact_field("username")
        assert not should_redact_field("base_url")
        assert not should_redact_field("timeout")
        assert not should_redact_field("enabled")
        assert not should_redact_field("name")

    def test_should_redact_non_string_key(self) -> None:
        """Test handling of non-string keys."""
        assert not should_redact_field(123)
        assert not should_redact_field(None)


class TestAirflowIntegrationScenarios:
    """Tests for Airflow-specific secret redaction scenarios."""

    def test_redact_airflow_basic_auth(self) -> None:
        """Test redaction of Airflow basic auth config."""
        config = {
            "base_url": "https://airflow.example.com",
            "instance_name": "prod-airflow",
            "auth_mode": "basic_env",
            "username_env": "AIRFLOW_USERNAME",
            "password_env": "AIRFLOW_PASSWORD",
            # These should never be in config, but test they're redacted
            "username": "admin",
            "password": "secret123",
        }
        redacted = redact_config(config)

        assert redacted["base_url"] == "https://airflow.example.com"
        assert redacted["instance_name"] == "prod-airflow"
        assert redacted["auth_mode"] == "basic_env"
        assert redacted["username_env"] == "AIRFLOW_USERNAME"
        # password_env contains "password" so it gets redacted (safe behavior)
        assert redacted["password_env"] == REDACTED_PLACEHOLDER
        assert redacted["username"] == "admin"  # username is not redacted
        assert redacted["password"] == REDACTED_PLACEHOLDER

    def test_redact_airflow_bearer_token(self) -> None:
        """Test redaction of Airflow bearer token config."""
        config = {
            "base_url": "https://airflow.example.com",
            "instance_name": "prod-airflow",
            "auth_mode": "bearer_env",
            "token_env": "AIRFLOW_TOKEN",
            # This should never be in config, but test it's redacted
            "token": "actual-secret-token-value",
        }
        redacted = redact_config(config)

        assert redacted["base_url"] == "https://airflow.example.com"
        # token_env contains "token" so it gets redacted (safe behavior)
        assert redacted["token_env"] == REDACTED_PLACEHOLDER
        assert redacted["token"] == REDACTED_PLACEHOLDER

    def test_redact_airflow_complex_config(self) -> None:
        """Test redaction of complex Airflow config with nested auth."""
        config = {
            "base_url": "https://airflow.example.com",
            "instance_name": "prod-airflow",
            "dag_id_regex": "customer_.*",
            "include_paused": False,
            "page_limit": 100,
            "auth": {
                "mode": "bearer",
                "token": "secret-token",
                "backup_credentials": {
                    "username": "backup_user",
                    "password": "backup_pass",
                },
            },
            "metadata": {
                "tags": ["production", "customer"],
                "owner": "data-team",
            },
        }
        redacted = redact_config(config)

        # Non-secret fields preserved
        assert redacted["base_url"] == "https://airflow.example.com"
        assert redacted["dag_id_regex"] == "customer_.*"
        assert redacted["include_paused"] is False
        assert redacted["metadata"]["tags"] == ["production", "customer"]

        # Secrets redacted
        assert redacted["auth"]["token"] == REDACTED_PLACEHOLDER
        assert redacted["auth"]["backup_credentials"]["password"] == REDACTED_PLACEHOLDER
        assert redacted["auth"]["backup_credentials"]["username"] == "backup_user"


class TestDbtIntegrationScenarios:
    """Tests for dbt-specific secret redaction scenarios."""

    def test_redact_dbt_profiles_with_secrets(self) -> None:
        """Test redaction of dbt profiles containing database passwords."""
        config = {
            "project_dir": "/path/to/project",
            "profiles": {
                "production": {
                    "type": "postgres",
                    "host": "db.example.com",
                    "user": "dbt_user",
                    "password": "db_password_123",
                    "port": 5432,
                    "database": "analytics",
                }
            },
        }
        redacted = redact_config(config)

        assert redacted["project_dir"] == "/path/to/project"
        assert redacted["profiles"]["production"]["host"] == "db.example.com"
        assert redacted["profiles"]["production"]["user"] == "dbt_user"
        assert redacted["profiles"]["production"]["password"] == REDACTED_PLACEHOLDER

    def test_redact_dbt_api_key(self) -> None:
        """Test redaction of dbt Cloud API key."""
        config = {
            "account_id": "12345",
            "api_key": "dbt_cloud_secret_key",
            "project_id": "67890",
        }
        redacted = redact_config(config)

        assert redacted["account_id"] == "12345"
        assert redacted["api_key"] == REDACTED_PLACEHOLDER
        assert redacted["project_id"] == "67890"
