"""UPTM-008 — the gate verifies the binding its evidence declares.

Criteria preregistered in docs/specs/UPTM-008-gate-verifies-its-binding.md §3.
Test names carry the criterion id, so a failure says which preregistered claim
broke rather than merely that something is red.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from runner import gates
from runner.binding import binding_errors, verify_declared_files
from runner.enforcement import _base, routes_for, unproven_claims
from runner.gates import evaluate_gate
from runner.paths import CAPITAL_RULES, ROOT
from runner.staleness import CURRENT, STALE, UNKNOWN
from runner.verdict import Verdict


def _real(path: str = "runner/gates.py") -> dict:
    return {"path": path, "sha256": hashlib.sha256((ROOT / path).read_bytes()).hexdigest()}


# ------------------------------------------------------------------ §G


def test_g1_a_true_binding_passes_and_the_gate_consults_it():
    assert verify_declared_files({"files": [_real()]}).status == CURRENT
    assert binding_errors({"files": [_real()]}) == []
    assert evaluate_gate(_base()).verdict is Verdict.PASS


def test_g2_a_changed_declared_file_denies_and_names_the_path():
    evidence = _base(files=[{"path": "runner/gates.py", "sha256": "c" * 64}])
    result = evaluate_gate(evidence)
    assert result.verdict is Verdict.FAIL
    assert any("binding STALE" in r and "runner/gates.py" in r for r in result.reasons)


def test_g3_a_missing_declared_file_is_unknown_not_stale():
    """Absence is not a measurement. Evidence naming a file that is gone has not
    been shown to describe anything, and must not be reported as a change."""
    evidence = _base(files=[{"path": "runner/no_such_module.py", "sha256": "b" * 64}])
    checked = verify_declared_files(evidence)
    assert checked.status == UNKNOWN
    assert checked.unreadable == ("runner/no_such_module.py",)
    assert checked.changed == ()
    assert evaluate_gate(evidence).verdict is Verdict.FAIL


def test_g4_the_fabricated_digest_that_passed_before_this_wall_now_denies():
    """The criterion that proves the wall. This exact evidence reached PASS on
    main at dcf77f4 - the gate required the files key to exist and never looked
    at what was in it."""
    fabricated = _base(files=[{"path": "runner/gates.py", "sha256": "a" * 64}])
    assert evaluate_gate(fabricated).verdict is Verdict.FAIL

    nonexistent = _base(files=[{"path": "no/such/file.py", "sha256": "b" * 64}])
    assert evaluate_gate(nonexistent).verdict is Verdict.FAIL


def test_g5_evidence_bound_to_nothing_denies():
    """P12 binds a PASS to a precisely identified state. An empty list is not a
    state, and a permissive reading of it would make every other criterion here
    trivially avoidable."""
    assert verify_declared_files({"files": []}).status == UNKNOWN
    assert evaluate_gate(_base(files=[])).verdict is Verdict.FAIL


@pytest.mark.parametrize(
    "entry",
    [
        "runner/gates.py",                                     # not an object
        {"sha256": "a" * 64},                                  # no path
        {"path": "runner/gates.py"},                           # no sha256
        {"path": "runner/gates.py", "sha256": "not-a-digest"}, # not a digest
        {"path": "runner/gates.py", "sha256": "A" * 64},       # not lowercase hex
        {"path": "", "sha256": "a" * 64},                      # empty path
    ],
)
def test_g6_a_malformed_entry_denies_rather_than_being_skipped(entry):
    """A check that silently ignores what it cannot parse is not a check, and
    unparseable is the easiest thing for a caller to produce on purpose."""
    assert verify_declared_files({"files": [entry]}).status == UNKNOWN
    assert evaluate_gate(_base(files=[entry])).verdict is Verdict.FAIL


def test_g7_the_gate_actually_calls_the_binding_check(monkeypatch):
    """Spy. A correct check nothing calls enforces nothing - UPTM-002c."""
    seen: list[dict] = []

    def spy(evidence, root=None):
        seen.append(evidence)
        return []

    monkeypatch.setattr(gates, "binding_errors", spy)
    evaluate_gate(_base())
    assert seen, "evaluate_gate never called the binding check"


def test_g7_neutering_the_binding_check_opens_a_denying_gate(monkeypatch):
    """Mutation. With the guard removed the fabricated binding must reach PASS
    again - which is how we know the denial was this check's doing and not some
    other check's side effect."""
    fabricated = _base(files=[{"path": "runner/gates.py", "sha256": "a" * 64}])
    assert evaluate_gate(fabricated).verdict is Verdict.FAIL

    monkeypatch.setattr(gates, "binding_errors", lambda evidence, root=None: [])
    assert evaluate_gate(fabricated).verdict is Verdict.PASS, (
        "the gate still denies without the binding check - the denial is not its doing"
    )


# ------------------------------------------------------------------ §R


def test_r1_p12_has_a_route_per_violation_shape_each_denying_by_its_own_check():
    routes = routes_for("P12")
    assert {r.route_id for r in routes} == {"P12-R1", "P12-R2", "P12-R3", "P12-R4", "P12-R5"}
    for route in routes:
        outcome = evaluate_gate(route.build(Path("/nonexistent")))
        assert outcome.verdict is not Verdict.PASS, route.route_id
        assert any(route.expect in reason for reason in outcome.reasons), (
            f"{route.route_id} denied, but not via {route.expect}: {outcome.reasons}"
        )


def test_r2_p12_is_not_named_as_an_unproven_claim():
    assert "P12" not in unproven_claims()


def test_r3_the_existing_routes_still_deny_for_their_own_reasons(tmp_path):
    """The fixtures carried a fabricated digest. Once the gate checks bindings,
    a route denied by its binding rather than by the guard it names would make
    every proof in UPTM-006 pass for the wrong reason."""
    for group in ("P8", "P10", "APS-001"):
        for route in routes_for(group):
            evidence = route.build(tmp_path)
            declared = evidence.get("files")
            assert isinstance(declared, list) and declared, route.route_id
            assert verify_declared_files(evidence).status == CURRENT, (
                f"{route.route_id} would now deny on its binding, not on {route.expect}"
            )


# ------------------------------------------------------------------ §C


def test_c3_no_other_principle_moved_and_live_trading_stays_false():
    rules = json.loads(CAPITAL_RULES.read_text(encoding="utf-8"))
    assert rules["live_capability"]["default"] == "DENY"
    assert rules["live_capability"]["lease"]["granted"] is False
    for pid in ("P8", "P10"):
        assert next(p["enforcement"] for p in rules["principles"] if p["id"] == pid) == "ENFORCED"
