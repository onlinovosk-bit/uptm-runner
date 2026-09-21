"""UPTM-002 preregistration integrity.

The detector does not exist yet. These tests guard the preregistration itself, so that
the acceptance criteria cannot drift once evidence starts arriving (CC/P4), and so that
writing the specification cannot be mistaken for enforcing it (CC/P9).
"""

from __future__ import annotations

import json

from runner.paths import CAPITAL_RULES, ROOT

SPEC_JSON = ROOT / "docs" / "specs" / "UPTM-002-fabrication-stop-conditions.json"
SPEC_MD = ROOT / "docs" / "specs" / "UPTM-002-fabrication-stop-conditions.md"


def _spec() -> dict:
    return json.loads(SPEC_JSON.read_text(encoding="utf-8"))


def _cases(spec: dict) -> list[dict]:
    return [c for group in spec["acceptance_cases"].values() for c in group]


def test_spec_documents_exist():
    assert SPEC_MD.is_file()
    assert SPEC_JSON.is_file()


def test_missing_parameter_never_resolves_to_pass():
    """The spine of the spec: an undeclared parameter buys UNKNOWN, never a pass."""
    assert _spec()["missing_parameter_verdict"] == "UNKNOWN"


def test_every_required_parameter_has_an_unknown_acceptance_case():
    """A required parameter with no missing-param case is an untested path."""
    spec = _spec()
    required = {
        (c["id"], param) for c in spec["checks"] for param in c["required_params"]
    }
    covered = {
        (c["check"], c["missing_param"]) for c in spec["acceptance_cases"]["must_unknown"]
    }
    assert not (required - covered), f"required params with no UNKNOWN case: {sorted(required - covered)}"


def test_acceptance_case_ids_are_unique():
    ids = [c["id"] for c in _cases(_spec())]
    assert len(ids) == len(set(ids))


def test_every_acceptance_case_targets_a_declared_check():
    spec = _spec()
    known = {c["id"] for c in spec["checks"]}
    for case in _cases(spec):
        assert case["check"] in known, case


def test_every_check_has_at_least_one_acceptance_case():
    spec = _spec()
    exercised = {c["check"] for c in _cases(spec)}
    missing = {c["id"] for c in spec["checks"]} - exercised
    assert not missing, f"checks with no acceptance case: {sorted(missing)}"


def test_false_positive_protection_is_preregistered():
    """Relaxations (flat prices, zero fees) must come with cases proving they pass."""
    assert len(_spec()["acceptance_cases"]["must_pass"]) >= 5


def test_target_is_partial_and_cannot_be_upgraded_by_green_tests():
    spec = _spec()
    assert spec["target_capability"] == "PARTIAL"
    assert spec["upgrade_by_green_tests_forbidden"] is True
    assert spec["upgrade_to_enforced_requires"]


def test_limits_are_declared_before_implementation():
    assert len(_spec()["declared_limits"]) >= 4


def test_preregistration_does_not_change_capability_status():
    """Writing a specification is not enforcement: the stop conditions stay DECLARATIVE."""
    spec = _spec()
    assert spec["detector_exists"] is False
    status = json.loads(CAPITAL_RULES.read_text(encoding="utf-8"))["control_plane_stop_condition_status"]
    for condition in spec["stop_conditions"]:
        assert status[condition] == "DECLARATIVE", (
            f"{condition} was upgraded without a detector"
        )
