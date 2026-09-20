"""Stop-condition detection. Fail closed / human review on violation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class StopConditionError(RuntimeError):
    """Hard stop; transition to HUMAN_REVIEW_REQUIRED."""


STOP_CONDITIONS = frozenset(
    {
        "live_trading_enablement_attempt",
        "safety_control_weakening",
        "fabricated_market_data",
        "fabricated_pnl",
        "evidence_forgery_detected",
        "gate_bypass_attempt",
        "wave_skip_attempt",
        "unauthorized_pr_merge",
    }
)


@dataclass(frozen=True)
class StopVerdict:
    triggered: bool
    condition: str | None
    detail: str


def check_live_trading(value: Any) -> StopVerdict:
    if value is True:
        return StopVerdict(
            True,
            "live_trading_enablement_attempt",
            "live_trading must remain false",
        )
    return StopVerdict(False, None, "ok")


def check_evidence_for_stops(evidence: dict[str, Any]) -> StopVerdict:
    lt = evidence.get("live_trading")
    if lt is not False:
        return StopVerdict(
            True,
            "live_trading_enablement_attempt",
            f"evidence.live_trading={lt!r} (required false)",
        )
    # Fabricated PnL heuristics: findings claiming fabricated success
    for finding in evidence.get("results", {}).get("findings", []):
        fid = str(finding.get("id", "")).lower()
        if "fabricat" in fid and finding.get("status") == "FIXED":
            # Not automatically stop — leave to adversarial; keep hook
            pass
    if evidence.get("agent_claim", {}).get("verdict") == "PASS":
        probes = evidence.get("probes") or []
        if not probes:
            return StopVerdict(
                True,
                "evidence_forgery_detected",
                "PASS claim with empty probes",
            )
    return StopVerdict(False, None, "ok")


def raise_if_stop(verdict: StopVerdict) -> None:
    if verdict.triggered:
        raise StopConditionError(f"{verdict.condition}: {verdict.detail}")
