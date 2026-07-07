import asyncio
import json
import uuid

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.agents.base_agent import BaseAgent
from app.ai.agents.html_generation_utils import (
    DASHBOARD_HTML_MAX_TOKENS,
    ECHARTS_CDN,
    ensure_echarts_script,
    extract_html,
)
from app.ai.schemas import AgentResult, AgentTask
from app.models.artifact import Artifact
from app.providers.manager import get_llm_for_model
from app.services import widget_service

SYSTEM_PROMPT = f"""You are DHANTI's dashboard editor. You will be given the current dashboard's \
complete HTML document (a self-contained page using the Bridge API for live data — see the \
window.bridge calls already in the code), a list of widgets available in this workspace (id, \
title, type), and a user instruction describing a change.

Apply ONLY the requested change. Do not rewrite, restyle, or restructure anything the \
instruction doesn't ask you to change — preserve every window.bridge call, dataset id, widget, \
and style choice exactly except where the instruction requires a change.

If the instruction asks to add an existing chart/widget to the dashboard (e.g. "add the pie \
chart", "add that visualization"), find the matching widget in the list below by its title/type \
and add a new container calling `await window.bridge.widget.execute("<its real id>")` — the \
SAME contract every other widget on the page already uses. NEVER invent a widget id: reference \
only ids that appear in the widget list. If no widget in the list plausibly matches what the \
instruction describes, say so in your one required output (respond with the HTML unchanged) \
rather than fabricating an id that doesn't exist — a fabricated id fails at render time with \
"Widget not found".

If you add a "chart" widget and <head> lacks an ECharts script tag, add exactly: \
<script src="{ECHARTS_CDN}"></script>

Respond with ONLY the complete updated HTML document, starting with <!DOCTYPE html>. No \
markdown fences, no explanation before or after."""


class DashboardRevisionAgent(BaseAgent):
    """Applies a natural-language revision instruction to an existing
    dashboard's HTML via the LLM, producing a new version (not a new
    artifact) — the code-editing counterpart to code_generation_agent."""

    name = "dashboard_revision_agent"

    async def run(self, task: AgentTask, db: AsyncSession) -> AgentResult:
        dashboard_artifact_id = task.input.get("dashboard_artifact_id")
        instruction = task.input.get("instruction")
        if not dashboard_artifact_id:
            return self._error(task, "dashboard_revision_agent requires 'dashboard_artifact_id'")
        if not instruction:
            return self._error(task, "dashboard_revision_agent requires 'instruction'")

        artifact = await db.get(Artifact, uuid.UUID(str(dashboard_artifact_id)))
        if artifact is None or artifact.type != "dashboard":
            return self._error(task, f"Dashboard artifact '{dashboard_artifact_id}' not found")

        current_html = artifact.content.get("entry", "")
        status_queue: asyncio.Queue | None = task.input.get("_status_queue")

        widgets = await widget_service.list_widgets(db, uuid.UUID(str(task.workspace_id)))
        # Most-recently-created first: when the instruction is vague ("add
        # that chart"), it almost always means whatever was just made.
        widgets_desc = [
            {"id": str(w.id), "title": w.title, "type": w.type}
            for w in reversed(widgets)
        ]

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Current dashboard HTML:\n{current_html}\n\n"
                    f"Available widgets in this workspace:\n{json.dumps(widgets_desc)}\n\n"
                    f"Instruction: {instruction}"
                ),
            },
        ]

        model = task.input.get("_model")
        llm = get_llm_for_model(model)
        try:
            if status_queue is None:
                raw = await llm.generate(
                    messages, model=model, temperature=0.2, max_tokens=DASHBOARD_HTML_MAX_TOKENS
                )
            else:
                # Live path: stream the revised code straight to the client as
                # it's written, same as a fresh generation — a revision is
                # still "the agent writing dashboard code."
                chunks: list[str] = []
                async for chunk in llm.generate_stream(
                    messages, model=model, temperature=0.2, max_tokens=DASHBOARD_HTML_MAX_TOKENS
                ):
                    chunks.append(chunk)
                    await status_queue.put(
                        ("code_delta", {"step_id": task.task_id, "delta": chunk})
                    )
                raw = "".join(chunks)
            updated_html = ensure_echarts_script(extract_html(raw))
        except Exception as exc:  # noqa: BLE001 - never abort the pipeline on an LLM/parsing failure
            logger.warning(f"dashboard_revision_agent: LLM revision failed | error={exc}")
            return self._error(task, f"Failed to generate dashboard revision: {exc}")

        updated_content = {
            "runtime": "html",
            "entry": updated_html,
            "assets": artifact.content.get("assets", []),
            "permissions": artifact.content.get(
                "permissions", {"read": True, "write": False, "execute": True}
            ),
        }

        return AgentResult(
            task_id=task.task_id,
            status="success",
            output=updated_content,
            artifact_type="dashboard",
            target_artifact_id=str(artifact.id),
            metadata={"agent": self.name, "instruction": instruction},
        )
