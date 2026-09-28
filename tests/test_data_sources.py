"""UPTM-013: a source that has been described must not read as one we have.

Criteria are preregistered in `docs/specs/UPTM-013-es-mes-data-sourcing.md`,
written before this file existed. Each test names the criterion it discharges.

**No test here opens a socket** (L2). Nothing reads market data, and nothing
builds a detector or a backtest - the module under test is what refuses to let
any of that happen while the source is unconnected.
"""

from __future__ import annotations

import copy
import json

import pytest

from runner.data_sources import (
    CONNECTED,
    SOURCES,
    STATES,
    load_source,
    may_run_detector,
    open_founder_tasks,
    source_path,
    state_errors,
)
from runner.paths import ROOT

CONTRACT = ROOT / "research" / "candidates" / "reversal" / "bearish_quasimodo.json"

# A record this spec has never seen: not ES, not futures, not in the repository.
UNSEEN_SOURCE = {
    "source_id": "invented_for_this_test",
    "connection_state": "MAPPED_UNVERIFIED",
    "map_document": "docs/architecture/uptm-data-sourcing-map.md",
    "candidates": [
        {
            "id": "vendor_a",
            "terms_verified": False,
            "verification": {"question": "What does it cost?", "url": "https://example.invalid/a"},
        },
        {
            "id": "vendor_b",
            "terms_verified": True,
            "verified_how": "Read the pricing page on 2026-09-28.",
            "verification": {"question": "What does it cost?", "url": "https://example.invalid/b"},
        },
    ],
}


@pytest.fixture()
def source() -> dict:
    return load_source("es_mes_bars")


@pytest.fixture()
def contract() -> dict:
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------
# D1 - the state is a rung, not a word
# --------------------------------------------------------------------------


def test_d1_the_record_sits_on_a_real_rung_and_is_otherwise_clean(source):
    assert source["connection_state"] in STATES
    assert source["connection_state"] == "MAPPED_UNVERIFIED"
    assert state_errors(source) == []


def test_d1_an_invented_state_is_named_and_rejected(source):
    forged = copy.deepcopy(source)
    forged["connection_state"] = "AVAILABLE"
    errors = state_errors(forged)
    assert len(errors) == 1
    assert "'AVAILABLE'" in errors[0]


def test_d1_a_missing_state_is_not_a_default(source):
    forged = copy.deepcopy(source)
    del forged["connection_state"]
    assert state_errors(forged) == [
        f"connection_state is None, which is not a rung of {list(STATES)}"
    ]


# --------------------------------------------------------------------------
# D2 - the expensive rung costs evidence
# --------------------------------------------------------------------------


def test_d2_connected_without_evidence_is_an_error_not_a_pass(source):
    claiming = copy.deepcopy(source)
    claiming["connection_state"] = CONNECTED
    errors = state_errors(claiming)
    assert len(errors) == 2
    assert any("evidence.artifact" in error for error in errors)
    assert any("evidence.commit" in error for error in errors)


@pytest.mark.parametrize("missing", ["artifact", "commit"])
def test_d2_half_the_evidence_is_not_evidence(source, missing):
    claiming = copy.deepcopy(source)
    claiming["connection_state"] = CONNECTED
    claiming["evidence"] = {"artifact": "evidence/feed.json", "commit": "abc1234"}
    claiming["evidence"][missing] = "   "
    errors = state_errors(claiming)
    assert len(errors) == 1
    assert f"evidence.{missing}" in errors[0]


def test_d2_connected_with_evidence_is_accepted(source):
    """The gate must be passable, or it is not a gate but a wall."""
    connected = copy.deepcopy(source)
    connected["connection_state"] = CONNECTED
    connected["evidence"] = {"artifact": "evidence/feed-probe.json", "commit": "abc1234"}
    assert state_errors(connected) == []
    assert may_run_detector(connected) is True


# --------------------------------------------------------------------------
# D3 - Directive 4, mechanically: no number from an unconnected source
# --------------------------------------------------------------------------


