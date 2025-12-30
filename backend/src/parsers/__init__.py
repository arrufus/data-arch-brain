"""Metadata parsers for various data infrastructure sources."""

from src.parsers.base import (
    MetadataParser,
    ParseError,
    ParseErrorSeverity,
    ParseResult,
    ParserRegistry,
    RawCapsule,
    RawColumn,
    RawColumnEdge,
    RawDomain,
    RawEdge,
    RawOrchestrationEdge,
    RawPipeline,
    RawPipelineTask,
    RawTag,
)
from src.parsers.dbt_config import (
    DbtParserConfig,
    LayerPattern,
    PIIPattern,
    DEFAULT_LAYER_PATTERNS,
    DEFAULT_PII_PATTERNS,
    LAYER_TAGS,
)
from src.parsers.dbt_parser import DbtParser
from src.parsers.airflow_config import AirflowParserConfig
from src.parsers.airflow_parser import AirflowParser
from src.parsers.snowflake_config import SnowflakeParserConfig
from src.parsers.snowflake_parser import SnowflakeParser

# Create and populate the default parser registry
default_registry = ParserRegistry()
default_registry.register("dbt", DbtParser)
default_registry.register("airflow", AirflowParser)
default_registry.register("snowflake", SnowflakeParser)


def get_parser(source_type: str) -> MetadataParser:
    """Get a parser instance for the given source type."""
    return default_registry.get(source_type)


def available_parsers() -> list[str]:
    """List available parser source types."""
    return default_registry.available_sources()


__all__ = [
    # Base classes
    "MetadataParser",
    "ParseError",
    "ParseErrorSeverity",
    "ParseResult",
    "ParserRegistry",
    # Raw data classes
    "RawCapsule",
    "RawColumn",
    "RawDomain",
    "RawEdge",
    "RawOrchestrationEdge",
    "RawPipeline",
    "RawPipelineTask",
    "RawTag",
    # dbt parser
    "DbtParser",
    "DbtParserConfig",
    "LayerPattern",
    "PIIPattern",
    "DEFAULT_LAYER_PATTERNS",
    "DEFAULT_PII_PATTERNS",
    "LAYER_TAGS",
    # Airflow parser
    "AirflowParser",
    "AirflowParserConfig",
    # Snowflake parser
    "SnowflakeParser",
    "SnowflakeParserConfig",
    # Registry functions
    "default_registry",
    "get_parser",
    "available_parsers",
]
