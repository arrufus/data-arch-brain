"""
Customer & Order Pipeline DAG

This DAG represents the processing pipeline for customer and order data capsules:
1. stg_customers (Staging) - URN: urn:dcs:dbt:model:jaffle_shop.staging:stg_customers
2. stg_orders (Staging) - URN: urn:dcs:dbt:model:jaffle_shop.staging:stg_orders
3. orders_fact (Mart) - URN: urn:dcs:dbt:model:jaffle_shop.marts:orders_fact

This pipeline demonstrates:
- Bronze → Silver → Gold medallion architecture
- Customer dimension and order fact processing
- Data quality checks and profiling
- Business term linkage (customer_id, order_status)
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
import logging

# Default arguments
default_args = {
    'owner': 'data_platform_team',
    'depends_on_past': False,
    'email_on_failure': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=3),
}

# DAG definition
dag = DAG(
    'customer_order_pipeline',
    default_args=default_args,
    description='Customer and order data processing pipeline',
    schedule_interval='0 */6 * * *',  # Run every 6 hours
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['customer', 'orders', 'analytics', 'jaffle_shop'],
    max_active_runs=2,
)

def stage_customers(**context):
    """
    Stage customer dimension data.
    Data Capsule: stg_customers
    Source: Raw customer data from application database
    Quality Rules: customer_id uniqueness, not null constraints
    """
    logger = logging.getLogger(__name__)
    logger.info("Processing stg_customers capsule")
    logger.info("URN: urn:dcs:dbt:model:jaffle_shop.staging:stg_customers")
    logger.info("Layer: Silver (Staging/Dimension)")
    logger.info("Type: Dimension 1 (customer dimension)")

    execution_date = context['execution_date']
    logger.info(f"Staging customers for date: {execution_date}")

    # Simulate staging process
    logger.info("Extracting from raw.customers table...")
    logger.info("✓ Cleaning customer names")
    logger.info("✓ Standardizing email formats")
    logger.info("✓ Validating customer_id uniqueness")
    logger.info("✓ Checking for null customer_id values")
    logger.info("✓ Deduplicating records")

    logger.info("Customer staging complete - PASSED")
    return {
        "status": "staged",
        "customer_count": 1500,
        "new_customers": 45,
        "updated_customers": 12
    }

def profile_customer_data(**context):
    """
    Profile customer data quality metrics.
    Generates statistics for monitoring and governance.
    """
    logger = logging.getLogger(__name__)
    logger.info("Profiling stg_customers data quality")

    ti = context['task_instance']
    customer_results = ti.xcom_pull(task_ids='stage_customers')

    logger.info("Data Quality Profile:")
    logger.info(f"  Total customers: {customer_results['customer_count']}")
    logger.info(f"  New customers: {customer_results['new_customers']}")
    logger.info(f"  Updated customers: {customer_results['updated_customers']}")
    logger.info("  Completeness: 100% (no null primary keys)")
    logger.info("  Uniqueness: 100% (no duplicate customer_ids)")
    logger.info("  Validity: 98.5% (email format validation)")

    logger.info("Customer data profiling complete")

def stage_orders(**context):
    """
    Stage order fact data.
    Data Capsule: stg_orders
    Source: Raw orders data
    Upstream Dependency: stg_customers (FK relationship)
    Business Terms: order_status, order_date
    """
    logger = logging.getLogger(__name__)
    logger.info("Processing stg_orders capsule")
    logger.info("URN: urn:dcs:dbt:model:jaffle_shop.staging:stg_orders")
    logger.info("Layer: Silver (Staging/Fact)")
    logger.info("Type: Fact table (order transactions)")

    execution_date = context['execution_date']
    logger.info(f"Staging orders for date: {execution_date}")

    # Simulate staging process
    logger.info("Extracting from raw.orders table...")
    logger.info("✓ Validating foreign key to stg_customers")
    logger.info("✓ Parsing order_date timestamps")
    logger.info("✓ Standardizing order_status values")
    logger.info("✓ Calculating order amounts")
    logger.info("✓ Checking for orphaned orders (no matching customer)")

    logger.info("Order staging complete - PASSED")
    return {
        "status": "staged",
        "order_count": 8500,
        "new_orders": 320,
        "order_statuses": {
            "completed": 7200,
            "pending": 800,
            "cancelled": 500
        }
    }

def validate_order_referential_integrity(**context):
    """
    Validate referential integrity between orders and customers.
    Quality Rule: All orders must have valid customer_id references.
    """
    logger = logging.getLogger(__name__)
    logger.info("Validating order → customer referential integrity")

    ti = context['task_instance']
    customer_results = ti.xcom_pull(task_ids='stage_customers')
    order_results = ti.xcom_pull(task_ids='stage_orders')

    # Simulate FK validation
    logger.info(f"Checking {order_results['order_count']} orders...")
    logger.info(f"Valid customer references: {customer_results['customer_count']}")
    logger.info("✓ All orders have valid customer_id values")
    logger.info("✓ No orphaned orders detected")

    logger.info("Referential integrity check PASSED")

def build_orders_fact(**context):
    """
    Build orders_fact analytical mart.
    Data Capsule: orders_fact
    Upstream Dependencies: stg_customers, stg_orders
    Transformation: Join customers and orders, calculate metrics
    """
    logger = logging.getLogger(__name__)
    logger.info("Building orders_fact mart")
    logger.info("URN: urn:dcs:dbt:model:jaffle_shop.marts:orders_fact")
    logger.info("Layer: Gold (Analytical Mart)")
    logger.info("Type: Fact table with enriched dimensions")

    execution_date = context['execution_date']
    logger.info(f"Building fact table for date: {execution_date}")

    # Simulate mart build
    logger.info("Running dbt model...")
    logger.info("✓ Joining stg_customers and stg_orders")
    logger.info("✓ Calculating customer lifetime value")
    logger.info("✓ Aggregating order metrics by customer")
    logger.info("✓ Enriching with customer attributes")
    logger.info("✓ Creating surrogate keys for analytics")

    ti = context['task_instance']
    order_results = ti.xcom_pull(task_ids='stage_orders')

    logger.info("Orders fact build complete - PASSED")
    return {
        "status": "built",
        "fact_count": order_results['order_count'],
        "total_order_value": 1245600.00,
        "avg_order_value": 146.54
    }

def test_orders_fact(**context):
    """
    Run data quality tests on orders_fact.
    Tests: not null, unique combinations, accepted values, relationships
    """
    logger = logging.getLogger(__name__)
    logger.info("Running dbt tests on orders_fact")

    logger.info("Executing quality rules:")
    logger.info("✓ Test: order_id is not null")
    logger.info("✓ Test: customer_id is not null")
    logger.info("✓ Test: order_date is not null")
    logger.info("✓ Test: order_status in ('completed', 'pending', 'cancelled')")
    logger.info("✓ Test: order_amount >= 0")
    logger.info("✓ Test: unique combination of (order_id, customer_id)")

    logger.info("All tests PASSED")

def update_data_catalog(**context):
    """
    Update DCS catalog with pipeline execution metadata.
    This would typically call the DCS API to update operational metadata.
    """
    logger = logging.getLogger(__name__)
    logger.info("Updating Data Capsule Server catalog")

    ti = context['task_instance']
    customer_results = ti.xcom_pull(task_ids='stage_customers')
    order_results = ti.xcom_pull(task_ids='stage_orders')
    fact_results = ti.xcom_pull(task_ids='build_orders_fact')

    execution_date = context['execution_date']

    # Simulate catalog update (would be actual API calls in production)
    logger.info("Updating capsule versions and metadata:")
    logger.info(f"  stg_customers: {customer_results['customer_count']} rows")
    logger.info(f"  stg_orders: {order_results['order_count']} rows")
    logger.info(f"  orders_fact: {fact_results['fact_count']} rows")
    logger.info(f"  Last updated: {execution_date}")
    logger.info(f"  Pipeline status: SUCCESS")

    logger.info("✓ Catalog updated successfully")
    logger.info("Data lineage graph updated in DCS")

def notify_completion(**context):
    """
    Notify completion and provide metrics summary.
    """
    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("Customer & Order Pipeline Completed Successfully")
    logger.info("=" * 60)

    ti = context['task_instance']
    customer_results = ti.xcom_pull(task_ids='stage_customers')
    order_results = ti.xcom_pull(task_ids='stage_orders')
    fact_results = ti.xcom_pull(task_ids='build_orders_fact')

    logger.info("Pipeline Summary:")
    logger.info(f"  Customers processed: {customer_results['customer_count']}")
    logger.info(f"  Orders processed: {order_results['order_count']}")
    logger.info(f"  Fact records created: {fact_results['fact_count']}")
    logger.info(f"  Total order value: ${fact_results['total_order_value']:,.2f}")
    logger.info(f"  Average order value: ${fact_results['avg_order_value']:.2f}")
    logger.info("=" * 60)

    logger.info("All data capsules updated and available for consumption")

# Task definitions
stage_customers_task = PythonOperator(
    task_id='stage_customers',
    python_callable=stage_customers,
    dag=dag,
)

profile_customers_task = PythonOperator(
    task_id='profile_customer_data',
    python_callable=profile_customer_data,
    dag=dag,
)

stage_orders_task = PythonOperator(
    task_id='stage_orders',
    python_callable=stage_orders,
    dag=dag,
)

validate_fk_task = PythonOperator(
    task_id='validate_order_referential_integrity',
    python_callable=validate_order_referential_integrity,
    dag=dag,
)

build_fact_task = PythonOperator(
    task_id='build_orders_fact',
    python_callable=build_orders_fact,
    dag=dag,
)

test_fact_task = PythonOperator(
    task_id='test_orders_fact',
    python_callable=test_orders_fact,
    dag=dag,
)

update_catalog_task = PythonOperator(
    task_id='update_data_catalog',
    python_callable=update_data_catalog,
    dag=dag,
)

notify_task = PythonOperator(
    task_id='notify_completion',
    python_callable=notify_completion,
    dag=dag,
)

# Define pipeline flow (matches DCS lineage)
# Process customer dimension first, then orders, then build fact table
stage_customers_task >> profile_customers_task
stage_customers_task >> stage_orders_task >> validate_fk_task
[profile_customers_task, validate_fk_task] >> build_fact_task >> test_fact_task >> update_catalog_task >> notify_task
