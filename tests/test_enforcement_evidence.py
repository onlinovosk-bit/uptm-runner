"""UPTM-006 — the ENFORCED claims in capital-rules.json, checked rather than read.

Acceptance criteria preregistered in docs/specs/UPTM-006-enforcement-evidence.md
§5. The case numbers below are that document's own.

An ENFORCED claim asserts there is no route to PASS while violating the
principle. These tests take that literally: they enumerate routes, drive the
real gate down each one, and require each denial to be load-bearing.
"""

from __future__ import annotations

import pytest

from runner import gates
from runner.enforcement import (
    CONDITIONAL_GUARDS,
    ROUTES,
    apply_stubs,
    enforced_principles,
    evidence_expiry,
    manifest,
    routes_for,
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


def test_both_enforced_principles_are_the_ones_covered():
    assert set(enforced_principles()) == {"P8", "P10"}
    assert {r.principle for r in ROUTES} == {"P8", "P10"}


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


def test_a_conditional_second_guard_is_named_as_conditional():
    """P10-R2's second guard is not a mechanism, it is a circumstance.

    run_validation_capital_detectors denies it only because the tranche is
    unset. The day the Founder sets validation_capital, that guard falls away
    and SC-I3 holds the route alone — the count drops from two to one with no
    code change at all. A reassuring number that quietly decays is worse than
    no number.
    """
    assert set(CONDITIONAL_GUARDS) == {"P10-R2"}
    assert "Setting the tranche removes that guard" in CONDITIONAL_GUARDS["P10-R2"]
    assert len(next(r for r in ROUTES if r.route_id == "P10-R2").guards) == 2


def test_one_guard_alone_does_not_open_the_doubly_guarded_route(route_root, monkeypatch):
    r4 = next(r for r in ROUTES if r.route_id == "P8-R4")
    evidence = r4.build(route_root)
    with apply_stubs(r4.stubs):
        monkeypatch.setattr(gates, "run_kill_switch_detectors", _neutral("run_kill_switch_detectors"))
        assert evaluate_gate(evidence).verdict is not Verdict.PASS, (
            "the KS-I3b invariant did not hold once the detector was removed"
        )


# --------------------------------------------------- the blocked route, stated


def test_the_blocked_route_still_denies_and_says_why(route_root):
    """P10-R5 cannot demonstrate its own guard while the tranche is unset.

    It is kept, it denies, and the manifest reports it as blocked. Relabelling
    it to whatever happens to fire would be the fabrication this repository
    builds detectors against."""
    blocked = [r for r in ROUTES if r.blocked_by is not None]
    assert [r.route_id for r in blocked] == ["P10-R5"]
    route = blocked[0]
    assert "validation_capital is unset" in route.blocked_by
    with apply_stubs(route.stubs):
        assert evaluate_gate(route.build(route_root)).verdict is not Verdict.PASS


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
    assert len(routes_for("P8")) + len(routes_for("P10")) == len(ROUTES)
    assert routes_for("P12") == ()
