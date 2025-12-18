# Data Capsule Server - Component Design

**Version**: 1.0
**Status**: Draft
**Last Updated**: December 2024

---

## Table of Contents

1. [Overview](#1-overview)
2. [Ingestion Components](#2-ingestion-components)
3. [dbt Parser Design](#3-dbt-parser-design)
4. [Graph Service](#4-graph-service)
5. [PII Service](#5-pii-service)
6. [Conformance Rule Engine](#6-conformance-rule-engine)
7. [Report Service](#7-report-service)
8. [CLI Design](#8-cli-design)

---

## 1. Overview

### 1.1 Component Summary

| Component | Responsibility | Key Dependencies |
|-----------|----------------|------------------|
| **IngestionService** | Orchestrate metadata ingestion pipeline | ParserRegistry, GraphService |
| **DbtParser** | Parse dbt manifest/catalog to normalized models | orjson, pyyaml |
| **GraphService** | Graph operations, lineage traversal | CapsuleRepository, EdgeRepository |
| **PIIService** | PII detection and lineage tracing | GraphService, ColumnRepository |
| **ConformanceService** | Rule execution and violation detection | RuleRepository, GraphService |
| **ReportService** | Generate formatted reports | All services, Jinja2 |
| **CLI** | Command-line interface | All services, Typer |

### 1.2 Dependency Graph

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           CLI (Typer)                                    │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
        ▼                       ▼                       ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│  Ingestion    │    │   PII         │    │ Conformance   │
│  Service      │    │   Service     │    │   Service     │
└───────┬───────┘    └───────┬───────┘    └───────┬───────┘
        │                    │                    │
        │            ┌───────┴───────┐            │
        │            │               │            │
        ▼            ▼               ▼            ▼
┌───────────────┐  ┌─────────────────────────────────────┐
│    Parser     │  │           GraphService               │
│   Registry    │  │  (lineage traversal, queries)       │
└───────┬───────┘  └───────────────┬─────────────────────┘
        │                          │
        ▼                          ▼
┌───────────────┐  ┌─────────────────────────────────────┐
│  DbtParser    │  │         Repository Layer            │
│  (MVP)        │  │  Capsule, Column, Edge, Rule, etc.  │
└───────────────┘  └───────────────┬─────────────────────┘
                                   │
                                   ▼
                   ┌─────────────────────────────────────┐
                   │           PostgreSQL                 │
                   └─────────────────────────────────────┘
```

---

## 2. Ingestion Components

### 2.1 IngestionService

Orchestrates the end-to-end ingestion pipeline.

```python
# src/services/ingestion_service.py

from dataclasses import dataclass
from typing import Optional
from uuid import UUID
import asyncio

from src.parsers.base import MetadataParser, ParseResult
from src.parsers.registry import ParserRegistry
from src.services.graph_service import GraphService
from src.repositories.ingestion_repository import IngestionRepository
from src.models.ingestion import IngestionJob, IngestionStatus


@dataclass
class IngestionConfig:
    source_type: str
    source_name: str
    config: dict
    run_conformance: bool = True


@dataclass
class IngestionResult:
    job_id: UUID
    status: IngestionStatus
    stats: dict
    errors: list[str]


class IngestionService:
    """Orchestrates metadata ingestion from various sources."""

    def __init__(
        self,
        parser_registry: ParserRegistry,
        graph_service: GraphService,
        ingestion_repo: IngestionRepository,
        conformance_service: Optional["ConformanceService"] = None,
    ):
        self.parser_registry = parser_registry
        self.graph_service = graph_service
        self.ingestion_repo = ingestion_repo
        self.conformance_service = conformance_service

    async def ingest(self, config: IngestionConfig) -> IngestionResult:
        """
        Run full ingestion pipeline:
        1. Create job record
        2. Parse source metadata
        3. Transform to graph nodes/edges
        4. Load into database
        5. Optionally run conformance check
        """
        # Create job record
        job = await self.ingestion_repo.create_job(
            source_type=config.source_type,
            source_name=config.source_name,
            config=config.config,
        )

        try:
            # Get appropriate parser
            parser = self.parser_registry.get(config.source_type)

            # Parse metadata
            await self._update_job_progress(job.id, "parsing", 0)
            parse_result = await parser.parse(config.config)

            if parse_result.errors:
                # Log warnings but continue
                for error in parse_result.errors:
                    await self._log_warning(job.id, error)

            # Load into graph
            await self._update_job_progress(job.id, "loading", 50)
            load_stats = await self.graph_service.load(
                capsules=parse_result.capsules,
                columns=parse_result.columns,
                edges=parse_result.edges,
                domains=parse_result.domains,
                tags=parse_result.tags,
                ingestion_id=job.id,
            )

            # Run conformance check if requested
            conformance_result = None
            if config.run_conformance and self.conformance_service:
                await self._update_job_progress(job.id, "conformance", 90)
                conformance_result = await self.conformance_service.evaluate_all(
                    ingestion_id=job.id
                )

            # Mark completed
            await self.ingestion_repo.complete_job(
                job_id=job.id,
                stats={
                    **load_stats,
                    "parse_errors": len(parse_result.errors),
                    "conformance": conformance_result,
                },
            )

            return IngestionResult(
                job_id=job.id,
                status=IngestionStatus.COMPLETED,
                stats=load_stats,
                errors=parse_result.errors,
            )

        except Exception as e:
            await self.ingestion_repo.fail_job(job.id, str(e))
            raise

    async def _update_job_progress(
        self, job_id: UUID, phase: str, percentage: int
    ) -> None:
        """Update job progress for status tracking."""
        await self.ingestion_repo.update_progress(job_id, phase, percentage)

    async def _log_warning(self, job_id: UUID, message: str) -> None:
        """Log a warning during ingestion."""
        await self.ingestion_repo.add_warning(job_id, message)
```

### 2.2 Parser Registry

Manages and dispatches to appropriate parsers.

```python
# src/parsers/registry.py

from typing import Dict, Type
from src.parsers.base import MetadataParser


class ParserRegistry:
    """Registry of metadata parsers by source type."""

    def __init__(self):
        self._parsers: Dict[str, Type[MetadataParser]] = {}

    def register(self, source_type: str, parser_class: Type[MetadataParser]) -> None:
        """Register a parser for a source type."""
        self._parsers[source_type] = parser_class

    def get(self, source_type: str) -> MetadataParser:
        """Get parser instance for source type."""
        if source_type not in self._parsers:
            raise ValueError(f"No parser registered for source type: {source_type}")
        return self._parsers[source_type]()

    def available_sources(self) -> list[str]:
        """List available source types."""
        return list(self._parsers.keys())


# Default registry setup
def create_default_registry() -> ParserRegistry:
    from src.parsers.dbt_parser import DbtParser

    registry = ParserRegistry()
    registry.register("dbt", DbtParser)
    # Future: registry.register("snowflake", SnowflakeParser)
    return registry
```

### 2.3 Parser Base Class

```python
# src/parsers/base.py

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Any

from src.models.capsule import DataCapsule
from src.models.column import Column
from src.models.edge import Edge
from src.models.domain import Domain
from src.models.tag import Tag


@dataclass
class ParseError:
    message: str
    location: str | None = None
    severity: str = "warning"  # warning, error


@dataclass
class ParseResult:
    capsules: List[DataCapsule] = field(default_factory=list)
    columns: List[Column] = field(default_factory=list)
    edges: List[Edge] = field(default_factory=list)
    domains: List[Domain] = field(default_factory=list)
    tags: List[Tag] = field(default_factory=list)
    errors: List[ParseError] = field(default_factory=list)


class MetadataParser(ABC):
    """Abstract base class for all metadata parsers."""

    @property
    @abstractmethod
    def source_type(self) -> str:
        """Return the source type identifier (e.g., 'dbt', 'snowflake')."""
        pass

    @abstractmethod
    async def parse(self, config: dict) -> ParseResult:
        """Parse metadata from the source and return normalized results."""
        pass

    @abstractmethod
    async def validate_config(self, config: dict) -> List[str]:
        """Validate parser configuration, return list of errors."""
        pass
```

---

## 3. dbt Parser Design

### 3.1 Overview

The dbt parser extracts metadata from dbt artifacts and transforms them into the Data Capsule model.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          dbt Parser Pipeline                             │
└─────────────────────────────────────────────────────────────────────────┘

  Input Files:
  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
  │ manifest.json   │  │  catalog.json   │  │   schema.yml    │
  │ (required)      │  │  (optional)     │  │   (optional)    │
  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘
           │                    │                    │
           ▼                    ▼                    ▼
  ┌─────────────────────────────────────────────────────────────────────┐
  │                        DbtParser                                     │
  │  ┌─────────────────────────────────────────────────────────────┐   │
  │  │ 1. Load & Validate Files                                     │   │
  │  │    • Parse JSON with orjson                                  │   │
  │  │    • Validate manifest version                               │   │
  │  │    • Extract project metadata                                │   │
  │  └─────────────────────────────────────────────────────────────┘   │
  │                              │                                       │
  │                              ▼                                       │
  │  ┌─────────────────────────────────────────────────────────────┐   │
  │  │ 2. Extract Nodes                                             │   │
  │  │    • Models → DataCapsule (type=model)                      │   │
  │  │    • Sources → DataCapsule (type=source)                    │   │
  │  │    • Seeds → DataCapsule (type=seed)                        │   │
  │  │    • Snapshots → DataCapsule (type=snapshot)                │   │
  │  └─────────────────────────────────────────────────────────────┘   │
  │                              │                                       │
  │                              ▼                                       │
  │  ┌─────────────────────────────────────────────────────────────┐   │
  │  │ 3. Extract Columns (from catalog)                            │   │
  │  │    • Column definitions with types                          │   │
  │  │    • Statistics (distinct_count, null_count)                │   │
  │  │    • Link to parent capsule                                 │   │
  │  └─────────────────────────────────────────────────────────────┘   │
  │                              │                                       │
  │                              ▼                                       │
  │  ┌─────────────────────────────────────────────────────────────┐   │
  │  │ 4. Infer Metadata                                            │   │
  │  │    • Layer from path/tags (bronze/silver/gold)              │   │
  │  │    • Domain from path/meta                                   │   │
  │  │    • PII from meta tags + column name patterns              │   │
  │  └─────────────────────────────────────────────────────────────┘   │
  │                              │                                       │
  │                              ▼                                       │
  │  ┌─────────────────────────────────────────────────────────────┐   │
  │  │ 5. Build Lineage                                             │   │
  │  │    • depends_on → FLOWS_TO edges                            │   │
  │  │    • Column-level lineage (if available)                    │   │
  │  └─────────────────────────────────────────────────────────────┘   │
  └─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
  Output:
  ┌─────────────────────────────────────────────────────────────────────┐
  │  ParseResult                                                         │
  │  • capsules: List[DataCapsule]                                      │
  │  • columns: List[Column]                                             │
  │  • edges: List[Edge]                                                 │
  │  • domains: List[Domain]                                             │
  │  • tags: List[Tag]                                                   │
  │  • errors: List[ParseError]                                          │
  └─────────────────────────────────────────────────────────────────────┘
```

### 3.2 DbtParser Implementation

```python
# src/parsers/dbt_parser.py

import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import orjson

from src.parsers.base import MetadataParser, ParseResult, ParseError
from src.models.capsule import DataCapsule, CapsuleType
from src.models.column import Column, SemanticType, PIIType
from src.models.edge import Edge, EdgeType
from src.models.domain import Domain
from src.models.tag import Tag


@dataclass
class DbtParserConfig:
    manifest_path: Path
    catalog_path: Optional[Path] = None
    project_name: Optional[str] = None

    # Layer inference patterns
    layer_patterns: Dict[str, List[str]] = field(default_factory=lambda: {
        "bronze": [r"^raw_", r"^source_", r"/raw/", r"/sources/"],
        "silver": [r"^stg_", r"^staging_", r"^int_", r"^intermediate_", r"/staging/", r"/intermediate/"],
        "gold": [r"^dim_", r"^fct_", r"^fact_", r"^mart_", r"^rpt_", r"^report_", r"/marts/", r"/reports/"],
    })

    # PII detection patterns
    pii_patterns: Dict[str, List[str]] = field(default_factory=lambda: {
        "email": [r"(?i)e?mail", r"(?i)email_address"],
        "phone": [r"(?i)phone", r"(?i)mobile", r"(?i)cell", r"(?i)tel(?:ephone)?"],
        "ssn": [r"(?i)ssn", r"(?i)social_security"],
        "address": [r"(?i)address", r"(?i)street", r"(?i)city", r"(?i)zip", r"(?i)postal"],
        "name": [r"(?i)first_name", r"(?i)last_name", r"(?i)full_name", r"(?i)customer_name"],
        "date_of_birth": [r"(?i)dob", r"(?i)birth_?date", r"(?i)date_of_birth"],
        "credit_card": [r"(?i)credit_card", r"(?i)card_number", r"(?i)cc_num"],
        "ip_address": [r"(?i)ip_addr", r"(?i)ip_address", r"(?i)client_ip"],
    })


class DbtParser(MetadataParser):
    """Parser for dbt manifest.json and catalog.json."""

    @property
    def source_type(self) -> str:
        return "dbt"

    async def validate_config(self, config: dict) -> List[str]:
        """Validate dbt parser configuration."""
        errors = []

        manifest_path = Path(config.get("manifest_path", ""))
        if not manifest_path.exists():
            errors.append(f"Manifest file not found: {manifest_path}")
        elif not manifest_path.suffix == ".json":
            errors.append("Manifest file must be a JSON file")

        catalog_path = config.get("catalog_path")
        if catalog_path:
            catalog_path = Path(catalog_path)
            if not catalog_path.exists():
                errors.append(f"Catalog file not found: {catalog_path}")

        return errors

    async def parse(self, config: dict) -> ParseResult:
        """Parse dbt artifacts into normalized models."""
        parser_config = DbtParserConfig(**config)
        result = ParseResult()

        # Load manifest
        manifest = await self._load_json(parser_config.manifest_path)
        if not manifest:
            result.errors.append(ParseError(
                message="Failed to load manifest.json",
                severity="error"
            ))
            return result

        # Load catalog (optional)
        catalog = None
        if parser_config.catalog_path and parser_config.catalog_path.exists():
            catalog = await self._load_json(parser_config.catalog_path)

        # Extract project info
        project_name = parser_config.project_name or manifest.get("metadata", {}).get("project_name", "default")

        # Process nodes
        await self._process_models(manifest, catalog, project_name, parser_config, result)
        await self._process_sources(manifest, catalog, project_name, parser_config, result)
        await self._process_seeds(manifest, catalog, project_name, parser_config, result)

        # Build lineage edges
        await self._build_lineage(manifest, project_name, result)

        # Extract domains from paths/tags
        await self._extract_domains(result)

        return result

    async def _load_json(self, path: Path) -> Optional[dict]:
        """Load JSON file using orjson for performance."""
        try:
            with open(path, "rb") as f:
                return orjson.loads(f.read())
        except Exception as e:
            return None

    async def _process_models(
        self,
        manifest: dict,
        catalog: Optional[dict],
        project_name: str,
        config: DbtParserConfig,
        result: ParseResult
    ) -> None:
        """Extract models from manifest."""
        nodes = manifest.get("nodes", {})

        for node_id, node in nodes.items():
            if node.get("resource_type") != "model":
                continue

            # Build URN
            urn = self._build_urn(
                source="dbt",
                node_type="model",
                namespace=f"{project_name}.{node.get('schema', 'default')}",
                name=node["name"]
            )

            # Infer layer
            layer = self._infer_layer(node, config.layer_patterns)

            # Infer domain from path
            domain_name = self._infer_domain(node)

            # Create capsule
            capsule = DataCapsule(
                urn=urn,
                name=node["name"],
                capsule_type=CapsuleType.MODEL,
                layer=layer,
                schema_name=node.get("schema"),
                database_name=node.get("database"),
                description=node.get("description"),
                materialization=node.get("config", {}).get("materialized"),
                domain_name=domain_name,
                meta={
                    "unique_id": node_id,
                    "package_name": node.get("package_name"),
                    "original_file_path": node.get("original_file_path"),
                    "config": node.get("config", {}),
                },
                tags=node.get("tags", []),
                has_tests=len(node.get("test_metadata", [])) > 0 or self._has_tests(node_id, manifest),
            )

            result.capsules.append(capsule)

            # Extract columns
            await self._extract_columns(
                capsule_urn=urn,
                node=node,
                catalog=catalog,
                node_id=node_id,
                config=config,
                result=result
            )

    async def _process_sources(
        self,
        manifest: dict,
        catalog: Optional[dict],
        project_name: str,
        config: DbtParserConfig,
        result: ParseResult
    ) -> None:
        """Extract sources from manifest."""
        sources = manifest.get("sources", {})

        for source_id, source in sources.items():
            urn = self._build_urn(
                source="dbt",
                node_type="source",
                namespace=f"{project_name}.{source.get('source_name', 'default')}",
                name=source["name"]
            )

            capsule = DataCapsule(
                urn=urn,
                name=source["name"],
                capsule_type=CapsuleType.SOURCE,
                layer="bronze",  # Sources are always bronze/raw
                schema_name=source.get("schema"),
                database_name=source.get("database"),
                description=source.get("description"),
                meta={
                    "unique_id": source_id,
                    "source_name": source.get("source_name"),
                    "loader": source.get("loader"),
                    "freshness": source.get("freshness"),
                },
                tags=source.get("tags", []),
            )

            result.capsules.append(capsule)

            # Extract columns if in catalog
            await self._extract_columns(
                capsule_urn=urn,
                node=source,
                catalog=catalog,
                node_id=source_id,
                config=config,
                result=result
            )

    async def _process_seeds(
        self,
        manifest: dict,
        catalog: Optional[dict],
        project_name: str,
        config: DbtParserConfig,
        result: ParseResult
    ) -> None:
        """Extract seeds from manifest."""
        nodes = manifest.get("nodes", {})

        for node_id, node in nodes.items():
            if node.get("resource_type") != "seed":
                continue

            urn = self._build_urn(
                source="dbt",
                node_type="seed",
                namespace=f"{project_name}.{node.get('schema', 'default')}",
                name=node["name"]
            )

            capsule = DataCapsule(
                urn=urn,
                name=node["name"],
                capsule_type=CapsuleType.SEED,
                layer="bronze",
                schema_name=node.get("schema"),
                database_name=node.get("database"),
                description=node.get("description"),
                meta={"unique_id": node_id},
                tags=node.get("tags", []),
            )

            result.capsules.append(capsule)

    async def _extract_columns(
        self,
        capsule_urn: str,
        node: dict,
        catalog: Optional[dict],
        node_id: str,
        config: DbtParserConfig,
        result: ParseResult
    ) -> None:
        """Extract column definitions from catalog and schema."""
        columns_data = {}

        # Get columns from manifest (descriptions, meta)
        manifest_columns = node.get("columns", {})
        for col_name, col_info in manifest_columns.items():
            columns_data[col_name] = {
                "name": col_name,
                "description": col_info.get("description"),
                "meta": col_info.get("meta", {}),
                "tags": col_info.get("tags", []),
            }

        # Enrich with catalog data (types, stats)
        if catalog:
            catalog_node = catalog.get("nodes", {}).get(node_id) or catalog.get("sources", {}).get(node_id)
            if catalog_node:
                for col_name, col_info in catalog_node.get("columns", {}).items():
                    if col_name not in columns_data:
                        columns_data[col_name] = {"name": col_name}

                    columns_data[col_name].update({
                        "data_type": col_info.get("type"),
                        "index": col_info.get("index"),
                        "stats": {
                            k: v.get("value")
                            for k, v in col_info.get("stats", {}).items()
                        },
                    })

        # Create Column objects
        for ordinal, (col_name, col_data) in enumerate(columns_data.items(), start=1):
            column_urn = f"{capsule_urn}.{col_name}"

            # Detect PII
            pii_type, detected_by = self._detect_pii(col_name, col_data, config.pii_patterns)

            # Determine semantic type
            semantic_type = self._infer_semantic_type(col_name, col_data, pii_type)

            column = Column(
                urn=column_urn,
                capsule_urn=capsule_urn,
                name=col_name,
                data_type=col_data.get("data_type"),
                ordinal_position=col_data.get("index", ordinal),
                is_nullable=True,  # dbt doesn't provide this directly
                semantic_type=semantic_type,
                pii_type=pii_type,
                pii_detected_by=detected_by,
                description=col_data.get("description"),
                meta=col_data.get("meta", {}),
                tags=col_data.get("tags", []),
                stats=col_data.get("stats", {}),
            )

            result.columns.append(column)

    async def _build_lineage(
        self,
        manifest: dict,
        project_name: str,
        result: ParseResult
    ) -> None:
        """Build lineage edges from depends_on relationships."""
        # Create URN lookup
        urn_lookup = {c.meta.get("unique_id"): c.urn for c in result.capsules}

        nodes = manifest.get("nodes", {})
        for node_id, node in nodes.items():
            if node_id not in urn_lookup:
                continue

            target_urn = urn_lookup[node_id]
            depends_on = node.get("depends_on", {}).get("nodes", [])

            for dep_id in depends_on:
                source_urn = urn_lookup.get(dep_id)
                if source_urn:
                    edge = Edge(
                        source_urn=source_urn,
                        target_urn=target_urn,
                        edge_type=EdgeType.FLOWS_TO,
                        transformation="ref" if dep_id.startswith("model.") else "source",
                    )
                    result.edges.append(edge)

    async def _extract_domains(self, result: ParseResult) -> None:
        """Extract unique domains from capsules."""
        domain_names = set()
        for capsule in result.capsules:
            if capsule.domain_name:
                domain_names.add(capsule.domain_name)

        for name in domain_names:
            result.domains.append(Domain(name=name))

    def _build_urn(self, source: str, node_type: str, namespace: str, name: str) -> str:
        """Build URN string."""
        return f"urn:dcs:{source}:{node_type}:{namespace}:{name}"

    def _infer_layer(self, node: dict, patterns: Dict[str, List[str]]) -> Optional[str]:
        """Infer architecture layer from node name and path."""
        name = node.get("name", "")
        path = node.get("original_file_path", "")

        # Check tags first (explicit layer tags)
        tags = node.get("tags", [])
        for tag in tags:
            tag_lower = tag.lower()
            if tag_lower in ["bronze", "raw"]:
                return "bronze"
            if tag_lower in ["silver", "staging", "intermediate"]:
                return "silver"
            if tag_lower in ["gold", "marts", "mart"]:
                return "gold"

        # Check patterns
        for layer, layer_patterns in patterns.items():
            for pattern in layer_patterns:
                if re.search(pattern, name) or re.search(pattern, path):
                    return layer

        return None

    def _infer_domain(self, node: dict) -> Optional[str]:
        """Infer domain from path structure or meta."""
        # Check meta first
        meta = node.get("config", {}).get("meta", {}) or node.get("meta", {})
        if "domain" in meta:
            return meta["domain"]

        # Infer from path (e.g., models/marts/customer/dim_customer.sql -> customer)
        path = node.get("original_file_path", "")
        parts = Path(path).parts

        # Look for domain-like folder names
        exclude = {"models", "staging", "intermediate", "marts", "raw", "sources", "reports"}
        for part in reversed(parts[:-1]):  # Exclude filename
            if part.lower() not in exclude and not part.startswith("_"):
                return part.lower()

        return None

    def _detect_pii(
        self,
        col_name: str,
        col_data: dict,
        patterns: Dict[str, List[str]]
    ) -> tuple[Optional[str], Optional[str]]:
        """Detect PII type from meta tags or column name patterns."""
        # Check meta tags first (explicit tagging)
        meta = col_data.get("meta", {})
        if meta.get("pii"):
            pii_type = meta.get("pii_type") or meta.get("pii")
            if isinstance(pii_type, bool):
                pii_type = "unknown"
            return pii_type, "tag"

        # Check column tags
        tags = col_data.get("tags", [])
        for tag in tags:
            if tag.lower() == "pii" or tag.lower().startswith("pii:"):
                pii_type = tag.split(":")[-1] if ":" in tag else "unknown"
                return pii_type, "tag"

        # Pattern-based detection
        for pii_type, type_patterns in patterns.items():
            for pattern in type_patterns:
                if re.search(pattern, col_name):
                    return pii_type, "pattern"

        return None, None

    def _infer_semantic_type(
        self,
        col_name: str,
        col_data: dict,
        pii_type: Optional[str]
    ) -> Optional[str]:
        """Infer semantic type from column characteristics."""
        if pii_type:
            return SemanticType.PII

        name_lower = col_name.lower()

        # Check meta
        meta = col_data.get("meta", {})
        if "semantic_type" in meta:
            return meta["semantic_type"]

        # Key detection
        if name_lower.endswith("_id") or name_lower.endswith("_key"):
            if name_lower.endswith("_sk") or "surrogate" in name_lower:
                return SemanticType.SURROGATE_KEY
            if "natural" in name_lower or "business" in name_lower:
                return SemanticType.BUSINESS_KEY
            return SemanticType.FOREIGN_KEY

        # Timestamp detection
        timestamp_patterns = ["_at", "_date", "_time", "timestamp", "created", "updated", "modified"]
        if any(p in name_lower for p in timestamp_patterns):
            return SemanticType.TIMESTAMP

        return None

    def _has_tests(self, node_id: str, manifest: dict) -> bool:
        """Check if node has associated tests."""
        nodes = manifest.get("nodes", {})
        for test_id, test in nodes.items():
            if test.get("resource_type") == "test":
                depends_on = test.get("depends_on", {}).get("nodes", [])
                if node_id in depends_on:
                    return True
        return False
```

### 3.3 Data Models

```python
# src/models/capsule.py

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, List, Any
from datetime import datetime
from uuid import UUID


class CapsuleType(str, Enum):
    MODEL = "model"
    SOURCE = "source"
    SEED = "seed"
    SNAPSHOT = "snapshot"
    ANALYSIS = "analysis"
    TEST = "test"


@dataclass
class DataCapsule:
    urn: str
    name: str
    capsule_type: CapsuleType

    # Optional fields
    id: Optional[UUID] = None
    layer: Optional[str] = None
    schema_name: Optional[str] = None
    database_name: Optional[str] = None
    description: Optional[str] = None
    materialization: Optional[str] = None
    domain_name: Optional[str] = None
    owner_name: Optional[str] = None
    source_system_name: Optional[str] = None

    # Metadata
    meta: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)

    # Quality indicators
    has_tests: bool = False
    test_count: int = 0
    doc_coverage: float = 0.0

    # Audit
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
```

```python
# src/models/column.py

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, List, Any
from uuid import UUID


class SemanticType(str, Enum):
    PII = "pii"
    BUSINESS_KEY = "business_key"
    NATURAL_KEY = "natural_key"
    SURROGATE_KEY = "surrogate_key"
    FOREIGN_KEY = "foreign_key"
    METRIC = "metric"
    MEASURE = "measure"
    DIMENSION = "dimension"
    TIMESTAMP = "timestamp"
    EVENT_TIME = "event_time"
    PROCESSING_TIME = "processing_time"


class PIIType(str, Enum):
    DIRECT_IDENTIFIER = "direct_identifier"
    EMAIL = "email"
    PHONE = "phone"
    ADDRESS = "address"
    SSN = "ssn"
    CREDIT_CARD = "credit_card"
    BANK_ACCOUNT = "bank_account"
    HEALTH = "health"
    BIOMETRIC = "biometric"
    DATE_OF_BIRTH = "date_of_birth"
    NAME = "name"
    IP_ADDRESS = "ip_address"
    DEVICE_ID = "device_id"


@dataclass
class Column:
    urn: str
    capsule_urn: str
    name: str

    # Optional fields
    id: Optional[UUID] = None
    data_type: Optional[str] = None
    ordinal_position: Optional[int] = None
    is_nullable: bool = True

    # Semantic classification
    semantic_type: Optional[str] = None
    pii_type: Optional[str] = None
    pii_detected_by: Optional[str] = None  # 'tag', 'pattern', 'manual'

    # Documentation
    description: Optional[str] = None

    # Metadata
    meta: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)

    # Quality
    has_tests: bool = False
    test_count: int = 0
```

---

## 4. Graph Service

### 4.1 Overview

The GraphService provides graph operations including loading, querying, and lineage traversal.

```python
# src/services/graph_service.py

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from uuid import UUID
from enum import Enum

from src.models.capsule import DataCapsule
from src.models.column import Column
from src.models.edge import Edge
from src.models.domain import Domain
from src.models.tag import Tag
from src.repositories.capsule_repository import CapsuleRepository
from src.repositories.column_repository import ColumnRepository
from src.repositories.edge_repository import EdgeRepository
from src.repositories.domain_repository import DomainRepository


class LineageDirection(str, Enum):
    UPSTREAM = "upstream"
    DOWNSTREAM = "downstream"
    BOTH = "both"


@dataclass
class LineageNode:
    urn: str
    name: str
    layer: Optional[str]
    capsule_type: str
    depth: int
    edge_type: str


@dataclass
class LineageResult:
    root: DataCapsule
    upstream: List[LineageNode]
    downstream: List[LineageNode]
    edges: List[Edge]
    summary: Dict[str, int]


@dataclass
class LoadStats:
    capsules_created: int = 0
    capsules_updated: int = 0
    capsules_unchanged: int = 0
    columns_processed: int = 0
    edges_created: int = 0
    domains_created: int = 0
    tags_created: int = 0


class GraphService:
    """Service for graph operations and lineage traversal."""

    def __init__(
        self,
        capsule_repo: CapsuleRepository,
        column_repo: ColumnRepository,
        edge_repo: EdgeRepository,
        domain_repo: DomainRepository,
    ):
        self.capsule_repo = capsule_repo
        self.column_repo = column_repo
        self.edge_repo = edge_repo
        self.domain_repo = domain_repo

    async def load(
        self,
        capsules: List[DataCapsule],
        columns: List[Column],
        edges: List[Edge],
        domains: List[Domain],
        tags: List[Tag],
        ingestion_id: UUID,
    ) -> LoadStats:
        """Load parsed data into the graph."""
        stats = LoadStats()

        # Upsert domains first (capsules reference them)
        for domain in domains:
            created = await self.domain_repo.upsert(domain)
            if created:
                stats.domains_created += 1

        # Upsert capsules
        for capsule in capsules:
            result = await self.capsule_repo.upsert(capsule, ingestion_id)
            if result == "created":
                stats.capsules_created += 1
            elif result == "updated":
                stats.capsules_updated += 1
            else:
                stats.capsules_unchanged += 1

        # Upsert columns
        for column in columns:
            await self.column_repo.upsert(column, ingestion_id)
            stats.columns_processed += 1

        # Upsert edges
        for edge in edges:
            created = await self.edge_repo.upsert(edge, ingestion_id)
            if created:
                stats.edges_created += 1

        return stats

    async def get_capsule_lineage(
        self,
        urn: str,
        direction: LineageDirection = LineageDirection.BOTH,
        depth: int = 3,
    ) -> LineageResult:
        """Get lineage for a capsule."""
        # Get root capsule
        root = await self.capsule_repo.get_by_urn(urn)
        if not root:
            raise ValueError(f"Capsule not found: {urn}")

        upstream = []
        downstream = []
        all_edges = []

        # Traverse upstream
        if direction in (LineageDirection.UPSTREAM, LineageDirection.BOTH):
            upstream, upstream_edges = await self._traverse(
                start_id=root.id,
                direction="upstream",
                max_depth=depth
            )
            all_edges.extend(upstream_edges)

        # Traverse downstream
        if direction in (LineageDirection.DOWNSTREAM, LineageDirection.BOTH):
            downstream, downstream_edges = await self._traverse(
                start_id=root.id,
                direction="downstream",
                max_depth=depth
            )
            all_edges.extend(downstream_edges)

        return LineageResult(
            root=root,
            upstream=upstream,
            downstream=downstream,
            edges=all_edges,
            summary={
                "total_upstream": len(upstream),
                "total_downstream": len(downstream),
                "max_upstream_depth": max((n.depth for n in upstream), default=0),
                "max_downstream_depth": max((n.depth for n in downstream), default=0),
            }
        )

    async def _traverse(
        self,
        start_id: UUID,
        direction: str,
        max_depth: int
    ) -> tuple[List[LineageNode], List[Edge]]:
        """Traverse graph in given direction using recursive CTE."""
        # This calls the repository which executes the recursive CTE query
        nodes, edges = await self.edge_repo.traverse(
            start_id=start_id,
            direction=direction,
            max_depth=max_depth
        )
        return nodes, edges

    async def get_column_lineage(
        self,
        column_urn: str,
        direction: LineageDirection = LineageDirection.BOTH,
        depth: int = 5,
    ) -> dict:
        """Get lineage for a column."""
        # Similar to capsule lineage but for columns
        column = await self.column_repo.get_by_urn(column_urn)
        if not column:
            raise ValueError(f"Column not found: {column_urn}")

        # Traverse column lineage edges
        # ... implementation similar to capsule lineage
        pass
```

---

## 5. PII Service

### 5.1 Overview

The PIIService handles PII detection, lineage tracing, and exposure analysis.

```python
# src/services/pii_service.py

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from enum import Enum

from src.services.graph_service import GraphService, LineageDirection
from src.repositories.column_repository import ColumnRepository


class PIIRisk(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class PIIInventoryItem:
    pii_type: str
    column_count: int
    capsule_count: int
    layers: List[str]
    columns: List[dict]


@dataclass
class PIIExposure:
    column: dict
    capsule: dict
    severity: str
    reason: str
    recommendation: str
    lineage_path: List[str]


@dataclass
class PIITraceResult:
    column: dict
    origin: dict
    propagation_path: List[dict]
    terminals: List[dict]
    risk_summary: dict


class PIIService:
    """Service for PII detection, tracking, and compliance."""

    def __init__(
        self,
        column_repo: ColumnRepository,
        graph_service: GraphService,
    ):
        self.column_repo = column_repo
        self.graph_service = graph_service

        # Configure which layers are "exposure" layers
        self.exposure_layers = {"gold", "marts", "reports"}
        self.safe_transformations = {"hashed", "masked", "encrypted", "redacted"}

    async def get_inventory(
        self,
        pii_type: Optional[str] = None,
        layer: Optional[str] = None,
        domain: Optional[str] = None,
        group_by: str = "pii_type",
    ) -> dict:
        """Get PII inventory with grouping options."""
        # Query all PII columns with filters
        columns = await self.column_repo.find_pii_columns(
            pii_type=pii_type,
            layer=layer,
            domain=domain,
        )

        # Group by requested dimension
        if group_by == "pii_type":
            grouped = self._group_by_pii_type(columns)
        elif group_by == "layer":
            grouped = self._group_by_layer(columns)
        elif group_by == "domain":
            grouped = self._group_by_domain(columns)
        else:
            grouped = columns

        # Calculate summary
        summary = {
            "total_pii_columns": len(columns),
            "capsules_with_pii": len(set(c.capsule_urn for c in columns)),
            "pii_types_found": list(set(c.pii_type for c in columns if c.pii_type)),
        }

        return {
            "summary": summary,
            f"by_{group_by}": grouped,
        }

    async def detect_exposure(
        self,
        layer: Optional[str] = None,
    ) -> dict:
        """Detect PII exposure (unmasked PII in consumption layers)."""
        target_layers = {layer} if layer else self.exposure_layers

        exposures = []

        # Get PII columns in target layers
        pii_columns = await self.column_repo.find_pii_columns(layers=target_layers)

        for column in pii_columns:
            # Check if column has masking transformation in lineage
            is_masked = await self._check_masking(column)

            if not is_masked:
                severity = self._calculate_exposure_severity(column)
                exposure = PIIExposure(
                    column={
                        "urn": column.urn,
                        "name": column.name,
                        "pii_type": column.pii_type,
                    },
                    capsule={
                        "urn": column.capsule_urn,
                        "name": column.capsule_name,
                        "layer": column.layer,
                    },
                    severity=severity,
                    reason=f"PII column in {column.layer} layer without masking transformation",
                    recommendation=self._get_recommendation(column),
                    lineage_path=await self._get_lineage_path(column),
                )
                exposures.append(exposure)

        # Calculate summary
        summary = {
            "exposed_pii_columns": len(exposures),
            "affected_capsules": len(set(e.capsule["urn"] for e in exposures)),
            "severity_breakdown": self._count_by_severity(exposures),
        }

        return {
            "summary": summary,
            "exposures": exposures,
        }

    async def trace_pii(self, column_urn: str) -> PIITraceResult:
        """Trace a PII column through the entire pipeline."""
        # Get column
        column = await self.column_repo.get_by_urn(column_urn)
        if not column:
            raise ValueError(f"Column not found: {column_urn}")

        # Get full lineage (both directions)
        lineage = await self.graph_service.get_column_lineage(
            column_urn=column_urn,
            direction=LineageDirection.BOTH,
            depth=10,
        )

        # Find origin (furthest upstream)
        origin = self._find_origin(lineage)

        # Build propagation path
        path = self._build_propagation_path(lineage)

        # Find terminals (furthest downstream, leaf nodes)
        terminals = self._find_terminals(lineage)

        # Calculate risk
        risk_summary = self._calculate_risk(terminals)

        return PIITraceResult(
            column={
                "urn": column.urn,
                "name": column.name,
                "pii_type": column.pii_type,
            },
            origin=origin,
            propagation_path=path,
            terminals=terminals,
            risk_summary=risk_summary,
        )

    async def _check_masking(self, column) -> bool:
        """Check if column has masking transformation in its lineage."""
        # Get upstream lineage for the column
        upstream = await self.column_repo.get_upstream_lineage(column.id)

        for edge in upstream:
            if edge.transformation_type in self.safe_transformations:
                return True

        return False

    def _calculate_exposure_severity(self, column) -> str:
        """Calculate severity of PII exposure."""
        high_risk_types = {"ssn", "credit_card", "bank_account", "health", "biometric"}
        medium_risk_types = {"email", "phone", "address", "date_of_birth"}

        if column.pii_type in high_risk_types:
            return "critical"
        elif column.pii_type in medium_risk_types:
            return "high"
        else:
            return "medium"

    def _get_recommendation(self, column) -> str:
        """Get remediation recommendation for exposure."""
        recommendations = {
            "email": "Apply hashing (e.g., MD5, SHA256) to email before exposing in consumption layer",
            "ssn": "SSN should never be exposed in consumption layers. Remove or use tokenization.",
            "phone": "Apply masking (e.g., show last 4 digits only) before exposing",
            "address": "Consider aggregating to postal code level instead of full address",
            "credit_card": "Credit card numbers should never be exposed. Use tokenization.",
        }
        return recommendations.get(
            column.pii_type,
            f"Apply masking or hashing to {column.pii_type} before exposing in {column.layer} layer"
        )

    def _group_by_pii_type(self, columns) -> List[PIIInventoryItem]:
        """Group columns by PII type."""
        groups = {}
        for col in columns:
            pii_type = col.pii_type or "unknown"
            if pii_type not in groups:
                groups[pii_type] = {
                    "columns": [],
                    "capsules": set(),
                    "layers": set(),
                }
            groups[pii_type]["columns"].append(col)
            groups[pii_type]["capsules"].add(col.capsule_urn)
            if col.layer:
                groups[pii_type]["layers"].add(col.layer)

        return [
            PIIInventoryItem(
                pii_type=pii_type,
                column_count=len(data["columns"]),
                capsule_count=len(data["capsules"]),
                layers=list(data["layers"]),
                columns=[{"urn": c.urn, "name": c.name, "capsule_name": c.capsule_name, "layer": c.layer} for c in data["columns"]],
            )
            for pii_type, data in groups.items()
        ]
```

---

## 6. Conformance Rule Engine

### 6.1 Overview

The ConformanceService provides a flexible rule engine for validating architecture conformance.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     CONFORMANCE RULE ENGINE                              │
└─────────────────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────────────┐
  │                         Rule Definition                              │
  │                                                                       │
  │  rules:                                                              │
  │    - id: NAMING_001                                                  │
  │      name: "Model naming convention"                                 │
  │      severity: warning                                               │
  │      scope: capsule                                                  │
  │      definition:                                                     │
  │        type: pattern                                                 │
  │        pattern: "^(raw|stg|dim|fct)_[a-z_]+$"                       │
  │        apply_to: name                                                │
  │                                                                       │
  │    - id: LINEAGE_001                                                 │
  │      name: "Gold sources Silver"                                     │
  │      severity: error                                                 │
  │      scope: capsule                                                  │
  │      definition:                                                     │
  │        type: graph                                                   │
  │        condition:                                                    │
  │          if: { layer: gold }                                        │
  │          then: { upstream_layers: [silver, intermediate] }          │
  └─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
  ┌─────────────────────────────────────────────────────────────────────┐
  │                         Rule Executors                               │
  │                                                                       │
  │  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐           │
  │  │ PatternRule   │  │  GraphRule    │  │ PropertyRule  │           │
  │  │ Executor      │  │  Executor     │  │ Executor      │           │
  │  │               │  │               │  │               │           │
  │  │ • Regex match │  │ • Lineage     │  │ • Property    │           │
  │  │ • Name/path   │  │   conditions  │  │   existence   │           │
  │  │   validation  │  │ • Graph       │  │ • Value       │           │
  │  │               │  │   queries     │  │   validation  │           │
  │  └───────────────┘  └───────────────┘  └───────────────┘           │
  └─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
  ┌─────────────────────────────────────────────────────────────────────┐
  │                         Evaluation Result                            │
  │                                                                       │
  │  {                                                                   │
  │    "score": 78.5,                                                   │
  │    "violations": [                                                   │
  │      { "rule_id": "NAMING_001", "capsule": "...", "message": "..." }│
  │    ]                                                                 │
  │  }                                                                   │
  └─────────────────────────────────────────────────────────────────────┘
```

### 6.2 Rule Types

| Type | Description | Use Cases |
|------|-------------|-----------|
| **Pattern** | Regex matching on properties | Naming conventions, format validation |
| **Graph** | Lineage/relationship conditions | Layer flow rules, dependency checks |
| **Property** | Property existence/value checks | Documentation, tagging requirements |
| **Aggregate** | Cross-entity aggregations | Coverage thresholds, counts |

### 6.3 ConformanceService Implementation

```python
# src/services/conformance_service.py

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Protocol
from uuid import UUID
from enum import Enum
import re

from src.repositories.rule_repository import RuleRepository
from src.repositories.violation_repository import ViolationRepository
from src.repositories.capsule_repository import CapsuleRepository
from src.services.graph_service import GraphService


class RuleType(str, Enum):
    PATTERN = "pattern"
    GRAPH = "graph"
    PROPERTY = "property"
    AGGREGATE = "aggregate"


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Rule:
    id: UUID
    rule_id: str
    name: str
    description: str
    severity: Severity
    category: str
    rule_set: Optional[str]
    scope: str  # 'capsule', 'column', 'lineage'
    definition: dict
    enabled: bool = True


@dataclass
class Violation:
    rule: Rule
    subject_type: str  # 'capsule' or 'column'
    subject_urn: str
    subject_name: str
    message: str
    details: dict = field(default_factory=dict)


@dataclass
class ConformanceResult:
    score: float
    weighted_score: float
    total_rules: int
    passing_rules: int
    failing_rules: int
    violations: List[Violation]
    by_severity: Dict[str, dict]
    by_category: Dict[str, dict]


class RuleExecutor(Protocol):
    """Protocol for rule executors."""

    async def execute(
        self,
        rule: Rule,
        capsules: List[Any],
        columns: List[Any],
        graph_service: GraphService,
    ) -> List[Violation]:
        ...


class PatternRuleExecutor:
    """Executes pattern-based rules (regex matching)."""

    async def execute(
        self,
        rule: Rule,
        capsules: List[Any],
        columns: List[Any],
        graph_service: GraphService,
    ) -> List[Violation]:
        violations = []
        definition = rule.definition

        pattern = definition.get("pattern")
        apply_to = definition.get("apply_to", "name")
        scope_filter = definition.get("filter", {})

        # Determine scope
        if rule.scope == "capsule":
            subjects = self._filter_capsules(capsules, scope_filter)
        else:
            subjects = self._filter_columns(columns, scope_filter)

        # Apply pattern
        compiled_pattern = re.compile(pattern)

        for subject in subjects:
            value = getattr(subject, apply_to, None)
            if value and not compiled_pattern.match(value):
                violations.append(Violation(
                    rule=rule,
                    subject_type=rule.scope,
                    subject_urn=subject.urn,
                    subject_name=subject.name,
                    message=f"{rule.scope.capitalize()} '{subject.name}' does not match pattern '{pattern}'",
                    details={
                        "expected_pattern": pattern,
                        "actual_value": value,
                        "apply_to": apply_to,
                    }
                ))

        return violations

    def _filter_capsules(self, capsules, filters) -> List:
        """Filter capsules based on rule conditions."""
        result = capsules
        if "layer" in filters:
            layers = filters["layer"] if isinstance(filters["layer"], list) else [filters["layer"]]
            result = [c for c in result if c.layer in layers]
        if "capsule_type" in filters:
            types = filters["capsule_type"] if isinstance(filters["capsule_type"], list) else [filters["capsule_type"]]
            result = [c for c in result if c.capsule_type in types]
        return result

    def _filter_columns(self, columns, filters) -> List:
        """Filter columns based on rule conditions."""
        # Similar filtering logic
        return columns


class GraphRuleExecutor:
    """Executes graph-based rules (lineage conditions)."""

    async def execute(
        self,
        rule: Rule,
        capsules: List[Any],
        columns: List[Any],
        graph_service: GraphService,
    ) -> List[Violation]:
        violations = []
        definition = rule.definition
        condition = definition.get("condition", {})

        if_clause = condition.get("if", {})
        then_clause = condition.get("then", {})

        # Find capsules matching the "if" condition
        matching_capsules = self._filter_by_condition(capsules, if_clause)

        for capsule in matching_capsules:
            # Check "then" condition
            if not await self._check_then_condition(capsule, then_clause, graph_service):
                violations.append(Violation(
                    rule=rule,
                    subject_type="capsule",
                    subject_urn=capsule.urn,
                    subject_name=capsule.name,
                    message=self._build_message(rule, capsule, then_clause),
                    details={
                        "condition": condition,
                        "capsule_layer": capsule.layer,
                    }
                ))

        return violations

    def _filter_by_condition(self, capsules, condition) -> List:
        """Filter capsules matching the if condition."""
        result = capsules
        if "layer" in condition:
            layers = condition["layer"] if isinstance(condition["layer"], list) else [condition["layer"]]
            result = [c for c in result if c.layer in layers]
        return result

    async def _check_then_condition(
        self,
        capsule,
        then_clause: dict,
        graph_service: GraphService
    ) -> bool:
        """Check if capsule satisfies the then condition."""
        if "upstream_layers" in then_clause:
            allowed_layers = set(then_clause["upstream_layers"])

            # Get upstream capsules
            lineage = await graph_service.get_capsule_lineage(
                urn=capsule.urn,
                direction="upstream",
                depth=1,
            )

            # Check all upstream capsules are in allowed layers
            for upstream in lineage.upstream:
                if upstream.layer and upstream.layer not in allowed_layers:
                    return False

            return True

        return True

    def _build_message(self, rule: Rule, capsule, then_clause) -> str:
        """Build violation message."""
        if "upstream_layers" in then_clause:
            return (
                f"{capsule.layer.capitalize()} layer model '{capsule.name}' "
                f"sources from layers outside {then_clause['upstream_layers']}"
            )
        return f"Model '{capsule.name}' violates rule '{rule.name}'"


class PropertyRuleExecutor:
    """Executes property-based rules (existence/value checks)."""

    async def execute(
        self,
        rule: Rule,
        capsules: List[Any],
        columns: List[Any],
        graph_service: GraphService,
    ) -> List[Violation]:
        violations = []
        definition = rule.definition

        check_type = definition.get("check")  # 'exists', 'not_empty', 'equals'
        property_name = definition.get("property")
        expected_value = definition.get("value")
        scope_filter = definition.get("filter", {})

        # Determine scope
        if rule.scope == "capsule":
            subjects = self._filter(capsules, scope_filter)
        else:
            subjects = self._filter(columns, scope_filter)

        for subject in subjects:
            value = getattr(subject, property_name, None)
            failed = False

            if check_type == "exists":
                failed = value is None
            elif check_type == "not_empty":
                failed = not value
            elif check_type == "equals":
                failed = value != expected_value
            elif check_type == "in":
                failed = value not in expected_value

            if failed:
                violations.append(Violation(
                    rule=rule,
                    subject_type=rule.scope,
                    subject_urn=subject.urn,
                    subject_name=subject.name,
                    message=f"{rule.scope.capitalize()} '{subject.name}' fails property check: {property_name} {check_type}",
                    details={
                        "property": property_name,
                        "check_type": check_type,
                        "actual_value": value,
                        "expected_value": expected_value,
                    }
                ))

        return violations

    def _filter(self, items, filters) -> List:
        """Filter items based on conditions."""
        result = items
        for key, value in filters.items():
            values = value if isinstance(value, list) else [value]
            result = [i for i in result if getattr(i, key, None) in values]
        return result


class ConformanceService:
    """Service for architecture conformance checking."""

    # Severity weights for scoring
    SEVERITY_WEIGHTS = {
        Severity.CRITICAL: 10,
        Severity.ERROR: 5,
        Severity.WARNING: 2,
        Severity.INFO: 1,
    }

    def __init__(
        self,
        rule_repo: RuleRepository,
        violation_repo: ViolationRepository,
        capsule_repo: CapsuleRepository,
        graph_service: GraphService,
    ):
        self.rule_repo = rule_repo
        self.violation_repo = violation_repo
        self.capsule_repo = capsule_repo
        self.graph_service = graph_service

        # Register rule executors
        self.executors = {
            RuleType.PATTERN: PatternRuleExecutor(),
            RuleType.GRAPH: GraphRuleExecutor(),
            RuleType.PROPERTY: PropertyRuleExecutor(),
        }

    async def evaluate(
        self,
        rule_sets: Optional[List[str]] = None,
        categories: Optional[List[str]] = None,
        scope_type: Optional[str] = None,  # 'domain', 'capsule', 'global'
        scope_value: Optional[str] = None,
    ) -> ConformanceResult:
        """Evaluate conformance rules."""
        # Load rules
        rules = await self.rule_repo.find_enabled(
            rule_sets=rule_sets,
            categories=categories,
        )

        # Load capsules and columns (scoped if specified)
        capsules = await self.capsule_repo.find_all(
            domain=scope_value if scope_type == "domain" else None,
            urn=scope_value if scope_type == "capsule" else None,
        )

        columns = []  # Load columns for column-scoped rules
        for capsule in capsules:
            capsule_columns = await self.capsule_repo.get_columns(capsule.id)
            columns.extend(capsule_columns)

        # Execute rules
        all_violations = []
        rules_passed = 0
        rules_failed = 0

        for rule in rules:
            executor = self.executors.get(RuleType(rule.definition.get("type")))
            if not executor:
                continue

            violations = await executor.execute(
                rule=rule,
                capsules=capsules,
                columns=columns,
                graph_service=self.graph_service,
            )

            if violations:
                rules_failed += 1
                all_violations.extend(violations)
            else:
                rules_passed += 1

        # Calculate scores
        total_rules = rules_passed + rules_failed
        score = (rules_passed / total_rules * 100) if total_rules > 0 else 100

        # Calculate weighted score
        total_weight = sum(self.SEVERITY_WEIGHTS[r.severity] for r in rules)
        failed_weight = sum(
            self.SEVERITY_WEIGHTS[v.rule.severity]
            for v in all_violations
        )
        weighted_score = ((total_weight - failed_weight) / total_weight * 100) if total_weight > 0 else 100

        # Group by severity and category
        by_severity = self._group_by_severity(rules, all_violations)
        by_category = self._group_by_category(rules, all_violations)

        # Store violations
        await self._store_violations(all_violations)

        return ConformanceResult(
            score=round(score, 2),
            weighted_score=round(weighted_score, 2),
            total_rules=total_rules,
            passing_rules=rules_passed,
            failing_rules=rules_failed,
            violations=all_violations,
            by_severity=by_severity,
            by_category=by_category,
        )

    def _group_by_severity(self, rules: List[Rule], violations: List[Violation]) -> Dict:
        """Group results by severity."""
        result = {}
        violation_rules = {v.rule.rule_id for v in violations}

        for severity in Severity:
            severity_rules = [r for r in rules if r.severity == severity]
            failing = len([r for r in severity_rules if r.rule_id in violation_rules])
            result[severity.value] = {
                "total": len(severity_rules),
                "passing": len(severity_rules) - failing,
                "failing": failing,
            }

        return result

    def _group_by_category(self, rules: List[Rule], violations: List[Violation]) -> Dict:
        """Group results by category."""
        result = {}
        categories = set(r.category for r in rules)
        violation_rules = {v.rule.rule_id for v in violations}

        for category in categories:
            cat_rules = [r for r in rules if r.category == category]
            failing = len([r for r in cat_rules if r.rule_id in violation_rules])
            passing = len(cat_rules) - failing
            score = (passing / len(cat_rules) * 100) if cat_rules else 100

            result[category] = {
                "score": round(score, 2),
                "passing": passing,
                "failing": failing,
            }

        return result

    async def _store_violations(self, violations: List[Violation]) -> None:
        """Store violations in database."""
        for violation in violations:
            await self.violation_repo.create(violation)
```

### 6.4 Default Rule Sets

```yaml
# config/rules/medallion.yaml
rules:
  - id: NAMING_001
    name: "Model naming convention"
    description: "Models must follow {layer}_{domain}_{entity} pattern"
    severity: warning
    category: naming
    rule_set: medallion
    scope: capsule
    definition:
      type: pattern
      pattern: "^(raw|stg|int|dim|fct|rpt)_[a-z]+(_[a-z]+)*$"
      apply_to: name
      filter:
        capsule_type: [model]

  - id: NAMING_002
    name: "Source naming convention"
    description: "Sources should use snake_case"
    severity: info
    category: naming
    rule_set: medallion
    scope: capsule
    definition:
      type: pattern
      pattern: "^[a-z][a-z0-9_]*$"
      apply_to: name
      filter:
        capsule_type: [source]

  - id: LINEAGE_001
    name: "Gold sources Silver only"
    description: "Gold/Mart layer models should only source from Silver/Intermediate layers"
    severity: error
    category: lineage
    rule_set: medallion
    scope: capsule
    definition:
      type: graph
      condition:
        if:
          layer: [gold, marts]
        then:
          upstream_layers: [silver, intermediate, staging]

  - id: LINEAGE_002
    name: "No Bronze to Gold direct"
    description: "Bronze layer should not directly feed Gold layer"
    severity: error
    category: lineage
    rule_set: medallion
    scope: capsule
    definition:
      type: graph
      condition:
        if:
          layer: [gold]
        then:
          upstream_layers_exclude: [bronze, raw]

  - id: DOC_001
    name: "Model description required"
    description: "All models must have a description"
    severity: warning
    category: documentation
    rule_set: dbt_best_practices
    scope: capsule
    definition:
      type: property
      check: not_empty
      property: description
      filter:
        capsule_type: [model]

  - id: DOC_002
    name: "Column description coverage"
    description: "At least 80% of columns should have descriptions"
    severity: info
    category: documentation
    rule_set: dbt_best_practices
    scope: capsule
    definition:
      type: property
      check: gte
      property: doc_coverage
      value: 0.8

  - id: PII_001
    name: "PII in Gold must be masked"
    description: "PII columns in Gold layer must have masking transformation"
    severity: critical
    category: pii
    rule_set: pii_compliance
    scope: column
    definition:
      type: graph
      condition:
        if:
          semantic_type: pii
          layer: [gold, marts]
        then:
          has_transformation: [hashed, masked, encrypted, redacted]

  - id: PII_002
    name: "PII columns must be tagged"
    description: "Columns detected as PII should have explicit PII tags"
    severity: warning
    category: pii
    rule_set: pii_compliance
    scope: column
    definition:
      type: property
      check: exists
      property: pii_type
      filter:
        pii_detected_by: pattern
```

---

## 7. Report Service

Brief design for generating reports.

```python
# src/services/report_service.py

from enum import Enum
from typing import Optional
from pathlib import Path
from jinja2 import Environment, PackageLoader

from src.services.pii_service import PIIService
from src.services.conformance_service import ConformanceService


class ReportFormat(str, Enum):
    HTML = "html"
    JSON = "json"
    CSV = "csv"


class ReportService:
    """Service for generating formatted reports."""

    def __init__(
        self,
        pii_service: PIIService,
        conformance_service: ConformanceService,
    ):
        self.pii_service = pii_service
        self.conformance_service = conformance_service
        self.jinja_env = Environment(loader=PackageLoader("src", "templates"))

    async def generate_pii_report(
        self,
        format: ReportFormat = ReportFormat.HTML,
        output_path: Optional[Path] = None,
    ) -> str:
        """Generate PII inventory report."""
        inventory = await self.pii_service.get_inventory()
        exposures = await self.pii_service.detect_exposure()

        if format == ReportFormat.HTML:
            template = self.jinja_env.get_template("pii_report.html")
            content = template.render(inventory=inventory, exposures=exposures)
        elif format == ReportFormat.JSON:
            content = {"inventory": inventory, "exposures": exposures}
        else:
            content = self._to_csv(inventory)

        if output_path:
            output_path.write_text(str(content))

        return content

    async def generate_conformance_report(
        self,
        format: ReportFormat = ReportFormat.HTML,
        output_path: Optional[Path] = None,
    ) -> str:
        """Generate conformance report."""
        result = await self.conformance_service.evaluate()

        if format == ReportFormat.HTML:
            template = self.jinja_env.get_template("conformance_report.html")
            content = template.render(result=result)
        elif format == ReportFormat.JSON:
            content = result
        else:
            content = self._violations_to_csv(result.violations)

        if output_path:
            output_path.write_text(str(content))

        return content
```

---

## 8. CLI Design

### 8.1 Command Structure

```
dab
├── ingest
│   ├── dbt           # Ingest dbt artifacts
│   └── status        # Check ingestion status
├── capsules
│   ├── list          # List capsules
│   ├── show          # Show capsule details
│   └── lineage       # Get capsule lineage
├── columns
│   ├── list          # List columns
│   ├── show          # Show column details
│   └── lineage       # Get column lineage
├── pii
│   ├── inventory     # PII inventory
│   ├── trace         # Trace PII column
│   └── exposure      # Check PII exposure
├── conformance
│   ├── score         # Get conformance score
│   ├── violations    # List violations
│   └── check         # Run conformance check
└── report
    ├── pii           # Generate PII report
    └── conformance   # Generate conformance report
```

### 8.2 CLI Implementation

```python
# src/cli/main.py

import typer
from typing import Optional
from pathlib import Path
from rich.console import Console
from rich.table import Table

app = typer.Typer(name="dab", help="Data Capsule Server CLI")
console = Console()


# Ingest commands
ingest_app = typer.Typer(help="Metadata ingestion commands")
app.add_typer(ingest_app, name="ingest")


@ingest_app.command("dbt")
def ingest_dbt(
    manifest: Path = typer.Option(..., "--manifest", "-m", help="Path to manifest.json"),
    catalog: Optional[Path] = typer.Option(None, "--catalog", "-c", help="Path to catalog.json"),
    project_name: Optional[str] = typer.Option(None, "--project", "-p", help="Project name override"),
    run_conformance: bool = typer.Option(True, "--conformance/--no-conformance", help="Run conformance check"),
):
    """Ingest dbt artifacts into the graph."""
    from src.services.ingestion_service import IngestionService, IngestionConfig
    from src.cli.dependencies import get_ingestion_service

    service = get_ingestion_service()

    with console.status("Ingesting dbt artifacts..."):
        result = service.ingest(IngestionConfig(
            source_type="dbt",
            source_name=project_name or manifest.parent.name,
            config={
                "manifest_path": str(manifest),
                "catalog_path": str(catalog) if catalog else None,
                "project_name": project_name,
            },
            run_conformance=run_conformance,
        ))

    # Display results
    console.print(f"\n[green]Ingestion completed![/green]")
    console.print(f"Job ID: {result.job_id}")

    table = Table(title="Ingestion Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Count", style="magenta")

    for key, value in result.stats.items():
        table.add_row(key.replace("_", " ").title(), str(value))

    console.print(table)


# PII commands
pii_app = typer.Typer(help="PII tracking commands")
app.add_typer(pii_app, name="pii")


@pii_app.command("inventory")
def pii_inventory(
    pii_type: Optional[str] = typer.Option(None, "--type", "-t", help="Filter by PII type"),
    layer: Optional[str] = typer.Option(None, "--layer", "-l", help="Filter by layer"),
    format: str = typer.Option("table", "--format", "-f", help="Output format: table, json, csv"),
):
    """Get PII inventory."""
    from src.services.pii_service import PIIService
    from src.cli.dependencies import get_pii_service

    service = get_pii_service()
    result = service.get_inventory(pii_type=pii_type, layer=layer)

    if format == "json":
        console.print_json(data=result)
    else:
        # Display as table
        console.print(f"\n[bold]PII Inventory Summary[/bold]")
        console.print(f"Total PII columns: {result['summary']['total_pii_columns']}")
        console.print(f"Capsules with PII: {result['summary']['capsules_with_pii']}")

        table = Table(title="PII by Type")
        table.add_column("PII Type", style="cyan")
        table.add_column("Columns", style="magenta")
        table.add_column("Capsules", style="green")
        table.add_column("Layers", style="yellow")

        for item in result["by_pii_type"]:
            table.add_row(
                item["pii_type"],
                str(item["column_count"]),
                str(item["capsule_count"]),
                ", ".join(item["layers"]),
            )

        console.print(table)


@pii_app.command("trace")
def pii_trace(
    column_urn: str = typer.Argument(..., help="Column URN to trace"),
):
    """Trace a PII column through the pipeline."""
    from src.services.pii_service import PIIService
    from src.cli.dependencies import get_pii_service

    service = get_pii_service()
    result = service.trace_pii(column_urn)

    console.print(f"\n[bold]PII Trace: {result.column['name']}[/bold]")
    console.print(f"Origin: {result.origin['capsule_name']}.{result.origin['name']}")

    console.print("\n[bold]Propagation Path:[/bold]")
    for step in result.propagation_path:
        status_icon = "[red]!" if step["pii_status"] == "unmasked" else "[green]✓"
        console.print(f"  {status_icon}[/] {step['layer']} → {step['column_urn']} ({step['transformation'] or 'direct'})")

    console.print(f"\n[bold]Risk Summary:[/bold]")
    console.print(f"  Unmasked terminals: {result.risk_summary['unmasked_terminals']}")
    console.print(f"  Overall risk: {result.risk_summary['overall_risk']}")


# Conformance commands
conformance_app = typer.Typer(help="Conformance checking commands")
app.add_typer(conformance_app, name="conformance")


@conformance_app.command("score")
def conformance_score(
    domain: Optional[str] = typer.Option(None, "--domain", "-d", help="Scope to domain"),
    rule_set: Optional[str] = typer.Option(None, "--rule-set", "-r", help="Filter by rule set"),
):
    """Get conformance score."""
    from src.services.conformance_service import ConformanceService
    from src.cli.dependencies import get_conformance_service

    service = get_conformance_service()
    result = service.evaluate(
        scope_type="domain" if domain else "global",
        scope_value=domain,
        rule_sets=[rule_set] if rule_set else None,
    )

    # Display score with color coding
    score_color = "green" if result.score >= 80 else "yellow" if result.score >= 60 else "red"
    console.print(f"\n[bold]Conformance Score: [{score_color}]{result.score}%[/{score_color}][/bold]")
    console.print(f"Weighted Score: {result.weighted_score}%")
    console.print(f"Rules: {result.passing_rules}/{result.total_rules} passing")

    # By severity
    console.print("\n[bold]By Severity:[/bold]")
    for severity, data in result.by_severity.items():
        console.print(f"  {severity}: {data['passing']}/{data['total']} passing")


@conformance_app.command("violations")
def conformance_violations(
    severity: Optional[str] = typer.Option(None, "--severity", "-s", help="Filter by severity"),
    category: Optional[str] = typer.Option(None, "--category", "-c", help="Filter by category"),
    format: str = typer.Option("table", "--format", "-f", help="Output format"),
):
    """List conformance violations."""
    from src.services.conformance_service import ConformanceService
    from src.cli.dependencies import get_conformance_service

    service = get_conformance_service()
    result = service.evaluate()

    violations = result.violations
    if severity:
        violations = [v for v in violations if v.rule.severity.value == severity]
    if category:
        violations = [v for v in violations if v.rule.category == category]

    if format == "json":
        console.print_json(data=[v.__dict__ for v in violations])
    else:
        table = Table(title=f"Violations ({len(violations)} total)")
        table.add_column("Rule", style="cyan")
        table.add_column("Severity", style="magenta")
        table.add_column("Subject", style="green")
        table.add_column("Message", style="white")

        for v in violations:
            severity_color = {
                "critical": "red",
                "error": "red",
                "warning": "yellow",
                "info": "blue",
            }.get(v.rule.severity.value, "white")

            table.add_row(
                v.rule.rule_id,
                f"[{severity_color}]{v.rule.severity.value}[/{severity_color}]",
                v.subject_name,
                v.message[:50] + "..." if len(v.message) > 50 else v.message,
            )

        console.print(table)


if __name__ == "__main__":
    app()
```

---

*End of Component Design Document*
