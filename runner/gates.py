"""Wave gate evaluation. Fail closed. Agent self-report alone never passes."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from runner.binding import binding_errors
from runner.evidence import (
    EvidenceError,
    count_findings,
    load_evidence,
    validate_evidence_structure,
)
from runner.detectors.fabrication import (
    CheckOutcome,
    detect_fabricated_market_data,
    detect_fabricated_pnl,
    worst,
    worst_verdict,
)
from runner.detectors.kill_switch import (
    detect_kill_switch,
    detect_kill_switch_drill,
    stop_is_engaged,
)
from runner.detectors.scope import detect_scope
from runner.detectors.validation_capital import (
    detect_return_as_criterion,
    detect_validation_capital,
)
from runner.paths import CAPITAL_RULES, RULES
from runner.stops import StopConditionError, check_evidence_for_stops, raise_if_stop
from runner.verdict import Decision, Verdict, resolve


@dataclass
class GateResult:
    """Outcome of a gate evaluation.

    ``verdict`` is the canonical state; ``passed`` and ``decision`` are derived
    from it, so the two can never disagree. Nothing assigns ``passed``
    directly — a gate that both "passed" and returned UNKNOWN would be a
    governance bug by construction.
    """

    verdict: Verdict
    reasons: list[str] = field(default_factory=list)
    critical: int = 0
    high: int = 0
    evidence_path: str | None = None

    @property
    def passed(self) -> bool:
        """Backwards-compatible boolean view. Derived, never stored."""
        return self.verdict is Verdict.PASS

    @property
    def decision(self) -> Decision:
        """Resolution through the one canonical path."""
        return resolve(self.verdict)


def load_rules() -> dict[str, Any]:
    return json.loads(RULES.read_text(encoding="utf-8"))


def run_fabrication_detectors(
    evidence: dict[str, Any], evidence_path: Path | None
) -> tuple[Verdict, list[str]]:
    """Invoke the UPTM-002 detectors from the gate path (UPTM-002c wiring).

    Wiring only: the detectors decide nothing. They return verdicts, this
    function folds them, and resolution stays with runner.verdict.resolve.

    Packs are evaluated only when the evidence carries them. Evidence that
    declares no market data and no PnL is left exactly as the gate treated it
    before — see the recorded limit on omission in constitution/capital-rules.json.
    """
    reasons: list[str] = []
    verdicts: list[Verdict] = []

    calendars = {k: set(v) for k, v in (evidence.get("calendars") or {}).items()}
    default_root = evidence_path.parent if evidence_path else Path(".")

    md = evidence.get("market_data")
    if md is not None:
        root = Path(md.get("snapshot_root") or default_root)
        outcomes = detect_fabricated_market_data(
            md, snapshot_root=root, calendars=calendars
        )
        verdict = worst(outcomes)
        verdicts.append(verdict)
        for o in outcomes:
            if o.verdict is not Verdict.PASS:
                label = "fabricated_market_data" if o.stop_condition_raised else "unverifiable"
                reasons.append(f"{label}: {o.check_id} {o.verdict.value} — {o.detail}")

    pl = evidence.get("pnl")
    if pl is not None:
        outcomes = detect_fabricated_pnl(pl)
        verdict = worst(outcomes)
        verdicts.append(verdict)
        for o in outcomes:
            if o.verdict is not Verdict.PASS:
                label = "fabricated_pnl" if o.stop_condition_raised else "unverifiable"
                reasons.append(f"{label}: {o.check_id} {o.verdict.value} — {o.detail}")

    return (worst_verdict(verdicts) if verdicts else Verdict.PASS), reasons


def load_capital_rules() -> dict[str, Any]:
    return json.loads(CAPITAL_RULES.read_text(encoding="utf-8"))


def run_kill_switch_detectors(evidence: dict[str, Any]) -> tuple[Verdict, list[str]]:
    """Invoke the UPTM-003 detectors from the gate path.

    Wiring only: the detectors decide nothing. They return verdicts, this
    function folds them, and resolution stays with runner.verdict.resolve.

    The pack is evaluated only when the evidence carries it. Evidence that
    declares no kill switch is left exactly as the gate treated it before — see
    the recorded limit on omission in constitution/capital-rules.json.
    """
    pack = evidence.get("kill_switch")
    if pack is None:
        return Verdict.PASS, []

    reasons: list[str] = []
    outcomes = detect_kill_switch(pack)

    drill = evidence.get("kill_switch_drill")
    if drill is None:
        outcomes.append(
            CheckOutcome(
                "KS-D0",
                Verdict.UNKNOWN,
                "undeclared preregistered parameter(s): kill_switch_drill — "
                "an untested kill switch does not exist",
            )
        )
    else:
        try:
            cadence = load_capital_rules()["live_capability"]["kill_switch_drill_cadence_days"]
        except (OSError, json.JSONDecodeError, KeyError):
            cadence = None
        outcomes.extend(detect_kill_switch_drill(drill, pack.get("stop_state") or {}, cadence))

    for o in outcomes:
        if o.verdict is not Verdict.PASS:
            label = "kill_switch" if o.stop_condition_raised else "unverifiable"
            reasons.append(f"{label}: {o.check_id} {o.verdict.value} — {o.detail}")

    return worst(outcomes), reasons


def wave_exit_criteria(evidence: dict[str, Any]) -> list[Any]:
    """The gate's preregistered criteria, read from where they actually live.

    waves/wave{N}.yaml carries exit_criteria (P4: fixed before execution).
    Evidence may declare additional criteria for a gate that has none there.
    """
    criteria: list[Any] = list(evidence.get("gate_criteria") or [])
    wave_id = evidence.get("wave_id")
    if isinstance(wave_id, int) and not isinstance(wave_id, bool):
        try:
            from runner.fsm import load_wave

            criteria.extend(load_wave(wave_id).get("exit_criteria") or [])
        except (OSError, ValueError, KeyError):
            pass
    return criteria


def run_validation_capital_detectors(evidence: dict[str, Any]) -> tuple[Verdict, list[str]]:
    """Invoke the UPTM-004 detectors from the gate path.

    Wiring only: the detectors decide nothing. Evaluated when the evidence
    declares a capital gate or carries a capital pack; a gate that is neither is
    left exactly as the gate treated it before.
    """
    pack = evidence.get("capital")
    if pack is None and evidence.get("capital_gate") is not True:
        return Verdict.PASS, []

    try:
        tranche = load_capital_rules().get("validation_capital") or {}
    except (OSError, json.JSONDecodeError):
        tranche = {}

    outcomes = detect_validation_capital(evidence, pack or {}, tranche)
    outcomes.extend(
        detect_return_as_criterion(
            wave_exit_criteria(evidence), evidence.get("agent_claim") or {}, pack or {}
        )
    )

    reasons = [
        f"{'validation_capital' if o.stop_condition_raised else 'unverifiable'}: "
        f"{o.check_id} {o.verdict.value} — {o.detail}"
        for o in outcomes
        if o.verdict is not Verdict.PASS
    ]
    return worst(outcomes), reasons


def run_scope_detector(evidence: dict[str, Any]) -> tuple[Verdict, list[str]]:
    """Invoke the UPTM-005 detector from the gate path.

    Runs on every gate, unconditionally. That is the point: the two walls it
    serves were steppable around precisely because their detectors ran only when
    the caller handed them something.
    """
    outcomes = detect_scope(evidence)
    reasons = [
        f"{'scope' if o.stop_condition_raised else 'unverifiable'}: "
        f"{o.check_id} {o.verdict.value} — {o.detail}"
        for o in outcomes
        if o.verdict is not Verdict.PASS
    ]
    return worst(outcomes), reasons


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
                Verdict.FAIL,
                [f"fail-closed: cannot load evidence: {exc}"],
                evidence_path=str(evidence_path),
            )

    if evidence is None:
        return GateResult(Verdict.FAIL, ["fail-closed: missing evidence artifact"])

    path_str = str(evidence_path) if evidence_path else evidence.get("evidence_id")

    try:
        raise_if_stop(check_evidence_for_stops(evidence))
    except StopConditionError as exc:
        return GateResult(Verdict.FAIL, [f"stop: {exc}"], evidence_path=path_str)

    structural = validate_evidence_structure(evidence)
    if structural:
        return GateResult(
            Verdict.FAIL,
            [f"fail-closed: {e}" for e in structural],
            evidence_path=path_str,
        )

    # UPTM-008 (P12): the artifact declares which files it came from. Until this
    # check existed the gate never looked, so evidence naming a file that did not
    # exist, with a digest computed from nothing, reached PASS.
    binding = binding_errors(evidence)
    if binding:
        return GateResult(
            Verdict.FAIL,
            [f"fail-closed: {e}" for e in binding],
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

    # Detectors run last, so gate_reasons holds every pre-existing gate reason.
    gate_reasons = list(reasons)
    fabrication_verdict, fabrication_reasons = run_fabrication_detectors(
        evidence, evidence_path
    )
    reasons.extend(fabrication_reasons)

    # FAIL dominates UNKNOWN dominates PASS. Every pre-existing gate reason is a
    # demonstrated violation, so it contributes FAIL; the detectors may contribute
    # UNKNOWN, which denies without asserting a violation and must not be
    # reported as FAIL.
    kill_switch_verdict, kill_switch_reasons = run_kill_switch_detectors(evidence)
    reasons.extend(kill_switch_reasons)

    contributing = [Verdict.FAIL] if gate_reasons else []
    contributing.append(fabrication_verdict)
    contributing.append(kill_switch_verdict)

    capital_verdict, capital_reasons = run_validation_capital_detectors(evidence)
    reasons.extend(capital_reasons)
    contributing.append(capital_verdict)

    scope_verdict, scope_reasons = run_scope_detector(evidence)
    reasons.extend(scope_reasons)
    contributing.append(scope_verdict)

    verdict = worst_verdict(contributing)

    # KS-I3b — the invariant, not the mechanism. KS-I3 is what denies while the
    # stop is engaged; this refuses to emit PASS if some later change to the
    # folding above ever let one through. It can only fire on a governance bug.
    if verdict is Verdict.PASS and stop_is_engaged(evidence.get("kill_switch") or {}):
        verdict = Verdict.FAIL
        reasons.append(
            "gate_bypass_attempt: a PASS verdict was produced while the kill switch reads ENGAGED"
        )

    return GateResult(
        verdict=verdict,
        reasons=reasons or ["gate passed"],
        critical=critical,
        high=high,
        evidence_path=path_str,
    )
