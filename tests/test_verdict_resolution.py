"""UPTM-002a — the canonical three-valued decision path.

Governance declared PASS/FAIL/UNKNOWN and UNKNOWN -> DENY before any code could
express it. These tests exist so that the declaration and the runtime cannot
drift apart, and so that no future detector has to invent its own reading of
UNKNOWN.
"""

from __future__ import annotations

import dataclasses
import json

import pytest

from runner.gates import GateResult
from runner.paths import CAPITAL_RULES, RULES
from runner.verdict import Decision, Verdict, resolve, resolve_all, resolve_planes

DECISIONS = ("ALLOW", "DENY", "UNKNOWN")


# 1. Verdict type


def test_verdict_has_exactly_three_values():
    assert {v.value for v in Verdict} == {"PASS", "FAIL", "UNKNOWN"}


def test_decision_has_exactly_two_values():
    assert {d.value for d in Decision} == {"ALLOW", "DENY"}


# 2. GateResult carries the verdict, and cannot hold a second state


def test_gate_result_stores_verdict_not_a_boolean():
    fields = {f.name for f in dataclasses.fields(GateResult)}
    assert "verdict" in fields
    assert "passed" not in fields, "passed must be derived, never a second state source"


def test_passed_is_derived_from_verdict():
    assert GateResult(Verdict.PASS).passed is True
    assert GateResult(Verdict.FAIL).passed is False
    assert GateResult(Verdict.UNKNOWN).passed is False


def test_passed_cannot_be_set_independently():
    with pytest.raises(AttributeError):
        GateResult(Verdict.UNKNOWN).passed = True  # type: ignore[misc]


def test_gate_result_decision_uses_the_canonical_resolver():
    assert GateResult(Verdict.PASS).decision is Decision.ALLOW
    assert GateResult(Verdict.FAIL).decision is Decision.DENY
    assert GateResult(Verdict.UNKNOWN).decision is Decision.DENY


# 3 + 5 + 6. One resolver; every branch asserted


@pytest.mark.parametrize(
    ("verdict", "expected"),
    [
        (Verdict.PASS, Decision.ALLOW),
        (Verdict.FAIL, Decision.DENY),
        (Verdict.UNKNOWN, Decision.DENY),
    ],
)
def test_each_verdict_branch_resolves_as_governance_declares(verdict, expected):
    assert resolve(verdict) is expected


@pytest.mark.parametrize("bad", [None, "", "pass", "Pass", "ALLOW", "nonsense", 0, object()])
def test_unrecognised_input_resolves_to_deny(bad):
    assert resolve(bad) is Decision.DENY


def test_empty_verdict_set_is_not_proof():
    assert resolve_all([]) is Decision.DENY


def test_one_non_pass_verdict_denies_the_whole_set():
    assert resolve_all([Verdict.PASS, Verdict.PASS]) is Decision.ALLOW
    assert resolve_all([Verdict.PASS, Verdict.UNKNOWN]) is Decision.DENY
    assert resolve_all([Verdict.PASS, Verdict.FAIL]) is Decision.DENY


# 4. The resolver reads the governance artifact, not a second copy in code


def test_resolver_follows_the_governance_matrix_when_it_changes(tmp_path, monkeypatch):
    """Mutate the matrix on disk; a hardcoded copy in code would ignore this."""
    assert resolve_planes("ALLOW", "ALLOW") is Decision.ALLOW

    rules = json.loads(CAPITAL_RULES.read_text(encoding="utf-8"))
    for row in rules["conflict_resolution"]["matrix"]:
        if row["cp"] == "ALLOW" and row["cc"] == "ALLOW":
            row["result"] = "DENY"
    mutated = tmp_path / "capital-rules.json"
    mutated.write_text(json.dumps(rules), encoding="utf-8")
    monkeypatch.setattr("runner.verdict.CAPITAL_RULES", mutated)

    assert resolve_planes("ALLOW", "ALLOW") is Decision.DENY


def test_unreadable_governance_matrix_denies(tmp_path, monkeypatch):
    monkeypatch.setattr("runner.verdict.CAPITAL_RULES", tmp_path / "absent.json")
    assert resolve_planes("ALLOW", "ALLOW") is Decision.DENY

    corrupt = tmp_path / "corrupt.json"
    corrupt.write_text("{not json", encoding="utf-8")
    monkeypatch.setattr("runner.verdict.CAPITAL_RULES", corrupt)
    assert resolve_planes("ALLOW", "ALLOW") is Decision.DENY


def test_pair_with_no_matrix_row_denies():
    assert resolve_planes("ALLOW", "MAYBE") is Decision.DENY
    assert resolve_planes(None, None) is Decision.DENY


# 8. The capital plane cannot grant control-plane authority through the resolver


@pytest.mark.parametrize("cp", DECISIONS)
@pytest.mark.parametrize("cc", DECISIONS)
def test_allow_requires_both_planes(cp, cc):
    expected = Decision.ALLOW if (cp == "ALLOW" and cc == "ALLOW") else Decision.DENY
    assert resolve_planes(cp, cc) is expected


def test_capital_plane_alone_never_produces_allow():
    for cp in ("DENY", "UNKNOWN"):
        assert resolve_planes(cp, "ALLOW") is Decision.DENY


# 7. The control plane itself is untouched


def test_control_plane_rules_still_fail_closed_and_live_trading_off():
    rules = json.loads(RULES.read_text(encoding="utf-8"))
    assert rules["live_trading"] is False
    assert rules["fail_closed"] is True
