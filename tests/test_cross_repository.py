"""UPTM-015: two verdicts, two repositories, and no winner.

Criteria are preregistered in `docs/specs/UPTM-015-close-map-q1-q2.md`, written
before this file existed. Each test names the criterion it discharges.

The last test in this file is the most important one: it asserts the mechanism
is **not** wired into the gate. Turning it on denies every current PASS, so it
must be a deliberate act with its own GO rather than a drift nobody noticed.
"""

from __future__ import annotations

import ast
import itertools
import json
from collections import Counter

import pytest

from runner.cross_repository import (
    CONTROL_PLANE,
    TRADING_SYSTEM,
    cross_repository_status,
    resolve_cross_repository,
)
from runner.paths import CAPITAL_RULES, ROOT
from runner.verdict import Decision

MAP = ROOT / "docs" / "architecture" / "governance-map.md"

NOT_A_DECISION = (None, "", "ALLOWED", "PASS", "allow", 1, object())


# --------------------------------------------------------------------------
# G1 / G2 - the closures are recorded, in the document and in the log
# --------------------------------------------------------------------------


@pytest.fixture(scope="module")
def governance_map() -> str:
    """Line wrapping is a typesetting choice, not a claim - so normalise it."""
    return " ".join(MAP.read_text(encoding="utf-8").split())


def test_g1_q1_is_adopted_yes_with_the_reason_that_no_empties_the_runner(governance_map):
    assert "**DECIDED (DEC-UPTM-MAP-Q1, 2026-09-28): YES.**" in governance_map
    assert "enforced against something that never runs" in governance_map
    # Adopting yes creates a requirement; it does not claim the link exists.
    assert "named unmet requirement" in governance_map


def test_g2_q2_is_adopted_neither_wins_and_derived_rather_than_chosen(governance_map):
    assert "**DECIDED (DEC-UPTM-MAP-Q2, 2026-09-28): NEITHER WINS.**" in governance_map
    assert "a tie; it is uncertainty" in governance_map
    assert "silence is not permission" in governance_map


def test_g1_g2_the_decisions_log_carries_both(governance_map):
    log = (ROOT / "docs" / "decisions.md").read_text(encoding="utf-8")
    assert "DEC-UPTM-MAP-Q1" in log and "DEC-UPTM-MAP-Q2" in log
    assert "[2026-09-28] DEC-UPTM-015" in log


# --------------------------------------------------------------------------
# G3 - the whole cross-product, not an example
# --------------------------------------------------------------------------


@pytest.mark.parametrize("ours,theirs", list(itertools.product(Decision, Decision)))
def test_g3_allow_only_when_both_sides_allow(ours, theirs):
    result = resolve_cross_repository(ours, theirs)
    both_allow = ours is theirs is Decision.ALLOW
    assert (result.decision is Decision.ALLOW) is both_allow


def test_g3_the_allow_case_exists_so_this_is_a_gate_not_a_wall():
    result = resolve_cross_repository(Decision.ALLOW, Decision.ALLOW)
    assert result.decision is Decision.ALLOW
    assert result.disputed is False
    assert result.missing == ()


# --------------------------------------------------------------------------
# G4 - absence is not a measurement
# --------------------------------------------------------------------------


@pytest.mark.parametrize("junk", NOT_A_DECISION)
def test_g4_an_unreadable_verdict_on_either_side_denies(junk):
    assert resolve_cross_repository(junk, Decision.ALLOW).decision is Decision.DENY
    assert resolve_cross_repository(Decision.ALLOW, junk).decision is Decision.DENY


def test_g4_the_missing_side_is_named_not_merely_counted():
    result = resolve_cross_repository(Decision.ALLOW, None)
    assert result.missing == (TRADING_SYSTEM,)
    assert TRADING_SYSTEM in result.reason

    both = resolve_cross_repository(None, None)
    assert both.missing == (CONTROL_PLANE, TRADING_SYSTEM)


