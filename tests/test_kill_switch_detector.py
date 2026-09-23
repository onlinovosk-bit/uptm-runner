"""UPTM-003 acceptance cases for the kill-switch detector.

Every case here is preregistered in docs/specs/UPTM-003-kill-switch.json. The
spec was written first; these tests are its executable form, and
`test_uptm003_preregistration.py` asserts that neither drifts from the other.
"""Acceptance criteria preregistered in docs/specs/UPTM-003-kill-switch-independence.md §5.

Written against the criteria as they stood before this detector existed, with
the two amendments recorded in §5a of that document. Case numbers below are the
spec's own.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from datetime import datetime, timedelta, timezone

import pytest

from runner.detectors.kill_switch import (
    DISENGAGED,
    ENGAGED,
    StopStateUnreadable,
    detect_kill_switch,
    stop_state_is_engaged,
)
from runner.paths import UPTM003_SPEC
from runner.verdict import Verdict

CADENCE = 14


@pytest.fixture
def ks_pack_factory(tmp_path):
    """A pack in which every preregistered property holds."""

    def _make(state: str = DISENGAGED, **overrides):
        root = tmp_path / "ks"
        root.mkdir(exist_ok=True)
        (root / "stop_state").write_text(state, encoding="utf-8")
        env = {
            "deployment_ref": "dep-1",
            "credentials_ref": "cred-1",
            "kill_switch_path_digest": "ks-digest-1",
            "gate_path_digest": "gate-digest-1",
            "changed_at_utc": "2026-09-01T00:00:00Z",
        }
        pack = {
            "stop_state_ref": "stop_state",
            "stop_state_root": str(root),
            "stop_state_read_via": "file:read_only",
            "declared_states": [ENGAGED, DISENGAGED],
            "runner_write_paths": [],
            "evaluated_at_utc": "2026-09-22T12:00:00Z",
            "drill": {
                "completed_at_utc": "2026-09-15T09:00:00Z",
                "result": "PASS",
                "before_state": DISENGAGED,
                "after_state": ENGAGED,
                "restored_state": DISENGAGED,
                "environment": dict(env),
            },
            "current_environment": dict(env),
            "operator_attestation": {
                "by": "founder",
                "at_utc": "2026-09-10T00:00:00Z",
                "statement": "kill switch runs outside the runner host on separate credentials",
            },
        }
        pack.update(overrides)
        return pack

    return _make


def run(pack, *, cadence=CADENCE, reader=None):
    return {
        o.check_id: o
        for o in detect_kill_switch(
            pack, stop_state_root=Path("."), cadence_days=cadence, reader=reader
        )
    }


def verdict_of(pack, check, **kw):
    return run(pack, **kw)[check].verdict


# ---------------------------------------------------------------- baseline


def test_a_fully_declared_pack_passes_every_check(ks_pack_factory):
    outcomes = run(ks_pack_factory())
    failing = {k: o.detail for k, o in outcomes.items() if o.verdict is not Verdict.PASS}
    assert not failing, failing


# ------------------------------------------------------------ must_fail (13)


def test_mut01_stop_state_token_outside_declared_states(ks_pack_factory, tmp_path):
    pack = ks_pack_factory()
    (tmp_path / "ks" / "stop_state").write_text("MAYBE", encoding="utf-8")
    assert verdict_of(pack, "KS-S1") is Verdict.FAIL


def test_mut02_stop_state_absent_is_fail_never_assumed_disengaged(ks_pack_factory, tmp_path):
    pack = ks_pack_factory()
    (tmp_path / "ks" / "stop_state").unlink()
    outcome = run(pack)["KS-S1"]
    assert outcome.verdict is Verdict.FAIL
    assert "unreadable" in outcome.detail


def test_mut03_a_reader_that_writes_is_caught(ks_pack_factory):
    pack = ks_pack_factory()

    def mutating_reader(path: Path) -> str:
        value = path.read_text(encoding="utf-8").strip()
        path.write_text(DISENGAGED + "\n", encoding="utf-8")  # the mutation
        return value

    assert verdict_of(pack, "KS-S2", reader=mutating_reader) is Verdict.FAIL


