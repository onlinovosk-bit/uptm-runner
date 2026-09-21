"""Detectors for `fabricated_market_data` and `fabricated_pnl`.

Implements the criteria preregistered in
docs/specs/UPTM-002-fabrication-stop-conditions.md, written before this module
existed (CC/P4).

What these detectors claim
--------------------------
They never report that data was fabricated. A sufficiently consistent forgery
passes every check here. They report that a required property of verifiability
or internal consistency does not hold:

    data or accounting whose provenance cannot be verified, or whose internal
    consistency cannot be reproduced, is treated as fabricated for safety
    purposes.

Verdicts only
-------------
Every check returns a Verdict and never a Decision. Resolution is the caller's,
through runner.verdict.resolve / resolve_all, so that no detector carries its
own reading of UNKNOWN.

A missing preregistered parameter is UNKNOWN, never a default. A default would
be this module guessing an instrument's behaviour, which is the false-positive
risk the specification exists to avoid.
"""

from __future__ import annotations

import hashlib
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

from runner.verdict import Verdict

OHLC = ("open", "high", "low", "close")


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


def _missing(pack: dict[str, Any], *params: str) -> list[str]:
    return [p for p in params if pack.get(p) is None]


def _unknown(check_id: str, absent: Iterable[str]) -> CheckOutcome:
    names = ", ".join(sorted(absent))
    return CheckOutcome(
        check_id, Verdict.UNKNOWN, f"undeclared preregistered parameter(s): {names}"
    )


def _ok(check_id: str, detail: str = "property holds") -> CheckOutcome:
    return CheckOutcome(check_id, Verdict.PASS, detail)


def _fail(check_id: str, detail: str) -> CheckOutcome:
    return CheckOutcome(check_id, Verdict.FAIL, detail)


# --------------------------------------------------------------------------
# fabricated_market_data
# --------------------------------------------------------------------------


def check_md_p1_provenance(pack: dict[str, Any]) -> CheckOutcome:
    """MD-P1 — the four provenance fields are declared."""
    absent = _missing(pack, "source_id", "acquired_at_utc", "content_digest", "coverage")
    return _unknown("MD-P1", absent) if absent else _ok("MD-P1")


def check_md_i1_digest(pack: dict[str, Any], snapshot_root: Path) -> CheckOutcome:
    """MD-I1 — the snapshot recomputes to the declared digest."""
    absent = _missing(pack, "content_digest")
    if absent:
        return _unknown("MD-I1", absent)
    ref = pack.get("snapshot_ref")
    if ref is None:
        return _unknown("MD-I1", ["snapshot_ref"])
    path = snapshot_root / ref
    try:
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        return _fail("MD-I1", f"snapshot unreadable: {exc}")
    if actual != pack["content_digest"]:
        return _fail(
            "MD-I1",
            f"digest mismatch: recomputed {actual[:16]}… != declared "
            f"{str(pack['content_digest'])[:16]}…",
        )
    return _ok("MD-I1")


def check_md_i2_snapshot_exists(pack: dict[str, Any], snapshot_root: Path) -> CheckOutcome:
    """MD-I2 — the referenced snapshot is present in the evidence store."""
    absent = _missing(pack, "snapshot_ref")
    if absent:
        return _unknown("MD-I2", absent)
    if not (snapshot_root / pack["snapshot_ref"]).is_file():
        return _fail("MD-I2", f"referenced snapshot absent: {pack['snapshot_ref']}")
    return _ok("MD-I2")


def check_md_i3_coverage(pack: dict[str, Any]) -> CheckOutcome:
    """MD-I3 — coverage contains the whole interval the result was computed over."""
    absent = _missing(pack, "coverage", "computation_interval")
    if absent:
        return _unknown("MD-I3", absent)
    cov, comp = pack["coverage"], pack["computation_interval"]
    if cov.get("first") is None or cov.get("last") is None:
        return _unknown("MD-I3", ["coverage.first/last"])
    if comp["first"] < cov["first"] or comp["last"] > cov["last"]:
        return _fail(
            "MD-I3",
            f"coverage [{cov['first']}, {cov['last']}] does not contain "
            f"computation interval [{comp['first']}, {comp['last']}]",
        )
    return _ok("MD-I3")


