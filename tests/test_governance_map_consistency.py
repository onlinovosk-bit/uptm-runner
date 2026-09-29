"""UPTM-018a - the map may not call the same question both decided and open.

`test_map_q3_is_decided_as_a_floor_and_copies_no_number` slices question 3's
block and asserts the decision is *in it*. It proves the decision was written.
It cannot prove the decision is not *also contradicted*, because a contradiction
lives outside the slice - and for three days one did: a paragraph above the
question list said `DEC-UPTM-MAP-Q3` "leaves that relation unadopted" while the
list said the same label was DECIDED.

That is a one-sided guard. These tests are the other side. They check the whole
document, per label, and they are shown to bite on the actual defect rather than
on a case invented to make them pass.

Criteria are the ones preregistered in
`docs/specs/UPTM-018a-map-q3-record-contradiction.md`; each test names its own.
"""

from __future__ import annotations

import json
import re

import pytest

from runner.paths import CAPITAL_RULES, CC_CONSTITUTION, ROOT

MAP = ROOT / "docs" / "architecture" / "governance-map.md"
DECISIONS = ROOT / "docs" / "decisions.md"

LABEL = re.compile(r"DEC-UPTM-MAP-Q\d+")
DECIDED = re.compile(r"\bDECIDED\b")
# Recorded from this map's own history (`OPEN (DEC-UPTM-MAP-Q3, ...)`,
# "stays open under", "leaves that relation unadopted", "is not decided here"),
# not derived. A novel phrasing would evade it; the record tests below are the
# second net. Stated in the spec as a known limit.
OPENNESS = re.compile(r"\bOPEN\b|unadopted|not adopted|not decided|stays? open|left open")

# The sentence as `5a6ecb0` (#38) wrote it, verbatim. It is the regression
# fixture: the guard is shown to catch the real defect, not a paraphrase of it.
LINE_112_AS_WRITTEN = (
    "**DEC-UPTM-MAP-Q3 leaves that relation unadopted.** Whether the tranche is a\n"
    "ceiling on the envelope, a subset of it, or an independent limit is not decided\n"
    "here. Neither number is rewritten into the other."
)


def _units(text: str) -> list[str]:
    """Paragraphs, with a numbered list split into its items.

    The unit is not the paragraph: the map's question list has no blank lines
    between items, so one paragraph holds questions 1-5 and would attribute
    question 1's DECIDED to question 3's label (G2).
    """
    units: list[str] = []
    for paragraph in re.split(r"\n\s*\n", text):
        for item in re.split(r"\n(?=\d+\. )", paragraph):
            units.append(" ".join(item.split()))
    return units


def _states_by_label(text: str) -> dict[str, dict[str, list[str]]]:
    """label -> {"DECIDED" | "OPEN" -> the units that assert it}."""
    found: dict[str, dict[str, list[str]]] = {}
    for unit in _units(text):
        labels = set(LABEL.findall(unit))
        if not labels:
            continue
        states = []
        if DECIDED.search(unit):
            states.append("DECIDED")
        if OPENNESS.search(unit):
            states.append("OPEN")
        for label in labels:
            slot = found.setdefault(label, {})
            for state in states:
                slot.setdefault(state, []).append(unit)
    return found


def _conflicts(text: str) -> dict[str, dict[str, list[str]]]:
    return {
        label: states
        for label, states in _states_by_label(text).items()
        if {"DECIDED", "OPEN"} <= states.keys()
    }


def _describe(conflicts: dict[str, dict[str, list[str]]]) -> str:
    lines = []
    for label, states in sorted(conflicts.items()):
        lines.append(f"{label} is asserted both DECIDED and OPEN:")
        for state, units in sorted(states.items()):
            for unit in units:
                lines.append(f"  [{state}] {unit[:140]}")
    lines.append(
        "The map is a current-state document: say what the label decided and put "
        "the history of the earlier state in docs/decisions.md."
    )
    return "\n".join(lines)


# --------------------------------------------------------------------------
# G1, G6 - THE REAL MAP
# --------------------------------------------------------------------------


def test_g1_no_label_in_the_map_is_asserted_both_decided_and_open():
    conflicts = _conflicts(MAP.read_text(encoding="utf-8"))
    assert not conflicts, _describe(conflicts)


def test_g6_the_scan_sees_every_labelled_question_so_it_cannot_pass_vacuously():
    """The labels found equal the labels the decisions log gives headings to.

    Without this a scan that matched nothing would report zero conflicts and
    look identical to a map with none. Question 4 carries no MAP label (it is
    recorded in its own form) and is absent from both sides - a limit the
    guard says out loud rather than hides.
    """
    log = DECISIONS.read_text(encoding="utf-8")
    logged = set(re.findall(r"^## \[[^\]]+\] (DEC-UPTM-MAP-Q\d+)\b", log, re.MULTILINE))
    seen = _states_by_label(MAP.read_text(encoding="utf-8"))
    assert logged, "no DEC-UPTM-MAP-Q headings found in the decisions log"
    assert set(seen) == logged, (
        f"the map and the decisions log disagree on which questions carry a label: "
        f"map={sorted(seen)}, log={sorted(logged)}"
    )
    for label in logged:
        assert seen[label], f"{label} is named in the map but asserts no state at all"


