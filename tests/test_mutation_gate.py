"""The mutation gate is itself a mechanism, so it gets the same treatment.

These tests do not run the suite under mutation — that is the CI step's job and
it costs a full pytest run per case. What they prove is cheaper and is what
actually rots: that each declared anchor still bites, that the source is always
restored, and that the gate reports a failure in each of the three ways it is
supposed to (anchor gone, suite stayed green, sentinel stopped catching).
"""

from __future__ import annotations

import subprocess

import pytest

from runner.mutation_gate import (
    MUTATIONS,
    Mutation,
    MutationAnchorError,
    applied,
    failed_nodes,
    run_mutation_gate,
)
from runner.paths import ROOT


def _proc(returncode: int, stdout: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=["pytest"], returncode=returncode, stdout=stdout, stderr="")


def _fake_mutation(tmp_path):
    target = tmp_path / "mod.py"
    target.write_text("def guard():\n    return check()\n", encoding="utf-8")
    return Mutation(
        mutation_id="fake",
        claim="fake",
        path="mod.py",
        anchor="    return check()\n",
        replacement="    return True  # disconnected\n",
        sentinels=("tests/test_x.py::test_guard",),
    )


# ------------------------------------------------------------ anchors still bite


@pytest.mark.parametrize("mutation", MUTATIONS, ids=lambda m: m.mutation_id)
def test_every_declared_anchor_still_matches_exactly_once(mutation):
    """The failure this catches is silent: code moves, the anchor stops matching,
    and a gate that skipped the case would report success while measuring
    nothing. Asserted here as well as in the gate so it surfaces in a normal
    test run, not only in CI."""
    text = (ROOT / mutation.path).read_text(encoding="utf-8")
    assert text.count(mutation.anchor) == 1, (
        f"{mutation.mutation_id}: anchor no longer matches {mutation.path} exactly once — "
        "re-aim the mutation rather than deleting it"
    )


# ------------------------------------------------------------------- restoration


def test_the_file_is_mutated_inside_the_block(tmp_path):
    mutation = _fake_mutation(tmp_path)
    target = tmp_path / "mod.py"
    with applied(mutation, tmp_path):
        assert "disconnected" in target.read_text(encoding="utf-8")


def test_the_file_is_restored_after_the_block(tmp_path):
    mutation = _fake_mutation(tmp_path)
    target = tmp_path / "mod.py"
    before = target.read_bytes()
    with applied(mutation, tmp_path):
        pass
    assert target.read_bytes() == before


def test_the_file_is_restored_even_when_the_body_raises(tmp_path):
    """A crash mid-run must not leave a mutated working tree behind."""
    mutation = _fake_mutation(tmp_path)
    target = tmp_path / "mod.py"
    before = target.read_bytes()
    with pytest.raises(ZeroDivisionError):
        with applied(mutation, tmp_path):
            1 / 0
    assert target.read_bytes() == before


def test_a_missing_anchor_raises_rather_than_skipping(tmp_path):
    mutation = _fake_mutation(tmp_path)
    (tmp_path / "mod.py").write_text("def guard():\n    return other()\n", encoding="utf-8")
    with pytest.raises(MutationAnchorError):
        with applied(mutation, tmp_path):
            pass


def test_an_ambiguous_anchor_raises(tmp_path):
    mutation = _fake_mutation(tmp_path)
    (tmp_path / "mod.py").write_text(
        "def a():\n    return check()\ndef b():\n    return check()\n", encoding="utf-8"
    )
    with pytest.raises(MutationAnchorError):
        with applied(mutation, tmp_path):
            pass


# ----------------------------------------------------------------- node parsing


def test_failed_nodes_strips_parametrisation():
    out = (
        "FAILED tests/test_enforcement_evidence.py::test_every_route_denies[P10-R4]\n"
        "FAILED tests/test_enforcement_evidence.py::test_every_route_denies[P10-R5]\n"
        "FAILED tests/test_prompt_stacks.py::test_binding\n"
        "1 failed\n"
    )
    assert failed_nodes(out) == {
        "tests/test_enforcement_evidence.py::test_every_route_denies",
        "tests/test_prompt_stacks.py::test_binding",
    }


def test_failed_nodes_is_empty_for_a_green_run():
    assert failed_nodes("334 passed in 2.92s\n") == set()


# ------------------------------------------------------------- the three verdicts


def test_a_mutation_the_suite_does_not_notice_fails_the_gate(tmp_path):
    mutation = _fake_mutation(tmp_path)
    ok, results, error = run_mutation_gate(
        (mutation,), root=tmp_path, runner=lambda _root: _proc(0)
    )
    assert error is None
    assert not ok
    assert results[0].applied and not results[0].suite_failed


def test_a_mutation_caught_by_the_wrong_test_fails_the_gate(tmp_path):
    """Red is not enough. If the named proof stopped catching it, that proof has
    quietly stopped being a proof even though the suite still goes red."""
    mutation = _fake_mutation(tmp_path)
    calls = {"n": 0}

    def runner(_root):
        calls["n"] += 1
        if calls["n"] == 1:
            return _proc(0)
        return _proc(1, "FAILED tests/test_other.py::test_something_else\n")

    ok, results, _ = run_mutation_gate((mutation,), root=tmp_path, runner=runner)
    assert not ok
    assert results[0].suite_failed
    assert results[0].missing_sentinels == ("tests/test_x.py::test_guard",)


def test_a_mutation_caught_by_its_sentinel_passes_the_gate(tmp_path):
    mutation = _fake_mutation(tmp_path)
    calls = {"n": 0}

    def runner(_root):
        calls["n"] += 1
        if calls["n"] == 1:
            return _proc(0)
        return _proc(1, "FAILED tests/test_x.py::test_guard[case-1]\n")

    ok, results, _ = run_mutation_gate((mutation,), root=tmp_path, runner=runner)
    assert ok
    assert results[0].caught_by == ("tests/test_x.py::test_guard",)


def test_a_stale_anchor_fails_the_gate_rather_than_being_skipped(tmp_path):
    mutation = _fake_mutation(tmp_path)
    (tmp_path / "mod.py").write_text("def guard():\n    return other()\n", encoding="utf-8")
    ok, results, _ = run_mutation_gate(
        (mutation,), root=tmp_path, runner=lambda _root: _proc(0)
    )
    assert not ok
    assert not results[0].applied
    assert "anchor found 0x" in (results[0].error or "")


def test_a_red_baseline_refuses_to_report_on_noise(tmp_path):
    """A test that was failing anyway is not a test that caught the mutation."""
    mutation = _fake_mutation(tmp_path)
    ok, results, error = run_mutation_gate(
        (mutation,), root=tmp_path, runner=lambda _root: _proc(1, "FAILED tests/test_x.py::test_guard\n")
    )
    assert not ok
    assert results == []
    assert error is not None


def test_an_empty_mutation_set_is_not_a_pass(tmp_path):
    """Deleting every case must not read as a clean gate."""
    ok, results, error = run_mutation_gate((), root=tmp_path, runner=lambda _root: _proc(0))
    assert not ok
    assert results == []
    assert error is None
