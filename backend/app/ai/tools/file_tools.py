import io

import pandas as pd

from app.ai.tools.registry import register_tool
from app.services import dataset_service


@register_tool("detect_encoding")
def detect_encoding(content: bytes) -> str:
    try:
        content.decode("utf-8")
        return "utf-8"
    except UnicodeDecodeError:
        return "latin-1"


@register_tool("read_csv")
def read_csv(content: bytes) -> pd.DataFrame:
    encoding = detect_encoding(content)
    return pd.read_csv(io.BytesIO(content), encoding=encoding)


@register_tool("read_excel")
def read_excel(content: bytes) -> pd.DataFrame:
    return pd.read_excel(io.BytesIO(content))


@register_tool("infer_schema")
def infer_schema(df: pd.DataFrame) -> list[dict]:
    return dataset_service.infer_schema(df)
