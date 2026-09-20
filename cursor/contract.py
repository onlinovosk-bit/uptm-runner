"""
Cursor execution contract / interface.

Cursor may not be callable from this host. Implementations must fail closed
when not configured. Do NOT fake successful agent runs.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


class CursorNotConfiguredError(RuntimeError):
    """Raised when Cursor is not configured; fail closed."""


@dataclass(frozen=True)
class CursorTask:
    wave_id: int
    stack_id: str
    prompt_ref: str
    max_agents: int = 8
    metadata: dict[str, Any] | None = None


@dataclass(frozen=True)
class CursorHandoff:
    """Handoff artifact when Cursor cannot be invoked in-process."""

    task: CursorTask
    instructions: str
    evidence_skeleton_path: str
    status: str = "HANDOFF_REQUIRED"


@dataclass(frozen=True)
class CursorResult:
    task: CursorTask
    status: str  # COMPLETED | FAILED | HANDOFF_REQUIRED
    evidence_paths: list[str]
    detail: str


class CursorExecutor(ABC):
    """Execution contract for Cursor agents."""

    @abstractmethod
    def is_configured(self) -> bool:
        ...

    @abstractmethod
    def dispatch(self, task: CursorTask) -> CursorResult:
        ...

    @abstractmethod
    def handoff(self, task: CursorTask) -> CursorHandoff:
        ...


class NullCursorExecutor(CursorExecutor):
    """
    Stub that fails closed if used for dispatch without configuration.

    Documented handoff path is available via handoff().
    """

    def is_configured(self) -> bool:
        return False

    def dispatch(self, task: CursorTask) -> CursorResult:
        if not self.is_configured():
            raise CursorNotConfiguredError(
                "Cursor executor not configured on this host. "
                "Use handoff() and document external agent results as evidence. "
                "Refusing to fake a successful Cursor run."
            )
        raise AssertionError("unreachable")

    def handoff(self, task: CursorTask) -> CursorHandoff:
        return CursorHandoff(
            task=task,
            instructions=(
                f"Execute wave {task.wave_id} stack {task.stack_id} "
                f"using prompt {task.prompt_ref}. Return schema-valid evidence "
                f"with probes; agent self-report alone will not pass Runner gates. "
                f"live_trading must remain false. Max agents={task.max_agents}."
            ),
            evidence_skeleton_path=f"evidence/wave{task.wave_id}/handoff_skeleton.json",
            status="HANDOFF_REQUIRED",
        )


def get_executor() -> CursorExecutor:
    """Factory: currently always NullCursorExecutor (no fake integration)."""
    return NullCursorExecutor()
