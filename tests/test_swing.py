"""UPTM-012: a swing, and the bar at which it is allowed to be known.

Criteria are preregistered in ``docs/specs/UPTM-012-swing-definition.md``,
written before this file existed. Each test names the criterion it discharges.

**Every price series here is constructed inside this file** (L2). Nothing reads
market data - ES/MES is an open unknown under Directive 4 - and nothing here
looks for a formation or measures a return. These tests are about whether the
definition is mechanical and causal, not about whether anything earns.
"""

from __future__ import annotations

import pytest

from runner.swing import (
    ABSOLUTE,
    RELATIVE,
    Bar,
    Label,
    Swing,
    SwingDefinition,
    SwingKind,
    detect,
    known_at,
    label,
)


def series(*pairs: tuple[float, float]) -> list[Bar]:
    """(high, low) per bar. Constructed, never sourced."""
    return [Bar(high=high, low=low) for high, low in pairs]


def wedge(*highs: float) -> list[Bar]:
    """A series whose lows track its highs, when only the highs are of interest."""
    return [Bar(high=high, low=high - 1) for high in highs]


# A shape with two peaks and a trough between them, wide enough for pivot_bars=2.
TWO_PEAKS = wedge(10, 11, 15, 11, 10, 9, 5, 9, 10, 14, 10, 9)


# --------------------------------------------------------------------------
# S1 - parameters are validated, never coerced
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "kwargs, expected",
    [
        ({"pivot_bars": 0}, ValueError),
        ({"pivot_bars": -3}, ValueError),
        ({"pivot_bars": 2.5}, TypeError),
        ({"pivot_bars": True}, TypeError),
        ({"pivot_bars": 2, "min_amplitude": -0.1}, ValueError),
        ({"pivot_bars": 2, "amplitude_mode": "percent"}, ValueError),
    ],
)
def test_s1_nonsense_parameters_raise_rather_than_being_repaired(kwargs, expected):
    with pytest.raises(expected):
        SwingDefinition(**kwargs)


def test_s1_a_valid_definition_reports_its_own_confirmation_lag():
    assert SwingDefinition(pivot_bars=3).confirmation_lag() == 3


# --------------------------------------------------------------------------
# S2 - strictly beyond both sides; a plateau is not an extreme
# --------------------------------------------------------------------------


def test_s2_a_peak_is_found_only_when_it_beats_both_sides():
    definition = SwingDefinition(pivot_bars=2)
    highs = [swing.index for swing in detect(TWO_PEAKS, definition) if swing.kind is SwingKind.HIGH]
    assert highs == [2, 9]


def test_s2_a_plateau_yields_no_swing():
    """Two bars share the extreme. Choosing one of them would be an invention."""
    tied = wedge(10, 11, 15, 15, 11, 10)
    assert detect(tied, SwingDefinition(pivot_bars=2)) == []

    # The same shape with the tie broken by a hair does produce one.
    broken = wedge(10, 11, 15, 14.99, 11, 10)
    highs = [s for s in detect(broken, SwingDefinition(pivot_bars=2)) if s.kind is SwingKind.HIGH]
    assert [s.index for s in highs] == [2]


def test_s2_a_peak_too_close_to_either_edge_is_not_a_swing():
    """There is no window either side of it, so there is nothing to be beyond."""
    definition = SwingDefinition(pivot_bars=2)
    assert detect(wedge(15, 11, 10, 9), definition) == []
    assert detect(wedge(9, 10, 11, 15), definition) == []


# --------------------------------------------------------------------------
# S3 - every swing says when it becomes knowable
# --------------------------------------------------------------------------


@pytest.mark.parametrize("pivot_bars", [1, 2, 3])
def test_s3_confirmation_is_the_extreme_plus_the_right_hand_window(pivot_bars):
    definition = SwingDefinition(pivot_bars=pivot_bars)
    swings = detect(TWO_PEAKS, definition)
    assert swings, "the fixture must produce something to assert about"
    for swing in swings:
        assert swing.confirmed_at == swing.index + pivot_bars
        # The thing the field exists to prevent.
        assert swing.confirmed_at > swing.index


