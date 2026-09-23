"""Acceptance criteria preregistered in docs/specs/UPTM-005-evidence-scope-declaration.md §5.

Case numbers are the spec's own.
"""

from __future__ import annotations

import copy

import pytest

from runner.detectors.scope import bears, detect_scope
from runner.gates import evaluate_gate
from runner.verdict import Decision, Verdict, resolve

CAPITAL_PACK = {"at_risk": 10.0, "cumulative_realised_loss": 0.0, "currency": "EUR"}
KS_PACK = {"stop_state": {"path": "/nonexistent", "owner": "ops", "runner_writable": False}}
DRILL = {"last_drill_at": "2026-09-22T12:00:00Z", "drill_commit": "c9ae2aa"}


def _outcome(outcomes, check_id):
    return next((o for o in outcomes if o.check_id == check_id), None)


def _worst(outcomes):
    verdicts = {o.verdict for o in outcomes}
    if Verdict.FAIL in verdicts:
        return Verdict.FAIL
    if Verdict.UNKNOWN in verdicts:
        return Verdict.UNKNOWN
    return Verdict.PASS


# ------------------------------------------------------------------ must FAIL


def test_case1_opting_out_of_capital_while_carrying_it():
    outcomes = detect_scope(
        {"scope": {"capital_bearing": False, "live_bearing": False}, "capital": CAPITAL_PACK}
    )
    sc_i3 = _outcome(outcomes, "SC-I3")
    assert sc_i3.verdict is Verdict.FAIL
    assert "gate_bypass_attempt" in sc_i3.detail
    assert "capital present while scope.capital_bearing is false" in sc_i3.detail


def test_case2_opting_out_of_live_while_carrying_a_kill_switch():
    outcomes = detect_scope(
        {"scope": {"capital_bearing": False, "live_bearing": False}, "kill_switch": KS_PACK}
    )
    assert _outcome(outcomes, "SC-I3").verdict is Verdict.FAIL


# --------------------------------------------------------------- must UNKNOWN


def test_case3_no_scope_at_all():
    outcomes = detect_scope({})
    sc_p1 = _outcome(outcomes, "SC-P1")
    assert sc_p1.verdict is Verdict.UNKNOWN
    assert resolve(sc_p1.verdict) is Decision.DENY
    assert not sc_p1.stop_condition_raised, "silence denies, it does not accuse"


def test_case4_one_flag_missing():
    outcomes = detect_scope({"scope": {"capital_bearing": True}})
    assert _outcome(outcomes, "SC-P1").verdict is Verdict.UNKNOWN


def test_case5_a_string_is_not_a_declaration():
    outcomes = detect_scope({"scope": {"capital_bearing": "true", "live_bearing": False}})
    sc_p1 = _outcome(outcomes, "SC-P1")
    assert sc_p1.verdict is Verdict.UNKNOWN
    assert "a string is not a declaration" in sc_p1.detail


def test_case6_capital_bearing_without_a_capital_pack():
    outcomes = detect_scope({"scope": {"capital_bearing": True, "live_bearing": False}})
    sc_i1 = _outcome(outcomes, "SC-I1")
    assert sc_i1.verdict is Verdict.UNKNOWN
    assert "the gate declares it bears capital" in sc_i1.detail


def test_case7_live_bearing_with_a_switch_but_no_drill():
    outcomes = detect_scope(
        {"scope": {"capital_bearing": False, "live_bearing": True}, "kill_switch": KS_PACK}
    )
    sc_i2 = _outcome(outcomes, "SC-I2")
    assert sc_i2.verdict is Verdict.UNKNOWN
    assert "kill_switch_drill" in sc_i2.detail


# ------------------------------------------------------------------ must PASS


def test_case8_a_gate_that_bears_neither_is_legitimate():
    """The case that keeps this wall from being a tax on every gate."""
    outcomes = detect_scope({"scope": {"capital_bearing": False, "live_bearing": False}})
    assert _worst(outcomes) is Verdict.PASS
    assert "bears nothing" in _outcome(outcomes, "SC-P1").detail


