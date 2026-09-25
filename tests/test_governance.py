"""Governance binding tests.

These tests exist so that a governance document cannot be silently detached from the
agents that must read it, and so that an enforcement claim cannot be made without a
named mechanism (GOVERNANCE.md §2.2 — declarative is never PASS).
"""

from __future__ import annotations

import json

from runner.paths import (
    CAPITAL_RULES,
    CC_CONSTITUTION,
    CONSTITUTION,
    CP_CONSTITUTION,
    GOVERNANCE,
    PROMPT_STACKS,
    ROOT,
    RULES,
    WAVES,
)

ENFORCEMENT_STATES = {"ENFORCED", "PARTIAL", "DECLARATIVE", "MISSING", "CONFLICT"}
PRINCIPLE_IDS = {f"P{n}" for n in range(1, 15)}


def _stack00() -> dict:
    return json.loads((PROMPT_STACKS / "00_constitution.json").read_text(encoding="utf-8"))


def _capital_rules() -> dict:
    return json.loads(CAPITAL_RULES.read_text(encoding="utf-8"))


def test_all_governance_documents_exist():
    for path in (CP_CONSTITUTION, CC_CONSTITUTION, GOVERNANCE, RULES, CAPITAL_RULES):
        assert path.is_file(), f"missing governance artifact: {path}"


def test_every_constitution_file_is_bound_to_stack00():
    """A governance file not in `binds` is invisible to agents."""
    binds = set(_stack00()["binds"])
    on_disk = {
        f"constitution/{p.name}" for p in CONSTITUTION.iterdir() if p.is_file()
    }
    unbound = on_disk - binds
    assert not unbound, f"constitution files not bound to stack 00: {sorted(unbound)}"


def test_capital_rules_cover_all_fourteen_principles():
    ids = {p["id"] for p in _capital_rules()["principles"]}
    assert ids == PRINCIPLE_IDS, f"principle coverage mismatch: {sorted(PRINCIPLE_IDS ^ ids)}"


def test_enforcement_states_are_from_the_declared_vocabulary():
    for p in _capital_rules()["principles"]:
        assert p["enforcement"] in ENFORCEMENT_STATES, p


def test_enforced_claim_requires_a_named_mechanism():
    """Declarative is never PASS: ENFORCED/PARTIAL must name where enforcement lives."""
    for p in _capital_rules()["principles"]:
        if p["enforcement"] in ("ENFORCED", "PARTIAL"):
            assert p.get("mechanism"), f"{p['id']} claims {p['enforcement']} with no mechanism"
        else:
            assert p.get("mechanism") is None, f"{p['id']} is {p['enforcement']} but names a mechanism"


def test_unknown_and_silence_resolve_to_deny():
    cr = _capital_rules()["conflict_resolution"]
    assert cr["unknown_resolves_to"] == "DENY"
    assert cr["silence_resolves_to"] == "DENY"
    for row in cr["matrix"]:
        if "UNKNOWN" in (row["cp"], row["cc"]):
            assert row["result"] == "DENY", row


def test_conflict_matrix_allows_only_when_both_planes_allow():
    for row in _capital_rules()["conflict_resolution"]["matrix"]:
        expected = "ALLOW" if row["cp"] == "ALLOW" and row["cc"] == "ALLOW" else "DENY"
        assert row["result"] == expected, row


def test_live_requires_all_four_conditions_and_defaults_deny():
    live = _capital_rules()["live_capability"]
    assert live["default"] == "DENY"
    assert set(live["requires_all"]) == {
        "cp_live_trading_true",
        "cc_live_capability_lease_valid",
        "founder_approval_valid",
        "all_required_capital_gates_pass",
    }
    assert live["lease"]["granted"] is False
    assert live["lease"]["on_expiry"] == "DENY"
    assert live["lease"]["silence_is_renewal"] is False


def test_lease_and_cp_flag_cannot_substitute_for_each_other():
    live = _capital_rules()["live_capability"]
    assert live["lease_may_replace_cp_flag"] is False
    assert live["cp_flag_may_replace_lease"] is False


def test_map_q5_stays_open():
    """DEC-UPTM-MAP-Q5: neither 0–7 nor 0–9 is the canonical wave numbering."""
    text = (ROOT / "docs/architecture/governance-map.md").read_text(encoding="utf-8")
    start = text.index("5. **Which wave vocabulary")
    block = text[start : text.index("\n## What this document", start)]
    assert "DEC-UPTM-MAP-Q5" in block
    assert "OPEN" in block
    assert "neither numbering is canonical" in block
    assert "DECIDED" not in block
    for wave_id in range(8):
        assert (WAVES / f"wave{wave_id}.yaml").is_file()
    assert not (WAVES / "wave8.yaml").exists()
    assert not (WAVES / "wave9.yaml").exists()
    constitution = CC_CONSTITUTION.read_text(encoding="utf-8")
    assert "v1.0" in constitution.splitlines()[0]
    assert "| Status | **LOCKED** |" in constitution


def test_map_q2_stays_open():
    """DEC-UPTM-MAP-Q2: neither repository's PASS wins a disagreement."""
    text = (ROOT / "docs/architecture/governance-map.md").read_text(encoding="utf-8")
    start = text.index("2. **Which repository's verdict wins")
    block = text[start : text.index("\n3. ", start)]
    assert "DEC-UPTM-MAP-Q2" in block
    assert "OPEN" in block
    assert "neither repository's `PASS` wins" in block
    assert "DECIDED" not in block
    constitution = CC_CONSTITUTION.read_text(encoding="utf-8")
    assert "v1.0" in constitution.splitlines()[0]
    assert "| Status | **LOCKED** |" in constitution


def test_map_q1_stays_open():
    """DEC-UPTM-MAP-Q1: neither answer about a trading-system wave is adopted."""
    text = (ROOT / "docs/architecture/governance-map.md").read_text(encoding="utf-8")
    start = text.index("1. **Does a trading-system wave gate")
    block = text[start : text.index("\n2. ", start)]
    assert "DEC-UPTM-MAP-Q1" in block
    assert "OPEN" in block
    assert "neither answer is adopted" in block
    assert "DECIDED" not in block
    constitution = CC_CONSTITUTION.read_text(encoding="utf-8")
    assert "v1.0" in constitution.splitlines()[0]
    assert "| Status | **LOCKED** |" in constitution


def test_control_plane_live_trading_still_false():
    """The capital plane must never have loosened the control plane."""
    assert json.loads(RULES.read_text(encoding="utf-8"))["live_trading"] is False


def test_capital_plane_declares_no_gates_yet():
    gates = _capital_rules()["capital_gates"]
    assert gates["track"] == "parallel"
    assert gates["not_waves"] is True
    assert gates["defined"] == []


def test_preexisting_capabilities_default_to_stale():
    pre = _capital_rules()["preexisting_capability_status"]
    assert pre["default_state"] == "STALE"
    assert pre["items"]


def test_constitutions_are_versioned():
    for path in (CP_CONSTITUTION, CC_CONSTITUTION, GOVERNANCE):
        assert "Version" in path.read_text(encoding="utf-8"), f"{path} has no version header"
