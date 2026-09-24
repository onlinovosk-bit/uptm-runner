"""Evidence Rule A, as adapted for this repository.

Rule A is written in `onlinovosk-bit/onlinovosk-bit-uptm`
(`docs/EVIDENCE_RULE_A.md`). It has two halves, and only one applies here. The
tests below pin both the half that was adopted and the reason the other one is
inapplicable — because "it does not apply here" is exactly the kind of claim
that rots silently once the circumstance it rests on changes.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from runner.enforcement import manifest
from runner.paths import ROOT
from runner.provenance import HeadProvenance, read_head


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True, text=True, check=True,
    ).stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A real repository with one commit. Rule A is about git, so the test uses git."""
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "t@example.invalid")
    _git(root, "config", "user.name", "test")
    (root / "code.py").write_text("x = 1\n", encoding="utf-8")
    _git(root, "add", "code.py")
    _git(root, "commit", "-qm", "first")
    return root


# ------------------------------------------- the half that was adopted


def test_the_head_is_read_from_the_repository_not_taken_from_the_caller(repo):
    """The point of the change. Before it, `--commit` was written into the
    artifact unexamined, so a manifest could name a commit whose code the routes
    had never run against."""
    head = _git(repo, "rev-parse", "HEAD")
    p = read_head(repo)
    assert p.evaluated_head == head
    assert p.source == "git"
    assert p.tree_clean is True
    assert p.usable


def test_a_supplied_head_that_disagrees_is_disputed_and_neither_side_wins(repo):
    """A caller's claim about the checkout is checked against the checkout. On a
    disagreement the artifact adopts neither — picking one would be the guess
    the rule exists to prevent."""
    head = _git(repo, "rev-parse", "HEAD")
    p = read_head(repo, expect="0" * 40)
    assert p.evaluated_head == head, "the repository stays the source"
    assert p.disputed_head == "0" * 40
    assert not p.usable
    assert any("disagrees with the repository" in problem for problem in p.problems)


def test_a_head_that_agrees_is_not_a_dispute(repo):
    p = read_head(repo, expect=_git(repo, "rev-parse", "HEAD"))
    assert p.disputed_head is None
    assert p.usable


def test_a_dirty_tree_evidences_no_commit(repo):
    """Routes that ran against uncommitted edits ran against code that is at no
    commit. The artifact says so rather than naming the nearest commit."""
    (repo / "code.py").write_text("x = 2\n", encoding="utf-8")
    p = read_head(repo)
    assert p.tree_clean is False
    assert "code.py" in p.dirty_paths
    assert not p.usable
    assert any("not clean" in problem for problem in p.problems)


def test_no_repository_yields_no_head_rather_than_a_plausible_one(tmp_path):
    """The three-valued discipline: unknown is unknown. A generation run outside
    a checkout must not invent a value, and must not crash either."""
    p = read_head(tmp_path)
    assert p.evaluated_head is None
    assert p.source == "unavailable"
    assert not p.usable
    assert any("could not be read" in problem for problem in p.problems)


def test_the_manifest_carries_every_reason_to_doubt_its_own_head(repo):
    """Doubt that stays in the generating process is doubt the auditor never
    sees. It travels into the artifact."""
    (repo / "code.py").write_text("x = 3\n", encoding="utf-8")
    m = manifest([], provenance=read_head(repo, expect="0" * 40))
    assert m["evaluated_head"] == _git(repo, "rev-parse", "HEAD")
    assert m["head_provenance"]["tree_clean"] is False
    assert m["head_provenance"]["disputed_head"] == "0" * 40
    assert len(m["head_provenance"]["problems"]) == 2


# ------------------------------------- the half that does not apply, and why


FORBIDDEN_BY_RULE_A = (
    "evidence_commit_sha",
    "tested_implementation_sha",
    "tested_head_sha",
    "evaluated_head_sha",
    "head_sha",
)


def test_the_manifest_carries_no_field_meaning_the_commit_that_contains_it():
    """Rule A's list of banned field names, checked literally. `evaluated_head`
    is not among them and is not one of them in meaning: it names the commit the
    routes ran against, which this artifact is never part of."""
    m = manifest([], provenance=HeadProvenance("a" * 40, True, "git"))
    for banned in FORBIDDEN_BY_RULE_A:
        assert banned not in m, f"{banned} is forbidden by Evidence Rule A"
    assert m["evaluated_head"] == "a" * 40


def test_the_artifact_is_not_committed_which_is_why_the_other_half_cannot_apply():
    """The self-SHA regress Rule A forbids needs a *tracked* artifact: editing a
    file to contain its own containing commit changes the tree and so changes
    that commit again. Here the artifact is ignored and never lands, so the
    regress has nowhere to start.

    If this ever becomes tracked, that reasoning collapses and the other half of
    Rule A starts applying. This test is the tripwire for that day."""
    ignored = subprocess.run(
        ["git", "-C", str(ROOT), "check-ignore", "evidence/enforcement/any.json"],
        capture_output=True, text=True, check=False,
    )
    assert ignored.returncode == 0, (
        "evidence/enforcement/ is no longer ignored - the artifact is now tracked, so "
        "Rule A's ban on a self-referential commit field applies and must be adopted"
    )
    tracked = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "evidence/enforcement/"],
        capture_output=True, text=True, check=False,
    )
    assert tracked.stdout.strip() == ""


def test_the_manifest_says_which_half_it_adopted():
    """An auditor reading the artifact alone should not have to reconstruct this
    from two repositories."""
    m = manifest([], provenance=HeadProvenance("a" * 40, True, "git"))
    assert "Adopted" in m["rule_a"] and "Not applicable" in m["rule_a"]
    assert "docs/evidence-rule-a.md" in m["rule_a"]
