"""UPTM-014: which joins are admissible, measured rather than declared.

Criteria are preregistered in `docs/specs/UPTM-014-roll-rule.md`, written before
this file existed. Each test names the criterion it discharges.

**Every contract series here is constructed in this file** (L2). Nothing reads
market data and nothing opens a socket - the source is still at
`MAPPED_UNVERIFIED`, and `runner.data_sources` would refuse anyway.
"""

from __future__ import annotations

import pytest

from runner.roll import (
    Adjustment,
    UninformativeProbe,
    Segment,
    build_continuous,
    calendar_schedule,
    front_contract,
    may_use,
    rewrites_history,
    seam_size,
    validate,
)
from runner.swing import Bar, SwingDefinition, SwingKind, detect, known_at

ROLL_AT = 5

# Two contracts, the later one trading ten points above the earlier - contango,
# and the reason a seam exists at all. Invented here; no price is from a market.
OLD = "ESZ6"
NEW = "ESH7"


def contract(*highs: float) -> list[Bar]:
    return [Bar(high=high, low=high - 1) for high in highs]


# A peak at index 2, well before the roll, so a swing is confirmed while the old
# contract is still front.
SERIES = {
    OLD: contract(100, 101, 105, 101, 100, 99, 98, 97),
    NEW: contract(110, 111, 115, 111, 110, 109, 108, 107),
}
SCHEDULE = [Segment(starts_at=0, contract=OLD), Segment(starts_at=ROLL_AT, contract=NEW)]

NO_ROLL = [Segment(starts_at=0, contract=OLD)]

ADMISSIBLE = (Adjustment.RAW_SPLICE, Adjustment.FORWARD_ADJUSTED)
REWRITING = (Adjustment.BACK_ADJUSTED, Adjustment.RATIO_BACK_ADJUSTED)


def highs(bars: list[Bar]) -> list[float]:
    return [round(bar.high, 6) for bar in bars]


# --------------------------------------------------------------------------
# R1 - a roll definition is validated, not coerced
# --------------------------------------------------------------------------


def test_r1_a_usable_definition_reports_nothing(_=None):
    assert validate(SCHEDULE, Adjustment.RAW_SPLICE) == []


def test_r1_an_empty_schedule_is_an_error():
    errors = validate([], Adjustment.RAW_SPLICE)
    assert errors == ["schedule is empty: no contract is ever front"]


def test_r1_a_schedule_that_does_not_start_at_the_first_bar_is_an_error():
    errors = validate([Segment(starts_at=3, contract=OLD)], Adjustment.RAW_SPLICE)
    assert len(errors) == 1
    assert "belong to no contract" in errors[0]


def test_r1_an_unordered_schedule_is_an_error():
    unordered = [Segment(0, OLD), Segment(5, NEW), Segment(5, "ESM7")]
    errors = validate(unordered, Adjustment.RAW_SPLICE)
    assert len(errors) == 1
    assert "not ordered" in errors[0]


def test_r1_an_adjustment_that_is_not_one_of_the_family_is_an_error():
    errors = validate(SCHEDULE, "smoothed")
    assert len(errors) == 1
    assert "'smoothed'" in errors[0]


# --------------------------------------------------------------------------
# R2 - the front contract is decided in advance, from expiries
# --------------------------------------------------------------------------


def test_r2_a_calendar_schedule_is_built_from_expiries_alone():
    schedule = calendar_schedule({NEW: 12, OLD: 6}, roll_offset=1)
    assert schedule == [Segment(0, OLD), Segment(5, NEW)]


def test_r2_the_roll_offset_is_a_parameter_and_moves_the_schedule():
    """It is not chosen here: where liquidity moves is a measurement nobody has."""
    assert calendar_schedule({NEW: 12, OLD: 6}, roll_offset=3)[1].starts_at == 3
    assert calendar_schedule({NEW: 12, OLD: 6}, roll_offset=0)[1].starts_at == 6


def test_r2_the_front_contract_changes_only_at_the_roll():
    assert [front_contract(SCHEDULE, i) for i in range(8)] == [OLD] * 5 + [NEW] * 3


