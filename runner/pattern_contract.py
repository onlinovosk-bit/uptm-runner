"""UPTM-011: the ladder a research pattern climbs, and what each rung costs.

A pattern candidate spends most of its life in a state one word cannot express:
the rules are pinned down, and nothing whatever is known about whether it earns.
A flat ``status: UNVERIFIED`` collapses that, and a flat ``VERIFIED`` is worse -
it lets "we checked the rules" drift into "we checked the money".

So six axes, ordered, each with its own lowest rung. An axis may rise above its
lowest rung only when every earlier axis stands at its top. The spec is
``docs/specs/UPTM-011-bearish-quasimodo-contract.md``.

The ordering is not decoration:

- ``rules`` waits on ``source`` because mechanical rules attributed to an author
  whose text nobody read are not that author's rules. They are ours, with their
  name on them.
- ``performance`` waits on ``no_leakage`` because a return measured with
  information the strategy could not have had at decision time is not a return.

Nothing here reads market data, runs a detector, or trades.
"""

from __future__ import annotations

from typing import Any

UNDEFINED = "UNDEFINED"

# The root every swing term rests on. A structure that names swings at all needs
# this defined; which structures those are is read out of the data, below.
SWING_DEFINITION = "swing_definition"

# Ordered. Earlier axes gate later ones.
AXES: tuple[str, ...] = (
    "source",
    "rules",
    "implementation",
    "no_leakage",
    "stats",
    "performance",
)

RUNGS: dict[str, tuple[str, ...]] = {
    "source": ("RESTATED_SECONDHAND", "PRIMARY_SOURCE_READ", "VERIFIED_SOURCE"),
    "rules": (UNDEFINED, "PARTIALLY_DEFINED", "MECHANICAL"),
    "implementation": ("NOT_STARTED", "IN_PROGRESS", "IMPLEMENTED_AND_TESTED"),
    "no_leakage": ("NOT_TESTED", "TESTED_NO_FUTURE_INFORMATION"),
    "stats": ("NOT_TESTED", "TESTED_OUT_OF_SAMPLE"),
    "performance": ("UNVERIFIED", "MEASURED_AFTER_COSTS"),
}


def lowest(axis: str) -> str:
    return RUNGS[axis][0]


def top(axis: str) -> str:
    return RUNGS[axis][-1]


def swing_terms_used(contract: dict[str, Any]) -> list[str]:
    """Every swing term the structure actually references, read out of the data.

    Derived, never typed. The sequence is the authority on which terms a pattern
    depends on; a hand-kept list beside it would rot the first time a step
    changed, exactly as a hand-kept dependency set or a typed ENFORCED does.
    """
    structure = contract.get("structure")
    if not isinstance(structure, dict):
        return []
    sequence = structure.get("sequence")
    if not isinstance(sequence, list):
        return []
    seen: list[str] = []
    for step in sequence:
        if isinstance(step, dict):
            term = step.get("swing")
            if isinstance(term, str) and term not in seen:
                seen.append(term)
    return seen


def required_terms(contract: dict[str, Any]) -> list[str]:
    """The terms this contract cannot be evaluated without, derived from it.

    A structure that names any swing at all rests on ``swing_definition``: HH and
    LH are not levels, they are verdicts about bars either side, and nobody can
    locate one until how many bars, and what amplitude, are fixed. So the root
    term is required whenever the sequence names a swing, and is not required of
    a contract whose structure names none.

    This is the rule rather than a list of term names for the same reason the
    swing terms themselves are read out of the sequence: a list kept beside the
    data is correct exactly until the data changes.
    """
    used = swing_terms_used(contract)
    if not used:
        return []
    return [SWING_DEFINITION, *used]


def undefined_terms(contract: dict[str, Any]) -> list[str]:
    """Terms the contract needs but does not define, plus any it marks UNDEFINED.

    A required term the glossary omits counts as undefined. Absent is not the
    same as defined, and silence must not read as agreement - otherwise the way
    past this gate is to delete the key.
    """
    terms = contract.get("terms")
    terms = terms if isinstance(terms, dict) else {}
    missing = [
        name
        for name in required_terms(contract)
        if terms.get(name, UNDEFINED) == UNDEFINED
    ]
    for name, value in terms.items():
        if value == UNDEFINED and name not in missing:
            missing.append(name)
    return missing


def ladder_errors(contract: dict[str, Any]) -> list[str]:
    """Every way this contract claims more than it has earned."""
    errors: list[str] = []

    if contract.get("live_trading") is not False:
        errors.append("live_trading must be false")

    status = contract.get("status")
    if not isinstance(status, dict):
        return errors + ["status must be an object carrying every axis"]

    for axis in AXES:
        if axis not in status:
            errors.append(f"status is missing the {axis} axis")
        elif status[axis] not in RUNGS[axis]:
            errors.append(
                f"status.{axis} is {status[axis]!r}, which is not a rung of "
                f"{axis}: {list(RUNGS[axis])}"
            )
    if errors:
        return errors

    # An axis above its lowest rung requires every earlier axis at its top.
    for index, axis in enumerate(AXES):
        if status[axis] == lowest(axis):
            continue
        for earlier in AXES[:index]:
            if status[earlier] != top(earlier):
                errors.append(
                    f"status.{axis} is {status[axis]!r} while status.{earlier} "
                    f"is {status[earlier]!r}, below {top(earlier)!r}"
                )

    # Rules cannot be defined while a term the structure uses is not.
    still_undefined = undefined_terms(contract)
    if still_undefined and status["rules"] != UNDEFINED:
        errors.append(
            f"status.rules is {status['rules']!r} while these terms are "
            f"undefined: {still_undefined}"
        )

    return errors
