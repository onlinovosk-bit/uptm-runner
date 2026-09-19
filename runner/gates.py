"""Wave gate evaluation. Fail closed. Agent self-report alone never passes."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from runner.evidence import (
    EvidenceError,
    count_findings,
    load_evidence,
    validate_evidence_structure,
)
from runner.paths import RULES
from runner.stops import StopConditionError, check_evidence_for_stops, raise_if_stop


@dataclass
class GateResult:
    passed: bool
    reasons: list[str] = field(default_factory=list)
    critical: int = 0
    high: int = 0
    evidence_path: str | None = None


def load_rules() -> dict[str, Any]:
    return json.loads(RULES.read_text(encoding="utf-8"))


def evaluate_gate(
    evidence: dict[str, Any] | None,
    *,
    evidence_path: Path | None = None,
    require_probes: bool = True,
) -> GateResult:
    """
    Deterministic gate from evidence artifacts only.

    Agent PASS without probes/results/before-after → FAIL.
    Missing evidence → FAIL (fail closed).
    CRITICAL>0 or HIGH>0 → FAIL.
    """
    rules = load_rules()
    gate_cfg = rules.get("gate", {})
    critical_max = int(gate_cfg.get("critical_max", 0))
    high_max = int(gate_cfg.get("high_max", 0))

    if evidence is None and evidence_path is not None:
        try:
            evidence = load_evidence(evidence_path)
        except (OSError, json.JSONDecodeError, EvidenceError) as exc:
            return GateResult(
                False,
                [f"fail-closed: cannot load evidence: {exc}"],
                evidence_path=str(evidence_path),
            )

    if evidence is None:
        return GateResult(False, ["fail-closed: missing evidence artifact"])

    path_str = str(evidence_path) if evidence_path else evidence.get("evidence_id")

    try:
        raise_if_stop(check_evidence_for_stops(evidence))
    except StopConditionError as exc:
        return GateResult(False, [f"stop: {exc}"], evidence_path=path_str)

    structural = validate_evidence_structure(evidence)
    if structural:
        return GateResult(
            False,
            [f"fail-closed: {e}" for e in structural],
            evidence_path=path_str,
        )

    reasons: list[str] = []

    claim = evidence.get("agent_claim") or {}
    probes = evidence.get("probes") or []
    results = evidence.get("results") or {}
    before = evidence.get("before") or {}
    after = evidence.get("after") or {}

    if gate_cfg.get("reject_agent_self_report_alone", True) and claim.get("verdict") == "PASS":
        if not probes:
            reasons.append("agent PASS rejected: no probes")
        if "findings" not in results:
            reasons.append("agent PASS rejected: no results.findings")
        if not before.get("digest") or not after.get("digest"):
            reasons.append("agent PASS rejected: missing before/after digests")

    if require_probes and (not probes or all(p.get("outcome") == "SKIPPED" for p in probes)):
        reasons.append("fail-closed: probes missing or all SKIPPED")

    for finding in results.get("findings", []):
        if finding.get("hidden_as") and finding.get("true_severity"):
            reasons.append(
                f"adversarial: finding {finding.get('id')} "
                f"true_severity={finding.get('true_severity')} "
                f"hidden_as={finding.get('hidden_as')}"
            )
        fid = str(finding.get("id", ""))
        sev = str(finding.get("severity", "")).upper()
        if fid.startswith("V-CRIT") and sev not in ("CRITICAL",):
            reasons.append(f"adversarial: {fid} severity downgraded to {sev}")
        if fid.startswith("V-HIGH") and sev not in ("HIGH", "CRITICAL"):
            reasons.append(f"adversarial: {fid} severity downgraded to {sev}")

    counts = count_findings(evidence)
    critical = counts.get("CRITICAL", 0)
    high = counts.get("HIGH", 0)

    if critical > critical_max:
        reasons.append(f"CRITICAL={critical} exceeds max {critical_max}")
    if high > high_max:
        reasons.append(f"HIGH={high} exceeds max {high_max}")

    passed = len(reasons) == 0
    return GateResult(
        passed=passed,
        reasons=reasons or ["gate passed"],
        critical=critical,
        high=high,
        evidence_path=path_str,
    )
