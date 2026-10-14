"""Raw gate: fail-fast checks on the raw CSV files, before staging starts.

The DAG runs this right after ingest_survey_files, and build_staging waits for it,
so staging never starts on a missing, truncated or broken file. The rules come from
the raw_files section of docs/data_contract.yaml. Checks, per file:

    file_presence  the file exists and is not empty
    checksum       the file still matches the SHA-256 recorded at ingestion
                   (catches a file replaced or edited after it was registered)
    schema         every required column is in the header
    row_count      at least min_rows data rows
    key_not_blank  key columns are never blank and always whole numbers
    weight         the survey weight is never blank or negative, and positive
                   exactly where the contract says (e.g. only on completed
                   Form 2 interviews; PSA gives every other result code weight 0)

Every check reads the whole file, not a sample. Results are written to
outputs/validation/raw_gate_latest.json like the other gates, and a failed
error-severity check raises DataQualityError, which fails the Airflow task.
"""
from pathlib import Path

import pandas as pd

from src.config import layer_path
from src.extract.ingest_survey import detect_encoding, locate, survey_tables
from src.utils.io_utils import read_json, sha256_of
from src.utils.logging_utils import get_logger
from src.validation.checks import CheckResult, load_contract, report_results

log = get_logger(__name__)


def _result(table: str, check: str, target: str, failing: int, detail: str) -> CheckResult:
    return CheckResult(table=table, check=check, target=target, passed=failing == 0,
                       failing_rows=int(failing), detail=detail)


def check_weight(df: pd.DataFrame, table: str, rule: dict) -> CheckResult:
    """Weights are never blank or negative; positive everywhere, or only where positive_when matches."""
    column = rule["column"]
    weight = pd.to_numeric(df[column].str.strip(), errors="coerce")
    bad = weight.isna() | (weight < 0)
    condition = rule.get("positive_when", {})
    if condition:
        match = pd.Series(True, index=df.index)
        for col, value in condition.items():
            match &= df[col].str.strip() == str(value)
        bad |= (match & (weight <= 0)) | (~match & (weight != 0))
        where = ", ".join(f"{col} = {value}" for col, value in condition.items())
        detail = (f"{int(bad.sum()):,} rows break the rule (positive only where {where}, else 0)" if bad.any()
                  else f"positive on all {int(match.sum()):,} rows where {where}, 0 on the other {int((~match).sum()):,}")
    else:
        bad |= weight <= 0
        detail = f"{int(bad.sum()):,} rows are blank, zero or negative" if bad.any() else "all rows positive"
    return _result(table, "weight", column, int(bad.sum()), detail)


def check_raw_file(table: str, path: Path, rules: dict, manifest_entry: dict | None = None) -> list[CheckResult]:
    """Run every raw check on one CSV file."""
    size = path.stat().st_size
    results = [_result(table, "file_presence", path.name, int(size == 0),
                       f"found, {size:,} bytes" if size else "file is empty")]
    if not size:
        return results

    if manifest_entry:
        same = sha256_of(path) == manifest_entry["sha256"]
        results.append(_result(table, "checksum", path.name, int(not same),
                               "matches the SHA-256 recorded at ingestion" if same
                               else "file changed after it was ingested; re-run ingestion"))

    encoding = detect_encoding(path)
    header = {c.strip().upper(): c for c in pd.read_csv(path, nrows=0, encoding=encoding).columns}
    required = rules["required_columns"]
    missing = [c for c in required if c.upper() not in header]
    results.append(_result(table, "schema", ",".join(required), len(missing),
                           f"missing columns: {missing}" if missing else f"all {len(required)} required columns present"))

    weight_rule = rules.get("weight", {})
    needed = rules.get("key_columns", []) + [weight_rule.get("column", "")] + list(weight_rule.get("positive_when", {}))
    present = [c for c in dict.fromkeys(needed) if c and c.upper() in header]
    df = pd.read_csv(path, usecols=[header[c.upper()] for c in present] or [0], dtype=str,
                     keep_default_na=False, encoding=encoding)
    df.columns = [c.strip().upper() for c in df.columns]

    minimum = rules["min_rows"]
    results.append(_result(table, "row_count", "*", int(len(df) < minimum),
                           f"{len(df):,} data rows (minimum {minimum:,})"))

    for column in rules.get("key_columns", []):
        if column in df.columns:
            bad = int((~df[column].str.strip().str.fullmatch(r"\d+")).sum())
            results.append(_result(table, "key_not_blank", column, bad,
                                   f"{bad:,} blank or non-integer values" if bad else "every value is a whole number"))

    if weight_rule and all(c in df.columns for c in [weight_rule["column"], *weight_rule.get("positive_when", {})]):
        results.append(check_weight(df, table, weight_rule))
    return results


def validate_raw(batch_id: str) -> list[CheckResult]:
    """Check every raw survey file against the contract; raise DataQualityError on failure."""
    rules = load_contract()["raw_files"]
    manifest_path = layer_path("raw") / "_manifests" / "latest.json"
    manifest = read_json(manifest_path)["files"] if manifest_path.exists() else {}

    results: list[CheckResult] = []
    for item in survey_tables():
        table = item["table"]
        try:
            path = locate(item)
        except FileNotFoundError as exc:
            results.append(_result(table, "file_presence", item["file_pattern"], 1, str(exc)))
            continue
        results.extend(check_raw_file(table, path, rules[table], manifest.get(table)))
    return report_results("raw_gate", results, batch_id)
