"""Runner finite-state machine."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import yaml

from runner.gates import GateResult, evaluate_gate
from runner.paths import BASELINE, ROOT, WAVES
from runner.stops import StopConditionError, check_live_trading, raise_if_stop


class State(str, Enum):
    DISCOVER = "DISCOVER"
    BASELINE = "BASELINE"
    PLAN = "PLAN"
    WAVE_READY = "WAVE_READY"
    PARALLEL_DISPATCH = "PARALLEL_DISPATCH"
    EXECUTION = "EXECUTION"
    COLLECT = "COLLECT"
    VERIFY = "VERIFY"
    ADVERSARIAL_VERIFY = "ADVERSARIAL_VERIFY"
    EVIDENCE = "EVIDENCE"
    WAVE_GATE = "WAVE_GATE"
    NEXT_WAVE = "NEXT_WAVE"
    PATCH_LOOP = "PATCH_LOOP"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
    COMPLETE = "COMPLETE"
    STOPPED = "STOPPED"


ALLOWED_TRANSITIONS: dict[State, set[State]] = {
    State.DISCOVER: {State.BASELINE, State.HUMAN_REVIEW_REQUIRED, State.STOPPED},
    State.BASELINE: {State.PLAN, State.HUMAN_REVIEW_REQUIRED, State.STOPPED},
    State.PLAN: {State.WAVE_READY, State.HUMAN_REVIEW_REQUIRED, State.STOPPED},
    State.WAVE_READY: {
        State.PARALLEL_DISPATCH,
        State.HUMAN_REVIEW_REQUIRED,
        State.STOPPED,
    },
    State.PARALLEL_DISPATCH: {
        State.EXECUTION,
        State.HUMAN_REVIEW_REQUIRED,
        State.STOPPED,
    },
    State.EXECUTION: {State.COLLECT, State.HUMAN_REVIEW_REQUIRED, State.STOPPED},
    State.COLLECT: {State.VERIFY, State.HUMAN_REVIEW_REQUIRED, State.STOPPED},
    State.VERIFY: {
        State.ADVERSARIAL_VERIFY,
        State.HUMAN_REVIEW_REQUIRED,
        State.STOPPED,
    },
    State.ADVERSARIAL_VERIFY: {
        State.EVIDENCE,
        State.HUMAN_REVIEW_REQUIRED,
        State.STOPPED,
    },
    State.EVIDENCE: {State.WAVE_GATE, State.HUMAN_REVIEW_REQUIRED, State.STOPPED},
    State.WAVE_GATE: {
        State.NEXT_WAVE,
        State.PATCH_LOOP,
        State.HUMAN_REVIEW_REQUIRED,
        State.STOPPED,
        State.COMPLETE,
    },
    State.NEXT_WAVE: {
        State.WAVE_READY,
        State.COMPLETE,
        State.HUMAN_REVIEW_REQUIRED,
        State.STOPPED,
    },
    State.PATCH_LOOP: {
        State.PARALLEL_DISPATCH,
        State.HUMAN_REVIEW_REQUIRED,
        State.STOPPED,
    },
    State.HUMAN_REVIEW_REQUIRED: set(),
    State.COMPLETE: set(),
    State.STOPPED: set(),
}


class FSMError(RuntimeError):
    pass


@dataclass
class RunnerFSM:
    state: State = State.DISCOVER
    current_wave: int = 0
    max_wave: int = 7
    patch_attempts: dict[str, int] = field(default_factory=dict)
    max_patch_attempts: int = 3
    unlocked_waves: set[int] = field(default_factory=lambda: {0})
    history: list[str] = field(default_factory=list)
    last_gate: GateResult | None = None

    def transition(self, new_state: State) -> None:
        allowed = ALLOWED_TRANSITIONS.get(self.state, set())
        if new_state not in allowed:
            raise FSMError(f"illegal transition {self.state.value} → {new_state.value}")
        self.history.append(f"{self.state.value}->{new_state.value}")
        self.state = new_state

    def assert_wave_unlocked(self, wave_id: int) -> None:
        if wave_id not in self.unlocked_waves:
            raise FSMError(f"wave_skip_attempt: wave {wave_id} not unlocked")
        if wave_id > 0 and (wave_id - 1) not in self.unlocked_waves:
            raise FSMError(f"wave_skip_attempt: wave {wave_id - 1} not gated")

    def unlock_next_wave(self) -> None:
        if self.current_wave >= self.max_wave:
            self.transition(State.COMPLETE)
            return
        nxt = self.current_wave + 1
        self.unlocked_waves.add(nxt)
        self.current_wave = nxt
        self.transition(State.NEXT_WAVE)
        self.transition(State.WAVE_READY)

    def record_patch(self, cluster_id: str) -> State:
        n = self.patch_attempts.get(cluster_id, 0) + 1
        self.patch_attempts[cluster_id] = n
        if n > self.max_patch_attempts:
            self.transition(State.HUMAN_REVIEW_REQUIRED)
            return self.state
        self.transition(State.PATCH_LOOP)
        return self.state

    def apply_gate(self, gate: GateResult, cluster_id: str = "default") -> State:
        self.last_gate = gate
        self.transition(State.WAVE_GATE)
        if gate.passed:
            if self.current_wave >= self.max_wave:
                self.transition(State.COMPLETE)
            else:
                self.unlock_next_wave()
            return self.state
        return self.record_patch(cluster_id)

    def stop(self, reason: str) -> None:
        self.history.append(f"STOP:{reason}")
        if self.state not in (State.HUMAN_REVIEW_REQUIRED, State.STOPPED, State.COMPLETE):
            # force via allowed path when possible
            if State.STOPPED in ALLOWED_TRANSITIONS.get(self.state, set()):
                self.transition(State.STOPPED)
            elif State.HUMAN_REVIEW_REQUIRED in ALLOWED_TRANSITIONS.get(self.state, set()):
                self.transition(State.HUMAN_REVIEW_REQUIRED)
            else:
                self.state = State.STOPPED


def load_baseline() -> dict[str, Any]:
    data = json.loads(BASELINE.read_text(encoding="utf-8"))
    raise_if_stop(check_live_trading(data.get("live_trading")))
    if data.get("pr4_merge_allowed") is not False:
        raise StopConditionError("unauthorized_pr_merge: pr4_merge_allowed must be false")
    return data


def load_wave(wave_id: int) -> dict[str, Any]:
    path = WAVES / f"wave{wave_id}.yaml"
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def wave_status(fsm: RunnerFSM | None = None) -> dict[str, Any]:
    fsm = fsm or RunnerFSM()
    waves = []
    for i in range(0, 8):
        w = load_wave(i)
        waves.append(
            {
                "wave_id": i,
                "name": w.get("name"),
                "unlocked": i in fsm.unlocked_waves,
                "current": i == fsm.current_wave,
                "depends_on": w.get("depends_on", []),
                "tip_assessment": w.get("tip_assessment"),
            }
        )
    return {
        "state": fsm.state.value,
        "current_wave": fsm.current_wave,
        "unlocked_waves": sorted(fsm.unlocked_waves),
        "patch_attempts": dict(fsm.patch_attempts),
        "waves": waves,
        "live_trading": False,
        "root": str(ROOT),
    }


def run_baseline_ack(out_dir: Path | None = None) -> dict[str, Any]:
    baseline = load_baseline()
    out_dir = out_dir or (ROOT / "evidence" / "wave0")
    out_dir.mkdir(parents=True, exist_ok=True)
    ack = {
        "evidence_id": "wave0-baseline-ack",
        "wave_id": 0,
        "commit_sha": "local-scaffold-0000000",
        "branch": "scaffold/uptm-runner",
        "pr": None,
        "files": [
            {
                "path": "audits/baseline/wave0_baseline.json",
                "sha256": __import__("hashlib")
                .sha256(BASELINE.read_bytes())
                .hexdigest(),
            }
        ],
        "commands": [{"cmd": "uptm-runner baseline", "exit_code": 0}],
        "results": {
            "passed": 1,
            "failed": 0,
            "findings": [
                *[
                    {
                        "id": f["id"],
                        "severity": f["severity"],
                        "status": "OPEN"
                        if "EXPLOITABLE" in f.get("status_after_pr3_audit", "")
                        or f.get("status_after_pr3_audit") == "CONFIRMED_EXPLOITABLE"
                        else "HYPOTHESIS"
                        if "pr4_claim" in f
                        else "OPEN",
                    }
                    for f in baseline.get("known_vulnerabilities", {}).get(
                        "from_audits_1_through_3", []
                    )
                ],
                *[
                    {
                        "id": r["id"],
                        "severity": r["severity"],
                        "status": r["status"],
                    }
                    for r in baseline.get("accepted_residuals", [])
                ],
            ],
        },
        "probes": [
            {
                "probe_id": "baseline_live_trading_false",
                "outcome": "BLOCKED",
                "output_digest": "live_trading_false",
            }
        ],
        "before": {"digest": "none", "summary": "pre-baseline"},
        "after": {
            "digest": __import__("hashlib").sha256(BASELINE.read_bytes()).hexdigest(),
            "summary": "baseline locked",
        },
        "agent_claim": {
            "verdict": "PASS",
            "notes": "baseline loaded by runner (not agent-only)",
        },
        "live_trading": False,
        "signature": None,
        "baseline_id": baseline.get("baseline_id"),
        "pr4_merge_allowed": False,
        "uptm_tip_pr": baseline.get("uptm_tip", {}).get("pr"),
        "uptm_tip_status": baseline.get("uptm_tip", {}).get("status"),
        "accepted_residuals": baseline.get("accepted_residuals", []),
        "uptm_machine_gate_required": baseline.get("runner_invariants", {}).get(
            "uptm_machine_gate_required", []
        ),
        "current_wave_assessment": baseline.get("current_wave_assessment", {}),
    }
    # Note: findings will include CRITICAL/HIGH OPEN — wave0 gate for "ack" is special;
    # baseline wave records them; gate for progressing past remediation waves must clear them.
    path = out_dir / "baseline_ack.json"
    path.write_text(json.dumps(ack, indent=2), encoding="utf-8")
    return {"path": str(path), "baseline_id": baseline.get("baseline_id"), "live_trading": False}
