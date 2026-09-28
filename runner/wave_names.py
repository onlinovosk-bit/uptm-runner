"""UPTM-016: a wave reference that leaves its repository must carry it.

Two systems number waves 0-7 and 0-9. ``docs/architecture/governance-map.md``
records what that costs: its own author conflated this repository's wave 7
(``exit_and_archive``) with the trading repository's ``W7``
(``INDEPENDENT RED TEAM``) on the day the map was written.

**Picking a canonical numbering does not fix it.** Renumbering this repository
would rewrite eight artifacts to solve a problem in how they are *quoted*, and
every status line already written would stay ambiguous. Declaring 0-7 canonical
for the other repository claims authority this one does not have over a
repository it cannot read. So neither numbering is canonical - that part of
``DEC-UPTM-MAP-Q5`` survives its own closure - and what changes is that a
reference crossing the boundary carries its repository.

The qualification lives **in the data**. Policing quotations would put the rule
in whoever writes the status line, which is exactly where it failed.

Not every number is ambiguous, and which ones are is **derived**: ours is
measured from the wave files on disk, theirs is *recorded* from the map, and the
ambiguous set is the intersection. ``W8`` and ``W9`` are unambiguous because this
repository has no such wave - and adding ``wave8.yaml`` would change that with
nobody editing a list.

The spec is ``docs/specs/UPTM-016-close-map-q5.md``.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from runner.paths import ROOT

WAVES = ROOT / "waves"

CONTROL_PLANE = "uptm-runner"
TRADING_SYSTEM = "onlinovosk-bit-uptm"

#: Recorded, never measured. This repository cannot read the other one, and a
#: number nobody checked must not be dressed as one that was.
THEIR_WAVES: frozenset[int] = frozenset(range(0, 10))
THEIR_WAVES_SOURCE = (
    "docs/architecture/governance-map.md — recorded from the map, not measured; "
    f"{TRADING_SYSTEM} is not readable from this repository"
)

_WAVE_FILE = re.compile(r"^wave(\d+)\.yaml$")
_REFERENCE = re.compile(r"^(?:(?P<repo>[A-Za-z0-9_.-]+):)?W(?P<number>\d+)$")


@dataclass(frozen=True)
class Reference:
    """A parsed wave reference, and whether it says which repository it means."""

    number: int
    repository: str | None = None

    @property
    def qualified(self) -> bool:
        return self.repository is not None

    def __str__(self) -> str:
        return f"{self.repository}:W{self.number}" if self.qualified else f"W{self.number}"


def our_waves(root: Path | None = None) -> frozenset[int]:
    """Measured from the files, so the set cannot drift from the tree."""
    base = (root or ROOT) / "waves"
    return frozenset(
        int(match.group(1))
        for path in base.glob("wave*.yaml")
        if (match := _WAVE_FILE.match(path.name))
    )


def ambiguous_numbers(root: Path | None = None) -> frozenset[int]:
    """The numbers a bare ``W<n>`` cannot distinguish: both repositories have one."""
    return our_waves(root) & THEIR_WAVES


def unambiguous_to(repository: str, root: Path | None = None) -> frozenset[int]:
    """Numbers only one repository has - so a bare reference to them is readable.

    Returned per repository rather than as a single "safe" set, because *whose*
    wave it unambiguously is, is the part a reader needs.
    """
    ours = our_waves(root)
    if repository == CONTROL_PLANE:
        return ours - THEIR_WAVES
    if repository == TRADING_SYSTEM:
        return THEIR_WAVES - ours
    raise ValueError(f"unknown repository {repository!r}")


def qualify(repository: str, number: int) -> str:
    if repository not in (CONTROL_PLANE, TRADING_SYSTEM):
        raise ValueError(f"unknown repository {repository!r}")
    return f"{repository}:W{number}"


def parse(reference: str) -> Reference:
    match = _REFERENCE.match(reference.strip())
    if match is None:
        raise ValueError(f"{reference!r} is not a wave reference")
    return Reference(
        number=int(match.group("number")),
        repository=match.group("repo"),
    )


def is_ambiguous(reference: str, root: Path | None = None) -> bool:
    """A bare reference to a number both repositories use. Qualified is never ambiguous."""
    parsed = parse(reference)
    return not parsed.qualified and parsed.number in ambiguous_numbers(root)


def index_disagreements(root: Path | None = None) -> list[str]:
    """N3: what ``waves/index.json`` claims, against what is on disk.

    Derived both ways. A wave added without updating the index, and an index
    entry with no file, are both findings - the second is how a deleted wave
    keeps appearing in status lines.
    """
    base = (root or ROOT) / "waves"
    try:
        index = json.loads((base / "index.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"waves/index.json could not be read: {exc}"]

    claimed = set(index.get("waves") or [])
    present = set(our_waves(root))
    findings = [
        f"waves/index.json lists wave {number} but wave{number}.yaml does not exist"
        for number in sorted(claimed - present)
    ] + [
        f"wave{number}.yaml exists but waves/index.json does not list it"
        for number in sorted(present - claimed)
    ]
    if index.get("repository") != CONTROL_PLANE:
        findings.append(
            f"waves/index.json does not declare repository {CONTROL_PLANE!r}; "
            "a number lifted out of it would be unqualified at source"
        )
    return findings


def artifact_disagreements(root: Path | None = None) -> list[str]:
    """N2: every wave file carries its repository, and carries it consistently.

    ``qualified_id`` is redundant with ``wave_id`` plus ``repository`` on
    purpose: the failure this closes is a single field being lifted out of the
    file, and a reader who lifts one field gets a qualified value. Redundancy in
    data is drift waiting to happen, so the agreement is derived and checked
    here rather than trusted.
    """
    import yaml

    base = (root or ROOT) / "waves"
    findings: list[str] = []
    for path in sorted(base.glob("wave*.yaml")):
        match = _WAVE_FILE.match(path.name)
        if match is None:
            continue
        number = int(match.group(1))
        try:
            document = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError) as exc:
            findings.append(f"{path.name} could not be read: {exc}")
            continue
        if document.get("repository") != CONTROL_PLANE:
            findings.append(f"{path.name} does not declare repository {CONTROL_PLANE!r}")
        expected = qualify(CONTROL_PLANE, number)
        if document.get("qualified_id") != expected:
            findings.append(
                f"{path.name} carries qualified_id "
                f"{document.get('qualified_id')!r}, not {expected!r}"
            )
        if document.get("wave_id") != number:
            findings.append(
                f"{path.name} carries wave_id {document.get('wave_id')!r}, not {number}"
            )
    return findings
