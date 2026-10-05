"""Automated data-quality checks.

The rules are not hard-coded here: they are read from docs/data_contract.yaml,
so the documented contract and the enforced checks can never drift apart.

Check types implemented (each returns a CheckResult):
    row_count          table has at least N rows
    required_columns   schema: every contracted column exists
    dtype              column has the contracted data type
    not_null           column has no missing values
    unique             no duplicate keys
    exact_duplicates   no fully identical rows
    accepted_values    values come from an allowed list
    range              numeric values fall inside [min, max]
    foreign_key        every key exists in the parent table (referential integrity)

run_validation() logs every result, writes a JSON report to outputs/validation/,
and raises DataQualityError if any check with severity "error" fails, which
makes the Airflow task fail and stops the downstream tasks.
"""
from dataclasses import asdict, dataclass

import pandas as pd
import yaml

from src.config import PROJECT_ROOT, layer_path
from src.utils.io_utils import safe_name, utc_now, write_json
from src.utils.logging_utils import get_logger

log = get_logger(__name__)

CONTRACT_PATH = PROJECT_ROOT / "docs" / "data_contract.yaml"


class DataQualityError(Exception):
    """Raised when at least one error-severity check fails."""


@dataclass
class CheckResult:
    table: str
    check: str
    target: str
    passed: bool
    failing_rows: int
    detail: str
    severity: str = "error"


