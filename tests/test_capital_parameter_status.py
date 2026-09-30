"""UPTM-018 - the note about the tranche parameters may not contradict the parameters.

`constitution/capital-rules.json` carried a note saying `validation_capital.amount`,
`.currency` and `.applies_to` were "unset. Every capital gate denies until all
three are set." They were set on 2026-09-23 (DEC-UPTM-004). The note was true when
written and stopped being true the day the Founder set them; nothing noticed, and
a handover later believed the 700 EUR tranche was still open because of it.

The suite was green with the stale sentence in place (measured: 851 passed), so
no existing test looked at it. The fix here is not to remember to edit prose. It
is to make the note's status word **equal the state of the data it describes**,
derived from the data, and to fail in both directions: a note that says
`SATISFIED` while a parameter is unset is as wrong as one that says `REQUIRED`
while all three are set.

Criteria are the ones preregistered in
`docs/specs/UPTM-018-account-equity-stays-in-the-pack.md`; each test names its own.
"""

from __future__ import annotations

import json
import re
from typing import Any

import pytest

from runner.detectors.validation_capital import check_vc_i6_account_covers_the_ceiling
from runner.paths import CAPITAL_RULES, CC_CONSTITUTION, ROOT
from runner.verdict import Verdict

NOTE_KEY = "founder_parameter_required"
PARAMS = ("amount", "currency", "applies_to")
STATUS = re.compile(r"^(SATISFIED|REQUIRED)\b")

# The sentence as it stood, verbatim. It is the regression fixture: the guard is
# shown to catch the real defect, not a paraphrase of it.
OLD_NOTE = (
    "validation_capital.amount, .currency and .applies_to are unset. "
    "Every capital gate denies until all three are set."
)


def _rules() -> dict[str, Any]:
    return json.loads(CAPITAL_RULES.read_text(encoding="utf-8"))


def _is_set(value: Any) -> bool:
    return value is not None and value != "" and value != [] and value != {}


def expected_status(validation_capital: dict[str, Any]) -> str:
    """Derived from the three parameters, never typed."""
    return "SATISFIED" if all(_is_set(validation_capital.get(k)) for k in PARAMS) else "REQUIRED"


def note_problems(note: str, validation_capital: dict[str, Any]) -> list[str]:
    expected = expected_status(validation_capital)
    match = STATUS.match(note.strip())
    if match is None:
        return [f"the note states no status; the parameters say {expected}"]
    if match.group(1) != expected:
        return [f"the note says {match.group(1)}; the parameters say {expected}"]
    return []


def _notes(tree: Any) -> list[str]:
    """Every note found by walking the file, not by naming where it lives (G5)."""
    found: list[str] = []
    if isinstance(tree, dict):
        for key, value in tree.items():
            if key == NOTE_KEY and isinstance(value, str):
                found.append(value)
            found.extend(_notes(value))
    elif isinstance(tree, list):
        for item in tree:
            found.extend(_notes(item))
    return found


def _keys(tree: Any) -> set[str]:
    keys: set[str] = set()
    if isinstance(tree, dict):
        for key, value in tree.items():
            keys.add(key)
            keys |= _keys(value)
    elif isinstance(tree, list):
        for item in tree:
            keys |= _keys(item)
    return keys


FULL = {"amount": 700, "currency": "EUR", "applies_to": ["cumulative_realised_loss"]}


# --------------------------------------------------------------------------
# G1, G5 - THE REAL FILE
# --------------------------------------------------------------------------


def test_g1_the_note_in_the_real_file_agrees_with_the_real_parameters():
    rules = _rules()
    for note in _notes(rules):
        assert note_problems(note, rules["validation_capital"]) == [], note[:120]


def test_g5_the_scan_finds_the_note_by_walking_so_it_cannot_pass_vacuously():
    assert _notes(_rules()), f"no `{NOTE_KEY}` found anywhere in capital-rules.json"


# --------------------------------------------------------------------------
# G2, G3, G4 - THE GUARD, ON DATA WE CONTROL
# --------------------------------------------------------------------------


def test_g2_all_three_set_and_a_note_claiming_required_fails():
    assert note_problems("REQUIRED: still to be set.", FULL) != []


