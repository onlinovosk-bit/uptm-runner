"""UPTM-016: a wave reference that leaves its repository must carry it.

Criteria are preregistered in `docs/specs/UPTM-016-close-map-q5.md`, written
before this file existed. Each test names the criterion it discharges.

Nothing here renumbers anything. Closing MAP-Q5 had to be possible *without*
rewriting eight artifacts to fix a problem in how they are quoted, and N1 and L2
are the tests that say it was.
"""

from __future__ import annotations

import json

import pytest
import yaml

from runner.paths import ROOT
from runner.wave_names import (
    CONTROL_PLANE,
    THEIR_WAVES,
    THEIR_WAVES_SOURCE,
    TRADING_SYSTEM,
    ambiguous_numbers,
    artifact_disagreements,
    index_disagreements,
    is_ambiguous,
    our_waves,
    parse,
    qualify,
    unambiguous_to,
)

WAVES = ROOT / "waves"
MAP = ROOT / "docs" / "architecture" / "governance-map.md"

# The numbering this repository has had since before MAP-Q5 was asked.
EXPECTED = {0, 1, 2, 3, 4, 5, 6, 7}


# --------------------------------------------------------------------------
# N1 / L2 - nothing is renumbered
# --------------------------------------------------------------------------


def test_n1_every_wave_keeps_the_number_it_had():
    assert our_waves() == EXPECTED
    for number in sorted(EXPECTED):
        document = yaml.safe_load((WAVES / f"wave{number}.yaml").read_text(encoding="utf-8"))
        assert document["wave_id"] == number


def test_l2_no_wave_was_added_or_removed():
    files = sorted(path.name for path in WAVES.glob("wave*.yaml"))
    assert files == [f"wave{n}.yaml" for n in sorted(EXPECTED)]


def test_n1_wave7_is_still_the_one_the_map_names():
    """The collision's own example: this repository's 7 is exit_and_archive."""
    document = yaml.safe_load((WAVES / "wave7.yaml").read_text(encoding="utf-8"))
    assert document["name"] == "exit_and_archive"


# --------------------------------------------------------------------------
# N2 - qualified at source
# --------------------------------------------------------------------------


def test_n2_every_wave_artifact_declares_its_repository_consistently():
    assert artifact_disagreements() == []


def test_n2_a_single_lifted_field_is_already_qualified():
    """The failure this closes: someone quotes one field into a status line."""
    document = yaml.safe_load((WAVES / "wave7.yaml").read_text(encoding="utf-8"))
    assert document["qualified_id"] == "uptm-runner:W7"
    assert is_ambiguous(document["qualified_id"]) is False


def test_n2_a_wave_file_that_drops_its_repository_is_a_finding(tmp_path):
    waves = tmp_path / "waves"
    waves.mkdir()
    (waves / "wave3.yaml").write_text("wave_id: 3\nqualified_id: uptm-runner:W3\n", encoding="utf-8")
    findings = artifact_disagreements(tmp_path)
    assert len(findings) == 1
    assert "does not declare repository" in findings[0]


def test_n2_a_qualified_id_that_disagrees_with_the_file_is_a_finding(tmp_path):
    waves = tmp_path / "waves"
    waves.mkdir()
    (waves / "wave3.yaml").write_text(
        "wave_id: 3\nrepository: uptm-runner\nqualified_id: uptm-runner:W4\n", encoding="utf-8"
    )
    findings = artifact_disagreements(tmp_path)
    assert len(findings) == 1
    assert "not 'uptm-runner:W3'" in findings[0]


# --------------------------------------------------------------------------
# N3 - the index agrees with the disk, both directions
# --------------------------------------------------------------------------


def test_n3_the_index_matches_the_files_on_disk():
    assert index_disagreements() == []
    index = json.loads((WAVES / "index.json").read_text(encoding="utf-8"))
    assert index["repository"] == CONTROL_PLANE
    assert index["qualified"] == [f"uptm-runner:W{n}" for n in sorted(EXPECTED)]


def _index(path, waves):
    (path / "waves").mkdir(exist_ok=True)
    (path / "waves" / "index.json").write_text(
        json.dumps({"repository": CONTROL_PLANE, "waves": waves}), encoding="utf-8"
    )


def test_n3_a_wave_missing_from_the_index_is_a_finding(tmp_path):
    _index(tmp_path, [0])
    (tmp_path / "waves" / "wave0.yaml").write_text("wave_id: 0\n", encoding="utf-8")
    (tmp_path / "waves" / "wave1.yaml").write_text("wave_id: 1\n", encoding="utf-8")
    findings = index_disagreements(tmp_path)
    assert len(findings) == 1
    assert "does not list it" in findings[0]


def test_n3_an_index_entry_with_no_file_is_a_finding(tmp_path):
    """How a deleted wave keeps appearing in status lines."""
    _index(tmp_path, [0, 1])
    (tmp_path / "waves" / "wave0.yaml").write_text("wave_id: 0\n", encoding="utf-8")
    findings = index_disagreements(tmp_path)
    assert len(findings) == 1
    assert "does not exist" in findings[0]


# --------------------------------------------------------------------------
# N4 - the ambiguous set is derived, not listed
# --------------------------------------------------------------------------


def test_n4_ambiguity_is_the_intersection_of_the_two_ranges():
    assert ambiguous_numbers() == EXPECTED
    assert unambiguous_to(TRADING_SYSTEM) == {8, 9}
    assert unambiguous_to(CONTROL_PLANE) == set()


