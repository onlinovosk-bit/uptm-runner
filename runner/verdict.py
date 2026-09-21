"""Canonical three-valued verdicts and the single resolution path.

Governance already declares the semantics (constitution/GOVERNANCE.md C1,
constitution/capital-rules.json conflict_resolution). This module makes them
executable so that no detector has to interpret UNKNOWN for itself.

    detector -> Verdict -> GateResult -> resolve -> Decision

A detector returns a verdict. It never returns a decision. Resolution happens
here and only here.
"""

from __future__ import annotations

import json
from enum import Enum
from typing import Any

from runner.paths import CAPITAL_RULES


class Verdict(str, Enum):
    """What the evidence shows about a prerequisite or invariant."""

    #: demonstrably satisfied
    PASS = "PASS"
    #: demonstrably violated — may raise a stop condition
    FAIL = "FAIL"
    #: cannot be evaluated from the available preregistered evidence or
    #: parameters — never renamed to FAIL merely so it can be recorded as a stop
    UNKNOWN = "UNKNOWN"


class Decision(str, Enum):
    """What the system is permitted to do as a result."""

    ALLOW = "ALLOW"
    DENY = "DENY"


def resolve(verdict: Verdict | str | None) -> Decision:
    """PASS -> ALLOW. Everything else, including anything unrecognised -> DENY."""
    try:
        return Decision.ALLOW if Verdict(verdict) is Verdict.PASS else Decision.DENY
    except ValueError:
        return Decision.DENY


def resolve_all(verdicts: list[Verdict | str | None]) -> Decision:
    """ALLOW only if every verdict resolves to ALLOW. An empty set is not proof."""
    if not verdicts:
        return Decision.DENY
    return (
        Decision.ALLOW
        if all(resolve(v) is Decision.ALLOW for v in verdicts)
        else Decision.DENY
    )


def _matrix() -> list[dict[str, Any]]:
    rules = json.loads(CAPITAL_RULES.read_text(encoding="utf-8"))
    return rules["conflict_resolution"]["matrix"]


def resolve_planes(cp: Decision | str | None, cc: Decision | str | None) -> Decision:
    """Resolve a Control Plane and a Capital Capability decision against each other.

    The matrix is read from constitution/capital-rules.json — the governance
    artifact itself, not a second copy of the rules in code. A pair with no row,
    or any unreadable input, resolves to DENY (GOVERNANCE.md C3: silence is not
    permission).
    """
    cp_s = cp.value if isinstance(cp, Decision) else cp
    cc_s = cc.value if isinstance(cc, Decision) else cc
    try:
        rows = _matrix()
    except (OSError, json.JSONDecodeError, KeyError):
        return Decision.DENY
    for row in rows:
        if row.get("cp") == cp_s and row.get("cc") == cc_s:
            return Decision.ALLOW if row.get("result") == "ALLOW" else Decision.DENY
    return Decision.DENY
