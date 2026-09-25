"""UPTM-009: read every file before CI runs any of them.

Two of the four merge incidents on 2026-09-24 were not wrong code. They were
files that could not be read at all:

- ``6b46cc2`` left a tuple unterminated in ``runner/enforcement.py``. 482 tests
  never collected. CI reported a collection error that named the collector, not
  the file.
- ``a32a5ee`` kept a deleted CI step beside the step that replaced it. Both ran
  ``runner.cli enforcement-evidence``; the first exited 2 on an argument that no
  longer existed, so the second - the one that mattered - never ran.

This module answers one question about each file the repository owns: *can it be
read*. It is not a linter and makes no claim about what the file means. The
spec, including what it deliberately does not establish, is
``docs/specs/UPTM-009-ci-syntax-gate.md``.

It is invoked as ``python -m runner.syntax_gate``, not through ``runner.cli``,
and that is the whole point. ``runner.cli`` imports ``enforcement``, ``gates``
and ``fsm``; had the gate been a subcommand, ``6b46cc2`` would have reached it
as an ImportError traceback before the first file was ever read. So this module
imports nothing from the tree it validates - stdlib and ``yaml`` only, and it
derives the repository root itself rather than borrowing ``runner.paths.ROOT``.
"""

from __future__ import annotations

import ast
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import yaml

ROOT = Path(__file__).resolve().parents[1]

# Excluded by directory NAME, at any depth, so nothing has to be kept in step
# with the tree as it grows. A hand-maintained file list is the same failure as
# a hand-maintained dependency set: it rots silently and the gate keeps
# reporting success.
EXCLUDED_DIRS = frozenset(
    {
        "__pycache__",
        ".git",
        ".venv",
        "venv",
        "node_modules",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".eggs",
        "build",
        "dist",
    }
)

WORKFLOWS = Path(".github") / "workflows"

# Both ways this repository's CLI is spelled: the module invocation used in CI
# and the console script declared in pyproject.toml.
_SUBCOMMAND = re.compile(r"(?:runner\.cli|uptm-runner)\s+([a-z][a-z0-9-]*)")


@dataclass(frozen=True)
class Problem:
    """One file that cannot be read, or one structure that must not exist."""

    path: str
    kind: str
    message: str
    line: int | None = None

    def __str__(self) -> str:
        where = f"{self.path}:{self.line}" if self.line is not None else self.path
        return f"{where}  {self.kind}: {self.message}"


def iter_files(root: Path, suffix: str) -> Iterator[Path]:
    """Every file with ``suffix`` that the repository owns, generated trees out."""
    for path in sorted(root.rglob(f"*{suffix}")):
        if EXCLUDED_DIRS.isdisjoint(path.relative_to(root).parts):
            yield path


def _read(path: Path, root: Path) -> tuple[str | None, Problem | None]:
    try:
        return path.read_text(encoding="utf-8"), None
    except (OSError, UnicodeDecodeError) as exc:
        return None, Problem(str(path.relative_to(root)), "unreadable", str(exc))


def check_python(root: Path) -> list[Problem]:
    """G1: every .py parses."""
    problems: list[Problem] = []
    for path in iter_files(root, ".py"):
        source, problem = _read(path, root)
        if problem is not None:
            problems.append(problem)
            continue
        try:
            ast.parse(source, filename=str(path))
        except SyntaxError as exc:
            problems.append(
                Problem(str(path.relative_to(root)), "python", exc.msg, exc.lineno)
            )
    return problems


def check_json(root: Path) -> list[Problem]:
    """G2: every .json parses."""
    problems: list[Problem] = []
    for path in iter_files(root, ".json"):
        source, problem = _read(path, root)
        if problem is not None:
            problems.append(problem)
            continue
        try:
            json.loads(source)
        except json.JSONDecodeError as exc:
            problems.append(
                Problem(str(path.relative_to(root)), "json", exc.msg, exc.lineno)
            )
    return problems


def _step_name(step: object, index: int) -> str:
    if isinstance(step, dict) and isinstance(step.get("name"), str):
        return step["name"]
    return f"step {index}"


def _duplicate_subcommands(document: object) -> Iterator[tuple[str, list[str]]]:
    """G4: a CLI subcommand invoked by two steps of the same job.

    This is ``a32a5ee``'s shape exactly. There is no opt-out: two steps running
    the same subcommand may well be deliberate one day, and when that day comes
    a human should decide it in a diff rather than have the gate wave it
    through. A rule with a marker anyone can add is a rule that removes itself.
    """
    if not isinstance(document, dict):
        return
    jobs = document.get("jobs")
    if not isinstance(jobs, dict):
        return
    for job in jobs.values():
        if not isinstance(job, dict):
            continue
        steps = job.get("steps")
        if not isinstance(steps, list):
            continue
        seen: dict[str, list[str]] = {}
        for index, step in enumerate(steps, start=1):
            run = step.get("run") if isinstance(step, dict) else None
            if not isinstance(run, str):
                continue
            for subcommand in dict.fromkeys(_SUBCOMMAND.findall(run)):
                seen.setdefault(subcommand, []).append(_step_name(step, index))
        for subcommand, names in seen.items():
            if len(names) > 1:
                yield subcommand, names


def check_workflows(root: Path) -> list[Problem]:
    """G3: every workflow parses as YAML. G4: no subcommand runs twice in a job."""
    problems: list[Problem] = []
    directory = root / WORKFLOWS
    if not directory.is_dir():
        return problems
    paths = sorted(p for p in directory.iterdir() if p.suffix in {".yml", ".yaml"})
    for path in paths:
        relative = str(path.relative_to(root))
        source, problem = _read(path, root)
        if problem is not None:
            problems.append(problem)
            continue
        try:
            document = yaml.safe_load(source)
        except yaml.YAMLError as exc:
            mark = getattr(exc, "problem_mark", None)
            line = mark.line + 1 if mark is not None else None
            problems.append(
                Problem(relative, "workflow", str(exc).replace("\n", " "), line)
            )
            continue
        for subcommand, names in _duplicate_subcommands(document):
            quoted = ", ".join(f'"{name}"' for name in names)
            problems.append(
                Problem(
                    relative,
                    "workflow",
                    f"{subcommand!r} runs in {len(names)} steps of one job: {quoted}",
                )
            )
    return problems


def run(root: Path | None = None) -> list[Problem]:
    """Every problem in the tree, not the first one.

    G5: a gate that stops at the first finding turns one batch of merge damage
    into a queue of CI runs.
    """
    base = ROOT if root is None else root
    return check_python(base) + check_json(base) + check_workflows(base)


def main(argv: list[str] | None = None) -> int:
    root = Path(argv[0]).resolve() if argv else ROOT
    problems = run(root)
    if not problems:
        print("syntax-gate: every file parses")
        return 0
    count = len(problems)
    print(
        f"syntax-gate: {count} problem{'s' if count != 1 else ''}", file=sys.stderr
    )
    for problem in problems:
        print(f"  {problem}", file=sys.stderr)
    return 1


if __name__ == "__main__":  # pragma: no cover - exercised as a subprocess
    raise SystemExit(main(sys.argv[1:]))
