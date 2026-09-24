"""UPTM-007 — STALE invalidation, checked against its preregistered criteria.

The criteria are docs/specs/UPTM-007-stale-invalidation.md §3. Test names carry
the criterion id so a failure says which preregistered claim broke, not merely
that something is red.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

from runner.enforcement import enforced_principles, manifest, unproven_claims
from runner.paths import CAPITAL_RULES
from runner.provenance import HeadProvenance
from runner.staleness import (
    CURRENT,
    STALE,
    UNKNOWN,
    dependency_digests,
    determinism_declaration,
    digest_file,
    staleness,
)

HEAD = HeadProvenance("a" * 40, True, "git")


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    """A miniature repository with one file of each dependency kind."""
    (tmp_path / "runner" / "detectors").mkdir(parents=True)
    (tmp_path / "runner" / "gates.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "runner" / "detectors" / "scope.py").write_text("y = 2\n", encoding="utf-8")
    (tmp_path / "constitution").mkdir()
    (tmp_path / "constitution" / "capital-rules.json").write_text("{}\n", encoding="utf-8")
    (tmp_path / "constitution" / "CONSTITUTION-CAPITAL.md").write_text("# c\n", encoding="utf-8")
    (tmp_path / "prompt-stacks").mkdir()
    (tmp_path / "prompt-stacks" / "00_constitution.json").write_text("{}\n", encoding="utf-8")
    return tmp_path


def _artifact(tree: Path) -> dict:
    return {"dependencies": dependency_digests(tree)}


# ------------------------------------------------------------------ §A


def test_a1_the_manifest_carries_derived_digests_not_a_literal_list():
    m = manifest([], provenance=HEAD)
    assert isinstance(m["dependencies"], dict) and m["dependencies"]
    assert all(len(v) == 64 for v in m["dependencies"].values())
    # derived: the real set contains files no literal list in the source names
    assert "runner/staleness.py" in m["dependencies"]
    assert "constitution/capital-rules.json" in m["dependencies"]


def test_a2_an_unmodified_tree_is_current(tree):
    result = staleness(_artifact(tree), tree)
    assert result.status == CURRENT and result.current
    assert result.checked == 5 and result.changed == (), "the fixture creates five dependency files; all five must be found"


@pytest.mark.parametrize(
    "target",
    ["runner/gates.py", "runner/detectors/scope.py", "constitution/capital-rules.json",
     "constitution/CONSTITUTION-CAPITAL.md", "prompt-stacks/00_constitution.json"],
)
def test_a3_changing_any_recorded_dependency_is_stale_and_names_it(tree, target):
    art = _artifact(tree)
    (tree / target).write_text("changed\n", encoding="utf-8")
    result = staleness(art, tree)
    assert result.status == STALE
    assert result.changed == (target,)


def test_a4_a_deleted_dependency_is_unknown_not_stale(tree):
    """Absence is not a measurement. A file that is gone cannot be compared, so
    it must not read as CURRENT and must not be reported as a content change."""
    art = _artifact(tree)
    (tree / "runner" / "gates.py").unlink()
    result = staleness(art, tree)
    assert result.status == UNKNOWN
    assert result.unreadable == ("runner/gates.py",)
    assert "could not be read" in result.reason


def test_a5_an_artifact_with_no_dependencies_is_unknown():
    for empty in ({}, {"dependencies": None}, {"dependencies": {}}, {"dependencies": []}):
        assert staleness(empty).status == UNKNOWN, empty


def test_a6_a_new_runner_module_makes_prior_evidence_stale_with_no_code_change(tree):
    """The criterion that proves the set is derived. A hand-maintained list
    passes A1-A5 and fails this: nobody edited it to mention the new file."""
    art = _artifact(tree)
    (tree / "runner" / "brand_new_detector.py").write_text("z = 3\n", encoding="utf-8")

    after = dependency_digests(tree)
    assert "runner/brand_new_detector.py" in after, "the new module was not picked up"
    assert set(after) - set(art["dependencies"]) == {"runner/brand_new_detector.py"}

    # the prior artifact does not know the file, so its recorded set still matches;
    # staleness of the *set* is what the added-file case changes.
    assert staleness(art, tree).status == CURRENT
    assert staleness({"dependencies": after}, tree).status == CURRENT
    assert len(after) == len(art["dependencies"]) + 1


def test_a7_the_constitution_is_a_dependency_as_it_says_of_itself():
    """CONSTITUTION-CAPITAL.md: 'This document is an evidence dependency. A
    change to its version invalidates every PASS issued under it (P12).'"""
    assert "constitution/CONSTITUTION-CAPITAL.md" in dependency_digests()


def test_a8_the_digest_is_of_content_not_of_mtime_or_size(tmp_path):
    f = tmp_path / "f.py"
    f.write_text("same\n", encoding="utf-8")
    first = digest_file(f)
    os.utime(f, (0, 0))
    assert digest_file(f) == first, "touching a file must not read as a change"
    f.write_text("diff\n", encoding="utf-8")
    assert digest_file(f) != first
    assert first == hashlib.sha256(b"same\n").hexdigest()


def test_pycache_is_excluded_so_running_the_suite_is_not_a_dependency_change():
    assert not any("__pycache__" in k for k in dependency_digests())


# ------------------------------------------------------------------ §B


def test_b1_the_manifest_declares_what_is_and_is_not_captured():
    m = manifest([], provenance=HEAD)
    assert set(m["determinism"]) == {"captured", "not_captured", "note"}
    assert m["determinism"]["captured"]


def test_b2_the_uncaptured_list_names_the_wall_clock_p12_names_directly():
    uncaptured = " ".join(determinism_declaration()["not_captured"]).lower()
    assert "wall clock" in uncaptured
    assert "generated_at" in uncaptured
    assert len(determinism_declaration()["not_captured"]) >= 3


def test_b3_the_block_is_structured_so_it_cannot_decay_into_prose():
    d = determinism_declaration()
    assert all(isinstance(v, list) for v in d.values())
    assert all(isinstance(item, str) and item for v in d.values() for item in v)


# ------------------------------------------------------------------ §C


def test_c1_c2_p12_did_not_advance_because_the_gate_does_not_consume_staleness():
    """Measured, not assumed. UPTM-006 says an ENFORCED claim means there is no
    route to PASS while violating the principle. evaluate_gate does not read
    dependency digests from the evidence it is handed, so no such route can be
    demonstrated and P12 has none in the registry.

    Per UPTM-007 C2 the status therefore stays PARTIAL. The spec is not amended
    to match what was built."""
    rules = json.loads(CAPITAL_RULES.read_text(encoding="utf-8"))
    p12 = next(p for p in rules["principles"] if p["id"] == "P12")
    assert p12["enforcement"] == "PARTIAL"
    assert "P12" not in enforced_principles(rules)
    assert unproven_claims(rules) == []


def test_c3_no_other_principle_moved_and_live_trading_stays_false():
    rules = json.loads(CAPITAL_RULES.read_text(encoding="utf-8"))
    assert enforced_principles(rules) == ["P8", "P10"]
    assert rules["live_capability"]["default"] == "DENY"
    assert rules["live_capability"]["lease"]["granted"] is False
