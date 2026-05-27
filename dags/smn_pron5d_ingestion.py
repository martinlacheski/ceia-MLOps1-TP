from __future__ import annotations

from datetime import UTC, datetime
import os
from pathlib import Path
import sys

import boto3
from airflow.decorators import dag, task


PROJECT_ROOT = Path("/opt/ml-rainops")
SRC_DIR = PROJECT_ROOT / "src"
DATA_DIR = PROJECT_ROOT / "data"
LOCAL_OUTPUT = DATA_DIR / "processed" / "smn_pron5d_daily.jsonl"
S3_BUCKET = os.getenv("DATA_REPO_BUCKET_NAME", "data")
S3_ENDPOINT_URL = os.getenv("AWS_ENDPOINT_URL_S3", "http://minio:9000")

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


@dag(
    dag_id="smn_pron5d_ingestion",
    description="Ingesta el pronóstico SMN pron5d de Misiones y lo persiste en data local y MinIO.",
    schedule=None,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["smn", "pron5d", "rainops"],
)
def smn_pron5d_ingestion():
    @task
    def download_parse_and_save_local() -> dict[str, str | int]:
        from ceml_rain.smn import run_pron5d_ingestion

        payload = run_pron5d_ingestion(output_path=LOCAL_OUTPUT)
        line_count = len([line for line in payload.splitlines() if line.strip()])

        return {
            "local_path": str(LOCAL_OUTPUT),
            "line_count": line_count,
        }

    @task
    def upload_to_minio(local_result: dict[str, str | int]) -> dict[str, str | int]:
        local_path = Path(str(local_result["local_path"]))
        execution_date = datetime.now(UTC).date().isoformat()
        s3_key = f"smn/pron5d/processed/forecast_daily_precipitation_{execution_date}.jsonl"

        s3_client = boto3.client("s3", endpoint_url=S3_ENDPOINT_URL)
        s3_client.upload_file(str(local_path), S3_BUCKET, s3_key)

        return {
            "bucket": S3_BUCKET,
            "key": s3_key,
            "line_count": int(local_result["line_count"]),
        }

    upload_to_minio(download_parse_and_save_local())


smn_pron5d_ingestion()
