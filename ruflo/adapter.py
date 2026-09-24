"""
Ruflo adapter boundary.

Ruflo may be unavailable. Orchestration must work through Runner FSM alone.
This module defines the adapter interface + a stub that reports unavailable.
Do NOT fake Ruflo connectivity.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from pathlib import PurePosixPath
from typing import Any

from runner.prompt_stacks import PromptStackError, assemble_prompt


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
        if self.max_parallel_agents < 1:
            raise SwarmDispatchError("fail-closed: max_parallel_agents must be positive")
        if self.max_parallel_agents > 8:
            raise SwarmDispatchError("fail-closed: max_parallel_agents exceeds 8")
        if len(self.claims) > self.max_parallel_agents:
            raise SwarmDispatchError("fail-closed: claim count exceeds max_parallel_agents")

        ownership: dict[PurePosixPath, str] = {}
        agent_ids: set[str] = set()
        lease_ids: set[str] = set()
        for claim in self.claims:
            if not claim.agent_id:
                raise SwarmDispatchError("fail-closed: agent_id required")
            if claim.agent_id in agent_ids:
                raise SwarmDispatchError(f"fail-closed: duplicate agent_id {claim.agent_id!r}")
            agent_ids.add(claim.agent_id)
            if claim.wave_id != self.wave_id:
                raise SwarmDispatchError("fail-closed: claim crosses wave boundary")
            if not claim.lease_id:
                raise SwarmDispatchError("fail-closed: work claim lease fields required")
            if claim.lease_id in lease_ids:
                raise SwarmDispatchError(f"fail-closed: duplicate lease_id {claim.lease_id!r}")
            lease_ids.add(claim.lease_id)
            _parse_lease_expiry(claim.lease_expires_at)
            _validate_prompt_envelope(claim)
            _validate_evidence_skeleton_path(claim)
            normalized_paths = _normalize_owned_paths(claim)
            for path in normalized_paths:
                for owned, owner in ownership.items():
                    if _paths_overlap(path, owned) and owner != claim.agent_id:
                        raise SwarmDispatchError(
                            f"fail-closed: ownership conflict for {str(path)!r}"
                        )
                ownership[path] = claim.agent_id


def _parse_relative_path(raw: str, *, field: str) -> PurePosixPath:
    if not raw:
        raise SwarmDispatchError(f"fail-closed: {field} required")
    path = PurePosixPath(raw)
    if path.is_absolute() or any(part in ("", ".", "..") for part in path.parts):
        raise SwarmDispatchError(f"fail-closed: unsafe {field} {raw!r}")
    return path


def _paths_overlap(left: PurePosixPath, right: PurePosixPath) -> bool:
    return left == right or left in right.parents or right in left.parents


def _parse_lease_expiry(raw: str) -> None:
    if not raw:
        raise SwarmDispatchError("fail-closed: work claim lease fields required")
    try:
        datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SwarmDispatchError("fail-closed: lease_expires_at must be ISO-8601") from exc


def _validate_prompt_envelope(claim: SwarmWorkClaim) -> None:
    try:
        assemble_prompt(
            claim.stack_ids,
            claim.role,
            {"wave_id": claim.wave_id, "agent_id": claim.agent_id},
        )
    except PromptStackError as exc:
        raise SwarmDispatchError(str(exc)) from exc


def _validate_evidence_skeleton_path(claim: SwarmWorkClaim) -> None:
    path = _parse_relative_path(claim.evidence_skeleton_path, field="evidence skeleton path")
    expected_prefix = PurePosixPath("evidence") / f"wave{claim.wave_id}"
    if expected_prefix not in (path, *path.parents):
        raise SwarmDispatchError(
            f"fail-closed: evidence skeleton path must live under {expected_prefix}"
        )
    if path.suffix != ".json":
        raise SwarmDispatchError("fail-closed: evidence skeleton path must be json")


def _normalize_owned_paths(claim: SwarmWorkClaim) -> tuple[PurePosixPath, ...]:
    if not claim.owned_paths:
        raise SwarmDispatchError("fail-closed: owned_paths required")
    normalized: list[PurePosixPath] = []
    seen: set[PurePosixPath] = set()
    for raw in claim.owned_paths:
        path = _parse_relative_path(raw, field="owned path")
        if path in seen:
            raise SwarmDispatchError(f"fail-closed: duplicate owned path {str(path)!r}")
        for existing in normalized:
            if _paths_overlap(path, existing):
                raise SwarmDispatchError(
                    f"fail-closed: overlapping owned_paths inside claim for {str(path)!r}"
                )
        seen.add(path)
        normalized.append(path)
    return tuple(normalized)


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
