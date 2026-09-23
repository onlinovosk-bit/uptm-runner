"""UPTM-003 preregistration integrity.

These tests guard the preregistration itself, so that the acceptance criteria
cannot drift once evidence starts arriving (CC/P4), and so that writing the
specification — or a detector, or a green suite — cannot be mistaken for
enforcing P8 (CC/P9).
"""

from __future__ import annotations

import json

from runner.gates import _kill_switch_stop_conditions
from runner.paths import CAPITAL_RULES, UPTM003_SPEC

SPEC_MD = UPTM003_SPEC.with_suffix(".md")


def _spec() -> dict:
    return json.loads(UPTM003_SPEC.read_text(encoding="utf-8"))


def _rules() -> dict:
    return json.loads(CAPITAL_RULES.read_text(encoding="utf-8"))


def _cases(spec: dict) -> list[dict]:
    return [c for group in spec["acceptance_cases"].values() for c in group]


def test_spec_documents_exist():
    assert SPEC_MD.is_file()
    assert UPTM003_SPEC.is_file()


def test_missing_parameter_never_resolves_to_pass():
    """The spine of the spec: an undeclared parameter buys UNKNOWN, never a pass."""
    assert _spec()["missing_parameter_verdict"] == "UNKNOWN"


def test_a_live_claim_without_a_pack_is_unknown():
    """Omission is closed on the one path P8 exists to protect."""
    assert _spec()["live_claim_without_pack_verdict"] == "UNKNOWN"


def test_every_required_parameter_has_an_unknown_acceptance_case():
    spec = _spec()
    required = {
        (c["id"], param) for c in spec["checks"] for param in c["required_params"]
    }
    covered = {
        (c["check"], c["missing_param"]) for c in spec["acceptance_cases"]["must_unknown"]
    }
    assert not (required - covered), (
        f"required params with no UNKNOWN case: {sorted(required - covered)}"
    )


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
    """Relaxations (declared-empty write paths, boundary cadence) need passing cases."""
    assert len(_spec()["acceptance_cases"]["must_pass"]) >= 5


def test_limits_are_declared_before_implementation():
    assert len(_spec()["declared_limits"]) >= 4


def test_deployment_independence_is_not_claimed_by_code():
    """The founder's boundary, kept in the artifact the tests read."""
    limits = _spec()["declared_limits"]
    assert "deployment_independence_not_certified_by_code" in limits
    assert "attestation" in limits["deployment_independence_not_certified_by_code"]


def test_target_is_partial_and_cannot_be_upgraded_by_green_tests():
    spec = _spec()
    assert spec["target_capability"] == "PARTIAL"
    assert spec["upgrade_by_green_tests_forbidden"] is True
    assert spec["upgrade_to_enforced_requires"]


# ------------------------------------------------- the artifact is the source


def test_the_cadence_is_declared_in_the_governance_artifact():
    """14 days is a founder decision recorded in capital-rules.json, not a constant
    in code. A detector that carried its own cadence would be inventing a safety
    parameter."""
    live = _rules()["live_capability"]
    assert live["kill_switch_drill_required"] is True
    assert isinstance(live["kill_switch_drill_cadence_days"], int)
    assert live["kill_switch_drill_cadence_days"] == 14


def test_a_drill_is_re_required_after_a_relevant_change():
    assert set(_rules()["live_capability"]["kill_switch_drill_reverify_on"]) == {
        "deployment_ref",
        "credentials_ref",
        "kill_switch_path_digest",
        "gate_path_digest",
    }


def test_the_gate_reads_its_stop_conditions_from_the_spec_not_a_copy():
    """A second copy of the mapping in code is a second thing to keep in sync."""
    spec = {c["id"]: c["stop_condition"] for c in _spec()["checks"]}
    assert _kill_switch_stop_conditions() == spec


def test_declared_stop_conditions_are_known_to_the_control_plane():
    from runner.stops import STOP_CONDITIONS

    assert set(_spec()["stop_conditions"]) <= STOP_CONDITIONS


# ------------------------------------------------------------------ ceilings


def test_p8_may_never_be_enforced_under_this_preregistration():
    """Deployment independence rests on a human attestation, so no amount of green
    tests can carry P8 past PARTIAL."""
    p8 = next(p for p in _rules()["principles"] if p["id"] == "P8")
    assert p8["enforcement"] != "ENFORCED"
    assert p8["enforcement"] in ("DECLARATIVE", "PARTIAL")


def test_capability_status_tracks_detector_reachability():
    """Writing a specification is not enforcement — and neither is writing a
    detector that nothing calls. Status may only advance once the runtime can
    reach it, and never past PARTIAL."""
    spec = _spec()
    status = _rules()["control_plane_stop_condition_status"]
    reachable = spec.get("detector_invoked_by_runtime", False)
    for condition in spec["stop_conditions"]:
        assert status[condition] != "ENFORCED", (
            f"{condition} may never be ENFORCED under this preregistration"
        )
        if not reachable:
            assert status[condition] == "DECLARATIVE", (
                f"{condition} was promoted although no runtime path invokes the detector"
            )


def test_the_enforcement_summary_is_counted_not_asserted():
    """The summary is a count of principles[].enforcement, so it cannot claim a
    state the principles themselves do not carry."""
    rules = _rules()
    counted: dict[str, int] = {}
    for principle in rules["principles"]:
        counted[principle["enforcement"]] = counted.get(principle["enforcement"], 0) + 1
    summary = rules["enforcement_summary"]
    for state in ("ENFORCED", "PARTIAL", "DECLARATIVE", "MISSING", "CONFLICT"):
        assert summary[state] == counted.get(state, 0), (
            f"{state}: summary says {summary[state]}, principles carry {counted.get(state, 0)}"
        )


def test_the_recorded_case_count_is_the_spec_s_own_count():
    """A number in a governance file with no source is the thing this repo builds
    detectors against. These two are counted from the spec, not typed in."""
    spec = _spec()
    record = _rules()["uptm003_detector"]
    assert record["checks"] == len(spec["checks"])
    assert record["acceptance_cases_passing"] == len(_cases(spec))
    assert record["drill_cadence_days"] == _rules()["live_capability"][
        "kill_switch_drill_cadence_days"
    ]


def test_the_detector_record_declares_the_same_ceiling_as_the_spec():
    spec, record = _spec(), _rules()["uptm003_detector"]
    assert record["max_status"] == spec["target_capability"] == "PARTIAL"
    assert set(record["upgrade_to_enforced_requires"]) == set(
        spec["upgrade_to_enforced_requires"]
    )
    assert set(record["open_limits"]) == set(spec["declared_limits"])
