import io
import json
import uuid

import pandas as pd
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import simple_query_engine
from app.ai.agents.base_agent import BaseAgent
from app.ai.schemas import AgentResult, AgentTask
from app.ai.tools import visualization_tools
from app.models.dataset import Dataset
from app.models.widget import WidgetCreate
from app.services import duckdb_service, file_service, widget_service

# Plain fallback sample when the prompt has no aggregation shape to parse —
# still a real, re-runnable widget query rather than a one-off pandas sample,
# so this chart is backed by a live widget exactly like the aggregated path.
_SAMPLE_QUERY = "SELECT * FROM dataset LIMIT 50"


class VisualizationAgent(BaseAgent):
    """Chooses a chart type and builds an ECharts config. Output: visualization artifact.

    Two data paths: if the prompt has an aggregation shape ("top 10 stores by
    sales"), the same zero-LLM parser simple_query_engine uses builds the
    exact (category, value) result to plot — not an arbitrary sample of raw
    rows. Otherwise falls back to a plain sample. Either way, an explicit
    chart type in the prompt ("pie chart") is honored instead of silently
    being overridden by the heuristic.

    Also persists a real Widget row backing whatever query produced the
    chart — without this, a chart created here had no widget_id a dashboard
    could actually reference, so "add this chart to the dashboard" made
    dashboard_revision_agent hallucinate a widget id that didn't exist,
    surfacing as "Widget not found" once the dashboard tried to load it."""

    name = "visualization_agent"

    async def run(self, task: AgentTask, db: AsyncSession) -> AgentResult:
        dataset_id = task.input.get("dataset_id")
        if not dataset_id:
            return self._error(task, "visualization_agent requires 'dataset_id' in input")

        dataset = await db.get(Dataset, uuid.UUID(str(dataset_id)))
        if dataset is None:
            return self._error(task, f"Dataset '{dataset_id}' not found")
        if not dataset.data_path:
            return self._error(task, f"Dataset '{dataset_id}' has no stored data")

        prompt = task.context.get("prompt", "")
        requested_chart_type = task.input.get("chart_type") or visualization_tools.detect_requested_chart_type(
            prompt
        )

        agg_result = await self._try_aggregated_result(prompt, dataset)
        if agg_result is not None:
            sql, x_field, y_field, rows = agg_result
            chart_type = requested_chart_type or visualization_tools.choose_chart_type_for_result(len(rows))
            config = visualization_tools.build_echarts_config_from_result(chart_type, x_field, y_field, rows)
        else:
            sql = _SAMPLE_QUERY
            content = await file_service.download_bytes(dataset.data_path)
            df = pd.read_parquet(io.BytesIO(content))
            sample_rows = json.loads(df.head(50).to_json(orient="records", date_format="iso"))
            chart_type = requested_chart_type or visualization_tools.choose_chart_type(
                dataset.columns, dataset.row_count
            )
            config = visualization_tools.build_echarts_config(
                chart_type, dataset.columns, sample_rows, dataset.row_count
            )

        widget_id = await self._create_backing_widget(db, task, dataset, chart_type, sql, prompt)

        output = {
            "library": "echarts",
            "config": config,
            "data_source": str(dataset.id),
            "widget_id": widget_id,
        }
        return self._success(
            task,
            output,
            artifact_type="visualization",
            metadata={"dataset_id": str(dataset.id), "chart_type": chart_type, "widget_id": widget_id},
        )

    async def _try_aggregated_result(
        self, prompt: str, dataset: Dataset
    ) -> tuple[str, str, str, list[dict]] | None:
        sql = simple_query_engine.build_query(prompt, dataset)
        if sql is None:
            return None
        try:
            columns_out, rows, _ = await duckdb_service.execute_widget_query(dataset, sql)
        except duckdb_service.WidgetQueryError as exc:
            logger.warning(f"visualization_agent: aggregated query failed, falling back to raw sample | error={exc}")
            return None
        if not rows or len(columns_out) < 2:
            return None
        return sql, columns_out[0], columns_out[-1], rows

    async def _create_backing_widget(
        self,
        db: AsyncSession,
        task: AgentTask,
        dataset: Dataset,
        chart_type: str,
        sql: str,
        prompt: str,
    ) -> str | None:
        title = prompt.strip().rstrip("?.! ").capitalize() if 0 < len(prompt.strip()) <= 100 else f"{chart_type.title()} chart"
        try:
            widget = await widget_service.create_widget(
                db,
                uuid.UUID(str(task.workspace_id)),
                WidgetCreate(
                    dataset_id=dataset.id,
                    name=f"{chart_type}_chart_{uuid.uuid4().hex[:8]}",
                    title=title,
                    type="chart",
                    query=sql,
                    config={"chart_type": chart_type},
                ),
            )
        except Exception as exc:  # noqa: BLE001 - the chart itself still renders even if widget persistence fails
            logger.warning(f"visualization_agent: failed to create backing widget | error={exc}")
            return None
        return str(widget.id)
