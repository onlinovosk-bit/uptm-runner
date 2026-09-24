"""Verify the binding a gate artifact declares (UPTM-008, P12).

Criteria preregistered in docs/specs/UPTM-008-gate-verifies-its-binding.md,
written before this module existed (CC/P4).

Gate evidence has always carried ``files: [{path, sha256}]``, and the gate has
never compared it to anything. Measured on main at dcf77f4: evidence declaring
a file that does not exist, with a digest never computed from anything, reached
PASS. That is P12's violation clause - a capability staying green after a change
to the code or data its evidence came from - except the evidence never described
the tree at all.

Nothing here adds a field. It starts checking one that was already required.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from runner.paths import ROOT
from runner.staleness import CURRENT, STALE, UNKNOWN, digest_file

SHA256 = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class Binding:
    """What the evidence claimed about the tree, and how that held up."""

    status: str
    changed: tuple[str, ...] = ()
    unreadable: tuple[str, ...] = ()
    malformed: tuple[str, ...] = ()
    checked: int = 0
    reason: str = ""

    @property
    def current(self) -> bool:
        return self.status == CURRENT


def verify_declared_files(evidence: dict[str, Any], root: Path | None = None) -> Binding:
    """CURRENT / STALE / UNKNOWN for the files a gate artifact declares.

    A malformed entry is UNKNOWN, never skipped: a check that silently ignores
    what it cannot parse is not a check, and "unparseable" is the easiest thing
    for a caller to produce on purpose.

    A declared file that is gone is UNKNOWN rather than STALE. Absence is not a
    measurement - the same reason a missing parameter is UNKNOWN rather than
    zero.
    """
    base = root or ROOT
    declared = evidence.get("files")

    if not isinstance(declared, list) or not declared:
        return Binding(
            UNKNOWN,
            reason=(
                "the evidence declares no files, so it is bound to nothing and cannot be "
                "checked against the tree"
            ),
        )

    changed: list[str] = []
    unreadable: list[str] = []
    malformed: list[str] = []

    for index, entry in enumerate(declared):
        if not isinstance(entry, dict):
            malformed.append(f"files[{index}] is not an object")
            continue
        path = entry.get("path")
        expected = entry.get("sha256")
        if not isinstance(path, str) or not path:
            malformed.append(f"files[{index}] declares no path")
            continue
        if not isinstance(expected, str) or not SHA256.match(expected):
            malformed.append(f"{path} declares no usable sha256")
            continue

        actual = digest_file(base / path)
        if actual is None:
            unreadable.append(path)
        elif actual != expected:
            changed.append(path)

    if malformed:
        return Binding(
            UNKNOWN,
            changed=tuple(changed),
            unreadable=tuple(unreadable),
            malformed=tuple(malformed),
            checked=len(declared),
            reason="the declared binding cannot be read, so it has not been checked",
        )
    if unreadable:
        return Binding(
            UNKNOWN,
            changed=tuple(changed),
            unreadable=tuple(unreadable),
            checked=len(declared),
            reason=(
                "a declared file is missing from the tree, so this evidence has not been "
                "shown to describe anything"
            ),
        )
    if changed:
        return Binding(
            STALE,
            changed=tuple(changed),
            checked=len(declared),
            reason="a declared file changed after this evidence was produced",
        )
    return Binding(
        CURRENT,
        checked=len(declared),
        reason="every declared file matches the tree",
    )


def binding_errors(evidence: dict[str, Any], root: Path | None = None) -> list[str]:
    """The gate's view: an empty list when the binding holds, reasons when not."""
    result = verify_declared_files(evidence, root)
    if result.current:
        return []
    detail = []
    if result.changed:
        detail.append("changed: " + ", ".join(result.changed))
    if result.unreadable:
        detail.append("missing: " + ", ".join(result.unreadable))
    if result.malformed:
        detail.append("malformed: " + "; ".join(result.malformed))
    suffix = f" ({' | '.join(detail)})" if detail else ""
    return [f"binding {result.status}: {result.reason}{suffix}"]
