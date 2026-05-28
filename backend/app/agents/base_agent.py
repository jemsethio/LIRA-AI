"""Base class shared by all LIRA-AI agents."""

from __future__ import annotations
from abc import ABC, abstractmethod
from pydantic import BaseModel
from typing import Any, Optional


class AgentOutput(BaseModel):
    agent_name: str
    success: bool
    result: Any
    evidence_trail: list[str]
    assumptions: list[str]
    needs_validation: list[str]
    confidence: str   # low / medium / high
    uncertainty_score: float  # 0=low, 1=high
    is_mock: bool


class BaseAgent(ABC):
    name: str = "BaseAgent"

    def run(self, **kwargs) -> AgentOutput:
        try:
            result = self._execute(**kwargs)
            return AgentOutput(
                agent_name=self.name,
                success=True,
                result=result,
                evidence_trail=self._evidence_trail(),
                assumptions=self._assumptions(),
                needs_validation=self._needs_validation(),
                confidence=self._confidence(),
                uncertainty_score=self._uncertainty(),
                is_mock=kwargs.get("is_mock", False),
            )
        except Exception as exc:
            return AgentOutput(
                agent_name=self.name,
                success=False,
                result={"error": str(exc)},
                evidence_trail=[],
                assumptions=[],
                needs_validation=["Agent execution failed — manual review required"],
                confidence="none",
                uncertainty_score=1.0,
                is_mock=True,
            )

    @abstractmethod
    def _execute(self, **kwargs) -> Any:
        ...

    def _evidence_trail(self) -> list[str]:
        return []

    def _assumptions(self) -> list[str]:
        return []

    def _needs_validation(self) -> list[str]:
        return []

    def _confidence(self) -> str:
        return "medium"

    def _uncertainty(self) -> float:
        return 0.5
