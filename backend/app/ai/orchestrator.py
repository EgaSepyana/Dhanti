import uuid
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import (
    artifact_generator,
    context_builder,
    intent_analyzer,
    planning_engine,
    simple_query_engine,
)
from app.ai.agents.base_agent import BaseAgent
from app.ai.agents.code_generation_agent import CodeGenerationAgent
from app.ai.agents.dashboard_agent import DashboardAgent
from app.ai.agents.dashboard_revision_agent import DashboardRevisionAgent
from app.ai.agents.dataset_agent import DatasetAgent
from app.ai.agents.dataset_qa_agent import DatasetQAAgent
from app.ai.agents.document_agent import DocumentAgent
from app.ai.agents.file_agent import FileAgent
from app.ai.agents.insight_agent import InsightAgent
from app.ai.agents.text_to_sql_agent import TextToSQLAgent
from app.ai.agents.visualization_agent import VisualizationAgent
from app.ai.agents.widget_planner_agent import WidgetPlannerAgent
from app.ai.artifact_generator import ArtifactValidationError
from app.ai.execution_router import ExecutionMode, route
from app.ai.schemas import AgentResult, AgentTask, IntentResult, WorkspaceContext
from app.models.dataset import Dataset
from app.services import artifact_service
from app.models.artifact import ArtifactUpdate

AGENT_REGISTRY: dict[str, BaseAgent] = {
    "file_agent": FileAgent(),
    "dataset_agent": DatasetAgent(),
    "document_agent": DocumentAgent(),
    "insight_agent": InsightAgent(),
    "visualization_agent": VisualizationAgent(),
    "widget_planner_agent": WidgetPlannerAgent(),
    "text_to_sql_agent": TextToSQLAgent(),
    "dashboard_agent": DashboardAgent(),
    "dashboard_revision_agent": DashboardRevisionAgent(),
    "code_generation_agent": CodeGenerationAgent(),
    "dataset_qa_agent": DatasetQAAgent(),
}

# Groups the underlying pipeline agents under the two specialist personas the
# UI presents in the "thinking" log: a Data Analyst that profiles data and
# derives findings, and a Dashboard Designer that lays out and codes the
# result. This is presentation-only — it doesn't change agent behavior or
# the plan/registry above — because splitting the tested 5-agent pipeline
# into two literal agent classes would touch planning_engine templates,
# schemas, and every orchestrator test for no behavioral benefit.
AGENT_SPECIALIST: dict[str, str] = {
    "file_agent": "Data Analyst",
    "dataset_agent": "Data Analyst",
    "document_agent": "Data Analyst",
    "insight_agent": "Data Analyst",
    "visualization_agent": "Data Analyst",
    "widget_planner_agent": "Data Analyst",
    "text_to_sql_agent": "Data Analyst",
    "dashboard_agent": "Dashboard Designer",
    "dashboard_revision_agent": "Dashboard Designer",
    "code_generation_agent": "Dashboard Designer",
    "dataset_qa_agent": "Data Analyst",
}

AGENT_LABEL: dict[str, str] = {
    "file_agent": "Locating source file",
    "dataset_agent": "Profiling dataset",
    "document_agent": "Indexing document",
    "insight_agent": "Analyzing patterns & trends",
    "visualization_agent": "Selecting the best chart types",
    "widget_planner_agent": "Deciding which widgets to build",
    "text_to_sql_agent": "Writing widget queries",
    "dashboard_agent": "Planning dashboard layout",
    "dashboard_revision_agent": "Revising dashboard",
    "code_generation_agent": "Writing HTML code",
    "dataset_qa_agent": "Querying the dataset",
}


class OrchestratorState(TypedDict):
    workspace_id: str
    prompt: str
    recent_messages: list[dict]
    db: Any  # AsyncSession; kept out of the TypedDict's serializable surface intentionally
    intent_result: dict | None
    context: dict | None
    plan: list[dict] | None
    step_results: dict[str, dict]
    artifacts: list[dict]
    status_queue: Any  # asyncio.Queue | None; not serialized, used to stream live agent-step status
    model: str | None  # user-picked model override; applies to every LLM call in this run, not just the final summary
    execution_mode: str | None  # ExecutionMode value chosen by the deterministic router
    routed_agent: str | None  # target agent for single_agent/code_generation/simple-query-fallback
    simple_query_resolved: bool | None  # True once execute_simple_query answers with zero LLM calls


