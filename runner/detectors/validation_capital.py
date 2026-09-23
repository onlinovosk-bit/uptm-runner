"""Detectors for `validation_capital_exceeded` and `return_used_as_gate_criterion`.

Implements the criteria preregistered in
docs/specs/UPTM-004-validation-capital-cap.md, written before this module
existed (CC/P4).

What these detectors claim
--------------------------
That the exposure a run *declares* stays within a declared tranche, that the
cumulative realised loss does too, and that no gate is judged by return.

What they do not claim
----------------------
That the exposure declared is the exposure that existed. A run which
under-declares what it risked is a fabrication problem and belongs to UPTM-002.
This module binds declarations; UPTM-002 binds declarations to reality. Neither
substitutes for the other.

Verdicts only
-------------
Every check returns a Verdict, never a Decision.
"""

from __future__ import annotations

import re
from typing import Any, Iterable

from runner.detectors.fabrication import CheckOutcome, _fail, _ok, _unknown
from runner.verdict import Verdict

#: What a tranche may be bound to. "€700" means three different ceilings
#: depending on which of these it binds, so the choice is the Founder's and is
#: never inferred here.
APPLIES_TO = (
    "per_position_at_risk",
    "aggregate_open_exposure",
    "cumulative_realised_loss",
)

#: Metrics that are return by another name. Kept deliberately short: matching a
#: substring of any criterion's name would fail a criterion called
#: "pnl_pack_declared", which is a requirement to *report*, not to profit.
RETURN_TERMS = frozenset(
    {
        "return",
        "realised_return",
        "realized_return",
        "roi",
        "pnl",
        "profit",
        "net_profit",
        "yield",
        "gain",
    }
)

_STRING_CRITERION = re.compile(
    r"\b(?P<metric>[a-z_ ]*?(?:return|roi|pnl|profit|yield|gain))\b\s*"
    r"(?P<op>>=|<=|>|<|==|=|at least|above|over)\s*"
    r"(?P<value>-?\d+(?:\.\d+)?)",
    re.IGNORECASE,
)


def _normalise(name: Any) -> str:
    return str(name).strip().lower().replace(" ", "_").replace("-", "_")


def _is_return_metric(name: Any) -> bool:
    n = _normalise(name)
    return n in RETURN_TERMS or any(n.endswith("_" + t) for t in RETURN_TERMS)


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


# --------------------------------------------------------------------------
# validation_capital_exceeded
# --------------------------------------------------------------------------


def check_vc_p1_tranche_declared(tranche: dict[str, Any]) -> CheckOutcome:
    """The tranche is a Founder parameter. Unset denies; it never defaults."""
    absent = []
    if _number(tranche.get("amount")) is None:
        absent.append("validation_capital.amount")
    if not tranche.get("currency"):
        absent.append("validation_capital.currency")
    applies = tranche.get("applies_to") or []
    if not applies:
        absent.append("validation_capital.applies_to")
    if absent:
        return _unknown("VC-P1", absent)
    unknown = [a for a in applies if a not in APPLIES_TO]
    if unknown:
        return _unknown("VC-P1", [f"applies_to entries outside {APPLIES_TO}: {unknown}"])
    return _ok(
        "VC-P1",
        f"tranche {tranche['amount']} {tranche['currency']} binding {', '.join(applies)}",
    )


def check_vc_p2_gate_declares_itself(evidence: dict[str, Any]) -> CheckOutcome:
    """Carrying capital without saying this is a capital gate is not evaluable."""
    if evidence.get("capital_gate") is None:
        return _unknown(
            "VC-P2",
            ["capital_gate — evidence carries a capital pack but does not declare the gate"],
        )
    return _ok("VC-P2", f"capital_gate={evidence['capital_gate']}")


def check_vc_i1_pack_present(evidence: dict[str, Any], pack: dict[str, Any]) -> CheckOutcome:
    """Closes UPTM-002's recorded omission_bypass for capital gates.

    A gate that says it puts capital at risk and then declares none is not
    silent agreement; it is a gap, and a gap denies.

    The pack is the one the caller resolved, not a second read of the evidence:
    one source of truth, so the check cannot disagree with what was evaluated.
    """
    if evidence.get("capital_gate") is True and not pack:
        return _unknown(
            "VC-I1",
            ["a capital pack — the gate declares capital_gate=true and carries none"],
        )
    return _ok("VC-I1", "capital declaration present for this gate")


def check_vc_i2_at_risk_within_tranche(
    pack: dict[str, Any], tranche: dict[str, Any]
) -> CheckOutcome:
    applies = tranche.get("applies_to") or []
    bound = [a for a in applies if a in ("per_position_at_risk", "aggregate_open_exposure")]
    if not bound:
        return _ok("VC-I2", "tranche does not bind exposure; VC-I3 carries the ceiling")
    amount = _number(tranche.get("amount"))
    at_risk = _number(pack.get("at_risk"))
    if amount is None:
        return _unknown("VC-I2", ["validation_capital.amount"])
    if at_risk is None:
        return _unknown("VC-I2", ["capital.at_risk as a number"])
    if at_risk > amount:
        return _fail(
            "VC-I2",
            f"capital at risk {at_risk} exceeds the validation tranche {amount} "
            f"({', '.join(bound)})",
        )
    return _ok("VC-I2", f"at risk {at_risk} within {amount}")


