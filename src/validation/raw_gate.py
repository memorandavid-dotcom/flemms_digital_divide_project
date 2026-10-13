"""Fail-fast raw-data validation gate (runs BEFORE staging).

Checks performed on every raw CSV, in order:
    1. file_presence   - every declared source file exists and is non-empty
    2. schema          - required columns are present in the CSV header
    3. checksum        - file SHA-256 matches the last ingested manifest
                         (warns; does not block, because a legitimate PSA update
                          should not stop the pipeline - ingest_survey logs it too)
    4. row_count       - data-line count meets the contract minimum
    5. constraints     - spot-check of mandatory raw columns:
                         no blank key columns (hhid, lno/lno_f2), numeric key
                         columns parse as integers, weight columns are positive

All failures are collected into a JSON report in outputs/validation/raw_gate_latest.json
and a DataQualityError is raised if any "error"-severity check fails, which makes
the Airflow task fail and prevents build_staging from starting on bad data.
"""

import pandas as pd

from src.config import layer_path
from src.extract.ingest_survey import detect_encoding, locate, survey_tables
from src.utils.io_utils import read_json, safe_name, sha256_of, utc_now, write_json
from src.utils.logging_utils import get_logger
from src.validation.checks import CheckResult, DataQualityError

log = get_logger(__name__)

# Raw-layer minimum row counts per source table (must be <= the values already
# checked on staged data so the gate is not looser than staging).
_RAW_MIN_ROWS: dict[str, int] = {
    "v1_household":            100_000,
    "v1_household_questions":  100_000,
    "v1_member":               300_000,
    "v1_literacy":             300_000,
}

# Required columns as they appear in the raw CSV header (case-sensitive, PSA names).
# These are the columns that the staging transform reads and would silently break
# if absent.  Add more here if you expand the staging logic.
_REQUIRED_COLUMNS: dict[str, list[str]] = {
    "v1_household":           ["HHID", "REG", "REG2", "PRV", "URBANITY", "PSU", "INTVW", "RFACT"],
    "v1_household_questions": ["HHID", "BENEFICIARY_4PS", "ELECTRICITY",
                               "HH_SMARTPHONE", "HH_BASICPHONE", "HH_PC",
                               "HH_TABLET", "HH_CABNET", "HH_NOCABNET",
                               "HH_MOBSUB", "ICT_EQUIP", "HH_RFACT"],
    "v1_member":              ["HHID", "LNO", "SEX", "AGE", "HGC_LEVEL",
                               "ATTEND_SCHOOL", "MEM_RFACT"],
    "v1_literacy":            ["HHID", "LNO_F2", "RESULT_CODE_F2", "AGE_F2",
                               "BLITERATE", "FLITERATE", "FLLEVEL", "RESP_RFACT_F2"],
}

# Raw column names that must never be blank and must parse as non-negative integers.
_INTEGER_KEY_COLUMNS: dict[str, list[str]] = {
    "v1_household":           ["HHID"],
    "v1_household_questions": ["HHID"],
    "v1_member":              ["HHID", "LNO"],
    "v1_literacy":            ["HHID", "LNO_F2"],
}

# Weight columns that must be positive numbers.
_WEIGHT_COLUMNS: dict[str, str] = {
    "v1_household":           "RFACT",
    "v1_household_questions": "HH_RFACT",
    "v1_member":              "MEM_RFACT",
    "v1_literacy":            "RESP_RFACT_F2",
}


def _result(table: str, check: str, target: str, passed: bool,
            failing: int, detail: str, severity: str = "error") -> CheckResult:
    return CheckResult(table=table, check=check, target=target,
                       passed=passed, failing_rows=failing,
                       detail=detail, severity=severity)


