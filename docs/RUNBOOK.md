# Data Capsule Server - Operational Runbook

**Version:** 1.0
**Last Updated:** January 2025

---

## Table of Contents

1. [Service Overview](#service-overview)
2. [Health Checks & Monitoring](#health-checks--monitoring)
3. [Common Operations](#common-operations)
4. [Incident Response](#incident-response)
5. [Capacity Planning](#capacity-planning)
6. [Backup & Recovery](#backup--recovery)
7. [Configuration Reference](#configuration-reference)

---

## Service Overview

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Data Capsule Server                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │         Next.js Web Dashboard (Port 3000)                │   │
│  │  React UI: Capsules, PII Compliance, Reports, Settings  │   │
│  └────────────────────┬─────────────────────────────────────┘   │
│                       │ HTTP REST API                            │
│                       ▼                                          │
│  ┌──────────┐   ┌──────────────┐   ┌─────────────────────────┐  │
│  │ FastAPI  │───│ Rate Limiter │───│ Authentication (API Key)│  │
│  │ App      │   │ (SlowAPI)    │   │ Middleware              │  │
│  └──────────┘   └──────────────┘   └─────────────────────────┘  │
│       │                                                          │
│       ▼                                                          │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    Service Layer                          │   │
│  │  ┌──────────┐  ┌────────────┐  ┌────────────────────────┐│   │
│  │  │Ingestion │  │Conformance │  │ Compliance (PII)       ││   │
│  │  └──────────┘  └────────────┘  └────────────────────────┘│   │
│  └──────────────────────────────────────────────────────────┘   │
│       │                                                          │
│       ▼                                                          │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                 Repository Layer                          │   │
│  │  ┌────────┐  ┌────────┐  ┌───────┐  ┌─────────────────┐  │   │
│  │  │Capsule │  │Column  │  │Lineage│  │Rule/Violation   │  │   │
│  │  └────────┘  └────────┘  └───────┘  └─────────────────┘  │   │
│  └──────────────────────────────────────────────────────────┘   │
│       │                                                          │
│       ▼                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │ PostgreSQL   │  │    Redis     │  │ Prometheus (Metrics) │   │
│  │ (Primary DB) │  │   (Cache)    │  │ + OpenTelemetry      │   │
│  └──────────────┘  └──────────────┘  └──────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Key Components

| Component | Purpose | Port |
|-----------|---------|------|
| Next.js Web Dashboard | React UI for visual exploration | 3000 |
| FastAPI Application | REST API server | 8002 |
| PostgreSQL | Primary database | 5433 |
| Redis | Cache & rate limiting | 6379 |
| Prometheus | Metrics scraping | 9090 |
| Jaeger (optional) | Distributed tracing | 16686 |

---

## Health Checks & Monitoring

### Health Endpoints

| Endpoint | Purpose | Response |
|----------|---------|----------|
| `GET /api/v1/health` | Full health check | `{ "status": "healthy", "database": "connected", ... }` |
| `GET /api/v1/health/live` | Liveness probe | `{ "status": "alive" }` |
| `GET /api/v1/health/ready` | Readiness probe | `{ "status": "ready" }` |

### Kubernetes Probes

```yaml
livenessProbe:
  httpGet:
    path: /api/v1/health/live
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 15
  failureThreshold: 3

readinessProbe:
  httpGet:
    path: /api/v1/health/ready
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 10
  failureThreshold: 3
```

### Key Metrics

| Metric | Type | Description | Alert Threshold |
|--------|------|-------------|-----------------|
| `dab_http_requests_total` | Counter | Total HTTP requests | - |
| `dab_http_request_duration_seconds` | Histogram | Request latency | p99 > 2s |
| `dab_ingestion_total` | Counter | Ingestion job count | error rate > 10% |
| `dab_conformance_score` | Gauge | Current conformance score | score < 0.5 |
| `dab_capsule_count` | Gauge | Total capsules in system | - |
| `dab_pii_column_count` | Gauge | PII columns by type | - |
| `dab_cache_hits_total` | Counter | Cache hit count | hit rate < 50% |
| `dab_db_query_duration_seconds` | Histogram | DB query latency | p95 > 500ms |

### Alerting Rules (Prometheus)

```yaml
groups:
  - name: dab-alerts
    rules:
      - alert: DABHighLatency
        expr: histogram_quantile(0.99, dab_http_request_duration_seconds_bucket) > 2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High API latency detected"
          
      - alert: DABDatabaseSlow
        expr: histogram_quantile(0.95, dab_db_query_duration_seconds_bucket) > 0.5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Database queries are slow"
          
      - alert: DABIngestionFailures
        expr: increase(dab_ingestion_total{status="failed"}[1h]) > 5
        for: 10m
        labels:
          severity: critical
        annotations:
          summary: "Multiple ingestion failures detected"
          
      - alert: DABLowCacheHitRate
        expr: dab_cache_hits_total / (dab_cache_hits_total + dab_cache_misses_total) < 0.5
        for: 15m
        labels:
          severity: warning
        annotations:
          summary: "Cache hit rate is below 50%"
```

---

## Common Operations

### Starting the Service

```bash
# Using Docker Compose (recommended)
docker-compose -f docker/docker-compose.yml up -d

# Using uvicorn directly
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --workers 4

# Development mode
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

### Stopping the Service

```bash
# Graceful shutdown
docker-compose -f docker/docker-compose.yml down

# Force stop (last resort)
docker-compose -f docker/docker-compose.yml down --timeout 30
```

### Database Migrations

```bash
# Check current migration status
alembic current

# Apply all pending migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Generate new migration
alembic revision --autogenerate -m "Description of changes"
```

### Cache Operations

```bash
# Clear all cache (Redis CLI)
redis-cli -h localhost -p 6379 FLUSHDB

# Clear specific cache patterns
redis-cli -h localhost -p 6379 KEYS "dcs:*" | xargs redis-cli DEL

# Check cache stats
redis-cli -h localhost -p 6379 INFO stats
```

### Ingesting Data

#### dbt Ingestion

```bash
# Via CLI
dab ingest dbt --manifest /path/to/manifest.json --catalog /path/to/catalog.json

# With project name override
dab ingest dbt --manifest /path/to/manifest.json --project my_project

# Via API
curl -X POST "http://localhost:8000/api/v1/ingest/dbt" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "manifest_path": "/path/to/manifest.json",
    "catalog_path": "/path/to/catalog.json",
    "project_name": "my_project"
  }'
```

#### Airflow Ingestion

```bash
# Via CLI - No authentication
dab ingest airflow --base-url https://airflow.example.com

# With bearer token authentication
export AIRFLOW_TOKEN=your-token-here
dab ingest airflow \
  --base-url https://airflow.example.com \
  --auth-mode bearer_env

# With basic authentication
export AIRFLOW_USERNAME=admin
export AIRFLOW_PASSWORD=password
dab ingest airflow \
  --base-url https://airflow.example.com \
  --auth-mode basic_env

# Filter by DAG regex
dab ingest airflow \
  --base-url https://airflow.example.com \
  --dag-regex "customer_.*"

# Include paused DAGs and cleanup orphans
dab ingest airflow \
  --base-url https://airflow.example.com \
  --include-paused \
  --cleanup-orphans

# Full configuration with all options
dab ingest airflow \
  --base-url https://airflow.example.com \
  --instance prod-airflow \
  --auth-mode bearer_env \
  --dag-regex "^(customer|product)_.*" \
  --include-paused \
  --page-limit 50 \
  --timeout 60.0 \
  --cleanup-orphans

# Via API
curl -X POST "http://localhost:8000/api/v1/ingest/airflow" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "base_url": "https://airflow.example.com",
    "instance_name": "prod-airflow",
    "auth_mode": "bearer_env",
    "token_env": "AIRFLOW_TOKEN",
    "dag_id_regex": "customer_.*",
    "include_paused": false,
    "cleanup_orphans": true
  }'

# Check ingestion status
curl -H "X-API-Key: your-api-key" \
  "http://localhost:8000/api/v1/ingest/job/{job_id}"

# List recent ingestion jobs
curl -H "X-API-Key: your-api-key" \
  "http://localhost:8000/api/v1/ingest/history?source_type=airflow&limit=10"
```

**Authentication Options:**
- `none`: No authentication (for local/dev Airflow instances)
- `bearer_env`: Bearer token from environment variable (recommended for production)
- `basic_env`: Basic auth credentials from environment variables

**DAG Filtering:**
- `--dag-regex`: Filter DAGs by regex pattern
- `--dag-allowlist`: Comma-separated list of DAG IDs to include (exclusive with denylist)
- `--dag-denylist`: Comma-separated list of DAG IDs to exclude (exclusive with allowlist)
- `--include-paused`: Include paused DAGs (default: false)
- `--include-inactive`: Include inactive DAGs (default: false)

### Resetting Application Data

Remove all data capsules, lineage, and property graph information to restore the application to a clean state.

#### Full Reset (All Data)

```bash
# Via PostgreSQL - Clear all data while preserving schema
docker-compose exec postgres psql -U dab -d dab -c "
TRUNCATE TABLE
    lineage_edges,
    column_lineage_edges,
    conformance_violations,
    capsule_tags,
    column_tags,
    data_product_capsules,
    columns,
    capsules,
    data_products,
    tags,
    domains,
    ingestion_jobs
CASCADE;
"

# Clear Redis cache after database reset
redis-cli -h localhost -p 6379 FLUSHDB

# Verify reset
curl -H "X-API-Key: your-api-key" \
  "http://localhost:8000/api/v1/capsules?limit=1" | jq '.total'
# Expected: 0
```

#### Reset Specific Components

```bash
# Clear only capsules and lineage (keeps rules, tags definitions)
docker-compose exec postgres psql -U dab -d dab -c "
TRUNCATE TABLE
    lineage_edges,
    column_lineage_edges,
    conformance_violations,
    capsule_tags,
    column_tags,
    data_product_capsules,
    columns,
    capsules
CASCADE;
"

# Clear only lineage information
docker-compose exec postgres psql -U dab -d dab -c "
TRUNCATE TABLE lineage_edges, column_lineage_edges CASCADE;
"

# Clear only property graph edges (keeps nodes)
docker-compose exec postgres psql -U dab -d dab -c "
TRUNCATE TABLE
    lineage_edges,
    column_lineage_edges,
    capsule_tags,
    column_tags,
    data_product_capsules
CASCADE;
"

# Clear only violations (for re-evaluation)
docker-compose exec postgres psql -U dab -d dab -c "
TRUNCATE TABLE conformance_violations;
"

# Clear only ingestion history
docker-compose exec postgres psql -U dab -d dab -c "
TRUNCATE TABLE ingestion_jobs;
"
```

#### Reset via Database Migration

For a complete reset with schema recreation:

```bash
# Rollback all migrations and re-apply
alembic downgrade base
alembic upgrade head

# Clear Redis cache
redis-cli -h localhost -p 6379 FLUSHDB
```

**Warning:** This approach recreates all tables and should only be used in development or when schema changes are needed.

#### Post-Reset Verification

```bash
# Verify all data cleared
curl -H "X-API-Key: your-api-key" "http://localhost:8000/api/v1/capsules?limit=1"
# Expected: {"items": [], "total": 0, ...}

curl -H "X-API-Key: your-api-key" "http://localhost:8000/api/v1/capsules/stats"
# Expected: All counts at 0

# Verify health still OK
curl http://localhost:8000/api/v1/health/ready
# Expected: {"status": "ready"}
```

---

### Running Conformance Evaluation

```bash
# Full evaluation
curl -X POST "http://localhost:8000/api/v1/conformance/evaluate" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"scope": "full", "persist_violations": true}'

# Layer-specific evaluation
curl -X POST "http://localhost:8000/api/v1/conformance/evaluate" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"scope": "layer", "layer": "gold"}'
```

### Managing Data Products

Data Products group capsules into logical units following the Data Mesh pattern. They track SLO compliance for freshness, availability, and quality.

#### Via CLI

```bash
# List all data products
dab products list

# Filter by domain
dab products list --domain customer

# Filter by status
dab products list --status active

# Create a new data product
dab products create \
  --name "Customer 360" \
  --description "Unified customer data product" \
  --domain customer \
  --owner data_engineering \
  --version "v1.0"

# Get product details
dab products get "Customer 360"

# Add a capsule to a data product (creates PART_OF edge)
dab products add-capsule \
  --product "Customer 360" \
  --capsule "urn:dcs:dbt:model:myproject.marts:dim_customers" \
  --role output

# Remove a capsule from a data product
dab products remove-capsule \
  --product "Customer 360" \
  --capsule "urn:dcs:dbt:model:myproject.marts:dim_customers"
```

#### Via API

```bash
# List all data products
curl -H "X-API-Key: your-api-key" \
  "http://localhost:8000/api/v1/products"

# Create a new data product
curl -X POST "http://localhost:8000/api/v1/products" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Customer 360",
    "description": "Unified customer data product",
    "domain_id": "uuid-of-domain",
    "slo_freshness_hours": 24,
    "slo_availability_percent": 99.9,
    "slo_quality_threshold": 0.95
  }'

# Add a capsule to a data product (creates PART_OF edge)
curl -X POST "http://localhost:8000/api/v1/products/{product_id}/capsules/{capsule_id}" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"role": "output"}'

# Check SLO status for a data product
curl -H "X-API-Key: your-api-key" \
  "http://localhost:8000/api/v1/products/{product_id}/slo-status"
# Response: {"freshness_met": true, "availability_met": true, "quality_met": false, "overall_status": "degraded"}

# Remove a capsule from a data product
curl -X DELETE "http://localhost:8000/api/v1/products/{product_id}/capsules/{capsule_id}" \
  -H "X-API-Key: your-api-key"
```

### Managing Tags

Tags are applied to capsules and columns as graph edges (TAGGED_WITH relationship).

```bash
# Create a new tag
curl -X POST "http://localhost:8000/api/v1/tags" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "pii",
    "category": "compliance",
    "description": "Personally identifiable information"
  }'

