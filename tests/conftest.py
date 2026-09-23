from __future__ import annotations

import json
from pathlib import Path

import pytest

from runner.paths import ROOT


@pytest.fixture
def root() -> Path:
    return ROOT


@pytest.fixture
def valid_evidence_factory():
    def _make(**overrides):
        base = {
            "evidence_id": "test-ev-1",
            "wave_id": 3,
            "commit_sha": "abc1234567",
            "branch": "test/branch",
            "pr": None,
            "files": [
                {
                    "path": "runner/gates.py",
                    "sha256": "a" * 64,
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
        return base

    return _make


@pytest.fixture
def write_evidence(tmp_path, valid_evidence_factory):
    def _write(name: str = "ev.json", **overrides) -> Path:
        path = tmp_path / name
        path.write_text(json.dumps(valid_evidence_factory(**overrides)), encoding="utf-8")
        return path

    return _write
