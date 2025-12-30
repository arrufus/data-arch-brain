# Airflow Metamodel - Visual Summary

## The Problem: Incorrect Categorization

### Current (Incorrect) ❌

```
When you run: dcs ingest airflow

Report says: "✓ Capsules Created: 42"

What's created:
├── airflow_dag capsules (5)
├── airflow_task capsules (37)
└── Total: 42 "data capsules"

Problem: DAGs and tasks are NOT data capsules!
They're orchestration metadata.
```

### Correct Model ✓

```
When you run: dcs ingest airflow

Report should say:
  "✓ Pipelines Created: 5"
  "✓ Tasks Created: 37"
  "✓ Data Capsules Linked: 15"

What's created:
├── Pipeline entities (5)        ← Orchestration
├── PipelineTask entities (37)   ← Orchestration
├── Data flow edges (52)         ← Links orchestration to data
└── DataCapsules (0 new)         ← These already exist from dbt ingestion
```

---

## Key Concept: Two Separate Layers

```
┌─────────────────────────────────────────────────────────┐
│              ORCHESTRATION LAYER                        │
│  "HOW data is moved, WHEN, and BY WHOM"                │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Pipeline: finance_gl_pipeline                          │
│    ├── Task: validate_chart_of_accounts                │
│    ├── Task: load_gl_transactions                      │
│    └── Task: generate_revenue_by_month                 │
│                                                         │
│  Pipeline: customer_order_pipeline                      │
│    ├── Task: stage_customers                            │
│    └── Task: build_orders_fact                          │
│                                                         │
└─────────────────────────────────────────────────────────┘
                          │
                          │ PRODUCES / CONSUMES
                          │ (Data Flow Edges)
                          ↓
┌─────────────────────────────────────────────────────────┐
│                  DATA LAYER                             │
│  "WHAT data exists, its structure, and lineage"        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  DataCapsule: chart_of_accounts (table)                │
│  DataCapsule: gl_transactions (table)                   │
│  DataCapsule: revenue_by_month (mart)                   │
│  DataCapsule: stg_customers (model)                     │
│  DataCapsule: orders_fact (mart)                        │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## Entity Comparison

### Before (Incorrect)

| Entity Type | Created From | Stored As | URN |
|-------------|--------------|-----------|-----|
| DAG | Airflow API | `Capsule` | urn:dcs:airflow:dag:...|
| Task | Airflow API | `Capsule` | urn:dcs:airflow:task:... |
| **Problem** | **DAGs/tasks are not data!** | **Wrong table** | **Wrong namespace** |

### After (Correct)

| Entity Type | Created From | Stored As | URN |
|-------------|--------------|-----------|-----|
| DAG | Airflow API | `Pipeline` | urn:dcs:pipeline:airflow:... |
| Task | Airflow API | `PipelineTask` | urn:dcs:task:airflow:... |
| Table | dbt/Snowflake | `DataCapsule` | urn:dcs:postgres:table:... |
| Model | dbt | `DataCapsule` | urn:dcs:dbt:model:... |

---

## Relationship Types

### Orchestration-to-Orchestration

```
Pipeline: finance_gl_pipeline
  │
  ├─[CONTAINS]─→ Task: validate_chart_of_accounts
  │                │
  │                └─[DEPENDS_ON]─→ Task: load_gl_transactions
  │                                   │
  │                                   └─[DEPENDS_ON]─→ Task: generate_revenue_by_month
  │
  └─[TRIGGERS]─→ Pipeline: cross_domain_analytics_pipeline
```

### Orchestration-to-Data (NEW!)

```
Task: load_gl_transactions
  │
  ├─[CONSUMES]─→ DataCapsule: chart_of_accounts
  │                (reads account hierarchy)
  │
  └─[PRODUCES]─→ DataCapsule: gl_transactions
                   (inserts daily transactions)
```

### Data-to-Data (Existing)

```
DataCapsule: chart_of_accounts
  │
  └─[FLOWS_TO]─→ DataCapsule: gl_transactions
                   │
                   └─[FLOWS_TO]─→ DataCapsule: revenue_by_month
```

---

## Integrated Lineage View

### Example: Finance GL Pipeline

```
ORCHESTRATION LAYER:
┌──────────────────────────────────────────────────────┐
│ Pipeline: finance_gl_pipeline (runs daily 1 AM)      │
│                                                      │
│ ┌────────────────────────┐                          │
│ │ validate_chart_of_     │                          │
│ │ accounts               │──┐                       │
│ │ [PythonOperator]       │  │                       │
│ └────────────────────────┘  │ CONSUMES              │
│                             │                       │
│ ┌────────────────────────┐  │                       │
│ │ load_gl_               │  │                       │
│ │ transactions           │←─┘                       │
│ │ [PythonOperator]       │                          │
│ └────────────────────────┘                          │
│         │                                            │
│         │ PRODUCES                                   │
│         ↓                                            │
│ ┌────────────────────────┐                          │
│ │ generate_revenue_      │                          │
│ │ by_month               │                          │
│ │ [DbtOperator]          │                          │
│ └────────────────────────┘                          │
└──────────────────────────────────────────────────────┘
         │              │
         │ CONSUMES     │ PRODUCES
         ↓              ↓
