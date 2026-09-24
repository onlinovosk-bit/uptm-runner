"""UPTM-006 — the ENFORCED claims in capital-rules.json, checked rather than read.

Acceptance criteria preregistered in docs/specs/UPTM-006-enforcement-evidence.md
§5. The case numbers below are that document's own.

An ENFORCED claim asserts there is no route to PASS while violating the
principle. These tests take that literally: they enumerate routes, drive the
real gate down each one, and require each denial to be load-bearing.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from runner import gates
from runner.enforcement import (
    CONDITIONAL_GUARDS,
    REDUNDANT_GUARDS,
    NON_PRINCIPLE_GUARDS,
    CORRECTED_PREDICTIONS,
    ROUTES,
    apply_stubs,
    enforced_principles,
    evidence_expiry,
    manifest,
    routes_for,
    run_routes,
    unproven_claims,
)
from runner.gates import evaluate_gate
from runner.verdict import Decision, Verdict, resolve


def _neutral(guard: str):
    """A guard that has stopped guarding, in the shape the gate expects."""
    if guard.startswith("run_"):
        return lambda *args, **kwargs: (Verdict.PASS, [])
    return lambda *args, **kwargs: False


@pytest.fixture
def route_root(tmp_path):
    return tmp_path


# ----------------------------------------------------- case 1: the claim gate


def test_every_enforced_claim_has_routes():
    """The inversion this wall exists for.

    ENFORCED stops being a word typed into a file: a principle claiming it with
    no enumerated routes fails here, and the claim cannot be made by editing
    the table alone.
    """
    unproven = unproven_claims()
    assert not unproven, (
        f"capital-rules.json claims ENFORCED for {unproven} with no routes registered in "
        "runner/enforcement.py — the claim is unearned"
    )


def test_the_claim_gate_would_actually_fire():
    """A guard that cannot fail is not a guard (CC/P9)."""
    fabricated = {"principles": [{"id": "P99", "enforcement": "ENFORCED"}]}
    assert unproven_claims(fabricated) == ["P99"]


def test_every_enforced_principle_is_covered_and_every_extra_group_is_declared():
    """The claim gate stays exact while the registry carries more than principles.

    A guard that protects no ENFORCED principle is not demanded by the claim
    gate, so it would otherwise go unrouted — remove it and nothing notices.
    Such groups are allowed here, but only if they are declared, so the
    registry cannot quietly acquire a category nobody named.
    """
    enforced = set(enforced_principles())
    assert enforced == {"P8", "P10"}
    covered = {r.principle for r in ROUTES}
    assert enforced <= covered

    extra = covered - enforced
    assert extra == set(NON_PRINCIPLE_GUARDS), (
        f"route groups that are neither a principle nor declared: "
        f"{sorted(extra - set(NON_PRINCIPLE_GUARDS))}"
    )


def test_the_prompt_stack_guard_is_routed_because_nothing_else_routes_it():
    """APS-001 made the prompt-stack binding mandatory and added no route.

    Removing that check would not have failed a single one of the seventeen
    P8/P10 routes, because their fixtures carry a valid binding. This is the
    gap those two routes close.
    """
    assert "APS-001" in NON_PRINCIPLE_GUARDS
    assert {r.route_id for r in routes_for("APS-001")} == {"PS-R1", "PS-R2"}
    assert "a guard nobody routes is" in NON_PRINCIPLE_GUARDS["APS-001"]


# ------------------------------------------------- case 2: every route denies


@pytest.mark.parametrize("route", ROUTES, ids=lambda r: r.route_id)
def test_every_route_denies(route, route_root):
    with apply_stubs(route.stubs):
        result = evaluate_gate(route.build(route_root))
    assert result.verdict is not Verdict.PASS, (
        f"{route.route_id} reached PASS: {route.description}"
    )
    assert resolve(result.verdict) is Decision.DENY


@pytest.mark.parametrize(
    "route", [r for r in ROUTES if r.blocked_by is None], ids=lambda r: r.route_id
)
def test_every_route_denies_for_its_own_reason(route, route_root):
    """A route that denies for an unrelated reason proves nothing about itself.

    This is the assertion that stops the proof quietly decaying: the surrounding
    evidence could rot, every route would still deny, and only this notices.
    """
    with apply_stubs(route.stubs):
        result = evaluate_gate(route.build(route_root))
    assert any(route.expect in reason for reason in result.reasons), (
        f"{route.route_id} denied, but not via {route.expect}: {result.reasons}"
    )


# ------------------------------------------- case 3: every denial is load-bearing


@pytest.mark.parametrize("route", ROUTES, ids=lambda r: r.route_id)
def test_every_named_guard_exists(route):
    """Case 4 of the spec: a route naming a guard that is not there."""
    for guard in route.guards:
        assert hasattr(gates, guard), f"{route.route_id} names a missing guard: {guard}"


@pytest.mark.parametrize(
    "route", [r for r in ROUTES if r.blocked_by is None], ids=lambda r: r.route_id
)
def test_neutering_the_named_guards_opens_the_route(route, route_root, monkeypatch):
    """Remove the guards and the route must reach PASS.

    If it still denies, something else is doing the work and the route names the
    wrong guard — which would make the evidence describe a mechanism that is not
    the one enforcing the principle.
    """
    evidence = route.build(route_root)
    with apply_stubs(route.stubs):
        assert evaluate_gate(evidence).verdict is not Verdict.PASS

        for guard in route.guards:
            monkeypatch.setattr(gates, guard, _neutral(guard))
        assert evaluate_gate(evidence).verdict is Verdict.PASS, (
            f"{route.route_id} still denies with {list(route.guards)} neutered — "
            "the denial comes from somewhere else"
        )


def test_the_doubly_guarded_routes_are_recorded_as_such():
    """"How many independent things would have to fail" is the question a reader
    actually has, so the count is data rather than prose."""
    doubled = {r.route_id for r in ROUTES if len(r.guards) > 1}
    assert doubled == {"P8-R2", "P8-R4", "P10-R2"}


def test_no_guard_is_currently_conditional():
    """The one entry this held was a prediction, and it was wrong. See below."""
    assert CONDITIONAL_GUARDS == {}


def test_the_refuted_prediction_is_kept_in_the_record():
    """A wall built on "claims must be checked" does not get to delete its own
    failed claim. It was written into the spec, into capital-rules.json, into a
    PR body and into a message to the Founder; deleting it quietly would be the
    fabrication this module exists to catch, turned inward."""
    entry = CORRECTED_PREDICTIONS["P10-R2-conditional-guard"]
    assert "MEASURED AFTER SETTING IT: false" in entry
    assert "VC-P2" in entry


@pytest.mark.parametrize(
    "route", [r for r in ROUTES if len(r.guards) > 1], ids=lambda r: r.route_id
)
def test_neither_guard_alone_opens_a_doubly_guarded_route(route, route_root, monkeypatch):
    """The stronger form of the count: two guards means two, measured one at a time."""
    evidence = route.build(route_root)
    for guard in route.guards:
        with apply_stubs(route.stubs):
            monkeypatch.setattr(gates, guard, _neutral(guard))
            assert evaluate_gate(evidence).verdict is not Verdict.PASS, (
                f"{route.route_id} opened with {guard} alone neutered — it has one guard, not "
                f"{len(route.guards)}"
            )
            monkeypatch.undo()


def test_one_guard_alone_does_not_open_the_doubly_guarded_route(route_root, monkeypatch):
    r4 = next(r for r in ROUTES if r.route_id == "P8-R4")
    evidence = r4.build(route_root)
    with apply_stubs(r4.stubs):
        monkeypatch.setattr(gates, "run_kill_switch_detectors", _neutral("run_kill_switch_detectors"))
        assert evaluate_gate(evidence).verdict is not Verdict.PASS, (
            "the KS-I3b invariant did not hold once the detector was removed"
        )


# --------------------------------------------------- the blocked route, stated


def test_nothing_is_blocked_now_that_the_tranche_is_set():
    """P10-R5 was blocked while validation_capital was unset: VC-P1 denied every
    capital gate before VC-R1 could be reached, so its own guard could not be
    shown to be load-bearing. Setting the tranche unblocked it, and it now
    denies via VC-R1 like any other route."""
    assert [r.route_id for r in ROUTES if r.blocked_by is not None] == []
    r5 = next(r for r in ROUTES if r.route_id == "P10-R5")
    assert r5.expect == "VC-R1"


def test_the_ceiling_itself_has_routes():
    """Before the tranche was set there was no ceiling to step over, so no route
    could test one. These are the routes that only became possible on 2026-09-23."""
    expected = {"VC-I2", "VC-I3", "VC-I4", "VC-P1", "VC-R1", "VC-R2"}
    assert expected <= {r.expect for r in ROUTES}


# ------------------------------------------------------------- case 7: manifest


def test_the_manifest_carries_a_commit_and_no_invented_expiry():
    m = manifest([], commit="abc1234")
    assert m["commit"] == "abc1234"
    assert m["expires_at"] is None
    assert "no evidence lifetime is preregistered" in m["expiry_note"].lower()
    assert evidence_expiry() is None


def test_the_manifest_states_what_it_does_not_establish():
    m = manifest([], commit="abc1234")
    assert "complete" in m["does_not_establish"]
    assert "advances no principle" in m["does_not_establish"]


def test_the_manifest_would_report_an_unearned_claim():
    assert manifest([], commit="abc1234")["unproven_claims"] == []


def test_routes_for_partitions_the_registry():
    groups = ("P8", "P10", "APS-001")
    assert sum(len(routes_for(g)) for g in groups) == len(ROUTES)
    assert routes_for("P12") == ()


def test_the_binding_check_itself_is_what_holds_the_prompt_stack_routes(
    route_root, monkeypatch
):
    """`validate_evidence_structure` is the seam these routes name, but it does
    more than one thing. Neuter only the binding validator inside it and a route
    held by the binding alone must open — otherwise it is held by the
    surrounding structural checks and names the wrong guard.

    PS-R1 does not open, and that is recorded rather than excused: dropping the
    key trips the required-field list as well, so the route is held twice over.
    The test asserts the measurement in both directions, so that a future change
    which removes either mechanism shows up here."""
    import runner.evidence as evidence_module

    for route in routes_for("APS-001"):
        evidence = route.build(route_root)
        assert evaluate_gate(evidence).verdict is not Verdict.PASS

        monkeypatch.setattr(evidence_module, "validate_prompt_stack_binding", lambda _e: [])
        try:
            outcome = evaluate_gate(evidence)
            if route.route_id in REDUNDANT_GUARDS:
                assert outcome.verdict is not Verdict.PASS, (
                    f"{route.route_id} is recorded as held by a second mechanism, but "
                    "neutering the binding validator opened it — the record is stale"
                )
                assert any("missing field: prompt_stack" in r for r in outcome.reasons), (
                    f"{route.route_id} still denies, but not via the required-field list "
                    f"the record names: {outcome.reasons}"
                )
            else:
                assert outcome.verdict is Verdict.PASS, (
                    f"{route.route_id} still denies with only the binding validator "
                    f"neutered — it is held by something else: {outcome.reasons}"
                )
        finally:
            monkeypatch.undo()


def test_each_mechanism_holding_ps_r1_denies_on_its_own():
    """The redundancy recorded for PS-R1 is two independent denials, not one
    denial counted twice. Called directly, each check refuses the route by
    itself."""
    import runner.evidence as evidence_module
    from runner.prompt_stacks import validate_prompt_stack_binding

    evidence = next(r for r in ROUTES if r.route_id == "PS-R1").build(Path("/nonexistent"))

    structural = evidence_module.validate_evidence_structure(evidence)
    assert any("missing field: prompt_stack" in e for e in structural)
    assert validate_prompt_stack_binding(evidence) == ["prompt_stack binding required"]

    assert "PS-R1" in REDUNDANT_GUARDS
    assert "twice over" in REDUNDANT_GUARDS["PS-R1"]


def test_the_manifest_reports_a_redundant_guard_rather_than_hiding_it(route_root):
    """A second guard that only lives in a comment is a second guard nobody
    auditing the artifact can see."""
    results = run_routes(route_root)
    by_id = {r["route_id"]: r for r in results}
    assert by_id["PS-R1"]["redundant_guard"] == REDUNDANT_GUARDS["PS-R1"]
    assert by_id["PS-R2"]["redundant_guard"] is None
