"""Unit tests for the dbt parser."""

from pathlib import Path

import pytest

from src.parsers import (
    DbtParser,
    DbtParserConfig,
    PIIPattern,
    LayerPattern,
    ParseResult,
    get_parser,
    available_parsers,
)


# Fixture paths
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "dbt"
MANIFEST_PATH = FIXTURES_DIR / "manifest.json"
CATALOG_PATH = FIXTURES_DIR / "catalog.json"


@pytest.fixture
def dbt_parser() -> DbtParser:
    """Create a dbt parser instance."""
    return DbtParser()


@pytest.fixture
def parser_config() -> dict:
    """Create a basic parser config dictionary."""
    return {
        "manifest_path": str(MANIFEST_PATH),
        "catalog_path": str(CATALOG_PATH),
    }


@pytest.fixture
def parser_config_no_catalog() -> dict:
    """Create a parser config without catalog."""
    return {
        "manifest_path": str(MANIFEST_PATH),
    }


class TestParserRegistry:
    """Tests for the parser registry."""

    def test_dbt_parser_registered(self):
        """Test that dbt parser is registered."""
        assert "dbt" in available_parsers()

    def test_get_dbt_parser(self):
        """Test getting dbt parser from registry."""
        parser = get_parser("dbt")
        assert isinstance(parser, DbtParser)

    def test_get_unknown_parser_raises(self):
        """Test that unknown parser raises ValueError."""
        with pytest.raises(ValueError, match="No parser registered"):
            get_parser("unknown_source")


class TestDbtParserConfig:
    """Tests for dbt parser configuration."""

    def test_from_dict_minimal(self):
        """Test creating config with minimal options."""
        config = DbtParserConfig.from_dict({"manifest_path": str(MANIFEST_PATH)})
        assert config.manifest_path == MANIFEST_PATH
        assert config.catalog_path is None
        assert config.pii_detection_enabled is True

    def test_from_dict_with_catalog(self, parser_config):
        """Test creating config with catalog path."""
        config = DbtParserConfig.from_dict(parser_config)
        assert config.manifest_path == MANIFEST_PATH
        assert config.catalog_path == CATALOG_PATH

    def test_from_dict_with_options(self):
        """Test creating config with various options."""
        config = DbtParserConfig.from_dict({
            "manifest_path": str(MANIFEST_PATH),
            "project_name": "test_project",
            "pii_detection_enabled": False,
            "include_sources": False,
            "include_seeds": False,
        })
        assert config.project_name == "test_project"
        assert config.pii_detection_enabled is False
        assert config.include_sources is False
        assert config.include_seeds is False

    def test_validate_missing_manifest(self, tmp_path):
        """Test validation fails for missing manifest."""
        config = DbtParserConfig(
            manifest_path=tmp_path / "nonexistent.json"
        )
        errors = config.validate()
        assert len(errors) == 1
        assert "Manifest file not found" in errors[0]

    def test_validate_invalid_extension(self, tmp_path):
        """Test validation fails for invalid file extension."""
        bad_file = tmp_path / "manifest.yaml"
        bad_file.touch()
        config = DbtParserConfig(manifest_path=bad_file)
        errors = config.validate()
        assert len(errors) == 1
        assert "must be JSON" in errors[0]


