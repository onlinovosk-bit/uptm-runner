"""Adversarial tests against the Runner itself."""

from __future__ import annotations

import json

import pytest

from cursor.contract import CursorNotConfiguredError, CursorTask, get_executor
from runner.fsm import FSMError, RunnerFSM, State
from runner.gates import evaluate_gate
from ruflo.adapter import OrchestrationEvent, RufloUnavailableError, get_adapter


def test_forged_evidence_rejected(valid_evidence_factory):
    """Evidence that claims PASS but lacks probe BLOCKED / has forged empty integrity."""
    ev = valid_evidence_factory(
        agent_claim={"verdict": "PASS", "notes": "forged"},
        probes=[
            {
                "probe_id": "forged",
                "outcome": "SKIPPED",
                "output_digest": "0" * 8,
            }
        ],
        signature="forged-sig",
    )
    r = evaluate_gate(ev)
    assert r.passed is False
    assert any("SKIPPED" in x or "probe" in x.lower() for x in r.reasons)


def test_fake_agent_pass(valid_evidence_factory):
    ev = valid_evidence_factory(
        evidence_id="fake",
        wave_id=1,
        commit_sha="deadbeef",
        branch="x",
        files=[],
        commands=[],
        results={"passed": 99, "failed": 0, "findings": []},
        probes=[],  # fake pass with no probes
        before={"digest": "x"},
        after={"digest": "y"},
        agent_claim={"verdict": "PASS"},
    )
    r = evaluate_gate(ev)
    assert r.passed is False
    assert any("probe" in reason.lower() for reason in r.reasons)


def test_wave_skip(valid_evidence_factory):
    fsm = RunnerFSM()
    with pytest.raises(FSMError, match="wave_skip"):
        fsm.assert_wave_unlocked(7)


def test_critical_hidden_as_warning(valid_evidence_factory):
    ev = valid_evidence_factory(
        results={
            "passed": 1,
            "failed": 0,
            "findings": [
                {
                    "id": "V-CRIT-COORDINATED-DB-KEY-RECEIPT",
                    "severity": "WARNING",
                    "status": "OPEN",
                    "hidden_as": "WARNING",
                    "true_severity": "CRITICAL",
                }
            ],
        }
    )
    r = evaluate_gate(ev)
    assert r.passed is False
    assert r.critical >= 1 or any("downgraded" in x or "hidden" in x for x in r.reasons)


def test_evidence_without_probes(valid_evidence_factory):
    ev = valid_evidence_factory(probes=[])
    r = evaluate_gate(ev)
    assert r.passed is False


def test_cursor_stub_fails_closed():
    ex = get_executor()
    assert ex.is_configured() is False
    with pytest.raises(CursorNotConfiguredError):
        ex.dispatch(CursorTask(1, "04", "prompt-stacks/04_dispatch.md"))


def test_ruflo_stub_unavailable():
    ad = get_adapter()
    assert ad.available() is False
    with pytest.raises(RufloUnavailableError):
        ad.publish(OrchestrationEvent("wave", {"id": 1}))


def test_orchestration_without_ruflo():
    """Local FSM works without Ruflo."""
    fsm = RunnerFSM()
    fsm.transition(State.BASELINE)
    fsm.transition(State.PLAN)
    fsm.transition(State.WAVE_READY)
    assert fsm.state == State.WAVE_READY


def test_pr4_merge_forbidden_in_baseline():
    from runner.fsm import load_baseline

    b = load_baseline()
    assert b.get("pr4_merge_allowed") is False
    assert b.get("pr4_production_ready") is False
    pr4 = next(p for p in b["pr_history"] if p["pr"] == 4)
    assert pr4["status"] == "claims_unverified"
    assert pr4["merge_allowed"] is False