# --------------------------------------------------------------------------
# R3 - as_of is a cut, not a trim
# --------------------------------------------------------------------------


@pytest.mark.parametrize("adjustment", list(Adjustment))
@pytest.mark.parametrize("as_of", range(8))
def test_r3_no_bar_after_as_of_is_returned(adjustment, as_of):
    assert len(build_continuous(SERIES, SCHEDULE, adjustment, as_of)) == as_of + 1


def test_r3_a_negative_as_of_yields_nothing_rather_than_raising():
    assert build_continuous(SERIES, SCHEDULE, Adjustment.RAW_SPLICE, -1) == []


# --------------------------------------------------------------------------
# R4 - prefix stability, measured at every cut
# --------------------------------------------------------------------------


@pytest.mark.parametrize("adjustment", ADMISSIBLE)
def test_r4_an_admissible_join_never_moves_a_bar_it_has_already_emitted(adjustment):
    for cut in range(1, 8):
        earlier = build_continuous(SERIES, SCHEDULE, adjustment, cut - 1)
        later = build_continuous(SERIES, SCHEDULE, adjustment, cut)
        assert later[: len(earlier)] == earlier, f"a bar moved between t={cut - 1} and t={cut}"


def test_r4_forward_adjustment_absorbs_the_seam_into_what_comes_after():
    built = build_continuous(SERIES, SCHEDULE, Adjustment.FORWARD_ADJUSTED, 7)
    # The old contract's own prices, untouched, continued at the old level.
    assert highs(built) == [100, 101, 105, 101, 100, 99, 98, 97]


def test_r4_a_raw_splice_keeps_each_contract_honest():
    built = build_continuous(SERIES, SCHEDULE, Adjustment.RAW_SPLICE, 7)
    assert highs(built) == [100, 101, 105, 101, 100, 109, 108, 107]


# --------------------------------------------------------------------------
# R5 - the counter-measurement, with the bar and both prices named
# --------------------------------------------------------------------------


def test_r5_back_adjustment_changes_a_price_it_already_published():
    """Not an abstract inequality: this bar, this price, then that price."""
    before = build_continuous(SERIES, SCHEDULE, Adjustment.BACK_ADJUSTED, ROLL_AT - 1)
    after = build_continuous(SERIES, SCHEDULE, Adjustment.BACK_ADJUSTED, ROLL_AT)

    assert before[2].high == 105, "the peak as published before the roll"
    assert after[2].high == 115, "the same bar after a roll that happened later"
    assert after[: len(before)] != before


def test_r5_ratio_adjustment_rewrites_the_past_too_just_multiplicatively():
    before = build_continuous(SERIES, SCHEDULE, Adjustment.RATIO_BACK_ADJUSTED, ROLL_AT - 1)
    after = build_continuous(SERIES, SCHEDULE, Adjustment.RATIO_BACK_ADJUSTED, ROLL_AT)
    assert before[2].high == 105
    assert after[2].high == pytest.approx(105 * (109 / 99))
    assert after[: len(before)] != before


# --------------------------------------------------------------------------
# R6 - the collision with UPTM-012, shown rather than argued
# --------------------------------------------------------------------------

PIVOT = SwingDefinition(pivot_bars=1)


def _confirmed_peak(adjustment: Adjustment, as_of: int):
    bars = build_continuous(SERIES, SCHEDULE, adjustment, as_of)
    swings = known_at(detect(bars, PIVOT), as_of)
    return next(swing for swing in swings if swing.kind is SwingKind.HIGH and swing.index == 2)


@pytest.mark.parametrize("adjustment", ADMISSIBLE)
def test_r6_a_swing_confirmed_before_the_roll_survives_an_admissible_join(adjustment):
    before = _confirmed_peak(adjustment, ROLL_AT - 1)
    after = _confirmed_peak(adjustment, 7)
    assert before.price == after.price == 105
    assert before.confirmed_at == after.confirmed_at == 3