class TestPIIPattern:
    """Tests for PII pattern matching."""

    def test_email_pattern_matches(self):
        """Test email pattern matches email columns."""
        pattern = PIIPattern(
            pii_type="email",
            patterns=[r"(?:^|_)e?mail(?:_|$)", r"(?:^|_)email_address(?:_|$)"]
        )
        assert pattern.matches("email")
        assert pattern.matches("user_email")
        assert pattern.matches("email_address")
        assert pattern.matches("mail")
        assert not pattern.matches("emailing")
        assert not pattern.matches("mailing_list")

    def test_phone_pattern_matches(self):
        """Test phone pattern matches phone columns."""
        pattern = PIIPattern(
            pii_type="phone",
            patterns=[r"(?:^|_)phone(?:_|$)", r"(?:^|_)mobile(?:_|$)"]
        )
        assert pattern.matches("phone")
        assert pattern.matches("phone_number")
        assert pattern.matches("mobile")
        assert pattern.matches("user_phone")
        assert not pattern.matches("telephone_company")

    def test_ssn_pattern_matches(self):
        """Test SSN pattern matches SSN columns."""
        pattern = PIIPattern(
            pii_type="ssn",
            patterns=[r"(?:^|_)ssn(?:_|$)", r"(?:^|_)social_security(?:_|$)"]
        )
        assert pattern.matches("ssn")
        assert pattern.matches("user_ssn")
        assert pattern.matches("social_security")
        assert pattern.matches("social_security_number")

    def test_case_insensitive(self):
        """Test patterns are case insensitive."""
        pattern = PIIPattern(
            pii_type="email",
            patterns=[r"(?:^|_)email(?:_|$)"]
        )
        assert pattern.matches("EMAIL")
        assert pattern.matches("Email")
        assert pattern.matches("USER_EMAIL")


class TestLayerPattern:
    """Tests for layer pattern matching."""

    def test_bronze_name_patterns(self):
        """Test bronze layer name patterns."""
        pattern = LayerPattern(
            layer="bronze",
            name_patterns=[r"^raw_", r"^source_", r"_raw$"],
            path_patterns=[r"/raw/", r"/sources/"]
        )
        assert pattern.matches_name("raw_customers")
        assert pattern.matches_name("source_orders")
        assert pattern.matches_name("customers_raw")
        assert not pattern.matches_name("stg_customers")

    def test_silver_name_patterns(self):
        """Test silver layer name patterns."""
        pattern = LayerPattern(
            layer="silver",
            name_patterns=[r"^stg_", r"^int_", r"^staging_"],
            path_patterns=[r"/staging/", r"/intermediate/"]
        )
        assert pattern.matches_name("stg_customers")
        assert pattern.matches_name("int_customer_orders")
        assert pattern.matches_name("staging_orders")
        assert not pattern.matches_name("dim_customers")

    def test_gold_name_patterns(self):
        """Test gold layer name patterns."""
        pattern = LayerPattern(
            layer="gold",
            name_patterns=[r"^dim_", r"^fct_", r"^mart_"],
            path_patterns=[r"/marts/", r"/gold/"]
        )
        assert pattern.matches_name("dim_customers")
        assert pattern.matches_name("fct_orders")
        assert pattern.matches_name("mart_sales")
        assert not pattern.matches_name("stg_customers")

    def test_path_patterns(self):
        """Test path pattern matching."""
        pattern = LayerPattern(
            layer="gold",
            name_patterns=[],
            path_patterns=[r"/marts/", r"/gold/"]
        )
        assert pattern.matches_path("models/marts/core/dim_customers.sql")
        assert pattern.matches_path("/gold/analytics/report.sql")
        assert not pattern.matches_path("models/staging/stg_customers.sql")


class TestDbtParserValidation:
    """Tests for parser configuration validation."""

    def test_validate_config_missing_manifest(self, dbt_parser):
        """Test validation fails when manifest_path is missing."""
        errors = dbt_parser.validate_config({})
        assert len(errors) == 1
        assert "manifest_path is required" in errors[0]

    def test_validate_config_valid(self, dbt_parser, parser_config):
        """Test validation passes with valid config."""
        errors = dbt_parser.validate_config(parser_config)
        assert len(errors) == 0

    def test_source_type(self, dbt_parser):
        """Test parser source type is correct."""
        assert dbt_parser.source_type == "dbt"