# --------------------------------------------------------------------------
# G2-G5 - THE CLASSIFIER, ON TEXT WE CONTROL
# --------------------------------------------------------------------------


def test_g3_it_bites_on_the_actual_defect_and_names_the_label():
    """The verbatim line-112 sentence beside a DECIDED line for the same label."""
    text = (
        "### The two capital numbers\n\n"
        f"{LINE_112_AS_WRITTEN}\n\n"
        "3. **How do the two relate?**\n"
        "   **DECIDED (DEC-UPTM-MAP-Q3, 2026-09-29): THE ACCOUNT IS A FLOOR.**\n"
    )
    conflicts = _conflicts(text)
    assert set(conflicts) == {"DEC-UPTM-MAP-Q3"}
    assert set(conflicts["DEC-UPTM-MAP-Q3"]) == {"DECIDED", "OPEN"}
    assert "unadopted" in _describe(conflicts)


def test_g2_the_unit_is_the_list_item_not_the_paragraph():
    """A list with no blank lines is one paragraph. Q1 decided next to Q2 open passes."""
    text = (
        "1. **First?** **DECIDED (DEC-UPTM-MAP-Q1, 2026-09-28): YES.**\n"
        "2. **Second?** **OPEN (DEC-UPTM-MAP-Q2, 2026-09-25):** nobody has chosen.\n"
    )
    assert len(_units(text)) == 2
    assert _conflicts(text) == {}
    # ...and the same list with question 2 asserting both is a conflict.
    both = text + "   **DECIDED (DEC-UPTM-MAP-Q2, 2026-09-28): NEITHER WINS.**\n"
    assert set(_conflicts(both)) == {"DEC-UPTM-MAP-Q2"}


def test_g4_the_rule_is_consistency_not_decidedness():
    """An open question must pass, or the guard would forbid ever reopening one."""
    only_open = "**OPEN (DEC-UPTM-MAP-Q7, 2026-10-01):** neither answer is adopted.\n"
    assert _conflicts(only_open) == {}
    assert set(_states_by_label(only_open)["DEC-UPTM-MAP-Q7"]) == {"OPEN"}


def test_g4_a_label_mentioned_without_a_state_word_is_neutral():
    pointer = "Question 3 below carries the decision (DEC-UPTM-MAP-Q3).\n"
    assert _conflicts(pointer) == {}
    assert _states_by_label(pointer)["DEC-UPTM-MAP-Q3"] == {}


def test_g5_a_decided_label_and_an_open_label_do_not_contaminate_each_other():
    text = (
        "**DECIDED (DEC-UPTM-MAP-Q1, 2026-09-28): YES.**\n\n"
        "**OPEN (DEC-UPTM-MAP-Q9, 2026-10-01):** not adopted.\n"
    )
    assert _conflicts(text) == {}


@pytest.mark.parametrize(
    "phrase",
    [
        "OPEN (DEC-UPTM-MAP-Q3, 2026-09-25)",
        "the relation is unadopted",
        "the relation is not adopted",
        "which is not decided here",
        "the question stays open",
        "the question was left open",
    ],
)
def test_g1_every_recorded_way_of_saying_open_is_recognised(phrase):
    text = f"DEC-UPTM-MAP-Q3: {phrase}.\n\n**DECIDED (DEC-UPTM-MAP-Q3, 2026-09-29): FLOOR.**\n"
    assert set(_conflicts(text)) == {"DEC-UPTM-MAP-Q3"}, phrase


# --------------------------------------------------------------------------
# R1-R4 - THE RECORD ITSELF
# --------------------------------------------------------------------------


def _numbers_section() -> str:
    text = MAP.read_text(encoding="utf-8")
    start = text.index("### The two capital numbers are not the same number")
    end = text.index("\n## ", start)
    return " ".join(text[start:end].split())


def test_r1_the_numbers_paragraph_states_the_relation_that_was_adopted():
    section = _numbers_section()
    assert "DEC-UPTM-MAP-Q3" in section
    assert "floor" in section.lower()
    assert "VC-I6" in section


def test_r2_the_numbers_paragraph_carries_no_openness_wording():
    section = _numbers_section()
    assert not OPENNESS.search(section), OPENNESS.search(section).group(0)


def test_r3_the_comparison_is_the_packs_own_figure_not_the_other_repositorys():
    section = _numbers_section()
    assert "capital.account_equity" in section
    assert "declares" in section
    assert "never measured" in section
    assert "nothing here commands the other repository" in section


def test_r4_nothing_was_copied_across_and_the_constitution_did_not_move():
    """Also asserted, on their own, by the older Q3 test - restated so this
    criterion is discharged here without depending on that test staying put."""
    rules = json.loads(CAPITAL_RULES.read_text(encoding="utf-8"))
    assert rules["validation_capital"]["amount"] == 700
    assert "750" not in json.dumps(rules)
    constitution = CC_CONSTITUTION.read_text(encoding="utf-8")
    assert "v1.0" in constitution.splitlines()[0]
    assert "| Status | **LOCKED** |" in constitution


def test_g7_the_one_sided_guard_is_still_there():
    """It answers "is the decision present". This file answers "is it also
    contradicted". Neither replaces the other."""
    source = (ROOT / "tests" / "test_governance.py").read_text(encoding="utf-8")
    assert "def test_map_q3_is_decided_as_a_floor_and_copies_no_number" in source
