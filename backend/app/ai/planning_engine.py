import json
import re

from loguru import logger

from app.ai.schemas import AGENT_NAMES, ExecutionPlan, IntentResult, PlanStep, WorkspaceContext
from app.providers.manager import get_llm_for_model

FALLBACK_TEMPLATES: dict[str, list[str]] = {
    "data_analysis": ["dataset_agent", "insight_agent", "visualization_agent"],
    "document_analysis": ["document_agent"],
    "summarize": ["document_agent"],
    "dashboard_generation": [
        "file_agent",
        "dataset_agent",
        "insight_agent",
        "visualization_agent",
        "widget_planner_agent",
        "text_to_sql_agent",
        "dashboard_agent",
        "code_generation_agent",
    ],
    "dashboard_revision": ["dashboard_revision_agent"],
    "code_generation": [
        "dataset_agent",
        "widget_planner_agent",
        "text_to_sql_agent",
        "dashboard_agent",
        "code_generation_agent",
    ],
    "question_answer": ["document_agent"],
    "dataset_qa": ["dataset_qa_agent"],
    "compare": ["dataset_agent", "insight_agent"],
}

# Single-purpose operations with exactly one correct agent sequence: skip the
# LLM proposal entirely rather than validate it. The membership+order check
# below can't catch a proposal that pads a one-agent fallback with harmless-
# looking extras (e.g. file_agent, dataset_agent) — for these intents extras
# aren't just wasteful, they change which inputs get resolved and can break
# the single targeted operation the user asked for.
DETERMINISTIC_INTENTS = {"dashboard_revision", "dataset_qa"}

DATASET_CONSUMERS = {
    "dataset_agent",
    "insight_agent",
    "visualization_agent",
    "widget_planner_agent",
    "text_to_sql_agent",
    "dashboard_agent",
    "code_generation_agent",
    "dataset_qa_agent",
}

PLANNING_SYSTEM_PROMPT = f"""You are DHANTI's planning engine. Given an analyzed intent and workspace \
context, output the ordered list of agents needed to fulfill the request.

Valid agent names: {", ".join(AGENT_NAMES)}

Respond with ONLY a JSON array of agent names in execution order, e.g.:
["dataset_agent", "insight_agent"]
No markdown fences, no explanation."""

# Output is just a short JSON array of agent names — see intent_analyzer's
# INTENT_MAX_TOKENS for why this is capped well below the app-wide default.
PLANNING_MAX_TOKENS = 300


def _resolve_by_name(items: list[dict], required_data: list[str], name_key: str = "name") -> dict | None:
    if not items:
        return None
    if required_data:
        for ref in required_data:
            ref_lower = ref.lower()
            for item in items:
                item_name = item[name_key].lower()
                if ref_lower in item_name or item_name in ref_lower:
                    return item
    return items[0]  # most recent, since context lists are ordered created_at desc


def _resolve_references(
    context: WorkspaceContext, required_data: list[str]
) -> tuple[dict | None, dict | None, dict | None]:
    resolved_file = _resolve_by_name(context.files, required_data)

    resolved_dataset = None
    if resolved_file:
        resolved_dataset = next(
            (d for d in context.datasets if d.get("file_id") == resolved_file["id"]), None
        )
    if resolved_dataset is None:
        resolved_dataset = _resolve_by_name(context.datasets, required_data)

    resolved_document = None
    if resolved_file:
        resolved_document = next(
            (d for d in context.documents if d.get("file_id") == resolved_file["id"]), None
        )
    if resolved_document is None:
        resolved_document = _resolve_by_name(context.documents, required_data)

    return resolved_file, resolved_dataset, resolved_document


def _resolve_dashboard_artifact(context: WorkspaceContext, required_data: list[str]) -> dict | None:
    # context.artifacts is ordered created_at desc and includes every version,
    # so the first dashboard-type entry is always the latest version.
    dashboards = [a for a in context.artifacts if a.get("type") == "dashboard"]
    return _resolve_by_name(dashboards, required_data, name_key="title")


