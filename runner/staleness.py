"""Dependency staleness for enforcement evidence (UPTM-007, P12).

Criteria preregistered in docs/specs/UPTM-007-stale-invalidation.md, written
before this module existed (CC/P4).

P12 requires that a change to a relevant dependency invalidates the affected
PASS. Expiry answers "how old is this?"; staleness answers "does it still
describe the system?" - and only the second question is about the code. An
artifact can sit well inside its seven days and describe a gate that has since
been rewritten.

The dependency set is derived from the repository rather than listed here. A
hand-maintained list is the same failure as a hand-typed ENFORCED: someone adds
a detector, forgets the list, and the evidence stays green while the thing it
describes has moved.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from runner.paths import CAPITAL_RULES, CC_CONSTITUTION, PROMPT_STACKS, ROOT

CURRENT = "CURRENT"
STALE = "STALE"
UNKNOWN = "UNKNOWN"


def _iter_dependency_paths(root: Path) -> list[Path]:
    """Every file whose content can change what the routes would conclude.

    Over-inclusion is deliberate. A file here that did not matter causes a false
    STALE and one wasted regeneration; a file missing from here causes a false
    CURRENT, which is the P12 violation itself. The failure modes are not
    symmetric, so this prefers the one that denies.
    """
    found: list[Path] = []

    runner_dir = root / "runner"
    if runner_dir.is_dir():
        found.extend(
            p for p in runner_dir.rglob("*.py") if "__pycache__" not in p.parts
        )

    for named in (root / CAPITAL_RULES.relative_to(ROOT),
                  root / CC_CONSTITUTION.relative_to(ROOT)):
        if named.is_file():
            found.append(named)

    stacks = root / PROMPT_STACKS.relative_to(ROOT)
    if stacks.is_dir():
        found.extend(
            p for p in stacks.rglob("*") if p.is_file() and "__pycache__" not in p.parts
        )

    return sorted(set(found))


def digest_file(path: Path) -> str | None:
    """sha256 of the file's bytes, or None when it cannot be read.

    Content, never mtime or size: a file touched without being changed is not a
    dependency change, and a file changed without growing is.
    """
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def dependency_digests(root: Path | None = None) -> dict[str, str]:
    """Path (repo-relative, posix) -> sha256, for every derived dependency."""
    base = root or ROOT
    digests: dict[str, str] = {}
    for path in _iter_dependency_paths(base):
        value = digest_file(path)
        if value is not None:
            digests[path.relative_to(base).as_posix()] = value
    return digests


@dataclass(frozen=True)
class Staleness:
    """What changed under an artifact since it was generated, and what is gone."""

    status: str
    changed: tuple[str, ...] = ()
    unreadable: tuple[str, ...] = ()
    reason: str = ""
    checked: int = 0

    @property
    def current(self) -> bool:
        return self.status == CURRENT


def staleness(
    manifest_payload: dict[str, Any], root: Path | None = None, *, now: Any = None
) -> Staleness:
    """CURRENT / STALE / UNKNOWN for an artifact against the tree it named.

    UNKNOWN is not a soft CURRENT. An artifact that recorded no dependencies, or
    whose dependencies can no longer be read, has not been shown to still
    describe anything - and under runner.verdict that dominates PASS and denies.
    A missing file is UNKNOWN rather than STALE for the same reason a missing
    parameter is UNKNOWN rather than zero: absence is not a measurement.
    """
    base = root or ROOT
    recorded = manifest_payload.get("dependencies")
    if not isinstance(recorded, dict) or not recorded:
        return Staleness(
            UNKNOWN,
            reason=(
                "the artifact recorded no dependencies, so nothing about it can be "
                "compared to the tree"
            ),
        )

    changed: list[str] = []
    unreadable: list[str] = []
    for rel, expected in sorted(recorded.items()):
        actual = digest_file(base / rel)
        if actual is None:
            unreadable.append(rel)
        elif actual != expected:
            changed.append(rel)

    if unreadable:
        return Staleness(
            UNKNOWN,
            changed=tuple(changed),
            unreadable=tuple(unreadable),
            checked=len(recorded),
            reason=(
                "a recorded dependency could not be read, so this artifact cannot be "
                "compared to the tree it named"
            ),
        )
    if changed:
        return Staleness(
            STALE,
            changed=tuple(changed),
            checked=len(recorded),
            reason="a dependency changed after this artifact was generated",
        )
    return Staleness(
        CURRENT,
        checked=len(recorded),
        reason="every recorded dependency still matches the tree",
    )


#: What the manifest can and cannot pin down (P12, §B of UPTM-007).
#:
#: P12 forbids calling a result reproducible without declaring its uncaptured
#: inputs, so this is a required field rather than prose someone may add.
def determinism_declaration() -> dict[str, list[str]]:
    return {
        "captured": [
            "the evaluated head, read from the repository (Evidence Rule A)",
            "the working tree's cleanliness at generation time",
            "sha256 of every derived dependency: runner/**.py, capital-rules.json, "
            "CONSTITUTION-CAPITAL.md, prompt-stacks/**",
            "the preregistered evidence lifetime and the resulting expires_at",
            "every route's verdict, decision and the check that denied it",
        ],
        "not_captured": [
            "the wall clock: generated_at moves every run, so no two artifacts are "
            "byte-identical even from an identical tree",
            "the Python version and installed packages - no dependency lock is read",
            "the runtime or container identity",
            "anything broker-side or network-timed: this wall drives no live path",
        ],
        "note": [
            "This block exists because P12's violation clause names calling a result "
            "reproducible without declaring uncaptured inputs. The routes are "
            "deterministic given the tree; the artifact is not byte-reproducible, and "
            "says so rather than implying otherwise."
        ],
    }
