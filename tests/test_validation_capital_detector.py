"""Acceptance criteria preregistered in docs/specs/UPTM-004-validation-capital-cap.md §5.

Case numbers are the spec's own. The tranche is passed in rather than read from
constitution/capital-rules.json, so these prove the logic while the real
configuration stays unset and fail-closed.
"""

from __future__ import annotations

import pytest

from runner.detectors.validation_capital import (
    detect_return_as_criterion,
    detect_validation_capital,
)
from runner.verdict import Decision, Verdict, resolve

TRANCHE = {
    "amount": 700,
    "currency": "EUR",
    "applies_to": ["per_position_at_risk", "cumulative_realised_loss"],
}


def _outcome(outcomes, check_id):
    return next(o for o in outcomes if o.check_id == check_id)


@pytest.fixture
def capital():
    def _make(**overrides):
        base = {
            "at_risk": 250.0,
            "cumulative_realised_loss": 120.0,
            "currency": "EUR",
        }
        base.update(overrides)
        return base

    return _make


@pytest.fixture
def evidence():
    def _make(**overrides):
        base = {"capital_gate": True}
        base.update(overrides)
        return base

    return _make


ROBUST_CRITERIA = ["live_trading_is_false", "kill_switch_drill_within_cadence", "pnl_pack_declared"]


# ------------------------------------------------------------------ must FAIL


def test_case1_exposure_above_the_tranche(capital, evidence):
    outcomes = detect_validation_capital(evidence(), capital(at_risk=900.0), TRANCHE)
    assert _outcome(outcomes, "VC-I2").verdict is Verdict.FAIL


def test_case2_cumulative_loss_sinks_the_tranche_while_each_action_is_small(capital, evidence):
    """Twenty positions of 50 each are all within the cap. The tranche is gone."""
    pack = capital(at_risk=50.0, cumulative_realised_loss=1000.0)
    outcomes = detect_validation_capital(evidence(), pack, TRANCHE)
    assert _outcome(outcomes, "VC-I2").verdict is Verdict.PASS, "each action was within the cap"
    assert _outcome(outcomes, "VC-I3").verdict is Verdict.FAIL
    assert "the tranche is gone anyway" in _outcome(outcomes, "VC-I3").detail


def test_case3_exit_criterion_keyed_on_return_as_a_string(capital):
    outcomes = detect_return_as_criterion(
        ROBUST_CRITERIA + ["realised return >= 5"], {"verdict": "PASS"}, capital()
    )
    ks = _outcome(outcomes, "VC-R1")
    assert ks.verdict is Verdict.FAIL
    assert "return is not a criterion of any gate" in ks.detail


def test_case3b_exit_criterion_keyed_on_return_as_a_mapping(capital):
    outcomes = detect_return_as_criterion(
        [{"metric": "roi", "op": ">=", "value": 0.05}], {"verdict": "PASS"}, capital()
    )
    assert _outcome(outcomes, "VC-R1").verdict is Verdict.FAIL


def test_case4_pass_justified_by_profit(capital):
    outcomes = detect_return_as_criterion(
        ROBUST_CRITERIA,
        {"verdict": "PASS", "basis": ["net_profit", "kill_switch_drill_within_cadence"]},
        capital(),
    )
    vc_r2 = _outcome(outcomes, "VC-R2")
    assert vc_r2.verdict is Verdict.FAIL
    assert "not by what it earned" in vc_r2.detail


def test_case5_pnl_threshold_fails_even_when_exposure_is_within_the_cap(capital, evidence):
    within = detect_validation_capital(evidence(), capital(), TRANCHE)
    assert all(o.verdict is Verdict.PASS for o in within)
    outcomes = detect_return_as_criterion(
        [{"metric": "pnl", "op": ">", "value": 0}], {"verdict": "PASS"}, capital()
    )
    assert _outcome(outcomes, "VC-R1").verdict is Verdict.FAIL


# --------------------------------------------------------------- must UNKNOWN


def test_case6_tranche_undeclared_is_unknown_not_pass(capital, evidence):
    outcomes = detect_validation_capital(evidence(), capital(), {})
    vc_p1 = _outcome(outcomes, "VC-P1")
    assert vc_p1.verdict is Verdict.UNKNOWN
    assert resolve(vc_p1.verdict) is Decision.DENY
    assert not vc_p1.stop_condition_raised, "an unset parameter denies, it does not accuse"


