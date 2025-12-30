"""Finance GL Pipeline - Example Airflow DAG

This DAG demonstrates a typical finance data pipeline that:
1. Validates reference data (chart of accounts)
2. Loads GL transactions from staging
3. Reconciles balances and generates reports

This example is used to demonstrate the DCS Airflow integration features.
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.empty import EmptyOperator


default_args = {
    "owner": "finance-team",
    "depends_on_past": False,
    "email": ["finance@example.com"],
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "execution_timeout": timedelta(minutes=30),
}


def validate_chart_of_accounts(**context):
    """Validate the chart of accounts reference table.

    This task reads from:
    - dim.chart_of_accounts

    Validations:
    - No duplicate account codes
    - All required fields populated
    - Valid account types
    """
    print("Validating chart of accounts...")
    # In real implementation, would query database:
    # SELECT COUNT(DISTINCT account_code) FROM dim.chart_of_accounts
    print("✓ Chart of accounts validated")


def load_gl_transactions(**context):
    """Load GL transactions from staging to facts table.

    This task:
    - Reads from: staging.raw_transactions, dim.chart_of_accounts
    - Writes to: facts.gl_transactions

    SQL logic (conceptual):
    ```sql
    INSERT INTO facts.gl_transactions (
        transaction_id,
        account_id,
        amount,
        transaction_date,
        description
    )
    SELECT
        t.id,
        c.account_id,
        t.amount,
        t.posted_date,
        t.description
    FROM staging.raw_transactions t
    JOIN dim.chart_of_accounts c
        ON t.account_code = c.account_code
    WHERE t.posted_date >= CURRENT_DATE - INTERVAL '1 day'
      AND t.status = 'approved'
    ```
    """
    print("Loading GL transactions...")
    # In real implementation, would execute SQL transformation
    print("✓ Loaded 1,234 GL transactions")


def reconcile_gl_balances(**context):
    """Reconcile GL balances and generate report.

    This task:
    - Reads from: facts.gl_transactions, dim.chart_of_accounts
    - Writes to: reports.gl_reconciliation

    Generates:
    - Account balance summaries
    - Trial balance report
    - Out-of-balance flags
    """
    print("Reconciling GL balances...")
    # In real implementation, would compute balances:
    # SELECT account_id, SUM(amount) as balance
    # FROM facts.gl_transactions
    # GROUP BY account_id
    print("✓ Reconciliation complete")


# Define the DAG
with DAG(
    dag_id="finance_gl_pipeline",
    default_args=default_args,
    description="Daily GL transaction processing pipeline",
    schedule_interval="0 2 * * *",  # Daily at 2 AM
    start_date=datetime(2024, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["finance", "gl", "critical", "domain:finance"],
    doc_md=__doc__,
) as dag:

    # Start marker
    start = EmptyOperator(
        task_id="start",
        doc_md="Pipeline start marker"
    )

    # Task 1: Validate chart of accounts
    validate_coa = PythonOperator(
        task_id="validate_chart_of_accounts",
        python_callable=validate_chart_of_accounts,
        pool="default_pool",
        priority_weight=10,
        doc_md=validate_chart_of_accounts.__doc__,
    )

    # Task 2: Load GL transactions
    load_gl = PythonOperator(
        task_id="load_gl_transactions",
        python_callable=load_gl_transactions,
        pool="default_pool",
        priority_weight=20,
        doc_md=load_gl_transactions.__doc__,
    )

    # Task 3: Reconcile balances
    reconcile = PythonOperator(
        task_id="reconcile_gl_balances",
        python_callable=reconcile_gl_balances,
        pool="default_pool",
        priority_weight=5,
        doc_md=reconcile_gl_balances.__doc__,
    )

    # End marker
    end = EmptyOperator(
        task_id="end",
        doc_md="Pipeline end marker"
    )

    # Define task dependencies
    start >> validate_coa >> load_gl >> reconcile >> end


# Additional example DAG for demonstration
with DAG(
    dag_id="finance_monthly_close",
    default_args=default_args,
    description="Monthly financial close process",
    schedule_interval="0 3 1 * *",  # Monthly on 1st at 3 AM
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["finance", "monthly-close", "critical"],
) as monthly_dag:

    def run_monthly_close(**context):
        """Run monthly close process."""
        print("Running monthly close...")
        print("✓ Monthly close complete")

    monthly_close = PythonOperator(
        task_id="run_monthly_close",
        python_callable=run_monthly_close,
    )
