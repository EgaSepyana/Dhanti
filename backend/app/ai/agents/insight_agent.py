import json
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.agents.base_agent import BaseAgent
from app.ai.schemas import AgentResult, AgentTask
from app.models.dataset import Dataset
from app.providers.manager import get_llm_for_model

SYSTEM_PROMPT = """You are a data analyst. Given a dataset's column schema and \
statistical profile, write a concise markdown report with these sections:

## Overview
## Key Trends
## Anomalies
## Recommendations

Be specific and reference actual column names and values from the profile. \
Keep it under 300 words. Do not invent data not present in the profile."""

# ~300 words of markdown; 700 covers that plus heading/formatting overhead
# without requesting far more than this call ever produces.
INSIGHT_MAX_TOKENS = 700


class InsightAgent(BaseAgent):
    """LLM reasoning over a dataset profile. Output: text artifact (patterns, trends, anomalies)."""

    name = "insight_agent"

    async def run(self, task: AgentTask, db: AsyncSession) -> AgentResult:
        dataset_id = task.input.get("dataset_id")
        if not dataset_id:
            return self._error(task, "insight_agent requires 'dataset_id' in input")

        dataset = await db.get(Dataset, uuid.UUID(str(dataset_id)))
        if dataset is None:
            return self._error(task, f"Dataset '{dataset_id}' not found")

        profile_summary = {
            "name": dataset.name,
            "row_count": dataset.row_count,
            "columns": [
                {"name": c["name"], "type": c["type"], "stats": c["stats"]}
                for c in dataset.columns
            ],
            "profile": dataset.profile,
        }

        model = task.input.get("_model")
        llm = get_llm_for_model(model)
        report = await llm.generate(
            [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(profile_summary, default=str)},
            ],
            model=model,
            temperature=0.3,
            max_tokens=INSIGHT_MAX_TOKENS,
        )

        output = {"text": report, "format": "markdown"}
        return self._success(
            task, output, artifact_type="text", metadata={"dataset_id": str(dataset.id)}
        )
