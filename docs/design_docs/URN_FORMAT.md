# URN Format Specification

## Overview

Data Capsule Server uses Uniform Resource Names (URNs) to uniquely identify all data assets within the platform. This document specifies the URN format and explains the design decisions behind it.

## Format

All URNs in Data Capsule Server follow this structure:

```
urn:dab:{source}:{type}:{namespace}:{name}
```

### Components

1. **Prefix**: Always `urn:dab`
   - Maintained for backward compatibility
   - See "Design Decision" section below

2. **Source**: The source system
   - `dbt` - dbt models, sources, and seeds
   - `airflow` - Airflow DAGs and tasks
   - `domain` - Business domains (graph nodes)
   - `tag` - Tags (graph nodes)
   - `capsule` - Direct capsule references

3. **Type**: The asset type
   - `model` - dbt models
   - `source` - dbt sources
   - `seed` - dbt seeds
   - `dag` - Airflow DAGs
   - `task` - Airflow tasks

4. **Namespace**: Organizational grouping
   - For dbt: schema name or project name
   - For Airflow: instance name
   - For domains/tags: not applicable (uses name directly)

5. **Name**: The specific asset identifier
   - For dbt models: model name
   - For Airflow: DAG ID or task ID
   - Must be unique within the namespace

## Examples

### dbt Assets
```
urn:dab:dbt:model:staging:stg_customers
urn:dab:dbt:source:raw:raw_customers
urn:dab:dbt:seed:core:country_codes
```

### Airflow Assets
```
urn:dab:airflow:dag:prod-instance:customer_etl_pipeline
urn:dab:airflow:task:prod-instance:customer_etl_pipeline.extract_customers
```

### Graph Nodes
```
urn:dab:domain:finance
urn:dab:domain:customer_analytics
urn:dab:tag:pii
urn:dab:tag:experimental
```

## Design Decision: Why "dab"?

### Background

When the application was renamed from "Data Architecture Brain" (DAB) to "Data Capsule Server" (DCS), the question arose: should URNs change from `urn:dab:*` to `urn:dcs:*`?

### Decision: Keep `urn:dab`

**Rationale**:

1. **Backward Compatibility**
   - Changing URN format is a breaking change
   - Existing stored URNs would become invalid
   - Would require data migration for any existing deployments

2. **URNs are Internal Identifiers**
   - URNs are primarily for internal system use
   - They don't represent user-facing branding
   - The prefix doesn't affect functionality

3. **Namespace Independence**
   - URNs serve as unique identifiers, not branding
   - The prefix is essentially a namespace delimiter
   - Similar to how `uuid:` doesn't spell out "Universally Unique Identifier"

4. **Historical Context**
   - The "dab" prefix documents the system's evolution
   - Maintains lineage with original design
   - No confusion since "dab" is just a namespace prefix

### Alternative Considered

If starting completely fresh with no existing data, `urn:dcs:*` would have been a reasonable choice. However, the benefits don't justify a breaking change.

### Future Considerations

If a future major version requires breaking changes anyway, the URN format could be reconsidered as part of that broader migration.

## Validation

URN validation uses the following regex pattern:

```regex
^urn:dab:[a-z]+:[a-z]+:[a-zA-Z0-9_.-]+:[a-zA-Z0-9_.-]+$
```

This ensures:
- Fixed prefix `urn:dab`
- Lowercase source and type identifiers
- Alphanumeric with underscores, hyphens, and dots for namespace/name

## Usage in Code

### Backend

URN generation and parsing occurs in:
- `backend/src/parsers/dbt_config.py` - dbt URN prefix configuration
- `backend/src/parsers/airflow_config.py` - Airflow URN prefix configuration
- `backend/src/api/middleware.py` - URN validation middleware
- `backend/src/services/graph_export.py` - Graph node URN generation

### Frontend

URN examples appear in:
- `frontend/src/components/compliance/PIITraceTab.tsx` - Input placeholders
- `frontend/src/lib/api/capsules.ts` - API documentation examples

## Best Practices

1. **Always use the configured prefix** - Don't hardcode `urn:dab`, use `urn_prefix` from config
2. **Validate URNs at boundaries** - Use the validation pattern for incoming URNs
3. **Document URNs in APIs** - Include URN examples in OpenAPI specs
4. **Index URNs properly** - Ensure database indexes on URN columns for performance
5. **Never expose raw URNs to end users** - Use human-readable names in UI

## Related Documentation

- [Data Model](./DATA_MODEL.md) - Database schema and relationships
- [Graph Architecture](./GRAPH_ARCHITECTURE.md) - Property graph structure
- [API Specification](../api/API_SPECIFICATION.md) - API endpoints and URN usage

---

**Last Updated**: 2025-12-17
**Status**: Active
**Review Cycle**: Annually or when breaking changes are considered