def test_mut04_declared_runner_write_path(ks_pack_factory):
    pack = ks_pack_factory(runner_write_paths=["/var/uptm/stop_state"])
    outcome = run(pack)["KS-S3"]
    assert outcome.verdict is Verdict.FAIL
    assert "write path" in outcome.detail


def test_mut05_drill_older_than_the_cadence(ks_pack_factory):
    pack = ks_pack_factory()
    pack["drill"]["completed_at_utc"] = "2026-09-07T12:00:00Z"  # 15 days
    assert verdict_of(pack, "KS-D1") is Verdict.FAIL


def test_mut06_drill_with_no_state_change(ks_pack_factory):
    pack = ks_pack_factory()
    pack["drill"]["after_state"] = DISENGAGED
    outcome = run(pack)["KS-D2"]
    assert outcome.verdict is Verdict.FAIL
    assert "no transition" in outcome.detail


def test_mut07_declared_pass_without_a_transition_is_forgery(ks_pack_factory):
    pack = ks_pack_factory()
    pack["drill"].pop("before_state")
    pack["drill"].pop("after_state")
    outcome = run(pack)["KS-D5"]
    assert outcome.verdict is Verdict.FAIL
    assert "declared verdict is not a drill" in outcome.detail


@pytest.mark.parametrize(
    "case,key",
    [
        ("MUT-08", "deployment_ref"),
        ("MUT-09", "credentials_ref"),
        ("MUT-10", "kill_switch_path_digest"),
        ("MUT-11", "gate_path_digest"),
    ],
)
def test_mut08_to_11_relevant_change_invalidates_the_drill(ks_pack_factory, case, key):
    """A fresh drill does not survive a change to what it was run against."""
    pack = ks_pack_factory()
    pack["current_environment"][key] = "changed"
    outcome = run(pack)["KS-D3"]
    assert outcome.verdict is Verdict.FAIL, case
    assert key in outcome.detail
    # and the cadence window is untouched — staleness is not why this failed
    assert run(pack)["KS-D1"].verdict is Verdict.PASS


def test_mut12_attestation_predating_the_last_change(ks_pack_factory):
    pack = ks_pack_factory()
    pack["current_environment"]["changed_at_utc"] = "2026-09-20T00:00:00Z"
    outcome = run(pack)["KS-D4"]
    assert outcome.verdict is Verdict.FAIL
    assert "predates" in outcome.detail


def test_mut13_engaged_stop_state_is_read_as_engaged(ks_pack_factory, tmp_path):
    """The detector-side half of KS-G1: the gate half lives in the gate tests."""
    pack = ks_pack_factory(state=ENGAGED)
    assert stop_state_is_engaged(pack, stop_state_root=Path(".")) is True


# --------------------------------------------------------- must_unknown (20)

#: How each preregistered parameter is withheld. A parameter in the spec with no
#: entry here fails test_every_spec_parameter_has_a_mutator below, so the spec
#: cannot grow a requirement that nothing exercises.
WITHHOLD = {
    "stop_state_ref": lambda p: p.pop("stop_state_ref"),
    "stop_state_read_via": lambda p: p.pop("stop_state_read_via"),
    "runner_write_paths": lambda p: p.pop("runner_write_paths"),
    "drill": lambda p: p.pop("drill"),
    "operator_attestation": lambda p: p.pop("operator_attestation"),
    "declared_states": lambda p: p.pop("declared_states"),
    "evaluated_at_utc": lambda p: p.pop("evaluated_at_utc"),
    "current_environment": lambda p: p.pop("current_environment"),
    "drill_completed_at_utc": lambda p: p["drill"].pop("completed_at_utc"),
    "drill_before_state": lambda p: p["drill"].pop("before_state"),
    "drill_after_state": lambda p: p["drill"].pop("after_state"),
    "drill_result": lambda p: p["drill"].pop("result"),
    "drill_environment": lambda p: p["drill"].pop("environment"),
    "operator_attestation_by": lambda p: p["operator_attestation"].pop("by"),
    "operator_attestation_at_utc": lambda p: p["operator_attestation"].pop("at_utc"),
    "cadence_days": lambda p: None,  # withheld at the call site, not in the pack
}


