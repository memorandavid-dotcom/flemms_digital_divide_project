"""File helpers: locating source files, checksums, JSON output, batch ids."""
import fnmatch
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def new_batch_id() -> str:
    """Batch id for runs started outside Airflow, e.g. cli_20261005T101500Z."""
    return "cli_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def safe_name(text: str) -> str:
    """Make an Airflow run id (which contains ':' and '+') safe for file names."""
    return re.sub(r"[^A-Za-z0-9_.-]", "_", text)


def find_source_file(folder: Path, pattern: str) -> Path:
    """Find exactly one file in `folder` matching `pattern`, ignoring upper/lower case.

    Matching is case-insensitive on purpose: PSA ships files as .CSV, and
    Linux (inside Docker) treats .CSV and .csv as different names.
    """
    if not folder.is_dir():
        raise FileNotFoundError(
            f"Source folder not found: {folder}. Download the survey files from the PSA "
            f"microdata catalog and place them there (see README, 'Getting the data')."
        )
    matches = sorted(p for p in folder.iterdir()
                     if p.is_file() and fnmatch.fnmatch(p.name.lower(), pattern.lower()))
    if not matches:
        raise FileNotFoundError(f"No file matching '{pattern}' in {folder}")
    if len(matches) > 1:
        names = [p.name for p in matches]
        raise ValueError(f"Pattern '{pattern}' matched several files in {folder}: {names}")
    return matches[0]


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(obj, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, default=str)
    return path


def read_json(path: Path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)
