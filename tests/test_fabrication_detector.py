"""UPTM-002 — the 34 preregistered acceptance cases.

Each case is a mutation of an otherwise valid evidence pack, so "the detector
works" and "the mutations were caught" are the same statement rather than two.
The case ids are read from the preregistration, and a test asserts that every
preregistered id is exercised here — a case cannot be silently skipped.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from runner.detectors.fabrication import (
    check_md_i1_digest,
    check_md_i2_snapshot_exists,
    check_md_i3_coverage,
    check_md_i4_ohlc,
    check_md_i5_degenerate,
    check_md_i6_calendar,
    check_md_i7_duplicate_block,
    check_md_p1_provenance,
    check_pl_a1_recomputation,
    check_pl_a2_fill_lineage,
    check_pl_a3_position_conservation,
    check_pl_m1_pnl_without_fills,
    check_pl_m2_fees_and_slippage,
    detect_fabricated_market_data,
    detect_fabricated_pnl,
    worst,
)
from runner.paths import ROOT
from runner.verdict import Decision, Verdict, resolve

SPEC = json.loads(
    (ROOT / "docs" / "specs" / "UPTM-002-fabrication-stop-conditions.json").read_text(
        encoding="utf-8"
    )
)

SESSIONS = ["2026-09-14", "2026-09-15", "2026-09-16", "2026-09-17", "2026-09-18"]
CLOSES = [100.0, 101.5, 99.0, 102.0, 103.5]


def _bars(closes=None, days=None):
    closes = closes or CLOSES
    days = days or SESSIONS
    out = []
    for day, close in zip(days, closes):
        out.append(
            {
                "ts": f"{day}T20:00:00Z",
                "open": close - 0.5,
                "high": close + 1.0,
                "low": close - 1.0,
                "close": close,
                "volume": 1000,
            }
        )
    return out


@pytest.fixture
def snapshots(tmp_path) -> Path:
    root = tmp_path / "snapshots"
    root.mkdir()
    (root / "series.json").write_text(json.dumps(_bars()), encoding="utf-8")
    return root


@pytest.fixture
def md(snapshots) -> dict:
    """A market-data pack for which every MD check returns PASS."""
    digest = hashlib.sha256((snapshots / "series.json").read_bytes()).hexdigest()
    return {
        "source_id": "vendor-x:EQ:ACME:1d",
        "acquired_at_utc": "2026-09-19T06:00:00Z",
        "content_digest": digest,
        "snapshot_ref": "series.json",
        "coverage": {"first": SESSIONS[0], "last": SESSIONS[-1]},
        "computation_interval": {"first": SESSIONS[1], "last": SESSIONS[-1]},
        "min_expected_variance": 0.01,
        "variance_window": 3,
        "calendar_id": "XNYS",
        "duplicate_block_min_len": 3,
        "allows_repeated_bars": False,
        "bars": _bars(),
    }


@pytest.fixture
def calendars() -> dict:
    return {"XNYS": set(SESSIONS)}


@pytest.fixture
def pnl() -> dict:
    """A PnL pack for which every PL check returns PASS."""
    return {
        "accounting_boundary": {"opening_position": 0.0, "opening_mark": 100.0},
        "quantity_convention": "signed_long_positive",
        "pnl_tolerance": {"absolute": 0.01, "relative": 0.001},
        "execution_model": {"charges_fees": True, "charges_slippage": True},
        "gated_order_ids": ["ord-1"],
        "fills": [
            {"order_id": "ord-1", "qty": 10.0, "price": 100.0, "fee": 1.0, "slippage": 0.5}
        ],
        "position_after": 10.0,
        "mark_price": 105.0,
        "reported_pnl": 48.5,
        "realized_pnl": -1001.5,
        "unrealized_pnl": 50.0,
    }


@pytest.fixture
def carry(pnl) -> dict:
    """A run with no fills and a non-zero opening position (legitimate carry-over)."""
    p = copy.deepcopy(pnl)
    p["accounting_boundary"] = {"opening_position": 10.0, "opening_mark": 100.0}
    p["fills"] = []
    p["position_after"] = 10.0
    p["realized_pnl"] = 0.0
    p["unrealized_pnl"] = 50.0
    p["reported_pnl"] = 50.0
    return p


def _drop(pack: dict, key: str) -> dict:
    out = copy.deepcopy(pack)
    out.pop(key, None)
    return out


# ---------------------------------------------------------------- must FAIL


def test_mut_01_ohlc_high_below_close(md):
    m = copy.deepcopy(md)
    m["bars"][2]["high"] = m["bars"][2]["close"] - 0.5
    assert check_md_i4_ohlc(m).verdict is Verdict.FAIL


def test_mut_02_snapshot_byte_changed_digest_unchanged(md, snapshots):
    (snapshots / "series.json").write_text(
        json.dumps(_bars(closes=[100.0, 101.5, 99.0, 102.0, 103.6])), encoding="utf-8"
    )
    assert check_md_i1_digest(md, snapshots).verdict is Verdict.FAIL


def test_mut_03_referenced_snapshot_absent(md, snapshots):
    m = copy.deepcopy(md)
    m["snapshot_ref"] = "does-not-exist.json"
    assert check_md_i2_snapshot_exists(m, snapshots).verdict is Verdict.FAIL


def test_mut_04_coverage_truncated_below_computation_interval(md):
    m = copy.deepcopy(md)
    m["coverage"] = {"first": SESSIONS[2], "last": SESSIONS[-1]}
    assert check_md_i3_coverage(m).verdict is Verdict.FAIL


def test_mut_05_bar_on_a_closed_calendar_date(md, calendars):
    m = copy.deepcopy(md)
    m["bars"].append({**m["bars"][0], "ts": "2026-09-19T20:00:00Z"})
    assert check_md_i6_calendar(m, calendars).verdict is Verdict.FAIL


def test_mut_06_duplicate_block_copied(md):
    m = copy.deepcopy(md)
    m["duplicate_block_min_len"] = 2
    m["bars"] = m["bars"][:2] + m["bars"][:2] + m["bars"][2:]
    assert check_md_i7_duplicate_block(m).verdict is Verdict.FAIL


def test_mut_07_flat_series_below_declared_variance(md):
    m = copy.deepcopy(md)
    m["bars"] = _bars(closes=[100.0] * 5)
    assert check_md_i5_degenerate(m).verdict is Verdict.FAIL


def test_mut_08_reported_pnl_beyond_tolerance(pnl):
    p = copy.deepcopy(pnl)
    p["reported_pnl"] = 148.5
    assert check_pl_a1_recomputation(p).verdict is Verdict.FAIL


def test_mut_09_orphan_fill(pnl):
    p = copy.deepcopy(pnl)
    p["fills"][0]["order_id"] = "ord-unknown"
    assert check_pl_a2_fill_lineage(p).verdict is Verdict.FAIL


def test_mut_10_position_after_altered(pnl):
    p = copy.deepcopy(pnl)
    p["position_after"] = 11.0
    assert check_pl_a3_position_conservation(p).verdict is Verdict.FAIL


def test_mut_11_realized_pnl_with_empty_fill_ledger(carry):
    p = copy.deepcopy(carry)
    p["realized_pnl"] = 25.0
    assert check_pl_m1_pnl_without_fills(p).verdict is Verdict.FAIL


def test_mut_12_declared_fees_but_zero_in_ledger(pnl):
    p = copy.deepcopy(pnl)
    p["fills"][0]["fee"] = 0.0
    assert check_pl_m2_fees_and_slippage(p).verdict is Verdict.FAIL


# ------------------------------------------------------------- must UNKNOWN


@pytest.mark.parametrize(
    ("case_id", "key"),
    [
        ("MUT-13", "content_digest"),
        ("MUT-21", "source_id"),
        ("MUT-22", "acquired_at_utc"),
        ("MUT-23", "coverage"),
    ],
)
def test_md_p1_missing_provenance_is_unknown(md, case_id, key):
    assert check_md_p1_provenance(_drop(md, key)).verdict is Verdict.UNKNOWN


def test_mut_14_undeclared_min_expected_variance(md):
    m = _drop(md, "min_expected_variance")
    m["bars"] = _bars(closes=[100.0] * 5)
    assert check_md_i5_degenerate(m).verdict is Verdict.UNKNOWN


def test_mut_15_undeclared_calendar_id(md, calendars):
    assert check_md_i6_calendar(_drop(md, "calendar_id"), calendars).verdict is Verdict.UNKNOWN


def test_mut_16_undeclared_duplicate_block_min_len(md):
    m = _drop(md, "duplicate_block_min_len")
    m["bars"] = m["bars"][:2] + m["bars"][:2] + m["bars"][2:]
    assert check_md_i7_duplicate_block(m).verdict is Verdict.UNKNOWN


def test_mut_17_undeclared_pnl_tolerance(pnl):
    assert check_pl_a1_recomputation(_drop(pnl, "pnl_tolerance")).verdict is Verdict.UNKNOWN


def test_mut_18_undeclared_accounting_boundary(pnl):
    assert check_pl_m1_pnl_without_fills(_drop(pnl, "accounting_boundary")).verdict is Verdict.UNKNOWN


def test_mut_19_undeclared_quantity_convention(pnl):
    assert check_pl_a3_position_conservation(_drop(pnl, "quantity_convention")).verdict is Verdict.UNKNOWN


def test_mut_20_undeclared_execution_model(pnl):
    assert check_pl_m2_fees_and_slippage(_drop(pnl, "execution_model")).verdict is Verdict.UNKNOWN


def test_mut_24_undeclared_snapshot_ref(md, snapshots):
    assert check_md_i2_snapshot_exists(_drop(md, "snapshot_ref"), snapshots).verdict is Verdict.UNKNOWN


def test_mut_25_undeclared_computation_interval(md):
    assert check_md_i3_coverage(_drop(md, "computation_interval")).verdict is Verdict.UNKNOWN


def test_mut_26_undeclared_variance_window(md):
    assert check_md_i5_degenerate(_drop(md, "variance_window")).verdict is Verdict.UNKNOWN


def test_mut_27_undeclared_allows_repeated_bars(md):
    assert check_md_i7_duplicate_block(_drop(md, "allows_repeated_bars")).verdict is Verdict.UNKNOWN


def test_mut_28_undeclared_content_digest_for_integrity_check(md, snapshots):
    assert check_md_i1_digest(_drop(md, "content_digest"), snapshots).verdict is Verdict.UNKNOWN


def test_mut_29_undeclared_coverage_for_sufficiency_check(md):
    assert check_md_i3_coverage(_drop(md, "coverage")).verdict is Verdict.UNKNOWN


# ---------------------------------------------- must PASS (false positives)


def test_neg_01_flat_series_with_declared_zero_variance(md):
    m = copy.deepcopy(md)
    m["bars"] = _bars(closes=[100.0] * 5)
    m["min_expected_variance"] = 0.0
    assert check_md_i5_degenerate(m).verdict is Verdict.PASS


def test_neg_02_zero_fees_under_a_declared_frictionless_simulation(pnl):
    p = copy.deepcopy(pnl)
    p["execution_model"] = {"charges_fees": False, "charges_slippage": False}
    p["fills"][0]["fee"] = 0.0
    p["fills"][0]["slippage"] = 0.0
    assert check_pl_m2_fees_and_slippage(p).verdict is Verdict.PASS


def test_neg_03_carry_over_unrealized_pnl_reconciles_with_marks(carry):
    assert check_pl_m1_pnl_without_fills(carry).verdict is Verdict.PASS


def test_neg_04_repeated_bars_declared_legitimate(md):
    m = copy.deepcopy(md)
    m["allows_repeated_bars"] = True
    m["bars"] = m["bars"][:2] + m["bars"][:2] + m["bars"][2:]
    assert check_md_i7_duplicate_block(m).verdict is Verdict.PASS


def test_neg_05_gap_over_a_declared_market_holiday(md):
    """The holiday is simply not a session, so the gap is not a missing bar."""
    days = [d for d in SESSIONS if d != "2026-09-16"]
    m = copy.deepcopy(md)
    m["bars"] = _bars(closes=[100.0, 101.5, 102.0, 103.5], days=days)
    assert check_md_i6_calendar(m, {"XNYS": set(days)}).verdict is Verdict.PASS


# ---------------------------------------------------- suite-level behaviour


def test_valid_packs_pass_every_check(md, snapshots, calendars, pnl):
    md_out = detect_fabricated_market_data(md, snapshot_root=snapshots, calendars=calendars)
    pl_out = detect_fabricated_pnl(pnl)
    assert worst(md_out) is Verdict.PASS, [(o.check_id, o.detail) for o in md_out if o.verdict is not Verdict.PASS]
    assert worst(pl_out) is Verdict.PASS, [(o.check_id, o.detail) for o in pl_out if o.verdict is not Verdict.PASS]


def test_detectors_return_verdicts_never_decisions(md, snapshots, calendars, pnl):
    """CC/P13-adjacent: a detector reports; it does not decide."""
    for outcome in detect_fabricated_market_data(md, snapshot_root=snapshots, calendars=calendars):
        assert isinstance(outcome.verdict, Verdict)
        assert not isinstance(outcome.verdict, Decision)
    for outcome in detect_fabricated_pnl(pnl):
        assert isinstance(outcome.verdict, Verdict)


def test_unknown_denies_without_raising_a_stop_condition(md, snapshots, calendars):
    """FAIL and UNKNOWN both deny; only FAIL asserts a violation."""
    m = _drop(md, "calendar_id")
    outcome = check_md_i6_calendar(m, calendars)
    assert outcome.verdict is Verdict.UNKNOWN
    assert resolve(outcome.verdict) is Decision.DENY
    assert outcome.stop_condition_raised is False

    m2 = copy.deepcopy(md)
    m2["bars"][0]["high"] = 0.1
    failed = check_md_i4_ohlc(m2)
    assert failed.verdict is Verdict.FAIL
    assert resolve(failed.verdict) is Decision.DENY
    assert failed.stop_condition_raised is True


def test_fail_dominates_unknown_when_both_present(md, snapshots, calendars):
    m = _drop(md, "calendar_id")
    m["bars"][0]["high"] = 0.1
    assert worst(detect_fabricated_market_data(m, snapshot_root=snapshots, calendars=calendars)) is Verdict.FAIL


# ------------------------------------------- the preregistration is honoured


def test_every_preregistered_case_id_is_exercised():
    """A preregistered case with no test would be a silently skipped criterion."""
    preregistered = {
        c["id"] for group in SPEC["acceptance_cases"].values() for c in group
    }
    source = Path(__file__).read_text(encoding="utf-8")
    # A case is exercised either as a test name (mut_01) or as a parametrised id ("MUT-01").
    missing = {
        cid
        for cid in preregistered
        if cid not in source and cid.lower().replace("-", "_") not in source
    }
    assert not missing, f"preregistered cases with no test: {sorted(missing)}"


def test_every_preregistered_check_id_has_an_implementation():
    from runner.detectors import fabrication

    implemented = {
        getattr(fabrication, n).__doc__.split("—")[0].strip()
        for n in dir(fabrication)
        if n.startswith("check_")
    }
    declared = {c["id"] for c in SPEC["checks"]}
    assert declared == implemented, f"mismatch: {sorted(declared ^ implemented)}"
