from app.ai.tools.registry import register_tool

NUMERIC_TYPES = ("integer", "float")

# Fixed categorical hue order (dataviz skill's validated default instance,
# light-mode steps) — never cycled, and shared with dashboard-runtime-source.ts
# so a static chart artifact and a live dashboard widget use the same series
# colors for the same kind of data.
CATEGORICAL_PALETTE = [
    "#2a78d6", "#1baf7a", "#eda100", "#008300", "#4a3aa7", "#e34948", "#e87ba4", "#eb6834",
]

PIE_MAX_CATEGORIES = 6

# Below this unique-values-to-row-count ratio, an integer column reads as a
# category/identifier (a store number, a flag) rather than a measured
# quantity — without this, "Store" (an ID) got picked as the numeric field
# to plot ahead of a genuine metric like "Weekly_Sales" simply because it's
# an integer column and happened to be listed first. See simple_query_engine,
# which needed the identical guard for the same reason.
_CATEGORICAL_INT_CARDINALITY_RATIO = 0.5


def _is_metric_column(col: dict, row_count: int) -> bool:
    if col["type"] == "float":
        return True
    if col["type"] != "integer":
        return False
    unique_count = col.get("stats", {}).get("unique_count")
    if not row_count or unique_count is None:
        return False
    return (unique_count / row_count) >= _CATEGORICAL_INT_CARDINALITY_RATIO


_CHART_TYPE_KEYWORDS: tuple[tuple[str, str], ...] = (
    ("pie", "pie"),
    ("scatter", "scatter"),
    ("trend", "line"),
    ("line", "line"),
    ("column chart", "bar"),
    ("bar", "bar"),
)


def detect_requested_chart_type(prompt: str) -> str | None:
    """Deterministic keyword match for an explicit chart type in the user's
    own words — no LLM, no heuristic guessing. visualization_agent already
    silently ignored this entirely (task.input["chart_type"] was never
    populated by anything), which is why asking for a pie chart could still
    come back as a bar chart."""
    text = prompt.lower()
    for keyword, chart_type in _CHART_TYPE_KEYWORDS:
        if keyword in text:
            return chart_type
    return None


@register_tool("choose_chart_type")
def choose_chart_type(columns: list[dict], row_count: int = 0) -> str:
    """Chooses a chart type by the data's job, not just its type composition:
    trend over time -> line, magnitude across categories -> bar (the safe
    default), correlation between two measures -> scatter, and a genuinely
    small part-to-whole split -> pie. Bar is preferred over pie whenever a
    category count gets large enough that slices stop being legible."""
    numeric = [c for c in columns if _is_metric_column(c, row_count)]
    datetime_cols = [c for c in columns if c["type"] == "datetime"]
    categorical = [c for c in columns if c["type"] == "string"]

    if datetime_cols and numeric:
        return "line"
    if categorical and numeric:
        if _unique_count(categorical[0]) <= PIE_MAX_CATEGORIES:
            return "pie"
        return "bar"
    if len(numeric) >= 2:
        return "scatter"
    if categorical:
        if _unique_count(categorical[0]) <= PIE_MAX_CATEGORIES:
            return "pie"
        return "bar"
    return "bar"


def _unique_count(column: dict) -> int:
    """Falls back to "too many to slice" when stats are missing, so an
    unprofiled column never accidentally gets a pie chart it can't support."""
    count = column.get("stats", {}).get("unique_count")
    return count if isinstance(count, int) else PIE_MAX_CATEGORIES + 1


@register_tool("choose_fields")
def choose_fields(chart_type: str, columns: list[dict], row_count: int = 0) -> tuple[str | None, str | None]:
    """Rule-based x/y field selection, shared by build_echarts_config (static
    charts) and dashboard_agent (field mappings for live Canvas data binding)."""
    numeric = [c["name"] for c in columns if _is_metric_column(c, row_count)]
    categorical = [c["name"] for c in columns if c["type"] == "string"]
    datetime_cols = [c["name"] for c in columns if c["type"] == "datetime"]

    if chart_type == "line" and datetime_cols and numeric:
        return datetime_cols[0], numeric[0]
    if chart_type in ("bar", "pie") and categorical and numeric:
        return categorical[0], numeric[0]
    if chart_type == "scatter" and len(numeric) >= 2:
        return numeric[0], numeric[1]

    x_field = categorical[0] if categorical else (numeric[0] if numeric else None)
    y_field = numeric[0] if numeric else None
    return x_field, y_field


