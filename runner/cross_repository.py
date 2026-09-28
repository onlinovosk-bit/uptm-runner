"""UPTM-015: two verdicts, two repositories, and no winner.

`docs/architecture/governance-map.md` recorded the gap in one sentence: *the
constitution is enforced against evidence, and nothing requires the trading
system to produce that evidence.* Two questions sat open beside it. Neither was
really open.

**MAP-Q1** asked whether a trading-system wave gate must satisfy the capital
constitution. The map itself states the consequence of "no": P8 and P10 would be
enforced against something that never runs - two of the three principles that
are actually ``ENFORCED``. So: yes. What was open was never the question but the
*mechanism*, and adopting "yes" turns an open question into a named unmet
requirement.

**MAP-Q2** asked which repository's verdict wins a disagreement. It assumes a
tie to be broken. P11 says uncertainty halts and ``GOVERNANCE.md`` C3 says
silence is not permission. **A disagreement is not a tie; it is uncertainty.**
So neither wins, and an absent counterpart is not an ``ALLOW`` either.

This module is **not wired into the gate**, on purpose and with a test saying
so. ``evaluate_gate`` reaches ``ALLOW`` today without asking the trading system
at all; connecting this would deny every current ``PASS``, which is a Founder
decision with its own GO. A switch that is off and known is safe. A switch that
is off and forgotten is the next ``DECLARATIVE`` principle.

The spec is ``docs/specs/UPTM-015-close-map-q1-q2.md``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from runner.verdict import Decision

CONTROL_PLANE = "uptm-runner"
TRADING_SYSTEM = "onlinovosk-bit-uptm"


@dataclass(frozen=True)
class CrossResult:
    """The resolved decision, and why - with both sides kept, never one erased.

    A disagreement is recorded as a *dispute*. Reporting it as "the control
    plane's PASS won" would say that the other verdict was read and overruled,
    when what happened is that nobody knows which is right.
    """

    decision: Decision
    reason: str
    control_plane: str | None = None
    trading_system: str | None = None
    disputed: bool = False
    missing: tuple[str, ...] = field(default_factory=tuple)


def _as_decision(value: Decision | str | None) -> Decision | None:
    """``None`` for anything that is not a decision this repository recognises."""
    if isinstance(value, Decision):
        return value
    try:
        return Decision(value)
    except (ValueError, KeyError):
        return None


def resolve_cross_repository(
    control_plane: Decision | str | None,
    trading_system: Decision | str | None,
) -> CrossResult:
    """MAP-Q2, adopted: neither wins. Disagreement denies, and so does absence.

    ``ALLOW`` only when both sides allow. Every other pair - including the pair
    where one side never spoke - is ``DENY``.
    """
    ours = _as_decision(control_plane)
    theirs = _as_decision(trading_system)

    missing = tuple(
        name
        for name, value in ((CONTROL_PLANE, ours), (TRADING_SYSTEM, theirs))
        if value is None
    )
    if missing:
        return CrossResult(
            decision=Decision.DENY,
            reason=(
                "no verdict from " + ", ".join(missing) + "; silence is not permission "
                "(GOVERNANCE.md C3), and an unread counterpart is not an ALLOW"
            ),
            control_plane=ours.value if ours else None,
            trading_system=theirs.value if theirs else None,
            missing=missing,
        )

    if ours is theirs is Decision.ALLOW:
        return CrossResult(
            decision=Decision.ALLOW,
            reason="both planes allow",
            control_plane=ours.value,
            trading_system=theirs.value,
        )

    disputed = ours is not theirs
    return CrossResult(
        decision=Decision.DENY,
        reason=(
            f"{CONTROL_PLANE} says {ours.value} and {TRADING_SYSTEM} says "
            f"{theirs.value}; neither wins, a disagreement is uncertainty and "
            "uncertainty halts (P11)"
        )
        if disputed
        else f"both planes deny ({ours.value})",
        control_plane=ours.value,
        trading_system=theirs.value,
        disputed=disputed,
    )


def cross_repository_status() -> CrossResult:
    """G6: what is actually true here today, measured rather than asserted.

    ``onlinovosk-bit-uptm`` is a separate repository and is not readable from
    this one. There is therefore no trading-system verdict to resolve against -
    which under MAP-Q2 is a denial, not a detail. Naming it here is what stops
    the gap being rediscovered as a surprise.
    """
    return resolve_cross_repository(Decision.ALLOW, None)
