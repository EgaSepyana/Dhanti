import re
from dataclasses import dataclass

from app.models.dataset import Dataset
from app.services import duckdb_service

# Ranking direction: which end of a sorted aggregate the question wants.
_RANK_DESC = re.compile(r"\b(highest|largest|biggest|maximum|max|most|top)\b", re.IGNORECASE)
_RANK_ASC = re.compile(r"\b(lowest|smallest|minimum|min|least|bottom)\b", re.IGNORECASE)

# Aggregate function: how to combine values within a group (or overall).
_METRIC_COUNT = re.compile(r"\b(how many|count of|number of|count)\b", re.IGNORECASE)
_METRIC_AVG = re.compile(r"\b(average|avg|mean)\b", re.IGNORECASE)
_METRIC_SUM = re.compile(r"\b(total|sum)\b", re.IGNORECASE)

_TOP_N_PATTERN = re.compile(r"\btop\s+(\d+)\b", re.IGNORECASE)
_YEAR_PATTERN = re.compile(r"\b(19|20)\d{2}\b")

# A request for a visual chart needs visualization_agent, which this engine
# has no concept of — bail out even if the phrasing also looks like an
# aggregation (e.g. "top 10 ... as a pie chart"), so a wrong execution_router
# classification can never turn into a silently chart-less text answer.
_CHART_REQUEST_PATTERN = re.compile(
    r"\b(chart|plot|graph|visuali[sz]e|visuali[sz]ation|pie|histogram)\b", re.IGNORECASE
)

_STOPWORDS = {"the", "of", "in", "on", "at", "by", "for", "and", "or", "id", "a", "an"}

# Below this unique-values-to-row-count ratio, an integer column reads as a
# category/identifier (a store number, a flag) rather than a quantity — the
# earlier version of this engine summed a "Store" ID column itself for
# "which store had the highest sales", which is exactly what this guards
# against. Floats are treated as metrics unconditionally: a low-cardinality
# float (e.g. a handful of price points) is still a measured quantity, not
# an identifier, in every dataset shape this app parses.
_CATEGORICAL_INT_CARDINALITY_RATIO = 0.5


@dataclass
class SimpleQueryResult:
    answer: str
    sql: str


def _name_tokens(name: str) -> set[str]:
    words = re.split(r"[_\s]+", name.lower())
    return {w for w in words if len(w) > 2 and w not in _STOPWORDS}


def _mentions_column(text_tokens: set[str], col: dict) -> bool:
    name_tokens = _name_tokens(col["name"])
    if not name_tokens:
        return False
    return bool(name_tokens & text_tokens) or col["name"].lower() in " ".join(text_tokens)


def _is_metric_candidate(col: dict, row_count: int) -> bool:
    if col["type"] == "float":
        return True
    if col["type"] != "integer":
        return False
    unique_count = col.get("stats", {}).get("unique_count")
    if not row_count or unique_count is None:
        return False
    return (unique_count / row_count) >= _CATEGORICAL_INT_CARDINALITY_RATIO


def _is_group_candidate(col: dict, row_count: int) -> bool:
    if col["type"] == "string":
        return True
    if col["type"] != "integer":
        return False
    return not _is_metric_candidate(col, row_count)


def _find_column(text_tokens: set[str], columns: list[dict], predicate) -> dict | None:
    for col in columns:
        if predicate(col) and _mentions_column(text_tokens, col):
            return col
    return None


def _find_literal_filter(text: str, columns: list[dict]) -> tuple[dict, str] | None:
    """A categorical column whose actual value (from its computed distribution
    — not a guess) appears verbatim in the prompt, e.g. "orders from the West
    region" matching region='West'."""
    for col in columns:
        if col["type"] != "string":
            continue
        values = [d.get("value") for d in col.get("stats", {}).get("distribution", [])]
        for value in values:
            if value and re.search(rf"\b{re.escape(str(value))}\b", text, re.IGNORECASE):
                return col, value
    return None


