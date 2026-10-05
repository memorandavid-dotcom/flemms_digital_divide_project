"""Curated Parquet -> PostgreSQL warehouse (entry point for the DAG and pipeline.py)."""
import pandas as pd

from src.config import layer_path, settings
from src.load.postgres_loader import load_tables
from src.utils.logging_utils import get_logger

log = get_logger(__name__)


def load_warehouse(batch_id: str) -> dict[str, int]:
    curated = layer_path("curated")
    names = [item["table"] for item in settings()["warehouse"]["tables"]]
    tables = {name: pd.read_parquet(curated / f"{name}.parquet") for name in names}
    # Lineage: tag the rows with the batch that loaded them
    for name, df in tables.items():
        if "batch_id" in df.columns:
            df["batch_id"] = batch_id
    return load_tables(tables, batch_id)
