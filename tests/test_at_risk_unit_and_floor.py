"""UPTM-017: what `at_risk` measures, and the floor that makes the ceiling real.

Criteria are preregistered in
`docs/specs/UPTM-017-at-risk-unit-and-account-floor.md`, written before this
file existed. Each test names the criterion it discharges.

No market data, no network call. The tranche is passed in or stubbed, never
read live, so these prove the logic independently of the values the Founder
has set.
"""

from __future__ import annotations

import copy
import json

import pytest

from runner import gates
from runner.detectors.validation_capital import (
    AT_RISK_BASIS,
    check_vc_i5_at_risk_basis_declared,
    check_vc_i6_account_covers_the_ceiling,
    detect_validation_capital,
)
from runner.enforcement import _base
from runner.gates import evaluate_gate
from runner.verdict import Decision, Verdict, resolve

TRANCHE = {
    "amount": 700,
    "currency": "EUR",
    "applies_to": ["aggregate_open_exposure", "cumulative_realised_loss"],
}

PACK = {
    "at_risk": 250.0,
    "at_risk_basis": AT_RISK_BASIS,
    "account_equity": 750.0,
    "cumulative_realised_loss": 120.0,
    "currency": "EUR",
}


def pack(**overrides):
    merged = {**PACK, **overrides}
    return {k: v for k, v in merged.items() if v is not ...}


def _outcome(outcomes, check_id):
    return next(o for o in outcomes if o.check_id == check_id)


# --------------------------------------------------------------------------
# U1 / U2 - the unit is declared, and only one declaration passes
# --------------------------------------------------------------------------


def test_u1_a_pack_that_does_not_say_what_at_risk_counts_is_unknown():
    outcome = check_vc_i5_at_risk_basis_declared(pack(at_risk_basis=...), TRANCHE)
    assert outcome.verdict is Verdict.UNKNOWN
    assert resolve(outcome.verdict) is Decision.DENY
    assert "at_risk_basis" in outcome.detail


@pytest.mark.parametrize("junk", [None, "", "   ", 1, ["risk_to_stop"]])
def test_u1_a_basis_that_is_not_a_word_is_unknown_not_a_guess(junk):
    assert check_vc_i5_at_risk_basis_declared(
        pack(at_risk_basis=junk), TRANCHE
    ).verdict is Verdict.UNKNOWN


def test_u2_the_adopted_basis_passes():
    outcome = check_vc_i5_at_risk_basis_declared(pack(), TRANCHE)
    assert outcome.verdict is Verdict.PASS
    assert AT_RISK_BASIS in outcome.detail


@pytest.mark.parametrize(
    "basis, because",
    [
        ("notional", "no ES or MES contract"),
        ("margin", "moves with volatility"),
    ],
)
def test_u2_the_two_rejected_bases_are_told_why_not_merely_that(basis, because):
    """A failure that does not say why teaches the reader nothing."""
    outcome = check_vc_i5_at_risk_basis_declared(pack(at_risk_basis=basis), TRANCHE)
    assert outcome.verdict is Verdict.FAIL
    assert basis in outcome.detail
    assert because in outcome.detail


def test_u2_an_unrecognised_basis_fails_without_inventing_a_reason():
    outcome = check_vc_i5_at_risk_basis_declared(pack(at_risk_basis="vibes"), TRANCHE)
    assert outcome.verdict is Verdict.FAIL
    assert "'vibes'" in outcome.detail


# --------------------------------------------------------------------------
# U3 - bound to applies_to, derived rather than typed
# --------------------------------------------------------------------------


def test_u3_a_tranche_that_binds_no_exposure_never_reads_at_risk():
    loss_only = {**TRANCHE, "applies_to": ["cumulative_realised_loss"]}
    outcome = check_vc_i5_at_risk_basis_declared(pack(at_risk_basis=...), loss_only)
    assert outcome.verdict is Verdict.PASS
    assert "not read" in outcome.detail


def test_u3_the_other_exposure_term_binds_it_too():
    per_position = {**TRANCHE, "applies_to": ["per_position_at_risk"]}
    assert check_vc_i5_at_risk_basis_declared(
        pack(at_risk_basis=...), per_position
    ).verdict is Verdict.UNKNOWN


# --------------------------------------------------------------------------
# U4 / U5 - the floor
# --------------------------------------------------------------------------


def test_u4_a_pack_that_does_not_declare_the_account_is_unknown():
    outcome = check_vc_i6_account_covers_the_ceiling(pack(account_equity=...), TRANCHE)
    assert outcome.verdict is Verdict.UNKNOWN
    assert resolve(outcome.verdict) is Decision.DENY
    assert "account_equity" in outcome.detail


