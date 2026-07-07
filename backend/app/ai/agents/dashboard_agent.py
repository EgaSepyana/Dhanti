import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.agents.base_agent import BaseAgent
from app.ai.schemas import AgentResult, AgentTask
from app.models.dataset import Dataset

GRID_COLUMNS = 12

_SIZE_BY_TYPE = {
    "metric": {"w": 3, "h": 2},
    "chart": {"w": 6, "h": 4},
    "table": {"w": 12, "h": 4},
}


class DashboardAgent(BaseAgent):
    """Plans a dashboard's layout — grid position/size per widget, in a
    simple left-to-right/wrap-to-next-row flow — from the widgets
    text_to_sql_agent already generated and persisted. Internal planning
    only: no artifact, just a dependency for code_generation_agent, the
    "developer" agent that writes the HTML calling each widget's
    /api/widgets/{id}/handler endpoint for its live data."""

    name = "dashboard_agent"

    async def run(self, task: AgentTask, db: AsyncSession) -> AgentResult:
        dataset_id = task.input.get("dataset_id")
        if not dataset_id:
            return self._error(task, "dashboard_agent requires 'dataset_id' in input")

        dataset = await db.get(Dataset, uuid.UUID(str(dataset_id)))
        if dataset is None:
            return self._error(task, f"Dataset '{dataset_id}' not found")

        dependencies = task.input.get("_dependencies", {})
        sql_output = dependencies.get("text_to_sql_agent")
        widgets = sql_output.get("widgets") if sql_output else None
        if not widgets:
            return self._error(task, "dashboard_agent requires a text_to_sql_agent dependency")

        layout_widgets = []
        cursor_x, cursor_y, row_height = 0, 0, 0
        for widget in widgets:
            size = _SIZE_BY_TYPE.get(widget["type"], {"w": 6, "h": 4})
            if cursor_x + size["w"] > GRID_COLUMNS:
                cursor_x = 0
                cursor_y += row_height
                row_height = 0
            layout_widgets.append(
                {
                    "widget_id": widget["id"],
                    "name": widget["name"],
                    "title": widget["title"],
                    "type": widget["type"],
                    "position": {"x": cursor_x, "y": cursor_y, **size},
                }
            )
            cursor_x += size["w"]
            row_height = max(row_height, size["h"])

        output = {
            "layout": {"type": "grid", "columns": GRID_COLUMNS},
            "widgets": layout_widgets,
            "theme": {
                "mode": "light",
                # dataviz skill's validated default palette (blue/orange slots) —
                # matches dashboard-runtime's built-in CSS defaults, so this only
                # needs to diverge from them for real per-dashboard branding.
                "primary_color": "#2a78d6",
                "accent_color": "#eb6834",
                "font": "system-ui, -apple-system, \"Segoe UI\", sans-serif",
            },
        }

        # No artifact_type: this is a planning step only, consumed by
        # code_generation_agent via _dependencies — see class docstring.
        return self._success(task, output, metadata={"dataset_id": str(dataset.id)})