def check_vc_i3_cumulative_loss_within_tranche(
    pack: dict[str, Any], tranche: dict[str, Any]
) -> CheckOutcome:
    """A per-action limit that does not sum is not a ceiling.

    Twenty positions of 50, each under the cap, lose the tranche and more. This
    is the failure mode P10 was written against.
    """
    applies = tranche.get("applies_to") or []
    if "cumulative_realised_loss" not in applies:
        return _ok("VC-I3", "tranche does not bind cumulative realised loss")
    amount = _number(tranche.get("amount"))
    loss = _number(pack.get("cumulative_realised_loss"))
    if amount is None:
        return _unknown("VC-I3", ["validation_capital.amount"])
    if loss is None:
        return _unknown("VC-I3", ["capital.cumulative_realised_loss as a number"])
    if loss > amount:
        return _fail(
            "VC-I3",
            f"cumulative realised loss {loss} exceeds the validation tranche {amount} — "
            "each action was within the cap and the tranche is gone anyway",
        )
    return _ok("VC-I3", f"cumulative realised loss {loss} within {amount}")


def check_vc_i4_currency_matches(pack: dict[str, Any], tranche: dict[str, Any]) -> CheckOutcome:
    """Never convert. An invented rate is a sourceless number in the one
    calculation that decides whether the money is protected."""
    declared, ceiling = pack.get("currency"), tranche.get("currency")
    if not declared or not ceiling:
        return _unknown("VC-I4", ["capital.currency and validation_capital.currency"])
    if str(declared).upper() != str(ceiling).upper():
        return _unknown(
            "VC-I4",
            [f"a comparable currency: capital is {declared}, the tranche is {ceiling}"],
        )
    return _ok("VC-I4", f"both in {ceiling}")


# --------------------------------------------------------------------------
# return_used_as_gate_criterion
# --------------------------------------------------------------------------


def _offending_criteria(criteria: Iterable[Any]) -> list[str]:
    offenders: list[str] = []
    for c in criteria or []:
        if isinstance(c, dict):
            metric = c.get("metric") or c.get("name") or c.get("id")
            has_comparison = c.get("op") is not None and c.get("value") is not None
            if metric is not None and _is_return_metric(metric) and has_comparison:
                offenders.append(f"{metric} {c.get('op')} {c.get('value')}")
        elif isinstance(c, str):
            m = _STRING_CRITERION.search(c)
            if m and _is_return_metric(m.group("metric")):
                offenders.append(c.strip())
    return offenders


def check_vc_r1_no_return_in_exit_criteria(criteria: Iterable[Any]) -> CheckOutcome:
    offenders = _offending_criteria(criteria)
    if offenders:
        return _fail(
            "VC-R1",
            "a gate criterion is keyed on return: "
            + "; ".join(offenders)
            + " — return is not a criterion of any gate",
        )
    return _ok("VC-R1", "no exit criterion is keyed on return")


def check_vc_r2_pass_not_justified_by_profit(claim: dict[str, Any]) -> CheckOutcome:
    if claim.get("verdict") != "PASS":
        return _ok("VC-R2", "no PASS claimed")
    basis = claim.get("basis") or []
    offenders = [b for b in basis if _is_return_metric(b)]
    if offenders:
        return _fail(
            "VC-R2",
            f"the PASS claim rests on {', '.join(map(str, offenders))} — "
            "a gate is judged by its preregistered robustness criteria, not by what it earned",
        )
    return _ok("VC-R2", "PASS claim does not rest on return")


def check_vc_r3_reporting_pnl_is_permitted(
    pack: dict[str, Any], criteria: Iterable[Any], claim: dict[str, Any]
) -> CheckOutcome:
    """Explicit false-positive protection.

    P10 forbids *judging* by return, not *measuring* it. A detector that made a
    reported loss a failure would push the system toward not measuring, which is
    the opposite of what the constitution wants and would collide with UPTM-002,
    which requires PnL to be declared so it can be checked.
    """
    reported = pack.get("realised_pnl")
    if reported is None:
        return _ok("VC-R3", "no PnL reported")
    if _offending_criteria(criteria) or [b for b in (claim.get("basis") or []) if _is_return_metric(b)]:
        return _ok("VC-R3", "PnL is reported and also judged — VC-R1/VC-R2 carry that")
    return _ok("VC-R3", f"PnL reported ({reported}) and referenced by no criterion — permitted")


# --------------------------------------------------------------------------


def detect_validation_capital(
    evidence: dict[str, Any], pack: dict[str, Any], tranche: dict[str, Any]
) -> list[CheckOutcome]:
    return [
        check_vc_p1_tranche_declared(tranche),
        check_vc_p2_gate_declares_itself(evidence),
        check_vc_i1_pack_present(evidence, pack),
        check_vc_i2_at_risk_within_tranche(pack, tranche),
        check_vc_i3_cumulative_loss_within_tranche(pack, tranche),
        check_vc_i4_currency_matches(pack, tranche),
    ]


def detect_return_as_criterion(
    criteria: Iterable[Any], claim: dict[str, Any], pack: dict[str, Any]
) -> list[CheckOutcome]:
    return [
        check_vc_r1_no_return_in_exit_criteria(criteria),
        check_vc_r2_pass_not_justified_by_profit(claim),
        check_vc_r3_reporting_pnl_is_permitted(pack, criteria, claim),
    ]
