"""
Daily Sales Summary DAG

This DAG creates daily sales summaries by aggregating order data.
It demonstrates a simpler pipeline that depends on the customer analytics
pipeline outputs.

Pipeline stages:
1. Wait for customer pipeline completion
2. Run sales aggregation queries
3. Generate sales reports
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from airflow.sensors.external_task import ExternalTaskSensor
import os

# Default arguments
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
    'daily_sales_summary',
    default_args=default_args,
    description='Daily sales summary report generation',
    schedule_interval='0 3 * * *',  # Run daily at 3 AM (after customer pipeline)
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['sales', 'reporting', 'daily'],
)

DBT_PROJECT_DIR = os.getenv('DBT_PROJECT_DIR', '/opt/airflow/dbt_project')
DBT_PROFILES_DIR = os.getenv('DBT_PROFILES_DIR', '/opt/airflow/dbt_project')
DBT_TARGET = 'prod'

def print_sales_summary(**context):
    """Print sales summary information."""
    print(f"Generating sales summary for {context['execution_date']}")
    print("Processing orders from silver layer...")

# Task: Start pipeline
summary_start = PythonOperator(
    task_id='summary_start',
    python_callable=print_sales_summary,
    dag=dag,
)

# Task: Wait for customer analytics pipeline to complete
wait_for_customer_pipeline = ExternalTaskSensor(
    task_id='wait_for_customer_pipeline',
    external_dag_id='customer_analytics_pipeline',
    external_task_id='pipeline_complete',
    allowed_states=['success'],
    failed_states=['failed', 'skipped'],
    mode='reschedule',
    timeout=7200,  # 2 hours
    poke_interval=300,  # Check every 5 minutes
    dag=dag,
)

def generate_sales_report(**context):
    """Generate sales report."""
    print("Sales Summary Report")
    print("===================")
    print("Top customers by revenue")
    print("Order trends by status")
    print("Payment method distribution")
    print("Report generation complete!")

# Task: Generate report
generate_report = PythonOperator(
    task_id='generate_report',
    python_callable=generate_sales_report,
    dag=dag,
)

def summary_complete(**context):
    """Print completion message."""
    print("Daily sales summary pipeline completed!")

# Task: Complete
summary_complete_task = PythonOperator(
    task_id='summary_complete',
    python_callable=summary_complete,
    dag=dag,
)

# Define dependencies
summary_start >> wait_for_customer_pipeline >> generate_report >> summary_complete_task
