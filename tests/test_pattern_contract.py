"""UPTM-011: the Bearish Quasimodo contract claims nothing it has not earned.

Criteria are preregistered in
``docs/specs/UPTM-011-bearish-quasimodo-contract.md``, written before this file
existed. Each test names the criterion it discharges.

Nothing here reads market data or runs a detector. There is nothing to run: the
contract's own ``rules`` axis says so, and these tests are what stop that axis
moving while it is true.
"""

from __future__ import annotations

import copy
import json

import pytest

from runner.pattern_contract import (
    AXES,
    RUNGS,
    SWING_DEFINITION,
    SWING_PARAMETERS,
    UNDEFINED,
    ladder_errors,
    lowest,
    required_terms,
    swing_terms_used,
    top,
    undefined_terms,
)
from runner.paths import ROOT

CANDIDATES = ROOT / "research" / "candidates"
CONTRACT_PATH = CANDIDATES / "reversal" / "bearish_quasimodo.json"

# Named by the spec's §1 right-hand column: what the restatement does not say.
# Listed here rather than derived because this assertion is about *this* source
# - it is the spec's provenance table, asserted.
NOT_STATED_BY_THE_SOURCE = {
    SWING_PARAMETERS,
    "break_tolerance",
    "entry_trigger",
    "target_exit",
    "instrument_es_vs_mes",
    "timeframe",
    "session_window",
    "slippage_model",
    "fee_model",
    "risk_sizing",
    "invalidation_rules",
}


@pytest.fixture()
def contract() -> dict:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def _raised(contract: dict, axis: str) -> dict:
    """The same contract with one axis moved one rung up."""
    moved = copy.deepcopy(contract)
    moved["status"][axis] = RUNGS[axis][1]
    return moved


# --------------------------------------------------------------------------
# C1 - every axis at its lowest rung, and nothing live
# --------------------------------------------------------------------------


def test_c1_the_contract_sits_at_the_bottom_of_every_axis(contract):
    assert contract["live_trading"] is False
    assert set(contract["status"]) == set(AXES)
    assert {axis: contract["status"][axis] for axis in AXES} == {
        axis: lowest(axis) for axis in AXES
    }
    assert ladder_errors(contract) == []


def test_c1_live_trading_cannot_be_switched_on_quietly(contract):
    live = copy.deepcopy(contract)
    live["live_trading"] = True
    assert "live_trading must be false" in ladder_errors(live)


def test_c1_an_invented_rung_is_not_a_rung(contract):
    forged = copy.deepcopy(contract)
    forged["status"]["performance"] = "PROFITABLE"
    errors = ladder_errors(forged)
    assert len(errors) == 1
    assert "'PROFITABLE'" in errors[0]


# --------------------------------------------------------------------------
# C2 - undefined is written down; absent is not a way past it
# --------------------------------------------------------------------------


def test_c2_everything_the_source_does_not_state_is_present_and_undefined(contract):
    terms = contract["terms"]
    assert NOT_STATED_BY_THE_SOURCE <= set(terms)
    assert {terms[name] for name in NOT_STATED_BY_THE_SOURCE} == {UNDEFINED}


def test_c2_deleting_a_term_does_not_define_it(contract):
    """Absent must fail the same way UNDEFINED does, or the gate is advisory."""
    assert SWING_PARAMETERS in undefined_terms(contract)

    # UPTM-012 wrote the root down; deleting it reopens it rather than closing it.
    deleted = copy.deepcopy(contract)
    del deleted["terms"][SWING_DEFINITION]
    assert SWING_DEFINITION in undefined_terms(deleted)

    deleted["status"]["source"] = top("source")
    deleted["status"]["rules"] = "MECHANICAL"
    errors = ladder_errors(deleted)
    assert any(SWING_DEFINITION in error for error in errors)


def test_c2_an_empty_terms_block_is_not_a_clean_contract(contract):
    stripped = copy.deepcopy(contract)
    stripped["terms"] = {}
    assert set(undefined_terms(stripped)) == set(required_terms(stripped))
    # With the root gone, the parameter term is not what stands in the way.
    assert SWING_DEFINITION in undefined_terms(stripped)
    assert SWING_PARAMETERS not in required_terms(stripped)


