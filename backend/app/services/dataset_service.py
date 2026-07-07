import math

import pandas as pd


def _clean(value):
    """Convert numpy/pandas scalars to JSON-safe Python primitives."""
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


def _infer_type(series: pd.Series) -> str:
    if pd.api.types.is_bool_dtype(series):
        return "boolean"
    if pd.api.types.is_integer_dtype(series):
        return "integer"
    if pd.api.types.is_float_dtype(series):
        return "float"
    if pd.api.types.is_datetime64_any_dtype(series):
        return "datetime"
    return "string"


def compute_column_stats(series: pd.Series, col_type: str) -> dict:
    stats: dict = {
        "null_count": int(series.isna().sum()),
        "unique_count": int(series.nunique(dropna=True)),
    }

    non_null = series.dropna()

    if col_type in ("integer", "float") and not non_null.empty:
        stats.update(
            {
                "min": _clean(non_null.min()),
                "max": _clean(non_null.max()),
                "mean": _clean(non_null.mean()),
                "median": _clean(non_null.median()),
                "mode": _clean(non_null.mode().iloc[0]) if not non_null.mode().empty else None,
            }
        )
        try:
            counts, bin_edges = pd.cut(non_null, bins=min(10, non_null.nunique()) or 1, retbins=True)
            hist = counts.value_counts(sort=False)
            stats["distribution"] = [
                {"range": f"{bin_edges[i]:.2f}-{bin_edges[i + 1]:.2f}", "count": int(hist.iloc[i])}
                for i in range(len(hist))
            ]
        except (ValueError, IndexError):
            stats["distribution"] = []
    elif col_type == "datetime" and not non_null.empty:
        stats.update({"min": str(non_null.min()), "max": str(non_null.max())})
    else:
        value_counts = non_null.astype(str).value_counts().head(10)
        stats["mode"] = value_counts.index[0] if not value_counts.empty else None
        stats["distribution"] = [
            {"value": str(idx), "count": int(count)} for idx, count in value_counts.items()
        ]

    return stats


def infer_schema(df: pd.DataFrame) -> list[dict]:
    columns = []
    for name in df.columns:
        series = df[name]
        col_type = _infer_type(series)
        columns.append(
            {
                "name": str(name),
                "type": col_type,
                "stats": compute_column_stats(series, col_type),
            }
        )
    return columns


def profile_dataset(df: pd.DataFrame, columns: list[dict]) -> dict:
    return {
        "row_count": len(df),
        "column_count": len(df.columns),
        "missing_total": int(df.isna().sum().sum()),
        "duplicate_rows": int(df.duplicated().sum()),
        "columns_with_nulls": [c["name"] for c in columns if c["stats"].get("null_count", 0) > 0],
    }


def detect_outliers(df: pd.DataFrame) -> dict:
    """IQR-based outlier detection for numeric columns."""
    outliers = {}
    for col in df.select_dtypes(include="number").columns:
        series = df[col].dropna()
        if series.empty:
            continue
        q1, q3 = series.quantile(0.25), series.quantile(0.75)
        iqr = q3 - q1
        if iqr == 0:
            continue
        lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        mask = (series < lower) | (series > upper)
        count = int(mask.sum())
        if count:
            outliers[str(col)] = {
                "count": count,
                "lower_bound": _clean(lower),
                "upper_bound": _clean(upper),
            }
    return outliers


def detect_missing(df: pd.DataFrame) -> dict:
    """Per-column missing value summary."""
    total = len(df)
    missing = {}
    for col in df.columns:
        null_count = int(df[col].isna().sum())
        if null_count:
            missing[str(col)] = {
                "count": null_count,
                "percent": round(null_count / total * 100, 2) if total else 0,
            }
    return missing
