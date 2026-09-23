"""Acceptance criteria preregistered in docs/specs/UPTM-003-kill-switch-independence.md §5.

Written against the criteria as they stood before this detector existed, with
the two amendments recorded in §5a of that document. Case numbers below are the
spec's own.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from runner.detectors.kill_switch import (
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