# Tag a capsule
curl -X POST "http://localhost:8000/api/v1/tags/capsules/{capsule_id}/{tag_id}" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"added_by": "ops@company.com"}'

# Tag a column
curl -X POST "http://localhost:8000/api/v1/tags/columns/{column_id}/{tag_id}" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"added_by": "ops@company.com"}'

# List all capsules with a specific tag
curl -H "X-API-Key: your-api-key" \
  "http://localhost:8000/api/v1/tags/{tag_id}/capsules"

# Remove a tag from a column
curl -X DELETE "http://localhost:8000/api/v1/tags/columns/{column_id}/{tag_id}" \
  -H "X-API-Key: your-api-key"
```

### Exporting the Property Graph

Export the property graph for visualization tools or integration with graph databases.

#### Via CLI

```bash
# Export full graph in Mermaid format (renders in GitHub, GitLab, Notion)
dab graph export --format mermaid --output graph.mmd

# Export in GraphML for Gephi or yEd
dab graph export --format graphml --output graph.graphml

# Export for Neo4j import (Cypher statements)
dab graph export --format cypher --output import.cypher

# Import to Neo4j
cat import.cypher | cypher-shell -u neo4j -p password

# Export DOT graph for Graphviz
dab graph export --format dot --output graph.dot

# Render DOT graph with Graphviz
dot -Tpng graph.dot -o graph.png
dot -Tsvg graph.dot -o graph.svg

