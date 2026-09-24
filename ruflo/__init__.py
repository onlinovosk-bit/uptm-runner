"""Ruflo adapter boundary package."""

from ruflo.adapter import (
    NullRufloAdapter,
    RufloAdapter,
    RufloUnavailableError,
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
    "SwarmDispatch",
    "SwarmDispatchError",
    "SwarmDispatchResult",
    "SwarmWorkClaim",
    "evidence_skeleton_for_claim",
    "evidence_skeleton_json",
]
