"""UPTM-010: a schema that cannot be read is a fault, not a pass.

Criteria are preregistered in `docs/specs/UPTM-010-schema-load-is-not-optional.md`,
written before this file existed. Each test names the criterion it discharges.
"""

from __future__ import annotations

import json
import sys

import pytest

from runner import evidence as evidence_mod
from runner.enforcement import _base
from runner.evidence import validate_evidence_structure
from runner.gates import evaluate_gate
from runner.verdict import Verdict

FAULT = "schema check could not run"


def _schema_faults(evidence: dict) -> list[str]:
    return [e for e in validate_evidence_structure(evidence) if e.startswith(FAULT)]


def test_s1_a_schema_that_does_not_parse_is_reported_with_its_line(tmp_path, monkeypatch):
    """The exact shape that was inert from c4c409d until UPTM-009 repaired it."""
    # Two `required` lists concatenated, comma dropped - c4c409d's damage.
    broken = '{\n  "required": [\n    "stale_on"\n    "wave_context"\n  ]\n}\n'
    path = tmp_path / "evidence.schema.json"
    path.write_text(broken, encoding="utf-8")
    monkeypatch.setattr(evidence_mod, "SCHEMA_PATH", path)

    faults = _schema_faults(_base())
    assert len(faults) == 1
    assert "does not parse" in faults[0]
    assert "line 4" in faults[0]
    # The decoder's own message, not a paraphrase.
    with pytest.raises(json.JSONDecodeError) as raised:
        json.loads(broken)
    assert raised.value.msg in faults[0]


def test_s2_an_absent_schema_is_reported(tmp_path, monkeypatch):
    monkeypatch.setattr(evidence_mod, "SCHEMA_PATH", tmp_path / "gone.json")
    faults = _schema_faults(_base())
    assert len(faults) == 1
    assert "unreadable" in faults[0]


def test_s3_a_file_that_parses_but_is_not_a_json_schema_is_reported(tmp_path, monkeypatch):
    path = tmp_path / "evidence.schema.json"
    path.write_text('{"type": 12345}', encoding="utf-8")
    monkeypatch.setattr(evidence_mod, "SCHEMA_PATH", path)

    faults = _schema_faults(_base())
    assert len(faults) == 1
    assert "not a valid" in faults[0]


def test_s4_jsonschema_not_importable_is_a_fault_not_a_pass(monkeypatch):
    """The judgement call recorded in the spec's §4, asserted here.

    jsonschema is a declared runtime dependency. An environment without it
    cannot run the check, and a check that did not run must not read as one
    that passed.
    """
    monkeypatch.setitem(sys.modules, "jsonschema", None)
    faults = _schema_faults(_base())
    assert len(faults) == 1
    assert "jsonschema is not importable" in faults[0]


def test_s5_evidence_that_does_not_match_a_loadable_schema_adds_no_error(tmp_path, monkeypatch):
    """Mismatch stays soft. Measured reason: the schema is behind the evidence."""
    path = tmp_path / "evidence.schema.json"
    path.write_text('{"required": ["a_field_no_evidence_has"]}', encoding="utf-8")
    monkeypatch.setattr(evidence_mod, "SCHEMA_PATH", path)

    # It really does mismatch...
    jsonschema = pytest.importorskip("jsonschema")
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(_base(), json.loads(path.read_text()))
    # ...and the gate is told nothing about it.
    assert validate_evidence_structure(_base()) == []


def test_s6_the_fault_denies_the_gate(tmp_path, monkeypatch):
    path = tmp_path / "evidence.schema.json"
    path.write_text("{,}", encoding="utf-8")
    monkeypatch.setattr(evidence_mod, "SCHEMA_PATH", path)

    result = evaluate_gate(_base())
    assert result.verdict is Verdict.FAIL
    assert any(r.startswith(f"fail-closed: {FAULT}") for r in result.reasons)


def test_s6_the_same_pack_passes_when_the_schema_loads():
    """The denial above is the schema fault, not something else about the pack."""
    assert evaluate_gate(_base()).verdict is Verdict.PASS


def test_s7_a_fault_is_reported_once_not_once_per_field(tmp_path, monkeypatch):
    path = tmp_path / "evidence.schema.json"
    path.write_text("{,}", encoding="utf-8")
    monkeypatch.setattr(evidence_mod, "SCHEMA_PATH", path)

    # Evidence missing many fields: the field errors are many, the fault is one.
    errors = validate_evidence_structure({})
    assert len([e for e in errors if e.startswith(FAULT)]) == 1
    assert len([e for e in errors if e.startswith("missing field")]) > 1


def test_l2_the_repaired_schema_accepts_a_real_gate_pack():
    """UPTM-009 left this open: the schema parsed, but did it accept anything?"""
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(evidence_mod.SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.validate(_base(), schema)