def _spec() -> dict:
    return json.loads(UPTM003_SPEC.read_text(encoding="utf-8"))


def _unknown_cases():
    return [
        (c["id"], c["check"], c["missing_param"])
        for c in _spec()["acceptance_cases"]["must_unknown"]
    ]


def test_every_spec_parameter_has_a_mutator():
    params = {p for c in _spec()["checks"] for p in c["required_params"]}
    assert not (params - set(WITHHOLD)), sorted(params - set(WITHHOLD))


@pytest.mark.parametrize("case,check,param", _unknown_cases())
def test_a_withheld_parameter_is_unknown_never_a_default(
    ks_pack_factory, case, check, param
):
    """The spine of the spec: an undeclared parameter buys UNKNOWN, never a pass."""
    if check == "KS-G1":
        pack = ks_pack_factory()
        WITHHOLD[param](pack)
        assert stop_state_is_engaged(pack, stop_state_root=Path(".")) is None, case
        return

    pack = ks_pack_factory()
    cadence = None if param == "cadence_days" else CADENCE
    WITHHOLD[param](pack)
    assert verdict_of(pack, check, cadence=cadence) is Verdict.UNKNOWN, (
        f"{case}: withholding {param} did not make {check} UNKNOWN"
    )


# ------------------------------------------------------------ must_pass (7)


def test_neg01_drill_exactly_at_the_cadence_boundary_is_still_valid(ks_pack_factory):
    pack = ks_pack_factory()
    pack["drill"]["completed_at_utc"] = "2026-09-08T12:00:00Z"  # exactly 14 days
    assert verdict_of(pack, "KS-D1") is Verdict.PASS


def test_neg02_disengaged_is_a_determinate_state(ks_pack_factory):
    pack = ks_pack_factory(state=DISENGAGED)
    assert verdict_of(pack, "KS-S1") is Verdict.PASS
    assert stop_state_is_engaged(pack, stop_state_root=Path(".")) is False


def test_neg03_engage_then_restore_passes(ks_pack_factory):
    pack = ks_pack_factory()
    pack["drill"]["restored_state"] = DISENGAGED
    assert verdict_of(pack, "KS-D2") is Verdict.PASS


def test_neg04_declared_empty_is_not_undeclared(ks_pack_factory):
    """An operator saying "there is none" is evidence. An absent field is not."""
    assert verdict_of(ks_pack_factory(runner_write_paths=[]), "KS-S3") is Verdict.PASS
    absent = ks_pack_factory()
    absent.pop("runner_write_paths")
    assert verdict_of(absent, "KS-S3") is Verdict.UNKNOWN


def test_neg05_attestation_after_the_last_change_passes(ks_pack_factory):
    pack = ks_pack_factory()
    pack["operator_attestation"]["at_utc"] = "2026-09-02T00:00:00Z"
    assert verdict_of(pack, "KS-D4") is Verdict.PASS


def test_neg06_engaged_while_already_denying_is_not_an_accusation(ks_pack_factory):
    """The gate half of KS-G1 — asserted end-to-end in the invocation tests."""
    from runner import gates

    pack = ks_pack_factory(state=ENGAGED)
    verdict, reasons = gates.apply_ks_g1(
        {"kill_switch": pack}, None, Verdict.FAIL, ["something else already failed"]
    )
    assert verdict is Verdict.FAIL
    assert not any("gate_bypass_attempt" in r for r in reasons)


def test_neg07_declared_pass_with_a_transition_is_substantiated(ks_pack_factory):
    assert verdict_of(ks_pack_factory(), "KS-D5") is Verdict.PASS


def test_a_declared_non_pass_drill_has_nothing_to_substantiate(ks_pack_factory):
    pack = ks_pack_factory()
    pack["drill"]["result"] = "FAIL"
    pack["drill"].pop("before_state")
    pack["drill"].pop("after_state")
    outcomes = run(pack)
    assert outcomes["KS-D5"].verdict is Verdict.PASS
    assert outcomes["KS-D2"].verdict is Verdict.UNKNOWN, (
        "an absent transition is UNKNOWN; only a declared PASS makes it forgery"
    )