class TestDbtParserParsing:
    """Tests for dbt manifest and catalog parsing."""

    @pytest.mark.asyncio
    async def test_parse_manifest(self, dbt_parser, parser_config):
        """Test parsing dbt manifest."""
        result = await dbt_parser.parse(parser_config)

        assert isinstance(result, ParseResult)
        assert result.source_type == "dbt"
        assert result.source_name == "jaffle_shop"
        assert result.source_version == "1.7.0"

    @pytest.mark.asyncio
    async def test_parse_models(self, dbt_parser, parser_config):
        """Test models are extracted correctly."""
        result = await dbt_parser.parse(parser_config)

        # Should have 5 models
        models = [c for c in result.capsules if c.capsule_type == "model"]
        assert len(models) == 5

        # Check model names
        model_names = {m.name for m in models}
        expected_names = {
            "stg_customers", "stg_orders", "int_customer_orders",
            "dim_customers", "fct_orders"
        }
        assert model_names == expected_names

    @pytest.mark.asyncio
    async def test_parse_sources(self, dbt_parser, parser_config):
        """Test sources are extracted correctly."""
        result = await dbt_parser.parse(parser_config)

        # Should have 2 sources
        sources = [c for c in result.capsules if c.capsule_type == "source"]
        assert len(sources) == 2

        # Check source names
        source_names = {s.name for s in sources}
        assert source_names == {"customers", "orders"}

        # Sources should be bronze layer
        for source in sources:
            assert source.layer == "bronze"

    @pytest.mark.asyncio
    async def test_parse_seeds(self, dbt_parser, parser_config):
        """Test seeds are extracted correctly."""
        result = await dbt_parser.parse(parser_config)

        # Should have 1 seed
        seeds = [c for c in result.capsules if c.capsule_type == "seed"]
        assert len(seeds) == 1
        assert seeds[0].name == "country_codes"
        assert seeds[0].layer == "bronze"  # Seeds are always bronze

    @pytest.mark.asyncio
    async def test_parse_without_catalog(self, dbt_parser, parser_config_no_catalog):
        """Test parsing without catalog still works."""
        result = await dbt_parser.parse(parser_config_no_catalog)

        assert not result.has_errors
        assert len(result.capsules) > 0

    @pytest.mark.asyncio
    async def test_invalid_manifest_path(self, dbt_parser, tmp_path):
        """Test parsing with invalid manifest path."""
        config = {"manifest_path": str(tmp_path / "nonexistent.json")}
        result = await dbt_parser.parse(config)

        assert result.has_errors
        assert result.error_count > 0


class TestLayerInference:
    """Tests for architecture layer inference."""

    @pytest.mark.asyncio
    async def test_staging_models_silver(self, dbt_parser, parser_config):
        """Test staging models are classified as silver."""
        result = await dbt_parser.parse(parser_config)

        stg_customers = next(
            c for c in result.capsules if c.name == "stg_customers"
        )
        stg_orders = next(
            c for c in result.capsules if c.name == "stg_orders"
        )

        assert stg_customers.layer == "silver"
        assert stg_orders.layer == "silver"

    @pytest.mark.asyncio
    async def test_intermediate_models_silver(self, dbt_parser, parser_config):
        """Test intermediate models are classified as silver."""
        result = await dbt_parser.parse(parser_config)

        int_model = next(
            c for c in result.capsules if c.name == "int_customer_orders"
        )
        assert int_model.layer == "silver"

    @pytest.mark.asyncio
    async def test_mart_models_gold(self, dbt_parser, parser_config):
        """Test mart models are classified as gold."""
        result = await dbt_parser.parse(parser_config)

        dim_customers = next(
            c for c in result.capsules if c.name == "dim_customers"
        )
        fct_orders = next(
            c for c in result.capsules if c.name == "fct_orders"
        )

        assert dim_customers.layer == "gold"
        assert fct_orders.layer == "gold"


