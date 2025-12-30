"""Snowflake metadata parser for INFORMATION_SCHEMA and ACCOUNT_USAGE."""

import asyncio
import logging
import re
import time
from pathlib import Path
from typing import Any, Optional

import snowflake.connector
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization

from src.parsers.base import (
    MetadataParser,
    ParseError,
    ParseErrorSeverity,
    ParseResult,
    RawCapsule,
    RawColumn,
    RawEdge,
)
from src.parsers.snowflake_config import SnowflakeParserConfig
from src.parsers import snowflake_queries
from src.utils.retry import (
    retry_with_exponential_backoff,
    is_retryable_snowflake_error,
    is_permission_error,
)

logger = logging.getLogger(__name__)

# Default mappings from Snowflake tags to DCS semantic types
DEFAULT_TAG_MAPPINGS = {
    "PII": {"semantic_type": "pii", "infer_pii_type": True},
    "PII:EMAIL": {"semantic_type": "pii", "pii_type": "email"},
    "PII:PHONE": {"semantic_type": "pii", "pii_type": "phone"},
    "PII:SSN": {"semantic_type": "pii", "pii_type": "ssn"},
    "PII:ADDRESS": {"semantic_type": "pii", "pii_type": "address"},
    "PII:NAME": {"semantic_type": "pii", "pii_type": "name"},
    "PII:CREDIT_CARD": {"semantic_type": "pii", "pii_type": "credit_card"},
    "PII:IP_ADDRESS": {"semantic_type": "pii", "pii_type": "ip_address"},
    "SENSITIVE": {"semantic_type": "pii", "pii_type": "confidential"},
    "PRIMARY_KEY": {"semantic_type": "business_key"},
    "FOREIGN_KEY": {"semantic_type": "foreign_key"},
}


