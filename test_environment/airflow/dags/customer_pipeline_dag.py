"""
Customer Analytics Pipeline DAG

This DAG orchestrates the customer analytics data pipeline using dbt.
It processes data from the bronze layer (raw sources) through the silver layer
(dimensional models) to create analytics-ready datasets.

Pipeline stages:
1. Bronze Layer: Staging models that clean and standardize raw data
2. Silver Layer: Dimensional models (facts and dimensions)
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
import os

# Default arguments for all tasks
default_args = {
    'owner': 'data_engineering',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# DAG definition
dag = DAG(
    'customer_analytics_pipeline',
    default_args=default_args,
    description='Customer analytics data pipeline with dbt',
    schedule_interval='0 2 * * *',  # Run daily at 2 AM
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['customer', 'analytics', 'dbt', 'bronze', 'silver'],
)

# Environment setup
DBT_PROJECT_DIR = os.getenv('DBT_PROJECT_DIR', '/opt/airflow/dbt_project')
DBT_PROFILES_DIR = os.getenv('DBT_PROFILES_DIR', '/opt/airflow/dbt_project')
DBT_TARGET = 'prod'

def print_pipeline_info(**context):
    """Print pipeline execution information."""
    print(f"Execution date: {context['execution_date']}")
    print(f"DBT project dir: {DBT_PROJECT_DIR}")
    print(f"DBT target: {DBT_TARGET}")
    print("Starting customer analytics pipeline...")

# Task: Print pipeline info
pipeline_start = PythonOperator(
    task_id='pipeline_start',
    python_callable=print_pipeline_info,
    dag=dag,
)

# Task: Install dbt dependencies (if any packages are used)
dbt_deps = BashOperator(
    task_id='dbt_deps',
    bash_command=f'cd {DBT_PROJECT_DIR} && dbt deps --profiles-dir {DBT_PROFILES_DIR} --target {DBT_TARGET}',
    dag=dag,
)

# Task: Run dbt seed (load country_codes reference data)
dbt_seed = BashOperator(
    task_id='dbt_seed',
    bash_command=f'cd {DBT_PROJECT_DIR} && dbt seed --profiles-dir {DBT_PROFILES_DIR} --target {DBT_TARGET}',
    dag=dag,
)

# Task: Run bronze layer models (staging)
dbt_run_bronze = BashOperator(
    task_id='dbt_run_bronze',
    bash_command=f'cd {DBT_PROJECT_DIR} && dbt run --profiles-dir {DBT_PROFILES_DIR} --target {DBT_TARGET} --select tag:bronze',
    dag=dag,
)

# Task: Test bronze layer models
dbt_test_bronze = BashOperator(
    task_id='dbt_test_bronze',
    bash_command=f'cd {DBT_PROJECT_DIR} && dbt test --profiles-dir {DBT_PROFILES_DIR} --target {DBT_TARGET} --select tag:bronze',
    dag=dag,
)

# Task: Run silver layer models (dimensional)
dbt_run_silver = BashOperator(
    task_id='dbt_run_silver',
    bash_command=f'cd {DBT_PROJECT_DIR} && dbt run --profiles-dir {DBT_PROFILES_DIR} --target {DBT_TARGET} --select tag:silver',
    dag=dag,
)

# Task: Test silver layer models
dbt_test_silver = BashOperator(
    task_id='dbt_test_silver',
    bash_command=f'cd {DBT_PROJECT_DIR} && dbt test --profiles-dir {DBT_PROFILES_DIR} --target {DBT_TARGET} --select tag:silver',
    dag=dag,
)

# Task: Generate dbt documentation
dbt_docs_generate = BashOperator(
    task_id='dbt_docs_generate',
    bash_command=f'cd {DBT_PROJECT_DIR} && dbt docs generate --profiles-dir {DBT_PROFILES_DIR} --target {DBT_TARGET}',
    dag=dag,
)

def print_pipeline_complete(**context):
    """Print pipeline completion message."""
    print("Customer analytics pipeline completed successfully!")
    print(f"Models processed: bronze layer -> silver layer")
    print(f"Documentation generated at: {DBT_PROJECT_DIR}/target")

# Task: Pipeline completion
pipeline_complete = PythonOperator(
    task_id='pipeline_complete',
    python_callable=print_pipeline_complete,
    dag=dag,
)

# Define task dependencies (pipeline flow)
pipeline_start >> dbt_deps >> dbt_seed >> dbt_run_bronze >> dbt_test_bronze >> dbt_run_silver >> dbt_test_silver >> dbt_docs_generate >> pipeline_complete
