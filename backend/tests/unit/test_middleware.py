"""Tests for middleware functions."""

import pytest

from src.api.middleware import (
    sanitize_search_query,
    sanitize_string,
    validate_layer,
    validate_capsule_type,
    validate_pagination,
    validate_severity,
    validate_urn,
    validate_uuid,
)


class TestSanitizeString:
    """Tests for string sanitization."""

    def test_empty_string(self):
        """Test empty string returns empty."""
        assert sanitize_string("") == ""
        assert sanitize_string(None) is None

    def test_normal_string(self):
        """Test normal string is unchanged."""
        assert sanitize_string("hello world") == "hello world"
        assert sanitize_string("user_name") == "user_name"

    def test_removes_script_tags(self):
        """Test XSS script tags are removed."""
        result = sanitize_string("<script>alert('xss')</script>")
        assert "<script>" not in result
        assert "</script>" not in result

    def test_removes_sql_comments(self):
        """Test SQL comments are removed."""
        result = sanitize_string("value -- comment")
        assert "--" not in result

    def test_removes_null_bytes(self):
        """Test null bytes are removed."""
        result = sanitize_string("value\x00with\x00nulls")
        assert "\x00" not in result
        assert result == "valuewithnulls"


class TestSanitizeSearchQuery:
    """Tests for search query sanitization."""

    def test_empty_query(self):
        """Test empty query returns empty."""
        assert sanitize_search_query("") == ""
        assert sanitize_search_query(None) is None

    def test_normal_query(self):
        """Test normal query is preserved."""
        assert sanitize_search_query("customers") == "customers"
        assert sanitize_search_query("stg orders") == "stg orders"

    def test_escapes_wildcards(self):
        """Test SQL LIKE wildcards are escaped."""
        result = sanitize_search_query("100%")
        assert "%" in result  # Still contains but escaped
        result = sanitize_search_query("user_name")
        assert "_" in result  # Still contains but escaped

    def test_truncates_long_query(self):
        """Test long queries are truncated."""
        long_query = "a" * 300
        result = sanitize_search_query(long_query, max_length=200)
        assert len(result) <= 200

    def test_strips_whitespace(self):
        """Test whitespace is stripped."""
        result = sanitize_search_query("  customer  ")
        assert result == "customer"


class TestValidateUrn:
    """Tests for URN validation."""

    def test_valid_urn(self):
        """Test valid URN format."""
        assert validate_urn("urn:dab:dbt:model:project.schema:name") is True
        assert validate_urn("urn:dab:dbt:source:project.raw:source_name") is True

    def test_invalid_urn(self):
        """Test invalid URN formats."""
        assert validate_urn("not-a-urn") is False
        assert validate_urn("urn:dab") is False
        assert validate_urn("") is False


class TestValidateUuid:
    """Tests for UUID validation."""

    def test_valid_uuid(self):
        """Test valid UUID format."""
        assert validate_uuid("550e8400-e29b-41d4-a716-446655440000") is True
        assert validate_uuid("550E8400-E29B-41D4-A716-446655440000") is True  # Uppercase

    def test_invalid_uuid(self):
        """Test invalid UUID formats."""
        assert validate_uuid("not-a-uuid") is False
        assert validate_uuid("550e8400-e29b-41d4-a716") is False  # Too short
        assert validate_uuid("") is False


class TestValidateLayer:
    """Tests for layer validation."""

    def test_valid_layers(self):
        """Test valid layer names."""
        assert validate_layer("bronze") is True
        assert validate_layer("silver") is True
        assert validate_layer("gold") is True
        assert validate_layer("BRONZE") is True  # Case insensitive

    def test_invalid_layers(self):
        """Test invalid layer names."""
        assert validate_layer("invalid") is False
        assert validate_layer("platinum") is False
        assert validate_layer("") is False


class TestValidateCapsuleType:
    """Tests for capsule type validation."""

    def test_valid_types(self):
        """Test valid capsule types."""
        assert validate_capsule_type("model") is True
        assert validate_capsule_type("source") is True
        assert validate_capsule_type("seed") is True
        assert validate_capsule_type("MODEL") is True  # Case insensitive

    def test_invalid_types(self):
        """Test invalid capsule types."""
        assert validate_capsule_type("table") is False
        assert validate_capsule_type("view") is False
        assert validate_capsule_type("") is False


class TestValidateSeverity:
    """Tests for severity validation."""

    def test_valid_severities(self):
        """Test valid severity levels."""
        assert validate_severity("critical") is True
        assert validate_severity("error") is True
        assert validate_severity("warning") is True
        assert validate_severity("info") is True
        assert validate_severity("CRITICAL") is True  # Case insensitive

    def test_invalid_severities(self):
        """Test invalid severity levels."""
        assert validate_severity("high") is False
        assert validate_severity("low") is False
        assert validate_severity("") is False


class TestValidatePagination:
    """Tests for pagination validation."""

    def test_valid_pagination(self):
        """Test valid pagination values."""
        offset, limit = validate_pagination(0, 50)
        assert offset == 0
        assert limit == 50

    def test_negative_offset(self):
        """Test negative offset is normalized to 0."""
        offset, limit = validate_pagination(-10, 50)
        assert offset == 0
        assert limit == 50

    def test_negative_limit(self):
        """Test negative limit is normalized to 1."""
        offset, limit = validate_pagination(0, -5)
        assert offset == 0
        assert limit == 1

    def test_limit_exceeds_max(self):
        """Test limit exceeding max is capped."""
        offset, limit = validate_pagination(0, 5000, max_limit=1000)
        assert offset == 0
        assert limit == 1000

    def test_custom_max_limit(self):
        """Test custom max limit."""
        offset, limit = validate_pagination(0, 200, max_limit=100)
        assert limit == 100
