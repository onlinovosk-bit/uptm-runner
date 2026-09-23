"""Detectors for `kill_switch_not_self_clearable` and `kill_switch_drill_valid`.

Implements the criteria preregistered in
docs/specs/UPTM-003-kill-switch-independence.md, written before this module
existed (CC/P4).

What these detectors claim
--------------------------
That the Runner cannot write the state that stops it, that it denies when it
cannot read that state, that reading does not change it, and that a drill which
demonstrably stopped something was performed recently enough against a pinned
commit, against the deployment still in force, and that an operator has attested
deployment independence with a date that is not older than that deployment.

What they do not claim
----------------------
That the switch is physically beyond the Runner's blast radius. A process
cannot certify its own deployment topology. These checks establish that *this*
process cannot write the stop path; they cannot establish that the path is on
another host, under other credentials, in another failure domain. That remains
a Founder attestation, never a PASS produced here.

Verdicts only
-------------
Every check returns a Verdict, never a Decision. Resolution stays with
runner.verdict.resolve.
"""

from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from runner.detectors.fabrication import CheckOutcome, _fail, _missing, _ok, _unknown
from runner.verdict import Verdict

#: The stop state may read exactly these. Anything else is not a state we can
#: act on, and guessing which way it leans is precisely what P11 forbids.
CLEAR = "CLEAR"
ENGAGED = "ENGAGED"
KNOWN_STATES = (CLEAR, ENGAGED)

RUNNING_STATES = ("RUNNING", "UP", "ACTIVE")
STOPPED_STATES = ("STOPPED", "HALTED", "DOWN")

#: What a drill is a drill *of*. A change to any of these invalidates it at
#: once, however recent it was: a drill against a deployment that no longer
#: exists proves nothing about the one that does. KS-D4 already covers the stop
#: path; these are the rest of the blast radius.
ENVIRONMENT_KEYS = ("deployment_ref", "credentials_ref", "gate_path_digest")