@pytest.mark.parametrize("junk", [None, "750", "", []])
def test_u4_an_account_that_is_not_a_number_is_unknown(junk):
    assert check_vc_i6_account_covers_the_ceiling(
        pack(account_equity=junk), TRANCHE
    ).verdict is Verdict.UNKNOWN


def test_u5_an_account_below_the_tranche_fails_and_says_why():
    """The bottom of the other repository's recorded range: 500 against 700."""
    outcome = check_vc_i6_account_covers_the_ceiling(pack(account_equity=500.0), TRANCHE)
    assert outcome.verdict is Verdict.FAIL
    assert "cannot bind before the account is empty" in outcome.detail
    assert "500" in outcome.detail and "700" in outcome.detail


def test_u5_an_account_exactly_at_the_tranche_passes():
    """A ceiling exactly at the account is still reachable, so it is a ceiling."""
    assert check_vc_i6_account_covers_the_ceiling(
        pack(account_equity=700.0), TRANCHE
    ).verdict is Verdict.PASS


def test_u5_the_recorded_account_of_750_covers_700():
    outcome = check_vc_i6_account_covers_the_ceiling(pack(), TRANCHE)
    assert outcome.verdict is Verdict.PASS
    assert "covers" in outcome.detail


# --------------------------------------------------------------------------
# U6 - the floor binds only where there is a ceiling to make real
# --------------------------------------------------------------------------


def test_u6_a_tranche_with_no_loss_ceiling_has_no_floor():
    exposure_only = {**TRANCHE, "applies_to": ["aggregate_open_exposure"]}
    outcome = check_vc_i6_account_covers_the_ceiling(
        pack(account_equity=...), exposure_only
    )
    assert outcome.verdict is Verdict.PASS
    assert "does not apply" in outcome.detail


def test_u6_an_unset_amount_is_unknown_not_a_floor_of_zero():
    no_amount = {**TRANCHE, "amount": None}
    assert check_vc_i6_account_covers_the_ceiling(
        pack(), no_amount
    ).verdict is Verdict.UNKNOWN


# --------------------------------------------------------------------------
# U7 - both checks reach the gate
# --------------------------------------------------------------------------


@pytest.fixture
def stub_tranche(monkeypatch):
    rules = json.loads(gates.CAPITAL_RULES.read_text(encoding="utf-8"))
    rules["validation_capital"] = TRANCHE
    monkeypatch.setattr(gates, "load_capital_rules", lambda: rules)
    return TRANCHE


def capital_evidence(**overrides):
    evidence = copy.deepcopy(_base())
    evidence["scope"] = {"capital_bearing": True, "live_bearing": False}
    evidence["capital_gate"] = True
    evidence["capital"] = pack(**overrides)
    return evidence


def test_u7_a_capital_gate_passes_when_both_are_declared(stub_tranche):
    """The denials below are the new checks, not something else about the pack."""
    assert evaluate_gate(capital_evidence()).verdict is Verdict.PASS


@pytest.mark.parametrize(
    "missing, check_id",
    [("at_risk_basis", "VC-I5"), ("account_equity", "VC-I6")],
)
def test_u7_the_gate_denies_a_pack_that_omits_either_and_names_the_check(
    stub_tranche, missing, check_id
):
    result = evaluate_gate(capital_evidence(**{missing: ...}))
    assert result.verdict is not Verdict.PASS
    assert resolve(result.verdict) is Decision.DENY
    assert any(check_id in reason for reason in result.reasons), result.reasons


def test_u7_an_account_below_the_tranche_denies_at_the_gate(stub_tranche):
    result = evaluate_gate(capital_evidence(account_equity=500.0))
    assert resolve(result.verdict) is Decision.DENY
    assert any("VC-I6" in reason for reason in result.reasons)


# --------------------------------------------------------------------------
# U8 - a non-capital gate is untouched, because §3 claims it is
# --------------------------------------------------------------------------


def test_u8_evidence_with_no_capital_pack_is_unaffected(stub_tranche):
    plain = _base()
    assert "capital" not in plain
    assert plain.get("capital_gate") is not True
    assert evaluate_gate(plain).verdict is Verdict.PASS


def test_u8_the_new_checks_are_not_even_reached_without_a_pack():
    outcomes = detect_validation_capital({}, {}, TRANCHE)
    ids = {o.check_id for o in outcomes}
    assert {"VC-I5", "VC-I6"} <= ids, "they run, but on an empty pack"
    # ...and on an empty pack they are the honest UNKNOWN, never a quiet pass.
    assert _outcome(outcomes, "VC-I5").verdict is Verdict.UNKNOWN
    assert _outcome(outcomes, "VC-I6").verdict is Verdict.UNKNOWN