class TestDomainInference:
    """Tests for business domain inference."""

    @pytest.mark.asyncio
    async def test_domain_from_meta(self, dbt_parser, parser_config):
        """Test domain is extracted from meta config."""
        result = await dbt_parser.parse(parser_config)

        dim_customers = next(
            c for c in result.capsules if c.name == "dim_customers"
        )
        assert dim_customers.domain_name == "core"

    @pytest.mark.asyncio
    async def test_domains_extracted(self, dbt_parser, parser_config):
        """Test unique domains are extracted."""
        result = await dbt_parser.parse(parser_config)

        domain_names = {d.name for d in result.domains}
        assert "core" in domain_names


class TestPIIDetection:
    """Tests for PII detection in columns."""

    @pytest.mark.asyncio
    async def test_pii_from_meta_tag(self, dbt_parser, parser_config):
        """Test PII detection from meta tag."""
        result = await dbt_parser.parse(parser_config)

        # Find first_name column in stg_customers
        first_name_col = next(
            c for c in result.columns
            if "stg_customers" in c.capsule_urn and c.name == "first_name"
        )

        assert first_name_col.pii_type == "name"
        assert first_name_col.pii_detected_by == "tag"

    @pytest.mark.asyncio
    async def test_pii_from_string_meta(self, dbt_parser, parser_config):
        """Test PII detection from string meta value."""
        result = await dbt_parser.parse(parser_config)

        # Find email column in stg_customers
        email_col = next(
            c for c in result.columns
            if "stg_customers" in c.capsule_urn and c.name == "email"
        )

        assert email_col.pii_type == "email"
        assert email_col.pii_detected_by == "tag"

    @pytest.mark.asyncio
    async def test_pii_sensitive_meta(self, dbt_parser, parser_config):
        """Test PII detection from sensitive meta flag."""
        result = await dbt_parser.parse(parser_config)

        # Find email column in dim_customers (has sensitive: true)
        email_col = next(
            c for c in result.columns
            if "dim_customers" in c.capsule_urn and c.name == "email"
        )

        assert email_col.pii_type == "sensitive"
        assert email_col.pii_detected_by == "tag"

    @pytest.mark.asyncio
    async def test_pii_pattern_detection(self, dbt_parser):
        """Test PII detection from column name patterns."""
        # Parse with pattern detection
        config = {
            "manifest_path": str(MANIFEST_PATH),
            "pii_detection_enabled": True,
        }
        result = await dbt_parser.parse(config)

        # Find email column in source (no explicit PII tag, detected by pattern)
        email_cols = [
            c for c in result.columns
            if c.name == "email" and c.pii_detected_by == "pattern"
        ]

        # At least one email column should be detected by pattern
        # (the source email column doesn't have explicit tag)
        assert any(c.pii_type == "email" for c in email_cols)

    @pytest.mark.asyncio
    async def test_pii_detection_disabled(self, dbt_parser):
        """Test PII detection can be disabled."""
        config = {
            "manifest_path": str(MANIFEST_PATH),
            "pii_detection_enabled": False,
        }
        result = await dbt_parser.parse(config)

        # No columns should have pattern-detected PII
        pattern_detected = [
            c for c in result.columns if c.pii_detected_by == "pattern"
        ]
        assert len(pattern_detected) == 0


