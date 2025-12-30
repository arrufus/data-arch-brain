"""
Finance General Ledger Pipeline DAG

This DAG represents the processing pipeline for finance data capsules:
1. chart_of_accounts (Master Data) - URN: urn:dcs:postgres:table:finance_erp.master:chart_of_accounts
2. gl_transactions (Fact Table) - URN: urn:dcs:postgres:table:finance_erp.facts:gl_transactions
3. revenue_by_month (Mart) - URN: urn:dcs:dbt:model:finance_analytics.marts:revenue_by_month

This pipeline demonstrates:
- Master data → Fact table → Analytical mart flow
- SOX/GAAP compliance requirements
- Data quality checks at each stage
- Financial data governance
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
import logging

# Default arguments
default_args = {
    'owner': 'finance_data_team',
    'depends_on_past': True,  # Finance data must be processed sequentially
    'email_on_failure': True,
    'email': ['finance-data@company.com'],
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

# DAG definition
dag = DAG(
    'finance_gl_pipeline',
    default_args=default_args,
    description='Finance General Ledger processing pipeline',
    schedule_interval='0 1 * * *',  # Run daily at 1 AM (after ERP batch loads)
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['finance', 'general_ledger', 'sox', 'gaap', 'tier-1', 'regulatory'],
    max_active_runs=1,  # Prevent concurrent runs for financial data
)

def validate_chart_of_accounts(**context):
    """
    Validate chart of accounts master data.
    Data Capsule: chart_of_accounts
    Quality Rules: Uniqueness, referential integrity, active accounts validation
    """
    logger = logging.getLogger(__name__)
    logger.info("Validating chart_of_accounts capsule")
    logger.info("URN: urn:dcs:postgres:table:finance_erp.master:chart_of_accounts")
    logger.info("Layer: Gold (Master Data)")
    logger.info("Compliance: SOX, GAAP")

    # Simulate validation checks
    logger.info("✓ Checking account_id uniqueness (PK constraint)")
    logger.info("✓ Checking parent_account_id referential integrity")
    logger.info("✓ Checking account hierarchy consistency")
    logger.info("✓ Verifying active accounts have valid types")
    logger.info("✓ Expected rows: ~500 accounts")

    logger.info("Chart of accounts validation complete - PASSED")
    return {"status": "valid", "account_count": 500}

def load_gl_transactions(**context):
    """
    Load and validate GL transactions fact table.
    Data Capsule: gl_transactions
    Upstream Dependency: chart_of_accounts (FK relationship)
    Quality Rules: Double-entry balance, foreign key integrity, date range validation
    """
    logger = logging.getLogger(__name__)
    logger.info("Processing gl_transactions capsule")
    logger.info("URN: urn:dcs:postgres:table:finance_erp.facts:gl_transactions")
    logger.info("Layer: Gold (Fact Table)")
    logger.info("Size: ~50M rows, 25 GB")
    logger.info("Partitioning: Range by transaction_date")
    logger.info("Compliance: SOX, GAAP, Audit Trail")

    # Simulate loading and validation
    logger.info("Loading transactions from ERP (NetSuite)...")
    logger.info("✓ Checking foreign key to chart_of_accounts")
    logger.info("✓ Validating double-entry accounting (debits = credits)")
    logger.info("✓ Checking transaction_status values")
    logger.info("✓ Validating fiscal_period format")
    logger.info("✓ Masking PII (created_by field)")

    execution_date = context['execution_date']
    logger.info(f"Processing transactions for date: {execution_date}")
    logger.info("GL transactions load complete - PASSED")

    return {
        "status": "loaded",
        "transaction_count": 125000,  # Daily transactions
        "debit_total": 15500000.00,
        "credit_total": 15500000.00,
        "balanced": True
    }

def check_double_entry_balance(**context):
    """
    Custom quality rule: Ensure debits equal credits.
    This is a critical SOX control for financial data integrity.
    """
    logger = logging.getLogger(__name__)
    logger.info("Running double-entry accounting validation (SOX Control ITGC-01)")

    # Get results from previous task
    ti = context['task_instance']
    gl_results = ti.xcom_pull(task_ids='load_gl_transactions')

    if gl_results['debit_total'] != gl_results['credit_total']:
        raise ValueError(
            f"Double-entry balance check FAILED: "
            f"Debits ({gl_results['debit_total']}) != Credits ({gl_results['credit_total']})"
        )

    logger.info(f"✓ Debit total: ${gl_results['debit_total']:,.2f}")
    logger.info(f"✓ Credit total: ${gl_results['credit_total']:,.2f}")
    logger.info(f"✓ Balanced: {gl_results['balanced']}")
    logger.info("Double-entry balance check PASSED")

def generate_revenue_by_month(**context):
    """
    Generate revenue_by_month analytical mart.
    Data Capsule: revenue_by_month
    Upstream Dependency: gl_transactions
    Transformation: Aggregation by fiscal_period and account_id
    Materialization: Incremental (dbt)
    """
    logger = logging.getLogger(__name__)
    logger.info("Generating revenue_by_month mart")
    logger.info("URN: urn:dcs:dbt:model:finance_analytics.marts:revenue_by_month")
    logger.info("Layer: Gold (Analytical Mart)")
    logger.info("Materialization: Incremental")
    logger.info("Compliance: SOX, GAAP, ASC 606 (Revenue Recognition)")

    # Simulate dbt incremental model run
    logger.info("Running dbt incremental model...")
    logger.info("✓ Filtering revenue accounts from gl_transactions")
    logger.info("✓ Aggregating by fiscal_period and account_id")
    logger.info("✓ Calculating revenue_amount and transaction_count")
    logger.info("✓ Applying ASC 606 revenue recognition rules")

    execution_date = context['execution_date']
    logger.info(f"Processing fiscal period: {execution_date.strftime('%Y-%m')}")
    logger.info("✓ Expected rows updated: ~12 (current fiscal year)")

    logger.info("Revenue mart generation complete - PASSED")
    return {
        "status": "generated",
        "rows_inserted": 12,
        "total_revenue": 4250000.00
    }

def validate_revenue_sla(**context):
    """
    Validate operational SLAs for revenue mart.
    SLA Requirements:
    - Freshness: 24 hours
    - Availability: 99.90%
    - Quality: 99.9% (no null revenue amounts)
    """
    logger = logging.getLogger(__name__)
    logger.info("Validating revenue_by_month operational SLAs")

    ti = context['task_instance']
    revenue_results = ti.xcom_pull(task_ids='generate_revenue_by_month')

    logger.info("✓ Freshness SLA: 24 hours - PASSED")
    logger.info("✓ Availability SLA: 99.90% - PASSED")
    logger.info("✓ Quality SLA: No null revenue amounts - PASSED")
    logger.info(f"✓ Total revenue for period: ${revenue_results['total_revenue']:,.2f}")

    logger.info("All SLAs validated successfully")

def notify_finance_team(**context):
    """
    Notify finance team of pipeline completion.
    Send metrics to data product consumers.
    """
    logger = logging.getLogger(__name__)
    logger.info("Finance GL pipeline completed successfully")
    logger.info("=" * 60)

    # Get metrics from all tasks
    ti = context['task_instance']
    coa_results = ti.xcom_pull(task_ids='validate_chart_of_accounts')
    gl_results = ti.xcom_pull(task_ids='load_gl_transactions')
    revenue_results = ti.xcom_pull(task_ids='generate_revenue_by_month')

    logger.info(f"Chart of Accounts: {coa_results['account_count']} accounts validated")
    logger.info(f"GL Transactions: {gl_results['transaction_count']} transactions processed")
    logger.info(f"Revenue Mart: {revenue_results['rows_inserted']} periods updated")
    logger.info(f"Total Revenue: ${revenue_results['total_revenue']:,.2f}")
    logger.info("=" * 60)

    logger.info("Data Products Updated:")
    logger.info("  1. Financial Reporting Product (v1.0.0)")
    logger.info("  2. General Ledger Data Product (v1.0.0)")
    logger.info("Notification sent to finance-data@company.com")

# Task definitions
validate_coa = PythonOperator(
    task_id='validate_chart_of_accounts',
    python_callable=validate_chart_of_accounts,
    dag=dag,
)

load_gl = PythonOperator(
    task_id='load_gl_transactions',
    python_callable=load_gl_transactions,
    dag=dag,
)

check_balance = PythonOperator(
    task_id='check_double_entry_balance',
    python_callable=check_double_entry_balance,
    dag=dag,
)

generate_revenue = PythonOperator(
    task_id='generate_revenue_by_month',
    python_callable=generate_revenue_by_month,
    dag=dag,
)

validate_sla = PythonOperator(
    task_id='validate_revenue_sla',
    python_callable=validate_revenue_sla,
    dag=dag,
)

notify = PythonOperator(
    task_id='notify_finance_team',
    python_callable=notify_finance_team,
    dag=dag,
)

# Define pipeline flow (matches DCS lineage)
# chart_of_accounts → gl_transactions → revenue_by_month
validate_coa >> load_gl >> check_balance >> generate_revenue >> validate_sla >> notify
