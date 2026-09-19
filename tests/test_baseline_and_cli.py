from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from runner.fsm import load_baseline, run_baseline_ack, wave_status, RunnerFSM
from runner.paths import ROOT


def test_baseline_loads():
    b = load_baseline()
    assert b["live_trading"] is False
    assert "known_vulnerabilities" in b
    vulns = b["known_vulnerabilities"]["from_audits_1_through_3"]
    assert any(v["id"] == "V-CRIT-COORDINATED-DB-KEY-RECEIPT" for v in vulns)


def test_baseline_ack_writes(tmp_path, monkeypatch):
    out = run_baseline_ack(out_dir=tmp_path)
    path = Path(out["path"])
    assert path.exists()
    data = json.loads(path.read_text())
    assert data["live_trading"] is False
    assert data["wave_id"] == 0


def test_wave_status_structure():
    st = wave_status(RunnerFSM())
    assert st["live_trading"] is False
    assert len(st["waves"]) == 8
    assert st["unlocked_waves"] == [0]


def test_smoke_cli():
    proc = subprocess.run(
        [sys.executable, "-m", "runner.cli", "smoke"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["ok"] is True
    assert payload["live_trading"] is False
