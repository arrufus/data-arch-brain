# Airflow Environment - Setup Summary

## Overview

The Airflow environment has been successfully reinitialized based on the design document at [docs/design_docs/airflow_integration_design.md](../docs/design_docs/airflow_integration_design.md).

**Setup Date:** December 28, 2025
**Airflow Version:** 2.8.0-python3.11
**Executor:** LocalExecutor

---

## Infrastructure

### Docker Compose Services

The environment consists of 3 containers:

1. **dab-postgres-airflow** (Port 5436)
   - Airflow metadata database
   - Image: postgres:15
   - Credentials: airflow/airflow

2. **dab-postgres-data** (Port 5435)
   - Data layer databases (bronze_db, silver_db)
   - Image: postgres:15
   - Credentials: postgres/postgres

3. **dab-airflow** (Port 8080)
   - Airflow standalone (webserver + scheduler)
   - Image: apache/airflow:2.8.0-python3.11
   - Admin credentials: admin/admin

---

## Example DAGs

The environment includes 5 DAGs demonstrating Data Capsule Server (DCS) integration:

### 1. Finance GL Pipeline (`finance_gl_pipeline`)
**Owner:** finance_data_team
**Schedule:** Daily at 1 AM
**Status:** ✓ Active

Processes finance data capsules from the DCS Finance domain:
- **chart_of_accounts** (Master Data)
  - URN: `urn:dcs:postgres:table:finance_erp.master:chart_of_accounts`
  - ~500 accounts
- **gl_transactions** (Fact Table)
  - URN: `urn:dcs:postgres:table:finance_erp.facts:gl_transactions`
  - ~50M rows, 25 GB
  - Includes double-entry accounting validation
- **revenue_by_month** (Analytical Mart)
  - URN: `urn:dcs:dbt:model:finance_analytics.marts:revenue_by_month`
  - Incremental dbt model

**Key Features:**
- SOX/GAAP compliance checks
- Double-entry balance validation (critical SOX control)
- Data quality rules at each stage
- Updates 2 data products: Financial Reporting Product & General Ledger Data Product

**Tags:** finance, general_ledger, sox, gaap, tier-1, regulatory

---

### 2. Customer Order Pipeline (`customer_order_pipeline`)
**Owner:** data_platform_team
**Schedule:** Every 6 hours
**Status:** ✓ Active

Processes customer and order data capsules from the Jaffle Shop domain:
- **stg_customers** (Staging/Dimension)
  - URN: `urn:dcs:dbt:model:jaffle_shop.staging:stg_customers`
  - ~1,500 customers
- **stg_orders** (Staging/Fact)
  - URN: `urn:dcs:dbt:model:jaffle_shop.staging:stg_orders`
  - ~8,500 orders
- **orders_fact** (Analytical Mart)
  - URN: `urn:dcs:dbt:model:jaffle_shop.marts:orders_fact`
  - Gold layer fact table

**Key Features:**
- Bronze → Silver → Gold medallion architecture
- Customer dimension processing with profiling
- Referential integrity validation (orders → customers FK)
- Data quality tests via dbt
- Updates DCS catalog with pipeline metadata

**Tags:** customer, orders, analytics, jaffle_shop

---

### 3. Cross-Domain Analytics Pipeline (`cross_domain_analytics_pipeline`)
**Owner:** analytics_team
**Schedule:** Daily at 4 AM
**Status:** ✓ Active

Demonstrates **Data Mesh principles** by composing data from multiple domains:

**Upstream Dependencies:**
- Waits for `finance_gl_pipeline` completion
- Waits for `customer_order_pipeline` completion

**Consumed Data Products:**
1. Finance domain: `revenue_by_month` capsule
2. Customer domain: `orders_fact` capsule

**Output Capsule (conceptual):**
- `customer_revenue_analytics`
- URN: `urn:dcs:dbt:model:analytics.marts:customer_revenue_analytics`

**Key Features:**
- Cross-domain data integration
- Revenue reconciliation between GL and customer orders
- Quality validation with acceptable variance thresholds (±5%)
- Updates DCS lineage graph with cross-domain edges
- Demonstrates federated data governance

**Consumers:**
- executive_dashboard
- finance_reporting
- customer_analytics

**Tags:** analytics, cross-domain, data-mesh, finance, customer

---

### 4. Customer Analytics Pipeline (`customer_analytics_pipeline`)
**Owner:** data_engineering
**Schedule:** Daily at 2 AM
**Status:** ✓ Active
**Description:** Legacy dbt-based customer analytics pipeline (existing)

---

### 5. Daily Sales Summary (`daily_sales_summary`)
**Owner:** data_engineering
**Schedule:** Daily at 3 AM
**Status:** ✓ Active
**Description:** Daily sales summary report generation (existing)

