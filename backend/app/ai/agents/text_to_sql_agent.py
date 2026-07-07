import json
import re
import uuid

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.agents.base_agent import BaseAgent
from app.ai.schemas import AgentResult, AgentTask
from app.models.dataset import Dataset
from app.models.widget import WidgetCreate
from app.providers.manager import get_llm_for_model
from app.services import widget_service

SYSTEM_PROMPT = """You are DHANTI's text-to-SQL specialist. You write DuckDB SQL that runs \
against a single table named "dataset" — the only table that exists. Given the dataset's \
column schema and a plain-language description of what a widget needs, write ONE safe, \
read-only SELECT (or WITH ... SELECT) query that produces exactly that.

Rules:
- Reference ONLY the "dataset" table and ONLY columns that exist in the schema you're given.
- Never use file/network functions (read_csv, read_parquet, http(s):// URLs, ATTACH, etc.) — \
the data is already loaded as "dataset".
- Never use DDL/DML (CREATE, INSERT, UPDATE, DELETE, DROP, ALTER, COPY, PRAGMA, INSTALL, ...).
- Exactly one statement, no trailing commentary.
- Quote column names with spaces or special characters using double quotes.
- For a "metric" widget, return a single row with a single aggregate column.
- For a "chart" widget, return one row per category/time bucket with the fields to plot.
- For a "table" widget, return the rows/columns to display, with a LIMIT if the widget asks \
for "all" data (cap at 500 rows to keep the response light).

Respond with ONLY the SQL query text — no markdown fences, no explanation."""

# One SQL query, called once per widget (up to several times per dashboard) —
# keeping this small matters most for a provider's per-minute token budget,
# since it's the call most likely to repeat back-to-back in one request.
SQL_MAX_TOKENS = 400


def _extract_sql(raw: str) -> str:
    raw = raw.strip()
    raw = re.sub(r"^```(?:sql)?\s*\n?", "", raw)
    raw = re.sub(r"\n?```\s*$", "", raw)
    return raw.strip()


class TextToSQLAgent(BaseAgent):
    """Turns each widget_planner_agent spec into a validated DuckDB SQL query
    and persists it as a Widget row (see widget_service/duckdb_service) — the
    query, not precomputed values, is what's stored, so a dashboard's widgets
    always reflect live data when executed via /api/widgets/{id}/handler."""

    name = "text_to_sql_agent"

    async def run(self, task: AgentTask, db: AsyncSession) -> AgentResult:
        dataset_id = task.input.get("dataset_id")
        if not dataset_id:
            return self._error(task, "text_to_sql_agent requires 'dataset_id' in input")

        dataset = await db.get(Dataset, uuid.UUID(str(dataset_id)))
        if dataset is None:
            return self._error(task, f"Dataset '{dataset_id}' not found")

        dependencies = task.input.get("_dependencies", {})
        planner_output = dependencies.get("widget_planner_agent")
        widget_specs = planner_output.get("widgets") if planner_output else None
        if not widget_specs:
            return self._error(task, "text_to_sql_agent requires a widget_planner_agent dependency")

        workspace_id = uuid.UUID(str(task.workspace_id))
        schema_desc = json.dumps([{"name": c["name"], "type": c["type"]} for c in dataset.columns])
        model = task.input.get("_model")
        llm = get_llm_for_model(model)

        created_widgets: list[dict] = []
        errors: list[str] = []

        for spec in widget_specs:
            name = str(spec.get("name") or "widget")
            title = str(spec.get("title") or name)
            widget_type = spec.get("type") if spec.get("type") in ("table", "chart", "metric") else "table"
            description = str(spec.get("description") or title)

            try:
                raw = await llm.generate(
                    [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {
                            "role": "user",
                            "content": (
                                f"Dataset columns:\n{schema_desc}\n\n"
                                f'Widget "{title}" ({widget_type}) needs: {description}'
                            ),
                        },
                    ],
                    model=model,
                    temperature=0.0,
                    max_tokens=SQL_MAX_TOKENS,
                )
                query = _extract_sql(raw)
                config = {
                    k: v for k, v in spec.items() if k not in ("name", "title", "type", "description")
                }

                widget = await widget_service.create_widget(
                    db,
                    workspace_id,
                    WidgetCreate(
                        dataset_id=dataset.id,
                        name=name,
                        title=title,
                        type=widget_type,
                        query=query,
                        config=config,
                    ),
                )
                created_widgets.append(
                    {"id": str(widget.id), "name": widget.name, "title": widget.title, "type": widget.type}
                )
            except Exception as exc:  # noqa: BLE001 - one bad widget must not sink the rest
                logger.warning(f"text_to_sql_agent: widget '{title}' failed | error={exc}")
                errors.append(f"{title}: {exc}")

        if not created_widgets:
            return self._error(task, f"No widgets could be generated: {'; '.join(errors)}")

        return self._success(
            task,
            {"widgets": created_widgets, "dataset_id": str(dataset.id)},
            metadata={"errors": errors} if errors else {},
        )