@pytest.mark.parametrize("rung", [rung for rung in STATES if rung != CONNECTED])
def test_d3_every_rung_below_connected_refuses_the_detector(source, rung):
    """Asserted for every rung, so a new one cannot be added permissively."""
    candidate = copy.deepcopy(source)
    candidate["connection_state"] = rung
    assert may_run_detector(candidate) is False


def test_d3_the_real_record_refuses_today(source):
    assert may_run_detector(source) is False


def test_d3_a_malformed_record_cannot_read_as_connected(source):
    """Fail-closed both ways: the part that would prove it is the part that broke."""
    broken = copy.deepcopy(source)
    broken["connection_state"] = CONNECTED
    broken["evidence"] = {"artifact": "evidence/feed.json", "commit": "abc1234"}
    broken["map_document"] = "docs/architecture/does-not-exist.md"
    assert state_errors(broken) != []
    assert may_run_detector(broken) is False


# --------------------------------------------------------------------------
# D4 - derived, not typed
# --------------------------------------------------------------------------


def test_d4_the_task_list_is_read_out_of_the_candidates(source):
    tasks = open_founder_tasks(source)
    unverified = [c for c in source["candidates"] if not c.get("terms_verified")]
    assert len(tasks) == len(unverified) == 4
    for candidate in unverified:
        assert any(candidate["id"] in task for task in tasks)
        assert any(candidate["verification"]["url"] in task for task in tasks)


def test_d4_an_unseen_record_yields_a_task_only_for_what_is_unverified():
    tasks = open_founder_tasks(UNSEEN_SOURCE)
    assert len(tasks) == 1
    assert "vendor_a" in tasks[0]
    assert "vendor_b" not in tasks[0]


def test_d4_adding_a_candidate_adds_its_task_and_verifying_it_removes_it():
    grown = copy.deepcopy(UNSEEN_SOURCE)
    grown["candidates"].append(
        {
            "id": "vendor_c",
            "terms_verified": False,
            "verification": {"question": "Any history?", "url": "https://example.invalid/c"},
        }
    )
    assert len(open_founder_tasks(grown)) == 2

    grown["candidates"][-1]["terms_verified"] = True
    grown["candidates"][-1]["verified_how"] = "Read it."
    assert len(open_founder_tasks(grown)) == 1


def test_d4_a_record_with_no_candidates_has_no_tasks_rather_than_raising():
    for empty in ({}, {"candidates": None}, {"candidates": []}):
        assert open_founder_tasks(empty) == []


# --------------------------------------------------------------------------
# D5 - a claim of verification must name how
# --------------------------------------------------------------------------


def test_d5_every_candidate_carries_a_question_and_a_url(source):
    for candidate in source["candidates"]:
        assert candidate["verification"]["question"].strip()
        assert candidate["verification"]["url"].startswith("https://")
        # Nothing was reachable from here, so nothing may claim otherwise.
        assert candidate["terms_verified"] is False


def test_d5_every_candidate_carries_the_uptm_014_disqualifier(source):
    """The question that can rule a vendor out on its own.

    It did not exist when the four questions were written. A checklist without
    it compares prices between options, one of which cannot be used at all - so
    it is asserted on every candidate rather than left to whoever asks to
    remember it.
    """
    criterion = source["disqualifying_criterion"]
    assert criterion["added_by"].startswith("UPTM-014")
    assert criterion["acceptable_answers"]

    for candidate in source["candidates"]:
        verification = candidate["verification"]
        assert "raw per-contract" in verification["also_must_answer"].lower()
        assert "back-adjusted" in verification["disqualifying_answer"]


def test_d5_verified_by_nobody_is_not_verified(source):
    claiming = copy.deepcopy(source)
    claiming["candidates"][0]["terms_verified"] = True
    errors = state_errors(claiming)
    assert len(errors) == 1
    assert "verified_how" in errors[0]

    claiming["candidates"][0]["verified_how"] = "Read the DataMine page on 2026-10-01."
    assert state_errors(claiming) == []


