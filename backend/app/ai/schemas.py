from typing import Literal

from pydantic import BaseModel, Field

Intent = Literal[
    "data_analysis",
    "document_analysis",
    "dashboard_generation",
    "dashboard_revision",
    "code_generation",
    "question_answer",
    "dataset_qa",
    "summarize",
    "compare",
]

AgentName = Literal[
    "file_agent",
    "dataset_agent",
    "document_agent",
    "insight_agent",
    "visualization_agent",
    "widget_planner_agent",
    "text_to_sql_agent",
    "dashboard_agent",
    "dashboard_revision_agent",
    "code_generation_agent",
    "dataset_qa_agent",
]

AGENT_NAMES: list[str] = [
    "file_agent",
    "dataset_agent",
    "document_agent",
    "insight_agent",
    "visualization_agent",
    "widget_planner_agent",
    "text_to_sql_agent",
    "dashboard_agent",
    "dashboard_revision_agent",
    "code_generation_agent",
    "dataset_qa_agent",
]

INTENTS: list[str] = [
    "data_analysis",
    "document_analysis",
    "dashboard_generation",
    "dashboard_revision",
    "code_generation",
    "question_answer",
    "dataset_qa",
    "summarize",
    "compare",
]


class IntentResult(BaseModel):
    intent: Intent
    complexity: Literal["simple", "medium", "complex"] = "simple"
    required_agents: list[AgentName] = Field(default_factory=list)
    required_data: list[str] = Field(default_factory=list)


class WorkspaceContext(BaseModel):
    workspace_id: str
    prompt: str
    recent_messages: list[dict] = Field(default_factory=list)
    files: list[dict] = Field(default_factory=list)
    datasets: list[dict] = Field(default_factory=list)
    documents: list[dict] = Field(default_factory=list)
    artifacts: list[dict] = Field(default_factory=list)
    relevant_chunks: list[dict] = Field(default_factory=list)
    relevant_memories: list[dict] = Field(default_factory=list)


class PlanStep(BaseModel):
    step_id: str
    agent: AgentName
    input: dict = Field(default_factory=dict)
    depends_on: list[str] = Field(default_factory=list)
    expected_output: str = ""


class ExecutionPlan(BaseModel):
    steps: list[PlanStep]


class AgentTask(BaseModel):
    task_id: str
    workspace_id: str
    input: dict = Field(default_factory=dict)
    context: dict = Field(default_factory=dict)
    constraints: dict = Field(default_factory=dict)
    expected_output: dict = Field(default_factory=dict)


class AgentResult(BaseModel):
    task_id: str
    status: Literal["success", "partial", "error"]
    output: dict = Field(default_factory=dict)
    artifact_type: str | None = None
    metadata: dict = Field(default_factory=dict)
    # When set, the orchestrator creates a new *version* of this existing
    # artifact (artifact_service.update_artifact) instead of a brand new one.
    target_artifact_id: str | None = None
