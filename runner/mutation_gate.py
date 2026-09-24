"""Proof that the guard tests are load-bearing — run in CI, not on request.

CLAUDE.md states the rule this module enforces: *deklarované ≠ vynútené*, and a
new gate is proven by mutation — break it and show the suite catches it. The
suite already carries spy and disconnection tests for that. What nothing carried
until now is a check that those tests **still** catch anything.

A green suite cannot tell the difference between a guard that works and a guard
whose test was deleted, renamed, skipped, or quietly weakened. Both read as
green. The only way to tell them apart is to break the guard on purpose and
require the named tests to go red.

So each case below breaks one mechanism in the source and names the tests whose
job is to notice. The gate fails when:

- the anchor no longer matches — the code was refactored and the mutation no
  longer bites, so the case is stale and a human has to re-aim it. Silently
  skipping it is the failure mode this module exists to prevent;
- the suite stays green under mutation — the mechanism is not load-bearing;
- a named sentinel does not fail — something else caught the mutation, and the
  test that was supposed to has stopped doing its job.

Extra failures beyond the sentinels are fine and expected: a disconnected guard
tends to trip several proofs at once. Only their *absence* is a finding.

The source is restored in a ``finally`` and the restoration is verified byte for
byte before the next case runs, so a crash mid-case cannot leave a mutated tree
behind.
"""

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterator

from contextlib import contextmanager

from runner.paths import ROOT

FAILED_LINE = re.compile(r"^FAILED\s+(\S+)", re.MULTILINE)


class MutationAnchorError(RuntimeError):
    """The text a mutation rewrites is no longer present, or is ambiguous.

    Raised rather than skipped: a mutation that cannot be applied proves
    nothing, and a gate that shrugs at it is worse than no gate, because it
    reports success.
    """


@dataclass(frozen=True)
class Mutation:
    """One deliberate break, and the tests required to notice it."""

    mutation_id: str
    claim: str
    path: str
    anchor: str
    replacement: str
    sentinels: tuple[str, ...]


@dataclass
class MutationResult:
    mutation_id: str
    claim: str
    applied: bool
    suite_failed: bool
    missing_sentinels: tuple[str, ...] = ()
    caught_by: tuple[str, ...] = ()
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.applied and self.suite_failed and not self.missing_sentinels

    def as_dict(self) -> dict:
        return {
            "mutation_id": self.mutation_id,
            "claim": self.claim,
            "ok": self.ok,
            "applied": self.applied,
            "suite_failed": self.suite_failed,
            "missing_sentinels": list(self.missing_sentinels),
            "caught_by": list(self.caught_by),
            "error": self.error,
        }


MUTATIONS: tuple[Mutation, ...] = (
    Mutation(
        mutation_id="evidence-binding-unverified",
        claim=(
            "UPTM-008's check is what makes the gate read the files[] binding every "
            "artifact declares. Remove the call and the gate returns to accepting a "
            "digest computed from nothing - which is what it did until 2026-09-24."
        ),
        path="runner/gates.py",
        anchor="    binding = binding_errors(evidence)\n",
        replacement="    binding = []  # mutation-gate: binding left unverified\n",
        sentinels=(
            "tests/test_binding.py::test_g4_the_fabricated_digest_that_passed_before_this_wall_now_denies",
            "tests/test_binding.py::test_g2_a_changed_declared_file_denies_and_names_the_path",
            "tests/test_binding.py::test_g7_neutering_the_binding_check_opens_a_denying_gate",
            "tests/test_binding.py::test_r1_p12_has_a_route_per_violation_shape_each_denying_by_its_own_check",
        ),
    ),
    Mutation(
        mutation_id="capital-detectors-disconnected",
        claim=(
            "The validation-capital detectors are what deny the P8/P10 routes. "
            "Disconnect them and the routes must stop denying for their own reason."
        ),
        path="runner/gates.py",
        anchor=(
            '    pack = evidence.get("capital")\n'
            '    if pack is None and evidence.get("capital_gate") is not True:\n'
            "        return Verdict.PASS, []\n"
        ),
        replacement=(
            "    return Verdict.PASS, []  # mutation-gate: detectors disconnected\n"
            '    pack = evidence.get("capital")\n'
            '    if pack is None and evidence.get("capital_gate") is not True:\n'
            "        return Verdict.PASS, []\n"
        ),
        sentinels=(
            "tests/test_detector_invocation.py::test_gate_actually_calls_the_validation_capital_detector",
            "tests/test_detector_invocation.py::test_gate_verdict_depends_on_what_the_capital_detector_returns",
            "tests/test_enforcement_evidence.py::test_every_route_denies_for_its_own_reason",
            "tests/test_enforcement_evidence.py::test_neutering_the_named_guards_opens_the_route",
        ),
    ),
    Mutation(
        mutation_id="prompt-stack-binding-disconnected",
        claim=(
            "APS-001's binding check is what holds the prompt-stack routes. Drop the "
            "call and the binding proofs must fail rather than the structural checks "
            "quietly covering for it."
        ),
        path="runner/evidence.py",
        anchor="    errors.extend(validate_prompt_stack_binding(evidence))\n",
        replacement="    pass  # mutation-gate: binding check disconnected\n",
        sentinels=(
            "tests/test_enforcement_evidence.py::test_the_binding_check_itself_is_what_holds_the_prompt_stack_routes",
            "tests/test_prompt_stacks.py::test_pass_without_prompt_stack_binding_rejected",
            "tests/test_prompt_stacks.py::test_evidence_binding_rejects_tampered_digest",
            "tests/test_prompt_stacks.py::test_stack_body_change_without_manifest_update_invalidates_evidence",
        ),
    ),
    Mutation(
        mutation_id="kill-switch-detectors-disconnected",
        claim=(
            "The UPTM-003 detectors are what deny the kill-switch routes, and the "
            "drill check folds in through the same call. Disconnect them and both "
            "the spy proofs and the routes that name them must go red."
        ),
        path="runner/gates.py",
        anchor=(
            '    pack = evidence.get("kill_switch")\n'
            "    if pack is None:\n"
            "        return Verdict.PASS, []\n"
        ),
        replacement=(
            "    return Verdict.PASS, []  # mutation-gate: detectors disconnected\n"
            '    pack = evidence.get("kill_switch")\n'
            "    if pack is None:\n"
            "        return Verdict.PASS, []\n"
        ),
        sentinels=(
            "tests/test_detector_invocation.py::test_gate_actually_calls_the_kill_switch_detector",
            "tests/test_detector_invocation.py::test_gate_verdict_depends_on_what_the_kill_switch_detector_returns",
            "tests/test_detector_invocation.py::test_gate_actually_calls_the_drill_detector",
            "tests/test_enforcement_evidence.py::test_every_route_denies_for_its_own_reason",
            "tests/test_enforcement_evidence.py::test_neutering_the_named_guards_opens_the_route",
        ),
    ),
)