def check_md_i4_ohlc(pack: dict[str, Any]) -> CheckOutcome:
    """MD-I4 — low <= min(open, close) and max(open, close) <= high, values sane."""
    for i, bar in enumerate(pack.get("bars") or []):
        values = [bar.get(k) for k in OHLC]
        if any(v is None for v in values):
            return _fail("MD-I4", f"bar {i}: incomplete OHLC")
        if any(not isinstance(v, (int, float)) or v <= 0 for v in values):
            return _fail("MD-I4", f"bar {i}: non-positive or non-numeric price")
        if bar.get("volume") is not None and bar["volume"] < 0:
            return _fail("MD-I4", f"bar {i}: negative volume")
        lo, hi = bar["low"], bar["high"]
        if lo > min(bar["open"], bar["close"]) or max(bar["open"], bar["close"]) > hi:
            return _fail(
                "MD-I4",
                f"bar {i}: OHLC invariant violated "
                f"(o={bar['open']} h={hi} l={lo} c={bar['close']})",
            )
    return _ok("MD-I4")


def check_md_i5_degenerate(pack: dict[str, Any]) -> CheckOutcome:
    """MD-I5 — variance judged only against a declared instrument invariant."""
    absent = _missing(pack, "min_expected_variance", "variance_window")
    if absent:
        return _unknown("MD-I5", absent)
    window = pack["variance_window"]
    closes = [b["close"] for b in pack.get("bars") or []]
    if len(closes) < window:
        return _unknown("MD-I5", [f"fewer bars ({len(closes)}) than variance_window ({window})"])
    floor = pack["min_expected_variance"]
    for start in range(len(closes) - window + 1):
        var = statistics.pvariance(closes[start : start + window])
        if var < floor:
            return _fail(
                "MD-I5",
                f"variance {var} over window at index {start} is below the declared "
                f"min_expected_variance {floor}",
            )
    return _ok("MD-I5")


def check_md_i6_calendar(pack: dict[str, Any], calendars: dict[str, set]) -> CheckOutcome:
    """MD-I6 — bars judged only against a declared instrument/market calendar."""
    absent = _missing(pack, "calendar_id")
    if absent:
        return _unknown("MD-I6", absent)
    cal_id = pack["calendar_id"]
    if cal_id not in calendars:
        return _unknown("MD-I6", [f"calendar_id {cal_id!r} unknown to the registry"])
    sessions = calendars[cal_id]
    seen = set()
    for bar in pack.get("bars") or []:
        day = str(bar["ts"])[:10]
        if day not in sessions:
            return _fail("MD-I6", f"bar timestamped {bar['ts']} outside calendar {cal_id}")
        seen.add(day)
    declared_gaps = set(pack.get("declared_gaps") or [])
    for day in sorted(sessions):
        if day not in seen and day not in declared_gaps:
            return _fail("MD-I6", f"expected session {day} absent with no declared gap reason")
    return _ok("MD-I6")


def check_md_i7_duplicate_block(pack: dict[str, Any]) -> CheckOutcome:
    """MD-I7 — two disjoint equal runs of length >= duplicate_block_min_len."""
    absent = _missing(pack, "duplicate_block_min_len", "allows_repeated_bars")
    if absent:
        return _unknown("MD-I7", absent)
    if pack["allows_repeated_bars"]:
        return _ok("MD-I7", "repeated bars declared legitimate for this dataset")
    k = pack["duplicate_block_min_len"]
    bars = pack.get("bars") or []
    tuples = [tuple(b[f] for f in (*OHLC, "volume")) for b in bars]
    if k <= 0 or len(tuples) < 2 * k:
        return _ok("MD-I7", "series too short to contain two disjoint blocks")
    blocks: dict[tuple, int] = {}
    for i in range(len(tuples) - k + 1):
        key = tuple(tuples[i : i + k])
        prev = blocks.get(key)
        if prev is not None and i >= prev + k:  # disjoint
            return _fail(
                "MD-I7",
                f"duplicate block of {k} bars at indices {prev} and {i}",
            )
        blocks.setdefault(key, i)
    return _ok("MD-I7")


