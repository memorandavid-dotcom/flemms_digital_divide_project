"""Pipeline configuration.

Non-secret settings (paths, source files, rules) live in config/pipeline.yaml.
Secrets and hosts (database passwords, API URL) come from environment variables,
which are read from .env when running locally and injected by Docker Compose
when running in containers.
"""
import os
from functools import lru_cache
from pathlib import Path

import yaml
from dotenv import load_dotenv

PROJECT_ROOT = Path(os.environ.get("PROJECT_ROOT", Path(__file__).resolve().parents[1]))

# Values already set in the environment (e.g. by Docker) take priority over .env
load_dotenv(PROJECT_ROOT / ".env", override=False)


@lru_cache(maxsize=1)
def settings() -> dict:
    """Return the parsed config/pipeline.yaml."""
    with open(PROJECT_ROOT / "config" / "pipeline.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def layer_path(name: str) -> Path:
    """Absolute path of a data layer or output folder (raw, staging, curated, outputs)."""
    path = PROJECT_ROOT / settings()["paths"][name]
    path.mkdir(parents=True, exist_ok=True)
    return path


def warehouse_params() -> dict:
    """Connection settings for the PostgreSQL warehouse."""
    required = ["WAREHOUSE_DB", "WAREHOUSE_USER", "WAREHOUSE_PASSWORD"]
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        raise RuntimeError(
            f"Missing environment variables {missing}. Copy .env.example to .env and fill them in."
        )
    return {
        "host": os.environ.get("WAREHOUSE_HOST", "localhost"),
        "port": int(os.environ.get("WAREHOUSE_PORT", "5433")),
        "dbname": os.environ["WAREHOUSE_DB"],
        "user": os.environ["WAREHOUSE_USER"],
        "password": os.environ["WAREHOUSE_PASSWORD"],
    }


def psgc_base_url() -> str:
    return os.environ.get("PSGC_API_BASE_URL", "https://psgc.gitlab.io/api").rstrip("/")
