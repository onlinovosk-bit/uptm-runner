"""
Cursor execution contract / interface.

Cursor may not be callable from this host. Implementations must fail closed
when not configured. Do NOT fake successful agent runs.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from runner.prompt_stacks import load_stacks
from ruflo.adapter import SwarmDispatch


class CursorNotConfiguredError(RuntimeError):
    """Raised when Cursor is not configured; fail closed."""


@dataclass(frozen=True)
class CursorTask:
    wave_id: int
    stack_id: str
    prompt_ref: str
    max_agents: int = 8
    role: str = "executor"
    metadata: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        metadata = dict(self.metadata or {})
        metadata.setdefault("role", self.role)
        metadata.setdefault("least_privilege", True)
        metadata.setdefault("wave_id", self.wave_id)
        metadata.setdefault("stack_id", self.stack_id)
        object.__setattr__(self, "metadata", metadata)


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

    @abstractmethod
    def handoff_swarm(
        self,
        dispatch: SwarmDispatch,
        *,
        branch: str,
        commit_sha: str,
        pr: int | None = None,
        write_root: Path | None = None,
    ) -> tuple[CursorHandoff, ...]:
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
                f"as role {task.role} using prompt {task.prompt_ref}. "
                f"Return schema-valid evidence "
                f"with probes; agent self-report alone will not pass Runner gates. "
                f"live_trading must remain false. Max agents={task.max_agents}."
            ),
            evidence_skeleton_path=f"evidence/wave{task.wave_id}/handoff_skeleton.json",
            status="HANDOFF_REQUIRED",
        )

    def handoff_swarm(
        self,
        dispatch: SwarmDispatch,
        *,
        branch: str,
        commit_sha: str,
        pr: int | None = None,
        write_root: Path | None = None,
    ) -> tuple[CursorHandoff, ...]:
        """Emit one documented handoff per validated swarm claim.

        Uses APS-004 skeletons for path and prompt_stack metadata. This is not
        execution: dispatch() remains fail-closed when Cursor is unconfigured.
        """
        if write_root is not None:
            dispatch.write_evidence_skeletons(
                root=write_root, branch=branch, commit_sha=commit_sha, pr=pr
            )
        skeletons = dispatch.evidence_skeletons(
            branch=branch, commit_sha=commit_sha, pr=pr
        )
        stacks = load_stacks()
        handoffs: list[CursorHandoff] = []
        for claim, skeleton in zip(dispatch.claims, skeletons, strict=True):
            primary_stack = claim.stack_ids[-1]
            prompt_ref = f"prompt-stacks/{stacks[primary_stack].file}"
            task = CursorTask(
                claim.wave_id,
                primary_stack,
                prompt_ref,
                max_agents=dispatch.max_parallel_agents,
                role=claim.role,
                metadata={
                    **skeleton["prompt_stack"],
                    "swarm_claim": dict(skeleton["swarm_claim"]),
                    "skeleton": True,
                    "evidence_skeleton_path": claim.evidence_skeleton_path,
                },
            )
            handoffs.append(
                CursorHandoff(
                    task=task,
                    instructions=(
                        f"Execute wave {claim.wave_id} stacks {list(claim.stack_ids)} "
                        f"as role {claim.role} for agent {claim.agent_id}. "
                        f"Owned paths: {list(skeleton['swarm_claim']['owned_paths'])}. "
                        f"Replace the SKIPPED skeleton at {claim.evidence_skeleton_path} "
                        f"with schema-valid evidence and real probes. "
                        f"The skeleton itself cannot pass a gate. "
                        f"live_trading must remain false. "
                        f"Max agents={dispatch.max_parallel_agents}."
                    ),
                    evidence_skeleton_path=claim.evidence_skeleton_path,
                    status="HANDOFF_REQUIRED",
                )
            )
        return tuple(handoffs)


def get_executor() -> CursorExecutor:
    """Factory: currently always NullCursorExecutor (no fake integration)."""
    return NullCursorExecutor()