# ------------------------------------------------- the read is a read, always


def test_the_default_reader_leaves_the_stop_state_byte_identical(ks_pack_factory, tmp_path):
    pack = ks_pack_factory()
    path = tmp_path / "ks" / "stop_state"
    before = path.read_bytes()
    assert verdict_of(pack, "KS-S2") is Verdict.PASS
    assert path.read_bytes() == before


def test_an_unreadable_stop_state_is_not_reported_as_a_mutation(ks_pack_factory, tmp_path):
    """KS-S1 owns unreadability. KS-S2 must not also accuse on the same fact."""
    pack = ks_pack_factory()
    (tmp_path / "ks" / "stop_state").unlink()
    outcomes = run(pack)
    assert outcomes["KS-S1"].verdict is Verdict.FAIL
    assert outcomes["KS-S2"].verdict is Verdict.UNKNOWN
    assert "non-mutation not established" in outcomes["KS-S2"].detail


def test_the_stop_state_is_read_exactly_once(ks_pack_factory):
    """A second read is a second chance for a mutating reader to look idempotent.

    This is the defect MUT-03 exposed: when KS-S1 read the file first, the
    mutation had already happened by the time KS-S2 bracketed its own read, and
    the digests matched.
    """
    reads: list[Path] = []

    def counting_reader(path: Path) -> str:
        reads.append(path)
        return path.read_text(encoding="utf-8").strip()

    run(ks_pack_factory(), reader=counting_reader)
    assert len(reads) == 1, f"the stop state was read {len(reads)} times"


def test_a_reader_that_raises_does_not_mutate(ks_pack_factory):
    def refusing_reader(path: Path) -> str:
        raise StopStateUnreadable("permission denied")

    outcomes = run(ks_pack_factory(), reader=refusing_reader)
    assert outcomes["KS-S2"].verdict is Verdict.PASS
    assert outcomes["KS-S1"].verdict is Verdict.FAIL
    detect_kill_switch,
    detect_kill_switch_drill,
    check_ks_d2_drill_recent,
    stop_is_engaged,
)
from runner.verdict import Decision, Verdict, resolve

CADENCE = 7
NOW = datetime(2026, 9, 23, 12, 0, tzinfo=timezone.utc)


def _outcome(outcomes, check_id):
    return next(o for o in outcomes if o.check_id == check_id)


@pytest.fixture
def stop_file(tmp_path):
    def _make(state: str = "CLEAR"):
        path = tmp_path / "stop.state"
        path.write_text(state, encoding="utf-8")
        return path

    return _make


@pytest.fixture
def pack(stop_file):
    def _make(state: str = "CLEAR", **stop_overrides):
        stop = {
            "path": str(stop_file(state)),
            "owner": "ops@revolis",
            "runner_writable": False,
            "environment": {
                "deployment_ref": "dep-1",
                "credentials_ref": "cred-1",
                "gate_path_digest": "gate-1",
                "changed_at": "2026-09-01T00:00:00Z",
            },
            "independence_attestation": {
                "by": "ops@revolis",
                "at": "2026-09-10T00:00:00Z",
            },
        }
        stop.update(stop_overrides)
        return {"stop_state": stop}

    return _make


@pytest.fixture
def drill():
    def _make(**overrides):
        base = {
            "last_drill_at": (NOW - timedelta(days=2)).isoformat(),
            "drill_commit": "c9ae2aa",
            "drill_stop_path": None,  # filled by the caller to match the pack
            "before": {"state": "RUNNING", "artifact_digest": "a" * 64},
            "after": {"state": "STOPPED", "artifact_digest": "b" * 64},
            "environment": {
                "deployment_ref": "dep-1",
                "credentials_ref": "cred-1",
                "gate_path_digest": "gate-1",
                "changed_at": "2026-09-01T00:00:00Z",
            },
        }
        base.update(overrides)
        return base

    return _make


