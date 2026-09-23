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


# ==========================================================================
# UPTM-003 — the same proof for the kill-switch detectors.
# ==========================================================================


@pytest.fixture
def sealed_stop(tmp_path, monkeypatch):
    """A stop state this process cannot write, whatever uid the suite runs as.

    `can_write` is stubbed rather than relying on file modes: for uid 0 the OS
    reports every path writable, and that is the correct answer, not a bug —
    a Runner running as root can clear its own stop. Stubbing keeps the
    invocation proof about wiring instead of about who ran pytest.
    """
    import runner.detectors.kill_switch as ks

    monkeypatch.setattr(ks, "can_write", lambda _path: False)

    def _make(state: str = "CLEAR"):
        path = tmp_path / "stop.state"
        path.write_text(state, encoding="utf-8")
        return {
            "stop_state": {
                "path": str(path),
                "owner": "ops@revolis",
                "runner_writable": False,
            }
        }

    return _make


@pytest.fixture
def ks_evidence(evidence, sealed_stop):
    def _make(state: str = "CLEAR"):
        ev = copy.deepcopy(evidence)
        pack = sealed_stop(state)
        ev["kill_switch"] = pack
        ev["kill_switch_drill"] = {
            "last_drill_at": "2026-09-22T12:00:00Z",
            "drill_commit": "c9ae2aa",
            "drill_stop_path": pack["stop_state"]["path"],
            "before": {"state": "RUNNING", "artifact_digest": "a" * 64},
            "after": {"state": "STOPPED", "artifact_digest": "b" * 64},
        }
        return ev

    return _make


def test_gate_actually_calls_the_kill_switch_detector(ks_evidence, monkeypatch):
    calls: list[dict] = []

    def spy(pack, **kwargs):
        calls.append(pack)
        return [CheckOutcome("KS-I1", Verdict.FAIL, "forced by spy")]

    monkeypatch.setattr(gates, "detect_kill_switch", spy)
    result = evaluate_gate(ks_evidence())

    assert len(calls) == 1, "the gate did not invoke the kill-switch detector"
    assert calls[0]["stop_state"]["owner"] == "ops@revolis"
    assert result.verdict is Verdict.FAIL
    assert any("forced by spy" in r for r in result.reasons)


def test_gate_verdict_depends_on_what_the_kill_switch_detector_returns(
    ks_evidence, monkeypatch
):
    """Disconnect the detector's judgement and the gate's outcome must change."""
    broken = ks_evidence()
    broken["kill_switch"]["stop_state"]["runner_writable"] = True
    assert evaluate_gate(broken).verdict is Verdict.FAIL

    monkeypatch.setattr(
        gates,
        "detect_kill_switch",
        lambda pack, **kwargs: [CheckOutcome("KS-P2", Verdict.PASS, "stub")],
    )
    assert evaluate_gate(broken).verdict is Verdict.PASS, (
        "the gate's verdict did not follow the detector — it is computing this elsewhere"
    )


def test_gate_actually_calls_the_drill_detector(ks_evidence, monkeypatch):
    calls: list[tuple] = []
    monkeypatch.setattr(
        gates,
        "detect_kill_switch_drill",
        lambda drill, stop, cadence: calls.append((drill, stop, cadence))
        or [CheckOutcome("KS-D1", Verdict.UNKNOWN, "spy")],
    )
    result = evaluate_gate(ks_evidence())
    assert len(calls) == 1, "the gate did not invoke the drill detector"
    assert calls[0][2] == 7, "the gate did not read the Founder's cadence from capital-rules.json"
    assert result.verdict is Verdict.UNKNOWN
    assert resolve(result.verdict) is Decision.DENY


def test_engaged_stop_denies_through_the_gate(ks_evidence):
    result = evaluate_gate(ks_evidence("ENGAGED"))
    assert result.verdict is Verdict.FAIL
    assert result.decision is Decision.DENY
    assert any("kill_switch_engaged" in r for r in result.reasons), result.reasons


def test_clear_stop_with_a_recent_drill_passes_the_gate(ks_evidence):
    result = evaluate_gate(ks_evidence("CLEAR"))
    assert result.verdict is Verdict.PASS, result.reasons


def test_missing_drill_denies_without_accusing(ks_evidence):
    ev = ks_evidence()
    ev.pop("kill_switch_drill")
    result = evaluate_gate(ev)
    assert result.verdict is Verdict.UNKNOWN
    assert resolve(result.verdict) is Decision.DENY
    assert any("KS-D0" in r and "unverifiable" in r for r in result.reasons), result.reasons


def test_ks_i3b_refuses_a_pass_produced_while_the_stop_is_engaged(ks_evidence, monkeypatch):
    """The invariant, not the mechanism.

    Stub the detector into reporting a clean bill of health while the stop on
    disk reads ENGAGED. A gate that emitted PASS here would be the bypass P8
    exists to prevent, so the fold must refuse it.
    """
    monkeypatch.setattr(
        gates,
        "detect_kill_switch",
        lambda pack, **kwargs: [CheckOutcome("KS-I3", Verdict.PASS, "stub says all clear")],
    )
    result = evaluate_gate(ks_evidence("ENGAGED"))
    assert result.verdict is Verdict.FAIL
    assert any("gate_bypass_attempt" in r for r in result.reasons), result.reasons


