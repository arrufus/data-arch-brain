# Data Architecture Brain - Product Specification

**Version**: 1.0
**Status**: Draft
**Last Updated**: December 2024
**Author**: Data Architecture Team

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Product Vision & Mission](#2-product-vision--mission)
3. [Problem Statement](#3-problem-statement)
4. [User Personas](#4-user-personas)
5. [Core Concepts](#5-core-concepts)
6. [Feature Specification](#6-feature-specification)
7. [Use Cases](#7-use-cases)
8. [Non-Functional Requirements](#8-non-functional-requirements)
9. [Integration Strategy](#9-integration-strategy)
10. [Success Metrics](#10-success-metrics)
11. [Roadmap](#11-roadmap)
12. [Appendices](#appendices)

---

## 1. Executive Summary

### 1.1 Product Overview

**Data Architecture Brain** is a read-only architecture intelligence platform that ingests metadata and lineage from diverse data infrastructure sources, constructs a unified graph representation of the data landscape, and provides intelligent insights for data governance, architecture conformance, and sensitive data tracking.

### 1.2 Key Value Propositions

| Value | Description |
|-------|-------------|
| **Unified Visibility** | Single pane of glass across all data assets, regardless of source system |
| **PII/Sensitive Data Tracking** | Trace sensitive data elements through entire transformation pipelines |
| **Architecture Conformance** | Automated detection of anti-patterns against defined standards |
| **Redundancy Detection** | Identify duplicate and overlapping data assets for consolidation |
| **Impact Analysis** | Understand downstream effects of proposed changes |

### 1.3 Target Users

- Data Architects
- Data Governance Teams
- Platform Engineers
- Data Product Owners
- Compliance Officers

### 1.4 Initial Scope (MVP)

- **Metadata Source**: dbt (manifest.json, catalog.json)
- **Priority Features**: PII lineage tracking, Architecture conformance checking
- **Environment**: Local Docker deployment
- **Interface**: REST API + CLI

---

## 2. Product Vision & Mission

### 2.1 Vision Statement

> "To be the intelligent layer that transforms fragmented metadata into actionable architecture insights, enabling organizations to understand, govern, and optimize their data landscape with confidence."

### 2.2 Mission Statement

> "Provide data teams with a unified, queryable graph of their data architecture that surfaces risks, redundancies, and non-conformance automatically—without requiring manual documentation or tribal knowledge."

### 2.3 Strategic Alignment

Data Architecture Brain complements **Easy Modeller** (AI-assisted data modelling studio) by providing:

| Easy Modeller | Data Architecture Brain |
|---------------|------------------------|
| Design-time modelling | Runtime architecture analysis |
| Forward engineering | Reverse engineering + validation |
| Create new models | Analyze existing landscape |
| Prescriptive (how it should be) | Descriptive (how it is) |

Together, they form a complete data architecture lifecycle: **Design → Implement → Analyze → Improve**.

---

## 3. Problem Statement

### 3.1 Current Pain Points

#### 3.1.1 Fragmented Metadata
Organizations use multiple tools (dbt, Snowflake, BigQuery, Databricks, Airflow, etc.), each with its own metadata store. There is no unified view of:
- What data assets exist
- How they relate to each other
- How data flows between systems

#### 3.1.2 Hidden PII/Sensitive Data
Sensitive data (PII, PCI, PHI) is:
- Tagged inconsistently across systems
- Propagated through transformations without tracking
- Exposed in downstream systems unknowingly
- Difficult to trace for compliance audits

#### 3.1.3 Architecture Drift
Organizations define architecture standards (Medallion, Data Vault, naming conventions) but:
- Enforcement is manual and inconsistent
- Anti-patterns accumulate over time
- Technical debt becomes invisible
- New team members repeat past mistakes

#### 3.1.4 Redundant Data Assets
Without visibility, teams:
- Create duplicate datasets unknowingly
- Maintain multiple sources of truth
- Waste compute/storage on redundant pipelines
- Make decisions on inconsistent data

### 3.2 Impact of These Problems

| Problem | Business Impact |
|---------|-----------------|
| Fragmented metadata | Weeks spent on impact analysis; failed migrations |
| Hidden PII | Regulatory fines (GDPR: up to 4% global revenue) |
| Architecture drift | Exponential technical debt; system brittleness |
| Redundancy | 20-40% wasted cloud spend; data quality issues |

---

## 4. User Personas

### 4.1 Primary Personas

#### 4.1.1 Dana - Data Architect

| Attribute | Description |
|-----------|-------------|
| **Role** | Lead Data Architect |
| **Experience** | 10+ years in data engineering/architecture |
| **Goals** | Ensure architecture standards are followed; reduce technical debt |
| **Pain Points** | Spends 40% of time on manual audits; can't enforce standards at scale |
| **Success Criteria** | Architecture conformance > 90%; audit time reduced by 75% |

**Key Jobs to Be Done:**
- Review new data models for conformance before approval
- Generate architecture conformance reports for leadership
- Identify anti-patterns and prioritize remediation
- Define and update architecture standards/rules

#### 4.1.2 Priya - Privacy/Compliance Officer

| Attribute | Description |
|-----------|-------------|
| **Role** | Data Privacy Manager |
| **Experience** | 5+ years in data governance/compliance |
| **Goals** | Ensure PII is properly tracked, protected, and auditable |
| **Pain Points** | No single source of truth for PII locations; audit prep takes weeks |
| **Success Criteria** | Complete PII inventory; audit prep < 1 day |

**Key Jobs to Be Done:**
- Generate PII inventory reports on demand
- Trace PII propagation through transformation layers
- Validate that PII is masked/encrypted where required
- Respond to data subject access requests (DSARs)

#### 4.1.3 Marcus - Platform Engineer

| Attribute | Description |
|-----------|-------------|
| **Role** | Senior Data Platform Engineer |
| **Experience** | 7+ years in data infrastructure |
| **Goals** | Maintain healthy, efficient data platform; enable self-service |
| **Pain Points** | Blind spots in data flows; surprises during migrations |
| **Success Criteria** | Zero surprise breaking changes; accurate impact analysis |

**Key Jobs to Be Done:**
- Perform impact analysis before infrastructure changes
- Identify unused/orphaned data assets for cleanup
- Understand dependencies between systems
- Plan migrations with confidence

### 4.2 Secondary Personas

#### 4.2.1 Taylor - Data Product Owner

| Attribute | Description |
|-----------|-------------|
| **Role** | Data Product Manager |
| **Goals** | Understand data product dependencies and consumers |
| **Key Jobs** | Map data product lineage; identify downstream consumers |

#### 4.2.2 Sam - Data Engineer

| Attribute | Description |
|-----------|-------------|
| **Role** | Senior Data Engineer |
| **Goals** | Build compliant pipelines; avoid duplicating existing work |
| **Key Jobs** | Check for existing similar datasets; validate new models |

---

## 5. Core Concepts

### 5.1 The Data Capsule Model

A **Data Capsule** is the atomic unit of the Data Architecture Brain graph. It represents a self-contained, domain-aligned data asset with full context.

#### 5.1.1 Data Capsule Definition

```
┌─────────────────────────────────────────────────────────────┐
│                      DATA CAPSULE                           │
├─────────────────────────────────────────────────────────────┤
│  Identity                                                   │
│  ├── Unique ID (URN)                                       │
│  ├── Name                                                   │
│  ├── Type (table, view, model, API, file, etc.)            │
│  └── Source System                                          │
├─────────────────────────────────────────────────────────────┤
│  Domain Context                                             │
│  ├── Domain (e.g., Customer, Order, Product)               │
│  ├── Subdomain                                              │
│  ├── Data Product (if applicable)                          │
│  └── Owner (team/individual)                                │
├─────────────────────────────────────────────────────────────┤
│  Architecture Context                                       │
│  ├── Layer (Bronze/Silver/Gold, Raw/Staging/Mart)          │
│  ├── Pattern (normalized, denormalized, SCD, snapshot)     │
│  ├── Update Frequency                                       │
│  └── Retention Policy                                       │
├─────────────────────────────────────────────────────────────┤
│  Schema                                                     │
│  ├── Columns[]                                              │
│  │   ├── Name, Type, Nullable                              │
│  │   ├── Semantic Type (PII, PCI, business key, etc.)      │
│  │   ├── Tags/Classifications                               │
│  │   └── Description                                        │
│  └── Constraints (PK, FK, unique, etc.)                    │
├─────────────────────────────────────────────────────────────┤
│  Lineage                                                    │
│  ├── Upstream Capsules[]                                   │
│  ├── Downstream Capsules[]                                 │
│  └── Transformation Logic (SQL, code reference)            │
├─────────────────────────────────────────────────────────────┤
│  Quality & Governance                                       │
│  ├── Tests/Validations[]                                   │
│  ├── Quality Score                                          │
│  ├── Documentation Completeness                            │
│  └── Compliance Status                                      │
└─────────────────────────────────────────────────────────────┘
```

#### 5.1.2 Data Capsule URN Schema

Each Data Capsule has a unique URN (Uniform Resource Name):

```
urn:dab:{source}:{type}:{namespace}:{name}

Examples:
urn:dab:dbt:model:jaffle_shop.staging:stg_customers
urn:dab:snowflake:table:analytics.marts:dim_customer
urn:dab:bigquery:view:project.dataset:customer_360
```

### 5.2 Graph Model

The Data Architecture Brain maintains a property graph with the following structure:

#### 5.2.1 Node Types

| Node Type | Description | Key Properties |
|-----------|-------------|----------------|
| `DataCapsule` | Core data asset | All capsule properties |
| `Domain` | Business domain | name, description, owner |
| `DataProduct` | Logical data product | name, domain, SLOs |
| `Column` | Individual column | name, type, semantic_type, tags |
| `SourceSystem` | Origin system | name, type, connection_info |
| `Owner` | Team or individual | name, type, contact |
| `Tag` | Classification tag | name, category, sensitivity_level |
| `Rule` | Conformance rule | name, type, severity, pattern |

#### 5.2.2 Edge Types

| Edge Type | From | To | Properties |
|-----------|------|-----|------------|
| `FLOWS_TO` | DataCapsule | DataCapsule | transformation_type |
| `CONTAINS` | DataCapsule | Column | ordinal_position |
| `BELONGS_TO` | DataCapsule | Domain | - |
| `PART_OF` | DataCapsule | DataProduct | - |
| `SOURCED_FROM` | DataCapsule | SourceSystem | - |
| `OWNED_BY` | DataCapsule | Owner | role |
| `TAGGED_WITH` | Column/DataCapsule | Tag | - |
| `DERIVED_FROM` | Column | Column | transformation |
| `VIOLATES` | DataCapsule | Rule | violation_details |

#### 5.2.3 Graph Visualization

```
                    ┌──────────┐
                    │  Domain  │
                    │ Customer │
                    └────┬─────┘
                         │ BELONGS_TO
         ┌───────────────┼───────────────┐
         │               │               │
    ┌────▼────┐    ┌────▼────┐    ┌────▼────┐
    │ Capsule │    │ Capsule │    │ Capsule │
    │  Bronze │───▶│  Silver │───▶│  Gold   │
    │raw_cust │    │stg_cust │    │dim_cust │
    └────┬────┘    └────┬────┘    └────┬────┘
         │              │              │
    ┌────▼────┐    ┌────▼────┐    ┌────▼────┐
    │ Column  │    │ Column  │    │ Column  │
    │  email  │───▶│  email  │───▶│email_hsh│
    │ PII:Yes │    │ PII:Yes │    │ PII:No  │
    └─────────┘    └─────────┘    └─────────┘
                   DERIVED_FROM
```

### 5.3 Semantic Types & Tags

#### 5.3.1 Built-in Semantic Types

| Category | Types |
|----------|-------|
| **Sensitivity** | PII, PCI, PHI, Confidential, Internal, Public |
| **Business Keys** | Primary Key, Business Key, Foreign Key, Natural Key |
| **Time** | Event Time, Processing Time, Valid From, Valid To |
| **Measures** | Metric, KPI, Aggregate, Calculated |
| **Identifiers** | Customer ID, Order ID, Product ID, etc. |

#### 5.3.2 PII Sub-classifications

| PII Type | Examples | Risk Level |
|----------|----------|------------|
| Direct Identifier | SSN, Passport, Driver's License | Critical |
| Contact Info | Email, Phone, Address | High |
| Financial | Bank Account, Credit Card | Critical |
| Health | Medical Records, Insurance | Critical |
| Demographic | Age, Gender, Ethnicity | Medium |
| Behavioral | Purchase History, Browsing | Medium |
| Biometric | Fingerprint, Face ID | Critical |

### 5.4 Architecture Patterns & Rules

#### 5.4.1 Supported Architecture Patterns

| Pattern | Description | Validation Rules |
|---------|-------------|------------------|
| **Medallion** | Bronze → Silver → Gold layers | Layer progression, naming conventions |
| **Data Vault** | Hub, Link, Satellite structures | Naming, key handling, historization |
| **Dimensional** | Fact and Dimension tables | Star schema conformance, SCD handling |
| **Data Mesh** | Domain-oriented data products | Product boundaries, contracts |

#### 5.4.2 Rule Categories

| Category | Example Rules |
|----------|---------------|
| **Naming** | Tables must follow `{layer}_{domain}_{entity}` pattern |
| **Lineage** | Gold layer must only source from Silver |
| **PII** | PII columns must be tagged; PII in Gold must be masked |
| **Documentation** | All models must have descriptions |
| **Testing** | All models must have at least one test |
| **Ownership** | All data products must have assigned owners |

---

## 6. Feature Specification

### 6.1 Feature Overview

| ID | Feature | Priority | MVP |
|----|---------|----------|-----|
| F1 | Metadata Ingestion | P0 | Yes |
| F2 | Graph Construction | P0 | Yes |
| F3 | PII Lineage Tracking | P0 | Yes |
| F4 | Architecture Conformance | P0 | Yes |
| F5 | Query API | P0 | Yes |
| F6 | CLI Interface | P1 | Yes |
| F7 | Redundancy Detection | P1 | No |
| F8 | Impact Analysis | P1 | No |
| F9 | Web Dashboard | P2 | No |
| F10 | Alerting & Notifications | P2 | No |

### 6.2 F1: Metadata Ingestion

#### 6.2.1 Description
Ingest metadata from source systems and normalize into the Data Capsule model.

#### 6.2.2 MVP Scope: dbt Integration

**Input Sources:**
- `manifest.json` - Model definitions, dependencies, configs
- `catalog.json` - Column-level metadata, stats
- `sources.yml` - Source definitions
- `schema.yml` - Tests, documentation

**Extracted Metadata:**

| dbt Artifact | Extracted Information |
|--------------|----------------------|
| Models | Name, schema, materialization, tags, meta, description |
| Columns | Name, type, description, meta (PII tags), tests |
| Sources | Name, database, schema, freshness, loaded_at |
| Tests | Type, column, severity, status |
| Lineage | depends_on, parent models, ref() relationships |

**Ingestion Process:**
```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  dbt Files  │────▶│   Parser    │────▶│ Transformer │────▶│   Graph     │
│  (JSON/YAML)│     │             │     │  (Normalize)│     │   Storage   │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
```

#### 6.2.3 Acceptance Criteria

- [ ] Parse dbt manifest.json and extract all models
- [ ] Parse dbt catalog.json and extract column metadata
- [ ] Extract lineage relationships from depends_on
- [ ] Normalize to Data Capsule format
- [ ] Handle incremental updates (re-ingestion)
- [ ] Report parsing errors with clear messages

### 6.3 F2: Graph Construction

#### 6.3.1 Description
Build and maintain a queryable graph from ingested metadata.

#### 6.3.2 Graph Operations

| Operation | Description |
|-----------|-------------|
| Create Node | Add new Data Capsule, Column, etc. |
| Create Edge | Add relationships (FLOWS_TO, CONTAINS, etc.) |
| Update Node | Modify properties on re-ingestion |
| Merge Node | Handle duplicate detection and merging |
| Query | Traverse, filter, aggregate |

#### 6.3.3 Acceptance Criteria

- [ ] Store all node types (DataCapsule, Column, Domain, Tag, etc.)
- [ ] Store all edge types with properties
- [ ] Support efficient traversal queries (BFS, DFS)
- [ ] Support property-based filtering
- [ ] Handle graph updates on re-ingestion
- [ ] Maintain referential integrity

### 6.4 F3: PII Lineage Tracking

#### 6.4.1 Description
Track sensitive data (PII/PCI/PHI) through transformation pipelines, identifying where it originates, propagates, and terminates.

#### 6.4.2 Capabilities

**PII Discovery:**
- Extract PII tags from dbt meta configurations
- Pattern-based detection (column names: email, ssn, phone, etc.)
- Type-based inference (configurable patterns)

**PII Lineage:**
- Trace PII columns upstream to source
- Trace PII columns downstream to consumers
- Identify transformation points (masking, hashing, encryption)
- Detect PII exposure (unmasked PII in Gold/Mart layers)

**PII Reporting:**
- Generate PII inventory (all PII columns by type)
- Generate PII flow diagrams
- Identify compliance gaps

#### 6.4.3 Example Queries

```
# Find all PII columns
GET /api/v1/columns?semantic_type=PII

# Trace a specific PII column
GET /api/v1/columns/{urn}/lineage?direction=both

# Find exposed PII (PII in Gold without masking)
GET /api/v1/compliance/pii-exposure

# Generate PII inventory report
GET /api/v1/reports/pii-inventory
```

#### 6.4.4 Acceptance Criteria

- [ ] Identify PII columns from dbt meta tags
- [ ] Identify PII columns from naming patterns
- [ ] Trace PII upstream to source
- [ ] Trace PII downstream to consumers
- [ ] Detect PII transformation points
- [ ] Detect exposed PII (unmasked in consumption layer)
- [ ] Generate PII inventory report

### 6.5 F4: Architecture Conformance Checking

#### 6.5.1 Description
Validate data architecture against defined standards and patterns, surfacing violations and anti-patterns.

#### 6.5.2 Rule Engine

**Rule Definition Format:**
```yaml
rules:
  - id: NAMING_001
    name: "Model naming convention"
    description: "Models must follow {layer}_{domain}_{entity} pattern"
    severity: warning
    category: naming
    scope: model
    pattern:
      type: regex
      value: "^(raw|stg|int|dim|fct|rpt)_[a-z]+_[a-z_]+$"

  - id: LINEAGE_001
    name: "Gold sources Silver only"
    description: "Gold/Mart models should only source from Silver/Intermediate"
    severity: error
    category: lineage
    scope: model
    condition:
      if:
        layer: gold
      then:
        upstream_layers: [silver, intermediate]

  - id: PII_001
    name: "PII in Gold must be masked"
    description: "PII columns in Gold layer must have masking transformation"
    severity: critical
    category: pii
    scope: column
    condition:
      if:
        layer: gold
        semantic_type: PII
      then:
        has_transformation: [hash, mask, encrypt, redact]
```

**Built-in Rule Sets:**

| Rule Set | Description | Rules |
|----------|-------------|-------|
| Medallion | Bronze/Silver/Gold pattern validation | 12 rules |
| dbt Best Practices | dbt community standards | 15 rules |
| PII Compliance | Sensitive data handling | 8 rules |
| Documentation | Required documentation | 5 rules |

#### 6.5.3 Conformance Scoring

```
Conformance Score = (Passing Rules / Total Applicable Rules) × 100

Weighted Score = Σ(Rule Weight × Pass/Fail) / Σ(Rule Weights)
  where Critical=10, Error=5, Warning=2, Info=1
```

#### 6.5.4 Acceptance Criteria

- [ ] Define rules in YAML format
- [ ] Support regex pattern matching
- [ ] Support graph-based conditions (lineage constraints)
- [ ] Execute rules against graph
- [ ] Calculate conformance scores
- [ ] Generate violation reports
- [ ] Support custom rule definitions

### 6.6 F5: Query API

#### 6.6.1 Description
RESTful API for querying the architecture graph.

#### 6.6.2 API Endpoints

**Capsules (Data Assets):**
```
GET    /api/v1/capsules                    # List all capsules
GET    /api/v1/capsules/{urn}              # Get capsule by URN
GET    /api/v1/capsules/{urn}/lineage      # Get lineage
GET    /api/v1/capsules/{urn}/columns      # Get columns
GET    /api/v1/capsules/{urn}/violations   # Get rule violations
```

**Columns:**
```
GET    /api/v1/columns                     # List columns (with filters)
GET    /api/v1/columns/{urn}               # Get column by URN
GET    /api/v1/columns/{urn}/lineage       # Get column lineage
```

**Domains & Products:**
```
GET    /api/v1/domains                     # List domains
GET    /api/v1/domains/{name}/capsules     # Capsules in domain
GET    /api/v1/products                    # List data products
GET    /api/v1/products/{name}/capsules    # Capsules in product
```

**Compliance & Conformance:**
```
GET    /api/v1/compliance/pii-inventory    # PII inventory report
GET    /api/v1/compliance/pii-exposure     # Exposed PII report
GET    /api/v1/conformance/score           # Overall conformance score
GET    /api/v1/conformance/violations      # All violations
GET    /api/v1/conformance/rules           # List configured rules
POST   /api/v1/conformance/evaluate        # Run conformance check
```

**Ingestion:**
```
POST   /api/v1/ingest/dbt                  # Ingest dbt artifacts
GET    /api/v1/ingest/status               # Ingestion status
GET    /api/v1/ingest/history              # Ingestion history
```

#### 6.6.3 Query Parameters

| Parameter | Description | Example |
|-----------|-------------|---------|
| `layer` | Filter by architecture layer | `?layer=gold` |
| `domain` | Filter by business domain | `?domain=customer` |
| `semantic_type` | Filter by semantic type | `?semantic_type=PII` |
| `tag` | Filter by tag | `?tag=pii:email` |
| `source` | Filter by source system | `?source=dbt` |
| `depth` | Lineage traversal depth | `?depth=3` |
| `direction` | Lineage direction | `?direction=upstream` |

#### 6.6.4 Acceptance Criteria

- [ ] Implement all capsule endpoints
- [ ] Implement column endpoints with lineage
- [ ] Implement compliance endpoints
- [ ] Implement conformance endpoints
- [ ] Support query parameters for filtering
- [ ] Return proper HTTP status codes
- [ ] Include pagination for list endpoints
- [ ] Document with OpenAPI spec

### 6.7 F6: CLI Interface

#### 6.7.1 Description
Command-line interface for common operations.

#### 6.7.2 Commands

```bash
# Ingestion
dab ingest dbt --manifest ./target/manifest.json --catalog ./target/catalog.json
dab ingest status

# Exploration
dab capsules list [--layer gold] [--domain customer]
dab capsules show <urn>
dab capsules lineage <urn> [--depth 3] [--direction both]

# PII
dab pii inventory [--format json|csv|table]
dab pii trace <column-urn> [--direction both]
dab pii exposure

# Conformance
dab conformance score
dab conformance violations [--severity critical|error|warning]
dab conformance check [--rules ./custom-rules.yaml]

# Reports
dab report pii-inventory --output ./reports/pii.html
dab report conformance --output ./reports/conformance.html
dab report lineage <urn> --output ./reports/lineage.html
```

#### 6.7.3 Acceptance Criteria

- [ ] Implement ingestion commands
- [ ] Implement exploration commands
- [ ] Implement PII commands
- [ ] Implement conformance commands
- [ ] Support multiple output formats (table, JSON, CSV)
- [ ] Provide helpful error messages
- [ ] Include --help for all commands

---

## 7. Use Cases

### 7.1 UC1: PII Lineage Audit

**Actor:** Priya (Privacy/Compliance Officer)

**Preconditions:**
- dbt project ingested into Data Architecture Brain
- PII columns tagged in dbt meta or detected by patterns

**Flow:**
1. Priya runs `dab pii inventory` to get complete PII inventory
2. System returns list of all PII columns grouped by type
3. Priya identifies email addresses in the customer domain
4. Priya runs `dab pii trace urn:dab:dbt:column:stg_customers.email`
5. System traces email from source → staging → mart
6. System shows email is hashed in dim_customer (transformation: SHA256)
7. Priya confirms PII handling is compliant

**Postconditions:**
- Priya has documented evidence of PII handling
- Audit report generated

**Acceptance Criteria:**
- [ ] PII inventory lists all sensitive columns
- [ ] Lineage trace shows complete path
- [ ] Transformations are identified
- [ ] Report is exportable

### 7.2 UC2: Architecture Conformance Review

**Actor:** Dana (Data Architect)

**Preconditions:**
- dbt project ingested
- Medallion architecture rules configured

**Flow:**
1. Dana runs `dab conformance score` for overall health check
2. System returns: 78% conformance (34/44 rules passing)
3. Dana runs `dab conformance violations --severity error`
4. System lists violations:
   - 3 models in Gold sourcing directly from Bronze
   - 2 models with missing descriptions
   - 1 model with non-standard naming
5. Dana reviews each violation with `dab capsules show <urn>`
6. Dana creates JIRA tickets for remediation
7. After fixes, Dana re-ingests and re-runs conformance check
8. Conformance score increases to 95%

**Postconditions:**
- Architecture violations identified and tracked
- Technical debt reduced

**Acceptance Criteria:**
- [ ] Conformance score calculated correctly
- [ ] Violations listed with details
- [ ] Violations include remediation guidance
- [ ] Re-ingestion detects fixes

### 7.3 UC3: Pre-Change Impact Analysis

**Actor:** Marcus (Platform Engineer)

**Preconditions:**
- dbt project ingested with full lineage

**Flow:**
1. Marcus needs to deprecate `stg_customers_legacy`
2. Marcus runs `dab capsules lineage urn:dab:dbt:model:stg_customers_legacy --direction downstream --depth 5`
3. System shows 12 downstream models depend on this table
4. Marcus exports dependency list for stakeholder review
5. Marcus identifies replacement strategy
6. After migration, Marcus re-ingests and confirms no dependencies remain

**Postconditions:**
- All downstream impacts identified
- Safe deprecation plan created

**Acceptance Criteria:**
- [ ] Full downstream lineage retrieved
- [ ] All indirect dependencies included
- [ ] Export functionality works
- [ ] Re-ingestion reflects changes

### 7.4 UC4: New Model Validation

**Actor:** Sam (Data Engineer)

**Preconditions:**
- Sam has created a new dbt model
- Architecture rules are configured

**Flow:**
1. Sam runs dbt build for new model
2. Sam runs `dab ingest dbt` with updated manifest
3. Sam runs `dab conformance check`
4. System flags: new model `gold_customer_metrics` sources from Bronze
5. System flags: new model lacks description
6. Sam fixes issues and re-runs
7. No violations for new model

**Postconditions:**
- New model conforms to standards before PR

**Acceptance Criteria:**
- [ ] New models detected on re-ingestion
- [ ] Violations specific to new models highlighted
- [ ] Clear guidance provided

---

## 8. Non-Functional Requirements

### 8.1 Performance

| Metric | Target | Notes |
|--------|--------|-------|
| Ingestion time | < 30s for 1000 models | Full dbt project |
| Query response | P95 < 500ms | Standard queries |
| Lineage traversal | < 2s for depth=10 | Complex graphs |
| Conformance check | < 10s for 50 rules | Full rule set |

### 8.2 Scalability

| Dimension | MVP Target | Future Target |
|-----------|------------|---------------|
| Models/Tables | 10,000 | 100,000 |
| Columns | 500,000 | 5,000,000 |
| Lineage edges | 100,000 | 1,000,000 |
| Rules | 100 | 500 |

### 8.3 Reliability

| Metric | Target |
|--------|--------|
| Availability | 99.9% (when deployed) |
| Data durability | No data loss on restart |
| Graceful degradation | Partial results on timeout |

### 8.4 Security

| Requirement | Description |
|-------------|-------------|
| Authentication | API key for CLI/API (MVP) |
| Authorization | Read-only by design |
| Data at rest | Encrypted storage |
| Secrets | No credentials stored in graph |

### 8.5 Operability

| Requirement | Description |
|-------------|-------------|
| Deployment | Docker Compose (MVP) |
| Configuration | Environment variables + config files |
| Logging | Structured JSON logs |
| Monitoring | Health check endpoint |

---

## 9. Integration Strategy

### 9.1 MVP Integration: dbt

```
┌─────────────────────────────────────────────────────────────┐
│                        dbt Project                          │
├─────────────────────────────────────────────────────────────┤
│  models/           schema.yml          target/              │
│  ├── staging/      ├── sources        ├── manifest.json    │
│  ├── intermediate/ └── models         └── catalog.json     │
│  └── marts/                                                 │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                  Data Architecture Brain                    │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────┐    ┌──────────┐    ┌──────────┐             │
│  │  Parser  │───▶│Transform │───▶│  Graph   │             │
│  │  (dbt)   │    │(Capsules)│    │ Storage  │             │
│  └──────────┘    └──────────┘    └──────────┘             │
└─────────────────────────────────────────────────────────────┘
```

### 9.2 Future Integrations (Post-MVP)

| Source | Priority | Metadata Type | Notes |
|--------|----------|---------------|-------|
| Snowflake | P1 | INFORMATION_SCHEMA, ACCESS_HISTORY | Live metadata |
| BigQuery | P1 | INFORMATION_SCHEMA, DATA_CATALOG | Live metadata |
| Databricks | P2 | Unity Catalog | Live metadata + lineage |
| Airflow | P2 | DAG definitions | Pipeline metadata |
| OpenLineage | P2 | Lineage events | Real-time lineage |
| DataHub/OpenMetadata | P3 | Existing catalogs | Complement existing |

### 9.3 Shared Infrastructure with Easy Modeller

| Component | Shared? | Notes |
|-----------|---------|-------|
| Database (PostgreSQL) | Yes | Separate schemas |
| Docker Compose | Yes | Shared network |
| Authentication | Yes | Same auth service |
| API Framework (FastAPI) | Yes | Same patterns |
| Frontend (if added) | Yes | Same React/Next.js stack |

---

## 10. Success Metrics

### 10.1 Adoption Metrics

| Metric | Target (3 months post-launch) |
|--------|------------------------------|
| Weekly active users | 10+ |
| Ingestion frequency | Daily for active projects |
| API calls per week | 500+ |

### 10.2 Value Metrics

| Metric | Target |
|--------|--------|
| PII inventory accuracy | 95%+ (validated by manual audit) |
| Conformance issues found | 20+ per project (initial scan) |
| Time to generate PII report | < 5 minutes (vs. days manually) |
| Time for impact analysis | < 10 minutes (vs. hours manually) |

### 10.3 Quality Metrics

| Metric | Target |
|--------|--------|
| False positive rate (PII detection) | < 10% |
| False negative rate (PII detection) | < 5% |
| Rule accuracy | 99%+ |
| API availability | 99.9% |

---

## 11. Roadmap

### 11.1 Phase 1: MVP Foundation (Weeks 1-6)

| Week | Focus | Deliverables |
|------|-------|--------------|
| 1-2 | Infrastructure | Docker setup, DB schema, API skeleton |
| 3-4 | dbt Ingestion | Parser, transformer, graph storage |
| 5-6 | Core Features | PII tracking, conformance engine, CLI |

**MVP Milestone:** Working CLI with dbt ingestion, PII lineage, conformance checking

### 11.2 Phase 2: Polish & Extend (Weeks 7-10)

| Week | Focus | Deliverables |
|------|-------|--------------|
| 7-8 | API & Reports | Full REST API, report generation |
| 9-10 | Rule Engine | Custom rules, rule sets, scoring |

### 11.3 Phase 3: Production Ready (Weeks 11-14)

| Week | Focus | Deliverables |
|------|-------|--------------|
| 11-12 | Hardening | Error handling, performance, testing |
| 13-14 | Documentation | User guide, API docs, examples |

### 11.4 Future Phases (Post-MVP)

| Phase | Focus |
|-------|-------|
| Phase 4 | Snowflake/BigQuery integration |
| Phase 5 | Web dashboard |
| Phase 6 | Redundancy detection |
| Phase 7 | LLM-powered insights |

---

## Appendices

### Appendix A: Glossary

| Term | Definition |
|------|------------|
| Data Capsule | Atomic unit representing a data asset with full context |
| URN | Uniform Resource Name - unique identifier for nodes |
| Lineage | The flow of data from source to destination |
| Conformance | Adherence to defined architecture standards |
| Semantic Type | Classification of data meaning (PII, key, metric, etc.) |
| Medallion | Architecture pattern with Bronze/Silver/Gold layers |

### Appendix B: dbt Meta Tag Conventions

For optimal PII detection, use these meta conventions in dbt:

```yaml
# schema.yml
models:
  - name: stg_customers
    columns:
      - name: email
        meta:
          pii: true
          pii_type: contact_info
          sensitivity: high
      - name: customer_id
        meta:
          semantic_type: business_key
```

### Appendix C: Sample Conformance Rules

See `docs/design_docs/conformance_rules.yaml` for the complete rule set.

### Appendix D: API Response Examples

See `docs/design_docs/api_specification.md` for detailed examples.

---

*End of Product Specification*
