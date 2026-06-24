from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

default_args = {
    "owner": "churn-analytics",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="churn_etl_pipeline",
    default_args=default_args,
    description="Daily churn ETL pipeline",
    schedule="@daily",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["churn", "etl"],
) as dag:

    run_etl = BashOperator(
        task_id="run_churn_etl",
        bash_command="cd /opt/airflow/project && python etl/pipeline.py",
        env={
            "DATABASE_URL": "postgresql://churn_user:churn_pass@postgres:5432/churn_db",
            "DATA_PATH": "data/raw/telco_churn.csv",
        },
    )
