import io
import json
import uuid

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.agents.base_agent import BaseAgent
from app.ai.schemas import AgentResult, AgentTask
from app.ai.tools import dataset_tools
from app.models.dataset import Dataset
from app.services import file_service


class DatasetAgent(BaseAgent):
    """Profiles a parsed dataset: stats, outliers, missing values. Output: dataset artifact."""

    name = "dataset_agent"

    async def run(self, task: AgentTask, db: AsyncSession) -> AgentResult:
        dataset_id = task.input.get("dataset_id")
        if not dataset_id:
            return self._error(task, "dataset_agent requires 'dataset_id' in input")

        dataset = await db.get(Dataset, uuid.UUID(str(dataset_id)))
        if dataset is None:
            return self._error(task, f"Dataset '{dataset_id}' not found")
        if not dataset.data_path:
            return self._error(task, f"Dataset '{dataset_id}' has no stored data")

        content = await file_service.download_bytes(dataset.data_path)
        df = pd.read_parquet(io.BytesIO(content))

        outliers = dataset_tools.detect_outliers(df)
        missing = dataset_tools.detect_missing(df)
        sample_rows = json.loads(df.head(20).to_json(orient="records", date_format="iso"))

        output = {
            "columns": dataset.columns,
            "rows": sample_rows,
            "schema": {"row_count": dataset.row_count, "column_count": len(dataset.columns)},
            "stats": {**dataset.profile, "outliers": outliers, "missing": missing},
        }

        return self._success(
            task, output, artifact_type="dataset", metadata={"dataset_id": str(dataset.id)}
        )
