"""Detector for `scope_undeclared` and `scope_contradicted`.

Implements the criteria preregistered in
docs/specs/UPTM-005-evidence-scope-declaration.md, written before this module
existed (CC/P4).

Why this exists
---------------
UPTM-003 and UPTM-004 each guard a door. Neither guards the doorway: a detector
cannot check a pack it is never handed, so both principles were steppable around
by omission. This makes the declaration mandatory, so that omission denies
instead of passing unexamined.

What it does not claim
----------------------
That a declaration is true. A gate declaring `live_bearing: false` while
actually bearing LIVE has not avoided the check — it has stated something untrue
in signed evidence, which is forgery rather than avoidance and belongs to
UPTM-002.
"""

from __future__ import annotations

from typing import Any

from runner.detectors.fabrication import CheckOutcome, _fail, _ok, _unknown
from runner.verdict import Verdict

#: Each flag, the packs it makes mandatory, and the name used in messages.
BEARINGS = (
    ("capital_bearing", ("capital",), "capital"),
    ("live_bearing", ("kill_switch", "kill_switch_drill"), "LIVE"),
)


def check_sc_p1_scope_declared(evidence: dict[str, Any]) -> CheckOutcome:
    """A gate that says nothing says nothing, and silence denies."""
    scope = evidence.get("scope")
    if not isinstance(scope, dict):
        return _unknown(
            "SC-P1",
            ["scope — every gate declares what it bears; there is no default"],
        )
    absent = [
        flag
        for flag, _packs, _label in BEARINGS
        if not isinstance(scope.get(flag), bool)
    ]
    if absent:
        return _unknown(
            "SC-P1",
            [f"scope.{a} as a boolean — a string is not a declaration" for a in absent],
        )
    borne = [label for flag, _packs, label in BEARINGS if scope[flag]] or ["nothing"]
    return _ok("SC-P1", f"gate declares it bears {', '.join(borne)}")


def check_sc_i1_declared_packs_present(evidence: dict[str, Any]) -> list[CheckOutcome]:
    """What a gate declares it bears, it must bring the evidence for."""
    scope = evidence.get("scope")
    if not isinstance(scope, dict):
        return []
    outcomes: list[CheckOutcome] = []
    for index, (flag, packs, label) in enumerate(BEARINGS, start=1):
        check_id = f"SC-I{index}"
        if scope.get(flag) is not True:
            continue
        missing = [p for p in packs if evidence.get(p) is None]
        if missing:
            outcomes.append(
                _unknown(
                    check_id,
                    [f"{', '.join(missing)} — the gate declares it bears {label}"],
                )
            )
        else:
            outcomes.append(_ok(check_id, f"{label}-bearing gate carries {', '.join(packs)}"))
    return outcomes


def check_sc_i3_no_opting_out_while_carrying(evidence: dict[str, Any]) -> CheckOutcome:
    """The check with teeth.

    Declaring yourself out of scope while carrying the very thing the scope
    governs is not sloppiness. It is the step-around P8 and P10 were open to,
    done explicitly.
    """
    scope = evidence.get("scope")
    if not isinstance(scope, dict):
        return _unknown("SC-I3", ["scope"])
    contradictions = [
        f"{pack} present while scope.{flag} is false"
        for flag, packs, _label in BEARINGS
        if scope.get(flag) is False
        for pack in packs
        if evidence.get(pack) is not None
    ]
    if contradictions:
        return _fail(
            "SC-I3",
            "gate_bypass_attempt: " + "; ".join(contradictions),
        )
    return _ok("SC-I3", "no pack is carried by a gate that declares it does not bear it")


def detect_scope(evidence: dict[str, Any]) -> list[CheckOutcome]:
    return [
        check_sc_p1_scope_declared(evidence),
        *check_sc_i1_declared_packs_present(evidence),
        check_sc_i3_no_opting_out_while_carrying(evidence),
    ]


def bears(evidence: dict[str, Any], flag: str) -> bool:
    """Whether the gate declared it bears this. Absence is not a yes and not a no."""
    scope = evidence.get("scope")
    return isinstance(scope, dict) and scope.get(flag) is True
