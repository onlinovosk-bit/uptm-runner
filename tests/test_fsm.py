from __future__ import annotations

import pytest

from runner.fsm import FSMError, RunnerFSM, State
from runner.gates import GateResult
from runner.paths import ROOT
from runner.staleness import digest_file
from runner.verdict import Verdict
from ruflo.adapter import SwarmCollectResult, SwarmDispatch, SwarmWorkClaim


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

    assert fsm.run_until_terminal(gate_provider, swarm_provider=_swarm_for_listed_agents) == State.EXIT
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


def _to_evidence(fsm: RunnerFSM | None = None) -> RunnerFSM:
    fsm = fsm or RunnerFSM()
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
    return fsm


def _pass() -> GateResult:
    return GateResult(verdict=Verdict.PASS, reasons=["ok"], critical=0, high=0)


def _claim(agent_id: str, path: str, *, wave_id: int = 0) -> SwarmWorkClaim:
    return SwarmWorkClaim(
        agent_id=agent_id,
        wave_id=wave_id,
        role="executor",
        stack_ids=("00", "04"),
        owned_paths=(path,),
        lease_id=f"lease-{agent_id}",
        lease_expires_at="2026-09-24T21:00:00Z",
        evidence_skeleton_path=f"evidence/wave{wave_id}/{agent_id}.json",
    )


def _dispatch() -> SwarmDispatch:
    return SwarmDispatch(
        wave_id=0,
        claims=(
            _claim("agent-a", "runner/fsm.py"),
            _claim("agent-b", "runner/gates.py"),
        ),
    )


def _real(claim: SwarmWorkClaim) -> dict:
    evidence = claim.evidence_skeleton(branch="fsm-collect", commit_sha="abc1234567")
    evidence["skeleton"] = False
    evidence["files"] = [
        {"path": path, "sha256": digest_file(ROOT / path)} for path in claim.owned_paths
    ]
    evidence["probes"] = [
        {"probe_id": "probe_live_trading", "outcome": "BLOCKED", "output_digest": "deadbeef"}
    ]
    evidence["results"] = {"passed": 1, "failed": 0, "findings": []}
    evidence["commands"] = [{"cmd": "pytest", "exit_code": 0}]
    evidence["agent_claim"] = {"verdict": "PASS", "notes": "executed"}
    return evidence


def _artifacts(dispatch: SwarmDispatch) -> dict[str, dict]:
    return {claim.evidence_skeleton_path: _real(claim) for claim in dispatch.claims}


_LISTED_CLAIMS = {
    1: ("cursor-discover", "runner/fsm.py"),
    3: ("cursor-gates", "runner/gates.py"),
}


def _swarm_for_listed_agents(fsm: RunnerFSM):
    from runner.fsm import _wave_lists_agents

    if not _wave_lists_agents(fsm.current_wave):
        return None
    agent_id, path = _LISTED_CLAIMS[fsm.current_wave]
    dispatch = SwarmDispatch(
        wave_id=fsm.current_wave,
        claims=(_claim(agent_id, path, wave_id=fsm.current_wave),),
    )
    return dispatch, _artifacts(dispatch)


def test_passing_collect_records_the_wave():
    dispatch = _dispatch()
    fsm = _to_evidence()
    assert fsm.apply_gate(_pass(), dispatch=dispatch, artifacts=_artifacts(dispatch)) == State.WAVE_READY
    assert fsm.last_collect is not None and fsm.last_collect.passed is True
    assert 0 in fsm.passed_waves
    assert fsm.current_wave == 1


def test_failing_collect_does_not_record_passed_wave():
    fsm = _to_evidence()
    assert fsm.apply_gate(_pass(), dispatch=_dispatch(), artifacts={}) == State.PATCH_LOOP
    assert fsm.last_collect is not None and fsm.last_collect.passed is False
    assert 0 not in fsm.passed_waves
    assert 1 not in fsm.unlocked_waves


def test_collect_for_another_wave_does_not_record_passed_wave():
    dispatch = _dispatch()
    foreign = SwarmDispatch(wave_id=2, claims=dispatch.claims)
    fsm = _to_evidence()
    assert fsm.apply_gate(_pass(), dispatch=foreign, artifacts=_artifacts(dispatch)) == State.PATCH_LOOP
    assert 0 not in fsm.passed_waves
    assert any("does not match current wave" in reason for reason in fsm.last_collect.reasons)


def test_gate_fail_still_blocks_a_passing_collect():
    dispatch = _dispatch()
    fsm = _to_evidence()
    fail = GateResult(verdict=Verdict.FAIL, reasons=["CRITICAL=1"], critical=1, high=0)
    assert fsm.apply_gate(fail, dispatch=dispatch, artifacts=_artifacts(dispatch)) == State.PATCH_LOOP
    assert fsm.last_collect.passed is True
    assert 0 not in fsm.passed_waves