class SnowflakeParser(MetadataParser):
    """Parser for Snowflake INFORMATION_SCHEMA and ACCOUNT_USAGE."""

    def __init__(self) -> None:
        self.connector: Optional[snowflake.connector.SnowflakeConnection] = None
        self._query_cache: dict[str, Any] = {}  # Simple query result cache
        self._cache_enabled: bool = True

    @property
    def source_type(self) -> str:
        return "snowflake"

    def validate_config(self, config: dict[str, Any]) -> list[str]:
        """Validate configuration."""
        try:
            parser_config = SnowflakeParserConfig.from_dict(config)
            return parser_config.validate()
        except Exception as e:
            return [f"Invalid configuration: {e}"]

    async def parse(self, config: dict[str, Any]) -> ParseResult:
        """Parse Snowflake metadata."""
        from datetime import datetime, timezone

        result = ParseResult(source_type=self.source_type)

        # Capture sync start time for incremental sync
        sync_start_time = datetime.now(timezone.utc)

        # Parse and validate config
        try:
            parser_config = SnowflakeParserConfig.from_dict(config)
        except Exception as e:
            result.add_error(
                f"Invalid configuration: {e}", severity=ParseErrorSeverity.ERROR
            )
            return result

        validation_errors = parser_config.validate()
        if validation_errors:
            for error in validation_errors:
                result.add_error(error, severity=ParseErrorSeverity.ERROR)
            return result

        # Configure cache
        self._cache_enabled = parser_config.enable_query_cache
        if not self._cache_enabled:
            self._query_cache.clear()
            logger.debug("Query cache disabled")

        # Connect to Snowflake
        try:
            await self._connect(parser_config)
            logger.info(
                f"Connected to Snowflake account: {parser_config.account}, "
                f"role: {parser_config.role}, warehouse: {parser_config.warehouse}"
            )
        except Exception as e:
            result.add_error(
                f"Failed to connect to Snowflake: {e}", severity=ParseErrorSeverity.ERROR
            )
            return result

        try:
            # Determine databases to scan
            databases = await self._get_databases(parser_config, result)
            result.source_name = ", ".join(databases)
            logger.info(f"Scanning {len(databases)} database(s): {result.source_name}")

            # Track extraction start time
            extraction_start = time.time()

            # Extract metadata for each database in parallel
            if len(databases) > 1 and parser_config.parallel_execution:
                logger.info(f"Extracting metadata from {len(databases)} databases in parallel...")
                # Create tasks for parallel execution
                tasks = [
                    self._extract_database_metadata(database, parser_config, result)
                    for database in databases
                ]
                # Execute in parallel and collect results
                await asyncio.gather(*tasks, return_exceptions=True)
            else:
                # Sequential execution for single database or if parallel disabled
                for database in databases:
                    logger.info(f"Extracting metadata from database: {database}")
                    await self._extract_database_metadata(database, parser_config, result)

            extraction_duration = time.time() - extraction_start
            logger.info(
                f"Database extraction complete in {extraction_duration:.2f}s: "
                f"{len(result.capsules)} capsules, {len(result.columns)} columns"
            )

            # Extract lineage from ACCESS_HISTORY (if enabled)
            if parser_config.enable_lineage and parser_config.use_account_usage:
                logger.info("Extracting lineage from ACCESS_HISTORY...")
                lineage_start = time.time()
                await self._extract_lineage(parser_config, result, databases)
                lineage_duration = time.time() - lineage_start
                logger.info(
                    f"Lineage extraction from ACCESS_HISTORY complete: {len(result.edges)} edges "
                    f"in {lineage_duration:.2f}s"
                )

            # Extract lineage from view definitions (if lineage enabled)
            if parser_config.enable_lineage:
                logger.info("Extracting lineage from view definitions...")
                view_lineage_start = time.time()
                await self._extract_view_lineage(parser_config, result, databases)
                view_lineage_duration = time.time() - view_lineage_start
                logger.info(
                    f"View lineage extraction complete: {len(result.edges)} total edges "
                    f"in {view_lineage_duration:.2f}s"
                )

            # Extract tags from TAG_REFERENCES (if enabled)
            if parser_config.enable_tag_extraction and parser_config.use_account_usage:
                logger.info("Extracting tags from TAG_REFERENCES...")
                tags_start = time.time()
                await self._extract_tags(parser_config, result, databases)
                tags_duration = time.time() - tags_start
                logger.info(f"Tag extraction complete in {tags_duration:.2f}s")

            # Log overall extraction summary
            total_duration = time.time() - extraction_start
            logger.info(
                f"Total extraction complete in {total_duration:.2f}s: "
                f"{len(result.capsules)} capsules, "
                f"{len(result.columns)} columns, {len(result.edges)} edges"
            )

        except Exception as e:
            result.add_error(
                f"Error during metadata extraction: {e}", severity=ParseErrorSeverity.ERROR
            )
            logger.exception("Error during metadata extraction")

        finally:
            await self._disconnect()

            # Calculate total sync duration
            sync_end_time = datetime.now(timezone.utc)
            total_duration = (sync_end_time - sync_start_time).total_seconds()

            # Store sync metadata
            sync_mode = "incremental" if parser_config.last_sync_timestamp else "full"
            result.metadata["sync_mode"] = sync_mode
            result.metadata["sync_start_time"] = sync_start_time.isoformat()
            result.metadata["sync_end_time"] = sync_end_time.isoformat()
            result.metadata["last_sync_timestamp"] = sync_start_time.isoformat()

            if parser_config.last_sync_timestamp:
                result.metadata["previous_sync_timestamp"] = parser_config.last_sync_timestamp

            # Store performance metrics
            result.metadata["performance"] = {
                "total_duration_seconds": round(total_duration, 2),
                "databases_processed": len(databases) if 'databases' in locals() else 0,
                "capsules_extracted": len(result.capsules),
                "columns_extracted": len(result.columns),
                "edges_extracted": len(result.edges),
                "errors_count": len(result.errors),
                "parallel_execution": parser_config.parallel_execution,
                "cache_enabled": parser_config.enable_query_cache,
            }

            logger.info(
                f"Sync complete: mode={sync_mode}, "
                f"duration={total_duration:.2f}s, "
                f"capsules={len(result.capsules)}, "
                f"columns={len(result.columns)}, "
                f"edges={len(result.edges)}"
            )

        return result

    @retry_with_exponential_backoff(
        max_retries=3,
        base_delay=1.0,
        max_delay=30.0,
        retryable_exceptions=(Exception,),
    )
    async def _connect(self, config: SnowflakeParserConfig) -> None:
        """
        Establish Snowflake connection with retry logic.

        Retries connection up to 3 times with exponential backoff for transient failures.

        Raises:
            Exception: If connection fails after all retries
        """
        try:
            connection_params: dict[str, Any] = {
                "account": config.account,
                "user": config.user,
                "warehouse": config.warehouse,
                "role": config.role,
            }

            # Handle authentication
            if config.private_key_path:
                # Key-pair authentication (preferred for production)
                private_key = self._load_private_key(config.private_key_path)
                connection_params["private_key"] = private_key
                logger.info("Using key-pair authentication")
            else:
                # Password authentication
                connection_params["password"] = config.password
                logger.info("Using password authentication")

            # Create connection
            logger.info(f"Connecting to Snowflake account: {config.account}")
            self.connector = snowflake.connector.connect(**connection_params)
            logger.info("Snowflake connection established successfully")

        except Exception as e:
            # Provide specific error messages for common issues
            error_message = self._format_connection_error(e)
            logger.error(f"Failed to connect to Snowflake: {error_message}")

            # Re-raise with enhanced context
            if is_permission_error(e):
                raise Exception(
                    f"Permission denied: {error_message}. "
                    f"Ensure the user has appropriate roles and privileges."
                ) from e
            elif is_retryable_snowflake_error(e):
                raise Exception(f"Connection error (retryable): {error_message}") from e
            else:
                raise Exception(f"Connection error: {error_message}") from e

    def _format_connection_error(self, error: Exception) -> str:
        """Format connection error with helpful context."""
        error_str = str(error)

        # Add helpful hints for common errors
        if "account" in error_str.lower() and "not found" in error_str.lower():
            return f"{error_str}. Check that the account identifier is correct (format: orgname-accountname)."
        elif "authentication" in error_str.lower() or "password" in error_str.lower():
            return f"{error_str}. Verify credentials and check if MFA is required."
        elif "warehouse" in error_str.lower():
            return f"{error_str}. Ensure the warehouse exists and is accessible."
        elif "role" in error_str.lower():
            return f"{error_str}. Verify the role exists and the user has been granted it."
        else:
            return error_str

    async def _disconnect(self) -> None:
        """Close Snowflake connection."""
        if self.connector:
            self.connector.close()
            self.connector = None
            logger.info("Snowflake connection closed")

    def _load_private_key(self, key_path: Path) -> bytes:
        """Load private key for key-pair authentication."""
        with open(key_path, "rb") as key_file:
            private_key = serialization.load_pem_private_key(
                key_file.read(), password=None, backend=default_backend()
            )

        # Serialize to DER format for Snowflake connector
        pkb = private_key.private_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        return pkb

    def _get_cache_key(self, prefix: str, *args: Any) -> str:
        """Generate cache key from prefix and arguments."""
        import hashlib
        key_str = f"{prefix}:{':'.join(str(arg) for arg in args)}"
        return hashlib.md5(key_str.encode()).hexdigest()

    def _get_cached(self, cache_key: str) -> Optional[Any]:
        """Get value from cache if available."""
        if not self._cache_enabled:
            return None
        return self._query_cache.get(cache_key)

    def _set_cached(self, cache_key: str, value: Any) -> None:
        """Set value in cache."""
        if self._cache_enabled:
            self._query_cache[cache_key] = value

    async def _get_databases(
        self, config: SnowflakeParserConfig, result: ParseResult
    ) -> list[str]:
        """Get list of databases to scan."""
        if config.databases:
            # Use configured databases
            return config.databases

        # Check cache
        cache_key = self._get_cache_key("databases")
        cached_databases = self._get_cached(cache_key)
        if cached_databases is not None:
            logger.debug(f"Using cached database list ({len(cached_databases)} databases)")
            return cached_databases

        # Query all accessible databases
        try:
            cursor = self.connector.cursor()  # type: ignore
            cursor.execute(snowflake_queries.QUERY_DATABASES)
            databases = [row[0] for row in cursor.fetchall()]
            cursor.close()

            # Cache the result
            self._set_cached(cache_key, databases)
            logger.debug(f"Cached database list ({len(databases)} databases)")

            return databases
        except Exception as e:
            result.add_error(
                f"Failed to query databases: {e}", severity=ParseErrorSeverity.WARNING
            )
            return []

    async def _extract_database_metadata(
        self, database: str, config: SnowflakeParserConfig, result: ParseResult
    ) -> None:
        """Extract tables, columns, and views for a database with error handling and performance tracking."""
        start_time = time.time()
        tables_processed = 0
        columns_processed = 0

        try:
            # Extract tables and views
            tables = await self._query_tables(database, config)
            logger.info(f"Found {len(tables)} tables/views in {database}")

            if len(tables) == 0:
                logger.warning(
                    f"No tables found in database {database}. "
                    f"Check permissions and schema filters."
                )

            for table_row in tables:
                try:
                    capsule = self._build_capsule(table_row, config)
                    result.capsules.append(capsule)
                    tables_processed += 1

                    # Extract columns for this table
                    columns = await self._query_columns(
                        database, table_row["schema_name"], table_row["table_name"]
                    )

                    for col_row in columns:
                        column = self._build_column(col_row, capsule.urn, config)
                        result.columns.append(column)
                        columns_processed += 1

                except Exception as e:
                    error_msg = (
                        f"Error processing table {database}.{table_row.get('schema_name')}."
                        f"{table_row.get('table_name')}: {e}"
                    )
                    logger.warning(error_msg)
                    result.add_error(
                        error_msg,
                        severity=ParseErrorSeverity.WARNING,
                        context={
                            "database": database,
                            "schema": table_row.get('schema_name'),
                            "table": table_row.get('table_name'),
                        }
                    )
                    # Continue processing other tables

            # Log performance metrics
            duration = time.time() - start_time
            logger.info(
                f"Database {database} extraction complete: "
                f"{tables_processed} tables, {columns_processed} columns "
                f"in {duration:.2f}s"
            )

        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"Error extracting metadata from database {database}: {e}"
            logger.error(f"{error_msg} (after {duration:.2f}s)")
            result.add_error(
                error_msg,
                severity=ParseErrorSeverity.ERROR,
                context={"database": database, "duration_seconds": duration}
            )

    async def _query_tables(
        self, database: str, config: SnowflakeParserConfig
    ) -> list[dict[str, Any]]:
        """Query INFORMATION_SCHEMA.TABLES for a database."""
        # Build schema filter
        schema_filter = ""
        if config.schemas:
            schema_list = ", ".join([f"'{s}'" for s in config.schemas])
            schema_filter = f"AND TABLE_SCHEMA IN ({schema_list})"

        # Build type filter
        type_filters = []
        if config.include_views:
            type_filters.append("'VIEW'")
        if config.include_materialized_views:
            type_filters.append("'MATERIALIZED VIEW'")
        if config.include_external_tables:
            type_filters.append("'EXTERNAL TABLE'")

        # Always include base tables
        type_filters.append("'BASE TABLE'")

        type_filter = f"AND TABLE_TYPE IN ({', '.join(type_filters)})"

        # Build incremental filter
        incremental_filter = ""
        if config.last_sync_timestamp:
            incremental_filter = f"AND LAST_ALTERED > '{config.last_sync_timestamp}'"

        # Format query
        query = snowflake_queries.QUERY_TABLES.format(
            database=database,
            schema_filter=schema_filter,
            type_filter=type_filter,
            incremental_filter=incremental_filter,
        )

        cursor = self.connector.cursor()  # type: ignore
        cursor.execute(query)
        columns = [desc[0].lower() for desc in cursor.description]
        tables = [dict(zip(columns, row)) for row in cursor.fetchall()]
        cursor.close()

        return tables

    async def _query_columns(
        self, database: str, schema: str, table: str
    ) -> list[dict[str, Any]]:
        """Query INFORMATION_SCHEMA.COLUMNS for a specific table."""
        schema_filter = f"AND TABLE_SCHEMA = '{schema}' AND TABLE_NAME = '{table}'"

        query = snowflake_queries.QUERY_COLUMNS.format(
            database=database, schema_filter=schema_filter
        )

        cursor = self.connector.cursor()  # type: ignore
        cursor.execute(query)
        columns = [desc[0].lower() for desc in cursor.description]
        column_rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        cursor.close()

        return column_rows

    def _build_capsule(
        self, row: dict[str, Any], config: SnowflakeParserConfig
    ) -> RawCapsule:
        """Build RawCapsule from Snowflake table row."""
        database_name = row["database_name"]
        schema_name = row["schema_name"]
        table_name = row["table_name"]
        table_type = row["table_type"]

        # Build URN
        urn = self._build_urn(table_type, database_name, schema_name, table_name)

        # Build unique ID (fully qualified name)
        unique_id = f"{database_name}.{schema_name}.{table_name}"

        # Infer layer from schema name
        layer = self._infer_layer(schema_name, config)

        # Normalize table type
        capsule_type = self._normalize_table_type(table_type)

        # Build capsule
        return RawCapsule(
            urn=urn,
            name=table_name,
            capsule_type=capsule_type,
            unique_id=unique_id,
            database_name=database_name,
            schema_name=schema_name,
            layer=layer,
            description=row.get("description"),
            materialization=capsule_type,
            meta={
                "row_count": row.get("row_count"),
                "bytes": row.get("bytes"),
                "created": str(row.get("created")) if row.get("created") else None,
                "last_altered": (
                    str(row.get("last_altered")) if row.get("last_altered") else None
                ),
                "table_type": table_type,
            },
            tags=[],
        )

    def _build_column(
        self, row: dict[str, Any], capsule_urn: str, config: SnowflakeParserConfig
    ) -> RawColumn:
        """Build RawColumn from Snowflake column row."""
        database_name = row["database_name"]
        schema_name = row["schema_name"]
        table_name = row["table_name"]
        column_name = row["column_name"]

        # Build URN
        urn = self._build_column_urn(database_name, schema_name, table_name, column_name)

        # Normalize data type
        data_type = self._normalize_data_type(row.get("data_type", ""))

        # Determine if nullable
        is_nullable = row.get("is_nullable", "YES") == "YES"

        return RawColumn(
            urn=urn,
            capsule_urn=capsule_urn,
            name=column_name,
            data_type=data_type,
            ordinal_position=row.get("ordinal_position"),
            is_nullable=is_nullable,
            description=row.get("description"),
            meta={
                "column_default": row.get("column_default"),
                "character_maximum_length": row.get("character_maximum_length"),
                "numeric_precision": row.get("numeric_precision"),
                "numeric_scale": row.get("numeric_scale"),
            },
            tags=[],
        )

    def _build_urn(
        self, table_type: str, database: str, schema: str, name: str
    ) -> str:
        """Build URN for Snowflake object."""
        normalized_type = self._normalize_table_type(table_type)
        namespace = f"{database}.{schema}"
        return f"urn:dcs:snowflake:{normalized_type}:{namespace}:{name}"

    def _build_column_urn(
        self, database: str, schema: str, table: str, column: str
    ) -> str:
        """Build URN for Snowflake column."""
        namespace = f"{database}.{schema}"
        return f"urn:dcs:snowflake:column:{namespace}:{table}.{column}"

    def _normalize_table_type(self, table_type: str) -> str:
        """Normalize Snowflake table type to DCS capsule type."""
        table_type_upper = table_type.upper()

        if table_type_upper == "BASE TABLE":
            return "table"
        elif table_type_upper == "VIEW":
            return "view"
        elif table_type_upper == "MATERIALIZED VIEW":
            return "materialized_view"
        elif table_type_upper == "EXTERNAL TABLE":
            return "external_table"
        else:
            return "table"  # Default fallback

    def _normalize_data_type(self, data_type: str) -> str:
        """Normalize Snowflake data type to standard type."""
        data_type_upper = data_type.upper()

        # Integer types
        if "NUMBER" in data_type_upper and ",0)" in data_type_upper:
            return "INTEGER"
        elif "NUMBER" in data_type_upper:
            return "DECIMAL"

        # Floating point
        if data_type_upper in ("FLOAT", "DOUBLE", "REAL"):
            return "FLOAT"

        # String types
        if data_type_upper.startswith("VARCHAR"):
            return "STRING"
        if data_type_upper in ("TEXT", "STRING"):
            return "STRING"

        # Temporal types
        if "TIMESTAMP" in data_type_upper:
            if "LTZ" in data_type_upper:
                return "TIMESTAMP_TZ"
            return "TIMESTAMP"
        if data_type_upper == "DATE":
            return "DATE"
        if data_type_upper == "TIME":
            return "TIME"

        # Semi-structured types
        if data_type_upper == "VARIANT":
            return "JSON"
        if data_type_upper == "ARRAY":
            return "ARRAY"
        if data_type_upper == "OBJECT":
            return "STRUCT"

        # Boolean
        if data_type_upper == "BOOLEAN":
            return "BOOLEAN"

        # Binary
        if data_type_upper in ("BINARY", "VARBINARY"):
            return "BINARY"

        # Return original if no mapping
        return data_type

    def _infer_layer(
        self, schema_name: str, config: SnowflakeParserConfig
    ) -> Optional[str]:
        """Infer architecture layer from schema name."""
        for layer, patterns in config.layer_patterns.items():
            for pattern in patterns:
                if re.match(pattern, schema_name, re.IGNORECASE):
                    return layer
        return None

    async def _extract_lineage(
        self,
        config: SnowflakeParserConfig,
        result: ParseResult,
        databases: list[str],
    ) -> None:
        """Extract lineage from ACCESS_HISTORY."""
        try:
            # Query ACCESS_HISTORY for lineage
            lineage_rows = await self._query_lineage(config, databases)
            logger.info(f"Found {len(lineage_rows)} lineage relationships")

            # Build map of existing capsule URNs for validation
            capsule_urns = {capsule.urn for capsule in result.capsules}

            # Track edges to de-duplicate
            edges_map: dict[tuple[str, str], dict[str, Any]] = {}

            for row in lineage_rows:
                try:
                    # Build URNs from fully qualified names
                    source_urn = self._build_urn_from_fqn(row["source_object"])
                    target_urn = self._build_urn_from_fqn(row["target_object"])

                    # Skip if either object not in extracted capsules (deleted or filtered out)
                    if source_urn not in capsule_urns or target_urn not in capsule_urns:
                        logger.debug(
                            f"Skipping lineage edge: {row['source_object']} -> {row['target_object']} "
                            "(one or both objects not found in extracted capsules)"
                        )
                        continue

                    # Skip self-referencing edges
                    if source_urn == target_urn:
                        continue

                    # De-duplicate: aggregate metadata for same edge
                    edge_key = (source_urn, target_urn)
                    if edge_key in edges_map:
                        # Update query count and last query time
                        existing = edges_map[edge_key]
                        existing["query_count"] += row.get("query_count", 1)
                        if row.get("last_query_time"):
                            if not existing.get("last_query_time") or row["last_query_time"] > existing["last_query_time"]:
                                existing["last_query_time"] = row["last_query_time"]
                    else:
                        # New edge
                        edges_map[edge_key] = {
                            "source_urn": source_urn,
                            "target_urn": target_urn,
                            "query_count": row.get("query_count", 1),
                            "last_query_time": row.get("last_query_time"),
                        }

                except Exception as e:
                    result.add_error(
                        f"Error processing lineage row: {e}",
                        severity=ParseErrorSeverity.WARNING,
                    )

            # Build RawEdge objects from de-duplicated edges
            for edge_data in edges_map.values():
                edge = RawEdge(
                    source_urn=edge_data["source_urn"],
                    target_urn=edge_data["target_urn"],
                    edge_type="flows_to",
                    transformation="query",
                    meta={
                        "query_count": edge_data["query_count"],
                        "last_query_time": (
                            str(edge_data["last_query_time"])
                            if edge_data["last_query_time"]
                            else None
                        ),
                        "source": "snowflake_access_history",
                    },
                )
                result.edges.append(edge)

            logger.info(f"Created {len(result.edges)} lineage edges after de-duplication")

        except Exception as e:
            result.add_error(
                f"Error extracting lineage: {e}",
                severity=ParseErrorSeverity.ERROR,
            )
            logger.exception("Error extracting lineage from ACCESS_HISTORY")

    async def _extract_view_lineage(
        self,
        config: SnowflakeParserConfig,
        result: ParseResult,
        databases: list[str],
    ) -> None:
        """
        Extract lineage from view definitions by parsing SQL DDL.

        This complements the ACCESS_HISTORY lineage by capturing structural
        dependencies defined in view DDL.

        Args:
            config: Parser configuration
            result: Parse result to add edges to
            databases: List of databases to process
        """
        try:
            # Track edges before adding view lineage
            edges_before = len(result.edges)

            # Build map of existing capsule URNs for validation
            capsule_urns = {capsule.urn for capsule in result.capsules}

            # Track edges to de-duplicate (may overlap with ACCESS_HISTORY)
            edges_map: dict[tuple[str, str], dict[str, Any]] = {}

            # Process each database
            for database in databases:
                try:
                    # Query view definitions
                    view_rows = await self._query_view_definitions(database, config)
                    logger.info(
                        f"Found {len(view_rows)} views to process for lineage in {database}"
                    )

                    for view_row in view_rows:
                        try:
                            database_name = view_row["database_name"]
                            schema_name = view_row["schema_name"]
                            view_name = view_row["view_name"]

                            # Fetch view DDL using GET_DDL function
                            try:
                                fqn = f"{database_name}.{schema_name}.{view_name}"
                                ddl_cursor = self.connector.cursor()  # type: ignore
                                ddl_cursor.execute(f"SELECT GET_DDL('VIEW', '{fqn}')")
                                ddl_result = ddl_cursor.fetchone()
                                ddl_cursor.close()
                                view_definition = ddl_result[0] if ddl_result else None
                            except Exception as e:
                                logger.warning(f"Failed to get DDL for view {fqn}: {e}")
                                view_definition = None

                            if not view_definition:
                                logger.debug(f"Skipping view {database_name}.{schema_name}.{view_name}: no definition")
                                continue

                            # Build URN for the target (the view itself)
                            target_urn = self._build_urn("VIEW", database_name, schema_name, view_name)

                            # Skip if view not in extracted capsules
                            if target_urn not in capsule_urns:
                                logger.debug(
                                    f"Skipping view lineage: {database_name}.{schema_name}.{view_name} "
                                    "not found in extracted capsules"
                                )
                                continue

                            # Parse view SQL to extract dependencies
                            dependencies = self._parse_view_dependencies(
                                view_definition, database_name, schema_name
                            )

                            # Create edges for each dependency
                            for dep_database, dep_schema, dep_table in dependencies:
                                # Build source URN (the table/view referenced by this view)
                                source_urn = self._build_urn(
                                    "BASE TABLE", dep_database, dep_schema, dep_table
                                )

                                # Skip if source not in extracted capsules
                                if source_urn not in capsule_urns:
                                    logger.debug(
                                        f"Skipping dependency: {dep_database}.{dep_schema}.{dep_table} "
                                        "not found in extracted capsules"
                                    )
                                    continue

                                # Skip self-referencing edges
                                if source_urn == target_urn:
                                    continue

                                # De-duplicate: track edge
                                edge_key = (source_urn, target_urn)
                                if edge_key not in edges_map:
                                    edges_map[edge_key] = {
                                        "source_urn": source_urn,
                                        "target_urn": target_urn,
                                    }

                        except Exception as e:
                            result.add_error(
                                f"Error processing view {view_row.get('database_name')}."
                                f"{view_row.get('schema_name')}.{view_row.get('view_name')}: {e}",
                                severity=ParseErrorSeverity.WARNING,
                            )
                            continue

                except Exception as e:
                    result.add_error(
                        f"Error extracting view lineage from database {database}: {e}",
                        severity=ParseErrorSeverity.WARNING,
                    )
                    logger.warning(f"Error processing views in database {database}: {e}")
                    continue

            # Build RawEdge objects from de-duplicated edges
            for edge_data in edges_map.values():
                edge = RawEdge(
                    source_urn=edge_data["source_urn"],
                    target_urn=edge_data["target_urn"],
                    edge_type="flows_to",
                    transformation="view_definition",
                    meta={
                        "source": "snowflake_view_ddl",
                    },
                )
                result.edges.append(edge)

            # Log summary
            edges_added = len(result.edges) - edges_before
            logger.info(f"Created {edges_added} view lineage edges from DDL parsing")

        except Exception as e:
            result.add_error(
                f"Error extracting view lineage: {e}",
                severity=ParseErrorSeverity.ERROR,
            )
            logger.exception("Error extracting lineage from view definitions")

    async def _query_lineage(
        self, config: SnowflakeParserConfig, databases: list[str]
    ) -> list[dict[str, Any]]:
        """Query ACCESS_HISTORY for lineage relationships."""
        # Build database filter
        database_filter = ""
        if databases:
            database_list = ", ".join([f"'{db}'" for db in databases])
            database_filter = f"AND SPLIT_PART(base_object_name, '.', 1) IN ({database_list})"

        # Build row limit (performance optimization)
        row_limit = ""
        if config.max_lineage_rows:
            row_limit = f"LIMIT {config.max_lineage_rows}"
            logger.info(f"Limiting ACCESS_HISTORY query to {config.max_lineage_rows} rows")

        # Format query with database filter and lookback days
        query = snowflake_queries.QUERY_LINEAGE.format(
            database_filter=database_filter,
            row_limit=row_limit
        )

        cursor = self.connector.cursor()  # type: ignore
        cursor.execute(query, {"lookback_days": config.lineage_lookback_days})
        columns = [desc[0].lower() for desc in cursor.description]
        lineage_rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        cursor.close()

        return lineage_rows

    async def _query_view_definitions(
        self, database: str, config: SnowflakeParserConfig
    ) -> list[dict[str, Any]]:
        """
        Query view definitions for a specific database.

        Args:
            database: Database name to query
            config: Parser configuration with schema filters

        Returns:
            List of view definition rows with database_name, schema_name, view_name, view_definition
        """
        # Build schema filter
        schema_filter = ""
        if config.schemas:
            schema_list = ", ".join([f"'{s}'" for s in config.schemas])
            schema_filter = f"AND TABLE_SCHEMA IN ({schema_list})"

        # Format query
        query = snowflake_queries.QUERY_VIEW_DEFINITIONS.format(
            database=database,
            schema_filter=schema_filter,
        )

        cursor = self.connector.cursor()  # type: ignore
        cursor.execute(query)
        columns = [desc[0].lower() for desc in cursor.description]
        view_rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        cursor.close()

        return view_rows

    def _build_urn_from_fqn(self, fqn: str) -> str:
        """
        Build URN from fully qualified name (database.schema.table).

        Args:
            fqn: Fully qualified name like "PROD.RAW_DATA.CUSTOMERS"

        Returns:
            URN like "urn:dcs:snowflake:table:PROD.RAW_DATA:CUSTOMERS"
        """
        parts = fqn.split(".")
        if len(parts) != 3:
            # Fallback for malformed FQN
            return f"urn:dcs:snowflake:table:::{fqn}"

        database, schema, table = parts
        # Default to table type (most common for lineage)
        return self._build_urn("BASE TABLE", database, schema, table)

    def _parse_view_dependencies(
        self, view_sql: str, default_database: str, default_schema: str
    ) -> list[tuple[str, str, str]]:
        """
        Parse SQL DDL to extract table/view references.

        Args:
            view_sql: The SQL DDL of the view
            default_database: Default database name for unqualified references
            default_schema: Default schema name for unqualified references

        Returns:
            List of (database, schema, table) tuples
        """
        dependencies = []

        # Normalize SQL: remove comments and extra whitespace
        sql = re.sub(r'--.*$', '', view_sql, flags=re.MULTILINE)  # Remove line comments
        sql = re.sub(r'/\*.*?\*/', '', sql, flags=re.DOTALL)  # Remove block comments
        sql = ' '.join(sql.split())  # Normalize whitespace

        # Pattern to match table references in FROM and JOIN clauses
        # Matches: FROM/JOIN [database].[schema].table or [schema].table or table
        # Handles optional quotes around identifiers
        pattern = r'(?:FROM|JOIN)\s+(?:"?(\w+)"?\.)?(?:"?(\w+)"?\.)?(?:"?(\w+)"?)'

        matches = re.finditer(pattern, sql, re.IGNORECASE)

        for match in matches:
            part1, part2, part3 = match.groups()

            # Determine database, schema, and table based on how many parts were matched
            if part1 and part2 and part3:
                # Three parts: database.schema.table
                database = part1.upper()
                schema = part2.upper()
                table = part3.upper()
            elif part2 and part3:
                # Two parts: schema.table (use default database)
                database = default_database.upper()
                schema = part2.upper()
                table = part3.upper()
            elif part3:
                # One part: table (use defaults)
                database = default_database.upper()
                schema = default_schema.upper()
                table = part3.upper()
            else:
                continue

            dependencies.append((database, schema, table))

        # De-duplicate dependencies
        unique_dependencies = list(set(dependencies))

        if unique_dependencies:
            logger.debug(
                f"Extracted {len(unique_dependencies)} unique dependencies from view SQL"
            )

        return unique_dependencies

    async def _extract_tags(
        self, config: SnowflakeParserConfig, result: ParseResult, databases: list[str]
    ) -> None:
        """
        Extract tags from TAG_REFERENCES and apply to columns.

        Args:
            config: Parser configuration
            result: Parse result to enrich with tags
            databases: List of database names to filter
        """
        try:
            # Query TAG_REFERENCES
            tag_rows = await self._query_tags(config, databases)
            logger.info(f"Found {len(tag_rows)} tag references")

            # Build map of column URNs for quick lookup
            column_urn_map = {col.urn: col for col in result.columns}

            # Track tag applications
            tags_applied = 0

            # Process each tag reference
            for row in tag_rows:
                try:
                    # Skip table-level tags (only process column tags)
                    column_name = row.get("column_name")
                    if not column_name:
                        continue

                    # Build column URN
                    database = row["object_database"]
                    schema = row["object_schema"]
                    table = row["object_name"]
                    column_urn = self._build_column_urn(database, schema, table, column_name)

                    # Find column in result
                    column = column_urn_map.get(column_urn)
                    if not column:
                        logger.debug(
                            f"Column not found for tag: {database}.{schema}.{table}.{column_name}"
                        )
                        continue

                    # Map tag to semantic type
                    tag_name = row["tag_name"]
                    tag_value = row.get("tag_value")
                    full_tag = f"{tag_name}:{tag_value}" if tag_value else tag_name

                    mapping = self._map_tag_to_semantic_type(full_tag, config)
                    if mapping:
                        # Apply semantic type
                        if "semantic_type" in mapping and not column.semantic_type:
                            column.semantic_type = mapping["semantic_type"]

                        # Apply PII type
                        if "pii_type" in mapping:
                            column.pii_type = mapping["pii_type"]
                            column.pii_detected_by = "snowflake_tag"
                            tags_applied += 1
                        elif mapping.get("infer_pii_type"):
                            # Infer PII type from column name
                            inferred_type = self._infer_pii_type(column_name)
                            if inferred_type:
                                column.pii_type = inferred_type
                                column.pii_detected_by = "snowflake_tag_inferred"
                                tags_applied += 1

                        logger.debug(
                            f"Applied tag {full_tag} to column {column_urn}: "
                            f"semantic_type={column.semantic_type}, pii_type={column.pii_type}"
                        )

                except Exception as e:
                    result.add_error(
                        f"Error processing tag row: {e}", severity=ParseErrorSeverity.WARNING
                    )
                    continue

            logger.info(f"Applied tags to {tags_applied} columns")

        except Exception as e:
            result.add_error(
                f"Error extracting tags: {e}", severity=ParseErrorSeverity.ERROR
            )
            logger.exception("Error extracting tags from TAG_REFERENCES")

    async def _query_tags(
        self, config: SnowflakeParserConfig, databases: list[str]
    ) -> list[dict[str, Any]]:
        """
        Query TAG_REFERENCES for tag metadata.

        Args:
            config: Parser configuration
            databases: List of database names to filter

        Returns:
            List of tag reference rows
        """
        # Build database filter
        database_filter = ""
        if databases:
            database_list = ", ".join([f"'{db}'" for db in databases])
            database_filter = f"AND OBJECT_DATABASE IN ({database_list})"

        # Format query with database filter
        query = snowflake_queries.QUERY_TAGS.format(database_filter=database_filter)

        cursor = self.connector.cursor()  # type: ignore
        cursor.execute(query)
        columns = [desc[0].lower() for desc in cursor.description]
        tag_rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        cursor.close()

        return tag_rows

    def _map_tag_to_semantic_type(
        self, tag_name: str, config: SnowflakeParserConfig
    ) -> Optional[dict[str, Any]]:
        """
        Map Snowflake tag name to DCS semantic type.

        Checks custom mappings first, then falls back to defaults.

        Args:
            tag_name: Tag name from Snowflake (e.g., "PII", "PII:EMAIL")
            config: Parser configuration with custom mappings

        Returns:
            Mapping dict with semantic_type and optionally pii_type, or None
        """
        # Try custom mappings first
        if tag_name in config.tag_mappings:
            return config.tag_mappings[tag_name]

        # Try case-insensitive match on custom mappings
        tag_upper = tag_name.upper()
        for key, value in config.tag_mappings.items():
            if key.upper() == tag_upper:
                return value

        # Fall back to default mappings
        if tag_name in DEFAULT_TAG_MAPPINGS:
            return DEFAULT_TAG_MAPPINGS[tag_name]

        # Try case-insensitive match on defaults
        for key, value in DEFAULT_TAG_MAPPINGS.items():
            if key.upper() == tag_upper:
                return value

        # No mapping found
        logger.debug(f"No mapping found for tag: {tag_name}")
        return None

    def _infer_pii_type(self, column_name: str) -> Optional[str]:
        """
        Infer PII type from column name patterns.

        Args:
            column_name: Column name to analyze

        Returns:
            Inferred PII type or None
        """
        # Normalize column name
        name_lower = column_name.lower()

        # PII type inference patterns (order matters - check more specific first)
        patterns = {
            "ip_address": [r"ip_address", r"ip_addr"],
            "credit_card": [r"credit_card", r"cc_number", r"card_number"],
            "email": [r"email", r"e_mail", r"mail"],
            "phone": [r"phone", r"tel", r"mobile", r"cell"],
            "ssn": [r"ssn", r"social_security"],
            "name": [r"first_name", r"last_name", r"full_name", r"username"],
            "address": [r"address", r"addr", r"street", r"city", r"state", r"zip"],
        }

        for pii_type, patterns_list in patterns.items():
            for pattern in patterns_list:
                if re.search(pattern, name_lower):
                    return pii_type

        return None