# --------------------------------------------------------------------------
# fabricated_pnl — PnL is derived, never trusted
# --------------------------------------------------------------------------


def _signed(fill: dict[str, Any], convention: str) -> float:
    qty = fill["qty"]
    if convention == "signed_long_positive":
        return float(qty)
    raise ValueError(f"unsupported quantity_convention: {convention}")


def check_pl_a1_recomputation(pack: dict[str, Any]) -> CheckOutcome:
    """PL-A1 — reported PnL against PnL recomputed from the fill ledger and marks."""
    absent = _missing(pack, "pnl_tolerance")
    if absent:
        return _unknown("PL-A1", absent)
    tol = pack["pnl_tolerance"]
    boundary = pack.get("accounting_boundary")
    if boundary is None:
        return _unknown("PL-A1", ["accounting_boundary"])
    realized = 0.0
    for fill in pack.get("fills") or []:
        realized -= float(fill["qty"]) * float(fill["price"])
        realized -= float(fill.get("fee") or 0.0)
        realized -= abs(float(fill.get("slippage") or 0.0))
    position = float(boundary["opening_position"]) + sum(
        float(f["qty"]) for f in pack.get("fills") or []
    )
    mark = pack.get("mark_price")
    if mark is None:
        return _unknown("PL-A1", ["mark_price"])
    recomputed = realized + position * float(mark) - float(boundary["opening_position"]) * float(
        boundary["opening_mark"]
    )
    reported = float(pack["reported_pnl"])
    delta = abs(reported - recomputed)
    limit = float(tol["absolute"]) + float(tol["relative"]) * abs(recomputed)
    if delta > limit:
        return _fail(
            "PL-A1",
            f"reported_pnl {reported} vs recomputed {recomputed:.6f}: "
            f"delta {delta:.6f} exceeds tolerance {limit:.6f}",
        )
    return _ok("PL-A1")


def check_pl_a2_fill_lineage(pack: dict[str, Any]) -> CheckOutcome:
    """PL-A2 — every fill references an order that passed the pre-trade gate."""
    gated = set(pack.get("gated_order_ids") or [])
    for fill in pack.get("fills") or []:
        if fill.get("order_id") not in gated:
            return _fail(
                "PL-A2", f"orphan fill: order_id {fill.get('order_id')!r} passed no gate"
            )
    return _ok("PL-A2")


def check_pl_a3_position_conservation(pack: dict[str, Any]) -> CheckOutcome:
    """PL-A3 — position_after == position_before + sum(signed fills)."""
    absent = _missing(pack, "quantity_convention", "accounting_boundary")
    if absent:
        return _unknown("PL-A3", absent)
    convention = pack["quantity_convention"]
    boundary = pack["accounting_boundary"]
    try:
        moved = sum(_signed(f, convention) for f in pack.get("fills") or [])
    except ValueError as exc:
        return _unknown("PL-A3", [str(exc)])
    expected = float(boundary["opening_position"]) + moved
    actual = float(pack["position_after"])
    if abs(expected - actual) > 1e-9:
        return _fail(
            "PL-A3",
            f"position_after {actual} != opening {boundary['opening_position']} "
            f"+ fills {moved} = {expected}",
        )
    return _ok("PL-A3")


