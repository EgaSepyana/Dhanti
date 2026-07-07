import pandas as pd

from app.ai.tools.registry import register_tool
from app.services import dataset_service


@register_tool("profile_dataset")
def profile_dataset(df: pd.DataFrame, columns: list[dict]) -> dict:
    return dataset_service.profile_dataset(df, columns)


@register_tool("compute_stats")
def compute_stats(series: pd.Series, col_type: str) -> dict:
    return dataset_service.compute_column_stats(series, col_type)


@register_tool("detect_outliers")
def detect_outliers(df: pd.DataFrame) -> dict:
    return dataset_service.detect_outliers(df)


@register_tool("detect_missing")
def detect_missing(df: pd.DataFrame) -> dict:
    return dataset_service.detect_missing(df)
