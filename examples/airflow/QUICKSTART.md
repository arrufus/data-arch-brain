# Airflow Integration - Quick Start Guide

Get up and running with the Airflow integration example in 5 minutes!

## Prerequisites

1. **Docker** and **Docker Compose** installed
2. **Python 3.11+** with `dcs` CLI installed
3. **PostgreSQL** database accessible (included in DCS stack)

## Quick Setup (5 Minutes)

### Step 1: Start DCS Services (1 minute)

```bash
cd /Users/rademola/data-arch-brain
make up
```

This starts:
- PostgreSQL database
- DCS API server (port 8000)
- Frontend UI (port 3000)

### Step 2: Create Sample Data (2 minutes)

```bash
# Connect to PostgreSQL
docker exec -it dcs-postgres psql -U dcs -d dcs

# Run the sample data script
\i /path/to/examples/airflow/sample_data_assets.sql

# Or copy-paste from terminal:
psql -h localhost -U dcs -d dcs -f examples/airflow/sample_data_assets.sql
```

### Step 3: Set Environment Variables (30 seconds)

```bash
export AIRFLOW_USERNAME=admin
export AIRFLOW_PASSWORD=admin
export AIRFLOW_BASE_URL=http://localhost:8080  # Or your Airflow URL
```

### Step 4: Run Complete Example (1 minute)

```bash
cd examples/airflow
./complete_example.sh
```

That's it! ✓

## What Gets Demonstrated

The script will automatically:

1. ✅ **Ingest Airflow metadata** (DAGs and tasks)
2. ✅ **Map tasks to data assets** (using annotations)
3. ✅ **Parse SQL for column lineage**
4. ✅ **Query pipelines and dependencies**
5. ✅ **Export lineage graphs**
6. ✅ **Analyze impact of schema changes**
7. ✅ **Find optimal deployment windows**
8. ✅ **Simulate what-if scenarios**

## View Results

All outputs are saved to `examples/airflow/output/`:

```bash
# View summary
cat output/SUMMARY.md

# View lineage graph
cat output/4_lineage.mermaid

# Analyze impact details
jq '.' output/5_impact_analysis.json

# Compare simulation scenarios
jq '{risk_level, success_rate: .historical_success_rate, recommendations}' output/7_simulation_*.json
```

## Manual Testing (Optional)

If you prefer to run commands individually:

### 1. Ingest Airflow

```bash
dcs ingest airflow \
  --base-url http://localhost:8080 \
  --instance prod \
  --auth-mode basic_env \
  --annotation-file finance_annotations.yml
```

### 2. Query Pipelines

```bash
# List all pipelines
curl http://localhost:8000/api/pipelines?source_type=airflow | jq '.'

# Get specific pipeline
curl http://localhost:8000/api/pipelines/urn:dcs:airflow:pipeline:prod:finance_gl_pipeline | jq '.'
```

### 3. Analyze Impact

```bash
# Analyze column change
curl -X POST "http://localhost:8000/api/impact/analyze/column/urn:dcs:column:erp.dim:chart_of_accounts.account_code?change_type=rename&include_temporal=true" | jq '.'
```

### 4. Simulate Changes

```bash
# Simulate with alias (safer)
curl -X POST http://localhost:8000/api/impact/simulate \
  -H "Content-Type: application/json" \
  -d '{
    "column_urn": "urn:dcs:column:erp.dim:chart_of_accounts.account_code",
    "change_type": "rename",
    "change_params": {"new_name": "account_number", "create_alias": true},
    "include_temporal": true
  }' | jq '.'
```

## Without Airflow Running (Mock Demo)

You can run the example even without a real Airflow instance by using the test data:

```bash
# The script will use mock data if Airflow is not reachable
# This demonstrates the API and features without live Airflow
./complete_example.sh
```

The example will:
- ✅ Create mock pipeline data in DCS
- ✅ Show all API responses
- ✅ Demonstrate all Phase 8 features

## Troubleshooting

### DCS API not reachable

```bash
# Check if services are running
docker ps | grep dcs

# Restart services
make down && make up

# Check API health
curl http://localhost:8000/health
```

### Airflow authentication errors

```bash
# Verify credentials
curl -u $AIRFLOW_USERNAME:$AIRFLOW_PASSWORD \
  http://localhost:8080/api/v1/version

# Try with explicit credentials
export AIRFLOW_USERNAME=your_username
export AIRFLOW_PASSWORD=your_password
```

### Database connection issues

```bash
# Check PostgreSQL
docker exec dcs-postgres pg_isready

# Connect manually
psql -h localhost -U dcs -d dcs

# Check tables exist
\dt dim.*
\dt staging.*
\dt facts.*
```

### Script permissions

```bash
# Make script executable
chmod +x complete_example.sh

# Run with bash explicitly
bash complete_example.sh
```

## Next Steps

Once you've run the example:

1. **Explore the UI**: Visit http://localhost:3000
2. **View lineage graphs**: Check `output/4_lineage.mermaid`
3. **Analyze impact**: Review `output/5_impact_analysis.json`
4. **Try custom scenarios**: Modify `finance_annotations.yml`
5. **Add your DAGs**: Point to your own Airflow instance

## Key Files

| File | Purpose |
|------|---------|
| `README.md` | Comprehensive feature documentation |
| `QUICKSTART.md` | This quick start guide |
| `complete_example.sh` | Automated demo script |
| `finance_gl_dag.py` | Sample Airflow DAG |
| `finance_annotations.yml` | Task → data mappings |
| `sample_data_assets.sql` | Database schema and sample data |

## Support

Having issues? Check:
- [Full Documentation](README.md)
- [Airflow Integration Design](../../docs/design_docs/airflow_integration_design.md)
- [Phase 8 Impact Analysis Guide](../../docs/user_guide/phase8_impact_analysis_guide.md)
- [API Specification](../../docs/api_specification.md)

---

**Time to complete**: ~5 minutes

**Last updated**: December 2025
