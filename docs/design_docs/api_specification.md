# Data Capsule Server - API Specification

**Version**: 1.0
**Status**: Draft
**Last Updated**: December 2024
**Base URL**: `/api/v1`

---

## Table of Contents

1. [Overview](#1-overview)
2. [Authentication](#2-authentication)
3. [Common Patterns](#3-common-patterns)
4. [Capsule Endpoints](#4-capsule-endpoints)
5. [Column Endpoints](#5-column-endpoints)
6. [Lineage Endpoints](#6-lineage-endpoints)
7. [Compliance Endpoints](#7-compliance-endpoints)
8. [Conformance Endpoints](#8-conformance-endpoints)
9. [Ingestion Endpoints](#9-ingestion-endpoints)
10. [Domain & Tag Endpoints](#10-domain--tag-endpoints)
11. [Error Handling](#11-error-handling)

---

## 1. Overview

### 1.1 API Design Principles

| Principle | Implementation |
|-----------|----------------|
| RESTful | Resource-oriented URLs, standard HTTP methods |
| JSON | All requests/responses in JSON |
| Pagination | Cursor-based for large collections |
| Filtering | Query parameters for common filters |
| Versioning | URL prefix (`/api/v1`) |
| Documentation | OpenAPI 3.0 spec auto-generated |

### 1.2 Base URL

```
Development: http://localhost:8001/api/v1
Production:  https://dab.example.com/api/v1
```

### 1.3 Content Types

```
Request:  Content-Type: application/json
Response: Content-Type: application/json
```

---

## 2. Authentication

### 2.1 API Key Authentication (MVP)

All requests require an API key in the header:

```http
X-API-Key: your-api-key-here
```

### 2.2 Authentication Errors

```json
{
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Invalid or missing API key",
    "status": 401
  }
}
```

---

## 3. Common Patterns

### 3.1 Pagination

**Request Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | integer | 50 | Items per page (max 100) |
| `cursor` | string | null | Cursor for next page |

**Response Format:**

```json
{
  "data": [...],
  "pagination": {
    "total": 1234,
    "limit": 50,
    "has_more": true,
    "next_cursor": "eyJpZCI6IjEyMzQ1In0="
  }
}
```

### 3.2 Filtering

Common filter parameters available on list endpoints:

| Parameter | Type | Description |
|-----------|------|-------------|
| `layer` | string | Filter by architecture layer |
| `domain` | string | Filter by domain name |
| `source` | string | Filter by source system |
| `tag` | string | Filter by tag (can repeat) |
| `search` | string | Full-text search on name/description |

**Example:**
```
GET /api/v1/capsules?layer=gold&domain=customer&tag=pii&tag=critical
```

### 3.3 Sorting

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `sort` | string | `-updated_at` | Field to sort by |

Prefix with `-` for descending order.

**Example:**
```
GET /api/v1/capsules?sort=-created_at
GET /api/v1/violations?sort=severity
```

### 3.4 Field Selection

| Parameter | Type | Description |
|-----------|------|-------------|
| `fields` | string | Comma-separated fields to include |

**Example:**
```
GET /api/v1/capsules?fields=urn,name,layer
```

### 3.5 Standard Response Envelope

**Success Response:**
```json
{
  "data": { ... },
  "meta": {
    "request_id": "req_abc123",
    "timestamp": "2024-12-01T12:00:00Z"
  }
}
```

**Error Response:**
```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Capsule not found",
    "status": 404,
    "details": { ... }
  },
  "meta": {
    "request_id": "req_abc123",
    "timestamp": "2024-12-01T12:00:00Z"
  }
}
```

---

## 4. Capsule Endpoints

### 4.1 List Capsules

```http
GET /api/v1/capsules
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `layer` | string | bronze, silver, gold |
| `capsule_type` | string | model, source, seed, snapshot |
| `domain` | string | Domain name |
| `source` | string | Source system name |
| `tag` | string | Tag name (repeatable) |
| `search` | string | Full-text search |
| `has_pii` | boolean | Filter by PII presence |
| `limit` | integer | Page size |
| `cursor` | string | Pagination cursor |

**Response:**
```json
{
  "data": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "urn": "urn:dcs:dbt:model:jaffle_shop.marts:dim_customer",
      "name": "dim_customer",
      "capsule_type": "model",
      "layer": "gold",
      "schema_name": "marts",
      "database_name": "analytics",
      "domain": {
        "id": "...",
        "name": "customer"
      },
      "source_system": {
        "id": "...",
        "name": "jaffle_shop_dbt",
        "source_type": "dbt"
      },
      "owner": {
        "id": "...",
        "name": "Data Platform Team"
      },
      "materialization": "table",
      "description": "Customer dimension table",
      "column_count": 12,
      "has_pii": true,
      "has_tests": true,
      "test_count": 5,
      "doc_coverage": 0.83,
      "tags": ["customer", "dimension", "core"],
      "created_at": "2024-12-01T10:00:00Z",
      "updated_at": "2024-12-01T12:00:00Z"
    }
  ],
  "pagination": {
    "total": 234,
    "limit": 50,
    "has_more": true,
    "next_cursor": "eyJpZCI6IjEyMzQ1In0="
  }
}
```

### 4.2 Get Capsule by URN

```http
GET /api/v1/capsules/{urn}
```

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `urn` | string | URL-encoded URN |

**Response:**
```json
{
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "urn": "urn:dcs:dbt:model:jaffle_shop.marts:dim_customer",
    "name": "dim_customer",
    "capsule_type": "model",
    "layer": "gold",
    "schema_name": "marts",
    "database_name": "analytics",
    "domain": { "id": "...", "name": "customer" },
    "source_system": { "id": "...", "name": "jaffle_shop_dbt" },
    "owner": { "id": "...", "name": "Data Platform Team" },
    "materialization": "table",
    "description": "Customer dimension table with SCD Type 2 history",
    "meta": {
      "unique_id": "model.jaffle_shop.dim_customer",
      "package_name": "jaffle_shop",
      "original_file_path": "models/marts/dim_customer.sql"
    },
    "tags": ["customer", "dimension", "core"],
    "column_count": 12,
    "has_pii": true,
    "pii_column_count": 2,
    "has_tests": true,
    "test_count": 5,
    "doc_coverage": 0.83,
    "upstream_count": 3,
    "downstream_count": 8,
    "violation_count": 1,
    "conformance_score": 92.5,
    "created_at": "2024-12-01T10:00:00Z",
    "updated_at": "2024-12-01T12:00:00Z",
    "last_ingested_at": "2024-12-01T11:00:00Z"
  }
}
```

### 4.3 Get Capsule Columns

```http
GET /api/v1/capsules/{urn}/columns
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `semantic_type` | string | Filter by semantic type |
| `pii_type` | string | Filter by PII type |
| `has_tests` | boolean | Filter by test presence |

**Response:**
```json
{
  "data": [
    {
      "id": "...",
      "urn": "urn:dcs:dbt:column:jaffle_shop.marts:dim_customer.customer_id",
      "name": "customer_id",
      "data_type": "INTEGER",
      "ordinal_position": 1,
      "is_nullable": false,
      "semantic_type": "surrogate_key",
      "pii_type": null,
      "description": "Surrogate key for customer",
      "has_tests": true,
      "test_count": 2,
      "tags": ["key"]
    },
    {
      "id": "...",
      "urn": "urn:dcs:dbt:column:jaffle_shop.marts:dim_customer.email",
      "name": "email",
      "data_type": "VARCHAR",
      "ordinal_position": 3,
      "is_nullable": true,
      "semantic_type": "pii",
      "pii_type": "email",
      "pii_detected_by": "pattern",
      "description": "Customer email address",
      "has_tests": true,
      "test_count": 1,
      "tags": ["pii", "contact"]
    }
  ],
  "pagination": {
    "total": 12,
    "limit": 50,
    "has_more": false
  }
}
```

### 4.4 Get Capsule Violations

```http
GET /api/v1/capsules/{urn}/violations
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `severity` | string | critical, error, warning, info |
| `status` | string | open, acknowledged, resolved |
| `category` | string | naming, lineage, pii, documentation |

**Response:**
```json
{
  "data": [
    {
      "id": "...",
      "rule": {
        "rule_id": "NAMING_001",
        "name": "Model naming convention",
        "category": "naming"
      },
      "severity": "warning",
      "status": "open",
      "message": "Model name 'dim_customer' does not match pattern '^(dim|fct)_[a-z]+_[a-z_]+$'",
      "details": {
        "expected_pattern": "^(dim|fct)_[a-z]+_[a-z_]+$",
        "actual_value": "dim_customer"
      },
      "detected_at": "2024-12-01T11:00:00Z"
    }
  ]
}
```

---

## 5. Column Endpoints

### 5.1 List Columns

```http
GET /api/v1/columns
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `capsule_urn` | string | Filter by parent capsule |
| `semantic_type` | string | pii, business_key, metric, etc. |
| `pii_type` | string | email, ssn, phone, etc. |
| `layer` | string | Filter by capsule layer |
| `domain` | string | Filter by capsule domain |
| `search` | string | Search column names |

**Response:**
```json
{
  "data": [
    {
      "id": "...",
      "urn": "urn:dcs:dbt:column:jaffle_shop.marts:dim_customer.email",
      "name": "email",
      "data_type": "VARCHAR",
      "semantic_type": "pii",
      "pii_type": "email",
      "capsule": {
        "urn": "urn:dcs:dbt:model:jaffle_shop.marts:dim_customer",
        "name": "dim_customer",
        "layer": "gold"
      },
      "description": "Customer email address"
    }
  ]
}
```

### 5.2 Get Column by URN

```http
GET /api/v1/columns/{urn}
```

**Response:**
```json
{
  "data": {
    "id": "...",
    "urn": "urn:dcs:dbt:column:jaffle_shop.marts:dim_customer.email",
    "name": "email",
    "data_type": "VARCHAR(255)",
    "ordinal_position": 3,
    "is_nullable": true,
    "semantic_type": "pii",
    "pii_type": "email",
    "pii_detected_by": "pattern",
    "description": "Customer email address (hashed in production)",
    "capsule": {
      "urn": "urn:dcs:dbt:model:jaffle_shop.marts:dim_customer",
      "name": "dim_customer",
      "layer": "gold",
      "domain": "customer"
    },
    "stats": {
      "distinct_count": 98234,
      "null_count": 1523,
      "null_percentage": 1.5
    },
    "tags": ["pii", "contact", "masked"],
    "has_tests": true,
    "test_count": 2,
    "upstream_columns": 2,
    "downstream_columns": 5,
    "created_at": "2024-12-01T10:00:00Z",
    "updated_at": "2024-12-01T12:00:00Z"
  }
}
```

---

## 6. Lineage Endpoints

### 6.1 Get Capsule Lineage

```http
GET /api/v1/capsules/{urn}/lineage
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `direction` | string | both | upstream, downstream, both |
| `depth` | integer | 3 | Max traversal depth (1-10) |
| `include_columns` | boolean | false | Include column-level lineage |

**Response:**
```json
{
  "data": {
    "root": {
      "urn": "urn:dcs:dbt:model:jaffle_shop.marts:dim_customer",
      "name": "dim_customer",
      "layer": "gold",
      "capsule_type": "model"
    },
    "upstream": [
      {
        "urn": "urn:dcs:dbt:model:jaffle_shop.staging:stg_customers",
        "name": "stg_customers",
        "layer": "silver",
        "capsule_type": "model",
        "depth": 1,
        "edge_type": "flows_to"
      },
      {
        "urn": "urn:dcs:dbt:source:jaffle_shop.raw:raw_customers",
        "name": "raw_customers",
        "layer": "bronze",
        "capsule_type": "source",
        "depth": 2,
        "edge_type": "flows_to"
      }
    ],
    "downstream": [
      {
        "urn": "urn:dcs:dbt:model:jaffle_shop.marts:fct_orders",
        "name": "fct_orders",
        "layer": "gold",
        "capsule_type": "model",
        "depth": 1,
        "edge_type": "flows_to"
      },
      {
        "urn": "urn:dcs:dbt:model:jaffle_shop.reports:rpt_customer_metrics",
        "name": "rpt_customer_metrics",
        "layer": "gold",
        "capsule_type": "model",
        "depth": 2,
        "edge_type": "flows_to"
      }
    ],
    "edges": [
      {
        "source_urn": "urn:dcs:dbt:model:jaffle_shop.staging:stg_customers",
        "target_urn": "urn:dcs:dbt:model:jaffle_shop.marts:dim_customer",
        "edge_type": "flows_to",
        "transformation": "ref"
      }
    ],
    "summary": {
      "total_upstream": 2,
      "total_downstream": 5,
      "max_upstream_depth": 2,
      "max_downstream_depth": 3
    }
  }
}
```

### 6.2 Get Column Lineage

```http
GET /api/v1/columns/{urn}/lineage
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `direction` | string | both | upstream, downstream, both |
| `depth` | integer | 5 | Max traversal depth |

**Response:**
```json
{
  "data": {
    "root": {
      "urn": "urn:dcs:dbt:column:jaffle_shop.marts:dim_customer.email",
      "name": "email",
      "capsule_name": "dim_customer",
      "semantic_type": "pii",
      "pii_type": "email"
    },
    "upstream": [
      {
        "urn": "urn:dcs:dbt:column:jaffle_shop.staging:stg_customers.email",
        "name": "email",
        "capsule_name": "stg_customers",
        "layer": "silver",
        "depth": 1,
        "transformation_type": "direct",
        "semantic_type": "pii",
        "pii_type": "email"
      },
      {
        "urn": "urn:dcs:dbt:column:jaffle_shop.raw:raw_customers.customer_email",
        "name": "customer_email",
        "capsule_name": "raw_customers",
        "layer": "bronze",
        "depth": 2,
        "transformation_type": "renamed",
        "semantic_type": "pii",
        "pii_type": "email"
      }
    ],
    "downstream": [
      {
        "urn": "urn:dcs:dbt:column:jaffle_shop.reports:rpt_customer_metrics.email_hash",
        "name": "email_hash",
        "capsule_name": "rpt_customer_metrics",
        "layer": "gold",
        "depth": 1,
        "transformation_type": "hashed",
        "semantic_type": null,
        "pii_type": null
      }
    ],
    "transformations": [
      {
        "from_urn": "urn:dcs:dbt:column:jaffle_shop.marts:dim_customer.email",
        "to_urn": "urn:dcs:dbt:column:jaffle_shop.reports:rpt_customer_metrics.email_hash",
        "type": "hashed",
        "expression": "MD5(email)"
      }
    ]
  }
}
```

---

## 7. Compliance Endpoints

### 7.1 Get PII Inventory

```http
GET /api/v1/compliance/pii-inventory
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `pii_type` | string | Filter by specific PII type |
| `layer` | string | Filter by architecture layer |
| `domain` | string | Filter by domain |
| `group_by` | string | pii_type, layer, domain, capsule |

**Response:**
```json
{
  "data": {
    "summary": {
      "total_pii_columns": 47,
      "capsules_with_pii": 12,
      "pii_types_found": ["email", "phone", "address", "name", "ssn"]
    },
    "by_pii_type": [
      {
        "pii_type": "email",
        "column_count": 15,
        "capsule_count": 8,
        "layers": ["bronze", "silver", "gold"],
        "columns": [
          {
            "urn": "urn:dcs:dbt:column:...",
            "name": "email",
            "capsule_name": "dim_customer",
            "layer": "gold"
          }
        ]
      },
      {
        "pii_type": "phone",
        "column_count": 8,
        "capsule_count": 5,
        "layers": ["bronze", "silver"],
        "columns": [...]
      }
    ],
    "by_layer": [
      {
        "layer": "bronze",
        "pii_column_count": 25,
        "pii_types": ["email", "phone", "address", "name", "ssn"]
      },
      {
        "layer": "silver",
        "pii_column_count": 18,
        "pii_types": ["email", "phone", "address", "name"]
      },
      {
        "layer": "gold",
        "pii_column_count": 4,
        "pii_types": ["email"]
      }
    ]
  }
}
```

### 7.2 Get PII Exposure Report

```http
GET /api/v1/compliance/pii-exposure
```

Identifies PII that may be improperly exposed (unmasked PII in Gold/consumption layers).

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `layer` | string | Layer to check (default: gold) |
| `severity` | string | critical, high, medium, low |

**Response:**
```json
{
  "data": {
    "summary": {
      "exposed_pii_columns": 3,
      "affected_capsules": 2,
      "severity_breakdown": {
        "critical": 1,
        "high": 2,
        "medium": 0
      }
    },
    "exposures": [
      {
        "column": {
          "urn": "urn:dcs:dbt:column:jaffle_shop.marts:dim_customer.email",
          "name": "email",
          "pii_type": "email"
        },
        "capsule": {
          "urn": "urn:dcs:dbt:model:jaffle_shop.marts:dim_customer",
          "name": "dim_customer",
          "layer": "gold"
        },
        "severity": "high",
        "reason": "PII column in Gold layer without masking transformation",
        "recommendation": "Apply hashing or masking to email before exposing in Gold layer",
        "lineage_path": [
          "raw_customers.customer_email → stg_customers.email → dim_customer.email"
        ]
      }
    ]
  }
}
```

### 7.3 Trace PII Column

```http
GET /api/v1/compliance/pii-trace/{column_urn}
```

Traces a specific PII column through the entire pipeline.

**Response:**
```json
{
  "data": {
    "column": {
      "urn": "urn:dcs:dbt:column:jaffle_shop.staging:stg_customers.email",
      "name": "email",
      "pii_type": "email"
    },
    "origin": {
      "urn": "urn:dcs:dbt:column:jaffle_shop.raw:raw_customers.customer_email",
      "name": "customer_email",
      "capsule_name": "raw_customers",
      "layer": "bronze",
      "source_system": "source_postgres"
    },
    "propagation_path": [
      {
        "column_urn": "urn:dcs:dbt:column:jaffle_shop.raw:raw_customers.customer_email",
        "layer": "bronze",
        "pii_status": "unmasked",
        "transformation": null
      },
      {
        "column_urn": "urn:dcs:dbt:column:jaffle_shop.staging:stg_customers.email",
        "layer": "silver",
        "pii_status": "unmasked",
        "transformation": "renamed"
      },
      {
        "column_urn": "urn:dcs:dbt:column:jaffle_shop.marts:dim_customer.email",
        "layer": "gold",
        "pii_status": "unmasked",
        "transformation": "direct"
      },
      {
        "column_urn": "urn:dcs:dbt:column:jaffle_shop.reports:rpt_metrics.email_hash",
        "layer": "gold",
        "pii_status": "masked",
        "transformation": "hashed (MD5)"
      }
    ],
    "terminals": [
      {
        "column_urn": "urn:dcs:dbt:column:jaffle_shop.marts:dim_customer.email",
        "pii_status": "unmasked",
        "risk": "high"
      },
      {
        "column_urn": "urn:dcs:dbt:column:jaffle_shop.reports:rpt_metrics.email_hash",
        "pii_status": "masked",
        "risk": "low"
      }
    ],
    "risk_summary": {
      "unmasked_terminals": 1,
      "masked_terminals": 1,
      "overall_risk": "high"
    }
  }
}
```

---

## 8. Conformance Endpoints

### 8.1 Get Conformance Score

```http
GET /api/v1/conformance/score
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `scope` | string | global, domain, capsule |
| `domain` | string | Domain name (if scope=domain) |
| `capsule_urn` | string | Capsule URN (if scope=capsule) |
| `rule_set` | string | Filter by rule set |

**Response:**
```json
{
  "data": {
    "scope": "global",
    "score": 78.5,
    "weighted_score": 82.3,
    "summary": {
      "total_rules": 44,
      "passing_rules": 34,
      "failing_rules": 10,
      "not_applicable": 0
    },
    "by_severity": {
      "critical": { "total": 5, "passing": 4, "failing": 1 },
      "error": { "total": 12, "passing": 9, "failing": 3 },
      "warning": { "total": 20, "passing": 16, "failing": 4 },
      "info": { "total": 7, "passing": 5, "failing": 2 }
    },
    "by_category": {
      "naming": { "score": 85.0, "passing": 17, "failing": 3 },
      "lineage": { "score": 70.0, "passing": 7, "failing": 3 },
      "pii": { "score": 80.0, "passing": 4, "failing": 1 },
      "documentation": { "score": 75.0, "passing": 6, "failing": 2 }
    },
    "computed_at": "2024-12-01T12:00:00Z"
  }
}
```

### 8.2 List Violations

```http
GET /api/v1/conformance/violations
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `severity` | string | critical, error, warning, info |
| `category` | string | naming, lineage, pii, documentation |
| `rule_set` | string | Filter by rule set |
| `status` | string | open, acknowledged, resolved |
| `capsule_urn` | string | Filter by capsule |
| `domain` | string | Filter by domain |

**Response:**
```json
{
  "data": [
    {
      "id": "...",
      "rule": {
        "rule_id": "LINEAGE_001",
        "name": "Gold sources Silver only",
        "category": "lineage",
        "rule_set": "medallion"
      },
      "severity": "error",
      "status": "open",
      "subject": {
        "type": "capsule",
        "urn": "urn:dcs:dbt:model:jaffle_shop.marts:fct_orders",
        "name": "fct_orders"
      },
      "message": "Gold layer model 'fct_orders' sources directly from Bronze layer",
      "details": {
        "bronze_sources": ["raw_orders", "raw_order_items"],
        "expected_pattern": "Gold should only source from Silver/Intermediate"
      },
      "remediation": "Add staging models between raw sources and fct_orders",
      "detected_at": "2024-12-01T11:00:00Z"
    }
  ],
  "pagination": {
    "total": 10,
    "limit": 50,
    "has_more": false
  }
}
```

### 8.3 Run Conformance Check

```http
POST /api/v1/conformance/evaluate
```

**Request Body:**
```json
{
  "rule_sets": ["medallion", "pii_compliance"],
  "categories": ["naming", "lineage"],
  "scope": {
    "type": "domain",
    "value": "customer"
  },
  "include_passing": false
}
```

**Response:**
```json
{
  "data": {
    "job_id": "eval_abc123",
    "status": "completed",
    "started_at": "2024-12-01T12:00:00Z",
    "completed_at": "2024-12-01T12:00:05Z",
    "results": {
      "score": 78.5,
      "total_evaluated": 156,
      "violations_found": 12,
      "new_violations": 3,
      "resolved_violations": 1
    }
  }
}
```

### 8.4 List Rules

```http
GET /api/v1/conformance/rules
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `rule_set` | string | Filter by rule set |
| `category` | string | Filter by category |
| `severity` | string | Filter by severity |
| `enabled` | boolean | Filter by enabled status |

**Response:**
```json
{
  "data": [
    {
      "id": "...",
      "rule_id": "NAMING_001",
      "name": "Model naming convention",
      "description": "Models must follow {layer}_{domain}_{entity} pattern",
      "severity": "warning",
      "category": "naming",
      "rule_set": "medallion",
      "scope": "capsule",
      "enabled": true,
      "definition": {
        "type": "pattern",
        "pattern": "^(raw|stg|int|dim|fct|rpt)_[a-z]+_[a-z_]+$",
        "apply_to": "name"
      },
      "created_at": "2024-12-01T10:00:00Z"
    }
  ]
}
```

### 8.5 Get Rule Details

```http
GET /api/v1/conformance/rules/{rule_id}
```

**Response:**
```json
{
  "data": {
    "id": "...",
    "rule_id": "LINEAGE_001",
    "name": "Gold sources Silver only",
    "description": "Gold/Mart layer models should only source from Silver/Intermediate layers",
    "severity": "error",
    "category": "lineage",
    "rule_set": "medallion",
    "scope": "capsule",
    "enabled": true,
    "definition": {
      "type": "graph",
      "condition": {
        "if": { "layer": ["gold", "marts"] },
        "then": {
          "upstream_layers": ["silver", "intermediate", "staging"]
        }
      }
    },
    "remediation_guidance": "Add staging/intermediate models between raw sources and Gold layer models. This ensures data quality checks and transformations occur before data reaches the consumption layer.",
    "examples": {
      "passing": "fct_orders sources from stg_orders, int_order_enriched",
      "failing": "fct_orders sources from raw_orders"
    },
    "violation_count": 3,
    "created_at": "2024-12-01T10:00:00Z"
  }
}
```

---

## 9. Ingestion Endpoints

### 9.1 Ingest dbt Artifacts

```http
POST /api/v1/ingest/dbt
```

**Request Body (multipart/form-data):**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `manifest` | file | Yes | manifest.json file |
| `catalog` | file | No | catalog.json file |
| `project_name` | string | No | Override project name |
| `run_conformance` | boolean | No | Run conformance check after ingestion |

**Alternative (JSON body with paths):**
```json
{
  "manifest_path": "/path/to/manifest.json",
  "catalog_path": "/path/to/catalog.json",
  "project_name": "jaffle_shop",
  "run_conformance": true
}
```

**Response:**
```json
{
  "data": {
    "job_id": "ingest_abc123",
    "status": "completed",
    "source_type": "dbt",
    "source_name": "jaffle_shop",
    "started_at": "2024-12-01T12:00:00Z",
    "completed_at": "2024-12-01T12:00:15Z",
    "stats": {
      "capsules_created": 45,
      "capsules_updated": 12,
      "capsules_unchanged": 23,
      "columns_processed": 234,
      "edges_created": 67,
      "pii_columns_detected": 15,
      "domains_created": 3,
      "tags_created": 8
    },
    "conformance": {
      "ran": true,
      "score": 78.5,
      "violations_found": 12
    }
  }
}
```

### 9.2 Get Ingestion Status

```http
GET /api/v1/ingest/status/{job_id}
```

**Response:**
```json
{
  "data": {
    "job_id": "ingest_abc123",
    "status": "running",
    "progress": {
      "phase": "transforming",
      "percentage": 65,
      "current_step": "Processing columns",
      "items_processed": 156,
      "items_total": 240
    },
    "started_at": "2024-12-01T12:00:00Z",
    "elapsed_seconds": 8
  }
}
```

### 9.3 List Ingestion History

```http
GET /api/v1/ingest/history
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `source_type` | string | Filter by source type |
| `status` | string | Filter by status |
| `limit` | integer | Page size |

**Response:**
```json
{
  "data": [
    {
      "job_id": "ingest_abc123",
      "source_type": "dbt",
      "source_name": "jaffle_shop",
      "status": "completed",
      "started_at": "2024-12-01T12:00:00Z",
      "completed_at": "2024-12-01T12:00:15Z",
      "stats": {
        "capsules_processed": 80,
        "columns_processed": 234
      }
    }
  ]
}
```

---

## 10. Domain & Tag Endpoints

### 10.1 List Domains

```http
GET /api/v1/domains
```

**Response:**
```json
{
  "data": [
    {
      "id": "...",
      "name": "customer",
      "description": "Customer domain - all customer-related data assets",
      "owner": {
        "name": "Customer Data Team"
      },
      "capsule_count": 23,
      "pii_capsule_count": 8,
      "conformance_score": 82.5,
      "created_at": "2024-12-01T10:00:00Z"
    }
  ]
}
```

### 10.2 Get Domain Details

```http
GET /api/v1/domains/{name}
```

### 10.3 List Domain Capsules

```http
GET /api/v1/domains/{name}/capsules
```

### 10.4 List Tags

```http
GET /api/v1/tags
```

### 10.5 Get Tag Details

```http
GET /api/v1/tags/{name}
```

---

## 11. Error Handling

### 11.1 Error Response Format

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "status": 400,
    "details": {
      "field": "additional context"
    }
  },
  "meta": {
    "request_id": "req_abc123",
    "timestamp": "2024-12-01T12:00:00Z"
  }
}
```

### 11.2 Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `UNAUTHORIZED` | 401 | Invalid or missing API key |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource not found |
| `VALIDATION_ERROR` | 400 | Invalid request parameters |
| `CONFLICT` | 409 | Resource conflict (e.g., duplicate) |
| `INTERNAL_ERROR` | 500 | Unexpected server error |
| `SERVICE_UNAVAILABLE` | 503 | Service temporarily unavailable |
| `INGESTION_FAILED` | 422 | Ingestion processing failed |
| `INVALID_URN` | 400 | Malformed URN format |
| `DEPTH_EXCEEDED` | 400 | Lineage depth exceeds maximum |

### 11.3 Validation Errors

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "status": 400,
    "details": {
      "errors": [
        {
          "field": "depth",
          "message": "Value must be between 1 and 10",
          "value": 15
        },
        {
          "field": "direction",
          "message": "Must be one of: upstream, downstream, both",
          "value": "invalid"
        }
      ]
    }
  }
}
```

---

## Appendix: OpenAPI Schema

The full OpenAPI 3.0 specification is auto-generated by FastAPI and available at:

```
GET /api/v1/openapi.json
GET /api/v1/docs        # Swagger UI
GET /api/v1/redoc       # ReDoc
```

---

*End of API Specification Document*
