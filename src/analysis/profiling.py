"""Profile every raw source before any transformation.

For each survey file this records, per column: data type, missing values,
distinct values, min/max/mean for numbers, and the most frequent values;
and per file: row and column counts and fully duplicated rows.

Outputs (outputs/profiling/):
  <table>.json         full machine-readable profile
  profiling_report.md  human-readable summary used in the documentation
"""
import pandas as pd

from src.config import layer_path
from src.extract.ingest_survey import detect_encoding, locate, survey_tables
from src.utils.io_utils import utc_now, write_json
from src.utils.logging_utils import get_logger

log = get_logger(__name__)


def profile_frame(df: pd.DataFrame) -> dict:
    """Column-level profile of a DataFrame read with every column as text."""
    columns = {}
    for col in df.columns:
        raw = df[col]
        blank = raw.isna() | (raw.str.strip() == "")
        values = raw[~blank]
        numeric = pd.to_numeric(values, errors="coerce")
        is_numeric = len(values) > 0 and numeric.notna().all()
        info = {
            "inferred_type": "numeric" if is_numeric else ("empty" if len(values) == 0 else "text"),
            "missing": int(blank.sum()),
            "missing_pct": round(100 * blank.mean(), 2),
            "distinct": int(values.nunique()),
            "top_values": values.value_counts().head(5).to_dict(),
        }
        if is_numeric:
            info.update(min=float(numeric.min()), max=float(numeric.max()),
                        mean=round(float(numeric.mean()), 3))
        elif len(values) and numeric.notna().any():
            info["non_numeric_examples"] = sorted(values[numeric.isna()].unique())[:5]
        columns[col] = info
    return columns


def profile_sources(batch_id: str) -> list[str]:
    out_dir = layer_path("outputs") / "profiling"
    lines = ["# Source profiling report", "",
             f"Generated {utc_now()} (batch `{batch_id}`) from the raw files, before any cleaning.", ""]

    for item in survey_tables():
        path = locate(item)
        df = pd.read_csv(path, dtype=str, keep_default_na=False, encoding=detect_encoding(path))
        cols = profile_frame(df)
        exact_dupes = int(df.duplicated().sum())
        profile = {"table": item["table"], "file": path.name, "rows": len(df), "columns": len(df.columns),
                   "exact_duplicate_rows": exact_dupes, "column_profiles": cols}
        write_json(profile, out_dir / f"{item['table']}.json")
        log.info("Profiled %s: %d rows x %d cols, %d exact duplicate rows",
                 item["table"], len(df), len(df.columns), exact_dupes)

        mostly_missing = [c for c, p in cols.items() if p["missing_pct"] >= 50]
        mixed = [c for c, p in cols.items() if "non_numeric_examples" in p]
        lines += [f"## {item['table']} — `{path.name}`", "",
                  f"- Rows: **{len(df):,}**, columns: **{len(df.columns)}**",
                  f"- Fully duplicated rows: **{exact_dupes:,}**",
                  f"- Columns ≥50% blank: {len(mostly_missing)}"
                  + (f" ({', '.join(mostly_missing[:15])}{' …' if len(mostly_missing) > 15 else ''})" if mostly_missing else ""),
                  f"- Columns mixing numbers and text: {', '.join(mixed) if mixed else 'none'}", "",
                  "| Column | Type | Missing % | Distinct | Min | Max | Mean |",
                  "|---|---|---:|---:|---:|---:|---:|"]
        for col, p in cols.items():
            lines.append(f"| {col} | {p['inferred_type']} | {p['missing_pct']} | {p['distinct']:,} | "
                         f"{p.get('min', '')} | {p.get('max', '')} | {p.get('mean', '')} |")
        lines.append("")

    report = out_dir / "profiling_report.md"
    report.write_text("\n".join(lines), encoding="utf-8")
    log.info("Profiling report written to %s", report)
    return [item["table"] for item in survey_tables()]