# --------------------------------------------------------------------------
# S4 - THE INVARIANT: filtering by confirmation == truncating the series
# --------------------------------------------------------------------------


@pytest.mark.parametrize("pivot_bars", [1, 2, 3])
def test_s4_what_is_knowable_at_t_is_what_a_detector_at_t_could_have_found(pivot_bars):
    """Asserted at every cut of the series, not at a chosen one.

    If any future information reached the detector, one of these cuts diverges.
    """
    definition = SwingDefinition(pivot_bars=pivot_bars)
    everything = detect(TWO_PEAKS, definition)
    for cut in range(len(TWO_PEAKS)):
        assert known_at(everything, cut) == detect(TWO_PEAKS[: cut + 1], definition), (
            f"divergence at t={cut}: the detector saw something a live system could not"
        )


def test_s4_the_invariant_also_holds_with_an_amplitude_filter_in_play():
    """The filter compares to an earlier accepted swing, so it must stay causal."""
    definition = SwingDefinition(pivot_bars=2, min_amplitude=3.0, amplitude_mode=ABSOLUTE)
    everything = detect(TWO_PEAKS, definition)
    for cut in range(len(TWO_PEAKS)):
        assert known_at(everything, cut) == detect(TWO_PEAKS[: cut + 1], definition)


def test_s4_a_swing_is_not_knowable_on_the_bar_it_sits_on():
    """Stated on its own because it is the whole point of `confirmed_at`."""
    definition = SwingDefinition(pivot_bars=2)
    peak = detect(TWO_PEAKS, definition)[0]
    assert peak.index == 2
    assert known_at([peak], peak.index) == []
    assert known_at([peak], peak.index + 1) == []
    assert known_at([peak], peak.confirmed_at) == [peak]


# --------------------------------------------------------------------------
# S5 - append-only: the past does not change
# --------------------------------------------------------------------------


@pytest.mark.parametrize("pivot_bars", [1, 2, 3])
def test_s5_what_was_known_stays_known_and_keeps_its_order(pivot_bars):
    definition = SwingDefinition(pivot_bars=pivot_bars)
    everything = detect(TWO_PEAKS, definition)
    for cut in range(1, len(TWO_PEAKS)):
        earlier = known_at(everything, cut - 1)
        later = known_at(everything, cut)
        assert later[: len(earlier)] == earlier, "a swing was withdrawn, repriced or reordered"


def test_s5_two_highs_in_a_row_are_both_kept_rather_than_one_replacing_the_other():
    """ZigZag would withdraw the first. A withdrawn swing may already be acted on."""
    # Rising highs with no qualifying low between them.
    rising = series(
        (10, 5), (11, 5), (15, 5), (11, 5), (12, 5), (18, 5), (12, 5), (11, 5)
    )
    kinds = [swing.kind for swing in detect(rising, SwingDefinition(pivot_bars=2))]
    assert kinds == [SwingKind.HIGH, SwingKind.HIGH]


# --------------------------------------------------------------------------
# S6 - the amplitude filter, and that it is load-bearing
# --------------------------------------------------------------------------


def test_s6_a_move_that_is_too_small_produces_no_swing():
    swings = detect(TWO_PEAKS, SwingDefinition(pivot_bars=2, min_amplitude=0.0))
    assert len(swings) == 3

    # The trough at index 6 is 4; the preceding accepted high is 15. A threshold
    # above that distance rejects it, and the later high then has no accepted
    # low to be measured from.
    strict = detect(TWO_PEAKS, SwingDefinition(pivot_bars=2, min_amplitude=12.0))
    assert [swing.index for swing in strict] == [2, 9]


