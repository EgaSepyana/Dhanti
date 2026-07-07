import asyncio
import io
import json
import re

import duckdb
import pandas as pd

from app.models.dataset import Dataset
from app.services import file_service

DATASET_VIEW_NAME = "dataset"
MAX_RESULT_ROWS = 5000

# Every widget query is LLM-authored (text_to_sql_agent) or submitted through
# the API, then executed server-side with real filesystem/process access —
# unlike the sandboxed Canvas iframe, DuckDB has no sandbox of its own, so
# this denylist is the only thing standing between a query and the host.
# Strategy: single SELECT/WITH statement only, referencing nothing but the
# pre-registered "dataset" view — no file/network readers, no system
# catalogs, no DDL/DML, no extension loading.
_FORBIDDEN_KEYWORDS = [
    # DDL/DML/procedural
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE",
    "GRANT", "REVOKE", "MERGE", "CALL", "EXECUTE", "PREPARE", "DEALLOCATE",
    # System/config/session
    "ATTACH", "DETACH", "PRAGMA", "SET", "RESET", "INSTALL", "LOAD",
    "FORCE", "CHECKPOINT", "VACUUM", "EXPORT", "IMPORT", "COPY",
    # File/network table functions — the query must only ever see "dataset"
    "READ_CSV", "READ_CSV_AUTO", "READ_PARQUET", "READ_JSON", "READ_JSON_AUTO",
    "READ_NDJSON", "PARQUET_SCAN", "GLOB", "SNIFF_CSV", "SCAN_ARROW_IPC",
    "ICEBERG_SCAN", "DELTA_SCAN", "READ_TEXT", "READ_BLOB",
    # Protocol prefixes as a last-resort net
    "HTTP://", "HTTPS://", "S3://", "FTP://", "FILE://",
    # System catalogs that could leak host/db info unrelated to this dataset
    "INFORMATION_SCHEMA", "PG_CATALOG", "DUCKDB_", "SQLITE_MASTER",
]

_FORBIDDEN_PATTERN = re.compile(
    r"(?<![A-Za-z0-9_])(" + "|".join(re.escape(k) for k in _FORBIDDEN_KEYWORDS) + r")(?![A-Za-z0-9_])",
    re.IGNORECASE,
)


class WidgetQueryError(Exception):
    pass


def _strip_comments(sql: str) -> str:
    sql = re.sub(r"--[^\n]*", " ", sql)
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)
    return sql


def validate_widget_sql(query: str) -> None:
    """Raises WidgetQueryError if `query` isn't a safe, single, read-only
    SELECT against the dataset view. See module docstring for the threat
    model — this is a denylist, not a parser, so it errs on the side of
    rejecting anything unusual rather than trying to allow everything safe."""
    stripped = _strip_comments(query).strip()
    if not stripped:
        raise WidgetQueryError("Query is empty")

    # Allow exactly one trailing semicolon, but nothing after it.
    body = stripped[:-1].strip() if stripped.endswith(";") else stripped
    if ";" in body:
        raise WidgetQueryError("Only a single SQL statement is allowed")

    if not re.match(r"^\s*(SELECT|WITH)\b", body, re.IGNORECASE):
        raise WidgetQueryError("Only SELECT (or WITH ... SELECT) queries are allowed")

    match = _FORBIDDEN_PATTERN.search(body)
    if match:
        raise WidgetQueryError(f"Query contains a disallowed keyword: '{match.group(0)}'")


def _run_query_sync(df: pd.DataFrame, query: str) -> tuple[list[str], list[dict]]:
    con = duckdb.connect(":memory:")
    try:
        con.register(DATASET_VIEW_NAME, df)
        result_df = con.execute(query).fetchdf()
    finally:
        con.close()

    result_df = result_df.head(MAX_RESULT_ROWS)
    columns = [str(c) for c in result_df.columns]
    # Round-trip through pandas' JSON encoder so numpy/NaT/NaN become JSON-safe
    # primitives, matching the pattern already used for dataset sample rows.
    rows = json.loads(result_df.to_json(orient="records", date_format="iso"))
    return columns, rows


async def execute_widget_query(dataset: Dataset, query: str) -> tuple[list[str], list[dict], int]:
    """Validates then executes `query` (a widget's stored SQL) against
    `dataset`'s parquet data via a fresh, isolated in-memory DuckDB
    connection. Returns (columns, rows, row_count)."""
    validate_widget_sql(query)

    if not dataset.data_path:
        raise WidgetQueryError(f"Dataset '{dataset.id}' has no stored data")

    content = await file_service.download_bytes(dataset.data_path)
    df = pd.read_parquet(io.BytesIO(content))

    try:
        columns, rows = await asyncio.to_thread(_run_query_sync, df, query)
    except duckdb.Error as exc:
        raise WidgetQueryError(f"Query failed: {exc}") from exc

    return columns, rows, len(rows)
