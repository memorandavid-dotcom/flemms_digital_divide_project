"""Source 1: PSA FLEMMS 2024 public-use file (CSV files + XLSX data dictionary).

PSA's microdata catalog requires a login and acceptance of its terms of use,
so a person downloads the files once and places them in data/raw/<folder>/.
From there this step is fully automatic:
  * finds every expected file (case-insensitive) and fails clearly if one is missing
  * detects the text encoding (PSA files are not always UTF-8)
  * records SHA-256 checksum, size, row and column counts, and ingestion time
  * compares checksums with the previous run, so a replaced source file is flagged
  * writes an ingestion manifest to data/raw/_manifests/
The raw files themselves are never modified.
"""
import codecs
from pathlib import Path

import pandas as pd

from src.config import PROJECT_ROOT, layer_path, settings
from src.utils.io_utils import (find_source_file, read_json, safe_name, sha256_of,
                                utc_now, write_json)
from src.utils.logging_utils import get_logger

log = get_logger(__name__)


def detect_encoding(path: Path) -> str:
    """Return 'utf-8-sig' if the file is valid UTF-8, otherwise 'latin-1'."""
    decoder = codecs.getincrementaldecoder("utf-8")()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                decoder.decode(chunk)
            decoder.decode(b"", final=True)
        return "utf-8-sig"  # also strips a byte-order mark if there is one
    except UnicodeDecodeError:
        return "latin-1"


def count_data_lines(path: Path) -> int:
    """Number of non-empty lines after the header."""
    with open(path, "rb") as f:
        lines = sum(1 for line in f if line.strip())
    return max(lines - 1, 0)


def survey_tables() -> list[dict]:
    """Every survey table declared in config/pipeline.yaml, with its source info."""
    items = []
    for source_name, source in settings()["sources"].items():
        if source["type"] != "survey_files":
            continue
        for table, spec in source["tables"].items():
            items.append({"source": source_name, "folder": source["folder"], "table": table, **spec})
    return items


def locate(item: dict) -> Path:
    return find_source_file(layer_path("raw") / item["folder"], item["file_pattern"])


def locate_codebooks() -> dict[str, Path]:
    """PSA data dictionaries (.xlsx), one per source that declares codebook_pattern."""
    found = {}
    for name, source in settings()["sources"].items():
        if source.get("codebook_pattern"):
            found[name] = find_source_file(layer_path("raw") / source["folder"], source["codebook_pattern"])
    return found


def ingest_survey_files(batch_id: str) -> dict:
    manifest_dir = layer_path("raw") / "_manifests"
    previous_file = manifest_dir / "latest.json"
    previous = read_json(previous_file) if previous_file.exists() else {"files": {}}

    # Fail fast: make sure every expected file is present before the slow checksum work
    paths = {item["table"]: locate(item) for item in survey_tables()}

    entries = {}
    for item in survey_tables():
        path = paths[item["table"]]
        if path.stat().st_size == 0:
            raise ValueError(f"Source file is empty: {path}")

        encoding = detect_encoding(path)
        try:
            header = pd.read_csv(path, nrows=0, encoding=encoding).columns.tolist()
        except Exception as exc:
            raise ValueError(f"Could not parse header of {path.name}: {exc}") from exc

        checksum = sha256_of(path)
        old = previous["files"].get(item["table"])
        changed = old is not None and old["sha256"] != checksum
        if changed:
            log.warning("%s changed since the last run (checksum differs)", path.name)

        entries[item["table"]] = {
            "source": item["source"],
            "file": path.name,
            "path": path.relative_to(PROJECT_ROOT).as_posix(),
            "sha256": checksum,
            "size_bytes": path.stat().st_size,
            "encoding": encoding,
            "data_lines": count_data_lines(path),
            "columns": len(header),
            "column_names": header,
            "file_modified_at": pd.Timestamp(path.stat().st_mtime, unit="s", tz="UTC").isoformat(),
            "changed_since_last_run": changed,
        }
        log.info("Registered %-12s %s | %s | %d lines x %d cols | %.1f MB",
                 item["table"], path.name, encoding, entries[item["table"]]["data_lines"],
                 len(header), path.stat().st_size / 1e6)

    for source, path in locate_codebooks().items():
        entries[f"{source}_codebook"] = {
            "source": source,
            "file": path.name,
            "path": path.relative_to(PROJECT_ROOT).as_posix(),
            "sha256": sha256_of(path),
            "size_bytes": path.stat().st_size,
            "data_lines": None,
        }
        log.info("Registered codebook %s", path.name)

    manifest = {"batch_id": batch_id, "ingested_at": utc_now(), "files": entries}
    write_json(manifest, manifest_dir / f"ingest_{safe_name(batch_id)}.json")
    write_json(manifest, previous_file)
    log.info("Ingestion manifest written for %d files", len(entries))
    return manifest
