"""UPTM-014: joining futures contracts, and the join that rewrites its own past.

ES rolls quarterly. A "continuous ES series" is therefore a **construction, not
a measurement**: somebody decided when to switch contracts and what to do about
the price gap between them, and those decisions change every price in the
series. ``UPTM-013`` found this while mapping the data source and left it
undecided so that picking a vendor could not settle it by accident.

It is decidable with no data at all, because it is a question about information
order and this repository already answered that one. ``UPTM-012`` committed to
an invariant: nothing is ever revised, because a withdrawn swing is one a live
system may already have acted on.

**Back adjustment rewrites the past by construction.** At each roll it shifts
every earlier bar so the seam disappears, which means a series built today and a
series built a quarter ago disagree about what the price was two years ago - and
that disagreement depends on rolls which, at the earlier date, had not happened.
It is also what most vendors ship and what a backtest usually reads.

So this module does not hold a list of approved methods. It **measures** whether
a join rewrites history, on a probe, and refuses to answer on a probe that
contains no roll - where every method looks stable and the answer would be a
comfortable lie. The spec is ``docs/specs/UPTM-014-roll-rule.md``.

Nothing here reads market data, opens a socket, or trades.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping, Sequence

from runner.swing import Bar


class Adjustment(str, Enum):
    """How the gap between two contracts is absorbed."""

    RAW_SPLICE = "raw_splice"
    """Take each contract's own prices. Honest, and leaves a seam."""

    FORWARD_ADJUSTED = "forward_adjusted"
    """Shift the NEW contract onto the old one's level. The past never moves."""

    BACK_ADJUSTED = "back_adjusted"
    """Shift every EARLIER bar onto the new level. The past moves at every roll."""

    RATIO_BACK_ADJUSTED = "ratio_back_adjusted"
    """The same, multiplicatively. The past still moves."""


@dataclass(frozen=True)
class Segment:
    """One contract, front from ``starts_at`` until the next segment begins."""

    starts_at: int
    contract: str


Schedule = Sequence[Segment]
Series = Mapping[str, Sequence[Bar]]


class UninformativeProbe(RuntimeError):
    """Asked to measure history-rewriting on a probe that cannot show it.

    Two shapes, one cause. A series with no roll never joins anything, and a
    roll whose two contracts trade at the same price shifts the past by zero -
    so on either, ``BACK_ADJUSTED`` is prefix-stable and would be classified
    safe. Raised rather than answered: a measurement that cannot distinguish its
    cases is not a measurement, and the comfortable answer is the wrong one.
    """


def validate(schedule: Schedule, adjustment: Adjustment) -> list[str]:
    """R1: what makes a roll definition unusable, said rather than coerced."""
    errors: list[str] = []
    if not isinstance(adjustment, Adjustment):
        errors.append(f"adjustment {adjustment!r} is not one of {[a.value for a in Adjustment]}")
    if not schedule:
        errors.append("schedule is empty: no contract is ever front")
        return errors
    if schedule[0].starts_at != 0:
        errors.append(
            f"schedule starts at index {schedule[0].starts_at}, not 0: "
            "the first bars would belong to no contract"
        )
    for earlier, later in zip(schedule, schedule[1:]):
        if later.starts_at <= earlier.starts_at:
            errors.append(
                f"schedule is not ordered: {later.contract} starts at "
                f"{later.starts_at}, at or before {earlier.contract} at {earlier.starts_at}"
            )
    return errors


def calendar_schedule(expiries: Mapping[str, int], roll_offset: int) -> list[Segment]:
    """R2: a schedule from expiry dates, which are known in advance.

    No bar is consulted. The offset is a *parameter* and is not chosen here; how
    many days before expiry to roll depends on where liquidity actually moves,
    and that is a measurement nobody can make while the source is unconnected.
    """
    ordered = sorted(expiries.items(), key=lambda item: item[1])
    segments = [Segment(starts_at=0, contract=ordered[0][0])]
    for (_, expiry), (following, _) in zip(ordered, ordered[1:]):
        segments.append(Segment(starts_at=max(expiry - roll_offset, 0), contract=following))
    return segments


def front_contract(schedule: Schedule, index: int) -> str:
    current = schedule[0].contract
    for segment in schedule:
        if segment.starts_at <= index:
            current = segment.contract
        else:
            break
    return current