def _parse_iso(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _digest(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _read_state(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8").strip().upper() or None
    except OSError:
        return None


# --------------------------------------------------------------------------
# kill_switch_not_self_clearable
# --------------------------------------------------------------------------


def check_ks_p1_declaration(stop: dict[str, Any]) -> CheckOutcome:
    """The pack must say where the stop lives, who owns it, and whether we can write it."""
    absent = [p for p in ("path", "owner") if not stop.get(p)]
    if stop.get("runner_writable") is None:
        absent.append("runner_writable")
    if absent:
        return _unknown("KS-P1", absent)
    return _ok("KS-P1", f"stop state declared at {stop['path']}, owned by {stop['owner']}")


def check_ks_p2_declared_not_writable(stop: dict[str, Any]) -> CheckOutcome:
    """A declaration that the Runner may write its own stop is a violation on its face."""
    if stop.get("runner_writable") is None:
        return _unknown("KS-P2", ["runner_writable"])
    if stop["runner_writable"] is True:
        return _fail(
            "KS-P2",
            "safety_control_weakening: the pack declares the Runner may write its own stop state",
        )
    return _ok("KS-P2", "declared not writable by the Runner")


def can_write(path: Path) -> bool:
    """Whether *this* process can write *path*, as the OS sees it.

    Injected so the check is testable without depending on the uid the suite
    happens to run under. Note that for uid 0 this is True whatever the file
    mode says — and that is the correct answer, not a false positive: a Runner
    running as root can clear its own stop, so P8's property does not hold.
    """
    return os.access(path, os.W_OK)


def check_ks_i1_not_writable_in_fact(
    stop: dict[str, Any], *, writable: Any = None
) -> CheckOutcome:
    """Probe the capability rather than read the claim.

    KS-P2 reads what the pack says. This asks the operating system whether this
    process can in fact write the stop path, or replace it by writing its
    directory. A declaration is not evidence; the access check is.
    """
    writable = writable or can_write
    path_s = stop.get("path")
    if not path_s:
        return _unknown("KS-I1", ["path"])
    path = Path(path_s)
    if not path.exists():
        # Whether the stop exists at all is KS-I2's question, not this one.
        return _unknown("KS-I1", ["an existing stop state to probe"])

    reachable = []
    if writable(path):
        reachable.append("the file")
    if writable(path.parent):
        reachable.append("its directory, so the file can be replaced")
    if reachable:
        return _fail(
            "KS-I1",
            "safety_control_weakening: this process can write "
            + " and ".join(reachable)
            + f" ({path_s}) — it can clear its own stop",
        )
    return _ok("KS-I1", "the running process cannot write the stop state or its directory")


def check_ks_i2_readable(stop: dict[str, Any]) -> CheckOutcome:
    """Unreadable is never PASS. P11: uncertainty halts, it does not guess."""
    path_s = stop.get("path")
    if not path_s:
        return _unknown("KS-I2", ["path"])
    state = _read_state(Path(path_s))
    if state is None:
        return _unknown("KS-I2", [f"a readable stop state at {path_s}"])
    if state not in KNOWN_STATES:
        return _unknown("KS-I2", [f"a stop state in {KNOWN_STATES}, read {state!r}"])
    return _ok("KS-I2", f"stop state readable and well-formed: {state}")


def check_ks_i3_engaged_denies(stop: dict[str, Any]) -> CheckOutcome:
    """An engaged stop denies. This is the check that makes the switch a switch.

    The detail names it as the switch working, not as an agent violation — but
    the verdict is FAIL, because FAIL is what denies while naming a demonstrated
    fact. UNKNOWN would misreport a state we read successfully as one we could
    not evaluate.
    """
    path_s = stop.get("path")
    if not path_s:
        return _unknown("KS-I3", ["path"])
    state = _read_state(Path(path_s))
    if state is None or state not in KNOWN_STATES:
        return _unknown("KS-I3", [f"a readable stop state at {path_s}"])
    if state == ENGAGED:
        return _fail(
            "KS-I3",
            "kill_switch_engaged: the stop is engaged, so no gate may pass. "
            "This is the switch working, not a violation by an agent.",
        )
    return _ok("KS-I3", "stop state CLEAR")


def check_ks_i4_read_does_not_mutate(stop: dict[str, Any], before: str | None) -> CheckOutcome:
    """Evaluating the switch must not change it."""
    path_s = stop.get("path")
    if not path_s:
        return _unknown("KS-I4", ["path"])
    after = _digest(Path(path_s))
    if before is None or after is None:
        return _unknown("KS-I4", [f"a readable stop state at {path_s}"])
    if before != after:
        return _fail(
            "KS-I4",
            "safety_control_weakening: the stop state changed while it was being evaluated "
            f"({before[:12]} -> {after[:12]})",
        )
    return _ok("KS-I4", "stop state unchanged across evaluation")


# --------------------------------------------------------------------------
# kill_switch_drill_valid
# --------------------------------------------------------------------------


def check_ks_d1_cadence_declared(cadence_days: Any) -> CheckOutcome:
    """The cadence is a Founder parameter. Unset means UNKNOWN, never a default."""
    if not isinstance(cadence_days, int) or isinstance(cadence_days, bool) or cadence_days <= 0:
        return _unknown(
            "KS-D1",
            ["live_capability.kill_switch_drill_cadence_days as a positive integer"],
        )
    return _ok("KS-D1", f"drill cadence {cadence_days} day(s)")


def check_ks_d2_drill_recent(
    drill: dict[str, Any], cadence_days: Any, *, now: datetime | None = None
) -> CheckOutcome:
    if not isinstance(cadence_days, int) or isinstance(cadence_days, bool) or cadence_days <= 0:
        return _unknown("KS-D2", ["a declared drill cadence"])
    last = _parse_iso(drill.get("last_drill_at"))
    if last is None:
        return _unknown("KS-D2", ["last_drill_at as an ISO-8601 timestamp"])
    reference = now or datetime.now(timezone.utc)
    age_days = (reference - last).total_seconds() / 86400
    if age_days > cadence_days:
        return _fail(
            "KS-D2",
            f"the last drill is {age_days:.1f} days old, cadence is {cadence_days} — "
            "an untested kill switch does not exist",
        )
    return _ok("KS-D2", f"last drill {age_days:.1f} day(s) ago, within {cadence_days}")


def check_ks_d3_drill_demonstrated_a_stop(drill: dict[str, Any]) -> CheckOutcome:
    """A record whose only content is a verdict is not evidence.

    The gate already refuses an agent PASS with no probes. A drill is a probe of
    the one control that matters most, and is held to the same rule.
    """
    before, after = drill.get("before"), drill.get("after")
    if not isinstance(before, dict) or not isinstance(after, dict):
        return _fail(
            "KS-D3",
            "evidence_forgery_detected: the drill record carries no before/after transition, "
            "only a claim that it happened",
        )
    absent = _missing(before, "state", "artifact_digest") + _missing(after, "state", "artifact_digest")
    if absent:
        return _fail(
            "KS-D3",
            "evidence_forgery_detected: the drill transition is missing "
            + ", ".join(sorted(set(absent)))
            + " — a state without an artifact is a claim",
        )
    b_state = str(before["state"]).upper()
    a_state = str(after["state"]).upper()
    if b_state not in RUNNING_STATES or a_state not in STOPPED_STATES:
        return _fail(
            "KS-D3",
            f"the drill does not show a stop: {b_state} -> {a_state}",
        )
    if before["artifact_digest"] == after["artifact_digest"]:
        return _fail(
            "KS-D3",
            "the drill's before and after artifacts are identical — nothing was demonstrated",
        )
    return _ok("KS-D3", f"drill demonstrated {b_state} -> {a_state}")


def check_ks_d4_commit_pinned(drill: dict[str, Any], stop: dict[str, Any]) -> CheckOutcome:
    """P12: evidence has a commit. A drill against a different stop path is expired."""
    commit = drill.get("drill_commit")
    if not commit:
        return _unknown("KS-D4", ["drill_commit"])
    drill_path = drill.get("drill_stop_path")
    if not drill_path:
        return _unknown("KS-D4", ["drill_stop_path — which stop the drill exercised"])
    if drill_path != stop.get("path"):
        return _unknown(
            "KS-D4",
            [
                f"a drill against today's stop path: drilled {drill_path!r}, "
                f"in force {stop.get('path')!r}"
            ],
        )
    return _ok("KS-D4", f"drill pinned to {commit}")


def check_ks_d5_environment_unchanged(
    drill: dict[str, Any], stop: dict[str, Any]
) -> CheckOutcome:
    """The drill has not been invalidated by a change to what it was run against.

    KS-D2 asks whether the drill is recent. This asks whether it is still *about*
    the system in force. The two are independent: a drill performed an hour ago
    against yesterday's credentials is fresh and worthless.

    A mismatch is UNKNOWN rather than FAIL, matching KS-D4: we do not have a
    valid drill for this deployment, which is not the same as having caught
    someone. Either way the gate denies.
    """
    recorded = drill.get("environment")
    in_force = stop.get("environment")
    if not isinstance(recorded, dict) or not isinstance(in_force, dict):
        return _unknown(
            "KS-D5",
            [
                "drill.environment and kill_switch.stop_state.environment declaring "
                + ", ".join(ENVIRONMENT_KEYS)
            ],
        )
    undeclared = [
        k for k in ENVIRONMENT_KEYS if recorded.get(k) is None or in_force.get(k) is None
    ]
    if undeclared:
        return _unknown("KS-D5", sorted(undeclared))
    changed = [k for k in ENVIRONMENT_KEYS if recorded[k] != in_force[k]]
    if changed:
        return _unknown(
            "KS-D5",
            [
                "a drill against today's "
                + ", ".join(sorted(changed))
                + " — the recorded drill predates that change, so a new drill is "
                "required regardless of the cadence window"
            ],
        )
    return _ok("KS-D5", "drill environment matches the one in force")


def check_ks_d6_independence_attested(
    stop: dict[str, Any], *, now: datetime | None = None
) -> CheckOutcome:
    """An operator has attested deployment independence, with a date.

    §0 of the specification is explicit that a process cannot certify its own
    deployment topology, and this check does not try to. It checks the one thing
    code *can* check about an attestation: that one exists, that it is dated,
    and that it is not older than the deployment it purports to describe.

    An attestation that predates the last relevant change describes a system
    that is gone. That is UNKNOWN — no valid attestation — not an accusation.
    """
    attested = stop.get("independence_attestation")
    if not isinstance(attested, dict):
        return _unknown(
            "KS-D6",
            ["independence_attestation — deployment independence is a dated operator claim"],
        )
    absent = _missing(attested, "by", "at")
    if absent:
        return _unknown("KS-D6", sorted(absent))
    at = _parse_iso(attested["at"])
    if at is None:
        return _unknown("KS-D6", ["at as an ISO-8601 timestamp"])
    reference = now or datetime.now(timezone.utc)
    if at > reference:
        return _unknown("KS-D6", ["an attestation that is not dated in the future"])
    in_force = stop.get("environment")
    changed_at = _parse_iso(in_force.get("changed_at")) if isinstance(in_force, dict) else None
    if changed_at is not None and at < changed_at:
        return _unknown(
            "KS-D6",
            [
                f"an attestation covering today's deployment: attested {attested['at']}, "
                f"deployment changed {in_force.get('changed_at')}"
            ],
        )
    return _ok("KS-D6", f"independence attested by {attested['by']} at {attested['at']}")


# --------------------------------------------------------------------------


def detect_kill_switch(
    pack: dict[str, Any], *, writable: Any = None
) -> list[CheckOutcome]:
    stop = pack.get("stop_state") or {}
    path_s = stop.get("path")
    before = _digest(Path(path_s)) if path_s else None
    return [
        check_ks_p1_declaration(stop),
        check_ks_p2_declared_not_writable(stop),
        check_ks_i1_not_writable_in_fact(stop, writable=writable),
        check_ks_i2_readable(stop),
        check_ks_i3_engaged_denies(stop),
        check_ks_i4_read_does_not_mutate(stop, before),
    ]


def detect_kill_switch_drill(
    pack: dict[str, Any], stop: dict[str, Any], cadence_days: Any
) -> list[CheckOutcome]:
    return [
        check_ks_d1_cadence_declared(cadence_days),
        check_ks_d2_drill_recent(pack, cadence_days),
        check_ks_d3_drill_demonstrated_a_stop(pack),
        check_ks_d4_commit_pinned(pack, stop),
        check_ks_d5_environment_unchanged(pack, stop),
        check_ks_d6_independence_attested(stop),
    ]


def stop_is_engaged(pack: dict[str, Any]) -> bool:
    """Read-only helper for the gate's bypass invariant (KS-I3b)."""
    path_s = (pack.get("stop_state") or {}).get("path")
    return bool(path_s) and _read_state(Path(path_s)) == ENGAGED
