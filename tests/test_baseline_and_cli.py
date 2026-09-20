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
    assert b["uptm_tip"]["pr"] == 16
    assert b["uptm_tip"]["status"] == "CLEAR_FOR_MEDIUM_LOW_ONLY"
    assert b["uptm_tip"]["merge_allowed_by_runner"] is False
    assert b["runner_invariants"]["uptm_auto_merge"] is False
    assert b["runner_invariants"]["uptm_machine_gate_required"] == [
        "CRITICAL=0",
        "HIGH=0",
        "tests_pass",
        "adversarial_tests_pass",
        "ci_pass",
        "invariants_hold",
    ]


def test_baseline_accepts_named_residuals():
    b = load_baseline()
    residuals = {r["id"]: r for r in b["accepted_residuals"]}
    assert residuals["R-MED-PLAINTEXT-PRIVATE-KEY-SIDECAR"]["status"] == "ACCEPT_RESIDUAL"
    assert (
        residuals["R-LOW-SIZINGPROPOSAL-MONKEYPATCH-BEFORE-PROPOSE"]["status"]
        == "ACCEPT_RESIDUAL"
    )
    assert {r["severity"] for r in residuals.values()} <= {"MEDIUM", "LOW"}


def test_baseline_ack_writes(tmp_path, monkeypatch):
    out = run_baseline_ack(out_dir=tmp_path)
    path = Path(out["path"])
    assert path.exists()
    data = json.loads(path.read_text())
    assert data["live_trading"] is False
    assert data["wave_id"] == 0
    assert data["uptm_tip_pr"] == 16
    assert data["uptm_tip_status"] == "CLEAR_FOR_MEDIUM_LOW_ONLY"
    assert data["accepted_residuals"]
    residual_findings = [
        f for f in data["results"]["findings"] if f["status"] == "ACCEPT_RESIDUAL"
    ]
    assert {f["id"] for f in residual_findings} == {
        "R-MED-PLAINTEXT-PRIVATE-KEY-SIDECAR",
        "R-LOW-SIZINGPROPOSAL-MONKEYPATCH-BEFORE-PROPOSE",
    }


def test_wave_status_structure():
    st = wave_status(RunnerFSM())
    assert st["live_trading"] is False
    assert len(st["waves"]) == 8
    assert st["unlocked_waves"] == [0]
    assessments = {w["wave_id"]: w["tip_assessment"] for w in st["waves"]}
    assert assessments[1] == "DONE_ON_TIP_PENDING_MAIN_MERGE"
    assert assessments[4] == "PARTIAL_DONE_ON_TIP_PENDING_MAIN_MERGE"
    assert assessments[5] == "NEXT_AFTER_CONSOLIDATE"


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