def validate_raw(batch_id: str) -> list[CheckResult]:
    """Run the raw-gate checks and return a list of CheckResults.

    Raises DataQualityError if any error-severity check fails.
    """
    manifest_path = layer_path("raw") / "_manifests" / "latest.json"
    previous: dict = {}
    if manifest_path.exists():
        previous = read_json(manifest_path).get("files", {})

    results: list[CheckResult] = []
    items = survey_tables()

    for item in items:
        table = item["table"]

        # ------------------------------------------------------------------
        # 1. File presence
        # ------------------------------------------------------------------
        try:
            path = locate(item)
        except FileNotFoundError as exc:
            results.append(_result(table, "file_presence", item["file_pattern"],
                                   False, 1, str(exc)))
            log.error("[RAW-GATE] %s | file_presence FAIL: %s", table, exc)
            # Cannot run any further checks for this table without the file.
            continue

        file_size = path.stat().st_size
        results.append(_result(table, "file_presence", path.name,
                               file_size > 0, 0 if file_size > 0 else 1,
                               f"File found ({file_size:,} bytes)" if file_size > 0
                               else "File exists but is empty (0 bytes)"))

        # ------------------------------------------------------------------
        # 2. Checksum / drift detection (warning only)
        # ------------------------------------------------------------------
        prev_entry = previous.get(table, {})
        if prev_entry:
            current_sha = sha256_of(path)
            checksum_match = current_sha == prev_entry.get("sha256", "")
            results.append(_result(
                table, "checksum", path.name,
                checksum_match, 0 if checksum_match else 1,
                "SHA-256 matches last ingested manifest" if checksum_match
                else (f"SHA-256 differs from last manifest - file may have been "
                      f"replaced.  Current: {current_sha[:12]}... "
                      f"Previous: {str(prev_entry.get('sha256',''))[:12]}..."),
                severity="warning",
            ))

        # ------------------------------------------------------------------
        # Read header for the remaining checks.
        # ------------------------------------------------------------------
        encoding = detect_encoding(path)
        try:
            header_df = pd.read_csv(path, nrows=0, encoding=encoding)
            header = [c.strip() for c in header_df.columns.tolist()]
        except Exception as exc:
            results.append(_result(table, "schema", "*", False, 1,
                                   f"Could not parse CSV header: {exc}"))
            log.error("[RAW-GATE] %s | schema FAIL: %s", table, exc)
            continue

        # ------------------------------------------------------------------
        # 3. Schema - required column presence
        # ------------------------------------------------------------------
        required = _REQUIRED_COLUMNS.get(table, [])
        header_upper = {c.upper() for c in header}
        missing_cols = [c for c in required if c.upper() not in header_upper]
        results.append(_result(table, "schema", ",".join(required),
                               not missing_cols, len(missing_cols),
                               (f"Missing columns: {missing_cols}" if missing_cols
                                else f"All {len(required)} required columns present")))

        # ------------------------------------------------------------------
        # 4. Row count
        # ------------------------------------------------------------------
        manifest_lines = prev_entry.get("data_lines")
        if manifest_lines is not None:
            raw_rows = manifest_lines
        else:
            with open(path, "rb") as fh:
                raw_rows = max(sum(1 for ln in fh if ln.strip()) - 1, 0)

        min_rows = _RAW_MIN_ROWS.get(table, 1)
        results.append(_result(table, "row_count", "*",
                               raw_rows >= min_rows, 0 if raw_rows >= min_rows else 1,
                               f"{raw_rows:,} data rows (minimum {min_rows:,})"))

        # ------------------------------------------------------------------
        # 5. Constraint spot-check on a 5 000-row sample
        # ------------------------------------------------------------------
        try:
            sample = pd.read_csv(path, nrows=5_000, dtype=str,
                                 keep_default_na=False, encoding=encoding)
            sample.columns = [c.strip().upper() for c in sample.columns]
        except Exception as exc:
            results.append(_result(table, "constraints", "*", False, 1,
                                   f"Could not read sample rows: {exc}"))
            continue

        # Integer key columns: not blank, parse as non-negative integer
        for col in _INTEGER_KEY_COLUMNS.get(table, []):
            if col not in sample.columns:
                continue  # already caught by schema check
            raw_col = sample[col].str.strip()
            blank = (raw_col == "").sum()
            non_int = pd.to_numeric(raw_col[raw_col != ""], errors="coerce").isna().sum()
            bad = int(blank) + int(non_int)
            results.append(_result(table, "constraints", col,
                                   bad == 0, bad,
                                   (f"{bad:,} values are blank or non-integer in sample"
                                    if bad else "All sampled key values are valid integers")))

        # Weight column: positive number
        wcol = _WEIGHT_COLUMNS.get(table)
        if wcol and wcol in sample.columns:
            raw_w = sample[wcol].str.strip()
            numeric_w = pd.to_numeric(raw_w, errors="coerce")
            bad_w = int((numeric_w.isna() | (numeric_w <= 0)).sum())
            results.append(_result(table, "constraints", wcol,
                                   bad_w == 0, bad_w,
                                   (f"{bad_w:,} weight values are missing or <= 0 in sample"
                                    if bad_w else "All sampled weight values are positive")))

    # ------------------------------------------------------------------
    # Write report and raise on errors
    # ------------------------------------------------------------------
    failed = [r for r in results if not r.passed and r.severity == "error"]
    warned = [r for r in results if not r.passed and r.severity == "warning"]

    from dataclasses import asdict
    report = {
        "stage": "raw_gate",
        "batch_id": batch_id,
        "run_at": utc_now(),
        "checks_run": len(results),
        "checks_failed": len(failed),
        "warnings": len(warned),
        "results": [asdict(r) for r in results],
    }
    out_dir = layer_path("outputs") / "validation"
    write_json(report, out_dir / f"raw_gate_{safe_name(batch_id)}.json")
    write_json(report, out_dir / "raw_gate_latest.json")

    for r in results:
        level = "PASS" if r.passed else r.severity.upper()
        log.info("[RAW-GATE][%s] %s.%s %s: %s", level, r.table, r.check, r.target, r.detail)
    log.info("Raw-gate '%s': %d checks, %d failed, %d warnings",
             batch_id, len(results), len(failed), len(warned))

    if failed:
        summary = "; ".join(
            f"{r.table}.{r.check}({r.target}): {r.detail}" for r in failed
        )
        raise DataQualityError(
            f"{len(failed)} raw-gate check(s) failed: {summary}"
        )
    return results