def test_s6_relative_and_absolute_modes_are_not_the_same_rule():
    bars = TWO_PEAKS
    absolute = detect(bars, SwingDefinition(pivot_bars=2, min_amplitude=0.8, amplitude_mode=ABSOLUTE))
    relative = detect(bars, SwingDefinition(pivot_bars=2, min_amplitude=0.8, amplitude_mode=RELATIVE))
    # One number, two rules: eight tenths of a point, versus eighty per cent.
    # The 15 -> 4 move is 11 points and 73%, so it clears one and not the other.
    assert [swing.index for swing in absolute] == [2, 6, 9]
    assert [swing.index for swing in relative] == [2, 9]


def test_s6_the_filter_measures_from_the_last_accepted_swing_not_the_last_candidate():
    definition = SwingDefinition(pivot_bars=2, min_amplitude=12.0)
    previous = Swing(index=0, price=15.0, kind=SwingKind.HIGH, confirmed_at=2)
    assert definition.moved_far_enough(previous, 3.0) is True
    assert definition.moved_far_enough(previous, 4.0) is False


# --------------------------------------------------------------------------
# S7 - HH / HL / LL / LH, derived and causal
# --------------------------------------------------------------------------


def test_s7_labels_compare_a_swing_to_the_previous_swing_of_its_own_kind():
    swings = [
        Swing(index=0, price=10.0, kind=SwingKind.HIGH, confirmed_at=2),
        Swing(index=4, price=4.0, kind=SwingKind.LOW, confirmed_at=6),
        Swing(index=8, price=12.0, kind=SwingKind.HIGH, confirmed_at=10),
        Swing(index=12, price=5.0, kind=SwingKind.LOW, confirmed_at=14),
        Swing(index=16, price=11.0, kind=SwingKind.HIGH, confirmed_at=18),
        Swing(index=20, price=3.0, kind=SwingKind.LOW, confirmed_at=22),
    ]
    assert label(swings) == [None, None, Label.HH, Label.HL, Label.LH, Label.LL]


def test_s7_the_first_of_each_kind_has_no_label_and_a_tie_has_none_either():
    swings = [
        Swing(index=0, price=10.0, kind=SwingKind.HIGH, confirmed_at=2),
        Swing(index=4, price=10.0, kind=SwingKind.HIGH, confirmed_at=6),
    ]
    assert label(swings) == [None, None]


def test_s7_labelling_a_prefix_gives_the_prefix_of_the_labels():
    """Causality again: no label may depend on a swing that has not happened."""
    swings = detect(TWO_PEAKS, SwingDefinition(pivot_bars=1))
    everything = label(swings)
    for cut in range(len(swings) + 1):
        assert label(swings[:cut]) == everything[:cut]


# --------------------------------------------------------------------------
# S8 - the parameters are the definition; a result without them is not one
# --------------------------------------------------------------------------


def test_s8_changing_pivot_bars_changes_the_answer():
    bars = TWO_PEAKS
    narrow = {(s.index, s.kind) for s in detect(bars, SwingDefinition(pivot_bars=1))}
    wide = {(s.index, s.kind) for s in detect(bars, SwingDefinition(pivot_bars=3))}
    assert narrow != wide
    # And not merely different - the wider window is the stricter one.
    assert wide < narrow


def test_s8_changing_the_amplitude_changes_the_answer():
    bars = TWO_PEAKS
    loose = detect(bars, SwingDefinition(pivot_bars=2, min_amplitude=0.0))
    tight = detect(bars, SwingDefinition(pivot_bars=2, min_amplitude=12.0))
    assert loose != tight


def test_s8_the_confirmation_lag_is_a_consequence_of_the_parameter_not_a_constant():
    """A reported lag that does not move with pivot_bars would be a fixed guess."""
    lags = {
        n: {s.confirmed_at - s.index for s in detect(TWO_PEAKS, SwingDefinition(pivot_bars=n))}
        for n in (1, 2, 3)
    }
    assert lags == {1: {1}, 2: {2}, 3: {3}}
