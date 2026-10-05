"""Compare CSV, JSON and Parquet on the same curated table, and measure partition pruning.

For each format: file size, write time, read time, and whether column types
survive a write/read round trip (schema preservation).
Then: reading one region partition vs reading the whole partitioned dataset.

Results: outputs/format_comparison.json and outputs/format_comparison.md.
The benchmark files themselves go to data/curated/_format_benchmark/ (not committed).
"""
import shutil
import time

import pandas as pd
import pyarrow.dataset as ds

from src.config import layer_path, settings
from src.utils.io_utils import utc_now, write_json
from src.utils.logging_utils import get_logger

log = get_logger(__name__)


def _timed(func):
    start = time.perf_counter()
    result = func()
    return result, time.perf_counter() - start


def _types_preserved(original: pd.DataFrame, reloaded: pd.DataFrame) -> str:
    changed = [c for c in original.columns if str(original[c].dtype) != str(reloaded[c].dtype)]
    return "yes" if not changed else f"no ({len(changed)} of {len(original.columns)} columns changed type)"


def benchmark_formats(batch_id: str) -> str:
    cfg = settings()["benchmark"]
    curated = layer_path("curated")
    source = curated / cfg["table"]
    df = pd.read_parquet(source)
    work = curated / "_format_benchmark"
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)

    writers = {
        "CSV": (work / "table.csv", lambda p: df.to_csv(p, index=False), lambda p: pd.read_csv(p)),
        "JSON (records, one per line)": (work / "table.jsonl",
                                         lambda p: df.to_json(p, orient="records", lines=True),
                                         lambda p: pd.read_json(p, orient="records", lines=True)),
        "Parquet (snappy)": (work / "table.parquet", lambda p: df.to_parquet(p, index=False),
                             lambda p: pd.read_parquet(p)),
    }
    rows = []
    for name, (path, write, read) in writers.items():
        _, write_s = _timed(lambda: write(path))
        reloaded, read_s = _timed(lambda: read(path))
        rows.append({"format": name, "size_mb": round(path.stat().st_size / 1e6, 2),
                     "write_s": round(write_s, 2), "read_s": round(read_s, 2),
                     "types_preserved": _types_preserved(df, reloaded)})
        log.info("%-30s %8.2f MB  write %.2fs  read %.2fs", name, rows[-1]["size_mb"], write_s, read_s)

    # Partition pruning: one region vs all regions
    region = cfg["demo_region_code"]
    key = settings()["partitioning"]["column"]
    dataset = ds.dataset(source, format="parquet", partitioning="hive")
    full, full_s = _timed(lambda: dataset.to_table())
    part, part_s = _timed(lambda: dataset.to_table(filter=ds.field(key) == region))
    files_total = len(dataset.files)
    files_read = len([f for f in dataset.files if f"{key}={region}/" in f.replace("\\", "/")])
    pruning = {"partition_column": key, "region_code": region,
               "rows_all": full.num_rows, "seconds_all": round(full_s, 3), "files_all": files_total,
               "rows_one_region": part.num_rows, "seconds_one_region": round(part_s, 3),
               "files_one_region": files_read}
    log.info("Partition pruning: all regions %d rows in %.3fs, region %s %d rows in %.3fs",
             full.num_rows, full_s, region, part.num_rows, part_s)

    result = {"batch_id": batch_id, "run_at": utc_now(), "table": cfg["table"],
              "rows": len(df), "columns": len(df.columns), "formats": rows, "partition_pruning": pruning}
    out = layer_path("outputs")
    write_json(result, out / "format_comparison.json")

    lines = ["# File format comparison", "",
             f"Table `{cfg['table']}`: {len(df):,} rows x {len(df.columns)} columns. "
             f"Generated {result['run_at']} (batch `{batch_id}`). Times depend on the machine.", "",
             "| Format | Size (MB) | Write (s) | Read (s) | Column types preserved |",
             "|---|---:|---:|---:|---|"]
    lines += [f"| {r['format']} | {r['size_mb']} | {r['write_s']} | {r['read_s']} | {r['types_preserved']} |"
              for r in rows]
    lines += ["", "## Partition pruning", "",
              f"The curated table is partitioned by `{key}`. Reading only region {region}:", "",
              "| Read | Files | Rows | Seconds |", "|---|---:|---:|---:|",
              f"| All regions | {files_total} | {full.num_rows:,} | {pruning['seconds_all']} |",
              f"| Region {region} only | {files_read} | {part.num_rows:,} | {pruning['seconds_one_region']} |", ""]
    (out / "format_comparison.md").write_text("\n".join(lines), encoding="utf-8")
    shutil.rmtree(work, ignore_errors=True)
    return "outputs/format_comparison.md"
