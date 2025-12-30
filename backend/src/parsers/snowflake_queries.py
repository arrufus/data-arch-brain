"""SQL query templates for Snowflake metadata extraction."""

# Extract tables and views from INFORMATION_SCHEMA
QUERY_TABLES = """
SELECT
    TABLE_CATALOG AS database_name,
    TABLE_SCHEMA AS schema_name,
    TABLE_NAME AS table_name,
    TABLE_TYPE,
    ROW_COUNT,
    BYTES,
    CREATED,
    LAST_ALTERED,
    COMMENT AS description
FROM {database}.INFORMATION_SCHEMA.TABLES
WHERE TABLE_SCHEMA NOT IN ('INFORMATION_SCHEMA', 'ACCOUNT_USAGE')
  {schema_filter}
  {type_filter}
  {incremental_filter}
ORDER BY TABLE_SCHEMA, TABLE_NAME
"""

# Extract columns from INFORMATION_SCHEMA
QUERY_COLUMNS = """
SELECT
    TABLE_CATALOG AS database_name,
    TABLE_SCHEMA AS schema_name,
    TABLE_NAME AS table_name,
    COLUMN_NAME,
    ORDINAL_POSITION,
    DATA_TYPE,
    IS_NULLABLE,
    COLUMN_DEFAULT,
    CHARACTER_MAXIMUM_LENGTH,
    NUMERIC_PRECISION,
    NUMERIC_SCALE,
    COMMENT AS description
FROM {database}.INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA NOT IN ('INFORMATION_SCHEMA', 'ACCOUNT_USAGE')
  {schema_filter}
ORDER BY TABLE_SCHEMA, TABLE_NAME, ORDINAL_POSITION
"""

# Extract view definitions
# Note: We select just the view metadata here, then fetch DDL separately per view
QUERY_VIEW_DEFINITIONS = """
SELECT
    TABLE_CATALOG AS database_name,
    TABLE_SCHEMA AS schema_name,
    TABLE_NAME AS view_name
FROM {database}.INFORMATION_SCHEMA.VIEWS
WHERE TABLE_SCHEMA NOT IN ('INFORMATION_SCHEMA', 'ACCOUNT_USAGE')
  {schema_filter}
ORDER BY TABLE_SCHEMA, TABLE_NAME
"""

# Extract lineage from ACCESS_HISTORY
QUERY_LINEAGE = """
WITH lineage_raw AS (
    SELECT DISTINCT
        ah.query_id,
        ah.query_start_time,
        base.value:objectName::STRING AS base_object_name,
        base.value:objectDomain::STRING AS base_object_domain,
        ref.value:objectName::STRING AS referenced_object_name,
        ref.value:objectDomain::STRING AS referenced_object_domain
    FROM SNOWFLAKE.ACCOUNT_USAGE.ACCESS_HISTORY ah,
        LATERAL FLATTEN(input => ah.base_objects_accessed) base,
        LATERAL FLATTEN(input => ah.objects_modified, OUTER => TRUE) ref
    WHERE ah.query_start_time >= DATEADD(day, -:lookback_days, CURRENT_TIMESTAMP())
      AND base.value:objectDomain IN ('Table', 'View', 'Materialized view')
      AND (ref.value:objectDomain IN ('Table', 'View', 'Materialized view')
           OR ref.value IS NULL)
      {database_filter}
    {row_limit}
)
SELECT
    referenced_object_name AS source_object,
    base_object_name AS target_object,
    COUNT(DISTINCT query_id) AS query_count,
    MAX(query_start_time) AS last_query_time
FROM lineage_raw
WHERE referenced_object_name IS NOT NULL
  AND source_object != target_object
GROUP BY source_object, target_object
ORDER BY query_count DESC
"""

# Extract tags from TAG_REFERENCES
QUERY_TAGS = """
SELECT
    TAG_DATABASE,
    TAG_SCHEMA,
    TAG_NAME,
    TAG_VALUE,
    OBJECT_DATABASE,
    OBJECT_SCHEMA,
    OBJECT_NAME,
    COLUMN_NAME,
    DOMAIN
FROM SNOWFLAKE.ACCOUNT_USAGE.TAG_REFERENCES
WHERE OBJECT_DELETED IS NULL
  AND TAG_DROPPED IS NULL
  {database_filter}
ORDER BY OBJECT_DATABASE, OBJECT_SCHEMA, OBJECT_NAME, COLUMN_NAME
"""

# Get list of accessible databases
QUERY_DATABASES = """
SELECT DATABASE_NAME
FROM SNOWFLAKE.INFORMATION_SCHEMA.DATABASES
WHERE DATABASE_NAME NOT IN ('SNOWFLAKE', 'SNOWFLAKE_SAMPLE_DATA')
  AND IS_TRANSIENT = 'NO'
ORDER BY DATABASE_NAME
"""

# Test connection
QUERY_TEST_CONNECTION = """
SELECT CURRENT_DATABASE(), CURRENT_SCHEMA(), CURRENT_ROLE(), CURRENT_USER()
"""