async def _node_build_context(state: OrchestratorState) -> dict:
    context = await context_builder.build_context(
        state["db"], state["workspace_id"], state["prompt"], state.get("recent_messages")
    )
    return {"context": context.model_dump()}


async def _node_route(state: OrchestratorState) -> dict:
    context = WorkspaceContext(**state["context"])
    decision = route(state["prompt"], context)
    return {"execution_mode": decision.mode.value, "routed_agent": decision.agent}


async def _node_build_deterministic_plan(state: OrchestratorState) -> dict:
    """Builds a single-step plan without any LLM call, for SINGLE_AGENT,
    CODE_GENERATION, and the SIMPLE_QUERY fallback (dataset_qa_agent) —
    reusing planning_engine's own reference-resolution helpers so a missing
    dataset/document/dashboard degrades exactly like the LLM-planned path
    already does (an empty step_input the target agent's own validation
    reports as a graceful per-step error, not a pipeline abort)."""
    context = WorkspaceContext(**state["context"])
    agent_name = state["routed_agent"]
    _, resolved_dataset, resolved_document = planning_engine._resolve_references(context, [])

    step_input: dict = {}
    intent = "data_analysis"
    if agent_name == "dashboard_revision_agent":
        intent = "dashboard_revision"
        resolved_dashboard = planning_engine._resolve_dashboard_artifact(context, [])
        if resolved_dashboard:
            step_input = {"dashboard_artifact_id": resolved_dashboard["id"], "instruction": context.prompt}
    elif agent_name == "document_agent":
        intent = "summarize"
        if resolved_document:
            step_input = {"document_id": resolved_document["id"]}
    elif agent_name == "insight_agent":
        intent = "data_analysis"
        if resolved_dataset:
            step_input = {"dataset_id": resolved_dataset["id"]}
    elif agent_name == "dataset_qa_agent":
        intent = "dataset_qa"
        if resolved_dataset:
            step_input = {"dataset_id": resolved_dataset["id"], "question": context.prompt}

    plan = [
        {
            "step_id": "s1",
            "agent": agent_name,
            "input": step_input,
            "depends_on": [],
            "expected_output": f"{agent_name} output",
        }
    ]
    intent_result = {
        "intent": intent,
        "complexity": "simple",
        "required_agents": [agent_name],
        "required_data": [],
    }
    return {"plan": plan, "intent_result": intent_result}


async def _node_execute_simple_query(state: OrchestratorState) -> dict:
    """Tries to answer with zero LLM calls via simple_query_engine's
    keyword/regex-parsed SQL. Falls back to dataset_qa_agent (routed through
    the same deterministic-plan builder, still skipping intent+planning
    LLM calls) when the question can't be confidently parsed — never a
    wrong guess, just a graceful step down to the next-cheapest tier."""
    context = WorkspaceContext(**state["context"])
    db: AsyncSession = state["db"]
    _, resolved_dataset, _ = planning_engine._resolve_references(context, [])

    dataset = await db.get(Dataset, uuid.UUID(resolved_dataset["id"])) if resolved_dataset else None
    result = await simple_query_engine.try_execute(state["prompt"], dataset) if dataset else None

    if result is None:
        return {"simple_query_resolved": False, "routed_agent": "dataset_qa_agent"}

    plan = [
        {
            "step_id": "s1",
            "agent": "simple_query_engine",
            "input": {},
            "depends_on": [],
            "expected_output": "simple query answer",
        }
    ]
    intent_result = {
        "intent": "dataset_qa",
        "complexity": "simple",
        "required_agents": [],
        "required_data": [],
    }
    return {
        "simple_query_resolved": True,
        "plan": plan,
        "intent_result": intent_result,
        "step_results": {
            "s1": {
                "task_id": "s1",
                "status": "success",
                "output": {"text": result.answer, "sql": result.sql},
                "artifact_type": None,
                "metadata": {"engine": "simple_query_engine"},
                "target_artifact_id": None,
            }
        },
        "artifacts": [],
    }


