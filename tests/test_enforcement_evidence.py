"""UPTM-006 — the ENFORCED claims in capital-rules.json, checked rather than read.

Acceptance criteria preregistered in docs/specs/UPTM-006-enforcement-evidence.md
§5. The case numbers below are that document's own.

An ENFORCED claim asserts there is no route to PASS while violating the
principle. These tests take that literally: they enumerate routes, drive the
real gate down each one, and require each denial to be load-bearing.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from runner import gates
from runner.enforcement import (
    CONDITIONAL_GUARDS,
    REDUNDANT_GUARDS,
    NON_PRINCIPLE_GUARDS,
    CORRECTED_PREDICTIONS,
    ROUTES,
    evaluate_route,
    enforced_principles,
    evidence_expiry,
    evidence_expiry_days,
    expiry_status,
    manifest,
    route_guard,
    routes_for,
    run_routes,
    unproven_claims,
)
from runner.gates import evaluate_gate
from runner.paths import CAPITAL_RULES
from runner.provenance import HeadProvenance
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
    assert enforced == {"P8", "P10", "P12"}
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
    assert {r.route_id for r in routes_for("APS-001")} == {
        "PS-R1", "PS-R2", "PS-R3", "PS-R4", "PS-R5", "PS-R6", "PS-R7", "PS-R8", "PS-R9", "PS-R10",
    }
    assert "a guard nobody routes is" in NON_PRINCIPLE_GUARDS["APS-001"]


#: Every field validate_evidence_structure requires. Duplicated from the
#: implementation on purpose: this is the pin. Remove a field there and the
#: parametrised test below fails, which is the whole point — before these
#: routes existed, the required-field list could have been emptied and the only
#: thing to notice would have been PS-R1's bookkeeping about prompt_stack.
REQUIRED_EVIDENCE_FIELDS = (
    "evidence_id", "wave_id", "commit_sha", "branch", "files", "commands",
    "results", "probes", "before", "after", "agent_claim", "live_trading",
    "prompt_stack",
)


def test_the_structural_arm_is_routed_because_nothing_else_routed_it():
    """The required-field list is the other arm of validate_evidence_structure.

    Measured before these routes were written: disabling all of the required
    fields failed two tests, and both were PS-R1 bookkeeping about prompt_stack.
    The ten routes naming this guard are all prompt-stack routes and every one
    is about the binding arm, so nothing asked whether evidence with no
    commit_sha could reach PASS.
    """
    assert "EVIDENCE-STRUCTURE" in NON_PRINCIPLE_GUARDS
    assert {r.route_id for r in routes_for("EVIDENCE-STRUCTURE")} == {
        "ES-R1", "ES-R2", "ES-R3",
    }
    assert "measured unrouted" in NON_PRINCIPLE_GUARDS["EVIDENCE-STRUCTURE"]


@pytest.mark.parametrize("field", REQUIRED_EVIDENCE_FIELDS)
def test_every_required_field_is_actually_required(field, valid_evidence_factory):
    """One assertion per field, so dropping one from the list is not silent.

    The routes above prove the arm denies; this proves what it denies *for*.
    Three routes cannot cover thirteen fields without thirteen routes, and
    thirteen routes would say the same thing thirteen times — the registry is
    about mechanisms, this is about the list's contents.
    """
    import runner.evidence as evidence_module

    evidence = {k: v for k, v in valid_evidence_factory().items() if k != field}
    errors = evidence_module.validate_evidence_structure(evidence)
    assert any(f"missing field: {field}" in e for e in errors), (
        f"{field} was dropped and validate_evidence_structure did not say so: {errors}"
    )


# ------------------------------------------------- case 2: every route denies


@pytest.mark.parametrize("route", ROUTES, ids=lambda r: r.route_id)
def test_every_route_denies(route, route_root):
    result = evaluate_route(route, route_root)
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
    result = evaluate_route(route, route_root)
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
    with route_guard(route, route_root):
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
        with route_guard(route, route_root):
            monkeypatch.setattr(gates, guard, _neutral(guard))
            assert evaluate_gate(evidence).verdict is not Verdict.PASS, (
                f"{route.route_id} opened with {guard} alone neutered — it has one guard, not "
                f"{len(route.guards)}"
            )
            monkeypatch.undo()


def test_one_guard_alone_does_not_open_the_doubly_guarded_route(route_root, monkeypatch):
    r4 = next(r for r in ROUTES if r.route_id == "P8-R4")
    evidence = r4.build(route_root)
    with route_guard(r4, route_root):
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


#: A head the repository reported, not one a caller asserted. Rule A is what
#: makes that distinction real; see tests/test_evidence_rule_a.py.
READ_HEAD = HeadProvenance("a" * 40, True, "git")


def test_the_manifest_carries_a_commit_and_an_expiry_the_founder_set():
    """P12 wants both. Before 2026-09-24 the expiry was null and said why; the
    Founder then set seven days and it became a timestamp."""
    generated = datetime(2026, 9, 24, 18, 0, tzinfo=timezone.utc)
    m = manifest([], provenance=READ_HEAD, generated_at=generated)
    assert m["evaluated_head"] == "a" * 40
    assert m["expiry_days"] == 7
    assert m["expires_at"] == (generated + timedelta(days=7)).isoformat()


def test_the_expiry_is_a_timestamp_not_a_sentence():
    """It used to read "7 days from generated_at", which sounds like an expiry
    and cannot be compared to anything. An expiry nothing can evaluate is
    decorative - the same defect as a status word nobody earned."""
    generated = datetime(2026, 9, 24, 18, 0, tzinfo=timezone.utc)
    value = evidence_expiry(generated_at=generated)
    assert datetime.fromisoformat(value) == generated + timedelta(days=7)


def test_the_lifetime_is_read_from_the_rules_and_never_defaulted():
    """A missing, zero, negative, boolean or non-integer lifetime is None. The
    Founder sets it or there is none - there is no computed fallback."""
    assert evidence_expiry_days() == 7
    for bad in ({}, {"evidence_expiry_days": 0}, {"evidence_expiry_days": -3},
                {"evidence_expiry_days": True}, {"evidence_expiry_days": "7"},
                {"evidence_expiry_days": 7.5}, {"evidence_expiry_days": None}):
        assert evidence_expiry_days(bad) is None, bad
        assert evidence_expiry(bad) is None, bad


def test_expiry_status_is_three_valued_and_unknown_is_not_a_soft_valid():
    """UNKNOWN dominates PASS under runner.verdict. An artifact with no expiry,
    an unparseable one, or one with no timezone has not been shown to be
    current, so it must not read as VALID."""
    generated = datetime(2026, 9, 24, 18, 0, tzinfo=timezone.utc)
    m = manifest([], provenance=READ_HEAD, generated_at=generated)

    assert expiry_status(m, now=generated + timedelta(days=6, hours=23)) == "VALID"
    assert expiry_status(m, now=generated + timedelta(days=7, seconds=1)) == "EXPIRED"

    for opaque in ({}, {"expires_at": None}, {"expires_at": ""},
                   {"expires_at": "soon"}, {"expires_at": "2030-01-01T00:00:00"}):
        assert expiry_status(opaque, now=generated) == "UNKNOWN", opaque


def test_the_expiry_matches_the_kill_switch_drill_cadence():
    """The reason for seven rather than any other number. Evidence that outlives
    the drill it rests on is evidence propped up by a stale drill."""
    rules = json.loads(CAPITAL_RULES.read_text(encoding="utf-8"))
    assert rules["evidence_expiry_days"] == rules["live_capability"]["kill_switch_drill_cadence_days"]


def test_the_expiry_parameter_was_not_what_advanced_p12():
    """This test was written when P12 was PARTIAL, to hold the line that setting
    a Founder parameter does not earn a status. That claim is still true and is
    what is asserted here: P12 moved on 2026-09-24 because UPTM-008 gave it
    routes through the gate, not because a number was written into a file.

    The earlier assertion (P12 == PARTIAL) is gone because the fact changed, not
    because the test was in the way."""
    rules = json.loads(CAPITAL_RULES.read_text(encoding="utf-8"))
    p12 = next(p for p in rules["principles"] if p["id"] == "P12")

    assert p12["enforcement"] == "ENFORCED"
    assert "UPTM-008" in p12["earned_by"], "the status must name the wall that earned it"
    assert routes_for("P12"), "ENFORCED with no routes is the typed word UPTM-006 forbids"

    # the expiry parameter is still just a parameter: it names no route
    assert "evidence_expiry" in rules
    assert not any(r.expect.startswith("expiry") for r in ROUTES)


def test_the_manifest_states_what_it_does_not_establish():
    m = manifest([], provenance=READ_HEAD)
    assert "complete" in m["does_not_establish"]
    assert "advances no principle" in m["does_not_establish"]


def test_the_manifest_would_report_an_unearned_claim():
    assert manifest([], provenance=READ_HEAD)["unproven_claims"] == []


def test_routes_for_partitions_the_registry():
    groups = ("P8", "P10", "P12", "APS-001")
    """Every route belongs to a declared group, and the groups do not overlap.

    The group list is derived rather than frozen: a hard-coded tuple has to be
    edited whenever a group is added, and an edit made to get a test passing is
    exactly the kind that stops asserting anything. Derived, an undeclared group
    still breaks the sum — a route in no declared group is simply not counted.
    """
    groups = set(enforced_principles()) | set(NON_PRINCIPLE_GUARDS)
    assert sum(len(routes_for(g)) for g in groups) == len(ROUTES)
    assert routes_for("P9") == (), "a principle with no routes must report none"


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
        with route_guard(route, route_root):
            assert evaluate_gate(evidence).verdict is not Verdict.PASS

        monkeypatch.setattr(evidence_module, "validate_prompt_stack_binding", lambda _e: [])
        try:
            with route_guard(route, route_root):
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


def test_ps_r3_backstop_survives_removal_of_the_declared_digest_check(route_root, monkeypatch):
    """Deleting the registry comparison must not open PS-R3.

    The binding still carries the digest of the body that was assembled. A
    drifted source recomputes a different digest, so the field comparison
    denies. The route's own expect string is the declared-digest raise; this
    test keeps the backstop visible so a later edit cannot retarget that
    string at the backstop and call the raise optional.
    """
    import runner.prompt_stacks as prompt_stacks

    route = next(r for r in ROUTES if r.route_id == "PS-R3")
    evidence = route.build(route_root)
    monkeypatch.setattr(prompt_stacks, "enforce_declared_body_digest", lambda *_a, **_k: None)
    with route_guard(route, route_root):
        result = evaluate_gate(evidence)
    assert result.verdict is not Verdict.PASS
    assert any("stack_digests mismatch" in reason for reason in result.reasons)
    assert not any("prompt stack 00 digest mismatch" in reason for reason in result.reasons)


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
    assert by_id["PS-R3"]["redundant_guard"] is None
    assert by_id["PS-R3"]["denied_by_its_own_check"] is True
