"""Detector for P8 — Independent Kill Switch (UPTM-003).

Implements the criteria preregistered in docs/specs/UPTM-003-kill-switch.md,
written before this module existed (CC/P4).

What this detector claims
-------------------------
It never reports that a kill switch is independent. Physical and topological
separation from the runner's process, credentials and network is an **operator
attestation carrying a date** — a fact about infrastructure, which code running
inside the thing being distrusted cannot establish. What it reports is narrower
and checkable:

    a stop state that cannot be read, cannot be resolved to one declared state,
    changes when it is read, is writable by the runner, or was last exercised by
    a drill that is stale, invalidated or unsubstantiated, is treated as no kill
    switch at all.

Verdicts only
-------------
Every check returns a Verdict and never a Decision. Resolution is the caller's,
through runner.verdict.resolve, so that no detector carries its own reading of
UNKNOWN.

A missing preregistered parameter is UNKNOWN, never a default. An absent stop
state read as DISENGAGED would be the silent permission GOVERNANCE.md C3
forbids: it would let a kill switch that was never wired look exactly like one
that is wired and off.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

from runner.detectors import CheckOutcome
from runner.verdict import Verdict

#: The state in which the system is stopped. A gate that would otherwise pass
#: while the stop state reads this is a bypass attempt, not a pass.
ENGAGED = "ENGAGED"
DISENGAGED = "DISENGAGED"

#: A drill is invalidated by a change to any of these, independently of when it
#: was last run. A drill against a deployment that no longer exists proves
#: nothing about the one that does.
ENVIRONMENT_KEYS = (
    "deployment_ref",
    "credentials_ref",
    "kill_switch_path_digest",
    "gate_path_digest",
)

StopStateReader = Callable[[Path], str]


class StopStateUnreadable(RuntimeError):
    """The stop state could not be read. Never silently a state."""


def read_stop_state_file(path: Path) -> str:
    """The default reader: open, read, close. Opens for reading only.

    KS-S2 asserts at runtime that whichever reader is configured leaves the
    stop state byte-identical. This one does, but the check does not take that
    on trust — a reader is a seam, and a seam that is trusted is not a seam.
    """
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise StopStateUnreadable(str(exc)) from exc


def _unknown(check_id: str, *absent: str) -> CheckOutcome:
    names = ", ".join(sorted(absent))
    return CheckOutcome(
        check_id, Verdict.UNKNOWN, f"undeclared preregistered parameter(s): {names}"
    )


def _ok(check_id: str, detail: str = "property holds") -> CheckOutcome:
    return CheckOutcome(check_id, Verdict.PASS, detail)


def _fail(check_id: str, detail: str) -> CheckOutcome:
    return CheckOutcome(check_id, Verdict.FAIL, detail)


def _missing(pack: dict[str, Any], *params: str) -> list[str]:
    return [p for p in params if pack.get(p) is None]


def _parse_utc(raw: Any) -> datetime | None:
    if not isinstance(raw, str):
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _digest(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _stop_state_path(pack: dict[str, Any], root: Path) -> Path:
    return Path(pack.get("stop_state_root") or root) / str(pack["stop_state_ref"])


# --------------------------------------------------------------------------
# declaration
# --------------------------------------------------------------------------


def check_ks_p1_declaration(pack: dict[str, Any]) -> CheckOutcome:
    """KS-P1 — the five fields the remaining checks read are declared."""
    absent = _missing(
        pack,
        "stop_state_ref",
        "stop_state_read_via",
        "runner_write_paths",
        "drill",
        "operator_attestation",
    )
    return _unknown("KS-P1", *absent) if absent else _ok("KS-P1")


# --------------------------------------------------------------------------
# stop state
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class StopStateRead:
    """One read of the stop state, with the digests that bracket it.

    The stop state is read exactly once per evaluation. Reading it twice would
    give a mutating reader a second chance to look idempotent: the first read
    changes the value, the second finds the change already made and reports
    nothing. KS-S1 and KS-S2 therefore judge the same single read rather than
    each performing their own.
    """

    value: str | None
    error: str | None
    digest_before: str | None
    digest_after: str | None


def read_stop_state_once(
    pack: dict[str, Any], root: Path, reader: StopStateReader
) -> StopStateRead:
    path = _stop_state_path(pack, root)
    before = _digest(path)
    try:
        value, error = reader(path), None
    except StopStateUnreadable as exc:
        value, error = None, str(exc)
    return StopStateRead(value, error, before, _digest(path))


def check_ks_s1_determinate(pack: dict[str, Any], read: StopStateRead) -> CheckOutcome:
    """KS-S1 — the stop state is readable and resolves to one declared state."""
    absent = _missing(pack, "stop_state_ref", "declared_states")
    if absent:
        return _unknown("KS-S1", *absent)
    if not isinstance(pack["declared_states"], (list, tuple, set)):
        return _unknown("KS-S1", "declared_states")
    declared = list(pack["declared_states"])
    if ENGAGED not in declared or DISENGAGED not in declared:
        return _unknown("KS-S1", "declared_states")
    if read.error is not None:
        return _fail("KS-S1", f"stop state unreadable: {read.error}")
    if read.value not in declared:
        return _fail(
            "KS-S1",
            f"stop state {read.value!r} is not one of the declared states {sorted(declared)}",
        )
    return _ok("KS-S1", f"stop state reads {read.value}")


def check_ks_s2_read_is_not_a_write(
    pack: dict[str, Any], read: StopStateRead
) -> CheckOutcome:
    """KS-S2 — reading the stop state did not change it.

    A reader that writes turns every inspection into a state change, so the
    value the gate acts on is a value the gate itself produced.

    Unreadability is KS-S1's to report. Here it only means non-mutation could
    not be established, which is UNKNOWN — accusing twice on one fact would
    inflate a single defect into two.
    """
    absent = _missing(pack, "stop_state_ref")
    if absent:
        return _unknown("KS-S2", *absent)
    if read.digest_before is None or read.digest_after is None:
        return CheckOutcome(
            "KS-S2",
            Verdict.UNKNOWN,
            "non-mutation not established: the stop state could not be digested "
            "(KS-S1 reports the unreadability itself)",
        )
    if read.digest_after != read.digest_before:
        return _fail(
            "KS-S2",
            f"reading the stop state changed it: {read.digest_before[:16]}… -> "
            f"{read.digest_after[:16]}…",
        )
    return _ok("KS-S2")


def check_ks_s3_no_runner_write_path(pack: dict[str, Any]) -> CheckOutcome:
    """KS-S3 — the runner declares no write path to the stop state.

    Declared-empty is not undeclared: an explicit ``[]`` is an operator saying
    there is none, and passes. An absent field is UNKNOWN.
    """
    if pack.get("runner_write_paths") is None:
        return _unknown("KS-S3", "runner_write_paths")
    paths = list(pack["runner_write_paths"])
    if paths:
        return _fail(
            "KS-S3",
            f"runner declares {len(paths)} write path(s) to the stop state: {sorted(map(str, paths))}",
        )
    return _ok("KS-S3", "no runner write path declared")


# --------------------------------------------------------------------------
# drill
# --------------------------------------------------------------------------


def check_ks_d1_cadence(
    drill: dict[str, Any], evaluated_at: Any, cadence_days: Any
) -> CheckOutcome:
    """KS-D1 — the last drill is no older than the preregistered cadence."""
    completed = _parse_utc(drill.get("completed_at_utc"))
    evaluated = _parse_utc(evaluated_at)
    absent = []
    if completed is None:
        absent.append("drill_completed_at_utc")
    if evaluated is None:
        absent.append("evaluated_at_utc")
    if cadence_days is None:
        absent.append("cadence_days")
    if absent:
        return _unknown("KS-D1", *absent)
    try:
        cadence = int(cadence_days)
    except (TypeError, ValueError):
        return _unknown("KS-D1", "cadence_days")
    age = evaluated - completed
    if age > timedelta(days=cadence):
        return _fail(
            "KS-D1",
            f"last drill is {age.days}d old, cadence is {cadence}d",
        )
    return _ok("KS-D1", f"last drill {age.days}d old within {cadence}d")


def check_ks_d2_transition(drill: dict[str, Any]) -> CheckOutcome:
    """KS-D2 — the drill records a real transition ending in ENGAGED."""
    absent = []
    if drill.get("before_state") is None:
        absent.append("drill_before_state")
    if drill.get("after_state") is None:
        absent.append("drill_after_state")
    if absent:
        return _unknown("KS-D2", *absent)
    before, after = drill["before_state"], drill["after_state"]
    if before == after:
        return _fail(
            "KS-D2",
            f"no transition: before_state == after_state == {before!r}",
        )
    if after != ENGAGED:
        return _fail(
            "KS-D2",
            f"drill ended in {after!r}; a drill that never engaged the switch proves nothing",
        )
    return _ok("KS-D2", f"{before} -> {after}")


def check_ks_d3_environment_unchanged(
    drill: dict[str, Any], current: Any
) -> CheckOutcome:
    """KS-D3 — no relevant change has invalidated the drill since it ran."""
    recorded = drill.get("environment")
    absent = []
    if not isinstance(recorded, dict):
        absent.append("drill_environment")
    if not isinstance(current, dict):
        absent.append("current_environment")
    if absent:
        return _unknown("KS-D3", *absent)
    undeclared = [k for k in ENVIRONMENT_KEYS if recorded.get(k) is None or current.get(k) is None]
    if undeclared:
        return _unknown("KS-D3", *(f"drill_environment.{k}" for k in undeclared))
    changed = [k for k in ENVIRONMENT_KEYS if recorded[k] != current[k]]
    if changed:
        return _fail(
            "KS-D3",
            f"drill invalidated by change to {', '.join(changed)} — a new drill is required "
            "regardless of the cadence window",
        )
    return _ok("KS-D3")


def check_ks_d4_attestation(
    attestation: Any, drill: dict[str, Any], current: Any
) -> CheckOutcome:
    """KS-D4 — an operator attested physical separation, and not before the last change.

    This check cannot establish that the attestation is true. It establishes
    that one exists, that it is dated, and that it is not older than the
    deployment it is supposed to describe.
    """
    if not isinstance(attestation, dict):
        attestation = {}
    if not isinstance(current, dict):
        current = {}
    absent = []
    if attestation.get("by") is None:
        absent.append("operator_attestation_by")
    attested_at = _parse_utc(attestation.get("at_utc"))
    if attested_at is None:
        absent.append("operator_attestation_at_utc")
    if absent:
        return _unknown("KS-D4", *absent)
    changed_at = _parse_utc(current.get("changed_at_utc"))
    if changed_at is not None and attested_at < changed_at:
        return _fail(
            "KS-D4",
            f"attestation dated {attestation['at_utc']} predates the last relevant change "
            f"at {current.get('changed_at_utc')}",
        )
    drilled_at = _parse_utc(drill.get("completed_at_utc"))
    if drilled_at is not None and attested_at < drilled_at - timedelta(days=365):
        return _fail(
            "KS-D4",
            "attestation is more than a year older than the drill it is supposed to cover",
        )
    return _ok("KS-D4", f"attested by {attestation['by']} at {attestation['at_utc']}")


def check_ks_d5_verdict_substantiated(drill: dict[str, Any]) -> CheckOutcome:
    """KS-D5 — a declared PASS is substantiated by the transition it claims.

    The claim is the evidence. A drill that reports success without recording
    the state change it consisted of is evidence_forgery_detected, exactly as a
    PASS claim with empty probes already is (runner.stops).
    """
    if drill.get("result") is None:
        return _unknown("KS-D5", "drill_result")
    if str(drill["result"]).upper() != "PASS":
        return _ok("KS-D5", f"drill declares {drill['result']!r}; nothing to substantiate")
    if drill.get("before_state") is None or drill.get("after_state") is None:
        return _fail(
            "KS-D5",
            "drill declares result PASS with no recorded transition — a declared verdict "
            "is not a drill",
        )
    return _ok("KS-D5", "declared PASS carries its transition")


# --------------------------------------------------------------------------
# entry point
# --------------------------------------------------------------------------


def detect_kill_switch(
    pack: dict[str, Any],
    *,
    stop_state_root: Path,
    cadence_days: Any,
    reader: StopStateReader | None = None,
) -> list[CheckOutcome]:
    """Run every UPTM-003 check that lives in the detector.

    KS-G1 is deliberately absent: its input is the gate's own composed verdict,
    so it is evaluated in runner.gates.evaluate_gate and nowhere else.
    """
    reader = reader or read_stop_state_file
    drill = pack.get("drill")
    if not isinstance(drill, dict):
        # A malformed drill is not a drill. Every drill check then reports
        # UNKNOWN, which denies — silently reading it as empty would let a
        # broken declaration look like an honest absence.
        drill = {}
    current = pack.get("current_environment")
    read = (
        read_stop_state_once(pack, stop_state_root, reader)
        if pack.get("stop_state_ref") is not None
        else StopStateRead(None, "stop_state_ref undeclared", None, None)
    )
    return [
        check_ks_p1_declaration(pack),
        check_ks_s1_determinate(pack, read),
        check_ks_s2_read_is_not_a_write(pack, read),
        check_ks_s3_no_runner_write_path(pack),
        check_ks_d1_cadence(drill, pack.get("evaluated_at_utc"), cadence_days),
        check_ks_d2_transition(drill),
        check_ks_d3_environment_unchanged(drill, current),
        check_ks_d4_attestation(pack.get("operator_attestation"), drill, current),
        check_ks_d5_verdict_substantiated(drill),
    ]


def stop_state_is_engaged(
    pack: dict[str, Any], *, stop_state_root: Path, reader: StopStateReader | None = None
) -> bool | None:
    """Read the stop state for KS-G1. None when it cannot be determined.

    None is not False. A stop state that cannot be read is not a stop state that
    is off.

    This is a second read of the same file, and it is safe precisely where it
    matters: the gate only escalates on it when the composed verdict is PASS,
    which requires KS-S2 to have passed — that is, to have demonstrated that
    reading this stop state does not change it.
    """
    reader = reader or read_stop_state_file
    if not isinstance(pack, dict) or pack.get("stop_state_ref") is None:
        return None
    try:
        value = reader(_stop_state_path(pack, stop_state_root))
    except StopStateUnreadable:
        return None
    if value == ENGAGED:
        return True
    if value == DISENGAGED:
        return False
    return None
