"""Unit tests for Snowflake tag extraction and mapping."""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from src.parsers.snowflake_parser import SnowflakeParser, DEFAULT_TAG_MAPPINGS
from src.parsers.snowflake_config import SnowflakeParserConfig
from src.parsers.base import ParseResult, RawCapsule, RawColumn


class TestSnowflakeTagMapping:
    """Tests for Snowflake tag mapping functionality."""

    def test_default_tag_mappings_pii(self):
        """Test default PII tag mapping."""
        parser = SnowflakeParser()
        config = SnowflakeParserConfig(
            account="test", user="test", password="test"
        )

        mapping = parser._map_tag_to_semantic_type("PII", config)
        assert mapping is not None
        assert mapping["semantic_type"] == "pii"
        assert mapping.get("infer_pii_type") is True

    def test_default_tag_mappings_pii_email(self):
        """Test default PII:EMAIL tag mapping."""
        parser = SnowflakeParser()
        config = SnowflakeParserConfig(
            account="test", user="test", password="test"
        )

        mapping = parser._map_tag_to_semantic_type("PII:EMAIL", config)
        assert mapping is not None
        assert mapping["semantic_type"] == "pii"
        assert mapping["pii_type"] == "email"

    def test_default_tag_mappings_primary_key(self):
        """Test default PRIMARY_KEY tag mapping."""
        parser = SnowflakeParser()
        config = SnowflakeParserConfig(
            account="test", user="test", password="test"
        )

        mapping = parser._map_tag_to_semantic_type("PRIMARY_KEY", config)
        assert mapping is not None
        assert mapping["semantic_type"] == "business_key"
        assert "pii_type" not in mapping

    def test_default_tag_mappings_case_insensitive(self):
        """Test tag mapping is case-insensitive."""
        parser = SnowflakeParser()
        config = SnowflakeParserConfig(
            account="test", user="test", password="test"
        )

        # Lowercase
        mapping = parser._map_tag_to_semantic_type("pii:email", config)
        assert mapping is not None
        assert mapping["semantic_type"] == "pii"
        assert mapping["pii_type"] == "email"

        # Mixed case
        mapping = parser._map_tag_to_semantic_type("Pii:Email", config)
        assert mapping is not None
        assert mapping["semantic_type"] == "pii"

    def test_custom_tag_mapping_overrides_default(self):
        """Test custom tag mapping overrides default."""
        parser = SnowflakeParser()
        config = SnowflakeParserConfig(
            account="test",
            user="test",
            password="test",
            tag_mappings={
                "PII": {"semantic_type": "custom_pii", "pii_type": "custom"}
            }
        )

        mapping = parser._map_tag_to_semantic_type("PII", config)
        assert mapping is not None
        assert mapping["semantic_type"] == "custom_pii"
        assert mapping["pii_type"] == "custom"

    def test_custom_tag_mapping_new_tag(self):
        """Test custom tag mapping for new tag."""
        parser = SnowflakeParser()
        config = SnowflakeParserConfig(
            account="test",
            user="test",
            password="test",
            tag_mappings={
                "CUSTOM_TAG": {"semantic_type": "custom_type"}
            }
        )

        mapping = parser._map_tag_to_semantic_type("CUSTOM_TAG", config)
        assert mapping is not None
        assert mapping["semantic_type"] == "custom_type"

    def test_unknown_tag_returns_none(self):
        """Test unknown tag returns None."""
        parser = SnowflakeParser()
        config = SnowflakeParserConfig(
            account="test", user="test", password="test"
        )

        mapping = parser._map_tag_to_semantic_type("UNKNOWN_TAG", config)
        assert mapping is None


