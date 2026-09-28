"""UPTM-013: a data source's state, and why it cannot be typed optimistically.

``UPTM-011`` recorded ES/MES market data as an open unknown because it was in no
sourcing map. Writing it down is the fix - and writing it down is also the risk,
because a source that has been *described* reads, at a glance, exactly like a
source that has been *obtained*.

So a source carries an ordered state rather than a word. The distance between
"we found four vendors" and "data reaches this runner" is four rungs, and the
top one costs evidence: a named artifact and a commit. A state anyone can type
is a state that will eventually be typed optimistically, usually by someone in a
hurry who is not lying.

Directive 4's rule is the one this module enforces mechanically: an unconnected
source may not produce a number. Nothing here opens a socket, reads a price, or
knows what a bar is. The spec is
``docs/specs/UPTM-013-es-mes-data-sourcing.md``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from runner.paths import ROOT

SOURCES = ROOT / "research" / "data_sources"

# Ordered. Each rung is a claim about the world, and each costs more than the last.
STATES: tuple[str, ...] = (
    "NOT_IN_MAP",
    "MAPPED_UNVERIFIED",
    "VERIFIED_TERMS",
    "LICENSED",
    "CONNECTED",
)

CONNECTED = STATES[-1]


def source_path(source_id: str) -> Path:
    return SOURCES / f"{source_id}.json"


def load_source(source_id: str) -> dict[str, Any]:
    return json.loads(source_path(source_id).read_text(encoding="utf-8"))


def open_founder_tasks(source: dict[str, Any]) -> list[str]:
    """What a person still has to go and find out, read out of the candidates.

    Derived, never typed. A hand-kept task list beside the candidates is correct
    until the first candidate changes, and then it is a list of work that was
    already done or was never needed - which is worse than no list, because
    somebody will work from it.
    """
    tasks: list[str] = []
    for candidate in source.get("candidates", []) or []:
        if not isinstance(candidate, dict) or candidate.get("terms_verified") is True:
            continue
        verification = candidate.get("verification")
        verification = verification if isinstance(verification, dict) else {}
        tasks.append(
            f"{candidate.get('id', '<unnamed candidate>')}: "
            f"{verification.get('question', '<no question recorded>')} "
            f"-> {verification.get('url', '<no url recorded>')}"
        )
    return tasks


def state_errors(source: dict[str, Any], root: Path | None = None) -> list[str]:
    """Every way this record claims more than it has earned."""
    base = ROOT if root is None else root
    errors: list[str] = []

    state = source.get("connection_state")
    if state not in STATES:
        return [
            f"connection_state is {state!r}, which is not a rung of {list(STATES)}"
        ]

    if state == CONNECTED:
        # UPTM-010's shape: the expensive claim is the one that must carry proof.
        evidence = source.get("evidence")
        evidence = evidence if isinstance(evidence, dict) else {}
        for field in ("artifact", "commit"):
            if not str(evidence.get(field, "")).strip():
                errors.append(
                    f"connection_state is {CONNECTED} but evidence.{field} is empty; "
                    "a source is connected when something proves it, not when it says so"
                )

    for index, candidate in enumerate(source.get("candidates", []) or [], start=1):
        name = (
            candidate.get("id", f"candidate {index}")
            if isinstance(candidate, dict)
            else f"candidate {index}"
        )
        if not isinstance(candidate, dict):
            errors.append(f"{name} is not an object")
            continue
        verification = candidate.get("verification")
        if not isinstance(verification, dict):
            errors.append(f"{name} carries no verification block")
            continue
        for field in ("question", "url"):
            if not str(verification.get(field, "")).strip():
                errors.append(f"{name} records no verification.{field}")
        if candidate.get("terms_verified") is True and not str(
            candidate.get("verified_how", "")
        ).strip():
            errors.append(
                f"{name} claims terms_verified without recording verified_how; "
                "verified by nobody is not verified"
            )

    document = str(source.get("map_document", "")).strip()
    if not document:
        errors.append("map_document is not recorded")
    elif not (base / document).is_file():
        errors.append(f"map_document {document!r} does not exist")

    return errors


def may_run_detector(source: dict[str, Any], root: Path | None = None) -> bool:
    """Directive 4, mechanically: an unconnected source may not produce a number.

    Fail-closed on both counts. A record that is malformed cannot be read as
    connected either, because the thing that would tell us it is connected is
    the part that failed to parse.
    """
    return source.get("connection_state") == CONNECTED and not state_errors(source, root)