def test_case9_the_two_bearings_are_independent():
    outcomes = detect_scope(
        {"scope": {"capital_bearing": True, "live_bearing": False}, "capital": CAPITAL_PACK}
    )
    assert _worst(outcomes) is Verdict.PASS
    assert _outcome(outcomes, "SC-I2") is None, "a non-LIVE gate is not asked for a kill switch"


def test_case10_both_borne_with_both_packs():
    outcomes = detect_scope(
        {
            "scope": {"capital_bearing": True, "live_bearing": True},
            "capital": CAPITAL_PACK,
            "kill_switch": KS_PACK,
            "kill_switch_drill": DRILL,
        }
    )
    assert _worst(outcomes) is Verdict.PASS


def test_bears_helper_treats_absence_as_neither_yes_nor_no():
    assert bears({}, "live_bearing") is False
    assert bears({"scope": {"live_bearing": True}}, "live_bearing") is True
    assert bears({"scope": {"live_bearing": "true"}}, "live_bearing") is False


# ------------------------------------------- the hole this wall was built for


def test_undeclared_evidence_no_longer_slips_past_the_gate(valid_evidence_factory):
    """The omission that kept P8 and P10 at PARTIAL.

    Before UPTM-005 this evidence passed unexamined: it declares no kill switch
    and no capital, so neither detector was ever handed anything.
    """
    ev = valid_evidence_factory()
    ev.pop("scope")
    result = evaluate_gate(ev)
    assert result.verdict is Verdict.UNKNOWN
    assert result.decision is Decision.DENY
    assert any("SC-P1" in r for r in result.reasons), result.reasons


def test_declaring_capital_then_bringing_none_denies_through_the_gate(valid_evidence_factory):
    ev = valid_evidence_factory(scope={"capital_bearing": True, "live_bearing": False})
    result = evaluate_gate(ev)
    assert result.verdict is Verdict.UNKNOWN
    assert any("SC-I1" in r for r in result.reasons), result.reasons


def test_opting_out_while_carrying_fails_through_the_gate(valid_evidence_factory):
    ev = valid_evidence_factory()
    ev["capital"] = CAPITAL_PACK
    result = evaluate_gate(ev)
    assert result.verdict is Verdict.FAIL
    assert any("gate_bypass_attempt" in r for r in result.reasons), result.reasons


def test_a_gate_bearing_neither_still_passes_through_the_gate(valid_evidence_factory):
    assert evaluate_gate(valid_evidence_factory()).verdict is Verdict.PASS


# ------------------------------------------------ proof of reachability

def test_gate_actually_calls_the_scope_detector(valid_evidence_factory, monkeypatch):
    from runner import gates
    from runner.detectors.fabrication import CheckOutcome

    calls: list[dict] = []
    monkeypatch.setattr(
        gates,
        "detect_scope",
        lambda ev: calls.append(ev) or [CheckOutcome("SC-P1", Verdict.FAIL, "forced by spy")],
    )
    result = evaluate_gate(valid_evidence_factory())
    assert len(calls) == 1, "the gate did not invoke the scope detector"
    assert result.verdict is Verdict.FAIL
    assert any("forced by spy" in r for r in result.reasons)


def test_gate_verdict_depends_on_what_the_scope_detector_returns(
    valid_evidence_factory, monkeypatch
):
    from runner import gates
    from runner.detectors.fabrication import CheckOutcome

    undeclared = valid_evidence_factory()
    undeclared.pop("scope")
    assert evaluate_gate(undeclared).verdict is Verdict.UNKNOWN

    monkeypatch.setattr(
        gates, "detect_scope", lambda ev: [CheckOutcome("SC-P1", Verdict.PASS, "stub")]
    )
    assert evaluate_gate(undeclared).verdict is Verdict.PASS, (
        "the gate's verdict did not follow the detector — it is computing this elsewhere"
    )
