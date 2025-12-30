# Airflow Integration User Guide

**Version:** 1.0
**Last Updated:** December 2024
**Audience:** Data Engineers and Data Architects

---

## ⚠️ Integration Status

**Current Status:** Active Integration

This guide describes how to integrate Apache Airflow with the Data Control System (DCS).

### Available Now ✅
- **Automatic DAG ingestion**: Import DAGs and tasks from Airflow via REST API
- **DAG filtering**: Include/exclude DAGs by regex, allowlist, or denylist
- **Authentication support**: Bearer token or basic auth
- **Capsule linking**: Automatically track which DAGs produce/consume data
- **Lineage tracking**: Capsule-level data flow visualization
- **Quality integration**: Call DCS APIs from Airflow tasks for validation

### Planned for Future Release 🚧
- Real-time task execution monitoring in DCS UI
- Task-level impact analysis (Phase 8)
- Visual DAG dependency explorer in DCS web interface
- Automated lineage extraction from task SQL code

### Key Command

```bash
# Ingest Airflow DAGs and tasks
dcs ingest airflow --base-url https://airflow.example.com
```

This guide shows you how to use the `dcs ingest airflow` command and integrate Airflow with DCS for unified data governance.

---

## Table of Contents

1. [Overview](#overview)
2. [Getting Started](#getting-started)
3. [Connecting Airflow to DCS](#connecting-airflow-to-dcs)
4. [Managing DAGs](#managing-dags)
5. [Monitoring Tasks](#monitoring-tasks)
6. [Data Lineage Integration](#data-lineage-integration)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)
9. [Examples](#examples)

---

## Overview

### What is Airflow Integration?

Data Control System (DCS) works alongside Apache Airflow to provide:

- **Lineage Tracking**: Document and visualize data flows managed by Airflow DAGs
- **Impact Analysis**: Understand how schema changes affect data consumed/produced by Airflow
- **Unified Governance**: Apply DCS quality rules to data processed by Airflow tasks
- **Metadata Linking**: Connect Airflow DAGs and tasks to DCS capsules
- **Quality Integration**: Call DCS validation APIs from Airflow tasks

> **Note:** Full bidirectional integration (automatic DAG sync, task monitoring) is planned for a future release. This guide focuses on currently available integration patterns.

### Architecture

**Current Integration Pattern:**

```
┌─────────────────────┐
│   Airflow Server    │
│  - DAG Execution    │
│  - Task Scheduling  │
└──────────┬──────────┘
           │
           │ You document relationships
           ↓ via metadata and annotations
┌─────────────────────┐
│   DCS System        │
│  - Capsule Tracking │
│  - Lineage Graph    │
│  - Quality Rules    │
└──────────┬──────────┘
           │
           ↓
┌─────────────────────┐
│   Data Sources      │
│  - Snowflake        │
│  - PostgreSQL       │
│  - S3 / Data Lake   │
└─────────────────────┘
```

Both systems read/write from the same data sources. You document their relationships in:
- Capsule metadata (which Airflow DAG manages this data)
- DAG code annotations (which DCS capsules are used)
- Lineage is tracked at the capsule level (table/dataset)

### Key Capabilities

| Feature | Status | Description |
|---------|--------|-------------|
| **Metadata Linking** | ✅ Available | Link Airflow DAGs to DCS capsules via metadata |
| **Lineage Visualization** | ✅ Available | Visualize capsule-level data flows |
| **Quality Integration** | ✅ Available | Call DCS APIs from Airflow Python tasks |
| **Manual Documentation** | ✅ Available | Document data flows in DAG code |
| **Impact Analysis** | ✅ Available | Capsule-level impact (table changes) |
| **Task Monitoring** | 🚧 Planned | Real-time Airflow task status in DCS UI |
| **DAG Auto-Discovery** | 🚧 Planned | Automatic sync of Airflow DAGs to DCS |
| **Task-Level Impact** | 🚧 Planned | Which Airflow tasks are affected by changes |

---

## Getting Started

### Prerequisites

Before integrating Airflow with DCS, ensure you have:

- ✅ Apache Airflow 2.0+ installed and running
- ✅ Airflow REST API enabled
- ✅ Network connectivity between DCS and Airflow
- ✅ Airflow credentials (username/password or token)
- ✅ DCS backend deployed and accessible

### System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| Airflow Version | 2.0.0 | 2.7.0+ |
| Python | 3.8 | 3.10+ |
| Network Latency | < 500ms | < 100ms |
| Airflow API | Enabled | Enabled with auth |

---

## Connecting Airflow to DCS

### Step 1: Enable Airflow REST API

Ensure the Airflow REST API is enabled in your `airflow.cfg`:

```ini
[api]
auth_backend = airflow.api.auth.backend.basic_auth
```

Or set via environment variable:

```bash
export AIRFLOW__API__AUTH_BACKEND=airflow.api.auth.backend.basic_auth
```

### Step 2: Configure DCS Connection

#### Option A: Using Environment Variables

```bash
# Airflow connection settings
export AIRFLOW_URL=http://airflow.yourcompany.com:8080
export AIRFLOW_USERNAME=admin
export AIRFLOW_PASSWORD=your_secure_password

# Optional: Authentication token (instead of username/password)
export AIRFLOW_API_TOKEN=your_api_token
```

#### Option B: Using Configuration File

Create or edit `config/airflow.yaml`:

```yaml
airflow:
  url: http://airflow.yourcompany.com:8080
  auth:
    type: basic  # or 'token'
    username: admin
    password: ${AIRFLOW_PASSWORD}  # Use env var for security
    # token: ${AIRFLOW_API_TOKEN}  # Alternative to username/password

  sync:
    enabled: true
    interval_minutes: 5  # How often to sync DAGs
    include_paused: false  # Whether to sync paused DAGs

  monitoring:
    enabled: true
    check_interval_seconds: 30  # How often to check task status
```

### Step 3: Test Connection

Test the Airflow connection using the DCS CLI:

```bash
# Test connectivity and list DAGs (dry run)
export AIRFLOW_USERNAME=admin
export AIRFLOW_PASSWORD=your_password

dcs ingest airflow \
  --base-url http://airflow.yourcompany.com:8080 \
  --auth-mode basic_env

# Expected output:
# ✓ Connected to Airflow at http://airflow.yourcompany.com:8080
# ✓ Found 42 DAGs
# ✓ Ingested 42 DAGs with 156 tasks
# ✓ Created X capsules
```

**Alternative: Test with curl first**

```bash
# Verify Airflow API is accessible
curl -u ${AIRFLOW_USERNAME}:${AIRFLOW_PASSWORD} \
  ${AIRFLOW_URL}/api/v1/health

# Expected output:
# {
#   "metadatabase": {"status": "healthy"},
#   "scheduler": {"status": "healthy"}
# }
```

### Step 4: Initial Sync

Perform an initial ingestion of all Airflow DAGs:

```bash
# Basic ingestion (no auth)
dcs ingest airflow --base-url http://airflow.yourcompany.com:8080

# With authentication
export AIRFLOW_USERNAME=admin
export AIRFLOW_PASSWORD=your_password

dcs ingest airflow \
  --base-url http://airflow.yourcompany.com:8080 \
  --auth-mode basic_env

# With DAG filtering
dcs ingest airflow \
  --base-url http://airflow.yourcompany.com:8080 \
  --auth-mode basic_env \
  --dag-regex "^production_.*" \
  --include-paused

# Expected output:
# ✓ Connected to Airflow at http://airflow.yourcompany.com:8080
# ✓ Found 42 DAGs (15 matched filter)
# ✓ Ingested 15 DAGs with 67 tasks
# ✓ Created 23 capsule references
```

**What gets ingested:**
- DAG metadata (ID, description, schedule, owner, tags)
- Task metadata (ID, operator type, dependencies)
- Data dependencies (inferred from task connections and SQL)

---

## Managing DAGs

### Viewing DAGs

> **Note:** The DCS web UI for viewing Airflow DAGs is planned for a future release.

#### Via Airflow Web UI

For now, view DAGs directly in the Airflow web interface:

1. Open your Airflow web UI: `http://airflow.yourcompany.com:8080`
2. Navigate to **DAGs** page
3. View DAG details, task dependencies, and execution history

#### Via Airflow API

Query DAG information programmatically:

```bash
# List all DAGs
curl -u ${AIRFLOW_USERNAME}:${AIRFLOW_PASSWORD} \
  ${AIRFLOW_URL}/api/v1/dags | jq '.dags[] | {dag_id, is_paused, schedule_interval}'

# Get specific DAG details
curl -u ${AIRFLOW_USERNAME}:${AIRFLOW_PASSWORD} \
  ${AIRFLOW_URL}/api/v1/dags/user_data_pipeline | jq .

# List tasks in a DAG
curl -u ${AIRFLOW_USERNAME}:${AIRFLOW_PASSWORD} \
  ${AIRFLOW_URL}/api/v1/dags/user_data_pipeline/tasks | jq '.tasks[] | .task_id'
```

### DAG Details

In the Airflow web UI, click on any DAG to view:

- **Overview**: Description, schedule, owner
- **Graph View**: Visual task dependency graph
- **Tree View**: Historical execution timeline
- **Code**: DAG definition source code
- **Runs**: Execution history with status
- **Logs**: Task execution logs

### Re-syncing DAGs

Re-run ingestion to update DAG metadata after changes:

```bash
# Re-sync all DAGs
dcs ingest airflow \
  --base-url http://airflow.yourcompany.com:8080 \
  --auth-mode basic_env

# Sync specific DAGs only
dcs ingest airflow \
  --base-url http://airflow.yourcompany.com:8080 \
  --auth-mode basic_env \
  --dag-allowlist "user_pipeline,order_pipeline,analytics_pipeline"

# Clean up deleted DAGs
dcs ingest airflow \
  --base-url http://airflow.yourcompany.com:8080 \
  --auth-mode basic_env \
  --cleanup-orphans
```

**When to re-sync:**
- After adding/removing DAGs in Airflow
- After modifying DAG metadata (description, schedule, tags)
- After changing task dependencies
- After updating task operators or connections

**Automation:** Set up a scheduled job to sync regularly:

```bash
# Cron job: sync every hour
0 * * * * dcs ingest airflow --base-url http://airflow.company.com:8080 --auth-mode basic_env
```

### DAG Metadata

DCS captures the following metadata for each DAG:

| Field | Description | Source |
|-------|-------------|--------|
| **DAG ID** | Unique identifier | Airflow |
| **Description** | Human-readable description | DAG docstring |
| **Schedule** | Cron expression or preset | Airflow schedule_interval |
| **Owner** | Team/person responsible | DAG owner field |
| **Tags** | Categorization labels | Airflow tags |
| **Is Paused** | Whether DAG is active | Airflow state |
| **Capsules** | Input/output data capsules | DCS lineage detection |

---

## Monitoring Tasks

### Task Execution Status

#### Real-Time Monitoring

> **Note:** Real-time task monitoring in the DCS dashboard is planned for a future release.

**Current approach:** Monitor tasks directly in Airflow:

1. **Airflow Web UI**: Navigate to your Airflow server at `http://airflow.yourcompany.com:8080`
2. **View DAGs**: See all DAGs with their current execution status
3. **Task Status**: Click into any DAG to see individual task states:
   - 🟢 **Running**: Task is currently executing
   - ✅ **Success**: Task completed successfully
   - ❌ **Failed**: Task failed with error
   - ⏸️ **Queued**: Waiting to execute
   - ⏭️ **Skipped**: Skipped due to conditions
   - ⏱️ **Scheduled**: Scheduled for future execution

**Or use the Airflow API:**

```bash
# Get recent task runs for a DAG
curl -u ${AIRFLOW_USERNAME}:${AIRFLOW_PASSWORD} \
  "${AIRFLOW_URL}/api/v1/dags/your_dag/dagRuns?limit=5" | \
  jq '.dag_runs[] | {execution_date, state, start_date, end_date}'
```

### Task Filtering

> **Note:** DCS CLI for task filtering is planned for a future release.

**Current approach:** Use Airflow API to filter tasks:

```bash
# Get task instances by status
curl -u ${AIRFLOW_USERNAME}:${AIRFLOW_PASSWORD} \
  "${AIRFLOW_URL}/api/v1/dags/~/dagRuns/~/taskInstances?state=failed" | \
  jq '.task_instances[] | {dag_id, task_id, state, start_date}'

# Get task instances for a specific DAG
curl -u ${AIRFLOW_USERNAME}:${AIRFLOW_PASSWORD} \
  "${AIRFLOW_URL}/api/v1/dags/user_data_pipeline/dagRuns/~/taskInstances" | \
  jq '.task_instances[] | {task_id, state, duration}'

# Filter by date range (last 10 runs)
curl -u ${AIRFLOW_USERNAME}:${AIRFLOW_PASSWORD} \
  "${AIRFLOW_URL}/api/v1/dags/user_data_pipeline/dagRuns?limit=10" | \
  jq '.dag_runs[] | {execution_date, state}'
```

**To link tasks with DCS capsules**, document the relationship in your DAG code (see examples below).

### Task Alerts

> **Note:** DCS-based alerting is planned for a future release.

**Current approach:** Use Airflow's native alerting:

**1. Email Alerts (Built-in)**

Configure in your DAG default_args:

```python
from airflow import DAG
from datetime import datetime

default_args = {
    'owner': 'data-team',
    'email': ['data-alerts@company.com'],
    'email_on_failure': True,
    'email_on_retry': False,
    'email_on_success': False,
}

with DAG(
    dag_id='user_pipeline',
    default_args=default_args,
    start_date=datetime(2024, 1, 1),
) as dag:
    # Your tasks here
    pass
```

**2. Slack Alerts (via Callback)**

```python
from airflow.providers.slack.operators.slack_webhook import SlackWebhookOperator

def task_fail_slack_alert(context):
    slack_msg = f"""
    :red_circle: Task Failed
    *Task*: {context.get('task_instance').task_id}
    *DAG*: {context.get('task_instance').dag_id}
    *Execution Time*: {context.get('execution_date')}
    *Log*: {context.get('task_instance').log_url}
    """
    SlackWebhookOperator(
        task_id='slack_alert',
        slack_webhook_conn_id='slack_webhook',
        message=slack_msg
    ).execute(context=context)

# Use in DAG:
default_args = {
    'on_failure_callback': task_fail_slack_alert,
}
```

**3. Custom Webhooks**

```python
import requests

def custom_failure_callback(context):
    # Call your monitoring system
    requests.post(
        'https://your-monitoring-system.com/webhook',
        json={
            'dag_id': context['dag'].dag_id,
            'task_id': context['task'].task_id,
            'execution_date': str(context['execution_date']),
            'exception': str(context.get('exception')),
        }
    )

default_args = {
    'on_failure_callback': custom_failure_callback,
}
```

---

## Data Lineage Integration

### How Lineage Works

> **Note:** Automatic lineage detection from Airflow task code is planned for a future release.

**Current approach:** DCS tracks lineage at the **capsule level** (tables/datasets), not at the Airflow task level.

**What DCS does:**
1. **Ingests capsules** from your data sources (Snowflake, PostgreSQL, etc.)
2. **Parses SQL transformations** to detect which capsules depend on others
3. **Builds a lineage graph** showing capsule-to-capsule data flows
4. **Tracks column-level dependencies** within SQL transformations

**What you document manually:**
- Which Airflow DAGs/tasks produce or consume each capsule
- Task schedules and dependencies
- Data quality checks performed by tasks

**Example workflow:**

1. **Airflow task writes data** → Snowflake table `users_staging`
2. **You ingest the capsule**: `dcs ingest --source-type snowflake --capsule-name users_staging`
3. **You add metadata**: Link the capsule to the Airflow task that created it
4. **DCS tracks lineage**: When `users_staging` is transformed into `users_analytics`, DCS automatically detects that relationship

### Planned Operator Support (Future)

When automatic DAG sync is implemented, DCS will support:

| Operator | Planned Support | Notes |
|----------|-----------------|-------|
| `PostgresOperator` | Full (SQL parsing) | Automatic lineage from SQL |
| `SnowflakeOperator` | Full (SQL parsing) | Automatic lineage from SQL |
| `PythonOperator` | Manual annotation required | Custom Python logic |
| `S3ToRedshiftOperator` | Automatic detection | Source → target mapping |
| `BashOperator` | Not supported | Cannot parse shell scripts |

### Viewing Task Lineage

#### Via DCS Lineage Graph

Use the existing DCS lineage commands to visualize data flows:

```bash
# Export lineage graph for a capsule
dcs lineage export --output-format mermaid > lineage.md

# Export as DOT format for Graphviz
dcs lineage export --output-format dot | dot -Tpng > lineage.png

# Export as JSON for programmatic access
dcs lineage export --output-format json > lineage.json
```

The lineage graph will show:
- Upstream capsules (data sources)
- Downstream capsules (data consumers)
- Transformation relationships

#### Linking Capsules to Airflow Tasks

Document which Airflow tasks interact with each capsule using metadata:

```bash
# During ingestion
dcs ingest --source-type snowflake \
  --capsule-name "users_staging" \
  --metadata "produced_by=user_etl_dag.extract_users" \
  --metadata "consumed_by=analytics_dag.compute_metrics"
```

#### Via Web UI (Planned)

> **Note:** A dedicated Tasks tab in the DCS web UI is planned for a future release. It will show:
> - Which Airflow tasks read from each capsule
> - Which Airflow tasks write to each capsule
> - Task execution schedules and status

### Manual Lineage Annotation

For tasks where automatic detection doesn't work (e.g., `PythonOperator`), annotate lineage manually:

```python
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime

def process_user_data(**context):
    # Your Python logic here
    pass

with DAG(
    dag_id='user_processing',
    start_date=datetime(2024, 1, 1),
    schedule_interval='@daily'
) as dag:

    process_task = PythonOperator(
        task_id='process_users',
        python_callable=process_user_data,

        # DCS lineage annotation
        doc_md="""
        **DCS Lineage:**
        - Reads: users_raw, user_profiles
        - Writes: users_processed
        - Transformation: Join + Aggregate
        """
    )
```

DCS will parse the `doc_md` field and extract lineage information.

---

## Best Practices

### 1. DAG Naming Conventions

Use clear, consistent naming:

```python
# Good
dag_id = 'finance_daily_revenue_calculation'
dag_id = 'marketing_weekly_campaign_analysis'
dag_id = 'ops_hourly_system_health_check'

# Bad
dag_id = 'dag1'
dag_id = 'my_dag'
dag_id = 'test'
```

### 2. Meaningful Descriptions

Add descriptions to DAGs:

```python
with DAG(
    dag_id='user_data_pipeline',
    description='Daily pipeline to process user data from raw to analytics-ready format',
    doc_md="""
    ## User Data Pipeline

    This pipeline:
    1. Extracts user data from production database
    2. Cleans and validates data
    3. Joins with profile information
    4. Loads into analytics warehouse

    **Owner:** Data Engineering Team
    **SLA:** Complete by 6 AM EST
    """,
    start_date=datetime(2024, 1, 1),
    schedule_interval='@daily'
) as dag:
    pass
```

### 3. Use Tags

Categorize DAGs with tags:

```python
with DAG(
    dag_id='revenue_reporting',
    tags=['finance', 'production', 'daily'],
    ...
) as dag:
    pass
```

### 4. Set Owners

Always specify an owner:

```python
with DAG(
    dag_id='marketing_pipeline',
    default_args={
        'owner': 'marketing-team',
        'email': ['marketing-data@company.com'],
        'email_on_failure': True,
    },
    ...
) as dag:
    pass
```

### 5. Document Data Dependencies

Use task documentation to describe data flows:

```python
extract_users = PostgresOperator(
    task_id='extract_users',
    sql='SELECT * FROM users WHERE updated_at > {{ prev_ds }}',
    doc_md="""
    Extracts user records that were updated since last run.

    **Input:** production.users table
    **Output:** users_raw capsule
    **Frequency:** Daily at 2 AM
    """,
)
```

### 6. Implement Idempotency

Ensure tasks can be safely retried:

```sql
-- Good: Idempotent insert
INSERT INTO target_table
SELECT * FROM source_table
WHERE date = '{{ ds }}'
ON CONFLICT (id) DO UPDATE SET ...

-- Bad: Non-idempotent insert
INSERT INTO target_table
SELECT * FROM source_table
```

### 7. Set Appropriate Timeouts

Configure task timeouts:

```python
process_data = PythonOperator(
    task_id='process_data',
    python_callable=process_fn,
    execution_timeout=timedelta(hours=2),  # Prevent hanging tasks
    retries=3,
    retry_delay=timedelta(minutes=5),
)
```

---

## Troubleshooting

### Connection Issues

**Problem:** Cannot connect to Airflow

**Solutions:**

1. **Verify Airflow is running:**
   ```bash
   curl http://airflow.yourcompany.com:8080/health
   ```

2. **Check credentials:**
   ```bash
   # Test with curl
   curl -u admin:password http://airflow.yourcompany.com:8080/api/v1/dags
   ```

3. **Verify network connectivity:**
   ```bash
   # From DCS server
   ping airflow.yourcompany.com
   telnet airflow.yourcompany.com 8080
   ```

4. **Check DCS logs:**
   ```bash
   docker logs dcs-backend | grep airflow
   ```

### Sync Issues

**Problem:** DAG ingestion fails or returns unexpected results

**Solutions:**

1. **Verify Airflow API access:**
   ```bash
   # Test API connectivity with curl first
   curl -u ${AIRFLOW_USERNAME}:${AIRFLOW_PASSWORD} \
     ${AIRFLOW_URL}/api/v1/dags | jq '.dags | length'

   # If successful, try DCS ingestion with increased verbosity
   export LOG_LEVEL=DEBUG
   dcs ingest airflow \
     --base-url ${AIRFLOW_URL} \
     --auth-mode basic_env
   ```

2. **Check authentication credentials:**
   ```bash
   # Verify environment variables are set
   echo $AIRFLOW_USERNAME
   echo $AIRFLOW_PASSWORD

   # Try with explicit token instead
   export AIRFLOW_TOKEN=your_bearer_token
   dcs ingest airflow \
     --base-url ${AIRFLOW_URL} \
     --auth-mode bearer_env
   ```

3. **Check Airflow API permissions:**
   - Ensure user has `can_read` permission on DAGs
   - Check Airflow RBAC role configuration
   - In Airflow UI: Security → List Users → Check user roles

4. **Review DCS backend logs:**
   ```bash
   # Check for ingestion errors
   docker logs dcs-backend --tail 100 | grep -i "airflow\|ingest"

   # Or if running locally
   tail -f logs/dcs-backend.log | grep -i airflow
   ```

5. **Increase timeout for slow Airflow APIs:**
   ```bash
   dcs ingest airflow \
     --base-url ${AIRFLOW_URL} \
     --auth-mode basic_env \
     --timeout 60.0
   ```

### Lineage Detection Issues

**Problem:** Lineage not detected for certain tasks

**Solutions:**

1. **Verify operator support:**
   - Check if operator is in supported list (see table above)
   - Use manual annotation for unsupported operators (see examples below)

2. **Check SQL syntax:**
   - Ensure SQL queries are valid and parseable
   - Avoid dynamic SQL when possible
   - Use explicit table references: `SELECT * FROM schema.table`

3. **Enable debug logging:**
   ```bash
   # Set environment variable for debug logging
   export LOG_LEVEL=DEBUG

   # Restart DCS backend to apply
   docker restart dcs-backend

   # Re-ingest capsule to see detailed logs
   dcs ingest --source-type snowflake --capsule-name your_capsule
   ```

4. **Review lineage detection logs:**
   ```bash
   # Check backend logs for lineage detection
   docker logs dcs-backend --tail 200 | grep -i "lineage\|parser"

   # Look for parsing errors
   docker logs dcs-backend | grep -i "error.*sql\|parse.*failed"
   ```

5. **Use manual lineage annotation in DAG code:**
   ```python
   task = PostgresOperator(
       task_id='my_task',
       sql='...',
       doc_md="""
       **DCS Lineage:**
       - Reads: source_capsule_1, source_capsule_2
       - Writes: target_capsule
       """
   )
   ```

### Performance Issues

**Problem:** Capsule ingestion or lineage detection is slow

**Solutions:**

1. **Ingest specific capsules instead of all:**
   ```bash
   # Ingest only what you need
   dcs ingest --source-type snowflake --capsule-name specific_table
   ```

2. **Use batch ingestion for multiple capsules:**
   ```python
   # Python script to ingest multiple capsules
   import subprocess

   capsules = ['users', 'orders', 'products']
   for capsule in capsules:
       subprocess.run([
           'dcs', 'ingest',
           '--source-type', 'snowflake',
           '--capsule-name', capsule
       ])
   ```

3. **Monitor backend resource usage:**
   ```bash
   # Check CPU/memory usage
   docker stats dcs-backend

   # Scale resources if needed (docker-compose.yml)
   # backend:
   #   deploy:
   #     resources:
   #       limits:
   #         cpus: '2'
   #         memory: 4G
   ```

4. **Optimize database queries:**
   ```bash
   # Check for slow queries in PostgreSQL
   docker exec -it dcs-postgres psql -U postgres -d dcs -c \
     "SELECT query, mean_exec_time FROM pg_stat_statements
      ORDER BY mean_exec_time DESC LIMIT 10;"
   ```

---

## Examples

### Example 1: Simple ETL Pipeline

```python
from airflow import DAG
from airflow.providers.postgres.operators.postgres import PostgresOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'data-team',
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
    'email_on_failure': True,
    'email': ['data-alerts@company.com'],
}

with DAG(
    dag_id='daily_user_etl',
    default_args=default_args,
    description='Extract, transform, and load user data daily',
    schedule_interval='@daily',
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['etl', 'users', 'production'],
    doc_md="""
    ## Daily User ETL Pipeline

    **DCS Lineage:**
    - Reads: production.users, production.user_profiles
    - Writes: warehouse.users_dim

    **Schedule:** Daily at 2 AM EST
    **Owner:** Data Engineering Team
    """
) as dag:

    # Extract users
    extract = PostgresOperator(
        task_id='extract_users',
        postgres_conn_id='production_db',
        sql="""
            SELECT
                user_id,
                email,
                created_at,
                updated_at
            FROM users
            WHERE updated_at >= '{{ prev_ds }}'
        """,
        doc_md="Extracts users modified since last run"
    )

    # Transform
    transform = PostgresOperator(
        task_id='transform_users',
        postgres_conn_id='staging_db',
        sql="""
            INSERT INTO staging.users_transformed
            SELECT
                user_id,
                LOWER(email) as email,
                DATE(created_at) as signup_date,
                CURRENT_TIMESTAMP as processed_at
            FROM staging.users_raw
            WHERE date = '{{ ds }}'
        """,
        doc_md="Cleans and standardizes user data"
    )

    # Load
    load = PostgresOperator(
        task_id='load_users',
        postgres_conn_id='warehouse_db',
        sql="""
            MERGE INTO warehouse.users_dim t
            USING staging.users_transformed s
            ON t.user_id = s.user_id
            WHEN MATCHED THEN
                UPDATE SET email = s.email, updated_at = s.processed_at
            WHEN NOT MATCHED THEN
                INSERT VALUES (s.user_id, s.email, s.signup_date, s.processed_at)
        """,
        doc_md="Loads data into warehouse"
    )

    extract >> transform >> load
```

### Example 2: Data Quality Checks

```python
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.operators.postgres import PostgresOperator
from datetime import datetime, timedelta

def validate_data(**context):
    """DCS quality check integration."""
    import requests

    # Call DCS quality API
    response = requests.post(
        'http://dcs-backend:8000/api/quality/validate',
        json={
            'capsule_urn': 'urn:dcs:capsule:users_staging',
            'rules': ['completeness', 'uniqueness', 'validity']
        }
    )

    results = response.json()
    if results['status'] == 'failed':
        raise ValueError(f"Quality checks failed: {results['failures']}")

    print(f"Quality checks passed: {results['summary']}")

with DAG(
    dag_id='users_with_quality_checks',
    schedule_interval='@daily',
    start_date=datetime(2024, 1, 1),
    tags=['quality', 'users'],
) as dag:

    load_data = PostgresOperator(
        task_id='load_staging',
        sql='INSERT INTO staging.users SELECT * FROM raw.users',
    )

    quality_check = PythonOperator(
        task_id='dcs_quality_check',
        python_callable=validate_data,
        doc_md="""
        Runs DCS quality checks on staged data.

        **Checks:**
        - Completeness: No NULL values in required fields
        - Uniqueness: No duplicate user_ids
        - Validity: Email format validation
        """
    )

    promote_to_prod = PostgresOperator(
        task_id='promote_to_production',
        sql='INSERT INTO prod.users SELECT * FROM staging.users',
    )

    load_data >> quality_check >> promote_to_prod
```

### Example 3: Complex Data Pipeline

```python
from airflow import DAG
from airflow.operators.dummy import DummyOperator
from airflow.providers.postgres.operators.postgres import PostgresOperator
from datetime import datetime, timedelta

with DAG(
    dag_id='revenue_reporting_pipeline',
    schedule_interval='0 6 * * *',  # 6 AM daily
    start_date=datetime(2024, 1, 1),
    tags=['finance', 'reporting', 'production'],
    doc_md="""
    ## Revenue Reporting Pipeline

    Comprehensive pipeline to calculate daily revenue metrics.

    **DCS Lineage:**
    - Reads: orders, payments, refunds, customers
    - Writes: revenue_daily, revenue_summary

    **Dependencies:**
    - orders table must be updated by 5 AM
    - payments table must be updated by 5:30 AM

    **SLA:** Must complete by 7 AM for morning reports
    """
) as dag:

    start = DummyOperator(task_id='start')

    # Extract orders
    extract_orders = PostgresOperator(
        task_id='extract_orders',
        sql="""
            SELECT * FROM orders
            WHERE order_date = '{{ ds }}'
        """
    )

    # Extract payments
    extract_payments = PostgresOperator(
        task_id='extract_payments',
        sql="""
            SELECT * FROM payments
            WHERE payment_date = '{{ ds }}'
        """
    )

    # Extract refunds
    extract_refunds = PostgresOperator(
        task_id='extract_refunds',
        sql="""
            SELECT * FROM refunds
            WHERE refund_date = '{{ ds }}'
        """
    )

    # Join data
    join_data = PostgresOperator(
        task_id='join_revenue_data',
        sql="""
            CREATE TEMP TABLE daily_revenue AS
            SELECT
                o.order_id,
                o.customer_id,
                o.order_amount,
                p.payment_amount,
                COALESCE(r.refund_amount, 0) as refund_amount,
                (p.payment_amount - COALESCE(r.refund_amount, 0)) as net_revenue
            FROM staging.orders o
            LEFT JOIN staging.payments p ON o.order_id = p.order_id
            LEFT JOIN staging.refunds r ON o.order_id = r.order_id
            WHERE o.order_date = '{{ ds }}'
        """
    )

    # Calculate metrics
    calculate_metrics = PostgresOperator(
        task_id='calculate_daily_metrics',
        sql="""
            INSERT INTO analytics.revenue_daily
            SELECT
                '{{ ds }}' as date,
                COUNT(DISTINCT order_id) as order_count,
                SUM(order_amount) as gross_revenue,
                SUM(net_revenue) as net_revenue,
                AVG(net_revenue) as avg_order_value,
                COUNT(DISTINCT customer_id) as unique_customers
            FROM daily_revenue
        """
    )

    # Update summary
    update_summary = PostgresOperator(
        task_id='update_revenue_summary',
        sql="""
            INSERT INTO analytics.revenue_summary
            SELECT
                DATE_TRUNC('month', date) as month,
                SUM(net_revenue) as monthly_revenue,
                AVG(net_revenue) as avg_daily_revenue,
                COUNT(*) as days_in_month
            FROM analytics.revenue_daily
            WHERE date >= DATE_TRUNC('month', '{{ ds }}'::date)
            GROUP BY DATE_TRUNC('month', date)
            ON CONFLICT (month)
            DO UPDATE SET
                monthly_revenue = EXCLUDED.monthly_revenue,
                avg_daily_revenue = EXCLUDED.avg_daily_revenue,
                days_in_month = EXCLUDED.days_in_month
        """
    )

    end = DummyOperator(task_id='end')

    # Dependencies
    start >> [extract_orders, extract_payments, extract_refunds]
    [extract_orders, extract_payments, extract_refunds] >> join_data
    join_data >> calculate_metrics >> update_summary >> end
```

---

## Quick Command Reference

### Essential Commands

```bash
# ═══════════════════════════════════════════════════════════════
# AIRFLOW INGESTION
# ═══════════════════════════════════════════════════════════════

# Basic ingestion (no auth)
dcs ingest airflow --base-url http://airflow.example.com:8080

# With basic authentication
export AIRFLOW_USERNAME=admin
export AIRFLOW_PASSWORD=your_password
dcs ingest airflow --base-url http://airflow.example.com:8080 --auth-mode basic_env

# With bearer token authentication
export AIRFLOW_TOKEN=your_bearer_token
dcs ingest airflow --base-url http://airflow.example.com:8080 --auth-mode bearer_env

# Filter by DAG regex pattern
dcs ingest airflow \
  --base-url http://airflow.example.com:8080 \
  --auth-mode basic_env \
  --dag-regex "^production_.*"

# Use allowlist for specific DAGs
dcs ingest airflow \
  --base-url http://airflow.example.com:8080 \
  --auth-mode basic_env \
  --dag-allowlist "dag1,dag2,dag3"

# Exclude specific DAGs with denylist
dcs ingest airflow \
  --base-url http://airflow.example.com:8080 \
  --auth-mode basic_env \
  --dag-denylist "test_dag,dev_dag"

# Include paused and inactive DAGs
dcs ingest airflow \
  --base-url http://airflow.example.com:8080 \
  --auth-mode basic_env \
  --include-paused \
  --include-inactive

# Clean up orphaned DAGs (removed from Airflow)
dcs ingest airflow \
  --base-url http://airflow.example.com:8080 \
  --auth-mode basic_env \
  --cleanup-orphans

# Increase timeout for slow APIs
dcs ingest airflow \
  --base-url http://airflow.example.com:8080 \
  --auth-mode basic_env \
  --timeout 60.0

# ═══════════════════════════════════════════════════════════════
# LINEAGE VISUALIZATION
# ═══════════════════════════════════════════════════════════════

# Export lineage graph as Mermaid
dcs lineage export --output-format mermaid > lineage.md

# Export as DOT format for Graphviz
dcs lineage export --output-format dot | dot -Tpng > lineage.png

# Export as JSON for programmatic access
dcs lineage export --output-format json > lineage.json

# ═══════════════════════════════════════════════════════════════
# AIRFLOW API QUERIES (for monitoring)
# ═══════════════════════════════════════════════════════════════

# Test Airflow connectivity
curl -u ${AIRFLOW_USERNAME}:${AIRFLOW_PASSWORD} \
  ${AIRFLOW_URL}/api/v1/health

# List all DAGs
curl -u ${AIRFLOW_USERNAME}:${AIRFLOW_PASSWORD} \
  "${AIRFLOW_URL}/api/v1/dags" | jq '.dags[] | {dag_id, is_paused, schedule_interval}'

# Get specific DAG details
curl -u ${AIRFLOW_USERNAME}:${AIRFLOW_PASSWORD} \
  "${AIRFLOW_URL}/api/v1/dags/your_dag_id" | jq .

# Get recent DAG runs
curl -u ${AIRFLOW_USERNAME}:${AIRFLOW_PASSWORD} \
  "${AIRFLOW_URL}/api/v1/dags/your_dag_id/dagRuns?limit=10" | \
  jq '.dag_runs[] | {execution_date, state, start_date, end_date}'

# Get failed task instances
curl -u ${AIRFLOW_USERNAME}:${AIRFLOW_PASSWORD} \
  "${AIRFLOW_URL}/api/v1/dags/~/dagRuns/~/taskInstances?state=failed" | \
  jq '.task_instances[] | {dag_id, task_id, state, start_date}'
```

### Automation Examples

**Cron job for regular syncing:**

```bash
# Add to crontab (crontab -e)
# Sync every hour
0 * * * * dcs ingest airflow --base-url http://airflow.company.com:8080 --auth-mode basic_env

# Sync every 6 hours with cleanup
0 */6 * * * dcs ingest airflow --base-url http://airflow.company.com:8080 --auth-mode basic_env --cleanup-orphans
```

**Systemd timer (Linux):**

```ini
# /etc/systemd/system/dcs-airflow-sync.service
[Unit]
Description=DCS Airflow Sync
After=network.target

[Service]
Type=oneshot
Environment="AIRFLOW_USERNAME=admin"
Environment="AIRFLOW_PASSWORD=your_password"
ExecStart=/usr/local/bin/dcs ingest airflow --base-url http://airflow.company.com:8080 --auth-mode basic_env
User=dcs
Group=dcs

# /etc/systemd/system/dcs-airflow-sync.timer
[Unit]
Description=DCS Airflow Sync Timer

[Timer]
OnCalendar=hourly
Persistent=true

[Install]
WantedBy=timers.target
```

---

## Additional Resources

### Documentation
- [Apache Airflow Documentation](https://airflow.apache.org/docs/)
- [DCS API Reference](./api_integration_guide.md)
- [DCS Lineage Guide](./column_lineage_guide.md)

### Support
- **Email:** data-platform@company.com
- **Slack:** #data-platform-support
- **GitHub Issues:** [github.com/yourcompany/dcs/issues](https://github.com)

### Training
- **Video Tutorial:** Airflow Integration Setup (20 minutes)
- **Workshop:** Advanced DAG Patterns (2 hours)
- **Office Hours:** Every Tuesday 2-3 PM EST

---

**Last Updated:** December 2024
**Version:** 1.0
**Maintained By:** Data Platform Team
