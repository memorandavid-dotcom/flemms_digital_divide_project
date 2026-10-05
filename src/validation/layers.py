"""Validation entry points for each layer (called by the DAG and by pipeline.py)."""
import pandas as pd

from src.config import layer_path
from src.extract.ingest_survey import survey_tables
from src.transform.curated import read_person_profile
from src.utils.io_utils import read_json
from src.validation.checks import CheckResult, check_row_reconciliation, run_validation

CURATED_TABLES = ["dim_region", "household", "member", "literacy_assessment", "agg_literacy_digital"]


def validate_staging(batch_id: str) -> list[CheckResult]:
    staging = layer_path("staging")
    tables = {item["table"]: pd.read_parquet(staging / f"{item['table']}.parquet") for item in survey_tables()}

    manifest = read_json(layer_path("raw") / "_manifests" / "latest.json")
    dedup = read_json(layer_path("outputs") / "staging" / "dedup_report.json")
    reconciliation = []
    for name, df in tables.items():
        stats = dedup["tables"][name]
        removed = stats["exact_duplicates_removed"] + stats["key_duplicates_removed"]
        reconciliation.append(check_row_reconciliation(name, manifest["files"][name]["data_lines"], len(df), removed))

    return run_validation("staging", tables, batch_id, extra_results=reconciliation)


def validate_curated(batch_id: str) -> list[CheckResult]:
    curated = layer_path("curated")
    tables = {name: pd.read_parquet(curated / f"{name}.parquet") for name in CURATED_TABLES}
    tables["person_profile"] = read_person_profile()
    return run_validation("curated", tables, batch_id)