@contextmanager
def applied(mutation: Mutation, root: Path | None = None) -> Iterator[None]:
    """Apply one mutation, then restore the file and verify the restoration.

    The anchor must appear exactly once. Zero means the code moved; more than
    one means the mutation is not aimed at a single place and the result would
    be ambiguous. Both raise.
    """
    target = (root or ROOT) / mutation.path
    original = target.read_bytes()
    text = original.decode("utf-8")
    found = text.count(mutation.anchor)
    if found != 1:
        raise MutationAnchorError(
            f"{mutation.mutation_id}: anchor found {found}x in {mutation.path}, expected 1. "
            "The code changed and this mutation no longer bites — re-aim it."
        )
    try:
        target.write_text(text.replace(mutation.anchor, mutation.replacement), encoding="utf-8")
        yield
    finally:
        target.write_bytes(original)
        if target.read_bytes() != original:  # pragma: no cover - filesystem failure
            raise RuntimeError(f"failed to restore {mutation.path} after {mutation.mutation_id}")


def failed_nodes(pytest_output: str) -> set[str]:
    """Node ids from a pytest run, with parametrisation stripped.

    Sentinels name a test, not a parameter set: a route id that appears or
    disappears should not silently retarget the gate.
    """
    return {FAILED_LINE.match(line).group(1).split("[")[0]  # type: ignore[union-attr]
            for line in pytest_output.splitlines()
            if FAILED_LINE.match(line)}


def _run_pytest(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--tb=no", "-p", "no:cacheprovider"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )


def run_mutation_gate(
    mutations: tuple[Mutation, ...] = MUTATIONS,
    root: Path | None = None,
    runner: Callable[[Path], subprocess.CompletedProcess[str]] = _run_pytest,
) -> tuple[bool, list[MutationResult], str | None]:
    """Run every mutation. Returns (ok, results, baseline_error).

    The unmutated suite is run first. If it is already red the mutation results
    mean nothing — a test that was failing anyway is not a test that caught the
    mutation — so the gate refuses rather than reporting on noise.
    """
    work = root or ROOT
    baseline = runner(work)
    if baseline.returncode != 0:
        return False, [], "the suite is red before any mutation; fix that first"

    results: list[MutationResult] = []
    for mutation in mutations:
        try:
            with applied(mutation, work):
                proc = runner(work)
        except MutationAnchorError as exc:
            results.append(
                MutationResult(
                    mutation_id=mutation.mutation_id,
                    claim=mutation.claim,
                    applied=False,
                    suite_failed=False,
                    error=str(exc),
                )
            )
            continue

        nodes = failed_nodes(proc.stdout + proc.stderr)
        missing = tuple(s for s in mutation.sentinels if s not in nodes)
        results.append(
            MutationResult(
                mutation_id=mutation.mutation_id,
                claim=mutation.claim,
                applied=True,
                suite_failed=proc.returncode != 0,
                missing_sentinels=missing,
                caught_by=tuple(sorted(n for n in nodes if n in mutation.sentinels)),
            )
        )

    return all(r.ok for r in results) and bool(results), results, None
