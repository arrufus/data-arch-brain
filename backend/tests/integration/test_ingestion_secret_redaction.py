"""Integration tests for secret redaction in ingestion jobs."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.ingestion import IngestionJobRepository
from src.services.secret_redaction import REDACTED_PLACEHOLDER


class TestIngestionJobSecretRedaction:
    """Integration tests for secret redaction in ingestion job persistence."""

    @pytest.mark.asyncio
    async def test_start_job_redacts_token(self, test_session: AsyncSession) -> None:
        """Test that token is redacted when starting an ingestion job."""
        repo = IngestionJobRepository(test_session)

        config = {
            "base_url": "https://api.example.com",
            "token": "super-secret-token-123",
        }

        job = await repo.start_job(
            source_type="airflow",
            source_name="prod-airflow",
            config=config,
        )

        # Verify job was created
        assert job.id is not None
        assert job.source_type == "airflow"
        assert job.source_name == "prod-airflow"

        # Verify token is redacted in persisted config
        assert job.config["base_url"] == "https://api.example.com"
        assert job.config["token"] == REDACTED_PLACEHOLDER

        # Verify original config was not mutated
        assert config["token"] == "super-secret-token-123"

    @pytest.mark.asyncio
    async def test_start_job_redacts_password(self, test_session: AsyncSession) -> None:
        """Test that password is redacted when starting an ingestion job."""
        repo = IngestionJobRepository(test_session)

        config = {
            "host": "db.example.com",
            "username": "db_user",
            "password": "super-secret-password",
        }

        job = await repo.start_job(
            source_type="dbt",
            source_name="analytics",
            config=config,
        )

        # Verify password is redacted
        assert job.config["host"] == "db.example.com"
        assert job.config["username"] == "db_user"
        assert job.config["password"] == REDACTED_PLACEHOLDER

    @pytest.mark.asyncio
    async def test_start_job_redacts_multiple_secrets(
        self, test_session: AsyncSession
    ) -> None:
        """Test that multiple secret fields are redacted."""
        repo = IngestionJobRepository(test_session)

        config = {
            "base_url": "https://api.example.com",
            "api_key": "secret-api-key",
            "secret": "secret-value",
            "authorization": "Bearer secret-token",
            "public_field": "public-value",
        }

        job = await repo.start_job(
            source_type="airflow",
            config=config,
        )

        # Verify all secrets are redacted
        assert job.config["api_key"] == REDACTED_PLACEHOLDER
        assert job.config["secret"] == REDACTED_PLACEHOLDER
        assert job.config["authorization"] == REDACTED_PLACEHOLDER

        # Verify public field is not redacted
        assert job.config["public_field"] == "public-value"

    @pytest.mark.asyncio
    async def test_start_job_redacts_nested_secrets(
        self, test_session: AsyncSession
    ) -> None:
        """Test that nested secret fields are redacted."""
        repo = IngestionJobRepository(test_session)

        config = {
            "base_url": "https://api.example.com",
            "auth": {
                "mode": "bearer",
                "token": "nested-secret-token",
                "credentials": {
                    "username": "user",
                    "password": "nested-password",
                },
            },
        }

        job = await repo.start_job(
            source_type="airflow",
            config=config,
        )

        # Verify nested secrets are redacted
        assert job.config["auth"]["mode"] == "bearer"
        assert job.config["auth"]["token"] == REDACTED_PLACEHOLDER
        assert job.config["auth"]["credentials"]["username"] == "user"
        assert job.config["auth"]["credentials"]["password"] == REDACTED_PLACEHOLDER

    @pytest.mark.asyncio
    async def test_start_job_redacts_secrets_in_list(
        self, test_session: AsyncSession
    ) -> None:
        """Test that secrets in list items are redacted."""
        repo = IngestionJobRepository(test_session)

        config = {
            "connections": [
                {"name": "conn1", "token": "secret1"},
                {"name": "conn2", "api_key": "secret2"},
            ]
        }

        job = await repo.start_job(
            source_type="airflow",
            config=config,
        )

        # Verify secrets in list items are redacted
        assert job.config["connections"][0]["name"] == "conn1"
        assert job.config["connections"][0]["token"] == REDACTED_PLACEHOLDER
        assert job.config["connections"][1]["name"] == "conn2"
        assert job.config["connections"][1]["api_key"] == REDACTED_PLACEHOLDER

    @pytest.mark.asyncio
    async def test_start_job_with_empty_config(
        self, test_session: AsyncSession
    ) -> None:
        """Test that empty config is handled correctly."""
        repo = IngestionJobRepository(test_session)

        job = await repo.start_job(
            source_type="dbt",
            source_name="test",
            config={},
        )

        # Verify job was created with empty config
        assert job.config == {}

    @pytest.mark.asyncio
    async def test_start_job_with_none_config(
        self, test_session: AsyncSession
    ) -> None:
        """Test that None config is handled correctly."""
        repo = IngestionJobRepository(test_session)

        job = await repo.start_job(
            source_type="dbt",
            source_name="test",
            config=None,
        )

        # Verify job was created with empty config
        assert job.config == {}

    @pytest.mark.asyncio
    async def test_airflow_bearer_auth_config_redaction(
        self, test_session: AsyncSession
    ) -> None:
        """Test Airflow bearer auth config is properly redacted."""
        repo = IngestionJobRepository(test_session)

        config = {
            "base_url": "https://airflow.example.com",
            "instance_name": "prod-airflow",
            "auth_mode": "bearer_env",
            "token_env": "AIRFLOW_TOKEN",
            # This should never be in config, but test defensive redaction
            "token": "actual-secret-token",
        }

        job = await repo.start_job(
            source_type="airflow",
            source_name="prod-airflow",
            config=config,
        )

        # Verify safe fields are preserved
        assert job.config["base_url"] == "https://airflow.example.com"
        assert job.config["instance_name"] == "prod-airflow"
        assert job.config["auth_mode"] == "bearer_env"
        # token_env contains "token" so it gets redacted (safe behavior)
        assert job.config["token_env"] == REDACTED_PLACEHOLDER

        # Verify token is redacted
        assert job.config["token"] == REDACTED_PLACEHOLDER

    @pytest.mark.asyncio
    async def test_airflow_basic_auth_config_redaction(
        self, test_session: AsyncSession
    ) -> None:
        """Test Airflow basic auth config is properly redacted."""
        repo = IngestionJobRepository(test_session)

        config = {
            "base_url": "https://airflow.example.com",
            "instance_name": "prod-airflow",
            "auth_mode": "basic_env",
            "username_env": "AIRFLOW_USERNAME",
            "password_env": "AIRFLOW_PASSWORD",
            # These should never be in config, but test defensive redaction
            "username": "admin",
            "password": "super-secret",
        }

        job = await repo.start_job(
            source_type="airflow",
            source_name="prod-airflow",
            config=config,
        )

        # Verify safe fields are preserved
        assert job.config["base_url"] == "https://airflow.example.com"
        assert job.config["auth_mode"] == "basic_env"
        assert job.config["username_env"] == "AIRFLOW_USERNAME"
        # password_env contains "password" so it gets redacted (safe behavior)
        assert job.config["password_env"] == REDACTED_PLACEHOLDER

        # Username is not redacted (not considered secret)
        assert job.config["username"] == "admin"

        # Password must be redacted
        assert job.config["password"] == REDACTED_PLACEHOLDER

    @pytest.mark.asyncio
    async def test_dbt_profiles_with_password_redaction(
        self, test_session: AsyncSession
    ) -> None:
        """Test dbt profiles with database passwords are redacted."""
        repo = IngestionJobRepository(test_session)

        config = {
            "project_dir": "/path/to/project",
            "profiles_dir": "/path/to/.dbt",
            "target": "production",
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

        job = await repo.start_job(
            source_type="dbt",
            source_name="analytics",
            config=config,
        )

        # Verify safe fields are preserved
        assert job.config["project_dir"] == "/path/to/project"
        assert job.config["profiles"]["production"]["host"] == "db.example.com"
        assert job.config["profiles"]["production"]["user"] == "dbt_user"

        # Password must be redacted
        assert job.config["profiles"]["production"]["password"] == REDACTED_PLACEHOLDER

    @pytest.mark.asyncio
    async def test_complex_nested_config_with_mixed_secrets(
        self, test_session: AsyncSession
    ) -> None:
        """Test complex nested configuration with secrets at various levels."""
        repo = IngestionJobRepository(test_session)

        config = {
            "source": "airflow",
            "instance": {
                "name": "prod",
                "url": "https://airflow.example.com",
                "credentials": {
                    "type": "oauth",
                    "client_id": "client123",
                    "client_secret": "oauth-secret",
                    "token": "access-token-123",
                },
            },
            "filters": {
                "dag_ids": ["dag1", "dag2"],
                "tags": ["production"],
            },
            "connections": [
                {
                    "name": "postgres",
                    "conn_type": "postgres",
                    "extra": {
                        "api_key": "postgres-api-key",
                    },
                },
            ],
            "metadata": {
                "owner": "data-team",
                "version": "1.0",
            },
        }

        job = await repo.start_job(
            source_type="airflow",
            source_name="prod",
            config=config,
        )

        # Verify structure is preserved
        assert job.config["source"] == "airflow"
        assert job.config["instance"]["name"] == "prod"
        assert job.config["instance"]["url"] == "https://airflow.example.com"
        assert job.config["filters"]["dag_ids"] == ["dag1", "dag2"]
        assert job.config["metadata"]["owner"] == "data-team"

        # Verify all secrets are redacted at various nesting levels
        assert (
            job.config["instance"]["credentials"]["client_secret"]
            == REDACTED_PLACEHOLDER
        )
        assert job.config["instance"]["credentials"]["token"] == REDACTED_PLACEHOLDER
        assert job.config["connections"][0]["extra"]["api_key"] == REDACTED_PLACEHOLDER

        # Verify non-secrets are preserved
        assert job.config["instance"]["credentials"]["client_id"] == "client123"

    @pytest.mark.asyncio
    async def test_case_insensitive_secret_keys(
        self, test_session: AsyncSession
    ) -> None:
        """Test that secret keys are matched case-insensitively."""
        repo = IngestionJobRepository(test_session)

        config = {
            "TOKEN": "secret1",
            "Token": "secret2",
            "token": "secret3",
            "PASSWORD": "secret4",
            "Password": "secret5",
            "password": "secret6",
        }

        job = await repo.start_job(
            source_type="test",
            config=config,
        )

        # All variations should be redacted
        assert job.config["TOKEN"] == REDACTED_PLACEHOLDER
        assert job.config["Token"] == REDACTED_PLACEHOLDER
        assert job.config["token"] == REDACTED_PLACEHOLDER
        assert job.config["PASSWORD"] == REDACTED_PLACEHOLDER
        assert job.config["Password"] == REDACTED_PLACEHOLDER
        assert job.config["password"] == REDACTED_PLACEHOLDER

    @pytest.mark.asyncio
    async def test_pattern_based_secret_keys(
        self, test_session: AsyncSession
    ) -> None:
        """Test that secret patterns in keys are detected and redacted."""
        repo = IngestionJobRepository(test_session)

        config = {
            "my_token": "secret1",
            "user_password": "secret2",
            "api_key_prod": "secret3",
            "service_secret": "secret4",
            "bearer_token_refresh": "secret5",
        }

        job = await repo.start_job(
            source_type="test",
            config=config,
        )

        # All should be redacted due to pattern matching
        assert job.config["my_token"] == REDACTED_PLACEHOLDER
        assert job.config["user_password"] == REDACTED_PLACEHOLDER
        assert job.config["api_key_prod"] == REDACTED_PLACEHOLDER
        assert job.config["service_secret"] == REDACTED_PLACEHOLDER
        assert job.config["bearer_token_refresh"] == REDACTED_PLACEHOLDER