#: The probe the checks use, stubbed so a case's outcome never depends on the
#: uid the suite runs under. `sealed` is the deployment P8 wants; `exposed` is
#: a Runner that can reach its own stop — which is what running as root means.
sealed = lambda _path: False
exposed = lambda _path: True


# ------------------------------------------------------------------ must FAIL


def test_case1_declared_writable_is_a_violation(pack):
    outcomes = detect_kill_switch(pack(runner_writable=True), writable=sealed)
    assert _outcome(outcomes, "KS-P2").verdict is Verdict.FAIL
    assert "safety_control_weakening" in _outcome(outcomes, "KS-P2").detail


def test_case2_writable_in_fact_while_declared_otherwise(pack):
    """The declaration says no; the operating system says yes. The probe wins."""
    outcomes = detect_kill_switch(pack(), writable=exposed)
    assert _outcome(outcomes, "KS-P2").verdict is Verdict.PASS, "the pack still declares false"
    assert _outcome(outcomes, "KS-I1").verdict is Verdict.FAIL
    assert "can clear its own stop" in _outcome(outcomes, "KS-I1").detail


def test_case3_engaged_stop_denies(pack):
    outcomes = detect_kill_switch(pack("ENGAGED"), writable=sealed)
    ks_i3 = _outcome(outcomes, "KS-I3")
    assert ks_i3.verdict is Verdict.FAIL
    assert resolve(ks_i3.verdict) is Decision.DENY
    assert "not a violation by an agent" in ks_i3.detail, (
        "an engaged switch must deny without being reported as misconduct"
    )


def test_case4_state_changing_during_evaluation(pack, monkeypatch):
    import runner.detectors.kill_switch as ks

    p = pack()
    digests = iter(["a" * 64, "z" * 64])
    monkeypatch.setattr(ks, "_digest", lambda _path: next(digests))
    outcomes = detect_kill_switch(p, writable=sealed)
    assert _outcome(outcomes, "KS-I4").verdict is Verdict.FAIL


def test_case5_drill_older_than_cadence(pack, drill):
    p = pack()
    d = drill(last_drill_at=(NOW - timedelta(days=30)).isoformat())
    outcome = check_ks_d2_drill_recent(d, CADENCE, now=NOW)
    assert outcome.verdict is Verdict.FAIL
    assert "an untested kill switch does not exist" in outcome.detail


def test_case6_drill_record_is_only_a_claim(pack, drill):
    p = pack()
    d = drill(before=None, after=None)
    d["drill_stop_path"] = p["stop_state"]["path"]
    outcomes = detect_kill_switch_drill(d, p["stop_state"], CADENCE)
    ks_d3 = _outcome(outcomes, "KS-D3")
    assert ks_d3.verdict is Verdict.FAIL
    assert "evidence_forgery_detected" in ks_d3.detail


def test_case6b_drill_states_without_artifacts(pack, drill):
    p = pack()
    d = drill(before={"state": "RUNNING"}, after={"state": "STOPPED"})
    d["drill_stop_path"] = p["stop_state"]["path"]
    ks_d3 = _outcome(detect_kill_switch_drill(d, p["stop_state"], CADENCE), "KS-D3")
    assert ks_d3.verdict is Verdict.FAIL
    assert "a state without an artifact is a claim" in ks_d3.detail


def test_case6c_drill_that_never_stopped_anything(pack, drill):
    p = pack()
    d = drill(after={"state": "RUNNING", "artifact_digest": "b" * 64})
    d["drill_stop_path"] = p["stop_state"]["path"]
    assert _outcome(detect_kill_switch_drill(d, p["stop_state"], CADENCE), "KS-D3").verdict is Verdict.FAIL


# --------------------------------------------------------------- must UNKNOWN


def test_case7_cadence_unset_is_unknown_not_pass(pack, drill):
    p = pack()
    d = drill()
    d["drill_stop_path"] = p["stop_state"]["path"]
    outcomes = detect_kill_switch_drill(d, p["stop_state"], None)
    assert _outcome(outcomes, "KS-D1").verdict is Verdict.UNKNOWN
    assert resolve(_outcome(outcomes, "KS-D1").verdict) is Decision.DENY