# --------------------------------------------------------------------------
# C3 - the dependency is in the data, not only in the prose
# --------------------------------------------------------------------------


def test_c3_the_sequence_names_swings_and_the_root_is_required(contract):
    """Amended by UPTM-012: the root is defined now, and still required."""
    assert SWING_DEFINITION in required_terms(contract)
    assert contract["terms"][SWING_DEFINITION] != UNDEFINED
    assert swing_terms_used(contract) == ["HH", "HL", "LL", "LH"]
    assert [step["swing"] for step in contract["structure"]["sequence"]] == [
        "HH",
        "HL",
        "HH",
        "LL",
        "LH",
    ]
    assert contract["structure"]["direction"] == "short"


def test_c3_rules_cannot_leave_undefined_while_the_root_is_undefined(contract):
    claiming = copy.deepcopy(contract)
    claiming["status"]["source"] = top("source")
    claiming["status"]["rules"] = "MECHANICAL"
    errors = ladder_errors(claiming)
    assert any("status.rules is 'MECHANICAL'" in error for error in errors)


# --------------------------------------------------------------------------
# C4 - derived, not typed: the rule holds for a contract this spec never saw
# --------------------------------------------------------------------------

# Not Quasimodo, not in the repository, not mentioned by the spec. If the rule
# were a hand-kept list of Quasimodo's terms, this contract would walk through.
UNSEEN_CONTRACT = {
    "candidate_id": "triple_bottom_invented_for_this_test",
    "live_trading": False,
    "status": {
        "source": "VERIFIED_SOURCE",
        "rules": "MECHANICAL",
        "implementation": "NOT_STARTED",
        "no_leakage": "NOT_TESTED",
        "stats": "NOT_TESTED",
        "performance": "UNVERIFIED",
    },
    "structure": {
        "sequence": [
            {"step": 1, "swing": "LL_first"},
            {"step": 2, "swing": "LH_between"},
            {"step": 3, "swing": "LL_second"},
        ],
        "direction": "long",
    },
    "terms": {
        "LL_first": "the lower of two consecutive swing lows",
        "LH_between": "the swing high separating them",
        "LL_second": "a swing low within tolerance of LL_first",
    },
}


def test_c4_an_unseen_contract_is_held_to_the_same_root():
    """Its own terms are all defined - and it still cannot claim MECHANICAL."""
    assert set(swing_terms_used(UNSEEN_CONTRACT)) == {
        "LL_first",
        "LH_between",
        "LL_second",
    }
    assert undefined_terms(UNSEEN_CONTRACT) == [SWING_DEFINITION]

    errors = ladder_errors(UNSEEN_CONTRACT)
    assert len(errors) == 1
    assert SWING_DEFINITION in errors[0]


def test_c4_defining_the_root_is_what_clears_it():
    """Amended by UPTM-012: defining the rule raises the next requirement.

    Before UPTM-012 this asserted that writing `swing_definition` cleared the
    contract outright. It no longer does - a mechanical rule whose parameters
    are unset is not an evaluation - so the test now asserts both steps rather
    than being relaxed to assert neither.
    """
    defined = copy.deepcopy(UNSEEN_CONTRACT)
    defined["terms"][SWING_DEFINITION] = "extreme of 5 bars either side, >= 0.25%"
    assert undefined_terms(defined) == [SWING_PARAMETERS]

    parametrised = copy.deepcopy(defined)
    parametrised["terms"][SWING_PARAMETERS] = "pivot_bars=5, min_amplitude=0.0025"
    assert undefined_terms(parametrised) == []
    assert ladder_errors(parametrised) == []


def test_c4_a_structure_that_names_no_swing_does_not_need_a_swing_definition():
    """The requirement is derived from the data, so it is absent when the data is."""
    no_swings = {
        "live_trading": False,
        "status": {axis: lowest(axis) for axis in AXES},
        "structure": {"sequence": [{"step": 1, "role": "a calendar date"}]},
        "terms": {},
    }
    assert required_terms(no_swings) == []
    assert undefined_terms(no_swings) == []