┌──────────────────────────────────────────────────────┐
│ DATA LAYER:                                          │
│                                                      │
│ ┌────────────┐     ┌────────────┐     ┌──────────┐ │
│ │chart_of_   │────→│gl_         │────→│revenue_  │ │
│ │accounts    │     │transactions│     │by_month  │ │
│ │[Master]    │     │[Fact]      │     │[Mart]    │ │
│ └────────────┘     └────────────┘     └──────────┘ │
│                          FLOWS_TO                    │
└──────────────────────────────────────────────────────┘
```

---

## Deep dbt Integration

### Scenario: Airflow runs dbt

```
Airflow Task: run_dbt_finance
  ├── Executes: "dbt run --select tag:finance"
  │
  ├── dbt manifest shows models:
  │   ├── gl_transactions
  │   └── revenue_by_month
  │
  └── System automatically creates:
      ├── PRODUCES → urn:dcs:postgres:table:finance_erp.facts:gl_transactions
      └── PRODUCES → urn:dcs:dbt:model:finance_analytics.marts:revenue_by_month
```

**Captured Metadata**:
```json
{
  "task": {
    "urn": "urn:dcs:task:airflow:local-dev:finance_gl_pipeline.run_dbt_finance",
    "name": "run_dbt_finance",
    "operator": "DbtOperator",
    "tool_reference": {
      "tool": "dbt",
      "dbt_selector": "tag:finance",
      "dbt_models_executed": ["gl_transactions", "revenue_by_month"]
    }
  },
  "data_flow": {
    "produces": [
      "urn:dcs:postgres:table:finance_erp.facts:gl_transactions",
      "urn:dcs:dbt:model:finance_analytics.marts:revenue_by_month"
    ]
  }
}
```

---

## Query Examples

### 1. "Which pipelines produce this data?"

```
Query: GET /api/v1/capsules/{urn}/producers

Input: urn:dcs:postgres:table:finance_erp.facts:gl_transactions

Output:
{
  "capsule": "gl_transactions",
  "producers": [
    {
      "pipeline": "finance_gl_pipeline",
      "pipeline_urn": "urn:dcs:pipeline:airflow:local-dev:finance_gl_pipeline",
      "task": "load_gl_transactions",
      "task_urn": "urn:dcs:task:airflow:local-dev:finance_gl_pipeline.load_gl_transactions",
      "operator": "PythonOperator",
      "schedule": "0 1 * * *",
      "last_run": "2025-12-28T01:00:00Z"
    }
  ]
}
```

### 2. "What data does this pipeline touch?"

```
Query: GET /api/v1/pipelines/{urn}/data-footprint

Input: urn:dcs:pipeline:airflow:local-dev:finance_gl_pipeline

Output:
{
  "pipeline": "finance_gl_pipeline",
  "data_footprint": {
    "consumes": [
      {
        "urn": "urn:dcs:postgres:table:finance_erp.master:chart_of_accounts",
        "name": "chart_of_accounts",
        "layer": "gold",
        "task_count": 2
      }
    ],
    "produces": [
      {
        "urn": "urn:dcs:postgres:table:finance_erp.facts:gl_transactions",
        "name": "gl_transactions",
        "layer": "gold",
        "task_count": 1
      },
      {
        "urn": "urn:dcs:dbt:model:finance_analytics.marts:revenue_by_month",
        "name": "revenue_by_month",
        "layer": "gold",
        "task_count": 1
      }
    ]
  }
}
```

### 3. "If I pause this pipeline, what breaks?"

```
Query: GET /api/v1/pipelines/{urn}/impact-analysis

Input: urn:dcs:pipeline:airflow:local-dev:finance_gl_pipeline

Output:
{
  "pipeline": "finance_gl_pipeline",
  "impact": {
    "downstream_capsules": [
      "revenue_by_month",
      "customer_revenue_analytics"
    ],
    "affected_pipelines": [
      {
        "pipeline": "cross_domain_analytics_pipeline",
        "reason": "Consumes revenue_by_month",
        "criticality": "high"
      }
    ],
    "affected_data_products": [
      "Financial Reporting Product",
      "Customer Revenue Analytics"
    ],
    "estimated_impact": "High - blocks downstream analytics"
  }
}
```

---

## Visualization: Before vs After

### Before (Flat, confusing)

```
Everything is a "capsule":

