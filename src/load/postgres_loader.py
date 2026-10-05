"""Load the curated tables into the PostgreSQL warehouse.

Rerun strategy (idempotency):
  * The schema is created with CREATE ... IF NOT EXISTS, so it can run every time.
  * Survey tables use "replace partition": the rows for this survey year are deleted
    and reloaded. Running the pipeline twice gives the same row counts, never doubles.
  * Lookup tables (dim_region) use UPSERT (INSERT ... ON CONFLICT DO UPDATE).
  * Everything happens in ONE transaction: if any table fails, nothing is changed.
Every load is recorded in the pipeline_run audit table.
"""
import io

import pandas as pd
import psycopg2
from psycopg2 import sql

from src.config import PROJECT_ROOT, settings, warehouse_params
from src.utils.io_utils import utc_now
from src.utils.logging_utils import get_logger

log = get_logger(__name__)

SCHEMA_FILE = PROJECT_ROOT / "sql" / "01_create_schema.sql"


def connect():
    params = warehouse_params()
    log.info("Connecting to warehouse %s:%s/%s", params["host"], params["port"], params["dbname"])
    return psycopg2.connect(**params, connect_timeout=10)


def create_schema(cur) -> None:
    cur.execute(SCHEMA_FILE.read_text(encoding="utf-8"))
    log.info("Schema ensured from %s", SCHEMA_FILE.name)


def _copy_frame(cur, table: str, df: pd.DataFrame) -> None:
    """Bulk-insert a DataFrame with COPY (much faster than row-by-row INSERTs)."""
    buffer = io.StringIO()
    df.to_csv(buffer, index=False, header=False)
    buffer.seek(0)
    statement = sql.SQL("COPY {} ({}) FROM STDIN WITH (FORMAT csv)").format(
        sql.Identifier(table), sql.SQL(", ").join(map(sql.Identifier, df.columns)))
    cur.copy_expert(statement.as_string(cur), buffer)


def _upsert_frame(cur, table: str, df: pd.DataFrame, key: list[str]) -> None:
    """Load into a temporary table, then merge into the target on its key."""
    temp = f"tmp_{table}"
    cur.execute(sql.SQL("CREATE TEMP TABLE {} (LIKE {} INCLUDING DEFAULTS) ON COMMIT DROP").format(
        sql.Identifier(temp), sql.Identifier(table)))
    _copy_frame(cur, temp, df)
    cols = list(df.columns)
    updates = [c for c in cols if c not in key]
    cur.execute(sql.SQL("INSERT INTO {t} ({c}) SELECT {c} FROM {tmp} "
                        "ON CONFLICT ({k}) DO UPDATE SET {u}").format(
        t=sql.Identifier(table), tmp=sql.Identifier(temp),
        c=sql.SQL(", ").join(map(sql.Identifier, cols)),
        k=sql.SQL(", ").join(map(sql.Identifier, key)),
        u=sql.SQL(", ").join(sql.SQL("{0} = EXCLUDED.{0}").format(sql.Identifier(c)) for c in updates)))


def load_tables(tables: dict[str, pd.DataFrame], batch_id: str) -> dict[str, int]:
    """Load tables in the order given in config (parents before children)."""
    plan = settings()["warehouse"]["tables"]
    year = settings()["survey_year"]
    started = utc_now()
    counts: dict[str, int] = {}

    conn = connect()
    try:
        with conn:  # commits on success, rolls back on any exception
            with conn.cursor() as cur:
                create_schema(cur)

                # Delete children before parents so foreign keys are never violated
                for item in reversed(plan):
                    if item["strategy"] == "replace_year":
                        cur.execute(sql.SQL("DELETE FROM {} WHERE survey_year = %s").format(
                            sql.Identifier(item["table"])), (year,))
                        log.info("Cleared %s rows for survey_year=%s: %d",
                                 item["table"], year, cur.rowcount)

                for item in plan:
                    name = item["table"]
                    df = tables[name]
                    if item["strategy"] == "upsert":
                        _upsert_frame(cur, name, df, item["key"])
                    else:
                        _copy_frame(cur, name, df)
                    counts[name] = len(df)
                    log.info("Loaded %s: %d rows", name, len(df))

                cur.execute(
                    "INSERT INTO pipeline_run (batch_id, survey_year, started_at, finished_at, row_counts) "
                    "VALUES (%s, %s, %s, now(), %s::jsonb)",
                    (batch_id, year, started, pd.Series(counts).to_json()))
    finally:
        conn.close()
    log.info("Warehouse load committed for batch %s", batch_id)
    return counts