class TestColumnExtraction:
    """Tests for column extraction and enrichment."""

    @pytest.mark.asyncio
    async def test_columns_extracted(self, dbt_parser, parser_config):
        """Test columns are extracted from models."""
        result = await dbt_parser.parse(parser_config)

        # Should have many columns
        assert len(result.columns) > 0

        # Check stg_customers columns
        stg_customer_cols = [
            c for c in result.columns if "stg_customers" in c.capsule_urn
        ]
        col_names = {c.name for c in stg_customer_cols}
        assert "customer_id" in col_names
        assert "first_name" in col_names
        assert "email" in col_names

    @pytest.mark.asyncio
    async def test_column_types_from_catalog(self, dbt_parser, parser_config):
        """Test column types are enriched from catalog."""
        result = await dbt_parser.parse(parser_config)

        # Find customer_id in stg_customers
        customer_id = next(
            c for c in result.columns
            if "stg_customers" in c.capsule_urn and c.name == "customer_id"
        )

        assert customer_id.data_type == "NUMBER"
        assert customer_id.ordinal_position == 1

    @pytest.mark.asyncio
    async def test_column_stats_from_catalog(self, dbt_parser, parser_config):
        """Test column statistics are extracted from catalog."""
        result = await dbt_parser.parse(parser_config)

        # Find customer_id in stg_customers (has stats)
        customer_id = next(
            c for c in result.columns
            if "stg_customers" in c.capsule_urn and c.name == "customer_id"
        )

        assert "row_count" in customer_id.stats
        assert customer_id.stats["row_count"] == 100

    @pytest.mark.asyncio
    async def test_column_tests_detected(self, dbt_parser, parser_config):
        """Test column tests are detected."""
        result = await dbt_parser.parse(parser_config)

        # Find customer_id in stg_customers (has tests)
        customer_id = next(
            c for c in result.columns
            if "stg_customers" in c.capsule_urn and c.name == "customer_id"
        )

        assert customer_id.has_tests is True
        assert customer_id.test_count == 2  # unique, not_null


class TestSemanticTypeInference:
    """Tests for semantic type inference."""

    @pytest.mark.asyncio
    async def test_surrogate_key_inference(self, dbt_parser, parser_config):
        """Test surrogate key inference."""
        result = await dbt_parser.parse(parser_config)

        # customer_sk should be identified as surrogate key
        customer_sk = next(
            c for c in result.columns
            if "dim_customers" in c.capsule_urn and c.name == "customer_sk"
        )
        assert customer_sk.semantic_type == "surrogate_key"

    @pytest.mark.asyncio
    async def test_foreign_key_inference(self, dbt_parser, parser_config):
        """Test foreign key inference."""
        result = await dbt_parser.parse(parser_config)

        # customer_fk should be identified as foreign key
        customer_fk = next(
            c for c in result.columns
            if "fct_orders" in c.capsule_urn and c.name == "customer_fk"
        )
        assert customer_fk.semantic_type == "foreign_key"

    @pytest.mark.asyncio
    async def test_timestamp_inference(self, dbt_parser, parser_config):
        """Test timestamp inference."""
        result = await dbt_parser.parse(parser_config)

        # created_at should be identified as timestamp
        created_at = next(
            c for c in result.columns
            if "stg_customers" in c.capsule_urn and c.name == "created_at"
        )
        assert created_at.semantic_type == "timestamp"

    @pytest.mark.asyncio
    async def test_metric_inference(self, dbt_parser, parser_config):
        """Test metric/measure inference."""
        result = await dbt_parser.parse(parser_config)

        # total_amount should be identified as metric
        total_amount = next(
            c for c in result.columns
            if "stg_orders" in c.capsule_urn and c.name == "total_amount"
        )
        assert total_amount.semantic_type == "metric"


class TestLineageEdges:
    """Tests for lineage edge extraction."""

    @pytest.mark.asyncio
    async def test_lineage_edges_created(self, dbt_parser, parser_config):
        """Test lineage edges are created from depends_on."""
        result = await dbt_parser.parse(parser_config)

        # Should have lineage edges
        assert len(result.edges) > 0

    @pytest.mark.asyncio
    async def test_source_to_staging_edge(self, dbt_parser, parser_config):
        """Test edge from source to staging model."""
        result = await dbt_parser.parse(parser_config)

        # Find edge from raw.customers source to stg_customers
        source_urn = next(
            c.urn for c in result.capsules
            if c.capsule_type == "source" and c.name == "customers"
        )
        stg_urn = next(
            c.urn for c in result.capsules
            if c.name == "stg_customers"
        )

        edge = next(
            (e for e in result.edges
             if e.source_urn == source_urn and e.target_urn == stg_urn),
            None
        )
        assert edge is not None
        assert edge.edge_type == "flows_to"
        assert edge.transformation == "source"

    @pytest.mark.asyncio
    async def test_model_to_model_edge(self, dbt_parser, parser_config):
        """Test edge between models."""
        result = await dbt_parser.parse(parser_config)

        # Find edge from stg_customers to int_customer_orders
        stg_urn = next(
            c.urn for c in result.capsules
            if c.name == "stg_customers"
        )
        int_urn = next(
            c.urn for c in result.capsules
            if c.name == "int_customer_orders"
        )

        edge = next(
            (e for e in result.edges
             if e.source_urn == stg_urn and e.target_urn == int_urn),
            None
        )
        assert edge is not None
        assert edge.transformation == "ref"