def test_case8_unreadable_stop_is_unknown_not_fail(pack, tmp_path):
    outcomes = detect_kill_switch(
        {"stop_state": {"path": str(tmp_path / "absent"), "owner": "ops", "runner_writable": False}},
        writable=sealed,
    )
    assert _outcome(outcomes, "KS-I2").verdict is Verdict.UNKNOWN
    assert _outcome(outcomes, "KS-I3").verdict is Verdict.UNKNOWN, (
        "an absent stop must not be read as CLEAR"
    )
    assert not any(o.stop_condition_raised for o in outcomes), (
        "absence denies, it does not accuse"
    )


def test_case9_owner_undeclared_is_unknown(pack):
    outcomes = detect_kill_switch(pack(owner=None), writable=sealed)
    assert _outcome(outcomes, "KS-P1").verdict is Verdict.UNKNOWN


def test_case10_drill_against_a_different_stop_path(pack, drill):
    p = pack()
    d = drill(drill_stop_path="/some/other/stop.state")
    assert _outcome(detect_kill_switch_drill(d, p["stop_state"], CADENCE), "KS-D4").verdict is Verdict.UNKNOWN


def test_case10b_drill_commit_absent(pack, drill):
    p = pack()
    d = drill(drill_commit=None)
    d["drill_stop_path"] = p["stop_state"]["path"]
    assert _outcome(detect_kill_switch_drill(d, p["stop_state"], CADENCE), "KS-D4").verdict is Verdict.UNKNOWN


def test_unknown_state_word_is_unknown_not_clear(pack):
    outcomes = detect_kill_switch(pack("MAYBE"), writable=sealed)
    assert _outcome(outcomes, "KS-I2").verdict is Verdict.UNKNOWN
    assert _outcome(outcomes, "KS-I3").verdict is Verdict.UNKNOWN


# ------------------------------------------------------------------ must PASS


def test_case11_well_formed_pack_passes(pack, drill):
    p = pack()
    d = drill()
    d["drill_stop_path"] = p["stop_state"]["path"]
    outcomes = detect_kill_switch(p, writable=sealed) + detect_kill_switch_drill(
        d, p["stop_state"], CADENCE
    )
    assert all(o.verdict is Verdict.PASS for o in outcomes), [
        (o.check_id, o.verdict.value, o.detail) for o in outcomes if o.verdict is not Verdict.PASS
    ]


def test_case12_drill_more_often_than_the_cadence_passes(drill):
    outcome = check_ks_d2_drill_recent(
        drill(last_drill_at=(NOW - timedelta(hours=3)).isoformat()), CADENCE, now=NOW
    )
    assert outcome.verdict is Verdict.PASS


def test_case13_engaged_is_reported_as_the_switch_working(pack):
    """Amended (§5a). The engaged stop denies, and says so without accusing.

    The preregistered case 13 asked for PASS here, which contradicted case 3:
    a detector that returns PASS on an engaged stop cannot also be what makes
    the gate deny. The property that survives is the one that matters — the
    denial is not recorded as misconduct.
    """
    p = pack("ENGAGED")
    outcomes = detect_kill_switch(p, writable=sealed)
    engaged = _outcome(outcomes, "KS-I3")
    assert resolve(engaged.verdict) is Decision.DENY
    assert "kill_switch_engaged" in engaged.detail
    assert stop_is_engaged(p) is True
    others = [o for o in outcomes if o.check_id != "KS-I3"]
    assert all(o.verdict is Verdict.PASS for o in others), (
        "engaging the switch must not make every other check fail"
    )


# ------------------------------------------------------------ KS-D5 / KS-D6
#
# Ported from the parallel UPTM-003 implementation (closed PR #9) on the
# Founder's instruction. KS-D4 already invalidates a drill run against a
# different stop path; these extend the same reasoning to the rest of the blast
# radius, and add the one thing code can check about an attestation.


def _drill_for(p, d):
    """A drill record consistent with the pack it was run against."""
    d = dict(d)
    d["drill_stop_path"] = p["stop_state"]["path"]
    return d


