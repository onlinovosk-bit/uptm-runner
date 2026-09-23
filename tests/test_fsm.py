from __future__ import annotations

import pytest

from runner.fsm import FSMError, RunnerFSM, State
from runner.gates import GateResult
from runner.verdict import Verdict


def test_fsm_happy_path_to_wave_ready():
    fsm = RunnerFSM()
    assert fsm.state == State.DISCOVER
    fsm.transition(State.BASELINE)
    fsm.transition(State.PLAN)
    fsm.transition(State.WAVE_READY)
    assert fsm.state == State.WAVE_READY


def test_fsm_illegal_transition_rejected():
    fsm = RunnerFSM()
    with pytest.raises(FSMError, match="illegal transition"):
        fsm.transition(State.WAVE_GATE)


def test_fsm_full_cycle_to_gate_pass_unlocks_next():
    fsm = RunnerFSM()
    for st in (
        State.BASELINE,
        State.PLAN,
        State.WAVE_READY,
        State.PARALLEL_DISPATCH,
        State.EXECUTION,
        State.COLLECT,
        State.VERIFY,
        State.ADVERSARIAL_VERIFY,
        State.EVIDENCE,
    ):
        fsm.transition(st)
    gate = GateResult(verdict=Verdict.PASS, reasons=["ok"], critical=0, high=0)
    out = fsm.apply_gate(gate)
    assert out == State.WAVE_READY
    assert 1 in fsm.unlocked_waves
    assert fsm.current_wave == 1


def test_wave_non_crossing():
    fsm = RunnerFSM()
    assert 0 in fsm.unlocked_waves
    with pytest.raises(FSMError, match="wave_skip"):
        fsm.assert_wave_unlocked(5)


def test_wave_one_cannot_start_until_wave_zero_gate_passes():
    fsm = RunnerFSM(unlocked_waves={0, 1})
    with pytest.raises(FSMError, match="not gated PASS"):
        fsm.assert_wave_unlocked(1)


def test_patch_limit_then_human_review():
    fsm = RunnerFSM()
    for st in (
        State.BASELINE,
        State.PLAN,
        State.WAVE_READY,
        State.PARALLEL_DISPATCH,
        State.EXECUTION,
        State.COLLECT,
        State.VERIFY,
        State.ADVERSARIAL_VERIFY,
        State.EVIDENCE,
    ):
        fsm.transition(st)
    fail = GateResult(verdict=Verdict.FAIL, reasons=["CRITICAL=1"], critical=1, high=0)
    for i in range(3):
        # after first fail we go PATCH_LOOP then need to get back to WAVE_GATE
        state = fsm.apply_gate(fail, cluster_id="c1")
        assert state == State.PATCH_LOOP
        # re-enter path to WAVE_GATE
        fsm.transition(State.PARALLEL_DISPATCH)
        for st in (
            State.EXECUTION,
            State.COLLECT,
            State.VERIFY,
            State.ADVERSARIAL_VERIFY,
            State.EVIDENCE,
        ):
            fsm.transition(st)
    # 4th failure exhausts (attempts become 4 > 3)
    state = fsm.apply_gate(fail, cluster_id="c1")
    assert state == State.HUMAN_REVIEW_REQUIRED
    assert fsm.patch_attempts["c1"] == 4


def test_terminating_fsm_reaches_exit_after_all_waves_pass():
    fsm = RunnerFSM()

    def gate_provider(_: RunnerFSM) -> GateResult:
        return GateResult(verdict=Verdict.PASS, reasons=["ok"], critical=0, high=0)

    assert fsm.run_until_terminal(gate_provider) == State.EXIT
    assert fsm.passed_waves == set(range(8))
    assert fsm.current_wave == 7


def test_terminating_fsm_reaches_human_review_after_patch_limit():
    fsm = RunnerFSM()

    def gate_provider(_: RunnerFSM) -> GateResult:
        return GateResult(verdict=Verdict.FAIL, reasons=["CRITICAL=1"], critical=1, high=0)

    assert fsm.run_until_terminal(gate_provider) == State.HUMAN_REVIEW_REQUIRED
    assert fsm.patch_attempts["wave0"] == 4


def test_inconsistent_pass_with_high_finding_does_not_unlock_next_wave():
    fsm = RunnerFSM()
    for st in (
        State.BASELINE,
        State.PLAN,
        State.WAVE_READY,
        State.PARALLEL_DISPATCH,
        State.EXECUTION,
        State.COLLECT,
        State.VERIFY,
        State.ADVERSARIAL_VERIFY,
        State.EVIDENCE,
    ):
        fsm.transition(st)
    gate = GateResult(verdict=Verdict.PASS, reasons=["inconsistent"], critical=0, high=1)
    assert fsm.apply_gate(gate) == State.PATCH_LOOP
    assert 0 not in fsm.passed_waves
    assert 1 not in fsm.unlocked_waves
