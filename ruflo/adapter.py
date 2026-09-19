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


@dataclass(frozen=True)
class OrchestrationEvent:
    kind: str
    payload: dict[str, Any]


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


def get_adapter() -> RufloAdapter:
    return NullRufloAdapter()