def test_n4_adding_a_wave_changes_the_set_without_anyone_editing_a_list(tmp_path):
    """A range this spec never listed, so the rule cannot be a lookup."""
    waves = tmp_path / "waves"
    waves.mkdir()
    for number in (3, 4, 8):
        (waves / f"wave{number}.yaml").write_text(f"wave_id: {number}\n", encoding="utf-8")

    assert our_waves(tmp_path) == {3, 4, 8}
    assert ambiguous_numbers(tmp_path) == {3, 4, 8}
    # 8 was unambiguously theirs a moment ago; a file on disk changed that.
    assert unambiguous_to(TRADING_SYSTEM, tmp_path) == {0, 1, 2, 5, 6, 7, 9}
    assert is_ambiguous("W8", tmp_path) is True


def test_n4_an_unknown_repository_is_not_silently_answered():
    with pytest.raises(ValueError):
        unambiguous_to("some-other-repo")
    with pytest.raises(ValueError):
        qualify("some-other-repo", 1)


# --------------------------------------------------------------------------
# N5 - parse, qualify, and which way the unambiguity runs
# --------------------------------------------------------------------------


@pytest.mark.parametrize("repository", [CONTROL_PLANE, TRADING_SYSTEM])
@pytest.mark.parametrize("number", [0, 7, 9])
def test_n5_qualify_and_parse_round_trip(repository, number):
    reference = qualify(repository, number)
    parsed = parse(reference)
    assert parsed.repository == repository
    assert parsed.number == number
    assert parsed.qualified is True
    assert str(parsed) == reference


def test_n5_a_bare_reference_parses_without_a_repository():
    parsed = parse("W7")
    assert parsed.repository is None
    assert parsed.qualified is False
    assert str(parsed) == "W7"


@pytest.mark.parametrize("number", sorted(EXPECTED))
def test_n5_every_shared_number_is_ambiguous_bare_and_readable_qualified(number):
    assert is_ambiguous(f"W{number}") is True
    assert is_ambiguous(qualify(CONTROL_PLANE, number)) is False
    assert is_ambiguous(qualify(TRADING_SYSTEM, number)) is False


@pytest.mark.parametrize("number", [8, 9])
def test_n5_w8_and_w9_are_theirs_not_nobodys(number):
    """The direction matters: a reader needs whose wave it unambiguously is."""
    assert is_ambiguous(f"W{number}") is False
    assert number in unambiguous_to(TRADING_SYSTEM)
    assert number not in our_waves()


@pytest.mark.parametrize("junk", ["", "wave7", "W", "W7x", "a:b:W7", "uptm runner:W7"])
def test_n5_something_that_is_not_a_reference_raises(junk):
    with pytest.raises(ValueError):
        parse(junk)


# --------------------------------------------------------------------------
# N6 - their range is recorded, not measured
# --------------------------------------------------------------------------


def test_n6_the_other_ranges_provenance_travels_with_the_number():
    assert THEIR_WAVES == frozenset(range(10))
    assert "not measured" in THEIR_WAVES_SOURCE
    assert "governance-map.md" in THEIR_WAVES_SOURCE
    assert TRADING_SYSTEM in THEIR_WAVES_SOURCE


# --------------------------------------------------------------------------
# N7 - the document that teaches the trap keeps the trap in it
# --------------------------------------------------------------------------


def test_n7_the_maps_own_w7_examples_survive():
    """Prose explaining the collision is not a status claim.

    A later tidy-up that qualified every W7 in the map would delete the example
    the map exists to give. This test fails if that happens.
    """
    text = MAP.read_text(encoding="utf-8")
    assert '### "W7" means two different things' in text
    assert '"W7 PASS" is not a wave verdict' in text
    assert text.count("W7") >= 8


# --------------------------------------------------------------------------
# N8 - recorded closed, in both places, and Q3 left alone
# --------------------------------------------------------------------------


def test_n8_q5_is_recorded_decided_in_both_places():
    text = " ".join(MAP.read_text(encoding="utf-8").split())
    assert "DECIDED (DEC-UPTM-MAP-Q5, 2026-09-28)" in text
    assert "OPEN (DEC-UPTM-MAP-Q5" not in text
    assert "stays open under `DEC-UPTM-MAP-Q5`" not in text
    # Neither numbering became canonical - the closure keeps that.
    assert "Neither numbering is canonical" in text


def test_n8_q3_was_not_swept_up_with_q5():
    """Amended by UPTM-017: Q3 is closed now, but on its own GO and its own date.

    N8 asked that closing Q5 leave Q3 alone. It did: Q3 stayed open for a day
    and was then decided separately, as a floor, by UPTM-017. The assertion
    moves from "still open" to "closed under its own marker", which is what the
    criterion was protecting.
    """
    text = " ".join(MAP.read_text(encoding="utf-8").split())
    assert "DECIDED (DEC-UPTM-MAP-Q3, 2026-09-29)" in text
    assert "DECIDED (DEC-UPTM-MAP-Q5, 2026-09-28)" in text
    assert "OPEN (DEC-UPTM-MAP-Q3" not in text


def test_n8_the_decisions_log_carries_it():
    log = (ROOT / "docs" / "decisions.md").read_text(encoding="utf-8")
    assert "[2026-09-28] DEC-UPTM-016" in log
