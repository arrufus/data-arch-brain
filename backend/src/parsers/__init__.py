"""Metadata parsers for various data infrastructure sources."""

from src.parsers.base import (
    MetadataParser,
    ParseError,
    ParseErrorSeverity,
    ParseResult,
    ParserRegistry,
    RawCapsule,
    RawColumn,
    RawDomain,
    RawEdge,
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

# Create and populate the default parser registry
default_registry = ParserRegistry()
default_registry.register("dbt", DbtParser)


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
    "RawTag",
    # dbt parser
    "DbtParser",
    "DbtParserConfig",
    "LayerPattern",
    "PIIPattern",
    "DEFAULT_LAYER_PATTERNS",
    "DEFAULT_PII_PATTERNS",
    "LAYER_TAGS",
    # Registry functions
    "default_registry",
    "get_parser",
    "available_parsers",
]