# Export filtered by domain
dab graph export --format mermaid --domain customer --output customer_graph.mmd

# Export lineage subgraph for a specific capsule
dab graph export-lineage "urn:dcs:dbt:model:project:orders" \
  --format mermaid \
  --depth 3 \
  --output orders_lineage.mmd

# Export upstream lineage only (data sources)
dab graph export-lineage "urn:dcs:dbt:model:project:orders" \
  --format dot \
  --direction upstream \
  --depth 5 \
  --output upstream.dot

# Export downstream lineage only (data consumers)
dab graph export-lineage "urn:dcs:dbt:model:project:orders" \
  --format mermaid \
  --direction downstream \
  --output downstream.mmd

# Export to stdout (for piping or viewing)
dab graph export --format mermaid
```

#### Via API

```bash
# List available export formats
curl -H "X-API-Key: your-api-key" \
  "http://localhost:8000/api/v1/graph/formats"
# Response: ["graphml", "dot", "cypher", "mermaid", "json-ld"]

# Export full graph in Mermaid format
curl -H "X-API-Key: your-api-key" \
  "http://localhost:8000/api/v1/graph/export?format=mermaid" > graph.mmd

# Export in GraphML for Gephi or yEd
curl -H "X-API-Key: your-api-key" \
  "http://localhost:8000/api/v1/graph/export?format=graphml" > graph.graphml

