"""Shared vocabulary for preregistered detectors.

A detector reports what the evidence shows about one preregistered check. It
never reports what the system is then permitted to do — resolution belongs to
``runner.verdict.resolve`` and to it alone.

``CheckOutcome`` and the folding helpers live here rather than inside any one
detector, so that two detectors cannot drift into two slightly different
readings of UNKNOWN.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from runner.verdict import Verdict

__all__ = ["CheckOutcome", "worst", "worst_verdict"]


@dataclass(frozen=True)
class CheckOutcome:
    """One preregistered check's result. Carries no decision."""

    check_id: str
    verdict: Verdict
    detail: str

    @property
    def stop_condition_raised(self) -> bool:
        """Only FAIL asserts a violation. UNKNOWN denies without accusing."""
        return self.verdict is Verdict.FAIL


def worst_verdict(verdicts: Iterable[Verdict]) -> Verdict:
    """FAIL dominates UNKNOWN dominates PASS.

    Both non-PASS states deny; only FAIL asserts a violation, so FAIL is
    reported when both are present. An empty set is not proof and yields
    UNKNOWN.
    """
    seen = set(verdicts)
    if Verdict.FAIL in seen:
        return Verdict.FAIL
    if Verdict.UNKNOWN in seen:
        return Verdict.UNKNOWN
    return Verdict.PASS if seen else Verdict.UNKNOWN


def worst(outcomes: Iterable[CheckOutcome]) -> Verdict:
    """worst_verdict over a set of check outcomes."""
    return worst_verdict(o.verdict for o in outcomes)
