#!/bin/bash

# Start script for Data Pipeline Test Environment
# This script starts the test environment and provides helpful information

set -e

echo "======================================"
echo "Data Pipeline Test Environment"
echo "======================================"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running. Please start Docker Desktop."
    exit 1
fi

echo "✓ Docker is running"
echo ""

# Start services
echo "Starting services..."
docker-compose up -d

echo ""
echo "Waiting for services to be ready..."
echo "(This may take 2-3 minutes on first run)"
echo ""

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL..."
until docker exec dab-postgres-data pg_isready -U postgres > /dev/null 2>&1; do
    sleep 2
done
echo "✓ PostgreSQL is ready"

# Wait for Airflow to be ready
echo "Waiting for Airflow..."
sleep 30  # Give Airflow time to initialize
echo "✓ Airflow should be ready"

echo ""
echo "======================================"
echo "Services Started Successfully!"
echo "======================================"
echo ""
echo "Next steps:"
echo ""
echo "1. Install dbt in Airflow container:"
echo "   docker exec -it dab-airflow pip install dbt-core==1.7.4 dbt-postgres==1.7.4"
echo ""
echo "2. Access Airflow UI:"
echo "   URL: http://localhost:8080"
echo "   Username: admin"
echo "   Password: admin"
echo ""
echo "3. Enable DAGs in the Airflow UI"
echo "   - Toggle customer_analytics_pipeline to ON"
echo "   - Click the play button to trigger a run"
echo ""
echo "4. Test DAB ingestion:"
echo "   cd ../backend"
echo "   dab ingest airflow --base-url http://localhost:8080 --instance local-test"
echo ""
echo "5. Verify capsules created:"
echo "   dab capsules --type airflow_dag"
echo "   dab capsules --type airflow_task"
echo ""
echo "======================================"
echo ""
echo "To view logs:"
echo "  docker-compose logs -f"
echo ""
echo "To stop services:"
echo "  docker-compose down"
echo ""
echo "For full documentation, see:"
echo "  ../docs/data_pipeline_setup.md"
echo ""
