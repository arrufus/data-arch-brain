# Data Capsule Server - System Architecture

**Version**: 1.0
**Status**: Draft
**Last Updated**: December 2024

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Design Principles](#2-design-principles)
3. [System Context](#3-system-context)
4. [Component Architecture](#4-component-architecture)
5. [Data Flow](#5-data-flow)
6. [Technology Stack](#6-technology-stack)
7. [Deployment Architecture](#7-deployment-architecture)
8. [Security Architecture](#8-security-architecture)
9. [Integration Patterns](#9-integration-patterns)

---

## 1. Architecture Overview

### 1.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CLIENTS                                         │
├─────────────────────────────────────────────────────────────────────────────┤
│    ┌─────────┐         ┌─────────┐         ┌─────────────┐                 │
│    │   CLI   │         │REST API │         │ Web UI      │                 │
│    │  (dab)  │         │ Clients │         │ (Future)    │                 │
│    └────┬────┘         └────┬────┘         └──────┬──────┘                 │
└─────────┼───────────────────┼────────────────────┼──────────────────────────┘
          │                   │                    │
          ▼                   ▼                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            API LAYER                                         │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                         FastAPI Application                           │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐     │  │
│  │  │  Ingest    │  │  Query     │  │ Compliance │  │Conformance │     │  │
│  │  │  Router    │  │  Router    │  │  Router    │  │  Router    │     │  │
│  │  └────────────┘  └────────────┘  └────────────┘  └────────────┘     │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
          │                   │                    │
          ▼                   ▼                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          SERVICE LAYER                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │  Ingestion   │  │    Graph     │  │     PII      │  │ Conformance  │   │
│  │   Service    │  │   Service    │  │   Service    │  │   Service    │   │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘   │
│         │                 │                 │                 │            │
│  ┌──────▼───────┐        │                 │                 │            │
│  │   Parsers    │        │                 │                 │            │
│  │  ┌────────┐  │        │                 │                 │            │
│  │  │  dbt   │  │        │                 │                 │            │
│  │  ├────────┤  │        │                 │                 │            │
│  │  │Snowflk │  │        │                 │                 │            │
│  │  ├────────┤  │        │                 │                 │            │
│  │  │  BQ    │  │        │                 │                 │            │
│  │  └────────┘  │        │                 │                 │            │
│  └──────────────┘        │                 │                 │            │
└─────────────────────────────────────────────────────────────────────────────┘
          │                   │                    │                │
          ▼                   ▼                    ▼                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        REPOSITORY LAYER                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │   Capsule    │  │    Column    │  │   Lineage    │  │    Rule      │   │
│  │ Repository   │  │ Repository   │  │ Repository   │  │ Repository   │   │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
          │                   │                    │                │
          ▼                   ▼                    ▼                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DATA LAYER                                           │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │                      PostgreSQL Database                            │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                 │    │
│  │  │   Nodes     │  │    Edges    │  │  Metadata   │                 │    │
│  │  │   Tables    │  │   Tables    │  │   Tables    │                 │    │
│  │  └─────────────┘  └─────────────┘  └─────────────┘                 │    │
│  └────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Architecture Style

**Layered Architecture** with clear separation of concerns:

| Layer | Responsibility |
|-------|----------------|
| **API Layer** | HTTP handling, request/response, authentication |
| **Service Layer** | Business logic, orchestration, domain operations |
| **Repository Layer** | Data access abstraction, query building |
| **Data Layer** | Persistence, graph storage, indexes |

---

## 2. Design Principles

### 2.1 Core Principles

| Principle | Application |
|-----------|-------------|
| **Read-Only by Design** | No mutations to source systems; only analyze |
| **Graph-First** | Model everything as nodes and edges |
| **Source Agnostic** | Abstract parser interface for any metadata source |
| **Incremental Processing** | Support partial updates, not just full reloads |
| **Shared Infrastructure** | Reuse Easy Modeller components where sensible |

### 2.2 Design Decisions

| Decision | Rationale |
|----------|-----------|
| PostgreSQL over Neo4j | Shared with Easy Modeller; adequate for MVP scale; JSONB for flexibility |
| FastAPI | Shared with Easy Modeller; async support; auto OpenAPI |
| Python | Team expertise; rich data ecosystem; dbt native |
| File-based dbt ingestion | Simplest integration; no network dependencies |

---

## 3. System Context

### 3.1 Context Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         EXTERNAL SYSTEMS                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │
│  │     dbt     │  │  Snowflake  │  │  BigQuery   │  │ Databricks  │   │
│  │  (manifest) │  │  (future)   │  │  (future)   │  │  (future)   │   │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘   │
│         │                │                │                │           │
│         │    Metadata    │    Metadata    │    Metadata    │           │
│         │    Artifacts   │    via API     │    via API     │           │
│         │                │                │                │           │
└─────────┼────────────────┼────────────────┼────────────────┼───────────┘
          │                │                │                │
          ▼                ▼                ▼                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                          │
│                      DATA ARCHITECTURE BRAIN                             │
│                                                                          │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │                     Core Capabilities                            │   │
│   │  • Metadata Ingestion & Normalization                           │   │
│   │  • Graph Construction & Querying                                │   │
│   │  • PII Lineage Tracking                                         │   │
│   │  • Architecture Conformance Checking                            │   │
│   └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
          │                │                │
          ▼                ▼                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                            CONSUMERS                                     │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │
│  │    Data     │  │  Compliance │  │  Platform   │  │    Data     │   │
│  │  Architects │  │  Officers   │  │  Engineers  │  │  Engineers  │   │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3.2 External Interfaces

| Interface | Type | Direction | Description |
|-----------|------|-----------|-------------|
| dbt Artifacts | File (JSON/YAML) | Inbound | manifest.json, catalog.json, schema.yml |
| Snowflake (future) | SQL/API | Inbound | INFORMATION_SCHEMA, ACCESS_HISTORY |
| BigQuery (future) | API | Inbound | INFORMATION_SCHEMA, Data Catalog API |
| REST API | HTTP/JSON | Outbound | Query results, reports |
| CLI | Terminal | Outbound | Interactive commands, scripts |

---

## 4. Component Architecture

### 4.1 Component Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              API LAYER                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐             │
│  │ IngestRouter    │  │ CapsuleRouter   │  │ ColumnRouter    │             │
│  │ POST /ingest/*  │  │ GET /capsules/* │  │ GET /columns/*  │             │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘             │
│           │                    │                    │                       │
│  ┌────────┴────────┐  ┌────────┴────────┐  ┌────────┴────────┐             │
│  │ComplianceRouter │  │ConformanceRouter│  │ ReportRouter    │             │
│  │GET /compliance/*│  │GET /conformance*│  │ GET /reports/*  │             │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘             │
│                                                                              │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            SERVICE LAYER                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │                        IngestionService                                │ │
│  │  • Orchestrates parsing and transformation                            │ │
│  │  • Manages ingestion jobs                                             │ │
│  │  • Handles incremental updates                                        │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│           │                                                                  │
│           ▼                                                                  │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │                          Parser Registry                               │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                   │ │
│  │  │ DbtParser   │  │SnowflakePrsr│  │BigQueryPrsr │                   │ │
│  │  │ (MVP)       │  │ (Future)    │  │ (Future)    │                   │ │
│  │  └─────────────┘  └─────────────┘  └─────────────┘                   │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │                         GraphService                                   │ │
│  │  • Node CRUD operations                                               │ │
│  │  • Edge management                                                    │ │
│  │  • Lineage traversal (BFS/DFS)                                       │ │
│  │  • Graph queries                                                      │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │                          PIIService                                    │ │
│  │  • PII detection (tags + patterns)                                    │ │
│  │  • PII lineage tracing                                                │ │
│  │  • Exposure detection                                                 │ │
│  │  • Inventory generation                                               │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │                      ConformanceService                                │ │
│  │  • Rule loading and parsing                                           │ │
│  │  • Rule execution engine                                              │ │
│  │  • Violation detection                                                │ │
│  │  • Score calculation                                                  │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │                        ReportService                                   │ │
│  │  • Report generation (HTML, JSON, CSV)                                │ │
│  │  • Template rendering                                                 │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          REPOSITORY LAYER                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐             │
│  │CapsuleRepository│  │ColumnRepository │  │ EdgeRepository  │             │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘             │
│                                                                              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐             │
│  │ DomainRepository│  │  TagRepository  │  │  RuleRepository │             │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘             │
│                                                                              │
│  ┌─────────────────┐  ┌─────────────────┐                                  │
│  │IngestionRepository│ │ViolationRepository│                                │
│  └─────────────────┘  └─────────────────┘                                  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Component Descriptions

#### 4.2.1 API Layer Components

| Component | Responsibility |
|-----------|----------------|
| **IngestRouter** | Handle ingestion requests, validate inputs, trigger jobs |
| **CapsuleRouter** | CRUD for Data Capsules, lineage queries |
| **ColumnRouter** | Column queries, column-level lineage |
| **ComplianceRouter** | PII inventory, exposure reports |
| **ConformanceRouter** | Rule management, violation queries, scoring |
| **ReportRouter** | Report generation endpoints |

#### 4.2.2 Service Layer Components

| Component | Responsibility |
|-----------|----------------|
| **IngestionService** | Orchestrate end-to-end ingestion pipeline |
| **Parser Registry** | Manage and dispatch to appropriate parsers |
| **DbtParser** | Parse dbt manifest.json, catalog.json, schema.yml |
| **GraphService** | Graph operations, traversals, queries |
| **PIIService** | PII detection, tracing, exposure analysis |
| **ConformanceService** | Rule engine, violation detection, scoring |
| **ReportService** | Generate formatted reports |

#### 4.2.3 Repository Layer Components

| Component | Responsibility |
|-----------|----------------|
| **CapsuleRepository** | Capsule CRUD, search, filtering |
| **ColumnRepository** | Column CRUD, semantic type queries |
| **EdgeRepository** | Relationship management, traversal support |
| **DomainRepository** | Domain CRUD |
| **TagRepository** | Tag/classification management |
| **RuleRepository** | Rule storage and retrieval |
| **ViolationRepository** | Violation storage and queries |
| **IngestionRepository** | Ingestion job tracking |

---

## 5. Data Flow

### 5.1 Ingestion Flow

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         INGESTION PIPELINE                                │
└──────────────────────────────────────────────────────────────────────────┘

  ┌─────────────┐
  │ dbt Project │
  │  manifest   │
  │  catalog    │
  └──────┬──────┘
         │
         ▼
  ┌─────────────────────────────────────────────────────────────────────┐
  │ 1. PARSE                                                             │
  │    ┌─────────────────────────────────────────────────────────────┐  │
  │    │ DbtParser                                                    │  │
  │    │  • Read manifest.json → extract models, sources, deps       │  │
  │    │  • Read catalog.json → extract columns, types, stats        │  │
  │    │  • Read schema.yml → extract descriptions, meta, tests      │  │
  │    │  • Output: List[RawDbtModel], List[RawDbtSource]            │  │
  │    └─────────────────────────────────────────────────────────────┘  │
  └──────────────────────────────────┬──────────────────────────────────┘
                                     │
                                     ▼
  ┌─────────────────────────────────────────────────────────────────────┐
  │ 2. TRANSFORM                                                         │
  │    ┌─────────────────────────────────────────────────────────────┐  │
  │    │ CapsuleTransformer                                           │  │
  │    │  • Convert RawDbtModel → DataCapsule                        │  │
  │    │  • Generate URNs                                             │  │
  │    │  • Extract columns → Column nodes                           │  │
  │    │  • Infer layer from path/tags                               │  │
  │    │  • Detect PII from meta/patterns                            │  │
  │    │  • Build lineage edges from depends_on                      │  │
  │    │  • Output: List[DataCapsule], List[Column], List[Edge]      │  │
  │    └─────────────────────────────────────────────────────────────┘  │
  └──────────────────────────────────┬──────────────────────────────────┘
                                     │
                                     ▼
  ┌─────────────────────────────────────────────────────────────────────┐
  │ 3. LOAD                                                              │
  │    ┌─────────────────────────────────────────────────────────────┐  │
  │    │ GraphLoader                                                  │  │
  │    │  • Upsert DataCapsule nodes (merge on URN)                  │  │
  │    │  • Upsert Column nodes (merge on URN)                       │  │
  │    │  • Upsert/replace edges                                      │  │
  │    │  • Create Domain nodes if new                               │  │
  │    │  • Create Tag nodes if new                                  │  │
  │    │  • Record ingestion metadata                                │  │
  │    └─────────────────────────────────────────────────────────────┘  │
  └──────────────────────────────────┬──────────────────────────────────┘
                                     │
                                     ▼
  ┌─────────────────────────────────────────────────────────────────────┐
  │ 4. POST-PROCESS                                                      │
  │    ┌─────────────────────────────────────────────────────────────┐  │
  │    │ ConformanceChecker (optional, async)                         │  │
  │    │  • Run all applicable rules                                  │  │
  │    │  • Store violations                                          │  │
  │    │  • Calculate scores                                          │  │
  │    └─────────────────────────────────────────────────────────────┘  │
  └─────────────────────────────────────────────────────────────────────┘
```

### 5.2 Query Flow (Lineage)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         LINEAGE QUERY FLOW                               │
└─────────────────────────────────────────────────────────────────────────┘

  User Request:
  GET /api/v1/capsules/urn:dcs:dbt:model:marts.dim_customer/lineage
      ?direction=both&depth=3

         │
         ▼
  ┌─────────────────────────────────────────────────────────────────────┐
  │ 1. API LAYER (CapsuleRouter)                                         │
  │    • Parse URN parameter                                             │
  │    • Validate query params (direction, depth)                        │
  │    • Call GraphService.get_lineage()                                 │
  └──────────────────────────────────┬──────────────────────────────────┘
                                     │
                                     ▼
  ┌─────────────────────────────────────────────────────────────────────┐
  │ 2. SERVICE LAYER (GraphService)                                      │
  │    • Resolve URN to internal node ID                                 │
  │    • Execute BFS/DFS traversal:                                      │
  │      - If upstream: follow FLOWS_TO edges backwards                  │
  │      - If downstream: follow FLOWS_TO edges forwards                 │
  │      - If both: traverse both directions                             │
  │    • Respect depth limit                                             │
  │    • Collect all nodes and edges in path                             │
  └──────────────────────────────────┬──────────────────────────────────┘
                                     │
                                     ▼
  ┌─────────────────────────────────────────────────────────────────────┐
  │ 3. REPOSITORY LAYER (EdgeRepository, CapsuleRepository)              │
  │    • Recursive CTE query for traversal                               │
  │    • Fetch node details for all traversed nodes                      │
  │    • Return structured result                                        │
  └──────────────────────────────────┬──────────────────────────────────┘
                                     │
                                     ▼
  ┌─────────────────────────────────────────────────────────────────────┐
  │ 4. RESPONSE                                                          │
  │    {                                                                  │
  │      "root": { "urn": "...", "name": "dim_customer", ... },         │
  │      "upstream": [                                                   │
  │        { "urn": "...", "name": "stg_customer", "depth": 1 },        │
  │        { "urn": "...", "name": "raw_customer", "depth": 2 }         │
  │      ],                                                              │
  │      "downstream": [                                                 │
  │        { "urn": "...", "name": "rpt_customer_metrics", "depth": 1 } │
  │      ],                                                              │
  │      "edges": [ ... ]                                                │
  │    }                                                                  │
  └─────────────────────────────────────────────────────────────────────┘
```

### 5.3 Conformance Check Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      CONFORMANCE CHECK FLOW                              │
└─────────────────────────────────────────────────────────────────────────┘

  User Request:
  POST /api/v1/conformance/evaluate
       { "rule_sets": ["medallion", "pii"], "scope": "all" }

         │
         ▼
  ┌─────────────────────────────────────────────────────────────────────┐
  │ 1. LOAD RULES                                                        │
  │    • Load rule definitions from DB/YAML                              │
  │    • Filter by requested rule_sets                                   │
  │    • Parse rule conditions                                           │
  └──────────────────────────────────┬──────────────────────────────────┘
                                     │
                                     ▼
  ┌─────────────────────────────────────────────────────────────────────┐
  │ 2. SCOPE RESOLUTION                                                  │
  │    • Determine which nodes to evaluate                               │
  │    • For each rule, identify applicable scope (model, column, etc.)  │
  └──────────────────────────────────┬──────────────────────────────────┘
                                     │
                                     ▼
  ┌─────────────────────────────────────────────────────────────────────┐
  │ 3. RULE EXECUTION                                                    │
  │    For each rule:                                                    │
  │    ┌───────────────────────────────────────────────────────────┐    │
  │    │ Rule Type: PATTERN (regex)                                 │    │
  │    │  • Apply regex to node property (e.g., name)              │    │
  │    │  • Record pass/fail for each node                         │    │
  │    └───────────────────────────────────────────────────────────┘    │
  │    ┌───────────────────────────────────────────────────────────┐    │
  │    │ Rule Type: GRAPH (lineage condition)                       │    │
  │    │  • Query graph relationships                               │    │
  │    │  • Evaluate condition (e.g., upstream layer check)        │    │
  │    │  • Record pass/fail for each node                         │    │
  │    └───────────────────────────────────────────────────────────┘    │
  │    ┌───────────────────────────────────────────────────────────┐    │
  │    │ Rule Type: PROPERTY (attribute check)                      │    │
  │    │  • Check node property exists/matches                     │    │
  │    │  • Record pass/fail for each node                         │    │
  │    └───────────────────────────────────────────────────────────┘    │
  └──────────────────────────────────┬──────────────────────────────────┘
                                     │
                                     ▼
  ┌─────────────────────────────────────────────────────────────────────┐
  │ 4. AGGREGATE RESULTS                                                 │
  │    • Calculate pass/fail counts per rule                             │
  │    • Calculate weighted conformance score                            │
  │    • Store violations with details                                   │
  │    • Return summary + violations                                     │
  └─────────────────────────────────────────────────────────────────────┘
```

---

## 6. Technology Stack

### 6.1 Core Technologies

| Layer | Technology | Version | Rationale |
|-------|------------|---------|-----------|
| **Language** | Python | 3.11+ | Team expertise, dbt ecosystem |
| **API Framework** | FastAPI | 0.100+ | Async, OpenAPI, shared with Easy Modeller |
| **Database** | PostgreSQL | 15+ | JSONB support, shared with Easy Modeller |
| **ORM** | SQLAlchemy | 2.0+ | Async support, migrations |
| **Migrations** | Alembic | 1.12+ | Database versioning |
| **Validation** | Pydantic | 2.0+ | Request/response models |
| **CLI** | Typer | 0.9+ | Modern CLI framework |
| **Testing** | pytest | 7.0+ | Async support, fixtures |

### 6.2 Supporting Libraries

| Purpose | Library | Notes |
|---------|---------|-------|
| HTTP Client | httpx | Async HTTP for future integrations |
| YAML Parsing | PyYAML, ruamel.yaml | Rule definitions |
| JSON Parsing | orjson | Fast JSON (dbt artifacts) |
| Template Engine | Jinja2 | Report generation |
| Logging | structlog | Structured JSON logs |
| Config | pydantic-settings | Environment configuration |

### 6.3 Development Tools

| Purpose | Tool |
|---------|------|
| Dependency Management | uv or poetry |
| Linting | ruff |
| Type Checking | mypy |
| Formatting | black, isort |
| Pre-commit | pre-commit hooks |
| Documentation | mkdocs |

---

## 7. Deployment Architecture

### 7.1 Docker Compose (MVP)

```yaml
# docker-compose.yml (conceptual)
version: '3.8'

services:
  # Data Capsule Server API
  dcs-api:
    build: ./backend
    ports:
      - "8001:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/dab
      - LOG_LEVEL=INFO
    depends_on:
      - db
    volumes:
      - ./data/ingested:/app/data  # For file-based ingestion

  # Shared PostgreSQL (with Easy Modeller)
  db:
    image: postgres:15
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
      - POSTGRES_DB=dab
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

volumes:
  postgres_data:
```

### 7.2 Container Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         DOCKER ENVIRONMENT                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                        docker network: dab-network               │   │
│  │                                                                   │   │
│  │  ┌─────────────────┐              ┌─────────────────┐           │   │
│  │  │   dcs-api       │              │   postgres      │           │   │
│  │  │                 │              │                 │           │   │
│  │  │  FastAPI App    │─────────────▶│  PostgreSQL 15  │           │   │
│  │  │  Port: 8000     │              │  Port: 5432     │           │   │
│  │  │                 │              │                 │           │   │
│  │  │  /app/data      │              │  /var/lib/pg    │           │   │
│  │  │  (mounted vol)  │              │  (named vol)    │           │   │
│  │  └─────────────────┘              └─────────────────┘           │   │
│  │           │                                │                      │   │
│  └───────────┼────────────────────────────────┼──────────────────────┘   │
│              │                                │                          │
│         Port 8001                        Port 5432                       │
│              │                                │                          │
└──────────────┼────────────────────────────────┼──────────────────────────┘
               │                                │
               ▼                                ▼
        ┌──────────────┐                ┌──────────────┐
        │   CLI (dab)  │                │  DB Clients  │
        │   curl/http  │                │  (optional)  │
        └──────────────┘                └──────────────┘
```

### 7.3 Shared Infrastructure with Easy Modeller

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    SHARED INFRASTRUCTURE                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                     PostgreSQL Instance                           │  │
│  │  ┌─────────────────────┐    ┌─────────────────────┐             │  │
│  │  │  easy_modeller      │    │  data_arch_brain    │             │  │
│  │  │  (schema)           │    │  (schema)           │             │  │
│  │  │                     │    │                     │             │  │
│  │  │  • projects         │    │  • capsules         │             │  │
│  │  │  • models           │    │  • columns          │             │  │
│  │  │  • entities         │    │  • edges            │             │  │
│  │  │  • attributes       │    │  • domains          │             │  │
│  │  │  • ...              │    │  • rules            │             │  │
│  │  │                     │    │  • violations       │             │  │
│  │  └─────────────────────┘    └─────────────────────┘             │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                     Shared Components                             │  │
│  │  • Database connection pooling                                    │  │
│  │  • Authentication (API keys)                                      │  │
│  │  • Logging infrastructure                                         │  │
│  │  • Health check patterns                                          │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 8. Security Architecture

### 8.1 Security Model

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         SECURITY LAYERS                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ 1. NETWORK SECURITY                                              │   │
│  │    • Docker network isolation                                    │   │
│  │    • No external DB access (internal network only)              │   │
│  │    • Future: TLS termination at load balancer                   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ 2. AUTHENTICATION                                                │   │
│  │    • API Key authentication (MVP)                                │   │
│  │    • X-API-Key header                                            │   │
│  │    • Future: OAuth2/OIDC integration                            │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ 3. AUTHORIZATION                                                 │   │
│  │    • Read-only by design (no mutations to source systems)       │   │
│  │    • All authenticated users can read all data (MVP)            │   │
│  │    • Future: Role-based access (admin, viewer)                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ 4. DATA SECURITY                                                 │   │
│  │    • No source credentials stored                                │   │
│  │    • Metadata only (no actual data)                             │   │
│  │    • PII indicators stored, not PII values                      │   │
│  │    • Encrypted at rest (PostgreSQL)                             │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 8.2 Authentication Flow (MVP)

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Client    │     │   API       │     │   Service   │
│   (CLI)     │     │   Layer     │     │   Layer     │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │
       │  Request          │                   │
       │  X-API-Key: xxx   │                   │
       │──────────────────▶│                   │
       │                   │                   │
       │                   │  Validate Key     │
       │                   │  (middleware)     │
       │                   │                   │
       │                   │  If valid:        │
       │                   │──────────────────▶│
       │                   │                   │
       │                   │  Response         │
       │                   │◀──────────────────│
       │  Response         │                   │
       │◀──────────────────│                   │
       │                   │                   │
```

---

## 9. Integration Patterns

### 9.1 Parser Interface

All metadata parsers implement a common interface:

```python
from abc import ABC, abstractmethod
from typing import List
from dataclasses import dataclass

@dataclass
class ParseResult:
    capsules: List[DataCapsule]
    columns: List[Column]
    edges: List[Edge]
    domains: List[Domain]
    tags: List[Tag]
    errors: List[ParseError]

class MetadataParser(ABC):
    """Abstract base class for all metadata parsers."""

    @property
    @abstractmethod
    def source_type(self) -> str:
        """Return the source type identifier (e.g., 'dbt', 'snowflake')."""
        pass

    @abstractmethod
    async def parse(self, config: ParserConfig) -> ParseResult:
        """Parse metadata from the source and return normalized results."""
        pass

    @abstractmethod
    async def validate_config(self, config: ParserConfig) -> List[str]:
        """Validate parser configuration, return list of errors."""
        pass
```

### 9.2 dbt Parser Configuration

```python
@dataclass
class DbtParserConfig(ParserConfig):
    manifest_path: Path
    catalog_path: Optional[Path] = None
    project_name: str = "default"

    # Layer inference settings
    layer_patterns: Dict[str, str] = field(default_factory=lambda: {
        "bronze": r"^(raw|source)_",
        "silver": r"^(stg|staging|int|intermediate)_",
        "gold": r"^(dim|fct|fact|mart|rpt|report)_"
    })

    # PII detection patterns
    pii_column_patterns: List[str] = field(default_factory=lambda: [
        r"(?i)(email|e_mail)",
        r"(?i)(ssn|social_security)",
        r"(?i)(phone|mobile|cell)",
        r"(?i)(address|street|city|zip|postal)",
        r"(?i)(first_name|last_name|full_name)",
        r"(?i)(date_of_birth|dob|birth_date)",
        r"(?i)(credit_card|card_number)",
        r"(?i)(password|secret|token)"
    ])
```

### 9.3 Future Integration Points

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      INTEGRATION ARCHITECTURE                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                     Parser Registry                              │   │
│  │                                                                   │   │
│  │  register("dbt", DbtParser)                                      │   │
│  │  register("snowflake", SnowflakeParser)  # Future                │   │
│  │  register("bigquery", BigQueryParser)    # Future                │   │
│  │  register("databricks", DatabricksParser) # Future               │   │
│  │                                                                   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                     Ingestion Service                            │   │
│  │                                                                   │
│  │  async def ingest(source_type: str, config: ParserConfig):      │   │
│  │      parser = registry.get(source_type)                         │   │
│  │      result = await parser.parse(config)                        │   │
│  │      await graph_service.load(result)                           │   │
│  │      return ingestion_result                                     │   │
│  │                                                                   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Next Documents

The following design documents complement this architecture:

1. **Database Schema** (`database_schema.md`) - Detailed table definitions
2. **API Specification** (`api_specification.md`) - OpenAPI spec and examples
3. **Component Design** (`component_design.md`) - Detailed component specs
4. **Conformance Rules** (`conformance_rules.md`) - Rule engine design

---

*End of System Architecture Document*