async def _node_analyze_intent(state: OrchestratorState) -> dict:
    context = WorkspaceContext(**state["context"])
    summary = context_builder.summarize_context(context)
    intent_result = await intent_analyzer.analyze_intent(state["prompt"], summary, state.get("model"))
    return {"intent_result": intent_result.model_dump()}


async def _node_plan(state: OrchestratorState) -> dict:
    intent_result = IntentResult(**state["intent_result"])
    context = WorkspaceContext(**state["context"])
    plan = await planning_engine.build_plan(intent_result, context, state.get("model"))
    return {"plan": [step.model_dump() for step in plan.steps]}


async def _emit_agent_step(state: OrchestratorState, step: dict, status: str) -> None:
    queue = state.get("status_queue")
    if queue is None:
        return
    agent_name = step["agent"]
    await queue.put((
        "agent_step",
        {
            "step_id": step["step_id"],
            "agent": agent_name,
            "specialist": AGENT_SPECIALIST.get(agent_name, "Assistant"),
            "label": AGENT_LABEL.get(agent_name, agent_name),
            "status": status,
        },
    ))


async def _node_execute_agents(state: OrchestratorState) -> dict:
    db: AsyncSession = state["db"]
    step_results: dict[str, dict] = {}
    artifacts: list[dict] = []
    dependencies_by_agent: dict[str, dict] = {}
    artifact_ids_so_far: list[dict] = []

    for step in state["plan"]:
        agent = AGENT_REGISTRY.get(step["agent"])
        if agent is None:
            step_results[step["step_id"]] = {
                "status": "error",
                "output": {"error": f"Unknown agent '{step['agent']}'"},
            }
            continue

        await _emit_agent_step(state, step, "running")

        step_input = {
            **step["input"],
            "_dependencies": dict(dependencies_by_agent),
            # Lets an agent stream incremental progress (e.g. code being
            # written) straight to the client via the same queue/sentinel
            # mechanism chat_service.py already drains into SSE events.
            "_status_queue": state.get("status_queue"),
            # The user's model override applies to every agent's LLM calls,
            # not just the final chat summary — otherwise picking a model
            # only relabels the trailing text while the actual dashboard
            # generation silently used whatever the default provider is.
            "_model": state.get("model"),
        }
        task = AgentTask(
            task_id=step["step_id"],
            workspace_id=state["workspace_id"],
            input=step_input,
            context=state["context"] or {},
        )

        try:
            result = await agent.run(task, db)
        except Exception as exc:  # noqa: BLE001 - agent failures must not abort the pipeline
            logger.exception(f"Agent '{step['agent']}' (step={step['step_id']}) failed")
            result = AgentResult(
                task_id=step["step_id"],
                status="error",
                output={"error": str(exc)},
                metadata={"agent": step["agent"]},
            )

        step_results[step["step_id"]] = result.model_dump()
        await _emit_agent_step(state, step, result.status)

        if result.status == "success":
            dependencies_by_agent[step["agent"]] = result.output

        if result.status == "success" and result.artifact_type and result.target_artifact_id:
            try:
                existing = await artifact_service.get_artifact(
                    db, uuid.UUID(result.target_artifact_id)
                )
                if existing is None:
                    raise ArtifactValidationError(
                        f"Target artifact '{result.target_artifact_id}' not found"
                    )
                artifact = await artifact_service.update_artifact(
                    db, existing, ArtifactUpdate(content=result.output)
                )
                artifacts.append(
                    {
                        "id": str(artifact.id),
                        "type": artifact.type,
                        "title": artifact.title,
                        "version": artifact.version,
                    }
                )
                artifact_ids_so_far.append({"type": "derived", "target_id": str(artifact.id)})
            except ArtifactValidationError as exc:
                step_results[step["step_id"]]["status"] = "partial"
                step_results[step["step_id"]]["output"]["artifact_error"] = str(exc)
        elif result.status == "success" and result.artifact_type:
            try:
                artifact = await artifact_generator.generate_artifact(
                    db,
                    state["workspace_id"],
                    result.artifact_type,
                    title=f"{step['agent']} — {step.get('expected_output', '')}".strip(" —"),
                    content=result.output,
                    metadata=result.metadata,
                    # Derived from every artifact this pipeline run has produced so
                    # far, e.g. a dashboard's relations trace back through its
                    # visualization to the dataset it was built from.
                    relations=list(artifact_ids_so_far),
                )
                artifacts.append(
                    {
                        "id": str(artifact.id),
                        "type": artifact.type,
                        "title": artifact.title,
                        "version": artifact.version,
                    }
                )
                artifact_ids_so_far.append({"type": "derived", "target_id": str(artifact.id)})
            except ArtifactValidationError as exc:
                step_results[step["step_id"]]["status"] = "partial"
                step_results[step["step_id"]]["output"]["artifact_error"] = str(exc)

    return {"step_results": step_results, "artifacts": artifacts}