---

## Data Capsule Lineage

The DAGs demonstrate the following lineage flows tracked in DCS:

### Finance Domain Flow
```
chart_of_accounts (Master Data)
        ↓
   foreign_key_join
        ↓
gl_transactions (Fact Table)
        ↓
   aggregation
        ↓
revenue_by_month (Mart)
```

### Customer Domain Flow
```
stg_customers (Dimension) ──┐
                            │
                       FK validation
                            │
stg_orders (Fact) ──────────┘
        ↓
    enrichment
        ↓
orders_fact (Mart)
```

### Cross-Domain Integration
```
revenue_by_month (Finance) ──┐
                             │
                        join + reconcile
                             │
orders_fact (Customer) ───────┘
        ↓
customer_revenue_analytics (Cross-Domain Mart)
```

---

## DCS Integration Points

### Metadata Represented in DAGs

Each DAG demonstrates key DCS concepts:

1. **URN Identification**: All capsules referenced by their DCS URN
2. **7 Dimensions Coverage**:
   - Identity & Context (capsule type, layer, domain)
   - Structural Metadata (columns, constraints, indexes)
   - Business Terms (linked terms documented in code)
   - Quality & Profiling (validation checks, profiles)
   - Data Policies (compliance tags: SOX, GAAP, retention)
   - Lineage & Transformation (upstream/downstream dependencies)
   - Operational Contract (SLAs, freshness, availability)

3. **Data Products**: DAGs update and produce data products
4. **Compliance Tags**: SOX, GAAP, regulatory tracking
5. **Quality Rules**: Uniqueness, referential integrity, custom rules
6. **Data Mesh**: Domain ownership, federated governance

### Future Airflow Parser Integration

These DAGs are designed to be ingested by the DCS Airflow parser (per the design doc):
- Each DAG would create `airflow_dag` capsules in DCS
- Each task would create `airflow_task` capsules
- Dependencies would create `FLOWS_TO` and `CONTAINS` edges
- Metadata visible via DCS API and graph export

---

## Access Information

### Airflow Web UI
- **URL:** http://localhost:8080
- **Username:** admin
- **Password:** admin

### Database Connections

**Airflow Metadata DB:**
```
Host: localhost
Port: 5436
Database: airflow
User: airflow
Password: airflow
```

**Data Layer DB:**
```
Host: localhost
Port: 5435
Database: bronze_db / silver_db
User: postgres
Password: postgres
```

---

## Management Commands

### Start Environment
```bash
cd test_environment
docker-compose up -d
```

### Stop Environment
```bash
cd test_environment
docker-compose down
```

### View Logs
```bash
docker logs dab-airflow -f
```

### List DAGs
```bash
docker exec dab-airflow airflow dags list
```

### Trigger a DAG
```bash
docker exec dab-airflow airflow dags trigger finance_gl_pipeline
```

### Pause/Unpause DAG
```bash
docker exec dab-airflow airflow dags pause finance_gl_pipeline
docker exec dab-airflow airflow dags unpause finance_gl_pipeline
```

---

## Next Steps

### Testing Airflow Parser Integration

To test the Airflow parser (per design doc):

1. **Start DCS Backend:**
   ```bash
   cd backend
   source .venv/bin/activate
   uvicorn src.api.main:app --reload --port 8000
   ```

2. **Run Airflow Ingestion:**
   ```bash
   # Set authentication
   export AIRFLOW_TOKEN=<your_token>

   # Ingest via CLI
   python -m src.cli.main ingest airflow \
     --base-url http://localhost:8080 \
     --instance local-dev \
     --include-paused

   # Or via API
   curl -X POST http://localhost:8000/api/v1/ingest/airflow \
     -H "Content-Type: application/json" \
     -d '{
       "base_url": "http://localhost:8080",
       "instance_name": "local-dev",
       "include_paused": true
     }'
   ```

3. **Query Ingested DAGs:**
   ```bash
   # List Airflow DAG capsules
   curl http://localhost:8000/api/v1/capsules?capsule_type=airflow_dag

   # List Airflow task capsules
   curl http://localhost:8000/api/v1/capsules?capsule_type=airflow_task

   # Export lineage for a DAG
   curl http://localhost:8000/api/v1/graph/export/lineage/urn:dcs:airflow:dag:local-dev:finance_gl_pipeline?format=mermaid
   ```

---

## Design Documentation

This setup implements concepts from:
- **Design Doc:** [docs/design_docs/airflow_integration_design.md](../docs/design_docs/airflow_integration_design.md)
- **Finance Seed Data:** [backend/scripts/README_FINANCE_SEED.md](../backend/scripts/README_FINANCE_SEED.md)

---

**Last Updated:** December 28, 2025
**Maintained By:** Data Platform Team