def test_d5_a_candidate_without_a_verification_block_is_an_error(source):
    claiming = copy.deepcopy(source)
    del claiming["candidates"][1]["verification"]
    errors = state_errors(claiming)
    assert len(errors) == 1
    assert "no verification block" in errors[0]


# --------------------------------------------------------------------------
# D6 - the pointer is checked, not assumed
# --------------------------------------------------------------------------


def test_d6_the_map_document_exists_where_the_record_says(source):
    assert (ROOT / source["map_document"]).is_file()
    assert source_path("es_mes_bars").is_file()


def test_d6_a_dangling_pointer_is_reported(source):
    dangling = copy.deepcopy(source)
    dangling["map_document"] = "docs/architecture/not-written-yet.md"
    errors = state_errors(dangling)
    assert len(errors) == 1
    assert "does not exist" in errors[0]


def test_d6_every_source_record_in_the_tree_is_valid():
    """Not only the one this spec wrote."""
    records = sorted(SOURCES.glob("*.json"))
    assert records, "the sourcing directory must not be empty"
    for path in records:
        record = json.loads(path.read_text(encoding="utf-8"))
        assert state_errors(record) == [], f"{path.name} is not a valid source record"


# --------------------------------------------------------------------------
# D7 - consistency, both ways
# --------------------------------------------------------------------------


def test_d7_the_contract_and_the_source_cannot_disagree(source, contract):
    """A biconditional, so connecting the source later fails here rather than
    leaving the contract's prose quietly stale."""
    requirement = contract["data_requirement"]
    assert requirement["source_id"] == source["source_id"]
    assert (ROOT / requirement["source_record"]).is_file()

    connected = may_run_detector(source)
    open_unknown = requirement["status"] == "OPEN_UNKNOWN"
    assert open_unknown is not connected
    if not connected:
        assert contract["status"]["implementation"] == "NOT_STARTED"


def test_d7_the_contract_no_longer_claims_the_source_is_unmapped(contract):
    """UPTM-011's finding was true then and is false now; it had to change."""
    finding = contract["data_requirement"]["finding"]
    assert "uptm-data-sourcing-map.md" in finding
    assert "MAPPED_UNVERIFIED" in finding
    assert "Written down is not obtained" in finding


# --------------------------------------------------------------------------
# D8 - the limitation this was built under is in the artifact
# --------------------------------------------------------------------------


def test_d8_the_egress_denial_is_recorded_with_its_hosts_and_date(source):
    limitation = source["environment_limitation"]
    assert limitation["date"] == "2026-09-28"
    assert set(limitation["denied_hosts"]) == {"databento.com", "www.cmegroup.com"}
    assert "were read from a primary source" in limitation["consequence"]
    assert "lead, not a term sheet" in limitation["what_was_readable"]


def test_d8_the_licence_regime_is_recorded_as_the_binding_constraint(source):
    regime = source["legal_regime"]
    assert "licensing" in regime["binding_constraint"].lower()
    assert "no personal data" in regime["why_not_gdpr"]
    # Directive 5 names a skill that does not exist. Said, not skipped.
    assert "does not exist" in regime["directive_5_note"]
    # The distinction that decides a future Revolis-facing feature.
    assert any("derived" in p for p in regime["permissions_that_are_not_the_same_thing"])


def test_d8_the_roll_rule_is_recorded_as_an_open_modelling_choice(source):
    """Amended by UPTM-014: the family is settled, the parameters are not.

    D8 asked that the roll rule be recorded as an open modelling choice rather
    than a data question. It still is - UPTM-014 ruled out the joins that
    reprice published bars and left the trigger and the remaining pick open, so
    the assertion now checks that shape instead of the single word it had.
    """
    roll = source["open_modelling_choice_not_a_data_question"]
    assert roll["status"] == "FAMILY_DEFINED_PARAMETERS_UNSET"
    assert "construction" in roll["why_it_matters"]
    assert roll["admissible"] and roll["inadmissible"]
    assert roll["still_open"], "settling the family must not close the parameters"
    assert "UNDEFINED" in roll["carried_in_the_contract_as"]