# Export for Neo4j import (Cypher statements)
curl -H "X-API-Key: your-api-key" \
  "http://localhost:8000/api/v1/graph/export?format=cypher" > import.cypher

# Export with additional nodes (columns, tags, data products)
curl -H "X-API-Key: your-api-key" \
  "http://localhost:8000/api/v1/graph/export?format=dot&include_columns=true&include_tags=true&include_data_products=true" > full_graph.dot

# Export lineage subgraph for a specific capsule
curl -H "X-API-Key: your-api-key" \
  "http://localhost:8000/api/v1/graph/export/lineage/urn:dcs:dbt:model:project:orders?format=mermaid&depth=3" > orders_lineage.mmd

# Export upstream lineage only (data sources)
curl -H "X-API-Key: your-api-key" \
  "http://localhost:8000/api/v1/graph/export/lineage/urn:dcs:dbt:model:project:orders?format=dot&direction=upstream&depth=5" > upstream.dot

# Export downstream lineage only (data consumers)
curl -H "X-API-Key: your-api-key" \
  "http://localhost:8000/api/v1/graph/export/lineage/urn:dcs:dbt:model:project:orders?format=mermaid&direction=downstream" > downstream.mmd
```

**Export Format Use Cases:**

| Format | File Extension | Use Cases |
|--------|---------------|-----------|
| `graphml` | `.graphml` | yEd, Gephi, Cytoscape, NetworkX |
| `dot` | `.dot` | Graphviz, VSCode GraphViz Preview |
| `cypher` | `.cypher` | Neo4j, Amazon Neptune, Memgraph |
| `mermaid` | `.mmd` | GitHub, GitLab, Notion, Obsidian |
| `json-ld` | `.jsonld` | Semantic web, Apache Jena, RDF tools |

---

## Incident Response

### Runbook: Service Unavailable (5xx errors)

**Symptoms:** API returns 500 errors, health check fails

**Steps:**

1. **Check service status**
   ```bash
   docker-compose ps
   curl http://localhost:8000/api/v1/health
   ```

2. **Check logs**
   ```bash
   docker-compose logs --tail=100 dcs-api
   ```

3. **Check database connectivity**
   ```bash
   docker-compose exec postgres pg_isready -h localhost -U dab
   ```

4. **Check Redis connectivity**
   ```bash
   docker-compose exec redis redis-cli ping
   ```

5. **Restart service if needed**
   ```bash
   docker-compose restart dcs-api
   ```

### Runbook: High Latency

**Symptoms:** p99 latency > 2s, slow API responses

**Steps:**

1. **Identify slow endpoints**
   ```promql
   topk(10, histogram_quantile(0.99, rate(dab_http_request_duration_seconds_bucket[5m])))
   ```

2. **Check database query performance**
   ```sql
   -- PostgreSQL slow query log
   SELECT query, mean_time, calls 
   FROM pg_stat_statements 
   ORDER BY mean_time DESC 
   LIMIT 10;
   ```

3. **Check cache hit rate**
   ```bash
   redis-cli INFO stats | grep -E "keyspace_hits|keyspace_misses"
   ```

4. **Check resource usage**
   ```bash
   docker stats dcs-api
   ```

5. **Scale if needed**
   ```bash
   docker-compose up -d --scale dcs-api=4
   ```

### Runbook: Ingestion Failures

**Symptoms:** Ingestion jobs failing, data not updating

**Steps:**

1. **Check recent ingestion jobs**
   ```bash
   curl "http://localhost:8000/api/v1/ingest/jobs?limit=10" \
     -H "X-API-Key: your-api-key"
   ```

2. **Get job details**
   ```bash
   curl "http://localhost:8000/api/v1/ingest/jobs/{job_id}" \
     -H "X-API-Key: your-api-key"
   ```

3. **Check for validation errors in logs**
   ```bash
   docker-compose logs --tail=500 dcs-api | grep -i "error\|validation"
   ```

4. **Validate input data**
   - Ensure manifest.json is valid
   - Check for required fields
   - Verify URN format compliance

5. **Retry ingestion**
   ```bash
   curl -X POST "http://localhost:8000/api/v1/ingest/jobs/{job_id}/retry" \
     -H "X-API-Key: your-api-key"
   ```

### Runbook: Airflow Ingestion Issues

**Symptoms:** Airflow ingestion failing, authentication errors, missing DAGs

**Steps:**

1. **Verify Airflow connectivity**
   ```bash
   # Test Airflow API directly
   curl https://airflow.example.com/api/v1/version \
     -H "Authorization: Bearer $AIRFLOW_TOKEN"
   ```

2. **Check authentication configuration**
   ```bash
   # Verify environment variables are set
   echo $AIRFLOW_TOKEN
   echo $AIRFLOW_USERNAME
   echo $AIRFLOW_PASSWORD

   # Test with different auth modes
   dab ingest airflow \
     --base-url https://airflow.example.com \
     --auth-mode none  # Try without auth first
   ```

3. **Verify DAG filtering**
   ```bash
   # List DAGs directly from Airflow
   curl "https://airflow.example.com/api/v1/dags?limit=10" \
     -H "Authorization: Bearer $AIRFLOW_TOKEN"

   # Test without filters
   dab ingest airflow \
     --base-url https://airflow.example.com \
     --auth-mode bearer_env

   # Gradually add filters
   dab ingest airflow \
     --base-url https://airflow.example.com \
     --auth-mode bearer_env \
     --dag-regex "test_.*"
   ```

4. **Check timeout and pagination settings**
   ```bash
   # Increase timeout for slow Airflow instances
   dab ingest airflow \
     --base-url https://airflow.example.com \
     --timeout 120.0

   # Reduce page size for large responses
   dab ingest airflow \
     --base-url https://airflow.example.com \
     --page-limit 50
   ```

5. **Review ingestion job logs**
   ```bash
   # Get detailed job information
   curl "http://localhost:8000/api/v1/ingest/history?source_type=airflow" \
     -H "X-API-Key: your-api-key"

   # Check for specific error patterns in logs
   docker-compose logs dcs-api | grep -i "airflow\|parse\|connection"
   ```

**Common Issues:**

| Issue | Cause | Solution |
|-------|-------|----------|
| `401 Unauthorized` | Missing or invalid auth token | Verify `AIRFLOW_TOKEN` is set and valid |
| `404 Not Found` | Wrong base URL or API version | Check Airflow is accessible and using v1 API |
| `Connection timeout` | Slow or unresponsive Airflow | Increase `--timeout` value |
| `No DAGs found` | Filters too restrictive | Review regex, allowlist, denylist settings |
| `Paused DAGs missing` | Paused DAGs excluded by default | Add `--include-paused` flag |
| `Secrets in database` | Config not redacted | Check secret redaction is enabled (should be automatic) |

### Runbook: Memory Issues (OOM)

**Symptoms:** Service crashes, OOM errors in logs

**Steps:**

1. **Check memory usage**
   ```bash
   docker stats dcs-api --no-stream
   ```

2. **Analyze heap dump (if available)**
   ```bash
   # Python memory profiling
   pip install memory_profiler
   python -m memory_profiler src/api/main.py
   ```

3. **Adjust memory limits**
   ```yaml
   # docker-compose.yml
   services:
     dcs-api:
       deploy:
         resources:
           limits:
             memory: 2G
   ```

4. **Enable pagination for large queries**
   - Use `limit` and `offset` parameters
   - Stream large reports instead of loading all data

---

## Capacity Planning

### Resource Requirements

| Deployment Size | Capsules | API Pods | CPU/Pod | Memory/Pod | PostgreSQL | Redis |
|----------------|----------|----------|---------|------------|------------|-------|
| Small | < 10,000 | 2 | 500m | 512MB | 2 vCPU, 4GB | 512MB |
| Medium | 10,000-100,000 | 4 | 1 | 1GB | 4 vCPU, 8GB | 2GB |
| Large | > 100,000 | 8 | 2 | 2GB | 8 vCPU, 16GB | 4GB |

### Performance Benchmarks

| Operation | Expected Latency (p95) | Throughput |
|-----------|----------------------|------------|
| Health check | < 10ms | 10,000 req/s |
| Get capsule by URN | < 50ms | 5,000 req/s |
| Search capsules | < 200ms | 1,000 req/s |
| Lineage query (depth 5) | < 500ms | 500 req/s |
| Full conformance evaluation | < 30s | 10 req/min |
| Ingestion (10k capsules) | < 60s | - |
| Data product SLO check | < 100ms | 2,000 req/s |
| Tag capsule/column | < 50ms | 3,000 req/s |
| Graph export (Mermaid) | < 2s | 100 req/min |
| Graph export (GraphML) | < 3s | 50 req/min |
| Lineage export (depth 3) | < 500ms | 500 req/s |

### Scaling Guidelines

1. **Horizontal Scaling (API)**
   - Scale API pods based on request rate
   - Each pod handles ~500 concurrent connections
   - Use sticky sessions for WebSocket (if added)

2. **Vertical Scaling (Database)**
   - Scale PostgreSQL for large datasets
   - Add read replicas for read-heavy workloads
   - Consider partitioning for > 1M capsules

3. **Cache Scaling**
   - Redis cluster for high availability
   - Increase memory for better hit rates
   - Consider separate Redis for rate limiting

---

## Backup & Recovery

### Database Backup

```bash
# Full backup
pg_dump -h localhost -U dab -d dab -F c -f backup_$(date +%Y%m%d).dump

