# Data Pipeline Test Environment

This directory contains a complete test environment for the Data Architecture Brain (DAB) Airflow integration.

## Quick Start

```bash
# Start the environment
docker-compose up -d

# Wait for services to be ready (2-3 minutes)
docker-compose logs -f airflow

# Access Airflow UI
open http://localhost:8080
# Username: admin
# Password: admin

# Install dbt in Airflow container
docker exec -it dab-airflow pip install dbt-core==1.7.4 dbt-postgres==1.7.4

# Enable DAGs in the Airflow UI
# Then trigger the customer_analytics_pipeline DAG

# Test DAB ingestion
cd ../backend
dab ingest airflow --base-url http://localhost:8080 --instance local-test

# Verify capsules
dab capsules --type airflow_dag
dab capsules --type airflow_task
```

## Directory Structure

```
test_environment/
├── docker-compose.yml           # Docker services configuration
├── .env.example                 # Environment variables template
├── airflow/
│   ├── dags/                   # Airflow DAG definitions
│   │   ├── customer_pipeline_dag.py
│   │   └── daily_sales_summary_dag.py
│   ├── dbt_project/            # dbt project
│   │   ├── dbt_project.yml
│   │   ├── profiles.yml
│   │   ├── models/
│   │   │   ├── bronze/        # Staging models
│   │   │   └── silver/        # Dimensional models
│   │   └── seeds/             # Reference data
│   └── requirements.txt        # Python dependencies
└── postgres/
    └── init/                   # Database initialization scripts
        └── 01_create_databases.sql
```

## Services

| Service | Port | Description |
|---------|------|-------------|
| Airflow Web UI | 8080 | Apache Airflow dashboard |
| PostgreSQL (Data) | 5435 | Bronze/Silver databases |
| PostgreSQL (Airflow) | 5436 | Airflow metadata database |

## Data Pipeline

### DAGs

1. **customer_analytics_pipeline**
   - Runs dbt models to transform customer and order data
   - Schedule: Daily at 2 AM
   - Layers: Bronze → Silver

2. **daily_sales_summary**
   - Generates daily sales reports
   - Schedule: Daily at 3 AM
   - Depends on: customer_analytics_pipeline

### Data Layers

- **Bronze Layer**: Raw source data (customers, orders, order_items)
- **Silver Layer**: Cleaned and conformed dimensional models (dim_customers, fct_orders)

## Documentation

See [docs/data_pipeline_setup.md](../docs/data_pipeline_setup.md) for comprehensive documentation including:
- Architecture details
- Test scenarios
- Troubleshooting guide
- API integration examples

## Stopping the Environment

```bash
# Stop services
docker-compose down

# Stop and remove volumes (deletes all data)
docker-compose down -v
```

## Troubleshooting

### Airflow not starting
- Check logs: `docker logs dab-airflow`
- Ensure ports 8080, 5435, 5436 are available
- Increase Docker memory to 4GB+

### dbt commands fail
- Install dbt: `docker exec -it dab-airflow pip install dbt-core dbt-postgres`
- Restart Airflow: `docker-compose restart airflow`

### Database connection errors
- Check PostgreSQL is healthy: `docker-compose ps`
- Verify connection from Airflow: `docker exec -it dab-airflow psql -h postgres-data -U postgres -d bronze_db`