@pytest.mark.parametrize("param", PARAMS)
@pytest.mark.parametrize("empty", [None, "", [], {}])
def test_g2_any_one_unset_and_a_note_claiming_satisfied_fails(param, empty):
    """Each of the three, and each way of being empty, tried separately.

    A guard that only watched `amount` would pass the first test above and
    quietly ignore the other two parameters.
    """
    unset = {**FULL, param: empty}
    assert expected_status(unset) == "REQUIRED"
    assert note_problems("SATISFIED 2026-09-23.", unset) != []
    assert note_problems("REQUIRED: still to be set.", unset) == []


def test_g2_a_consistent_note_passes_in_both_states():
    assert note_problems("SATISFIED 2026-09-23.", FULL) == []
    assert note_problems("REQUIRED.", {"amount": 700}) == []


def test_g3_a_note_with_no_status_word_fails():
    """Silence is not agreement: prose that never says which state it is in."""
    for note in ("", "all fine here", "see DEC-UPTM-004", "  ", "satisfied (lower case)"):
        problems = note_problems(note, FULL)
        assert problems and "no status" in problems[0], note


def test_g4_it_bites_on_the_actual_defect():
    """The verbatim old sentence, against the real - set - parameters."""
    problems = note_problems(OLD_NOTE, _rules()["validation_capital"])
    assert problems, "the sentence that was wrong for a week is accepted"
    assert "no status" in problems[0]


# --------------------------------------------------------------------------
# A1-A4 - THE RECORD
# --------------------------------------------------------------------------


def _the_note() -> str:
    notes = _notes(_rules())
    assert len(notes) == 1, notes
    return " ".join(notes[0].split())


def test_a1_the_note_is_dated_and_names_the_decision_that_satisfied_it():
    note = _the_note()
    assert note.startswith("SATISFIED")
    assert "2026-09-23" in note and "DEC-UPTM-004" in note


def test_a2_the_note_names_the_one_figure_still_supplied_from_outside():
    note = _the_note()
    assert "capital.account_equity" in note
    assert "each pack declares it" in note
    assert "UNKNOWN" in note
    assert "DEC-UPTM-018" in note


def test_a3_nothing_was_added_to_the_constitution():
    rules = _rules()
    assert "account_equity" not in _keys(rules), "account_equity became a constitution field"
    assert rules["validation_capital"]["amount"] == 700
    assert "750" not in json.dumps(rules)
    constitution = CC_CONSTITUTION.read_text(encoding="utf-8")
    assert "v1.0" in constitution.splitlines()[0]
    assert "| Status | **LOCKED** |" in constitution


def test_a4_the_decision_is_recorded_newest_first_and_names_the_option_not_taken():
    log = (ROOT / "docs" / "decisions.md").read_text(encoding="utf-8")
    first = log.index("## [2026-09-30] DEC-UPTM-018")
    assert first < log.index("## [2026-09-29] DEC-UPTM-017"), "not newest first"
    block = " ".join(log[first : log.index("\n---\n", first)].split())
    assert "constitution-level account figure" in block
    assert "MAP-Q2" in block


# --------------------------------------------------------------------------
# G6 - WHAT THE GATE DOES ON THE REAL CONFIGURATION
# --------------------------------------------------------------------------


def _vc6(equity: Any):
    tranche = _rules()["validation_capital"]
    pack = {} if equity is None else {"account_equity": equity}
    return check_vc_i6_account_covers_the_ceiling(pack, tranche)


def test_g6_an_undeclared_account_ends_unknown_and_names_the_key():
    outcome = _vc6(None)
    assert outcome.verdict is Verdict.UNKNOWN
    assert "capital.account_equity" in outcome.detail


def test_g6_an_account_below_the_tranche_fails():
    amount = _rules()["validation_capital"]["amount"]
    assert _vc6(amount - 1).verdict is Verdict.FAIL


def test_g6_an_account_at_or_above_the_tranche_passes():
    amount = _rules()["validation_capital"]["amount"]
    assert _vc6(amount).verdict is Verdict.PASS
    assert _vc6(amount * 2).verdict is Verdict.PASS
