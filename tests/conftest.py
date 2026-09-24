from __future__ import annotations

import json
from pathlib import Path

import hashlib

import pytest

from runner.paths import ROOT
from runner.prompt_stacks import assemble_prompt


@pytest.fixture
def root() -> Path:
    return ROOT


@pytest.fixture
def valid_evidence_factory():
    def _make(**overrides):
        prompt_stack_override = overrides.pop("prompt_stack", None)
        base = {
            "evidence_id": "test-ev-1",
            "wave_id": 3,
            "commit_sha": "abc1234567",
            "branch": "test/branch",
            "pr": None,
            # UPTM-008: the gate now verifies this binding. The digest is read
            # from the file the evidence names, because "a" * 64 was a
            # fabrication that passed unexamined for as long as the fixture
            # existed - which is the hole UPTM-008 was built to close.
            "files": [
                {
                    "path": "runner/gates.py",
                    "sha256": hashlib.sha256(
                        (ROOT / "runner" / "gates.py").read_bytes()
                    ).hexdigest(),
                }
            ],
            "commands": [{"cmd": "pytest", "exit_code": 0}],
            "results": {"passed": 1, "failed": 0, "findings": []},
            "probes": [
                {
                    "probe_id": "probe_live_trading",
                    "outcome": "BLOCKED",
                    "output_digest": "deadbeef",
                }
            ],
            "before": {"digest": "b" * 64, "summary": "before"},
            "after": {"digest": "c" * 64, "summary": "after"},
            "agent_claim": {"verdict": "PASS", "notes": "ok"},
            "live_trading": False,
            # UPTM-005: every gate declares what it bears. This one bears
            # neither, which is the common and legitimate case.
            "scope": {"capital_bearing": False, "live_bearing": False},
            "signature": None,
        }
        base.update(overrides)
        if prompt_stack_override is not None:
            base["prompt_stack"] = prompt_stack_override
        else:
            base["prompt_stack"] = assemble_prompt(
                ["00"],
                "commander",
                {"wave_id": base["wave_id"], "producer": "tests.valid_evidence_factory"},
            ).cursor_metadata()
        return base

    return _make


@pytest.fixture
def write_evidence(tmp_path, valid_evidence_factory):
    def _write(name: str = "ev.json", **overrides) -> Path:
        path = tmp_path / name
        path.write_text(json.dumps(valid_evidence_factory(**overrides)), encoding="utf-8")
        return path

    return _write
