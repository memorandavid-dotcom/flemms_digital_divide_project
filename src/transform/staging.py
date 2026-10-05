"""Raw -> staging: clean, type and de-duplicate each survey file on its own.

Allowed in this layer (no joins, no business logic yet):
  * column names standardised to lower_snake_case (hidden BOM characters removed)
  * surrounding spaces trimmed; blank cells become missing values (NA)
  * columns whose values are all numbers converted to integer/decimal types
  * exact duplicate rows removed
  * rows that repeat a primary key removed (first one kept); the removed rows are
    saved to data/staging/_rejects/ so nothing disappears without a trace
  * lineage columns added: source_file, source_line, batch_id, ingested_at
  * PSA's value-label sheet (data dictionary .xlsx) parsed into codebook.parquet

Each table is written to data/staging/<table>.parquet, replacing the previous
version, so re-running this step never duplicates data.
A de-duplication report is written to outputs/staging/.
"""
import re

import pandas as pd

from src.config import layer_path, settings
from src.extract.ingest_survey import detect_encoding, locate, locate_codebooks, survey_tables
from src.utils.io_utils import utc_now, write_json
from src.utils.logging_utils import get_logger

log = get_logger(__name__)

LINEAGE_COLUMNS = ["source_file", "source_line", "batch_id", "ingested_at"]


class DuplicateThresholdError(Exception):
    """Too many duplicates: usually a wrong key or a corrupted file, not real duplicates."""


def clean_column_name(name: str) -> str:
    name = name.replace("﻿", "").strip().lower()
    name = re.sub(r"[^0-9a-z]+", "_", name)
    return name.strip("_")


def standardise(df: pd.DataFrame) -> pd.DataFrame:
    df = df.rename(columns=clean_column_name)
    for col in df.columns:
        df[col] = df[col].str.strip().replace("", pd.NA)
    return df


def convert_types(df: pd.DataFrame, keep_text: list[str]) -> tuple[pd.DataFrame, dict]:
    """Turn all-numeric text columns into Int64 (whole numbers) or Float64."""
    converted = {}
    for col in df.columns:
        if col in keep_text:
            continue
        values = df[col].dropna()
        if values.empty:
            continue
        numbers = pd.to_numeric(values, errors="coerce")
        if numbers.isna().any():
            continue  # contains text: leave as string
        whole = (numbers % 1 == 0).all()
        df[col] = pd.to_numeric(df[col]).astype("Int64" if whole else "Float64")
        converted[col] = "Int64" if whole else "Float64"
    return df, converted


def deduplicate(df: pd.DataFrame, key: list[str], data_columns: list[str]) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    rows_in = len(df)
    exact = df.duplicated(subset=data_columns)
    df = df[~exact]

    repeated = df.duplicated(subset=key, keep=False)
    rejects = df[repeated]
    df = df.drop_duplicates(subset=key, keep="first")

    stats = {
        "rows_in": rows_in,
        "exact_duplicates_removed": int(exact.sum()),
        "rows_sharing_a_key": int(repeated.sum()),
        "key_duplicates_removed": int(len(rejects) - rejects[key].drop_duplicates().shape[0]),
        "rows_out": len(df),
    }
    return df, rejects, stats


def parse_codebook(path) -> pd.DataFrame:
    """Turn PSA's value-set sheet into one row per (variable, code range, label).

    In the sheet a value set starts with a row like  REG_VS1 | Region
    followed by rows                                  _ | _ | label | from | to
    """
    sheet = pd.read_excel(path, sheet_name=1, header=None, dtype=str)
    rows, value_set, set_label = [], None, None
    for r in sheet.itertuples(index=False):
        if pd.notna(r[0]):
            value_set, set_label = r[0].strip(), (r[1] or "").strip()
        elif value_set and pd.notna(r[3]):
            rows.append({
                "value_set": value_set,
                "variable": clean_column_name(value_set.split("_VS")[0]),
                "variable_label": set_label,
                "value_from": int(float(r[3])),
                "value_to": int(float(r[4])) if pd.notna(r[4]) else int(float(r[3])),
                "value_label": r[2].strip() if pd.notna(r[2]) else None,
            })
    return pd.DataFrame(rows)


def build_codebook() -> int:
    frames = []
    for source, path in locate_codebooks().items():
        book = parse_codebook(path)
        book.insert(0, "source", source)
        frames.append(book)
    codebook = pd.concat(frames, ignore_index=True)
    codebook.to_parquet(layer_path("staging") / "codebook.parquet", index=False)
    log.info("Codebook staged: %d value labels for %d variables",
             len(codebook), codebook["variable"].nunique())
    return len(codebook)


def build_staging(batch_id: str) -> dict:
    staging = layer_path("staging")
    max_share = settings()["staging"]["max_duplicate_share"]
    ingested_at = utc_now()
    report = {"batch_id": batch_id, "run_at": ingested_at, "tables": {}}

    for item in survey_tables():
        path = locate(item)
        df = pd.read_csv(path, dtype=str, keep_default_na=False, encoding=detect_encoding(path))
        df = standardise(df)
        # Line number in the original file (line 1 is the header) for record tracing
        df.insert(0, "source_line", pd.RangeIndex(2, len(df) + 2))
        key = item["key"]
        missing_key = [k for k in key if k not in df.columns]
        if missing_key:
            raise KeyError(f"{item['table']}: key columns {missing_key} not found in {path.name}")

        df, converted = convert_types(df, keep_text=item.get("keep_as_text", []) + ["source_line"])
        data_columns = [c for c in df.columns if c != "source_line"]
        df, rejects, stats = deduplicate(df, key, data_columns)

        removed = stats["exact_duplicates_removed"] + stats["key_duplicates_removed"]
        share = removed / stats["rows_in"] if stats["rows_in"] else 0
        if share > max_share:
            raise DuplicateThresholdError(
                f"{item['table']}: {removed:,} of {stats['rows_in']:,} rows ({share:.2%}) are duplicates, "
                f"above the {max_share:.2%} limit. Check the key {key} and the source file.")

        df["source_file"] = path.name
        df["batch_id"] = batch_id
        df["ingested_at"] = ingested_at
        df["source_line"] = df["source_line"].astype("Int64")

        out = staging / f"{item['table']}.parquet"
        df.to_parquet(out, index=False)
        reject_file = staging / "_rejects" / f"{item['table']}_duplicate_keys.parquet"
        if len(rejects):
            reject_file.parent.mkdir(exist_ok=True)
            rejects.to_parquet(reject_file, index=False)
        elif reject_file.exists():
            reject_file.unlink()

        stats.update(key=key, typed_columns=len(converted), output=out.name)
        report["tables"][item["table"]] = stats
        log.info("Staged %-12s %s rows in -> %s out | exact dupes removed %d | key dupes removed %d",
                 item["table"], f"{stats['rows_in']:,}", f"{stats['rows_out']:,}",
                 stats["exact_duplicates_removed"], stats["key_duplicates_removed"])

    report["codebook_labels"] = build_codebook()
    out_dir = layer_path("outputs") / "staging"
    write_json(report, out_dir / "dedup_report.json")
    return {t: s["rows_out"] for t, s in report["tables"].items()}