finance_gl_pipeline (capsule?)
├── validate_chart_of_accounts (capsule?)
├── load_gl_transactions (capsule?)
├── generate_revenue_by_month (capsule?)
├── chart_of_accounts (capsule)
├── gl_transactions (capsule)
└── revenue_by_month (capsule)

Problem: Can't tell pipelines from data!
```

### After (Layered, clear)

```
Orchestration Layer:
  Pipeline: finance_gl_pipeline
    ├── Task: validate_chart_of_accounts
    ├── Task: load_gl_transactions
    └── Task: generate_revenue_by_month
         │
         │ (PRODUCES/CONSUMES edges)
         ↓
Data Layer:
  DataCapsule: chart_of_accounts
  DataCapsule: gl_transactions
  DataCapsule: revenue_by_month

Clear separation! ✓
```

---

## CLI Output Comparison

### Current (Incorrect)

```bash
$ dcs ingest airflow --base-url http://localhost:8080 \
    --auth-mode basic_env --include-paused

⠙ Ingesting Airflow metadata...

✓ Ingestion completed successfully!
  Job ID: 4a9a25e0-3079-4b97-8352-5e393c565549
  Source: local-dev
  Duration: 0.90s

    Ingestion Statistics
┌──────────────────────┬───────┐
│ Metric               │ Count │
├──────────────────────┼───────┤
│ Capsules Created     │    42 │  ❌ WRONG!
│ Columns Created      │     0 │
│ Lineage Edges        │    71 │
└──────────────────────┴───────┘
```

### Corrected (Should be)

```bash
$ dcs ingest airflow --base-url http://localhost:8080 \
    --auth-mode basic_env --include-paused

⠙ Ingesting Airflow metadata...

✓ Ingestion completed successfully!
  Job ID: 4a9a25e0-3079-4b97-8352-5e393c565549
  Source: local-dev
  Duration: 0.90s

    Ingestion Statistics
┌──────────────────────────────┬───────┐
│ Metric                       │ Count │
├──────────────────────────────┼───────┤
│ Pipelines Created            │     5 │  ✓ CORRECT!
│ Pipeline Tasks Created       │    37 │  ✓ CORRECT!
│ Data Capsules Linked         │    15 │  ✓ CORRECT!
│ Orchestration Edges          │    42 │  ✓ (CONTAINS, DEPENDS_ON)
│ Data Flow Edges              │    29 │  ✓ (PRODUCES, CONSUMES)
└──────────────────────────────┴───────┘

Data Flow Summary:
  Pipelines that PRODUCE data:    5
  Pipelines that CONSUME data:    4
  Total data capsules in scope:  15
```

---

## Implementation Checklist

### Phase 1: Metamodel (Week 1-2)
- [ ] Create `Pipeline` model
- [ ] Create `PipelineTask` model
- [ ] Create `ToolReference` model
- [ ] Add new edge types (PRODUCES, CONSUMES, TRANSFORMS)
- [ ] Database migrations

### Phase 2: Parser (Week 2-3)
- [ ] Refactor Airflow parser to create Pipelines (not Capsules)
- [ ] Implement task parsing
- [ ] Implement orchestration edge creation

### Phase 3: Data Flow (Week 3-5)
- [ ] Implement data flow mapping
- [ ] Add dbt integration (DbtOperator → dbt models → capsules)
- [ ] Add SQL parsing
- [ ] Manual annotation support

### Phase 4: API (Week 5-6)
- [ ] Pipeline query endpoints
- [ ] Capsule-to-pipeline queries
- [ ] Integrated lineage endpoints
- [ ] Impact analysis endpoint

### Phase 5: CLI (Week 6-7)
- [ ] Pipeline commands
- [ ] Updated ingestion output
- [ ] Integrated lineage commands

### Phase 6: Visualization (Week 7-8)
- [ ] Orchestration-only view
- [ ] Data-only view
- [ ] Integrated view
- [ ] Mermaid/DOT export

---

## Key Takeaways

1. **Airflow DAGs are NOT data capsules**
   - They're orchestration/pipeline metadata
   - Store in separate `Pipeline` entities

2. **Tasks link orchestration to data**
   - Tasks PRODUCE data capsules
   - Tasks CONSUME data capsules
   - This creates the data flow map

3. **Two lineage types**
   - Orchestration lineage (pipeline → task → task)
   - Data lineage (capsule → capsule)
   - Combined: integrated view

4. **Deep tool integration**
   - Airflow → dbt → data capsules
   - Airflow → SQL → tables
   - Airflow → Spark → datasets

5. **Correct reporting**
   - Report pipelines/tasks created
   - Report data capsules linked
   - NOT "42 capsules created"

---

**Status**: Design Complete ✓
**Next**: Implementation (DO NOT IMPLEMENT YET)
**Reference**: [Full Design Document](./airflow_orchestration_metamodel.md)