def _shift(bar: Bar, offset: float) -> Bar:
    return Bar(high=bar.high + offset, low=bar.low + offset)


def _scale(bar: Bar, factor: float) -> Bar:
    return Bar(high=bar.high * factor, low=bar.low * factor)


def _seam(series: Series, leaving: str, arriving: str, at: int) -> tuple[float, float]:
    """Both contracts' prices on the bar the new one takes over."""
    return series[leaving][at].high, series[arriving][at].high


def build_continuous(
    series: Series,
    schedule: Schedule,
    adjustment: Adjustment,
    as_of: int,
) -> list[Bar]:
    """The continuous series **as it would be known at** ``as_of``.

    R3: no bar after ``as_of`` is returned - not trimmed afterwards but never
    built, because a construction that sees past its own decision point is the
    thing this module exists to catch.

    The difference between the joins lives in one place. ``FORWARD_ADJUSTED``
    accumulates the seam into everything that comes *after* it, so a bar, once
    emitted, is final. ``BACK_ADJUSTED`` walks backwards over bars it already
    emitted and moves them.
    """
    if as_of < 0:
        return []

    rolls = [segment for segment in schedule if 0 < segment.starts_at <= as_of]
    bars: list[Bar] = []
    forward_offset = 0.0

    for index in range(as_of + 1):
        contract = front_contract(schedule, index)
        bar = series[contract][index]
        if adjustment is Adjustment.FORWARD_ADJUSTED:
            roll = next((r for r in rolls if r.starts_at == index), None)
            if roll is not None:
                leaving = front_contract(schedule, index - 1)
                old, new = _seam(series, leaving, contract, index)
                forward_offset += old - new
            bar = _shift(bar, forward_offset)
        bars.append(bar)

    if adjustment in (Adjustment.BACK_ADJUSTED, Adjustment.RATIO_BACK_ADJUSTED):
        # Every roll reaches back over bars that were already emitted. This is
        # the whole point: the loop below is what UPTM-012's S5 forbids.
        for roll in rolls:
            leaving = front_contract(schedule, roll.starts_at - 1)
            old, new = _seam(series, leaving, roll.contract, roll.starts_at)
            for earlier in range(roll.starts_at):
                if adjustment is Adjustment.BACK_ADJUSTED:
                    bars[earlier] = _shift(bars[earlier], new - old)
                else:
                    bars[earlier] = _scale(bars[earlier], new / old)

    return bars


def rewrites_history(
    series: Series,
    schedule: Schedule,
    adjustment: Adjustment,
) -> bool:
    """R7: measured on the probe, not looked up in a list of approved methods.

    A list beside the enum is correct until somebody adds a method and forgets
    to update it, and the failure is silent in the safe direction - the new
    method reads as admissible. So the question is asked of the data: build the
    series at two moments and see whether the earlier bars survived.
    """
    rolls = [segment for segment in schedule if segment.starts_at > 0]
    def has_gap(roll: Segment) -> bool:
        leaving = front_contract(schedule, roll.starts_at - 1)
        old, new = _seam(series, leaving, roll.contract, roll.starts_at)
        return old != new

    if not any(has_gap(roll) for roll in rolls):
        raise UninformativeProbe(
            "the probe has no roll with a price gap, so every join is trivially "
            "stable on it; measuring here would classify a history-rewriting join "
            f"as safe ({len(rolls)} roll(s), none with a seam)"
        )

    last = max(roll.starts_at for roll in rolls)
    before = build_continuous(series, schedule, adjustment, as_of=last - 1)
    after = build_continuous(series, schedule, adjustment, as_of=last)
    return after[: len(before)] != before


def may_use(series: Series, schedule: Schedule, adjustment: Adjustment) -> bool:
    """UPTM-012's invariant, applied to the series a detector would read."""
    return not rewrites_history(series, schedule, adjustment)


def seam_size(series: Series, schedule: Schedule, adjustment: Adjustment, at: int) -> float:
    """R8: what a raw splice leaves behind, so 'admissible' is not read as 'free'.

    The jump between the last bar of the old contract and the first of the new.
    A raw splice carries the whole gap into the series as a move that never
    happened to anybody; forward adjustment removes it and pays by making prices
    no longer equal to what was quoted.
    """
    built = build_continuous(series, schedule, adjustment, as_of=at)
    return built[at].high - built[at - 1].high
