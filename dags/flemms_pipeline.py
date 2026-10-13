"""Airflow DAG: FLEMMS 2024 digital divide pipeline.

    ingest_survey_files --> profile_raw_sources
            |                      (parallel)
            v
    validate_raw_gate  <-- fail-fast: file presence, schema, checksums,
            |              row counts, constraint spot-check BEFORE staging
            v
    build_staging --> validate_staging --> build_curated --> validate_curated --> load_warehouse
                                               ^                     |
    fetch_region_codes ------------------------+                     +--> benchmark_file_formats
                                                                     +--> generate_charts

Each task calls a function in src/, the same code that pipeline.py runs from a
terminal. Tasks pass data through the data/ layers (files), not through XCom;
XCom only carries small summaries (row counts, file names).

Failure handling:
  * every task retries twice with exponential backoff (network blips, DB restarts)
  * data-quality failures raise AirflowFailException: they fail immediately without
    retrying, because re-running on the same bad data would give the same result
  * on_failure_callback writes a one-line summary (task, run, error) to the task log
"""
import logging
from datetime import datetime, timedelta

from airflow.sdk import Param, dag, task
from airflow.sdk.exceptions import AirflowFailException

log = logging.getLogger(__name__)


def notify_failure(context) -> None:
    ti = context["task_instance"]
    log.error("TASK FAILED | dag=%s task=%s run=%s try=%s | error=%s",
              ti.dag_id, ti.task_id, context["run_id"], ti.try_number, context.get("exception"))


default_args = {
    "owner": "flemms-team",
    "retries": 2,
    "retry_delay": timedelta(minutes=1),
    "retry_exponential_backoff": True,
    "execution_timeout": timedelta(minutes=30),
    "on_failure_callback": notify_failure,
}


@dag(
    dag_id="flemms_digital_divide_pipeline",
    description="FLEMMS 2024 Vol 1 + Vol 2 + PSGC regions -> raw -> staging -> curated -> PostgreSQL",
    schedule="@monthly",  # re-checks sources monthly; reruns are idempotent
    start_date=datetime(2026, 10, 1),
    catchup=False,
    max_active_runs=1,  # two runs must never write the same layer files at once
    default_args=default_args,
    params={
        "run_format_benchmark": Param(True, type="boolean",
                                      description="Compare CSV / JSON / Parquet size and speed"),
    },
    tags=["flemms", "data-engineering"],
)
def flemms_digital_divide_pipeline():

    @task
    def fetch_region_codes(**context) -> dict:
        from src.extract.fetch_psgc import fetch_regions
        return fetch_regions(context["run_id"])

    @task
    def ingest_survey_files(**context) -> dict:
        from src.extract.ingest_survey import ingest_survey_files as ingest
        manifest = ingest(context["run_id"])
        return {t: f["data_lines"] for t, f in manifest["files"].items()}

    @task
    def profile_raw_sources(**context) -> list:
        from src.analysis.profiling import profile_sources
        return profile_sources(context["run_id"])

    @task
    def validate_raw_gate(**context) -> int:
        """Fail-fast gate: file presence, schema, checksums, row counts, constraints.

        Runs after ingestion (so the manifest exists) and before staging, so that
        build_staging never starts on missing, truncated or schema-broken raw files.
        Raises AirflowFailException on any error-severity failure; warnings are
        logged and reported but do not block the pipeline.
        """
        from src.validation.checks import DataQualityError
        from src.validation.raw_gate import validate_raw
        try:
            return len(validate_raw(context["run_id"]))
        except DataQualityError as exc:
            raise AirflowFailException(str(exc)) from exc

    @task
    def build_staging(**context) -> dict:
        from src.transform.staging import build_staging as run
        return run(context["run_id"])

    @task
    def validate_staging(**context) -> int:
        from src.validation.checks import DataQualityError
        from src.validation.layers import validate_staging as run
        try:
            return len(run(context["run_id"]))
        except DataQualityError as exc:
            raise AirflowFailException(str(exc)) from exc

    @task
    def build_curated(**context) -> dict:
        from src.transform.curated import build_curated as run
        return run(context["run_id"])

    @task
    def validate_curated(**context) -> int:
        from src.validation.checks import DataQualityError
        from src.validation.layers import validate_curated as run
        try:
            return len(run(context["run_id"]))
        except DataQualityError as exc:
            raise AirflowFailException(str(exc)) from exc

    @task
    def load_warehouse(**context) -> dict:
        from src.load.warehouse import load_warehouse as run
        return run(context["run_id"])

    @task
    def generate_charts(**context) -> list:
        """Generate PNG summary charts for the demo and README.

        Produces:
          outputs/charts/functional_literacy_by_access_tier.png
          outputs/charts/home_internet_by_region.png
          outputs/charts/sample_sizes_region_tier.png
        """
        from src.analysis.charts import generate_charts as run
        return run(context["run_id"])

    @task
    def benchmark_file_formats(**context) -> str:
        if not context["params"]["run_format_benchmark"]:
            log.info("Skipped: run_format_benchmark is false")
            return "skipped"
        from src.analysis.format_benchmark import benchmark_formats
        return benchmark_formats(context["run_id"])

    regions = fetch_region_codes()
    ingested = ingest_survey_files()
    raw_gate = validate_raw_gate()
    staged = build_staging()
    curated = build_curated()
    checked_curated = validate_curated()

    # profile_raw_sources runs in parallel with the raw gate – profiling never
    # blocks staging; the gate does.
    ingested >> [profile_raw_sources(), raw_gate]
    raw_gate >> staged
    staged >> validate_staging() >> curated
    regions >> curated
    curated >> checked_curated >> [load_warehouse(), benchmark_file_formats(), generate_charts()]


flemms_digital_divide_pipeline()
