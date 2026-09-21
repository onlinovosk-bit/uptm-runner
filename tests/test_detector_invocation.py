"""UPTM-002c — proof that the runtime path invokes the detectors.

`import fabrication` proves nothing. These tests prove that a real
`evaluate_gate` call reaches the detectors, and that the gate's verdict
*depends on what they return* — disconnect them and the outcome changes.
"""

from __future__ import annotations

import copy
import hashlib
import json

import pytest

from runner import gates
from runner.detectors.fabrication import CheckOutcome
from runner.gates import evaluate_gate
from runner.verdict import Decision, Verdict, resolve

SESSIONS = ["2026-09-14", "2026-09-15", "2026-09-16", "2026-09-17", "2026-09-18"]
CLOSES = [100.0, 101.5, 99.0, 102.0, 103.5]


def _bars():
    return [
        {
            "ts": f"{day}T20:00:00Z",
            "open": c - 0.5,
            "high": c + 1.0,
            "low": c - 1.0,
            "close": c,
            "volume": 1000,
        }
        for day, c in zip(SESSIONS, CLOSES)
    ]


@pytest.fixture
def market_pack(tmp_path):
    root = tmp_path / "snap"
    root.mkdir()
    (root / "series.json").write_text(json.dumps(_bars()), encoding="utf-8")
    digest = hashlib.sha256((root / "series.json").read_bytes()).hexdigest()
    return {
        "source_id": "vendor-x:EQ:ACME:1d",
        "acquired_at_utc": "2026-09-19T06:00:00Z",
        "content_digest": digest,
        "snapshot_ref": "series.json",
        "snapshot_root": str(root),
        "coverage": {"first": SESSIONS[0], "last": SESSIONS[-1]},
        "computation_interval": {"first": SESSIONS[1], "last": SESSIONS[-1]},
        "min_expected_variance": 0.01,
        "variance_window": 3,
        "calendar_id": "XNYS",
        "duplicate_block_min_len": 3,
        "allows_repeated_bars": False,
        "bars": _bars(),
    }


@pytest.fixture
def pnl_pack():
    return {
        "accounting_boundary": {"opening_position": 0.0, "opening_mark": 100.0},
        "quantity_convention": "signed_long_positive",
        "pnl_tolerance": {"absolute": 0.01, "relative": 0.001},
        "execution_model": {"charges_fees": True, "charges_slippage": True},
        "gated_order_ids": ["ord-1"],
        "fills": [
            {"order_id": "ord-1", "qty": 10.0, "price": 100.0, "fee": 1.0, "slippage": 0.5}
        ],
        "position_after": 10.0,
        "mark_price": 105.0,
        "reported_pnl": 48.5,
        "realized_pnl": -1001.5,
        "unrealized_pnl": 50.0,
    }


@pytest.fixture
def evidence(valid_evidence_factory, market_pack, pnl_pack):
    return valid_evidence_factory(
        market_data=market_pack,
        pnl=pnl_pack,
        calendars={"XNYS": SESSIONS},
    )


# ---------------------------------------------------- the path is reachable


def test_valid_packs_pass_through_the_gate(evidence):
    result = evaluate_gate(evidence)
    assert result.verdict is Verdict.PASS, result.reasons


def test_gate_fails_and_names_fabricated_market_data(evidence):
    ev = copy.deepcopy(evidence)
    ev["market_data"]["content_digest"] = "0" * 64
    result = evaluate_gate(ev)
    assert result.verdict is Verdict.FAIL
    assert any("fabricated_market_data" in r for r in result.reasons), result.reasons
    assert result.decision is Decision.DENY


def test_gate_fails_and_names_fabricated_pnl(evidence):
    ev = copy.deepcopy(evidence)
    ev["pnl"]["fills"][0]["order_id"] = "ord-unknown"
    result = evaluate_gate(ev)
    assert result.verdict is Verdict.FAIL
    assert any("fabricated_pnl" in r for r in result.reasons), result.reasons