def test_g4_an_absent_counterpart_is_not_a_dispute():
    """Nobody disagreed. One side never spoke, which is a different failure."""
    result = resolve_cross_repository(Decision.ALLOW, None)
    assert result.disputed is False
    assert "not an ALLOW" in result.reason


# --------------------------------------------------------------------------
# G5 - a disagreement is a dispute, not a defeat
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "ours,theirs", [(Decision.ALLOW, Decision.DENY), (Decision.DENY, Decision.ALLOW)]
)
def test_g5_a_disagreement_keeps_both_sides_and_names_neither_a_winner(ours, theirs):
    result = resolve_cross_repository(ours, theirs)
    assert result.decision is Decision.DENY
    assert result.disputed is True
    assert result.control_plane == ours.value
    assert result.trading_system == theirs.value
    assert "neither wins" in result.reason
    assert "P11" in result.reason
    for word in ("wins the", "overrules", "overrides"):
        assert word not in result.reason


def test_g5_agreement_to_deny_is_not_a_dispute():
    result = resolve_cross_repository(Decision.DENY, Decision.DENY)
    assert result.decision is Decision.DENY
    assert result.disputed is False


# --------------------------------------------------------------------------
# G6 - today's state, measured
# --------------------------------------------------------------------------


def test_g6_no_trading_system_verdict_is_reachable_from_here():
    """The gap named in one sentence by the governance map, as a value."""
    status = cross_repository_status()
    assert status.decision is Decision.DENY
    assert status.missing == (TRADING_SYSTEM,)
    assert status.trading_system is None


# --------------------------------------------------------------------------
# G7 - closing a question changes no principle's state
# --------------------------------------------------------------------------


def test_g7_the_enforcement_states_are_exactly_what_they_were():
    rules = json.loads(CAPITAL_RULES.read_text(encoding="utf-8"))

    def states(node, out=None):
        out = [] if out is None else out
        if isinstance(node, dict):
            if isinstance(node.get("enforcement"), str):
                out.append(node["enforcement"])
            for value in node.values():
                states(value, out)
        elif isinstance(node, list):
            for value in node:
                states(value, out)
        return out

    assert Counter(states(rules)) == {
        "PARTIAL": 6,
        "MISSING": 4,
        "ENFORCED": 3,
        "DECLARATIVE": 1,
    }


# --------------------------------------------------------------------------
# G8 - the document cannot contradict itself
# --------------------------------------------------------------------------


def test_g8_the_map_does_not_still_call_q1_or_q2_open(governance_map):
    for question in ("DEC-UPTM-MAP-Q1", "DEC-UPTM-MAP-Q2"):
        assert f"OPEN ({question}" not in governance_map
        assert f"stays open under `{question}`" not in governance_map
    # The two that really are still open must not have been swept up with them.
    assert "stays open under `DEC-UPTM-MAP-Q3`" in governance_map
    assert "stays open under `DEC-UPTM-MAP-Q5`" in governance_map


def test_g8_closing_them_is_recorded_as_creating_work(governance_map):
    assert "creates work rather than" in governance_map


# --------------------------------------------------------------------------
# L2 - THE SWITCH IS OFF, AND THAT IS THE POINT
# --------------------------------------------------------------------------


def test_l2_the_gate_does_not_consult_the_trading_system_yet():
    """Derived from the module's AST, not from memory.

    Wiring this in denies every current PASS, because no trading-system verdict
    exists and that repository is not even in scope here. This test fails on the
    day somebody connects it - which is the point. A switch that is off and
    known is safe; a switch that is off and forgotten is the next DECLARATIVE
    principle.
    """
    source = (ROOT / "runner" / "gates.py").read_text(encoding="utf-8")
    imported: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
        elif isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)

    assert "runner.cross_repository" not in imported, (
        "the cross-repository resolution has been wired into the gate; that "
        "denies every current PASS and needs its own Founder GO"
    )
    assert "cross_repository" not in source