def load_contract() -> dict:
    with open(CONTRACT_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


# ---------- individual checks ----------

def check_row_count(df: pd.DataFrame, table: str, minimum: int) -> CheckResult:
    n = len(df)
    return CheckResult(table, "row_count", "*", n >= minimum, 0 if n >= minimum else 1,
                       f"{n:,} rows (minimum {minimum:,})")


def check_required_columns(df: pd.DataFrame, table: str, columns: list[str]) -> CheckResult:
    missing = [c for c in columns if c not in df.columns]
    return CheckResult(table, "required_columns", ",".join(columns), not missing, len(missing),
                       f"missing: {missing}" if missing else f"all {len(columns)} columns present")


DTYPE_TESTS = {
    "integer": pd.api.types.is_integer_dtype,
    "float": pd.api.types.is_numeric_dtype,
    "string": lambda s: pd.api.types.is_string_dtype(s) or pd.api.types.is_object_dtype(s),
    "boolean": pd.api.types.is_bool_dtype,
}


def check_dtype(df: pd.DataFrame, table: str, column: str, expected: str) -> CheckResult:
    ok = DTYPE_TESTS[expected](df[column])
    return CheckResult(table, "dtype", column, ok, 0 if ok else len(df),
                       f"expected {expected}, found {df[column].dtype}")


def check_not_null(df: pd.DataFrame, table: str, column: str) -> CheckResult:
    nulls = int(df[column].isna().sum())
    return CheckResult(table, "not_null", column, nulls == 0, nulls, f"{nulls:,} missing values")


def check_unique(df: pd.DataFrame, table: str, columns: list[str]) -> CheckResult:
    dupes = int(df.duplicated(subset=columns, keep=False).sum())
    return CheckResult(table, "unique", ",".join(columns), dupes == 0, dupes,
                       f"{dupes:,} rows share a key with another row")


def check_exact_duplicates(df: pd.DataFrame, table: str, ignore: list[str]) -> CheckResult:
    cols = [c for c in df.columns if c not in ignore]
    dupes = int(df.duplicated(subset=cols).sum())
    return CheckResult(table, "exact_duplicates", "*", dupes == 0, dupes,
                       f"{dupes:,} fully duplicated rows")


def check_accepted_values(df: pd.DataFrame, table: str, column: str, allowed) -> CheckResult:
    values = df[column].dropna()
    bad = values[~values.isin(list(allowed))]
    sample = sorted(map(str, bad.unique()))[:10]
    return CheckResult(table, "accepted_values", column, bad.empty, len(bad),
                       f"{len(bad):,} values outside the allowed list" + (f", e.g. {sample}" if sample else ""))


def check_range(df: pd.DataFrame, table: str, column: str, low=None, high=None) -> CheckResult:
    values = df[column].dropna()
    bad = values[((values < low) if low is not None else False) | ((values > high) if high is not None else False)]
    return CheckResult(table, "range", column, bad.empty, len(bad),
                       f"{len(bad):,} values outside [{low}, {high}]")


def check_foreign_key(child: pd.DataFrame, table: str, columns: list[str],
                      parent: pd.DataFrame, parent_table: str, parent_columns: list[str]) -> CheckResult:
    keys = child[columns].dropna().drop_duplicates()
    parent_keys = parent[parent_columns].drop_duplicates()
    parent_keys.columns = columns
    merged = keys.merge(parent_keys, on=columns, how="left", indicator=True)
    orphans = int((merged["_merge"] == "left_only").sum())
    return CheckResult(table, "foreign_key", ",".join(columns), orphans == 0, orphans,
                       f"{orphans:,} key values not found in {parent_table}")


# ---------- contract-driven runner ----------

def validate_table(df: pd.DataFrame, name: str, spec: dict,
                   tables: dict[str, pd.DataFrame]) -> list[CheckResult]:
    """Run every check the contract declares for one table."""
    results = [check_row_count(df, name, spec.get("min_rows", 1))]
    columns = spec["columns"]
    results.append(check_required_columns(
        df, name, [c for c, rules in columns.items() if rules.get("required", True)]))

    for col, rules in columns.items():
        if col not in df.columns:
            continue
        severity = rules.get("severity", "error")
        col_results = [check_dtype(df, name, col, rules["type"])]
        if not rules.get("nullable", True):
            col_results.append(check_not_null(df, name, col))
        if "accepted_values" in rules:
            col_results.append(check_accepted_values(df, name, col, rules["accepted_values"]))
        if "min" in rules or "max" in rules:
            col_results.append(check_range(df, name, col, rules.get("min"), rules.get("max")))
        for r in col_results:
            r.severity = severity
        results.extend(col_results)

    results.append(check_unique(df, name, spec["primary_key"]))
    results.append(check_exact_duplicates(df, name, ignore=spec.get("lineage_columns", [])))

    for fk in spec.get("foreign_keys", []):
        parent = fk["references"]["table"]
        if parent in tables:
            results.append(check_foreign_key(df, name, fk["columns"], tables[parent],
                                             parent, fk["references"]["columns"]))
        else:
            log.warning("Skipping foreign key %s -> %s: parent table not loaded", name, parent)
    return results


def run_validation(stage: str, tables: dict[str, pd.DataFrame], batch_id: str) -> list[CheckResult]:
    """Validate the given tables against the contract and stop the pipeline on failure."""
    contract = load_contract()
    results: list[CheckResult] = []
    for name, df in tables.items():
        spec = contract["tables"].get(name)
        if spec is None:
            raise KeyError(f"Table '{name}' is not described in {CONTRACT_PATH.name}")
        results.extend(validate_table(df, name, spec, tables))

    failed = [r for r in results if not r.passed and r.severity == "error"]
    warned = [r for r in results if not r.passed and r.severity == "warning"]
    for r in results:
        level = "PASS" if r.passed else r.severity.upper()
        log.info("[%s] %s.%s %s: %s", level, r.table, r.check, r.target, r.detail)

    report = {
        "stage": stage,
        "batch_id": batch_id,
        "run_at": utc_now(),
        "checks_run": len(results),
        "checks_failed": len(failed),
        "warnings": len(warned),
        "results": [asdict(r) for r in results],
    }
    out_dir = layer_path("outputs") / "validation"
    write_json(report, out_dir / f"{stage}_{safe_name(batch_id)}.json")
    write_json(report, out_dir / f"{stage}_latest.json")
    log.info("Validation '%s': %d checks, %d failed, %d warnings",
             stage, len(results), len(failed), len(warned))

    if failed:
        summary = "; ".join(f"{r.table}.{r.check}({r.target}): {r.detail}" for r in failed)
        raise DataQualityError(f"{len(failed)} data-quality check(s) failed in '{stage}': {summary}")
    return results