def test_fsm_actually_calls_collect_and_verify(monkeypatch):
    calls: list[dict] = []

    def spy(self, artifacts):
        calls.append(dict(artifacts))
        return SwarmCollectResult(wave_id=self.wave_id, passed=False, reasons=("forced by spy",))

    monkeypatch.setattr(SwarmDispatch, "collect_and_verify", spy)
    fsm = _to_evidence()
    state = fsm.apply_gate(_pass(), dispatch=_dispatch(), artifacts={})
    assert len(calls) == 1, "apply_gate did not invoke collect_and_verify"
    assert state == State.PATCH_LOOP
    assert 0 not in fsm.passed_waves
    assert any("forced by spy" in reason for reason in fsm.last_collect.reasons)


def test_passed_wave_depends_on_collect_result(monkeypatch):
    """Disconnect the collector's judgement and the wave record must follow it."""
    fsm = _to_evidence()
    assert fsm.apply_gate(_pass(), dispatch=_dispatch(), artifacts={}) == State.PATCH_LOOP
    assert 0 not in fsm.passed_waves

    monkeypatch.setattr(
        SwarmDispatch,
        "collect_and_verify",
        lambda self, artifacts: SwarmCollectResult(wave_id=self.wave_id, passed=True, reasons=()),
    )
    opened = _to_evidence()
    assert opened.apply_gate(_pass(), dispatch=_dispatch(), artifacts={}) == State.WAVE_READY
    assert 0 in opened.passed_waves


def test_run_until_terminal_does_not_record_a_wave_whose_collect_fails():
    fsm = RunnerFSM()
    dispatch = _dispatch()

    def gate_provider(_: RunnerFSM) -> GateResult:
        return _pass()

    def swarm_provider(current: RunnerFSM):
        assert current.current_wave == dispatch.wave_id
        return dispatch, {}

    assert fsm.run_until_terminal(gate_provider, swarm_provider=swarm_provider) == State.HUMAN_REVIEW_REQUIRED
    assert fsm.passed_waves == set()
    assert fsm.last_collect is not None and fsm.last_collect.passed is False


def test_listed_agents_without_dispatch_does_not_record():
    fsm = _to_evidence()
    fsm.current_wave = 1
    assert fsm.apply_gate(_pass()) == State.PATCH_LOOP
    assert fsm.last_collect is not None and fsm.last_collect.passed is False
    assert any("no swarm dispatch" in reason for reason in fsm.last_collect.reasons)
    assert 1 not in fsm.passed_waves
    assert 2 not in fsm.unlocked_waves


def test_empty_agent_list_still_records_without_dispatch():
    fsm = _to_evidence()
    fsm.current_wave = 2
    assert fsm.apply_gate(_pass()) == State.WAVE_READY
    assert fsm.last_collect is None
    assert 2 in fsm.passed_waves


def test_unreadable_agents_field_requires_a_dispatch(monkeypatch):
    monkeypatch.setattr(
        "runner.fsm.load_wave",
        lambda wave_id: {"ownership": {"agents": "cursor-discover"}},
    )
    fsm = _to_evidence()
    assert fsm.apply_gate(_pass()) == State.PATCH_LOOP
    assert 0 not in fsm.passed_waves
    assert any("no swarm dispatch" in reason for reason in fsm.last_collect.reasons)


def test_fsm_actually_checks_listed_agents(monkeypatch):
    calls: list[int] = []

    def spy(wave_id: int) -> bool:
        calls.append(wave_id)
        return True

    monkeypatch.setattr("runner.fsm._wave_lists_agents", spy)
    fsm = _to_evidence()
    fsm.current_wave = 1
    state = fsm.apply_gate(_pass())
    assert calls == [1], "apply_gate did not check listed agents"
    assert state == State.PATCH_LOOP
    assert 1 not in fsm.passed_waves


def test_passed_wave_depends_on_listed_agent_check(monkeypatch):
    """Disconnect the listed-agent check and the wave record must follow it."""
    fsm = _to_evidence()
    fsm.current_wave = 1
    assert fsm.apply_gate(_pass()) == State.PATCH_LOOP
    assert 1 not in fsm.passed_waves

    monkeypatch.setattr("runner.fsm._wave_lists_agents", lambda wave_id: False)
    opened = _to_evidence()
    opened.current_wave = 1
    assert opened.apply_gate(_pass()) == State.WAVE_READY
    assert 1 in opened.passed_waves


def test_run_until_terminal_stops_when_listed_agents_have_no_dispatch():
    fsm = RunnerFSM()

    def gate_provider(_: RunnerFSM) -> GateResult:
        return _pass()

    assert fsm.run_until_terminal(gate_provider) == State.HUMAN_REVIEW_REQUIRED
    assert fsm.passed_waves == {0}
    assert fsm.current_wave == 1
    assert any("no swarm dispatch" in reason for reason in fsm.last_collect.reasons)