@pytest.mark.parametrize("key", ["deployment_ref", "credentials_ref", "gate_path_digest"])
def test_a_relevant_change_invalidates_an_otherwise_fresh_drill(pack, drill, key):
    """Recent and worthless are not mutually exclusive."""
    p = pack()
    p["stop_state"]["environment"][key] = "changed-after-the-drill"
    outcomes = detect_kill_switch_drill(_drill_for(p, drill()), p["stop_state"], CADENCE)

    assert _outcome(outcomes, "KS-D5").verdict is Verdict.UNKNOWN
    assert key in _outcome(outcomes, "KS-D5").detail
    assert resolve(_outcome(outcomes, "KS-D5").verdict) is Decision.DENY
    # freshness is untouched — staleness is not why this denied
    assert _outcome(outcomes, "KS-D2").verdict is Verdict.PASS


def test_an_undeclared_environment_is_unknown_never_assumed_equal(pack, drill):
    p = pack()
    d = _drill_for(p, drill())
    d.pop("environment")
    assert _outcome(detect_kill_switch_drill(d, p["stop_state"], CADENCE), "KS-D5").verdict is (
        Verdict.UNKNOWN
    )


def test_a_matching_environment_passes(pack, drill):
    p = pack()
    outcomes = detect_kill_switch_drill(_drill_for(p, drill()), p["stop_state"], CADENCE)
    assert _outcome(outcomes, "KS-D5").verdict is Verdict.PASS


def test_a_missing_attestation_is_unknown(pack, drill):
    p = pack()
    p["stop_state"].pop("independence_attestation")
    outcomes = detect_kill_switch_drill(_drill_for(p, drill()), p["stop_state"], CADENCE)
    assert _outcome(outcomes, "KS-D6").verdict is Verdict.UNKNOWN
    assert "dated operator claim" in _outcome(outcomes, "KS-D6").detail


@pytest.mark.parametrize("field", ["by", "at"])
def test_an_undated_or_unsigned_attestation_is_unknown(pack, drill, field):
    p = pack()
    p["stop_state"]["independence_attestation"].pop(field)
    outcomes = detect_kill_switch_drill(_drill_for(p, drill()), p["stop_state"], CADENCE)
    assert _outcome(outcomes, "KS-D6").verdict is Verdict.UNKNOWN


def test_an_attestation_predating_the_deployment_it_describes_is_unknown(pack, drill):
    """An attestation older than the deployment describes a system that is gone."""
    p = pack()
    p["stop_state"]["environment"]["changed_at"] = "2026-09-20T00:00:00Z"  # after the attestation
    outcomes = detect_kill_switch_drill(_drill_for(p, drill()), p["stop_state"], CADENCE)
    assert _outcome(outcomes, "KS-D6").verdict is Verdict.UNKNOWN
    assert "covering today's deployment" in _outcome(outcomes, "KS-D6").detail


def test_an_attestation_dated_after_the_last_change_passes(pack, drill):
    p = pack()
    p["stop_state"]["independence_attestation"]["at"] = "2026-09-02T00:00:00Z"
    outcomes = detect_kill_switch_drill(_drill_for(p, drill()), p["stop_state"], CADENCE)
    assert _outcome(outcomes, "KS-D6").verdict is Verdict.PASS


def test_a_future_dated_attestation_is_unknown(pack, drill):
    p = pack()
    p["stop_state"]["independence_attestation"]["at"] = "2099-01-01T00:00:00Z"
    outcomes = detect_kill_switch_drill(_drill_for(p, drill()), p["stop_state"], CADENCE)
    assert _outcome(outcomes, "KS-D6").verdict is Verdict.UNKNOWN


def test_neither_check_claims_deployment_independence_is_true(pack, drill):
    """The boundary, asserted: a PASS here means an attestation exists and is
    current. It does not mean the switch is beyond the Runner's blast radius —
    no code in this repository establishes that."""
    p = pack()
    p["stop_state"]["independence_attestation"]["by"] = "someone who never checked"
    outcomes = detect_kill_switch_drill(_drill_for(p, drill()), p["stop_state"], CADENCE)
    assert _outcome(outcomes, "KS-D6").verdict is Verdict.PASS
