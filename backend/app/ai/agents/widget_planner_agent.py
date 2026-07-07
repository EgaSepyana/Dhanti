import json
import re
import uuid

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.agents.base_agent import BaseAgent
from app.ai.schemas import AgentResult, AgentTask
from app.models.dataset import Dataset
from app.providers.manager import get_llm_for_model

WIDGET_TYPES = {"table", "chart", "metric"}

SYSTEM_PROMPT = """You are DHANTI's data analyst — an expert at deciding what a dashboard \
should actually show. Given a dataset's column schema/profile and any analyst insights, \
decide the small set of widgets (3-6) that best answer what the data is about.

Each widget is one of:
- "metric": a single headline number (a KPI/stat tile).
- "chart": a chart showing a trend, comparison, or breakdown. Include a "chart_type" \
(bar, line, scatter, or pie — pie only for a genuinely small part-to-whole split).
- "table": a row-level or grouped data table.

For each widget, describe the data need in plain language — what to compute/group/filter — \
not SQL yet; a separate specialist turns this into a query.

Respond with ONLY a JSON array, no markdown fences, e.g.:
[
  {"name": "total_revenue", "title": "Total Revenue", "type": "metric",
   "description": "Sum of the revenue column across all rows"},
  {"name": "revenue_by_region", "title": "Revenue by Region", "type": "chart",
   "chart_type": "bar", "description": "Total revenue grouped by region, ordered descending"},
  {"name": "raw_data", "title": "All Records", "type": "table",
   "description": "All rows with every column, most relevant columns first"}
]

Only reference column names that actually exist in the schema you're given. Prefer fewer,
higher-signal widgets over an exhaustive list."""

# 3-6 short widget specs as JSON; generous headroom without requesting the
# app-wide default on every call.
WIDGET_PLAN_MAX_TOKENS = 1200


def _extract_json_array(raw: str) -> list[dict]:
    match = re.search(r"\[.*\]", raw, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON array found in LLM response: {raw!r}")
    return json.loads(match.group(0))


def _fallback_widgets(dataset: Dataset) -> list[dict]:
    numeric_cols = [c["name"] for c in dataset.columns if c["type"] in ("integer", "float")]
    metric_field = numeric_cols[0] if numeric_cols else None
    return [
        {
            "name": f"total_{metric_field}" if metric_field else "row_count",
            "title": f"Total {metric_field}" if metric_field else "Row Count",
            "type": "metric",
            "description": f"Sum of {metric_field} across all rows" if metric_field else "Count of all rows",
        },
        {
            "name": "all_data",
            "title": dataset.name,
            "type": "table",
            "description": "All rows, all columns",
        },
    ]


class WidgetPlannerAgent(BaseAgent):
    """DHANTI's data-analysis specialist for dashboards: decides WHAT widgets
    (metric/chart/table) best represent a dataset, from its profile and any
    analyst insights — text_to_sql_agent turns each into a real query next.
    Planning only: no artifact, just a dependency for the next step."""

    name = "widget_planner_agent"

    async def run(self, task: AgentTask, db: AsyncSession) -> AgentResult:
        dataset_id = task.input.get("dataset_id")
        if not dataset_id:
            return self._error(task, "widget_planner_agent requires 'dataset_id' in input")

        dataset = await db.get(Dataset, uuid.UUID(str(dataset_id)))
        if dataset is None:
            return self._error(task, f"Dataset '{dataset_id}' not found")

        dependencies = task.input.get("_dependencies", {})
        insight_output = dependencies.get("insight_agent")
        insight_text = insight_output.get("text") if insight_output else None

        profile_summary = {
            "name": dataset.name,
            "row_count": dataset.row_count,
            "columns": [
                {"name": c["name"], "type": c["type"], "stats": c["stats"]} for c in dataset.columns
            ],
        }
        user_content = f"Dataset columns/profile:\n{json.dumps(profile_summary, default=str)}"
        if insight_text:
            user_content += f"\n\nAnalyst insights:\n{insight_text}"

        widgets: list[dict] = []
        model = task.input.get("_model")
        try:
            llm = get_llm_for_model(model)
            raw = await llm.generate(
                [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                model=model,
                temperature=0.3,
                max_tokens=WIDGET_PLAN_MAX_TOKENS,
            )
            widgets = [w for w in _extract_json_array(raw) if isinstance(w, dict) and w.get("type") in WIDGET_TYPES]
        except Exception as exc:  # noqa: BLE001 - never abort dashboard generation over a planning hiccup
            logger.warning(f"widget_planner_agent: LLM planning failed, using fallback widgets | error={exc}")
            widgets = []

        if not widgets:
            widgets = _fallback_widgets(dataset)

        return self._success(task, {"widgets": widgets}, metadata={"dataset_id": str(dataset.id)})