# Schema only
pg_dump -h localhost -U dab -d dab -s -f schema_$(date +%Y%m%d).sql

# Automated backup (cron)
0 2 * * * pg_dump -h localhost -U dab -d dab -F c -f /backups/dab_$(date +\%Y\%m\%d).dump
```

### Database Restore

```bash
# Restore from dump
pg_restore -h localhost -U dab -d dab -c backup_20250101.dump

# Restore schema only
psql -h localhost -U dab -d dab -f schema_20250101.sql
```

### Disaster Recovery

1. **RPO (Recovery Point Objective):** 1 hour
   - Daily full backups
   - Hourly incremental backups (WAL archiving)

2. **RTO (Recovery Time Objective):** 4 hours
   - Automated restore scripts
   - Tested quarterly

3. **Failover Procedure:**
   - Promote standby database
   - Update connection strings
   - Verify data integrity
   - Resume service

---

## Configuration Reference

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `DATABASE_URL` | PostgreSQL connection string | - | Yes |
| `REDIS_URL` | Redis connection string | - | No |
| `AUTH_ENABLED` | Enable API key auth | `true` | No |
| `API_KEYS` | Comma-separated API keys | - | Yes (prod) |
| `RATE_LIMIT_ENABLED` | Enable rate limiting | `true` | No |
| `RATE_LIMIT_DEFAULT` | Default rate limit | `100/minute` | No |
| `CACHE_ENABLED` | Enable Redis caching | `true` | No |
| `METRICS_ENABLED` | Enable Prometheus metrics | `true` | No |
| `TRACING_ENABLED` | Enable OpenTelemetry | `false` | No |
| `TRACING_OTLP_ENDPOINT` | OTLP collector URL | - | No |
| `LOG_LEVEL` | Logging level | `INFO` | No |
| `ENVIRONMENT` | Environment name | `development` | No |

### Sample Production Configuration

```bash
# .env.production
DATABASE_URL=postgresql+asyncpg://dcs:secure_password@db.prod.example.com:5432/dab
REDIS_URL=redis://cache.prod.example.com:6379/0
AUTH_ENABLED=true
API_KEYS=key1_abc123,key2_def456
RATE_LIMIT_ENABLED=true
RATE_LIMIT_DEFAULT=100/minute
RATE_LIMIT_STORAGE_URI=redis://cache.prod.example.com:6379/1
CACHE_ENABLED=true
CACHE_REDIS_URL=redis://cache.prod.example.com:6379/0
METRICS_ENABLED=true
TRACING_ENABLED=true
TRACING_OTLP_ENDPOINT=http://jaeger.prod.example.com:4317
LOG_LEVEL=INFO
ENVIRONMENT=production
```

---

## Appendix

### Log Format

Logs use structured JSON format (structlog):

```json
{
  "timestamp": "2025-01-13T10:30:00Z",
  "level": "info",
  "event": "request_completed",
  "request_id": "abc123",
  "method": "GET",
  "path": "/api/v1/capsules",
  "status_code": 200,
  "duration_ms": 45
}
```

### Useful Commands

```bash
# Check API version
curl http://localhost:8000/api/v1/health | jq '.version'

# Count capsules
curl "http://localhost:8000/api/v1/capsules?limit=1" -H "X-API-Key: key" | jq '.total'

# Get metrics
curl http://localhost:8000/metrics

# Test rate limiting
for i in {1..110}; do curl -s -o /dev/null -w "%{http_code}\n" \
  "http://localhost:8000/api/v1/capsules" -H "X-API-Key: key"; done

# Export conformance report
curl "http://localhost:8000/api/v1/reports/conformance?format=html" \
  -H "X-API-Key: key" -o conformance_report.html
```

### Contact & Escalation

| Level | Contact | Response Time |
|-------|---------|---------------|
| L1 | On-call engineer | 15 min |
| L2 | Data Platform team | 1 hour |
| L3 | Platform architects | 4 hours |

---

*Document maintained by the Data Platform Team*