def test_c4_a_malformed_structure_yields_nothing_rather_than_raising():
    for broken in ({}, {"structure": None}, {"structure": {"sequence": "HH,HL"}}):
        assert swing_terms_used(broken) == []


# --------------------------------------------------------------------------
# C5 - the ladder holds for every axis, not for one example
# --------------------------------------------------------------------------


@pytest.mark.parametrize("index", range(1, len(AXES)))
def test_c5_no_axis_rises_while_any_earlier_axis_is_at_its_floor(index, contract):
    axis = AXES[index]
    # The ordering findings only - raising `rules` also trips the undefined-term
    # rule, and that one is C3's subject, not this one's.
    errors = [e for e in ladder_errors(_raised(contract, axis)) if "below " in e]
    # Every earlier axis is at its floor, so every one of them is named, once.
    assert len(errors) == index
    for earlier in AXES[:index]:
        assert any(
            f"status.{axis} is" in error and f"status.{earlier} is" in error
            for error in errors
        ), f"{axis} rose without {earlier} being named"


def test_c5_performance_needs_the_whole_ladder_beneath_it(contract):
    """The claim the ordering exists to forbid: a return above an untested leak."""
    claiming = copy.deepcopy(contract)
    for axis in AXES[: AXES.index("no_leakage")]:
        claiming["status"][axis] = top(axis)
    claiming["terms"][SWING_DEFINITION] = "defined for the sake of the argument"
    claiming["status"]["performance"] = "MEASURED_AFTER_COSTS"

    errors = ladder_errors(claiming)
    assert any(
        "status.performance is 'MEASURED_AFTER_COSTS'" in error
        and "status.no_leakage is 'NOT_TESTED'" in error
        for error in errors
    )


def test_c5_a_missing_axis_is_a_finding_not_a_default(contract):
    partial = copy.deepcopy(contract)
    del partial["status"]["no_leakage"]
    assert "status is missing the no_leakage axis" in ladder_errors(partial)


# --------------------------------------------------------------------------
# C6 - provenance keeps claimed apart from interpreted
# --------------------------------------------------------------------------


def test_c6_the_source_is_recorded_as_secondhand_and_unread(contract):
    provenance = contract["provenance"]
    assert provenance["primary_source_read"] is False
    assert contract["status"]["source"] == "RESTATED_SECONDHAND"
    assert provenance["claimed_by_the_source"]
    assert provenance["our_interpretation_not_the_source"]


def test_c6_the_bearish_entry_is_not_inferred_from_the_bullish_one(contract):
    """The one inference available and deliberately not taken."""
    assert contract["terms"]["entry_trigger"] == UNDEFINED
    interpretation = " ".join(contract["provenance"]["our_interpretation_not_the_source"])
    assert "retest" in interpretation


def test_c6_worked_examples_are_filed_as_illustrations_not_measurements(contract):
    not_evidence = contract["provenance"]["not_evidence"]
    assert "3R" in not_evidence["note"]
    missing = not_evidence["missing_for_any_performance_claim"]
    assert {"expectancy", "out-of-sample results"} <= set(missing)
    assert contract["status"]["performance"] == "UNVERIFIED"


# --------------------------------------------------------------------------
# C7 - the no-prediction invariant, carried forward not re-invented
# --------------------------------------------------------------------------


def test_c7_the_forbidden_list_is_the_existing_candidates_plus_the_swing_case(contract):
    hafez = json.loads(
        (CANDIDATES / "mechanical_break_retest_hafez.json").read_text(encoding="utf-8")
    )
    invariant = contract["no_prediction_principle"]
    assert invariant["rule"] == hafez["no_prediction_principle"]["rule"]
    assert set(hafez["no_prediction_principle"]["forbidden"]) <= set(
        invariant["forbidden"]
    )
    # The one this pattern adds: a swing is only a swing once later bars confirm
    # it, so a detector that labels one at the decision bar is reading ahead.
    assert any("later than the decision timestamp" in f for f in invariant["forbidden"])


# --------------------------------------------------------------------------
# C8 - the data source is an open unknown, not a detail for later
# --------------------------------------------------------------------------