def build_query(prompt: str, dataset: Dataset) -> str | None:
    """Parses a factual aggregate question into a SQL shape via keyword/regex
    rules only — no LLM. Returns None (never a wrong guess) when the question
    can't be confidently parsed. Shared by try_execute (a text answer) and
    visualization_agent (chart data) so "top 10 X by Y" means the same
    aggregation whether the request wants words or a chart back."""
    text = prompt.strip()
    text_lower = text.lower()
    text_tokens = {w for w in re.split(r"[^a-z0-9]+", text_lower) if w}
    columns = dataset.columns or []
    row_count = dataset.row_count or 0

    if _METRIC_COUNT.search(text_lower):
        metric = "COUNT"
    elif _METRIC_AVG.search(text_lower):
        metric = "AVG"
    elif _METRIC_SUM.search(text_lower):
        metric = "SUM"
    elif _RANK_DESC.search(text_lower) or _RANK_ASC.search(text_lower):
        # "which store has the highest sales" names no explicit metric word —
        # ranking a raw value by SUM per group is the natural reading.
        metric = "SUM"
    else:
        return None

    numeric_col = None
    if metric != "COUNT":
        numeric_col = _find_column(
            text_tokens, columns, lambda c: _is_metric_candidate(c, row_count)
        )
        if numeric_col is None:
            return None

    group_col = _find_column(
        text_tokens,
        [c for c in columns if c is not numeric_col],
        lambda c: _is_group_candidate(c, row_count),
    )

    rank_desc = bool(_RANK_DESC.search(text_lower))
    rank_asc = bool(_RANK_ASC.search(text_lower))
    top_n_match = _TOP_N_PATTERN.search(text_lower)
    limit = int(top_n_match.group(1)) if top_n_match else (1 if (rank_desc or rank_asc) else None)

    where_parts = []
    year_match = _YEAR_PATTERN.search(text)
    # Prefer a real datetime column, but many CSV imports leave dates as
    # strings (pandas didn't recognize the format) — a name-based fallback
    # still lets a year filter apply instead of silently being dropped and
    # the query quietly answering over all years instead.
    date_col = next(
        (c for c in columns if c["type"] == "datetime"),
        None,
    ) or next(
        (c for c in columns if c["type"] == "string" and re.search(r"date|time|year", c["name"], re.IGNORECASE)),
        None,
    )
    if year_match and date_col:
        where_parts.append(f"CAST(\"{date_col['name']}\" AS VARCHAR) LIKE '%{year_match.group(0)}%'")

    literal_filter = _find_literal_filter(text, columns)
    if literal_filter:
        filter_col, filter_value = literal_filter
        if filter_col is not group_col:
            escaped = str(filter_value).replace("'", "''")
            where_parts.append(f"\"{filter_col['name']}\" = '{escaped}'")

    where_clause = f" WHERE {' AND '.join(where_parts)}" if where_parts else ""

    if metric == "COUNT" and group_col is None and numeric_col is None:
        select_expr = "COUNT(*) AS count"
        order_clause = ""
        limit_clause = ""
    else:
        agg_alias = f"{numeric_col['name']}_{metric.lower()}" if numeric_col else "count"
        agg_expr = f'{metric}("{numeric_col["name"]}")' if numeric_col else f"{metric}(*)"

        if group_col:
            select_expr = f'"{group_col["name"]}", {agg_expr} AS "{agg_alias}"'
            order_clause = f' ORDER BY {agg_expr} {"ASC" if rank_asc else "DESC"}'
            limit_clause = f" LIMIT {limit}" if limit else ""
        else:
            select_expr = f'{agg_expr} AS "{agg_alias}"'
            order_clause = ""
            limit_clause = ""

    group_clause = f' GROUP BY "{group_col["name"]}"' if group_col else ""
    return f"SELECT {select_expr} FROM dataset{where_clause}{group_clause}{order_clause}{limit_clause}"


async def try_execute(prompt: str, dataset: Dataset) -> SimpleQueryResult | None:
    """Attempts to answer a factual aggregate question with zero LLM calls:
    build_query's SQL, executed exactly like any other widget query. Returns
    None (never a wrong guess) when the question can't be confidently parsed
    or is actually a chart request, so the caller can fall back to the
    LLM-driven dataset_qa_agent instead."""
    if _CHART_REQUEST_PATTERN.search(prompt.lower()):
        return None

    sql = build_query(prompt, dataset)
    if sql is None:
        return None

    try:
        columns_out, rows, _ = await duckdb_service.execute_widget_query(dataset, sql)
    except duckdb_service.WidgetQueryError:
        return None

    if not rows:
        return SimpleQueryResult(answer="The query returned no matching rows.", sql=sql)
    if len(rows) == 1:
        answer = "; ".join(f"{col}: {rows[0].get(col)}" for col in columns_out)
    else:
        lines = [", ".join(f"{col}={row.get(col)}" for col in columns_out) for row in rows[:10]]
        suffix = f" (showing 10 of {len(rows)} rows)" if len(rows) > 10 else ""
        answer = "\n".join(lines) + suffix
    return SimpleQueryResult(answer=answer, sql=sql)