def test_r6_back_adjustment_reprices_a_swing_that_was_already_confirmed():
    """UPTM-012's S5 is what forbids the method. Not preference - the invariant."""
    before = _confirmed_peak(Adjustment.BACK_ADJUSTED, ROLL_AT - 1)
    after = _confirmed_peak(Adjustment.BACK_ADJUSTED, 7)

    assert before.confirmed_at == 3, "confirmed two bars before the roll"
    assert before.price == 105
    assert after.price == 115, "repriced by a roll that had not happened when it was confirmed"


# --------------------------------------------------------------------------
# R7 - admissibility is measured, and refuses a probe that cannot decide
# --------------------------------------------------------------------------


@pytest.mark.parametrize("adjustment", list(Adjustment))
def test_r7_every_member_of_the_family_is_classified_by_measurement(adjustment):
    measured = rewrites_history(SERIES, SCHEDULE, adjustment)
    assert measured is (adjustment in REWRITING)
    assert may_use(SERIES, SCHEDULE, adjustment) is not measured


def test_r7_a_probe_without_a_roll_raises_rather_than_reassuring():
    """Every join is stable on a series that never joins anything."""
    with pytest.raises(UninformativeProbe) as raised:
        rewrites_history(SERIES, NO_ROLL, Adjustment.BACK_ADJUSTED)
    assert "no roll with a price gap" in str(raised.value)


def test_r7_a_roll_with_no_gap_is_refused_for_the_same_reason():
    """Implemented one notch broader than R7 preregistered, and for its reason.

    Back adjustment shifts the past by the seam. A seam of zero shifts it by
    nothing, so this probe would classify the method as safe just as confidently
    as a roll-free one. Same cause, same refusal.
    """
    flat = {OLD: contract(100, 101, 102, 103, 104, 105), NEW: contract(0, 0, 0, 0, 0, 105)}
    schedule = [Segment(0, OLD), Segment(ROLL_AT, NEW)]

    # It really is stable on this probe, which is why answering would mislead.
    before = build_continuous(flat, schedule, Adjustment.BACK_ADJUSTED, ROLL_AT - 1)
    after = build_continuous(flat, schedule, Adjustment.BACK_ADJUSTED, ROLL_AT)
    assert after[: len(before)] == before

    with pytest.raises(UninformativeProbe):
        rewrites_history(flat, schedule, Adjustment.BACK_ADJUSTED)


def test_r7_the_measurement_reads_the_bars_not_the_method_name():
    """The same method, two probes, and the classification follows the data."""
    assert rewrites_history(SERIES, SCHEDULE, Adjustment.BACK_ADJUSTED) is True
    wider = {
        OLD: SERIES[OLD],
        NEW: contract(200, 201, 205, 201, 200, 199, 198, 197),
    }
    assert rewrites_history(wider, SCHEDULE, Adjustment.BACK_ADJUSTED) is True
    # ...and the admissible one stays admissible on both, for the same reason.
    assert rewrites_history(wider, SCHEDULE, Adjustment.FORWARD_ADJUSTED) is False


# --------------------------------------------------------------------------
# R8 - admissible is not free
# --------------------------------------------------------------------------


def test_r8_a_raw_splice_carries_a_move_that_happened_to_nobody():
    """From 100 to 109 in one bar, because the contract changed underneath."""
    assert seam_size(SERIES, SCHEDULE, Adjustment.RAW_SPLICE, ROLL_AT) == pytest.approx(9.0)


def test_r8_forward_adjustment_removes_the_seam_and_pays_for_it_elsewhere():
    assert seam_size(SERIES, SCHEDULE, Adjustment.FORWARD_ADJUSTED, ROLL_AT) == pytest.approx(-1.0)
    # The price it pays: after the roll, no bar equals what was quoted.
    built = build_continuous(SERIES, SCHEDULE, Adjustment.FORWARD_ADJUSTED, 7)
    assert built[7].high == 97
    assert SERIES[NEW][7].high == 107


def test_r8_the_trade_off_is_left_open_by_this_spec():
    """Both are admissible. Which is right needs seam sizes nobody can measure yet."""
    for adjustment in ADMISSIBLE:
        assert may_use(SERIES, SCHEDULE, adjustment) is True