def check_pl_m1_pnl_without_fills(pack: dict[str, Any]) -> CheckOutcome:
    """PL-M1 — realized PnL with no fills is impossible; unrealized may be carry-over."""
    absent = _missing(pack, "accounting_boundary")
    if absent:
        return _unknown("PL-M1", absent)
    if pack.get("fills"):
        return _ok("PL-M1", "run contains fills; boundary rule not engaged")
    boundary = pack["accounting_boundary"]
    if abs(float(pack.get("realized_pnl") or 0.0)) > 1e-9:
        return _fail("PL-M1", "realized PnL is non-zero with an empty fill ledger")
    unrealized = float(pack.get("unrealized_pnl") or 0.0)
    if abs(unrealized) <= 1e-9:
        return _ok("PL-M1")
    opening = float(boundary["opening_position"])
    if opening == 0.0:
        return _fail("PL-M1", "unrealized PnL changed with zero fills and zero opening position")
    mark = pack.get("mark_price")
    if mark is None:
        return _unknown("PL-M1", ["mark_price"])
    expected = opening * (float(mark) - float(boundary["opening_mark"]))
    if abs(expected - unrealized) > 1e-6:
        return _fail(
            "PL-M1",
            f"unrealized PnL {unrealized} does not reconcile with marks (expected {expected})",
        )
    return _ok("PL-M1", "carry-over unrealized PnL reconciles with marks")


def check_pl_m2_fees_and_slippage(pack: dict[str, Any]) -> CheckOutcome:
    """PL-M2 — the ledger against the declared execution model, not against zero."""
    absent = _missing(pack, "execution_model")
    if absent:
        return _unknown("PL-M2", absent)
    model = pack["execution_model"]
    charges_fees = bool(model.get("charges_fees"))
    charges_slippage = bool(model.get("charges_slippage"))
    for fill in pack.get("fills") or []:
        if charges_fees and abs(float(fill.get("fee") or 0.0)) <= 1e-12:
            return _fail(
                "PL-M2",
                f"execution model declares fees but fill {fill.get('order_id')!r} records none",
            )
        if charges_slippage and abs(float(fill.get("slippage") or 0.0)) <= 1e-12:
            return _fail(
                "PL-M2",
                f"execution model declares slippage but fill "
                f"{fill.get('order_id')!r} records none",
            )
    return _ok("PL-M2")


# --------------------------------------------------------------------------
# Suites — verdicts only; the caller resolves
# --------------------------------------------------------------------------


def detect_fabricated_market_data(
    pack: dict[str, Any],
    *,
    snapshot_root: Path,
    calendars: dict[str, set] | None = None,
) -> list[CheckOutcome]:
    cals = calendars or {}
    return [
        check_md_p1_provenance(pack),
        check_md_i1_digest(pack, snapshot_root),
        check_md_i2_snapshot_exists(pack, snapshot_root),
        check_md_i3_coverage(pack),
        check_md_i4_ohlc(pack),
        check_md_i5_degenerate(pack),
        check_md_i6_calendar(pack, cals),
        check_md_i7_duplicate_block(pack),
    ]


def detect_fabricated_pnl(pack: dict[str, Any]) -> list[CheckOutcome]:
    return [
        check_pl_a1_recomputation(pack),
        check_pl_a2_fill_lineage(pack),
        check_pl_a3_position_conservation(pack),
        check_pl_m1_pnl_without_fills(pack),
        check_pl_m2_fees_and_slippage(pack),
    ]


def worst(outcomes: Iterable[CheckOutcome]) -> Verdict:
    """FAIL dominates UNKNOWN dominates PASS. Both non-PASS states deny; only
    FAIL asserts a violation, so FAIL is reported when both are present."""
    seen = {o.verdict for o in outcomes}
    if Verdict.FAIL in seen:
        return Verdict.FAIL
    if Verdict.UNKNOWN in seen:
        return Verdict.UNKNOWN
    return Verdict.PASS if seen else Verdict.UNKNOWN