def test_undeclared_parameter_makes_the_gate_unknown_not_fail(evidence):
    """UNKNOWN denies without accusing — the distinction survives the wiring."""
    ev = copy.deepcopy(evidence)
    ev["market_data"].pop("calendar_id")
    result = evaluate_gate(ev)
    assert result.verdict is Verdict.UNKNOWN, result.reasons
    assert resolve(result.verdict) is Decision.DENY
    assert result.passed is False
    assert not any("fabricated_market_data" in r for r in result.reasons)
    assert any("unverifiable" in r for r in result.reasons), result.reasons


# -------------------------------------- proof of reachability (disconnection)


def test_gate_actually_calls_the_market_data_detector(evidence, monkeypatch):
    calls: list[dict] = []

    def spy(pack, *, snapshot_root, calendars):
        calls.append({"pack": pack, "calendars": calendars})
        return [CheckOutcome("MD-I1", Verdict.FAIL, "forced by spy")]

    monkeypatch.setattr(gates, "detect_fabricated_market_data", spy)
    result = evaluate_gate(evidence)

    assert len(calls) == 1, "the gate did not invoke the market-data detector"
    assert calls[0]["pack"]["source_id"] == "vendor-x:EQ:ACME:1d"
    assert calls[0]["calendars"] == {"XNYS": set(SESSIONS)}
    assert result.verdict is Verdict.FAIL
    assert any("forced by spy" in r for r in result.reasons)


def test_gate_verdict_depends_on_what_the_detector_returns(evidence, monkeypatch):
    """Disconnect the detector's judgement and the gate's outcome must change."""
    broken = copy.deepcopy(evidence)
    broken["market_data"]["content_digest"] = "0" * 64
    assert evaluate_gate(broken).verdict is Verdict.FAIL

    monkeypatch.setattr(
        gates,
        "detect_fabricated_market_data",
        lambda pack, *, snapshot_root, calendars: [CheckOutcome("MD-I1", Verdict.PASS, "stub")],
    )
    assert evaluate_gate(broken).verdict is Verdict.PASS, (
        "the gate's verdict did not follow the detector — it is computing this elsewhere"
    )


def test_gate_actually_calls_the_pnl_detector(evidence, monkeypatch):
    calls: list[dict] = []
    monkeypatch.setattr(
        gates,
        "detect_fabricated_pnl",
        lambda pack: calls.append(pack) or [CheckOutcome("PL-A1", Verdict.UNKNOWN, "spy")],
    )
    result = evaluate_gate(evidence)
    assert len(calls) == 1, "the gate did not invoke the PnL detector"
    assert result.verdict is Verdict.UNKNOWN


# ------------------------------------------ the pre-existing path is untouched


def test_evidence_without_packs_never_reaches_the_detectors(valid_evidence_factory, monkeypatch):
    def explode(*args, **kwargs):  # pragma: no cover - must never run
        raise AssertionError("detector invoked for evidence that declares no packs")

    monkeypatch.setattr(gates, "detect_fabricated_market_data", explode)
    monkeypatch.setattr(gates, "detect_fabricated_pnl", explode)
    assert evaluate_gate(valid_evidence_factory()).verdict is Verdict.PASS


def test_existing_gate_failures_still_fail_with_valid_packs(evidence):
    """A CRITICAL finding must still FAIL even when every pack verifies."""
    ev = copy.deepcopy(evidence)
    ev["results"] = {
        "passed": 0,
        "failed": 1,
        "findings": [{"id": "V-CRIT-X", "severity": "CRITICAL", "status": "OPEN"}],
    }
    result = evaluate_gate(ev)
    assert result.verdict is Verdict.FAIL
    assert any("CRITICAL=1" in r for r in result.reasons)


def test_fail_dominates_unknown_in_the_gate(evidence):
    ev = copy.deepcopy(evidence)
    ev["market_data"].pop("calendar_id")          # UNKNOWN
    ev["pnl"]["fills"][0]["order_id"] = "orphan"  # FAIL
    assert evaluate_gate(ev).verdict is Verdict.FAIL
