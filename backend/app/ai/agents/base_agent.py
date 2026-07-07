from abc import ABC, abstractmethod

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.schemas import AgentResult, AgentTask


class BaseAgent(ABC):
    name: str

    @abstractmethod
    async def run(self, task: AgentTask, db: AsyncSession) -> AgentResult: ...

    def _success(self, task: AgentTask, output: dict, artifact_type: str | None = None, metadata: dict | None = None) -> AgentResult:
        return AgentResult(
            task_id=task.task_id,
            status="success",
            output=output,
            artifact_type=artifact_type,
            metadata={"agent": self.name, **(metadata or {})},
        )

    def _error(self, task: AgentTask, message: str) -> AgentResult:
        return AgentResult(
            task_id=task.task_id,
            status="error",
            output={"error": message},
            metadata={"agent": self.name},
        )