class TestTagExtraction:
    """Tests for tag extraction."""

    @pytest.mark.asyncio
    async def test_tags_extracted(self, dbt_parser, parser_config):
        """Test unique tags are extracted."""
        result = await dbt_parser.parse(parser_config)

        # Should have tags
        assert len(result.tags) > 0

        tag_names = {t.name for t in result.tags}
        assert "staging" in tag_names
        assert "pii" in tag_names

    @pytest.mark.asyncio
    async def test_tag_categorization(self, dbt_parser, parser_config):
        """Test tags are categorized."""
        result = await dbt_parser.parse(parser_config)

        # Find pii:email tag
        pii_tag = next(
            (t for t in result.tags if t.name == "pii:email"),
            None
        )
        if pii_tag:
            assert pii_tag.category == "sensitivity"


class TestURNGeneration:
    """Tests for URN generation."""

    @pytest.mark.asyncio
    async def test_model_urn_format(self, dbt_parser, parser_config):
        """Test model URN format."""
        result = await dbt_parser.parse(parser_config)

        stg_customers = next(
            c for c in result.capsules if c.name == "stg_customers"
        )

        # URN format: urn:dab:dbt:model:{project}.{schema}:{name}
        assert stg_customers.urn.startswith("urn:dab:dbt:model:")
        assert "jaffle_shop" in stg_customers.urn
        assert "stg_customers" in stg_customers.urn

    @pytest.mark.asyncio
    async def test_source_urn_format(self, dbt_parser, parser_config):
        """Test source URN format."""
        result = await dbt_parser.parse(parser_config)

        customers_source = next(
            c for c in result.capsules
            if c.capsule_type == "source" and c.name == "customers"
        )

        assert customers_source.urn.startswith("urn:dab:dbt:source:")
        assert "customers" in customers_source.urn

    @pytest.mark.asyncio
    async def test_column_urn_format(self, dbt_parser, parser_config):
        """Test column URN format."""
        result = await dbt_parser.parse(parser_config)

        customer_id = next(
            c for c in result.columns
            if "stg_customers" in c.capsule_urn and c.name == "customer_id"
        )

        # Column URN: {capsule_urn}.{column_name}
        assert customer_id.urn.endswith(".customer_id")
        assert customer_id.capsule_urn in customer_id.urn


class TestParseResultSummary:
    """Tests for parse result summary."""

    @pytest.mark.asyncio
    async def test_summary_counts(self, dbt_parser, parser_config):
        """Test summary returns correct counts."""
        result = await dbt_parser.parse(parser_config)
        summary = result.summary()

        assert summary["capsules"] == len(result.capsules)
        assert summary["columns"] == len(result.columns)
        assert summary["edges"] == len(result.edges)
        assert summary["domains"] == len(result.domains)
        assert summary["tags"] == len(result.tags)

    @pytest.mark.asyncio
    async def test_no_errors_for_valid_input(self, dbt_parser, parser_config):
        """Test no errors for valid input."""
        result = await dbt_parser.parse(parser_config)

        assert not result.has_errors
        assert result.error_count == 0