def test_case6b_applies_to_missing_is_unknown(capital, evidence):
    tranche = {"amount": 700, "currency": "EUR"}
    assert _outcome(
        detect_validation_capital(evidence(), capital(), tranche), "VC-P1"
    ).verdict is Verdict.UNKNOWN


def test_case6c_applies_to_with_an_unrecognised_binding_is_unknown(capital, evidence):
    tranche = dict(TRANCHE, applies_to=["whatever_feels_right"])
    assert _outcome(
        detect_validation_capital(evidence(), capital(), tranche), "VC-P1"
    ).verdict is Verdict.UNKNOWN


def test_case7_capital_gate_with_no_pack_is_unknown(evidence):
    """The omission UPTM-002 recorded, closed here for capital gates."""
    outcomes = detect_validation_capital(evidence(), {}, TRANCHE)
    vc_i1 = _outcome(outcomes, "VC-I1")
    assert vc_i1.verdict is Verdict.UNKNOWN
    assert "declares capital_gate=true and carries none" in vc_i1.detail


def test_case8_currency_mismatch_is_unknown_never_converted(capital, evidence):
    outcomes = detect_validation_capital(evidence(), capital(currency="USD"), TRANCHE)
    vc_i4 = _outcome(outcomes, "VC-I4")
    assert vc_i4.verdict is Verdict.UNKNOWN
    assert not vc_i4.stop_condition_raised


def test_case9_gate_that_does_not_declare_itself_is_unknown(capital):
    outcomes = detect_validation_capital({}, capital(), TRANCHE)
    assert _outcome(outcomes, "VC-P2").verdict is Verdict.UNKNOWN


# ------------------------------------------------------------------ must PASS


def test_case10_within_the_tranche_with_robustness_criteria(capital, evidence):
    outcomes = detect_validation_capital(evidence(), capital(), TRANCHE)
    outcomes += detect_return_as_criterion(ROBUST_CRITERIA, {"verdict": "PASS"}, capital())
    assert all(o.verdict is Verdict.PASS for o in outcomes), [
        (o.check_id, o.detail) for o in outcomes if o.verdict is not Verdict.PASS
    ]


def test_case11_a_reported_loss_is_never_a_gate_failure(capital, evidence):
    """Losing money inside the tranche is the expected outcome of a validation run."""
    pack = capital(realised_pnl=-310.0, cumulative_realised_loss=310.0)
    outcomes = detect_validation_capital(evidence(), pack, TRANCHE)
    outcomes += detect_return_as_criterion(ROBUST_CRITERIA, {"verdict": "PASS"}, pack)
    assert all(o.verdict is Verdict.PASS for o in outcomes), [
        (o.check_id, o.detail) for o in outcomes if o.verdict is not Verdict.PASS
    ]


def test_case12_an_unreferenced_profit_is_permitted(capital):
    pack = capital(realised_pnl=420.0)
    outcomes = detect_return_as_criterion(ROBUST_CRITERIA, {"verdict": "PASS"}, pack)
    assert all(o.verdict is Verdict.PASS for o in outcomes)
    assert "referenced by no criterion — permitted" in _outcome(outcomes, "VC-R3").detail


def test_case13_a_criterion_merely_naming_pnl_is_not_a_return_criterion(capital):
    """`pnl_pack_declared` requires reporting, not profit. It must not trip VC-R1."""
    outcomes = detect_return_as_criterion(
        ["pnl_pack_declared", "fills_reconcile"], {"verdict": "PASS"}, capital()
    )
    assert _outcome(outcomes, "VC-R1").verdict is Verdict.PASS


def test_tranche_binding_only_cumulative_loss_leaves_exposure_to_vc_i3(capital, evidence):
    tranche = dict(TRANCHE, applies_to=["cumulative_realised_loss"])
    outcomes = detect_validation_capital(evidence(), capital(at_risk=5000.0), tranche)
    assert _outcome(outcomes, "VC-I2").verdict is Verdict.PASS
    assert "VC-I3 carries the ceiling" in _outcome(outcomes, "VC-I2").detail
