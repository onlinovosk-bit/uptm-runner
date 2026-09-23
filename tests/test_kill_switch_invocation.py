"""UPTM-003 — proof that the runtime path invokes the kill-switch detector.

`import kill_switch` proves nothing, and neither does a green detector suite.
These tests prove that a real `evaluate_gate` call reaches the detector, and
that the gate's verdict *depends on what it returns* — disconnect it and the
outcome changes.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from runner import gates
from runner.detectors import CheckOutcome
from runner.detectors.kill_switch import DISENGAGED, ENGAGED
from runner.gates import evaluate_gate
from runner.paths import CAPITAL_RULES
from runner.verdict import Decision, Verdict, resolve


@pytest.fixture
def ks_pack(tmp_path):
    root = tmp_path / "ks"
    root.mkdir()
    (root / "stop_state").write_text(DISENGAGED, encoding="utf-8")
    env = {
        "deployment_ref": "dep-1",
        "credentials_ref": "cred-1",
        "kill_switch_path_digest": "ks-digest-1",
        "gate_path_digest": "gate-digest-1",
        "changed_at_utc": "2026-09-01T00:00:00Z",
    }
    return {
        "stop_state_ref": "stop_state",
        "stop_state_root": str(root),
        "stop_state_read_via": "file:read_only",
        "declared_states": [ENGAGED, DISENGAGED],
        "runner_write_paths": [],
        "evaluated_at_utc": "2026-09-22T12:00:00Z",
        "drill": {
            "completed_at_utc": "2026-09-15T09:00:00Z",
            "result": "PASS",
            "before_state": DISENGAGED,
            "after_state": ENGAGED,
            "restored_state": DISENGAGED,
            "environment": dict(env),
        },
        "current_environment": dict(env),
        "operator_attestation": {
            "by": "founder",
            "at_utc": "2026-09-10T00:00:00Z",
            "statement": "kill switch runs outside the runner host on separate credentials",
        },
    }


@pytest.fixture
def evidence(valid_evidence_factory, ks_pack):
    return valid_evidence_factory(kill_switch=ks_pack, live_capability_claim=True)


def engage(evidence):
    pack = evidence["kill_switch"]
    (Path(pack["stop_state_root"]) / pack["stop_state_ref"]).write_text(
        ENGAGED, encoding="utf-8"
    )


# ---------------------------------------------------- the path is reachable


def test_a_complete_kill_switch_pack_passes_through_the_gate(evidence):
    result = evaluate_gate(evidence)
    assert result.verdict is Verdict.PASS, result.reasons


def test_gate_fails_and_names_the_stop_condition(evidence):
    ev = copy.deepcopy(evidence)
    ev["kill_switch"]["runner_write_paths"] = ["/var/uptm/stop_state"]
    result = evaluate_gate(ev)
    assert result.verdict is Verdict.FAIL
    assert any("gate_bypass_attempt: KS-S3" in r for r in result.reasons), result.reasons
    assert result.decision is Decision.DENY


def test_a_forged_drill_verdict_is_named_evidence_forgery(evidence):
    ev = copy.deepcopy(evidence)
    ev["kill_switch"]["drill"].pop("before_state")
    ev["kill_switch"]["drill"].pop("after_state")
    result = evaluate_gate(ev)
    assert result.verdict is Verdict.FAIL
    assert any("evidence_forgery_detected: KS-D5" in r for r in result.reasons), result.reasons


def test_a_withheld_parameter_denies_without_accusing(evidence):
    ev = copy.deepcopy(evidence)
    ev["kill_switch"].pop("declared_states")
    result = evaluate_gate(ev)
    assert result.verdict is Verdict.UNKNOWN, result.reasons
    assert resolve(result.verdict) is Decision.DENY
    assert result.passed is False
    assert not any("gate_bypass_attempt" in r for r in result.reasons)
    assert any("unverifiable: KS-S1" in r for r in result.reasons), result.reasons


# ------------------------------------------------------------------- KS-G1


def test_engaged_stop_state_with_an_otherwise_passing_gate_is_a_bypass_attempt(evidence):
    """The whole point of P8: a gate cannot answer PASS while the system is stopped."""
    assert evaluate_gate(evidence).verdict is Verdict.PASS  # baseline, disengaged
    engage(evidence)
    result = evaluate_gate(evidence)
    assert result.verdict is Verdict.FAIL
    assert any("gate_bypass_attempt: KS-G1" in r for r in result.reasons), result.reasons
    assert result.decision is Decision.DENY


def test_engaged_while_the_gate_already_denies_asserts_no_bypass(evidence):
    ev = copy.deepcopy(evidence)
    ev["results"] = {
        "passed": 0,
        "failed": 1,
        "findings": [{"id": "V-CRIT-X", "severity": "CRITICAL", "status": "OPEN"}],
    }
    engage(ev)
    result = evaluate_gate(ev)
    assert result.verdict is Verdict.FAIL
    assert not any("KS-G1 FAIL" in r for r in result.reasons), result.reasons
    assert any("KS-G1 PASS" in r for r in result.reasons), result.reasons


def test_an_indeterminate_stop_state_never_reads_as_disengaged(evidence):
    ev = copy.deepcopy(evidence)
    pack = ev["kill_switch"]
    (Path(pack["stop_state_root"]) / pack["stop_state_ref"]).write_text("MAYBE", encoding="utf-8")
    result = evaluate_gate(ev)
    assert result.verdict is Verdict.FAIL
    assert result.decision is Decision.DENY


# -------------------------------------------------------------- omission


def test_a_live_claim_without_a_pack_is_unknown_not_pass(valid_evidence_factory):
    """On the one path P8 protects, omission does not buy silence."""
    result = evaluate_gate(valid_evidence_factory(live_capability_claim=True))
    assert result.verdict is Verdict.UNKNOWN, result.reasons
    assert any("no kill_switch pack" in r for r in result.reasons), result.reasons


def test_evidence_without_a_pack_or_a_live_claim_never_reaches_the_detector(
    valid_evidence_factory, monkeypatch
):
    """The recorded limit omission_bypass_outside_live_claim, asserted as written."""

    def explode(*args, **kwargs):  # pragma: no cover - must never run
        raise AssertionError("kill-switch detector invoked for evidence with no pack")

    monkeypatch.setattr(gates, "detect_kill_switch", explode)
    assert evaluate_gate(valid_evidence_factory()).verdict is Verdict.PASS


# -------------------------------------- proof of reachability (spy + disconnect)


def test_gate_actually_calls_the_kill_switch_detector(evidence, monkeypatch):
    calls: list[dict] = []

    def spy(pack, *, stop_state_root, cadence_days, reader=None):
        calls.append({"pack": pack, "cadence_days": cadence_days})
        return [CheckOutcome("KS-S3", Verdict.FAIL, "forced by spy")]

    monkeypatch.setattr(gates, "detect_kill_switch", spy)
    result = evaluate_gate(evidence)

    assert len(calls) == 1, "the gate did not invoke the kill-switch detector"
    assert calls[0]["pack"]["stop_state_ref"] == "stop_state"
    assert result.verdict is Verdict.FAIL
    assert any("forced by spy" in r for r in result.reasons)


def test_the_gate_passes_the_preregistered_cadence_to_the_detector(evidence, monkeypatch):
    """The cadence is read from the governance artifact, not from a constant in code."""
    seen: list[object] = []

    def spy(pack, *, stop_state_root, cadence_days, reader=None):
        seen.append(cadence_days)
        return [CheckOutcome("KS-D1", Verdict.PASS, "stub")]

    monkeypatch.setattr(gates, "detect_kill_switch", spy)
    evaluate_gate(evidence)

    declared = json.loads(CAPITAL_RULES.read_text(encoding="utf-8"))["live_capability"][
        "kill_switch_drill_cadence_days"
    ]
    assert seen == [declared]


def test_gate_verdict_depends_on_what_the_detector_returns(evidence, monkeypatch):
    """Disconnect the detector's judgement and the gate's outcome must change."""
    broken = copy.deepcopy(evidence)
    broken["kill_switch"]["runner_write_paths"] = ["/var/uptm/stop_state"]
    assert evaluate_gate(broken).verdict is Verdict.FAIL

    monkeypatch.setattr(
        gates,
        "detect_kill_switch",
        lambda pack, **kw: [CheckOutcome("KS-S3", Verdict.PASS, "stub")],
    )
    assert evaluate_gate(broken).verdict is Verdict.PASS, (
        "the gate's verdict did not follow the detector — it is computing this elsewhere"
    )


#: Every must_fail mutation that the detector owns, as a gate-level mutation.
#: KS-G1 is excluded: it is the gate's own check, and has its own removal test.
DETECTOR_MUTATIONS = {
    "MUT-01": lambda ev: _write_state(ev, "MAYBE"),
    "MUT-02": lambda ev: _unlink_state(ev),
    "MUT-04": lambda ev: ev["kill_switch"].update(runner_write_paths=["/var/uptm/stop"]),
    "MUT-05": lambda ev: ev["kill_switch"]["drill"].update(completed_at_utc="2026-09-07T12:00:00Z"),
    "MUT-06": lambda ev: ev["kill_switch"]["drill"].update(after_state=DISENGAGED),
    "MUT-07": lambda ev: [ev["kill_switch"]["drill"].pop("before_state"),
                          ev["kill_switch"]["drill"].pop("after_state")],
    "MUT-08": lambda ev: ev["kill_switch"]["current_environment"].update(deployment_ref="changed"),
    "MUT-09": lambda ev: ev["kill_switch"]["current_environment"].update(credentials_ref="changed"),
    "MUT-10": lambda ev: ev["kill_switch"]["current_environment"].update(kill_switch_path_digest="changed"),
    "MUT-11": lambda ev: ev["kill_switch"]["current_environment"].update(gate_path_digest="changed"),
    "MUT-12": lambda ev: ev["kill_switch"]["current_environment"].update(changed_at_utc="2026-09-20T00:00:00Z"),
}


def _state_path(ev) -> Path:
    pack = ev["kill_switch"]
    return Path(pack["stop_state_root"]) / pack["stop_state_ref"]


def _write_state(ev, value: str) -> None:
    _state_path(ev).write_text(value, encoding="utf-8")


def _unlink_state(ev) -> None:
    _state_path(ev).unlink()


@pytest.mark.parametrize("case", sorted(DETECTOR_MUTATIONS))
def test_removing_the_detector_changes_the_gate_verdict_for_every_mutation(
    evidence, monkeypatch, case
):
    """The mutation proof: break the gate, then remove the detector and watch the
    break stop being detected. A detector whose removal changes nothing is not
    enforcing anything (CC/P9 — declared is not detected)."""
    ev = copy.deepcopy(evidence)
    DETECTOR_MUTATIONS[case](ev)

    with_detector = evaluate_gate(ev).verdict
    assert with_detector is not Verdict.PASS, f"{case} was not caught at all"

    monkeypatch.setattr(
        gates,
        "detect_kill_switch",
        lambda pack, **kw: [CheckOutcome("KS-P1", Verdict.PASS, "detector removed")],
    )
    without_detector = evaluate_gate(ev).verdict
    assert without_detector is Verdict.PASS, (
        f"{case}: removing the detector left the gate denying — the gate is not "
        "relying on the detector for this case"
    )


def test_removing_the_gate_composition_check_lets_an_engaged_switch_pass(
    evidence, monkeypatch
):
    """The same mutation proof for KS-G1, which lives in the gate, not the detector."""
    engage(evidence)
    assert evaluate_gate(evidence).verdict is Verdict.FAIL

    monkeypatch.setattr(gates, "stop_state_is_engaged", lambda pack, **kw: False)
    assert evaluate_gate(evidence).verdict is Verdict.PASS, (
        "bypassing KS-G1 did not change the gate verdict — it is not the thing "
        "stopping an engaged switch from passing"
    )


# ------------------------------------------ the pre-existing path is untouched


def test_existing_gate_failures_still_fail_with_a_valid_pack(evidence):
    ev = copy.deepcopy(evidence)
    ev["results"] = {
        "passed": 0,
        "failed": 1,
        "findings": [{"id": "V-CRIT-X", "severity": "CRITICAL", "status": "OPEN"}],
    }
    result = evaluate_gate(ev)
    assert result.verdict is Verdict.FAIL
    assert any("CRITICAL=1" in r for r in result.reasons)


def test_fail_dominates_unknown_across_the_kill_switch_checks(evidence):
    ev = copy.deepcopy(evidence)
    ev["kill_switch"].pop("declared_states")                       # UNKNOWN
    ev["kill_switch"]["runner_write_paths"] = ["/var/uptm/stop"]   # FAIL
    assert evaluate_gate(ev).verdict is Verdict.FAIL


# ------------------------------------------- malformed evidence denies, never crashes


@pytest.mark.parametrize("malformed", ["yes", 1, ["stop_state"]])
def test_a_kill_switch_that_is_not_a_pack_denies(valid_evidence_factory, malformed):
    """A crash is not a verdict. Malformed evidence must resolve, and to DENY."""
    result = evaluate_gate(valid_evidence_factory(kill_switch=malformed))
    assert result.verdict is Verdict.UNKNOWN, result.reasons
    assert result.decision is Decision.DENY
    assert any("not a pack" in r for r in result.reasons), result.reasons


@pytest.mark.parametrize(
    "field,value",
    [
        ("declared_states", "ENGAGED"),
        ("drill", "done"),
        ("current_environment", "same"),
        ("operator_attestation", "founder said so"),
    ],
)
def test_a_malformed_field_is_undeclared_not_a_crash(evidence, field, value):
    ev = copy.deepcopy(evidence)
    ev["kill_switch"][field] = value
    result = evaluate_gate(ev)
    assert result.verdict is not Verdict.PASS, result.reasons
    assert result.decision is Decision.DENY


def test_a_detector_that_raises_denies_without_accusing(evidence, monkeypatch):
    """A guard that cannot run has not cleared anything — but it has not caught
    anyone either, so the verdict is UNKNOWN and not a stop condition."""

    def exploding(pack, **kw):
        raise RuntimeError("detector is broken")

    monkeypatch.setattr(gates, "detect_kill_switch", exploding)
    result = evaluate_gate(evidence)
    assert result.verdict is Verdict.UNKNOWN
    assert result.decision is Decision.DENY
    assert any("detector raised RuntimeError" in r for r in result.reasons), result.reasons
    assert not any("gate_bypass_attempt" in r for r in result.reasons)


def test_an_uninterpretable_cadence_denies(evidence, monkeypatch):
    """The cadence comes from a file. A corrupted one must not pass as 'no limit'."""
    monkeypatch.setattr(gates, "drill_cadence_days", lambda: "fourteen")
    result = evaluate_gate(evidence)
    assert result.verdict is Verdict.UNKNOWN, result.reasons
    assert any("KS-D1 UNKNOWN" in r for r in result.reasons), result.reasons
