from __future__ import annotations

from runner.gates import evaluate_gate
from runner.stops import StopConditionError
from runner.fsm import load_baseline
import pytest


def test_gate_fail_closed_missing_evidence():
    r = evaluate_gate(None)
    assert r.passed is False
    assert any("missing evidence" in x for x in r.reasons)


def test_agent_pass_without_evidence_rejected(valid_evidence_factory):
    # Strip probes and digests — self-report only shape
    ev = valid_evidence_factory(
        probes=[],
        before={"digest": ""},
        after={"digest": ""},
        agent_claim={"verdict": "PASS", "notes": "trust me"},
    )
    # Also remove required structure by emptying probes — validate will fail
    r = evaluate_gate(ev)
    assert r.passed is False


def test_agent_pass_without_probes_rejected(valid_evidence_factory):
    ev = valid_evidence_factory()
    ev["probes"] = []
    r = evaluate_gate(ev)
    assert r.passed is False
    assert any("probe" in x.lower() for x in r.reasons)


def test_valid_evidence_passes(valid_evidence_factory):
    ev = valid_evidence_factory()
    r = evaluate_gate(ev)
    assert r.passed is True
    assert r.critical == 0
    assert r.high == 0


def test_open_critical_fails_gate(valid_evidence_factory):
    ev = valid_evidence_factory(
        results={
            "passed": 0,
            "failed": 1,
            "findings": [
                {
                    "id": "V-CRIT-COORDINATED-DB-KEY-RECEIPT",
                    "severity": "CRITICAL",
                    "status": "OPEN",
                }
            ],
        }
    )
    r = evaluate_gate(ev)
    assert r.passed is False
    assert r.critical >= 1


def test_live_trading_stop(valid_evidence_factory):
    ev = valid_evidence_factory(live_trading=True)
    r = evaluate_gate(ev)
    assert r.passed is False
    assert any("live_trading" in x or "stop:" in x for x in r.reasons)


def test_baseline_live_trading_false():
    b = load_baseline()
    assert b["live_trading"] is False
    assert b["pr4_merge_allowed"] is False