@register_tool("build_echarts_config")
def build_echarts_config(
    chart_type: str, columns: list[dict], sample_rows: list[dict], row_count: int = 0
) -> dict:
    numeric = [c["name"] for c in columns if _is_metric_column(c, row_count)]
    x_field, y_field = choose_fields(chart_type, columns, row_count)

    categories = [str(row.get(x_field)) for row in sample_rows] if x_field else []
    values = [row.get(y_field) for row in sample_rows] if y_field else []

    if chart_type == "pie":
        if y_field:
            series = [{"name": cat, "value": val} for cat, val in zip(categories, values, strict=False)]
        else:
            # No numeric field to sum — the slice value is how often each
            # category occurs (e.g. "region" alone -> count of rows per region).
            counts: dict[str, int] = {}
            for cat in categories:
                counts[cat] = counts.get(cat, 0) + 1
            series = [{"name": cat, "value": count} for cat, count in counts.items()]
        return {
            "color": CATEGORICAL_PALETTE,
            "tooltip": {"trigger": "item"},
            "legend": {"top": "bottom"},
            "series": [{"type": "pie", "radius": "60%", "data": series}],
        }

    if chart_type == "scatter":
        data = list(zip(values, [row.get(numeric[1]) if len(numeric) > 1 else None for row in sample_rows], strict=False))
        return {
            "color": CATEGORICAL_PALETTE,
            "tooltip": {"trigger": "item"},
            "xAxis": {"type": "value", "name": x_field},
            "yAxis": {"type": "value", "name": y_field},
            "series": [{"type": "scatter", "data": data}],
        }

    return {
        "color": CATEGORICAL_PALETTE,
        "tooltip": {"trigger": "axis"},
        "xAxis": {"type": "category", "name": x_field, "data": categories},
        "yAxis": {"type": "value", "name": y_field},
        "series": [{"type": chart_type, "name": y_field, "data": values}],
    }


def choose_chart_type_for_result(num_categories: int) -> str:
    """Default chart type for an already-aggregated (category, value) result
    when the user didn't name one explicitly: a small part-to-whole split
    reads fine as a pie, more categories than that stop being legible as
    slices and read better as a bar."""
    return "pie" if num_categories <= PIE_MAX_CATEGORIES else "bar"


def build_echarts_config_from_result(chart_type: str, x_field: str, y_field: str, rows: list[dict]) -> dict:
    """Builds a chart directly from an already-aggregated (category, value)
    result set — e.g. simple_query_engine's "top 10 stores by total sales"
    query — instead of guessing fields by column type over unaggregated
    sample rows. x_field/y_field are already known from how the aggregation
    was built, so there's no field-selection heuristic to get wrong here."""
    categories = [str(row.get(x_field)) for row in rows]
    values = [row.get(y_field) for row in rows]

    if chart_type == "pie":
        series = [{"name": cat, "value": val} for cat, val in zip(categories, values, strict=False)]
        return {
            "color": CATEGORICAL_PALETTE,
            "tooltip": {"trigger": "item"},
            "legend": {"top": "bottom"},
            "series": [{"type": "pie", "radius": "60%", "data": series}],
        }

    if chart_type == "scatter":
        data = list(zip(range(len(values)), values, strict=False))
        return {
            "color": CATEGORICAL_PALETTE,
            "tooltip": {"trigger": "item"},
            "xAxis": {"type": "value", "name": x_field},
            "yAxis": {"type": "value", "name": y_field},
            "series": [{"type": "scatter", "data": data}],
        }

    return {
        "color": CATEGORICAL_PALETTE,
        "tooltip": {"trigger": "axis"},
        "xAxis": {"type": "category", "name": x_field, "data": categories},
        "yAxis": {"type": "value", "name": y_field},
        "series": [{"type": chart_type, "name": y_field, "data": values}],
    }