def test_c8_market_data_is_recorded_as_an_open_unknown(contract):
    """Amended by UPTM-013: the map it names changed, the criterion did not.

    C8 asked that the requirement record the source as an open unknown against
    a sourcing map. It named the Revolis map because that was the only map
    there was. UPTM-013 wrote a UPTM one, so the assertion now checks that the
    map the finding names is a file that exists - which is what the criterion
    was reaching for, and stronger than the substring it used to settle for.
    """
    requirement = contract["data_requirement"]
    assert requirement["status"] == "OPEN_UNKNOWN"
    assert contract["status"]["implementation"] == "NOT_STARTED"

    named = [
        word.strip(".,")
        for word in requirement["finding"].split()
        if word.strip(".,").endswith("sourcing-map.md")
    ]
    assert named, "the finding must name the sourcing map it was measured against"
    for path in named:
        assert (ROOT / path).is_file(), f"{path} is named but does not exist"


# --------------------------------------------------------------------------
# L2 - the existing candidate is untouched by this change
# --------------------------------------------------------------------------


def test_l2_the_hafez_candidate_still_carries_its_flat_status():
    """This adds a second candidate. It does not migrate the first."""
    hafez = json.loads(
        (CANDIDATES / "mechanical_break_retest_hafez.json").read_text(encoding="utf-8")
    )
    assert hafez["status"] == "UNVERIFIED"
    assert isinstance(hafez["status"], str)


# --------------------------------------------------------------------------
# UPTM-012 - the root is defined, and the contract is still not evaluable
# --------------------------------------------------------------------------


def test_s9_the_root_is_defined_and_names_the_module_that_implements_it(contract):
    definition = contract["terms"][SWING_DEFINITION]
    assert definition != UNDEFINED
    assert "runner/swing.py" in definition
    # The two choices UPTM-012 made rather than inherited are carried in the
    # contract, not left in the spec where a reader of the data would miss them.
    assert "plateau yields no swing" in definition
    assert "never at index" in definition


def test_s9_the_four_relational_terms_are_defined_against_the_previous_same_kind(contract):
    terms = contract["terms"]
    for name in ("HH", "HL", "LL", "LH"):
        assert terms[name] != UNDEFINED
        assert "previous swing" in terms[name]


def test_s9_rules_still_cannot_move_and_the_reason_has_changed(contract):
    """The advance is real and small, and the contract has to say which."""
    assert contract["status"]["rules"] == UNDEFINED
    assert ladder_errors(contract) == []

    still_open = undefined_terms(contract)
    assert SWING_DEFINITION not in still_open
    assert SWING_PARAMETERS in still_open
    assert {"entry_trigger", "target_exit", "break_tolerance"} <= set(still_open)

    claiming = copy.deepcopy(contract)
    claiming["status"]["source"] = top("source")
    claiming["status"]["rules"] = "MECHANICAL"
    assert any(SWING_PARAMETERS in error for error in ladder_errors(claiming))


def test_s10_defining_the_rule_raises_the_requirement_for_its_parameters(contract):
    assert SWING_PARAMETERS in required_terms(contract)

    # And deleting the key does not hide it - C2's rule, applied to the term
    # that UPTM-012 put in front of the reader.
    deleted = copy.deepcopy(contract)
    del deleted["terms"][SWING_PARAMETERS]
    assert SWING_PARAMETERS in undefined_terms(deleted)


def test_s10_the_parameter_requirement_appears_only_once_the_rule_is_written():
    """Before the root is defined, the finding points at the root, not past it."""
    unwritten = copy.deepcopy(UNSEEN_CONTRACT)
    assert required_terms(unwritten) == [
        SWING_DEFINITION,
        "LL_first",
        "LH_between",
        "LL_second",
    ]
    assert SWING_PARAMETERS not in required_terms(unwritten)


def test_s9_the_contract_records_that_the_definition_is_ours_not_the_sources(contract):
    interpretation = " ".join(contract["provenance"]["our_interpretation_not_the_source"])
    assert "swing definition" in interpretation.lower()
    assert contract["status"]["source"] == "RESTATED_SECONDHAND"
