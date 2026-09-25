"""Ruflo adapter boundary package."""

from ruflo.adapter import (
    NullRufloAdapter,
    RufloAdapter,
    RufloUnavailableError,
    SwarmCollectResult,
    SwarmDispatch,
    SwarmDispatchError,
    SwarmDispatchResult,
    SwarmWorkClaim,
    evidence_skeleton_for_claim,
    evidence_skeleton_json,
)

__all__ = [
    "RufloAdapter",
    "RufloUnavailableError",
    "NullRufloAdapter",
    "SwarmCollectResult",
    "SwarmDispatch",
    "SwarmDispatchError",
    "SwarmDispatchResult",
    "SwarmWorkClaim",
    "evidence_skeleton_for_claim",
    "evidence_skeleton_json",
]
