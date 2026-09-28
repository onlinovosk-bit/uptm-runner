"""UPTM-012: what a swing is, and - the part that matters - when it may be known.

``UPTM-011`` established that all seven reversal formations bottom out on one
undefined term. This is that term, and the causality guard around it.

A swing high at bar ``i`` is not knowable at bar ``i``. The bars to its right
have not happened yet. It becomes knowable at ``i + pivot_bars``, when the
right-hand window closes, and every swing here carries that timestamp because a
detector that uses the other one is reading the future and will report an edge
that nobody could have traded.

``research/candidates/reversal/bearish_quasimodo.json`` forbids "swing points
confirmed by bars later than the decision timestamp". This module is where that
sentence becomes a thing that can fail. The spec, including what it deliberately
does not establish, is ``docs/specs/UPTM-012-swing-definition.md``.

Two choices are made rather than inherited, and both are in the spec's §1:

- **A plateau yields no swing.** A tie is not an extreme, and picking one of two
  equal bars would be a rule a later reader could not reconstruct.
- **Nothing is ever revised.** The usual ZigZag withdraws a swing when a later
  bar makes a better one. A withdrawn swing is one a live system may already
  have acted on, so consecutive same-kind swings are both kept instead.

Nothing here reads market data, looks for a formation, or trades.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Sequence

ABSOLUTE = "absolute"
RELATIVE = "relative"
AMPLITUDE_MODES = frozenset({ABSOLUTE, RELATIVE})


class SwingKind(str, Enum):
    HIGH = "swing_high"
    LOW = "swing_low"

    @property
    def opposite(self) -> "SwingKind":
        return SwingKind.LOW if self is SwingKind.HIGH else SwingKind.HIGH


class Label(str, Enum):
    """A swing read against the previous swing of its own kind."""

    HH = "HH"
    HL = "HL"
    LL = "LL"
    LH = "LH"


@dataclass(frozen=True)
class Bar:
    high: float
    low: float


@dataclass(frozen=True)
class Swing:
    index: int
    """The bar the extreme sits on."""

    price: float
    kind: SwingKind

    confirmed_at: int
    """The earliest bar at which this swing is knowable.

    Not ``index``. The difference between the two is the entire reason this
    field exists: a backtest that treats a swing as known at ``index`` has used
    ``pivot_bars`` bars of future information at every single decision.
    """


@dataclass(frozen=True)
class SwingDefinition:
    """The rule, parametrised. The parameters are not chosen here.

    Choosing ``pivot_bars`` and ``min_amplitude`` requires bar data to choose
    against, and ES/MES data is an open unknown under Directive 4. A number
    picked without data would be a fabricated parameter wearing a definition's
    clothes, so the contract carries ``swing_parameters: UNDEFINED`` and blocks
    on that instead.

    This is ``DEC-UPTM-003``'s shape: the machinery is defined while the
    parameters are unset, and those two are not in tension.
    """

    pivot_bars: int
    min_amplitude: float = 0.0
    amplitude_mode: str = ABSOLUTE

    def __post_init__(self) -> None:
        # Raised, never coerced. A definition that quietly repairs a nonsense
        # parameter reports a result nobody asked for under a name they did.
        if not isinstance(self.pivot_bars, int) or isinstance(self.pivot_bars, bool):
            raise TypeError(f"pivot_bars must be an int, got {type(self.pivot_bars).__name__}")
        if self.pivot_bars < 1:
            raise ValueError(f"pivot_bars must be at least 1, got {self.pivot_bars}")
        if self.min_amplitude < 0:
            raise ValueError(f"min_amplitude must not be negative, got {self.min_amplitude}")
        if self.amplitude_mode not in AMPLITUDE_MODES:
            raise ValueError(
                f"amplitude_mode must be one of {sorted(AMPLITUDE_MODES)}, "
                f"got {self.amplitude_mode!r}"
            )

    def confirmation_lag(self) -> int:
        """Bars between a swing existing and a live system being allowed to see it."""
        return self.pivot_bars

    def moved_far_enough(self, previous: Swing, price: float) -> bool:
        """Is the move from ``previous`` large enough to accept a swing at ``price``?

        Measured against the last *accepted* swing of the opposite kind, which
        was confirmed strictly earlier - so this question is answerable at
        ``confirmed_at`` and carries no future information.
        """
        move = abs(price - previous.price)
        if self.amplitude_mode == RELATIVE:
            if previous.price == 0:
                return move >= self.min_amplitude
            return move / abs(previous.price) >= self.min_amplitude
        return move >= self.min_amplitude


def _is_pivot(bars: Sequence[Bar], index: int, reach: int, kind: SwingKind) -> bool:
    """Strictly beyond every bar within ``reach`` on BOTH sides. Ties yield nothing."""
    if index - reach < 0 or index + reach > len(bars) - 1:
        return False
    if kind is SwingKind.HIGH:
        pivot = bars[index].high
        return all(
            bars[other].high < pivot
            for other in range(index - reach, index + reach + 1)
            if other != index
        )
    pivot = bars[index].low
    return all(
        bars[other].low > pivot
        for other in range(index - reach, index + reach + 1)
        if other != index
    )


def detect(bars: Sequence[Bar], definition: SwingDefinition) -> list[Swing]:
    """Every swing in ``bars``, in confirmation order, each carrying when it is knowable.

    Causality is structural rather than checked afterwards: a candidate at
    ``index`` is decided only by bars within ``pivot_bars`` of it, and the
    amplitude test compares it only to a swing confirmed strictly earlier. That
    is what makes the spec's §2 invariant hold - filtering this list by
    ``confirmed_at`` and truncating ``bars`` before calling this give the same
    answer, for every cut.
    """
    reach = definition.pivot_bars
    accepted: list[Swing] = []
    last_by_kind: dict[SwingKind, Swing] = {}

    for index in range(len(bars)):
        for kind in (SwingKind.HIGH, SwingKind.LOW):
            if not _is_pivot(bars, index, reach, kind):
                continue
            price = bars[index].high if kind is SwingKind.HIGH else bars[index].low
            previous_opposite = last_by_kind.get(kind.opposite)
            if previous_opposite is not None and not definition.moved_far_enough(
                previous_opposite, price
            ):
                continue
            swing = Swing(
                index=index,
                price=price,
                kind=kind,
                confirmed_at=index + reach,
            )
            accepted.append(swing)
            last_by_kind[kind] = swing

    return accepted


def known_at(swings: Iterable[Swing], when: int) -> list[Swing]:
    """The swings a system at bar ``when`` is allowed to have seen.

    The only honest way to ask a detector what it knew. Anything that reads the
    full list at a decision point is reading ahead by ``pivot_bars`` bars.
    """
    return [swing for swing in swings if swing.confirmed_at <= when]


def label(swings: Sequence[Swing]) -> list[Label | None]:
    """Each swing read against the previous swing of its own kind.

    ``None`` where there is no predecessor of that kind, and ``None`` on an
    exact tie - a swing equal to the last one is neither higher nor lower, and
    calling it either would be an invention.

    Causal by construction: a label depends only on swings that came before, so
    labelling a prefix gives the same answer as labelling the whole list and
    taking that prefix.
    """
    labels: list[Label | None] = []
    previous: dict[SwingKind, Swing] = {}
    for swing in swings:
        earlier = previous.get(swing.kind)
        if earlier is None or swing.price == earlier.price:
            labels.append(None)
        elif swing.kind is SwingKind.HIGH:
            labels.append(Label.HH if swing.price > earlier.price else Label.LH)
        else:
            labels.append(Label.HL if swing.price > earlier.price else Label.LL)
        previous[swing.kind] = swing
    return labels
