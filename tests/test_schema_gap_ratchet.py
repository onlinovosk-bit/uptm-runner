"""UPTM-019 - the evidence schema's blind spot is bounded, and cannot widen silently.

`_schema_errors` returns `[]` when evidence does not match the schema (UPTM-010
made that a deliberate choice: the schema is measurably behind the code). So the
schema, today, catches exactly one thing - that it cannot be loaded - and the
suite is green whether or not a new pack shape is ever taught to it. Measured:
a new root-key read added to runner/gates.py leaves all 877 existing tests green.

This does not teach the schema anything and tightens nothing. It makes the gap a
*visible, bounded* thing: the set of root keys the runner reads that the schema
does not know is derived from the source, compared with a baseline of
acknowledged gaps, and the comparison fails in both directions - a new gap, and a
stale acknowledgement - so the baseline can only shrink.

The failing-validation COUNT is deliberately not pinned: every legitimate new test
moves it with no change in the gap. The derived key set does not move.

Criteria are the ones preregistered in docs/specs/UPTM-019-schema-gap-ratchet.md.
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path
from typing import Any

import jsonschema
import pytest

from runner.paths import ROOT, SCHEMAS

SCHEMA_PATH = SCHEMAS / "evidence.schema.json"
BASELINE_PATH = SCHEMAS / "schema-gaps.json"
BASELINE_KEY = "acknowledged_unknown_root_keys"
EVIDENCE_NAMES = frozenset({"evidence", "ev"})


# --------------------------------------------------------------------------
# derivation - from the source, never typed
# --------------------------------------------------------------------------


def root_keys_read(source: str) -> set[str]:
    """Root keys a module reads from a variable named `evidence` or `ev`.

    Four shapes: `evidence.get/pop/setdefault("k")`, `evidence["k"]`, and
    `"k" in evidence`. Nested access yields only the root key. A non-literal key,
    or any other variable, is ignored. Known limit, stated in the spec: a read
    through a variable with another name is not seen.
    """
    found: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        key: Any = None
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id in EVIDENCE_NAMES
            and node.func.attr in {"get", "setdefault", "pop"}
            and node.args
            and isinstance(node.args[0], ast.Constant)
        ):
            key = node.args[0].value
        elif (
            isinstance(node, ast.Subscript)
            and isinstance(node.value, ast.Name)
            and node.value.id in EVIDENCE_NAMES
            and isinstance(node.slice, ast.Constant)
        ):
            key = node.slice.value
        elif (
            isinstance(node, ast.Compare)
            and len(node.ops) == 1
            and isinstance(node.ops[0], (ast.In, ast.NotIn))
            and isinstance(node.comparators[0], ast.Name)
            and node.comparators[0].id in EVIDENCE_NAMES
            and isinstance(node.left, ast.Constant)
        ):
            key = node.left.value
        if isinstance(key, str):
            found.add(key)
    return found


def runner_reads() -> dict[str, list[str]]:
    """key -> the runner files that read it."""
    reads: dict[str, list[str]] = {}
    for path in sorted((ROOT / "runner").rglob("*.py")):
        for key in root_keys_read(path.read_text(encoding="utf-8")):
            reads.setdefault(key, []).append(str(path.relative_to(ROOT)))
    return reads


def schema_known() -> set[str]:
    return set(json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))["properties"])


def parse_baseline(text: str) -> dict[str, str]:
    """The acknowledged gaps: key -> reason. Strict, because the file is a promise."""

    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        keys = [k for k, _ in pairs]
        dupes = sorted({k for k in keys if keys.count(k) > 1})
        if dupes:
            raise ValueError(f"duplicate entries in the baseline: {dupes}")
        return dict(pairs)

    document = json.loads(text, object_pairs_hook=reject_duplicates)
    if not isinstance(document, dict) or not isinstance(document.get(BASELINE_KEY), dict):
        raise ValueError(f"the baseline must be an object holding an object `{BASELINE_KEY}`")
    entries = document[BASELINE_KEY]
    for key, reason in entries.items():
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError(f"`{key}` is acknowledged with no reason - say why it is not taught")
    return dict(entries)


def ratchet_problems(
    read: dict[str, list[str]], known: set[str], baseline: dict[str, str]
) -> list[str]:
    """Both directions. Empty means the baseline matches the derived gap exactly."""
    gap = set(read) - known
    problems: list[str] = []
    for key in sorted(gap - set(baseline)):
        problems.append(
            f"NEW GAP: `{key}` is read by {', '.join(read[key])} but is unknown to the "
            f"evidence schema and not acknowledged. Either teach "
            f"schemas/evidence.schema.json the key, or acknowledge it in "
            f"schemas/schema-gaps.json with a reason."
        )
    for key in sorted(set(baseline) & known):
        problems.append(
            f"STALE: `{key}` is acknowledged as a gap but the schema now knows it - "
            f"remove it from schemas/schema-gaps.json."
        )
    for key in sorted(set(baseline) - known - set(read)):
        problems.append(
            f"STALE: `{key}` is acknowledged as a gap but the runner no longer reads it - "
            f"remove it from schemas/schema-gaps.json."
        )
    return problems


# --------------------------------------------------------------------------
# K1 - the derivation, on source we control
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "line, expected",
    [
        ('x = evidence.get("a")', {"a"}),
        ('x = evidence.get("a", {})', {"a"}),
        ('x = evidence.setdefault("a", [])', {"a"}),
        ('x = evidence.pop("a")', {"a"}),
        ('x = evidence["a"]', {"a"}),
        ('x = "a" in evidence', {"a"}),
        ('x = "a" not in evidence', {"a"}),
        ('x = ev.get("a")', {"a"}),
        ('x = evidence["a"]["b"]', {"a"}),
        ('x = evidence.get("a").get("b")', {"a"}),
        ('x = other.get("a")', set()),
        ('x = pack["a"]', set()),
        ("x = evidence.get(name)", set()),
        ("x = evidence[name]", set()),
        ('x = evidence.get(1)', set()),
        ('x = "a" in pack', set()),
        ('x = evidence.keys()', set()),
    ],
)
def test_k1_the_scan_recognises_the_read_shapes_and_ignores_the_rest(line, expected):
    assert root_keys_read(line) == expected


def test_k1_a_read_inside_a_nested_function_is_still_seen():
    source = "def f(evidence):\n    def g():\n        return evidence.get('deep')\n    return g\n"
    assert root_keys_read(source) == {"deep"}


# --------------------------------------------------------------------------
# K2, K3 - THE REAL REPOSITORY
# --------------------------------------------------------------------------


def test_k2_the_real_scan_is_not_vacuous_and_nothing_about_it_is_typed():
    """Reads found, and some of them are keys the schema knows.

    Deliberately NOT "and some it does not": the day the gap is closed the
    baseline is empty and the ratchet must pass, not punish the success.
    """
    read = runner_reads()
    assert read, "the scan found no root-key reads in runner/ at all"
    assert set(read) & schema_known(), "the scan found no key the schema knows - it is not reading evidence"


def test_k3_the_baseline_equals_the_derived_gap_on_the_real_repository():
    problems = ratchet_problems(
        runner_reads(), schema_known(), parse_baseline(BASELINE_PATH.read_text(encoding="utf-8"))
    )
    assert not problems, "\n".join(problems)


def test_k3_every_acknowledgement_carries_a_reason_and_the_file_is_strict():
    entries = parse_baseline(BASELINE_PATH.read_text(encoding="utf-8"))
    for key, reason in entries.items():
        assert len(reason.split()) >= 5, f"`{key}`: a reason is a sentence, not a word"


# --------------------------------------------------------------------------
# K4, K5, K6 - THE RATCHET, ON INPUTS WE CONTROL
# --------------------------------------------------------------------------

KNOWN = {"files", "scope", "wave_id"}
READ = {"files": ["runner/a.py"], "scope": ["runner/a.py"], "capital": ["runner/b.py"]}
BASELINE = {"capital": "read by the capital detectors, fails closed, shape unknown"}


def test_k4_the_consistent_state_passes():
    assert ratchet_problems(READ, KNOWN, BASELINE) == []


def test_k4_a_new_unacknowledged_gap_fails_and_names_both_ways_out():
    read = {**READ, "brand_new_pack": ["runner/c.py"]}
    problems = ratchet_problems(read, KNOWN, BASELINE)
    assert len(problems) == 1
    text = problems[0]
    assert "NEW GAP" in text and "`brand_new_pack`" in text and "runner/c.py" in text
    assert "teach" in text and "acknowledge it" in text


def test_k4_acknowledging_it_with_a_reason_is_the_visible_way_out():
    read = {**READ, "brand_new_pack": ["runner/c.py"]}
    assert ratchet_problems(read, KNOWN, {**BASELINE, "brand_new_pack": "a reason of some words"}) == []


def test_k4_teaching_the_schema_is_the_other_way_out():
    read = {**READ, "brand_new_pack": ["runner/c.py"]}
    assert ratchet_problems(read, KNOWN | {"brand_new_pack"}, BASELINE) == []


def test_k5_a_key_the_schema_has_since_learned_is_a_stale_acknowledgement():
    problems = ratchet_problems(READ, KNOWN | {"capital"}, BASELINE)
    assert len(problems) == 1
    assert "STALE" in problems[0] and "schema now knows" in problems[0]


def test_k5_a_key_the_runner_no_longer_reads_is_a_stale_acknowledgement():
    read = {k: v for k, v in READ.items() if k != "capital"}
    problems = ratchet_problems(read, KNOWN, BASELINE)
    assert len(problems) == 1
    assert "STALE" in problems[0] and "no longer reads" in problems[0]


def test_k5_closing_the_whole_gap_passes_so_success_is_not_punished():
    read = {"files": ["runner/a.py"], "scope": ["runner/a.py"]}
    assert ratchet_problems(read, KNOWN, {}) == []


@pytest.mark.parametrize(
    "text, fragment",
    [
        ('{"acknowledged_unknown_root_keys": {"a": ""}}', "no reason"),
        ('{"acknowledged_unknown_root_keys": {"a": "   "}}', "no reason"),
        ('{"acknowledged_unknown_root_keys": {"a": 5}}', "no reason"),
        ('{"acknowledged_unknown_root_keys": {"a": "x y z w v", "a": "x y z w v"}}', "duplicate"),
        ('["a"]', "must be an object"),
        ('{"acknowledged_unknown_root_keys": ["a"]}', "must be an object"),
        ('{"something_else": {}}', "must be an object"),
    ],
)
def test_k6_a_malformed_baseline_is_refused(text, fragment):
    with pytest.raises(ValueError, match=fragment):
        parse_baseline(text)


# --------------------------------------------------------------------------
# K7 - THE SCHEMA BITES WHERE IT KNOWS
# --------------------------------------------------------------------------


def test_k7_the_base_evidence_validates_against_the_real_schema(valid_evidence_factory):
    jsonschema.validate(valid_evidence_factory(), json.loads(SCHEMA_PATH.read_text(encoding="utf-8")))


def test_k7_a_corrupted_known_field_is_rejected(valid_evidence_factory):
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    corrupted = {**valid_evidence_factory(), "wave_id": "three"}
    with pytest.raises(jsonschema.ValidationError, match="wave_id|three"):
        jsonschema.validate(corrupted, schema)


def test_k7_an_unknown_root_key_is_rejected_by_the_schema_itself(valid_evidence_factory):
    """Why the gap exists at all: additionalProperties is false, so the eight packs
    the runner reads are rejected by the schema - and that rejection is silent."""
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert schema.get("additionalProperties") is False
    with pytest.raises(jsonschema.ValidationError, match="Additional properties"):
        jsonschema.validate({**valid_evidence_factory(), "brand_new_pack": {}}, schema)


def test_k8_a_schema_mismatch_is_still_silent_in_the_gate(valid_evidence_factory):
    """No behaviour change: UPTM-010's decision stands."""
    from runner.evidence import _schema_errors

    assert _schema_errors({**valid_evidence_factory(), "brand_new_pack": {}}) == []
