# Data Pipeline Test Environment Setup

**Version**: 1.0
**Status**: Active
**Last Updated**: December 2024

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Prerequisites](#prerequisites)
4. [Quick Start](#quick-start)
5. [Components](#components)
6. [Data Flow](#data-flow)
7. [Testing DAB Airflow Integration](#testing-dab-airflow-integration)
8. [Troubleshooting](#troubleshooting)
9. [Appendix](#appendix)

---

## Overview

This test environment provides a complete data pipeline infrastructure for testing the Data Architecture Brain (DAB) Airflow integration. It includes:

- **Apache Airflow**: Orchestrates dbt jobs and data pipelines
- **PostgreSQL**: Two databases for bronze and silver data layers
- **dbt**: Transforms data from bronze to silver layers
- **Sample Data**: Customer and order data for realistic testing

### Purpose

This environment enables:
1. Testing DAB's Airflow ingestion functionality
2. Validating DAG and task capsule creation
3. Verifying lineage tracking across dbt models
4. Demonstrating PII detection and tracking

---

## Architecture

### Infrastructure Components

```
┌─────────────────────────────────────────────────────────────────┐
│                     Test Environment                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────────┐         ┌──────────────────┐             │
│  │   PostgreSQL     │         │   PostgreSQL     │             │
│  │  (Data Layers)   │         │   (Airflow DB)   │             │
│  │                  │         │                  │             │
│  │  - bronze_db     │         │  - airflow       │             │
│  │  - silver_db     │         │                  │             │
│  └────────┬─────────┘         └────────┬─────────┘             │
│           │                            │                        │
│           │                            │                        │
│           │         ┌──────────────────┴─────────┐             │
│           │         │                            │             │
│           │         │      Apache Airflow        │             │
│           │         │                            │             │
│           └────────>│  ┌──────────────────────┐  │             │
│                     │  │   DAG: customer_     │  │             │
│                     │  │   analytics_pipeline │  │             │
│                     │  │                      │  │             │
│                     │  │  - dbt seed          │  │             │
│                     │  │  - dbt run (bronze)  │  │             │
│                     │  │  - dbt test (bronze) │  │             │
│                     │  │  - dbt run (silver)  │  │             │
│                     │  │  - dbt test (silver) │  │             │
│                     │  └──────────────────────┘  │             │
│                     │                            │             │
│                     │  ┌──────────────────────┐  │             │
│                     │  │   DAG: daily_sales_  │  │             │
│                     │  │   summary            │  │             │
│                     │  └──────────────────────┘  │             │
│                     │                            │             │
│                     │  Port: 8080                │             │
│                     └────────────────────────────┘             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Data Layer Architecture

```
Bronze Layer (bronze_db)          Silver Layer (silver_db)
━━━━━━━━━━━━━━━━━━━━━━━          ━━━━━━━━━━━━━━━━━━━━━━━

Sources:                          Dimensional Models:
┌─────────────┐                  ┌─────────────────┐
│ customers   │────┐             │ dim_customers   │
└─────────────┘    │             │ (with metrics)  │
                   │             └─────────────────┘
┌─────────────┐    │
│ orders      │────┼────────────>┌─────────────────┐
└─────────────┘    │             │ fct_orders      │
                   │             │ (aggregated)    │
┌─────────────┐    │             └─────────────────┘
│ order_items │────┘
└─────────────┘                  ┌─────────────────┐
                                 │ int_customer_   │
Staging Models:                  │ orders          │
┌─────────────┐                  └─────────────────┘
│ stg_customers
│ stg_orders
│ stg_order_items
└─────────────┘

Seeds:
┌─────────────┐
│ country_codes
└─────────────┘
```

---

## Prerequisites

### Required Software

- Docker Desktop (or Docker Engine + Docker Compose)
- Minimum 4GB RAM allocated to Docker
- 10GB free disk space

### Ports Required

| Service | Port | Purpose |
|---------|------|---------|
| Airflow Web UI | 8080 | Airflow dashboard |
| PostgreSQL (Data) | 5435 | Bronze/Silver databases |
| PostgreSQL (Airflow) | 5436 | Airflow metadata |

---

## Quick Start

### 1. Start the Environment

```bash
cd test_environment
docker-compose up -d
```

This command will:
- Start PostgreSQL containers (data and Airflow metadata)
- Initialize bronze_db and silver_db with sample data
- Start Airflow and initialize the metadata database
- Create default admin user (username: `admin`, password: `admin`)

### 2. Verify Services are Running

```bash
docker-compose ps
```

Expected output:
```
NAME                    STATUS      PORTS
dab-postgres-data       Up          0.0.0.0:5435->5432/tcp
dab-postgres-airflow    Up          0.0.0.0:5436->5432/tcp
dab-airflow             Up          0.0.0.0:8080->8080/tcp
```

### 3. Access Airflow Web UI

Open browser to: http://localhost:8080

Login credentials:
- **Username**: `admin`
- **Password**: `admin`

### 4. Install dbt in Airflow Container

```bash
docker exec -it dab-airflow bash
pip install dbt-core==1.7.4 dbt-postgres==1.7.4
exit
```

### 5. Enable and Trigger DAGs

In the Airflow UI:
1. Navigate to the DAGs page
2. Toggle the `customer_analytics_pipeline` DAG to **ON**
3. Click the ▶️ (Play) button to trigger a run
4. Monitor the task execution in the Graph view

### 6. Test DAB Ingestion

```bash
# From the backend directory
cd ../backend

# Ingest Airflow metadata
dab ingest airflow \
  --base-url http://localhost:8080 \
  --instance local-test \
  --auth-mode basic_env

# Set credentials (if basic auth is enabled)
export AIRFLOW_USERNAME=admin
export AIRFLOW_PASSWORD=admin
```

### 7. Verify Capsules Created

```bash
# List Airflow DAG capsules
dab capsules --type airflow_dag

# List Airflow task capsules
dab capsules --type airflow_task

# View lineage for a specific DAG
dab lineage --urn "urn:dab:airflow:dag:local-test:customer_analytics_pipeline"
```

---

## Components

### PostgreSQL Databases

#### Bronze Database (bronze_db)

**Port**: 5435
**Database**: bronze_db
**Schema**: bronze

**Tables**:
- `customers`: 10 sample customer records
- `orders`: 15 sample order records
- `order_items`: 16 order line items

**Sample Data**: Pre-loaded with realistic customer and order data including PII fields (email, phone, address).

#### Silver Database (silver_db)

**Port**: 5435 (same container)
**Database**: silver_db
**Schema**: silver

**Tables** (created by dbt):
- `dim_customers`: Customer dimension with aggregated metrics
- `fct_orders`: Orders fact table with line item aggregates
- `int_customer_orders`: Intermediate joined data

### Apache Airflow

**Version**: 2.8.0
**Executor**: LocalExecutor
**Port**: 8080

**DAGs**:

1. **customer_analytics_pipeline**
   - **Schedule**: Daily at 2 AM
   - **Tags**: customer, analytics, dbt, bronze, silver
   - **Tasks**:
     - `pipeline_start`: Initialize pipeline
     - `dbt_deps`: Install dbt dependencies
     - `dbt_seed`: Load reference data
     - `dbt_run_bronze`: Run bronze layer models
     - `dbt_test_bronze`: Test bronze models
     - `dbt_run_silver`: Run silver layer models
     - `dbt_test_silver`: Test silver models
     - `dbt_docs_generate`: Generate documentation
     - `pipeline_complete`: Finalize pipeline

2. **daily_sales_summary**
   - **Schedule**: Daily at 3 AM
   - **Tags**: sales, reporting, daily
   - **Dependencies**: Waits for `customer_analytics_pipeline` to complete
   - **Tasks**:
     - `summary_start`: Initialize
     - `wait_for_customer_pipeline`: External task sensor
     - `generate_report`: Create sales report
     - `summary_complete`: Finalize

### dbt Project

**Name**: customer_analytics
**Version**: 1.0.0
**Profile**: customer_analytics

**Models**:

#### Bronze Layer (Staging)
- `stg_customers`: Cleaned customer data
- `stg_orders`: Cleaned order data
- `stg_order_items`: Cleaned order line items

#### Silver Layer (Dimensional)
- `int_customer_orders`: Intermediate model joining customers and orders
- `dim_customers`: Customer dimension with metrics (total_orders, total_spent, avg_order_value)
- `fct_orders`: Orders fact table with aggregated line items

**Seeds**:
- `country_codes`: Reference data for country information

---

## Data Flow

### Pipeline Execution Flow

```
1. Pipeline Start
   │
   ├─> 2. Install dbt Dependencies
   │
   ├─> 3. Load Seeds (country_codes)
   │
   ├─> 4. Run Bronze Layer Models
   │      ├─> stg_customers
   │      ├─> stg_orders
   │      └─> stg_order_items
   │
   ├─> 5. Test Bronze Models
   │      ├─> Source data tests
   │      └─> Staging model tests
   │
   ├─> 6. Run Silver Layer Models
   │      ├─> int_customer_orders
   │      ├─> dim_customers
   │      └─> fct_orders
   │
   ├─> 7. Test Silver Models
   │      ├─> Dimensional model tests
   │      └─> Referential integrity tests
   │
   ├─> 8. Generate Documentation
   │
   └─> 9. Pipeline Complete
```

### Data Lineage

```
bronze.customers (source)
    └─> stg_customers (view)
        └─> dim_customers (table)
            └─> Used by analytics queries

bronze.orders (source)
    └─> stg_orders (view)
        ├─> int_customer_orders (view)
        │   └─> dim_customers (table)
        └─> fct_orders (table)
            └─> Used by sales reports

bronze.order_items (source)
    └─> stg_order_items (view)
        └─> fct_orders (table)
            └─> Used by sales reports
```

### DAG Dependencies

```
customer_analytics_pipeline (2 AM daily)
    │
    └─> Triggers: dbt transformations
        │
        └─> Completes: pipeline_complete task
            │
            └─> Triggers: daily_sales_summary (3 AM daily)
                │
                └─> Generates: Sales reports
```

---

## Testing DAB Airflow Integration

### Test Scenario 1: Basic Ingestion

**Objective**: Verify DAB can ingest Airflow metadata and create capsules.

```bash
# 1. Start the test environment
cd test_environment
docker-compose up -d

# 2. Wait for Airflow to initialize (2-3 minutes)
docker logs dab-airflow -f

# 3. Enable DAGs in Airflow UI
# Navigate to http://localhost:8080
# Toggle customer_analytics_pipeline to ON

# 4. Run DAB ingestion
cd ../backend
dab ingest airflow \
  --base-url http://localhost:8080 \
  --instance local-test

# 5. Verify capsules created
dab capsules --type airflow_dag
# Expected: 2 DAG capsules (customer_analytics_pipeline, daily_sales_summary)

dab capsules --type airflow_task
# Expected: 11 task capsules across both DAGs
```

**Expected Results**:
- 2 DAG capsules created
- 11 task capsules created
- Lineage edges connecting tasks within DAGs
- Tags preserved from Airflow DAG definitions

### Test Scenario 2: DAG Filtering

**Objective**: Test DAG filtering using regex patterns.

```bash
# Ingest only customer-related DAGs
dab ingest airflow \
  --base-url http://localhost:8080 \
  --instance local-test \
  --dag-regex "customer.*"

# Verify only customer_analytics_pipeline is ingested
dab capsules --type airflow_dag
# Expected: 1 DAG capsule
```

### Test Scenario 3: Lineage Verification

**Objective**: Verify task lineage within DAGs is correctly captured.

```bash
# Get lineage for customer_analytics_pipeline
dab lineage \
  --urn "urn:dab:airflow:dag:local-test:customer_analytics_pipeline" \
  --direction downstream

# Verify lineage includes:
# - pipeline_start -> dbt_deps
# - dbt_deps -> dbt_seed
# - dbt_seed -> dbt_run_bronze
# - dbt_run_bronze -> dbt_test_bronze
# - dbt_test_bronze -> dbt_run_silver
# - dbt_run_silver -> dbt_test_silver
# - dbt_test_silver -> dbt_docs_generate
# - dbt_docs_generate -> pipeline_complete
```

### Test Scenario 4: Secret Redaction

**Objective**: Verify database credentials and secrets are not persisted.

```bash
# Run ingestion with authentication
export AIRFLOW_USERNAME=admin
export AIRFLOW_PASSWORD=admin

dab ingest airflow \
  --base-url http://localhost:8080 \
  --instance local-test \
  --auth-mode basic_env

# Check ingestion job config
dab stats --recent

# Verify config does NOT contain:
# - AIRFLOW_PASSWORD value
# - Any raw credential values
# Only environment variable names should be present
```

### Test Scenario 5: Cross-DAG Dependencies

**Objective**: Verify external task dependencies are captured.

```bash
# Get lineage for daily_sales_summary
dab lineage \
  --urn "urn:dab:airflow:dag:local-test:daily_sales_summary" \
  --direction upstream

# Should show dependency on customer_analytics_pipeline via
# wait_for_customer_pipeline task
```

### Test Scenario 6: PII Detection

**Objective**: Verify PII fields in dbt models are detected after ingestion.

```bash
# Ingest dbt project (if dbt manifest integration exists)
# Or verify PII tagging from dbt meta tags

dab pii-exposure

# Expected PII fields:
# - customers.email (email)
# - customers.phone (phone)
# - customers.address (address)
# - orders.shipping_address (address)
```

---

## Troubleshooting

### Common Issues

#### 1. Airflow Container Fails to Start

**Symptom**: `dab-airflow` container exits immediately

**Diagnosis**:
```bash
docker logs dab-airflow
```

**Solutions**:
- Ensure PostgreSQL containers are healthy first
- Check port 8080 is not already in use
- Increase Docker memory allocation to 4GB+

#### 2. dbt Commands Fail in Airflow

**Symptom**: DAG tasks fail with "dbt: command not found"

**Solution**:
```bash
# Install dbt in Airflow container
docker exec -it dab-airflow bash
pip install dbt-core==1.7.4 dbt-postgres==1.7.4
exit

# Restart Airflow
docker-compose restart airflow
```

#### 3. Database Connection Errors

**Symptom**: dbt cannot connect to PostgreSQL

**Diagnosis**:
```bash
# Check PostgreSQL is running
docker-compose ps postgres-data

# Test connection from Airflow
docker exec -it dab-airflow bash
psql -h postgres-data -U postgres -d bronze_db
```

**Solution**:
- Verify environment variables in docker-compose.yml
- Check profiles.yml uses correct host (`postgres-data` inside container)

#### 4. DAB Ingestion Returns No DAGs

**Symptom**: `dab capsules --type airflow_dag` returns empty

**Diagnosis**:
1. Check Airflow is accessible:
   ```bash
   curl http://localhost:8080/api/v1/health
   ```
2. Check DAGs are enabled in Airflow UI
3. Check Airflow logs:
   ```bash
   docker logs dab-airflow | grep ERROR
   ```

**Solution**:
- Enable DAGs in Airflow UI (toggle switch)
- Verify Airflow REST API is enabled
- Check authentication settings match

#### 5. Port Conflicts

**Symptom**: "bind: address already in use"

**Solution**:
```bash
# Check what's using the ports
lsof -i :8080  # Airflow
lsof -i :5435  # PostgreSQL data
lsof -i :5436  # PostgreSQL Airflow

# Option 1: Stop conflicting services
# Option 2: Change ports in docker-compose.yml
```

### Reset Environment

To completely reset the test environment:

```bash
# Stop and remove all containers
docker-compose down -v

# Remove all volumes (deletes data)
docker volume rm test_environment_postgres-data-volume
docker volume rm test_environment_postgres-airflow-volume
docker volume rm test_environment_airflow-logs

# Restart fresh
docker-compose up -d
```

---

## Appendix

### A. Sample Data Details

**Customers**: 10 records
- Customer IDs: 1-10
- Locations: Various US cities
- All records include PII (email, phone, address)

**Orders**: 15 records
- Order IDs: 101-115
- Date range: January - April 2024
- Statuses: completed, shipped, processing
- Payment methods: credit_card, paypal, debit_card

**Order Items**: 16 records
- Product IDs: 501-516
- Products: Tech equipment (laptops, monitors, accessories)
- Price range: $25 - $450

### B. URN Patterns

**Airflow DAGs**:
```
urn:dab:airflow:dag:local-test:customer_analytics_pipeline
urn:dab:airflow:dag:local-test:daily_sales_summary
```

**Airflow Tasks**:
```
urn:dab:airflow:task:local-test:customer_analytics_pipeline.pipeline_start
urn:dab:airflow:task:local-test:customer_analytics_pipeline.dbt_deps
urn:dab:airflow:task:local-test:customer_analytics_pipeline.dbt_seed
...
```

**dbt Models** (if dbt integration is added):
```
urn:dab:dbt:model:customer_analytics.bronze:stg_customers
urn:dab:dbt:model:customer_analytics.silver:dim_customers
urn:dab:dbt:model:customer_analytics.silver:fct_orders
```

### C. Environment Variables

**Airflow Container**:
```env
BRONZE_DB_HOST=postgres-data
BRONZE_DB_PORT=5432
BRONZE_DB_NAME=bronze_db
BRONZE_DB_USER=postgres
BRONZE_DB_PASSWORD=postgres

SILVER_DB_HOST=postgres-data
SILVER_DB_PORT=5432
SILVER_DB_NAME=silver_db
SILVER_DB_USER=postgres
SILVER_DB_PASSWORD=postgres

DBT_PROJECT_DIR=/opt/airflow/dbt_project
DBT_PROFILES_DIR=/opt/airflow/dbt_project
```

**DAB Ingestion**:
```env
AIRFLOW_USERNAME=admin
AIRFLOW_PASSWORD=admin
```

### D. Useful Commands

**Docker Management**:
```bash
# View logs for specific service
docker logs dab-airflow -f
docker logs dab-postgres-data -f

# Execute command in container
docker exec -it dab-airflow bash
docker exec -it dab-postgres-data psql -U postgres

# Restart specific service
docker-compose restart airflow
docker-compose restart postgres-data
```

**Airflow CLI** (inside container):
```bash
# List DAGs
airflow dags list

# Trigger DAG run
airflow dags trigger customer_analytics_pipeline

# List tasks in DAG
airflow tasks list customer_analytics_pipeline

# Test specific task
airflow tasks test customer_analytics_pipeline dbt_run_bronze 2024-01-01
```

**dbt CLI** (inside container):
```bash
cd /opt/airflow/dbt_project

# List models
dbt ls

# Run specific model
dbt run --select stg_customers

# Test specific model
dbt test --select stg_customers

# Generate and view docs
dbt docs generate
dbt docs serve --port 8081
```

**PostgreSQL Queries**:
```bash
# Connect to bronze_db
docker exec -it dab-postgres-data psql -U postgres -d bronze_db

# List tables
\dt bronze.*

# Query customers
SELECT COUNT(*) FROM bronze.customers;

# Check silver layer tables
\c silver_db
\dt silver.*
```

### E. Performance Considerations

**Expected Execution Times**:
- Environment startup: 2-3 minutes
- Customer analytics pipeline: 1-2 minutes
- DAB ingestion: 5-10 seconds
- dbt model runs: 10-30 seconds

**Resource Usage**:
- Memory: ~2GB total
- CPU: Minimal during idle
- Disk: ~1GB for containers and volumes

### F. Integration with DAB

**Recommended Test Flow**:

1. **Initial Setup**:
   ```bash
   docker-compose up -d
   # Wait 3 minutes for initialization
   ```

2. **Run Pipeline**:
   - Enable DAGs in Airflow UI
   - Trigger `customer_analytics_pipeline`
   - Wait for completion (~2 minutes)

3. **Ingest into DAB**:
   ```bash
   dab ingest airflow --base-url http://localhost:8080 --instance local-test
   ```

4. **Verify Capsules**:
   ```bash
   dab capsules --type airflow_dag
   dab capsules --type airflow_task
   ```

5. **Explore Lineage**:
   ```bash
   dab lineage --urn "urn:dab:airflow:dag:local-test:customer_analytics_pipeline"
   ```

6. **Check PII Detection**:
   ```bash
   dab pii-exposure
   ```

---

## Next Steps

After setting up this test environment, you can:

1. **Test Airflow Integration**: Follow the test scenarios in the "Testing DAB Airflow Integration" section

2. **Extend the Pipeline**: Add more dbt models or Airflow DAGs to test complex scenarios

3. **Test dbt Integration**: If DAB adds dbt ingestion, this environment is ready for testing dbt manifest ingestion alongside Airflow

4. **Performance Testing**: Scale up the data volumes to test DAB performance with larger datasets

5. **API Testing**: Use the running Airflow instance to test DAB's REST API ingestion endpoints

---

*Last Updated: December 2024*
*Environment Version: 1.0*
*Maintained by: Data Engineering Team*
