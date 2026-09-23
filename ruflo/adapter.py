"""
Ruflo adapter boundary.

Ruflo may be unavailable. Orchestration must work through Runner FSM alone.
This module defines the adapter interface + a stub that reports unavailable.
Do NOT fake Ruflo connectivity.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


class RufloUnavailableError(RuntimeError):
    """Ruflo not available; callers must use local orchestration."""


class SwarmDispatchError(ValueError):
    """Swarm dispatch contract rejected an unsafe fanout."""


@dataclass(frozen=True)
class OrchestrationEvent:
    kind: str
    payload: dict[str, Any]


@dataclass(frozen=True)
class SwarmWorkClaim:
    agent_id: str
    wave_id: int
    role: str
    stack_ids: tuple[str, ...]
    owned_paths: tuple[str, ...]
    lease_id: str
    lease_expires_at: str
    evidence_skeleton_path: str


@dataclass(frozen=True)
class SwarmDispatch:
    wave_id: int
    claims: tuple[SwarmWorkClaim, ...]
    max_parallel_agents: int = 8
    allow_single_threaded_cursor_handoff: bool = True

    def validate(self) -> None:
        if not self.claims:
            raise SwarmDispatchError("fail-closed: swarm dispatch has no claims")
        if self.max_parallel_agents > 8:
            raise SwarmDispatchError("fail-closed: max_parallel_agents exceeds 8")
        if len(self.claims) > self.max_parallel_agents:
            raise SwarmDispatchError("fail-closed: claim count exceeds max_parallel_agents")

        ownership: dict[str, str] = {}
        for claim in self.claims:
            if claim.wave_id != self.wave_id:
                raise SwarmDispatchError("fail-closed: claim crosses wave boundary")
            if not claim.lease_id or not claim.lease_expires_at:
                raise SwarmDispatchError("fail-closed: work claim lease fields required")
            if not claim.evidence_skeleton_path:
                raise SwarmDispatchError("fail-closed: evidence skeleton path required")
            for path in claim.owned_paths:
                owner = ownership.setdefault(path, claim.agent_id)
                if owner != claim.agent_id:
                    raise SwarmDispatchError(
                        f"fail-closed: ownership conflict for {path!r}"
                    )


@dataclass(frozen=True)
class SwarmDispatchResult:
    dispatch: SwarmDispatch
    status: str
    evidence_skeleton_paths: tuple[str, ...]
    detail: str


class RufloAdapter(ABC):
    @abstractmethod
    def available(self) -> bool:
        ...

    @abstractmethod
    def publish(self, event: OrchestrationEvent) -> None:
        ...

    @abstractmethod
    def subscribe(self, topic: str) -> list[OrchestrationEvent]:
        ...

    @abstractmethod
    def dispatch_swarm(self, dispatch: SwarmDispatch) -> SwarmDispatchResult:
        ...


class NullRufloAdapter(RufloAdapter):
    """Stub: Ruflo unavailable. Local FSM remains source of truth."""

    def available(self) -> bool:
        return False

    def publish(self, event: OrchestrationEvent) -> None:
        raise RufloUnavailableError(
            "Ruflo adapter not configured. Use runner.fsm.RunnerFSM for orchestration. "
            "Refusing to pretend Ruflo accepted the event."
        )

    def subscribe(self, topic: str) -> list[OrchestrationEvent]:
        raise RufloUnavailableError(
            f"Ruflo unavailable; cannot subscribe to {topic!r}. "
            "Use local wave status / evidence collection."
        )

    def dispatch_swarm(self, dispatch: SwarmDispatch) -> SwarmDispatchResult:
        dispatch.validate()
        raise RufloUnavailableError(
            "Ruflo adapter not configured; refusing swarm fanout success. "
            "Use documented single-threaded Cursor handoff if appropriate, and collect "
            "schema-valid evidence skeletons before any gate can pass."
        )


def get_adapter() -> RufloAdapter:
    return NullRufloAdapter()