class TestSnowflakePIIInference:
    """Tests for PII type inference from column names."""

    def test_infer_email_patterns(self):
        """Test email pattern inference."""
        parser = SnowflakeParser()

        assert parser._infer_pii_type("email") == "email"
        assert parser._infer_pii_type("EMAIL") == "email"
        assert parser._infer_pii_type("user_email") == "email"
        assert parser._infer_pii_type("e_mail") == "email"
        assert parser._infer_pii_type("contact_mail") == "email"

    def test_infer_phone_patterns(self):
        """Test phone pattern inference."""
        parser = SnowflakeParser()

        assert parser._infer_pii_type("phone") == "phone"
        assert parser._infer_pii_type("phone_number") == "phone"
        assert parser._infer_pii_type("mobile") == "phone"
        assert parser._infer_pii_type("cell_phone") == "phone"
        assert parser._infer_pii_type("telephone") == "phone"

    def test_infer_ssn_patterns(self):
        """Test SSN pattern inference."""
        parser = SnowflakeParser()

        assert parser._infer_pii_type("ssn") == "ssn"
        assert parser._infer_pii_type("social_security_number") == "ssn"
        assert parser._infer_pii_type("SSN") == "ssn"

    def test_infer_address_patterns(self):
        """Test address pattern inference."""
        parser = SnowflakeParser()

        assert parser._infer_pii_type("address") == "address"
        assert parser._infer_pii_type("street_address") == "address"
        assert parser._infer_pii_type("city") == "address"
        assert parser._infer_pii_type("state") == "address"
        assert parser._infer_pii_type("zip_code") == "address"
        assert parser._infer_pii_type("postal_addr") == "address"

    def test_infer_name_patterns(self):
        """Test name pattern inference."""
        parser = SnowflakeParser()

        assert parser._infer_pii_type("first_name") == "name"
        assert parser._infer_pii_type("last_name") == "name"
        assert parser._infer_pii_type("full_name") == "name"
        assert parser._infer_pii_type("username") == "name"

    def test_infer_credit_card_patterns(self):
        """Test credit card pattern inference."""
        parser = SnowflakeParser()

        assert parser._infer_pii_type("credit_card") == "credit_card"
        assert parser._infer_pii_type("cc_number") == "credit_card"
        assert parser._infer_pii_type("card_number") == "credit_card"

    def test_infer_ip_address_patterns(self):
        """Test IP address pattern inference."""
        parser = SnowflakeParser()

        assert parser._infer_pii_type("ip_address") == "ip_address"
        assert parser._infer_pii_type("ip_addr") == "ip_address"

    def test_infer_no_match_returns_none(self):
        """Test non-PII column returns None."""
        parser = SnowflakeParser()

        assert parser._infer_pii_type("id") is None
        assert parser._infer_pii_type("created_at") is None
        assert parser._infer_pii_type("amount") is None
        assert parser._infer_pii_type("status") is None


