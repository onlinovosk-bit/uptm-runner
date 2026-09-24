"""Where the evaluated commit comes from (Evidence Rule A, adapted).

Rule A lives in `onlinovosk-bit/onlinovosk-bit-uptm` (`docs/EVIDENCE_RULE_A.md`)
and has two halves. Only one of them applies here, and pretending otherwise
would be the same class of error the rule exists to prevent — see
`docs/evidence-rule-a.md` in this repository for the reasoning.

The half that applies: **the evaluated head is read from the repository, never
asserted by the caller.** Before this module, `enforcement-evidence` took
`--commit` and wrote whatever it was given into the artifact. Nothing compared
it to the checkout, so a manifest could name a commit whose code the routes had
never run against, and nothing downstream could tell.

The three-valued discipline applies here as everywhere else: a head that cannot
be established is `None` with a stated reason, never a plausible default.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class HeadProvenance:
    """What the repository says it is, and every reason to doubt it."""

    evaluated_head: str | None
    tree_clean: bool | None
    source: str
    dirty_paths: tuple[str, ...] = ()
    disputed_head: str | None = None
    problems: tuple[str, ...] = field(default_factory=tuple)

    @property
    def usable(self) -> bool:
        """Whether this provenance can support an evidence claim at all."""
        return not self.problems


def _git(root: Path, *args: str) -> str | None:
    """Run git, or report that it could not be run. Never raise."""
    try:
        done = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if done.returncode != 0:
        return None
    return done.stdout


def read_head(root: Path, *, expect: str | None = None) -> HeadProvenance:
    """Read the evaluated head from the repository at ``root``.

    ``expect`` is cross-checked, not trusted. This is the inversion that makes
    the artifact worth reading: the repository is the source and the caller's
    value is a claim about it, so a disagreement is recorded as a dispute rather
    than silently resolved in the caller's favour.

    Note the name is deliberately not Rule A's ``--evaluated-head``. There the
    flag *is* the source; here it is the thing being checked. Two repositories
    already disagree about what "W7" and "evidence" mean, and a third collision
    was not worth the familiarity.
    """
    problems: list[str] = []

    head = _git(root, "rev-parse", "HEAD")
    if head is None:
        return HeadProvenance(
            evaluated_head=None,
            tree_clean=None,
            source="unavailable",
            problems=(
                "the evaluated head could not be read from the repository: this artifact "
                "evidences no commit",
            ),
        )
    head = head.strip()

    status = _git(root, "status", "--porcelain")
    if status is None:
        tree_clean: bool | None = None
        dirty: tuple[str, ...] = ()
        problems.append("the working tree state could not be read: cleanliness is unknown")
    else:
        dirty = tuple(line[3:] for line in status.splitlines() if line.strip())
        tree_clean = not dirty
        if dirty:
            problems.append(
                "the working tree is not clean: the routes ran against code that is at no "
                "commit, so this artifact evidences no commit"
            )

    if expect is not None and expect != head:
        problems.append(
            f"the supplied head {expect} disagrees with the repository at {head}: "
            "neither is adopted"
        )

    return HeadProvenance(
        evaluated_head=head,
        tree_clean=tree_clean,
        source="git",
        dirty_paths=dirty,
        disputed_head=expect if expect is not None and expect != head else None,
        problems=tuple(problems),
    )