def _select_branch(state: OrchestratorState) -> str:
    return state["execution_mode"]


def _select_after_simple_query(state: OrchestratorState) -> str:
    return "done" if state.get("simple_query_resolved") else "build_deterministic_plan"


def _build_graph():
    graph = StateGraph(OrchestratorState)
    graph.add_node("build_context", _node_build_context)
    graph.add_node("route", _node_route)
    graph.add_node("analyze_intent", _node_analyze_intent)
    graph.add_node("plan", _node_plan)
    graph.add_node("build_deterministic_plan", _node_build_deterministic_plan)
    graph.add_node("execute_simple_query", _node_execute_simple_query)
    graph.add_node("execute_agents", _node_execute_agents)

    graph.add_edge(START, "build_context")
    graph.add_edge("build_context", "route")
    # Execution Router branches here: SIMPLE_QUERY tries a zero-LLM answer,
    # SINGLE_AGENT/CODE_GENERATION build a one-step plan with no LLM call,
    # and only MULTI_AGENT reaches the LLM-driven intent+planning stages —
    # the existing full pipeline, completely unchanged below this branch.
    graph.add_conditional_edges(
        "route",
        _select_branch,
        {
            ExecutionMode.MULTI_AGENT.value: "analyze_intent",
            ExecutionMode.SINGLE_AGENT.value: "build_deterministic_plan",
            ExecutionMode.CODE_GENERATION.value: "build_deterministic_plan",
            ExecutionMode.SIMPLE_QUERY.value: "execute_simple_query",
        },
    )
    graph.add_edge("analyze_intent", "plan")
    graph.add_edge("plan", "execute_agents")
    graph.add_edge("build_deterministic_plan", "execute_agents")
    graph.add_conditional_edges(
        "execute_simple_query",
        _select_after_simple_query,
        {"done": END, "build_deterministic_plan": "build_deterministic_plan"},
    )
    graph.add_edge("execute_agents", END)

    return graph.compile()


_compiled_graph = None


def get_orchestrator():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = _build_graph()
    return _compiled_graph


def initial_state(
    db: AsyncSession,
    workspace_id: uuid.UUID | str,
    prompt: str,
    recent_messages: list[dict] | None = None,
    status_queue: Any = None,
    model: str | None = None,
) -> OrchestratorState:
    return {
        "workspace_id": str(workspace_id),
        "prompt": prompt,
        "recent_messages": recent_messages or [],
        "db": db,
        "intent_result": None,
        "context": None,
        "plan": None,
        "step_results": {},
        "artifacts": [],
        "status_queue": status_queue,
        "model": model,
        "execution_mode": None,
        "routed_agent": None,
        "simple_query_resolved": None,
    }


async def run_orchestrator(
    db: AsyncSession,
    workspace_id: uuid.UUID | str,
    prompt: str,
    recent_messages: list[dict] | None = None,
    model: str | None = None,
) -> dict:
    graph = get_orchestrator()
    return await graph.ainvoke(initial_state(db, workspace_id, prompt, recent_messages, model=model))