def test_evidence_without_a_kill_switch_pack_is_untouched(evidence):
    """The omission path is left exactly as the gate treated it before."""
    assert "kill_switch" not in evidence
    result = evaluate_gate(evidence)
    assert result.verdict is Verdict.PASS
    assert not any("kill_switch" in r or r.startswith("KS-") for r in result.reasons)


# ==========================================================================
# UPTM-004 — the same proof for the validation-capital detectors.
# ==========================================================================


TRANCHE = {
    "amount": 700,
    "currency": "EUR",
    "applies_to": ["per_position_at_risk", "cumulative_realised_loss"],
}


@pytest.fixture
def declared_tranche(monkeypatch):
    """The real capital-rules.json leaves validation_capital unset on purpose.

    Stubbing the loader keeps these tests about wiring, and leaves the shipped
    configuration fail-closed until the Founder sets applies_to.
    """
    rules = json.loads(gates.CAPITAL_RULES.read_text(encoding="utf-8"))
    rules["validation_capital"] = TRANCHE
    monkeypatch.setattr(gates, "load_capital_rules", lambda: rules)
    return TRANCHE


@pytest.fixture
def capital_evidence(evidence, declared_tranche):
    def _make(**capital_overrides):
        ev = copy.deepcopy(evidence)
        ev["capital_gate"] = True
        ev["capital"] = {
            "at_risk": 250.0,
            "cumulative_realised_loss": 120.0,
            "currency": "EUR",
            **capital_overrides,
        }
        return ev

    return _make


def test_gate_actually_calls_the_validation_capital_detector(capital_evidence, monkeypatch):
    calls: list[tuple] = []

    def spy(evidence, pack, tranche):
        calls.append((pack, tranche))
        return [CheckOutcome("VC-I2", Verdict.FAIL, "forced by spy")]

    monkeypatch.setattr(gates, "detect_validation_capital", spy)
    result = evaluate_gate(capital_evidence())

    assert len(calls) == 1, "the gate did not invoke the validation-capital detector"
    assert calls[0][0]["at_risk"] == 250.0
    assert calls[0][1]["amount"] == 700, "the gate did not read the tranche from capital-rules.json"
    assert result.verdict is Verdict.FAIL
    assert any("forced by spy" in r for r in result.reasons)


def test_gate_verdict_depends_on_what_the_capital_detector_returns(capital_evidence, monkeypatch):
    """Disconnect the detector's judgement and the gate's outcome must change."""
    over = capital_evidence(at_risk=5000.0)
    assert evaluate_gate(over).verdict is Verdict.FAIL

    monkeypatch.setattr(
        gates,
        "detect_validation_capital",
        lambda evidence, pack, tranche: [CheckOutcome("VC-I2", Verdict.PASS, "stub")],
    )
    assert evaluate_gate(over).verdict is Verdict.PASS, (
        "the gate's verdict did not follow the detector — it is computing this elsewhere"
    )


def test_gate_actually_calls_the_return_criterion_detector(capital_evidence, monkeypatch):
    calls: list[tuple] = []
    monkeypatch.setattr(
        gates,
        "detect_return_as_criterion",
        lambda criteria, claim, pack: calls.append((criteria, claim))
        or [CheckOutcome("VC-R1", Verdict.UNKNOWN, "spy")],
    )
    result = evaluate_gate(capital_evidence())
    assert len(calls) == 1, "the gate did not invoke the return-criterion detector"
    assert "all_gate_unit_tests_green" in calls[0][0], (
        "the gate did not read exit_criteria from waves/wave3.yaml — "
        f"evidence is wave_id 3, criteria seen: {calls[0][0]}"
    )
    assert result.verdict is Verdict.UNKNOWN


def test_exposure_over_the_tranche_denies_through_the_gate(capital_evidence):
    result = evaluate_gate(capital_evidence(at_risk=5000.0))
    assert result.verdict is Verdict.FAIL
    assert result.decision is Decision.DENY
    assert any("exceeds the validation tranche" in r for r in result.reasons), result.reasons


def test_a_reported_loss_within_the_tranche_still_passes_the_gate(capital_evidence):
    result = evaluate_gate(capital_evidence(realised_pnl=-310.0, cumulative_realised_loss=310.0))
    assert result.verdict is Verdict.PASS, result.reasons


def test_capital_gate_without_a_pack_denies_without_accusing(capital_evidence):
    ev = capital_evidence()
    ev.pop("capital")
    result = evaluate_gate(ev)
    assert result.verdict is Verdict.UNKNOWN
    assert resolve(result.verdict) is Decision.DENY
    assert any("VC-I1" in r and "unverifiable" in r for r in result.reasons), result.reasons


def test_unset_tranche_denies_every_capital_gate(capital_evidence, monkeypatch):
    """The shipped default. Until applies_to is set, a capital gate cannot pass."""
    rules = json.loads(gates.CAPITAL_RULES.read_text(encoding="utf-8"))
    rules.pop("validation_capital", None)
    monkeypatch.setattr(gates, "load_capital_rules", lambda: rules)
    result = evaluate_gate(capital_evidence())
    assert result.verdict is Verdict.UNKNOWN
    assert any("VC-P1" in r for r in result.reasons), result.reasons


def test_evidence_without_capital_is_untouched(evidence):
    assert "capital" not in evidence and "capital_gate" not in evidence
    result = evaluate_gate(evidence)
    assert result.verdict is Verdict.PASS
    assert not any(r.startswith("validation_capital") or "VC-" in r for r in result.reasons)
