import uuid

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.agents.base_agent import BaseAgent
from app.ai.agents.text_to_sql_agent import SQL_MAX_TOKENS, _extract_sql
from app.ai.schemas import AgentResult, AgentTask
from app.models.dataset import Dataset
from app.providers.manager import get_llm_for_model
from app.services import duckdb_service

SYSTEM_PROMPT = """You are DHANTI's data analyst assistant. You write DuckDB SQL that runs \
against a single table named "dataset" — the only table that exists. Given the dataset's \
column schema and the user's specific question, write ONE safe, read-only SELECT (or WITH \
... SELECT) query whose result set directly answers it — no follow-up query needed.

Rules:
- Reference ONLY the "dataset" table and ONLY columns that exist in the schema you're given.
- Never use file/network functions (read_csv, read_parquet, http(s):// URLs, ATTACH, etc.) — \
the data is already loaded as "dataset".
- Never use DDL/DML (CREATE, INSERT, UPDATE, DELETE, DROP, ALTER, COPY, PRAGMA, INSTALL, ...).
- Exactly one statement, no trailing commentary.
- Quote column names with spaces or special characters using double quotes.
- Aggregate/filter/sort/limit so the result set already contains the answer — e.g. for \
"which X has the highest Y" return one row with X and Y, already sorted descending and \
limited to 1. For "how many..." return a single count. Don't return raw unaggregated rows \
unless the question genuinely asks to list them.

Respond with ONLY the SQL query text — no markdown fences, no explanation."""


def _format_answer(columns: list[str], rows: list[dict]) -> str:
    if not rows:
        return "The query returned no matching rows."
    if len(rows) == 1:
        return "; ".join(f"{col}: {rows[0].get(col)}" for col in columns)
    lines = [", ".join(f"{col}={row.get(col)}" for col in columns) for row in rows[:10]]
    suffix = f" (showing 10 of {len(rows)} rows)" if len(rows) > 10 else ""
    return "\n".join(lines) + suffix


class DatasetQAAgent(BaseAgent):
    """Answers one specific factual/aggregate question about a dataset with a
    single generated SQL query executed directly against the file — the
    lightweight counterpart to the dataset_agent -> insight_agent ->
    visualization_agent chain, which profiles the whole dataset and has an
    LLM reason over that profile even for a question a single query already
    answers exactly. Skips dataset_agent's full outlier/missing-value
    profiling and any chart selection: this path is for a direct answer,
    not an artifact."""

    name = "dataset_qa_agent"

    async def run(self, task: AgentTask, db: AsyncSession) -> AgentResult:
        dataset_id = task.input.get("dataset_id")
        if not dataset_id:
            return self._error(task, "dataset_qa_agent requires 'dataset_id' in input")

        dataset = await db.get(Dataset, uuid.UUID(str(dataset_id)))
        if dataset is None:
            return self._error(task, f"Dataset '{dataset_id}' not found")

        question = task.input.get("question") or task.context.get("prompt", "")
        schema_desc = ", ".join(f"{c['name']} ({c['type']})" for c in dataset.columns)
        model = task.input.get("_model")
        llm = get_llm_for_model(model)

        try:
            raw = await llm.generate(
                [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": f"Dataset columns:\n{schema_desc}\n\nQuestion: {question}",
                    },
                ],
                model=model,
                temperature=0.0,
                max_tokens=SQL_MAX_TOKENS,
            )
            query = _extract_sql(raw)
            columns, rows, row_count = await duckdb_service.execute_widget_query(dataset, query)
        except Exception as exc:  # noqa: BLE001 - a bad query must not abort the pipeline
            logger.warning(f"dataset_qa_agent: query failed | error={exc}")
            return self._error(task, f"Couldn't answer that from '{dataset.name}': {exc}")

        answer = _format_answer(columns, rows)
        return self._success(
            task,
            {"text": answer, "sql": query, "row_count": row_count},
            metadata={"dataset_id": str(dataset.id)},
        )
