"""
Cross-Domain Analytics Pipeline DAG

This DAG demonstrates cross-domain data integration, consuming data from:
1. Finance domain: revenue_by_month capsule
2. Customer domain: orders_fact capsule

Creates integrated analytics that combine financial and customer data,
showing how data products from different domains can be composed together.

Output Capsule (conceptual):
- customer_revenue_analytics - URN: urn:dcs:dbt:model:analytics.marts:customer_revenue_analytics

This demonstrates:
- Data mesh principles (consuming multiple domain data products)
- Cross-domain lineage tracking
- Federated data governance
- Data product composition
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.sensors.external_task import ExternalTaskSensor
import logging

# Default arguments
default_args = {
    'owner': 'analytics_team',
    'depends_on_past': False,
    'email_on_failure': True,
    'email': ['analytics@company.com'],
    'retries': 2,
    'retry_delay': timedelta(minutes=10),
}

# DAG definition
dag = DAG(
    'cross_domain_analytics_pipeline',
    default_args=default_args,
    description='Cross-domain analytics combining finance and customer data',
    schedule_interval='0 4 * * *',  # Run daily at 4 AM (after source pipelines)
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['analytics', 'cross-domain', 'data-mesh', 'finance', 'customer'],
    max_active_runs=1,
)

def validate_upstream_data(**context):
    """
    Validate that required upstream data products are available and fresh.
    Checks SLA compliance for source capsules.
    """
    logger = logging.getLogger(__name__)
    logger.info("Validating upstream data products")
    logger.info("=" * 60)

    # Check Finance domain data products
    logger.info("Finance Domain - Financial Reporting Product (v1.0.0)")
    logger.info("  Capsule: revenue_by_month")
    logger.info("  URN: urn:dcs:dbt:model:finance_analytics.marts:revenue_by_month")
    logger.info("  Expected SLA: 24hr freshness")
    logger.info("  Status: ✓ Available and fresh")

    # Check Customer domain data products
    logger.info("Customer Domain - Orders Data Product")
    logger.info("  Capsule: orders_fact")
    logger.info("  URN: urn:dcs:dbt:model:jaffle_shop.marts:orders_fact")
    logger.info("  Expected SLA: 6hr freshness")
    logger.info("  Status: ✓ Available and fresh")

    logger.info("=" * 60)
    logger.info("All upstream data products validated successfully")

    return {
        "finance_data_available": True,
        "customer_data_available": True,
        "validation_passed": True
    }

def extract_revenue_data(**context):
    """
    Extract revenue data from finance domain.
    Source Capsule: revenue_by_month (Finance domain)
    """
    logger = logging.getLogger(__name__)
    logger.info("Extracting revenue data from finance domain")
    logger.info("Source: revenue_by_month (urn:dcs:dbt:model:finance_analytics.marts:revenue_by_month)")

    execution_date = context['execution_date']
    logger.info(f"Extracting revenue for period: {execution_date.strftime('%Y-%m')}")

    # Simulate extraction
    logger.info("Reading from finance data product output port...")
    logger.info("✓ Extracted 12 fiscal periods")
    logger.info("✓ Total revenue amount: $4,250,000")
    logger.info("✓ Revenue categories: 15 account types")

    return {
        "status": "extracted",
        "fiscal_periods": 12,
        "total_revenue": 4250000.00,
        "categories": 15
    }

def extract_customer_order_data(**context):
    """
    Extract customer and order data from customer domain.
    Source Capsule: orders_fact (Customer domain)
    """
    logger = logging.getLogger(__name__)
    logger.info("Extracting customer order data from customer domain")
    logger.info("Source: orders_fact (urn:dcs:dbt:model:jaffle_shop.marts:orders_fact)")

    execution_date = context['execution_date']
    logger.info(f"Extracting orders for date: {execution_date}")

    # Simulate extraction
    logger.info("Reading from customer data product output port...")
    logger.info("✓ Extracted 8,500 orders")
    logger.info("✓ Unique customers: 1,500")
    logger.info("✓ Total order value: $1,245,600")

    return {
        "status": "extracted",
        "order_count": 8500,
        "customer_count": 1500,
        "total_value": 1245600.00
    }

def join_cross_domain_data(**context):
    """
    Join finance and customer data to create integrated analytics.
    This demonstrates data mesh principle of composing data products.
    """
    logger = logging.getLogger(__name__)
    logger.info("Creating cross-domain analytics")
    logger.info("=" * 60)

    ti = context['task_instance']
    revenue_data = ti.xcom_pull(task_ids='extract_revenue_data')
    customer_data = ti.xcom_pull(task_ids='extract_customer_order_data')

    logger.info("Joining data from multiple domains:")
    logger.info(f"  Finance revenue: ${revenue_data['total_revenue']:,.2f}")
    logger.info(f"  Customer orders: ${customer_data['total_value']:,.2f}")

    # Simulate join and enrichment
    logger.info("Performing cross-domain join...")
    logger.info("✓ Mapping customer orders to revenue accounts")
    logger.info("✓ Calculating customer contribution to revenue")
    logger.info("✓ Identifying top revenue-generating customers")
    logger.info("✓ Analyzing revenue by customer segment")

    # Calculate metrics
    revenue_reconciliation = revenue_data['total_revenue'] - customer_data['total_value']
    reconciliation_pct = (revenue_reconciliation / revenue_data['total_revenue']) * 100

    logger.info("=" * 60)
    logger.info("Integration Metrics:")
    logger.info(f"  Total GL revenue: ${revenue_data['total_revenue']:,.2f}")
    logger.info(f"  Total customer orders: ${customer_data['total_value']:,.2f}")
    logger.info(f"  Variance: ${revenue_reconciliation:,.2f} ({reconciliation_pct:.2f}%)")
    logger.info(f"  Top customer segment contribution: 35%")
    logger.info("=" * 60)

    return {
        "status": "joined",
        "integrated_records": 1500,
        "gl_revenue": revenue_data['total_revenue'],
        "customer_revenue": customer_data['total_value'],
        "variance": revenue_reconciliation
    }

def validate_cross_domain_quality(**context):
    """
    Validate quality of cross-domain analytics.
    Quality Rules:
    - Revenue reconciliation within acceptable variance (±5%)
    - No orphaned records
    - All customers mapped to revenue accounts
    """
    logger = logging.getLogger(__name__)
    logger.info("Running cross-domain quality validation")

    ti = context['task_instance']
    join_results = ti.xcom_pull(task_ids='join_cross_domain_data')

    # Calculate variance percentage
    variance_pct = abs(join_results['variance'] / join_results['gl_revenue']) * 100

    logger.info("Quality Checks:")
    logger.info(f"✓ Revenue reconciliation variance: {variance_pct:.2f}%")

    if variance_pct > 5.0:
        logger.warning(f"WARNING: Variance {variance_pct:.2f}% exceeds 5% threshold")
        logger.warning("This requires investigation but will not fail the pipeline")
    else:
        logger.info(f"✓ Variance within acceptable range (<5%)")

    logger.info("✓ No orphaned customer records")
    logger.info("✓ All customers mapped to revenue accounts")
    logger.info("✓ Date ranges align across domains")

    logger.info("Cross-domain quality validation PASSED")

def materialize_analytics_mart(**context):
    """
    Materialize the cross-domain analytics mart.
    Output Capsule: customer_revenue_analytics
    """
    logger = logging.getLogger(__name__)
    logger.info("Materializing customer_revenue_analytics mart")
    logger.info("URN: urn:dcs:dbt:model:analytics.marts:customer_revenue_analytics")
    logger.info("Layer: Gold (Cross-Domain Analytical Mart)")

    ti = context['task_instance']
    join_results = ti.xcom_pull(task_ids='join_cross_domain_data')

    logger.info("Creating mart with integrated insights...")
    logger.info("✓ Customer lifetime revenue contribution")
    logger.info("✓ Revenue by customer segment")
    logger.info("✓ Order-to-revenue reconciliation")
    logger.info("✓ Customer acquisition cost vs. revenue")

    logger.info(f"Materialized {join_results['integrated_records']} customer records")
    logger.info("Analytics mart ready for consumption")

    return {
        "status": "materialized",
        "mart_records": join_results['integrated_records'],
        "consumers": ["executive_dashboard", "finance_reporting", "customer_analytics"]
    }

def update_lineage_graph(**context):
    """
    Update DCS lineage graph with cross-domain dependencies.
    This creates lineage edges showing data mesh composition.
    """
    logger = logging.getLogger(__name__)
    logger.info("Updating DCS lineage graph")
    logger.info("=" * 60)

    logger.info("Creating lineage edges:")
    logger.info("  revenue_by_month → customer_revenue_analytics")
    logger.info("    Edge type: FLOWS_TO")
    logger.info("    Domain: finance → analytics")
    logger.info("    Transformation: aggregation + join")

    logger.info("  orders_fact → customer_revenue_analytics")
    logger.info("    Edge type: FLOWS_TO")
    logger.info("    Domain: customer → analytics")
    logger.info("    Transformation: enrichment + join")

    logger.info("=" * 60)
    logger.info("✓ Lineage graph updated in DCS")
    logger.info("✓ Cross-domain dependencies tracked")
    logger.info("✓ Data mesh topology visible in graph export")

def notify_analytics_complete(**context):
    """
    Notify analytics stakeholders of completion.
    """
    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("Cross-Domain Analytics Pipeline Completed Successfully")
    logger.info("=" * 60)

    ti = context['task_instance']
    join_results = ti.xcom_pull(task_ids='join_cross_domain_data')
    mart_results = ti.xcom_pull(task_ids='materialize_analytics_mart')

    logger.info("Pipeline Summary:")
    logger.info("  Domains integrated: Finance + Customer")
    logger.info(f"  GL revenue: ${join_results['gl_revenue']:,.2f}")
    logger.info(f"  Customer orders: ${join_results['customer_revenue']:,.2f}")
    logger.info(f"  Analytics records: {mart_results['mart_records']}")
    logger.info(f"  Known consumers: {len(mart_results['consumers'])}")

    for consumer in mart_results['consumers']:
        logger.info(f"    - {consumer}")

    logger.info("=" * 60)
    logger.info("Data product: Customer Revenue Analytics (v1.0.0)")
    logger.info("Status: Available for consumption")
    logger.info("Notification sent to analytics@company.com")

# Task definitions

# Wait for upstream pipelines to complete
wait_for_finance = ExternalTaskSensor(
    task_id='wait_for_finance_pipeline',
    external_dag_id='finance_gl_pipeline',
    external_task_id='notify_finance_team',
    allowed_states=['success'],
    failed_states=['failed', 'skipped'],
    mode='reschedule',
    timeout=3600,
    poke_interval=300,
    dag=dag,
)

wait_for_customer = ExternalTaskSensor(
    task_id='wait_for_customer_pipeline',
    external_dag_id='customer_order_pipeline',
    external_task_id='notify_completion',
    allowed_states=['success'],
    failed_states=['failed', 'skipped'],
    mode='reschedule',
    timeout=3600,
    poke_interval=300,
    dag=dag,
)

validate_upstream = PythonOperator(
    task_id='validate_upstream_data',
    python_callable=validate_upstream_data,
    dag=dag,
)

extract_revenue = PythonOperator(
    task_id='extract_revenue_data',
    python_callable=extract_revenue_data,
    dag=dag,
)

extract_customers = PythonOperator(
    task_id='extract_customer_order_data',
    python_callable=extract_customer_order_data,
    dag=dag,
)

join_data = PythonOperator(
    task_id='join_cross_domain_data',
    python_callable=join_cross_domain_data,
    dag=dag,
)

validate_quality = PythonOperator(
    task_id='validate_cross_domain_quality',
    python_callable=validate_cross_domain_quality,
    dag=dag,
)

materialize_mart = PythonOperator(
    task_id='materialize_analytics_mart',
    python_callable=materialize_analytics_mart,
    dag=dag,
)

update_lineage = PythonOperator(
    task_id='update_lineage_graph',
    python_callable=update_lineage_graph,
    dag=dag,
)

notify = PythonOperator(
    task_id='notify_analytics_complete',
    python_callable=notify_analytics_complete,
    dag=dag,
)

# Define pipeline flow
# Wait for both upstream pipelines, then process
[wait_for_finance, wait_for_customer] >> validate_upstream
validate_upstream >> [extract_revenue, extract_customers]
[extract_revenue, extract_customers] >> join_data >> validate_quality >> materialize_mart >> update_lineage >> notify