async def _propose_agent_sequence(
    intent_result: IntentResult, context: WorkspaceContext, model: str | None = None
) -> list[str]:
    fallback = FALLBACK_TEMPLATES.get(intent_result.intent, ["dataset_agent"])
    if intent_result.intent in DETERMINISTIC_INTENTS:
        return fallback

    proposed = None
    try:
        llm = get_llm_for_model(model)
        raw = await llm.generate(
            [
                {"role": "system", "content": PLANNING_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Intent: {intent_result.model_dump_json()}\n"
                        f"Available data: files={len(context.files)}, "
                        f"datasets={len(context.datasets)}, documents={len(context.documents)}"
                    ),
                },
            ],
            model=model,
            temperature=0.0,
            max_tokens=PLANNING_MAX_TOKENS,
        )
        match = re.search(r"\[.*\]", raw, re.DOTALL)
        if match:
            proposed = json.loads(match.group(0))
    except Exception as exc:  # noqa: BLE001 - never abort the pipeline over a planning hiccup
        logger.warning(f"planning_engine: agent-sequence proposal failed, using fallback template | error={exc}")
        proposed = None

    if not isinstance(proposed, list):
        return fallback

    # dict.fromkeys dedupes while preserving first-occurrence order: an LLM
    # that accidentally repeats an agent (e.g. ["dataset_agent", "insight_agent",
    # "insight_agent", ...]) would otherwise run that agent twice — doubling its
    # artifact and doubling its text in the final summary's findings — since
    # both checks below (set membership, first-index ordering) are blind to
    # extra repeats once the required agents are already present in order.
    valid = list(dict.fromkeys(a for a in proposed if a in AGENT_NAMES))
    # Require the LLM's plan to at least cover the reliable minimum for this intent,
    # in the same relative order — later agents in the fallback depend on earlier
    # ones' output (e.g. code_generation_agent needs dashboard_agent's result), so
    # membership alone isn't enough: a reordered-but-complete plan can still break
    # the dependency chain.
    if not valid or not set(fallback).issubset(set(valid)) or not _preserves_order(valid, fallback):
        return fallback
    return valid


def _preserves_order(proposed: list[str], required: list[str]) -> bool:
    positions = []
    for agent in required:
        try:
            positions.append(proposed.index(agent))
        except ValueError:
            return False
    return positions == sorted(positions)


async def build_plan(
    intent_result: IntentResult, context: WorkspaceContext, model: str | None = None
) -> ExecutionPlan:
    agent_sequence = await _propose_agent_sequence(intent_result, context, model)
    resolved_file, resolved_dataset, resolved_document = _resolve_references(
        context, intent_result.required_data
    )
    resolved_dashboard = _resolve_dashboard_artifact(context, intent_result.required_data)

    steps: list[PlanStep] = []
    prev_id: str | None = None
    for i, agent_name in enumerate(agent_sequence, start=1):
        step_id = f"s{i}"
        step_input: dict = {}

        if agent_name == "file_agent" and resolved_file:
            step_input["file_id"] = resolved_file["id"]
        elif agent_name == "document_agent" and resolved_document:
            step_input["document_id"] = resolved_document["id"]
        elif agent_name == "dashboard_revision_agent" and resolved_dashboard:
            step_input["dashboard_artifact_id"] = resolved_dashboard["id"]
            step_input["instruction"] = context.prompt
        elif agent_name in DATASET_CONSUMERS and resolved_dataset:
            step_input["dataset_id"] = resolved_dataset["id"]

        steps.append(
            PlanStep(
                step_id=step_id,
                agent=agent_name,
                input=step_input,
                depends_on=[prev_id] if prev_id else [],
                expected_output=f"{agent_name} output",
            )
        )
        prev_id = step_id

    return ExecutionPlan(steps=steps)