class TestSnowflakeTagExtraction:
    """Tests for Snowflake tag extraction."""

    @pytest.mark.asyncio
    async def test_extract_tags_basic(self):
        """Test basic tag extraction."""
        parser = SnowflakeParser()
        config = SnowflakeParserConfig(
            account="test",
            user="test",
            password="test",
            enable_tag_extraction=True,
            use_account_usage=True,
        )

        # Create parse result with capsules and columns
        result = ParseResult(source_type="snowflake")
        capsule = RawCapsule(
            urn="urn:dcs:snowflake:table:PROD.RAW:CUSTOMERS",
            name="CUSTOMERS",
            capsule_type="table",
            unique_id="PROD.RAW.CUSTOMERS",
            database_name="PROD",
            schema_name="RAW",
        )
        result.capsules.append(capsule)

        column = RawColumn(
            urn="urn:dcs:snowflake:column:PROD.RAW:CUSTOMERS.email",
            capsule_urn=capsule.urn,
            name="email",
            data_type="VARCHAR",
        )
        result.columns.append(column)

        # Mock tag query results
        tag_data = [
            {
                "tag_database": "PROD",
                "tag_schema": "GOVERNANCE",
                "tag_name": "PII",
                "tag_value": "EMAIL",
                "object_database": "PROD",
                "object_schema": "RAW",
                "object_name": "CUSTOMERS",
                "column_name": "email",
                "domain": "COLUMN",
            }
        ]

        with patch.object(parser, "_query_tags", return_value=tag_data):
            await parser._extract_tags(config, result, ["PROD"])

        # Verify tag was applied
        assert column.semantic_type == "pii"
        assert column.pii_type == "email"
        assert column.pii_detected_by == "snowflake_tag"

    @pytest.mark.asyncio
    async def test_extract_tags_with_inference(self):
        """Test tag extraction with PII type inference."""
        parser = SnowflakeParser()
        config = SnowflakeParserConfig(
            account="test",
            user="test",
            password="test",
            enable_tag_extraction=True,
            use_account_usage=True,
        )

        result = ParseResult(source_type="snowflake")
        capsule = RawCapsule(
            urn="urn:dcs:snowflake:table:PROD.RAW:CUSTOMERS",
            name="CUSTOMERS",
            capsule_type="table",
            unique_id="PROD.RAW.CUSTOMERS",
            database_name="PROD",
            schema_name="RAW",
        )
        result.capsules.append(capsule)

        column = RawColumn(
            urn="urn:dcs:snowflake:column:PROD.RAW:CUSTOMERS.user_email",
            capsule_urn=capsule.urn,
            name="user_email",
            data_type="VARCHAR",
        )
        result.columns.append(column)

        # Mock tag query with generic PII tag (no specific type)
        tag_data = [
            {
                "tag_database": "PROD",
                "tag_schema": "GOVERNANCE",
                "tag_name": "PII",
                "tag_value": None,
                "object_database": "PROD",
                "object_schema": "RAW",
                "object_name": "CUSTOMERS",
                "column_name": "user_email",
                "domain": "COLUMN",
            }
        ]

        with patch.object(parser, "_query_tags", return_value=tag_data):
            await parser._extract_tags(config, result, ["PROD"])

        # Verify tag was applied with inferred type
        assert column.semantic_type == "pii"
        assert column.pii_type == "email"  # Inferred from column name
        assert column.pii_detected_by == "snowflake_tag_inferred"

    @pytest.mark.asyncio
    async def test_extract_tags_custom_mapping(self):
        """Test tag extraction with custom mapping."""
        parser = SnowflakeParser()
        config = SnowflakeParserConfig(
            account="test",
            user="test",
            password="test",
            enable_tag_extraction=True,
            use_account_usage=True,
            tag_mappings={
                "CUSTOM_TAG": {"semantic_type": "custom", "pii_type": "custom_pii"}
            }
        )

        result = ParseResult(source_type="snowflake")
        capsule = RawCapsule(
            urn="urn:dcs:snowflake:table:PROD.RAW:CUSTOMERS",
            name="CUSTOMERS",
            capsule_type="table",
            unique_id="PROD.RAW.CUSTOMERS",
            database_name="PROD",
            schema_name="RAW",
        )
        result.capsules.append(capsule)

        column = RawColumn(
            urn="urn:dcs:snowflake:column:PROD.RAW:CUSTOMERS.custom_field",
            capsule_urn=capsule.urn,
            name="custom_field",
            data_type="VARCHAR",
        )
        result.columns.append(column)

        tag_data = [
            {
                "tag_database": "PROD",
                "tag_schema": "GOVERNANCE",
                "tag_name": "CUSTOM_TAG",
                "tag_value": None,
                "object_database": "PROD",
                "object_schema": "RAW",
                "object_name": "CUSTOMERS",
                "column_name": "custom_field",
                "domain": "COLUMN",
            }
        ]

        with patch.object(parser, "_query_tags", return_value=tag_data):
            await parser._extract_tags(config, result, ["PROD"])

        # Verify custom mapping was applied
        assert column.semantic_type == "custom"
        assert column.pii_type == "custom_pii"
        assert column.pii_detected_by == "snowflake_tag"

    @pytest.mark.asyncio
    async def test_extract_tags_skip_table_level(self):
        """Test tag extraction skips table-level tags."""
        parser = SnowflakeParser()
        config = SnowflakeParserConfig(
            account="test",
            user="test",
            password="test",
            enable_tag_extraction=True,
            use_account_usage=True,
        )

        result = ParseResult(source_type="snowflake")

        # Mock tag query with table-level tag (no column_name)
        tag_data = [
            {
                "tag_database": "PROD",
                "tag_schema": "GOVERNANCE",
                "tag_name": "SENSITIVE",
                "tag_value": None,
                "object_database": "PROD",
                "object_schema": "RAW",
                "object_name": "CUSTOMERS",
                "column_name": None,  # Table-level tag
                "domain": "TABLE",
            }
        ]

        with patch.object(parser, "_query_tags", return_value=tag_data):
            await parser._extract_tags(config, result, ["PROD"])

        # No errors should be added
        assert len(result.errors) == 0

    @pytest.mark.asyncio
    async def test_extract_tags_skip_missing_column(self):
        """Test tag extraction handles missing columns gracefully."""
        parser = SnowflakeParser()
        config = SnowflakeParserConfig(
            account="test",
            user="test",
            password="test",
            enable_tag_extraction=True,
            use_account_usage=True,
        )

        result = ParseResult(source_type="snowflake")
        # No columns in result

        # Mock tag query with tag for non-existent column
        tag_data = [
            {
                "tag_database": "PROD",
                "tag_schema": "GOVERNANCE",
                "tag_name": "PII",
                "tag_value": "EMAIL",
                "object_database": "PROD",
                "object_schema": "RAW",
                "object_name": "CUSTOMERS",
                "column_name": "email",
                "domain": "COLUMN",
            }
        ]

        with patch.object(parser, "_query_tags", return_value=tag_data):
            await parser._extract_tags(config, result, ["PROD"])

        # Should not crash, just log debug message
        assert len(result.errors) == 0

    @pytest.mark.asyncio
    async def test_extract_tags_error_handling(self):
        """Test tag extraction handles query errors gracefully."""
        parser = SnowflakeParser()
        config = SnowflakeParserConfig(
            account="test",
            user="test",
            password="test",
            enable_tag_extraction=True,
            use_account_usage=True,
        )

        result = ParseResult(source_type="snowflake")

        # Mock query failure
        with patch.object(parser, "_query_tags", side_effect=Exception("Query failed")):
            await parser._extract_tags(config, result, ["PROD"])

        # Should add error to result
        assert len(result.errors) > 0
        assert any("tag" in str(e).lower() for e in result.errors)

    @pytest.mark.asyncio
    async def test_extract_tags_multiple_columns(self):
        """Test extracting tags for multiple columns."""
        parser = SnowflakeParser()
        config = SnowflakeParserConfig(
            account="test",
            user="test",
            password="test",
            enable_tag_extraction=True,
            use_account_usage=True,
        )

        result = ParseResult(source_type="snowflake")
        capsule = RawCapsule(
            urn="urn:dcs:snowflake:table:PROD.RAW:CUSTOMERS",
            name="CUSTOMERS",
            capsule_type="table",
            unique_id="PROD.RAW.CUSTOMERS",
            database_name="PROD",
            schema_name="RAW",
        )
        result.capsules.append(capsule)

        email_col = RawColumn(
            urn="urn:dcs:snowflake:column:PROD.RAW:CUSTOMERS.email",
            capsule_urn=capsule.urn,
            name="email",
            data_type="VARCHAR",
        )
        phone_col = RawColumn(
            urn="urn:dcs:snowflake:column:PROD.RAW:CUSTOMERS.phone",
            capsule_urn=capsule.urn,
            name="phone",
            data_type="VARCHAR",
        )
        result.columns.extend([email_col, phone_col])

        # Mock tags for both columns
        tag_data = [
            {
                "tag_database": "PROD",
                "tag_schema": "GOVERNANCE",
                "tag_name": "PII",
                "tag_value": "EMAIL",
                "object_database": "PROD",
                "object_schema": "RAW",
                "object_name": "CUSTOMERS",
                "column_name": "email",
                "domain": "COLUMN",
            },
            {
                "tag_database": "PROD",
                "tag_schema": "GOVERNANCE",
                "tag_name": "PII",
                "tag_value": "PHONE",
                "object_database": "PROD",
                "object_schema": "RAW",
                "object_name": "CUSTOMERS",
                "column_name": "phone",
                "domain": "COLUMN",
            },
        ]

        with patch.object(parser, "_query_tags", return_value=tag_data):
            await parser._extract_tags(config, result, ["PROD"])

        # Verify both columns were tagged
        assert email_col.semantic_type == "pii"
        assert email_col.pii_type == "email"
        assert phone_col.semantic_type == "pii"
        assert phone_col.pii_type == "phone"

    @pytest.mark.asyncio
    async def test_query_tags_with_database_filter(self):
        """Test tag query builds correct database filter."""
        parser = SnowflakeParser()
        parser.connector = MagicMock()

        config = SnowflakeParserConfig(
            account="test",
            user="test",
            password="test",
        )

        # Mock cursor
        mock_cursor = MagicMock()
        mock_cursor.description = [
            ("tag_database",), ("tag_name",), ("object_database",)
        ]
        mock_cursor.fetchall.return_value = []
        parser.connector.cursor.return_value = mock_cursor

        await parser._query_tags(config, ["PROD", "ANALYTICS"])

        # Verify execute was called with database filter
        execute_call = mock_cursor.execute.call_args
        query = execute_call[0][0]
        assert "'PROD'" in query
        assert "'ANALYTICS'" in query
        assert "OBJECT_DATABASE IN" in query

    @pytest.mark.asyncio
    async def test_query_tags_no_database_filter(self):
        """Test tag query without database filter."""
        parser = SnowflakeParser()
        parser.connector = MagicMock()

        config = SnowflakeParserConfig(
            account="test",
            user="test",
            password="test",
        )

        mock_cursor = MagicMock()
        mock_cursor.description = [("tag_database",), ("tag_name",)]
        mock_cursor.fetchall.return_value = []
        parser.connector.cursor.return_value = mock_cursor

        await parser._query_tags(config, [])

        # Verify execute was called without database filter
        execute_call = mock_cursor.execute.call_args
        query = execute_call[0][0]
        # Should not have database filter when empty list
        assert "AND OBJECT_DATABASE IN ()" not in query
