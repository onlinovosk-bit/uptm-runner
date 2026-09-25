"""Runner finite-state machine."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import yaml

from runner.gates import GateResult, evaluate_gate
from runner.paths import BASELINE, ROOT, WAVES
from runner.prompt_stacks import assemble_prompt
from runner.stops import StopConditionError, check_live_trading, raise_if_stop
from ruflo.adapter import SwarmCollectResult, SwarmDispatch, SwarmDispatchError


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
    EXIT = "EXIT"
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
        State.EXIT,
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
    State.EXIT: set(),
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
    passed_waves: set[int] = field(default_factory=set)
    history: list[str] = field(default_factory=list)
    last_gate: GateResult | None = None
    last_collect: SwarmCollectResult | None = None

    def transition(self, new_state: State) -> None:
        allowed = ALLOWED_TRANSITIONS.get(self.state, set())
        if new_state not in allowed:
            raise FSMError(f"illegal transition {self.state.value} → {new_state.value}")
        self.history.append(f"{self.state.value}->{new_state.value}")
        self.state = new_state

    def assert_wave_unlocked(self, wave_id: int) -> None:
        if wave_id not in self.unlocked_waves:
            raise FSMError(f"wave_skip_attempt: wave {wave_id} not unlocked")
        if wave_id > 0 and (wave_id - 1) not in self.passed_waves:
            raise FSMError(f"wave_skip_attempt: wave {wave_id - 1} not gated PASS")

    def unlock_next_wave(self) -> None:
        if self.current_wave >= self.max_wave:
            self.transition(State.EXIT)
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

    def apply_gate(
        self,
        gate: GateResult,
        cluster_id: str = "default",
        *,
        dispatch: SwarmDispatch | None = None,
        artifacts: Mapping[str, Mapping[str, Any]] | None = None,
    ) -> State:
        self.last_gate = gate
        self.last_collect = None
        self.transition(State.WAVE_GATE)
        collect_ok = True
        if dispatch is not None:
            mismatch = _agent_ledger_mismatch(self.current_wave, dispatch)
            if mismatch is not None:
                self.last_collect = mismatch
                collect_ok = False
            else:
                self.last_collect = _collect_for_wave(self.current_wave, dispatch, artifacts)
                collect_ok = self.last_collect.passed
        elif _wave_lists_agents(self.current_wave):
            self.last_collect = SwarmCollectResult(
                wave_id=self.current_wave,
                passed=False,
                reasons=("fail-closed: wave lists agents and has no swarm dispatch",),
            )
            collect_ok = False
        gate_passed = gate.passed and gate.critical == 0 and gate.high == 0 and collect_ok
        if gate_passed:
            self.passed_waves.add(self.current_wave)
            if self.current_wave >= self.max_wave:
                self.transition(State.EXIT)
            else:
                self.unlock_next_wave()
            return self.state
        return self.record_patch(cluster_id)

    def is_terminal(self) -> bool:
        return self.state in {
            State.HUMAN_REVIEW_REQUIRED,
            State.EXIT,
            State.COMPLETE,
            State.STOPPED,
        }

    def run_until_terminal(
        self,
        gate_provider: Any,
        *,
        swarm_provider: Any = None,
        max_steps: int = 256,
    ) -> State:
        """Drive the control loop until EXIT or a terminal stop.

        ``gate_provider`` is called as ``gate_provider(fsm)`` at each WAVE_GATE.
        It must return a ``GateResult`` produced from complete evidence. The
        step cap is a safety assertion: an infinite control loop is a bug.

        ``swarm_provider(fsm)`` may return ``(dispatch, artifacts)`` for the
        current wave. A returned ledger is collected before ``passed_waves``
        can record that wave. ``None`` supplies no ledger. A wave whose yaml
        lists agents still denies without one, and a bound ledger must name
        exactly those agents.
        """
        steps = 0
        while not self.is_terminal():
            steps += 1
            if steps > max_steps:
                raise FSMError("non_terminating_fsm: step cap exceeded")

            if self.state is State.DISCOVER:
                self.transition(State.BASELINE)
            elif self.state is State.BASELINE:
                self.transition(State.PLAN)
            elif self.state is State.PLAN:
                self.assert_wave_unlocked(self.current_wave)
                self.transition(State.WAVE_READY)
            elif self.state is State.WAVE_READY:
                self.assert_wave_unlocked(self.current_wave)
                self.transition(State.PARALLEL_DISPATCH)
            elif self.state is State.PARALLEL_DISPATCH:
                self.transition(State.EXECUTION)
            elif self.state is State.EXECUTION:
                self.transition(State.COLLECT)
            elif self.state is State.COLLECT:
                self.transition(State.VERIFY)
            elif self.state is State.VERIFY:
                self.transition(State.ADVERSARIAL_VERIFY)
            elif self.state is State.ADVERSARIAL_VERIFY:
                self.transition(State.EVIDENCE)
            elif self.state is State.EVIDENCE:
                dispatch = None
                artifacts = None
                if swarm_provider is not None:
                    supplied = swarm_provider(self)
                    if supplied is not None:
                        dispatch, artifacts = supplied
                self.apply_gate(
                    gate_provider(self),
                    cluster_id=f"wave{self.current_wave}",
                    dispatch=dispatch,
                    artifacts=artifacts,
                )
            elif self.state is State.PATCH_LOOP:
                self.transition(State.PARALLEL_DISPATCH)
            elif self.state is State.NEXT_WAVE:
                self.transition(State.WAVE_READY)
            else:
                raise FSMError(f"non_terminating_fsm: unhandled state {self.state.value}")
        return self.state

    def stop(self, reason: str) -> None:
        self.history.append(f"STOP:{reason}")
        if self.state not in (
            State.HUMAN_REVIEW_REQUIRED,
            State.STOPPED,
            State.EXIT,
            State.COMPLETE,
        ):
            # force via allowed path when possible
            if State.STOPPED in ALLOWED_TRANSITIONS.get(self.state, set()):
                self.transition(State.STOPPED)
            elif State.HUMAN_REVIEW_REQUIRED in ALLOWED_TRANSITIONS.get(self.state, set()):
                self.transition(State.HUMAN_REVIEW_REQUIRED)
            else:
                self.state = State.STOPPED


def _declared_agents(wave_id: int) -> tuple[str, ...] | None:
    """Yaml agent names, or None when the declaration cannot be read.

    An empty tuple means the wave names nobody. Duplicate or blank entries are
    unreadable, so they deny rather than collapse into a smaller set.
    """
    agents = (load_wave(wave_id).get("ownership") or {}).get("agents", [])
    if not isinstance(agents, list):
        return None
    if any(not isinstance(item, str) or not item for item in agents):
        return None
    if len(agents) != len(set(agents)):
        return None
    return tuple(agents)


def _wave_lists_agents(wave_id: int) -> bool:
    """True when the wave yaml names agents, or the declaration cannot be read.

    An empty list is the declaration that the wave has no swarm. Anything else
    requires a SwarmDispatch before the wave can be recorded.
    """
    declared = _declared_agents(wave_id)
    if declared is None:
        return True
    # DEC-UPTM-APS-010: an empty list names nobody. It is not a missing ledger.
    return len(declared) > 0


def _agent_ledger_mismatch(
    wave_id: int, dispatch: SwarmDispatch
) -> SwarmCollectResult | None:
    """None when claim agent ids equal the yaml list, or the list names nobody.

    A non-empty list must be the same set as the ledger. An unreadable
    declaration denies even when a dispatch is bound.
    """
    declared = _declared_agents(wave_id)
    if declared is None:
        return SwarmCollectResult(
            wave_id=wave_id,
            passed=False,
            reasons=("fail-closed: wave agents declaration cannot be read",),
        )
    claimed = [claim.agent_id for claim in dispatch.claims]
    if declared and set(claimed) != set(declared):
        return SwarmCollectResult(
            wave_id=wave_id,
            passed=False,
            reasons=("fail-closed: claim agent_id does not match ownership.agents",),
        )
    return None


def _collect_for_wave(
    wave_id: int,
    dispatch: SwarmDispatch,
    artifacts: Mapping[str, Mapping[str, Any]] | None,
) -> SwarmCollectResult:
    """Collect the wave's own ledger. A foreign wave or a rejected ledger denies."""
    if dispatch.wave_id != wave_id:
        return SwarmCollectResult(
            wave_id=wave_id,
            passed=False,
            reasons=("fail-closed: collect wave does not match current wave",),
        )
    try:
        return dispatch.collect_and_verify(dict(artifacts or {}))
    except SwarmDispatchError as exc:
        return SwarmCollectResult(wave_id=wave_id, passed=False, reasons=(str(exc),))


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
        "passed_waves": sorted(fsm.passed_waves),
        "patch_attempts": dict(fsm.patch_attempts),
        "waves": waves,
        "live_trading": False,
        "root": str(ROOT),
    }


def run_baseline_ack(out_dir: Path | None = None) -> dict[str, Any]:
    baseline = load_baseline()
    prompt_stack = assemble_prompt(
        ["00"],
        "commander",
        {"wave_id": 0, "producer": "runner.fsm.run_baseline_ack"},
    )
    out_dir = out_dir or (ROOT / "evidence" / "wave0")
    out_dir.mkdir(parents=True, exist_ok=True)
    current_findings = [
        {
            "id": r["id"],
            "severity": r["severity"],
            "status": r["status"],
            "owner": r.get("owner"),
            "notes": r.get("notes") or r.get("rationale"),
        }
        for r in baseline.get("accepted_residuals", [])
    ]
    historical_findings = [
        {
            "id": f["id"],
            "severity": f["severity"],
            "status": "ARCHIVED_PRE_CLEAR",
            "source": f.get("first_seen_audit"),
            "notes": f.get("status_after_pr3_audit"),
        }
        for f in baseline.get("known_vulnerabilities", {}).get(
            "from_audits_1_through_3", []
        )
    ]
    ack = {
        "evidence_id": "wave0-baseline-ack",
        "wave_id": 0,
        # UPTM-005: every gate declares what it bears. Wave 0 locks a baseline —
        # it puts no capital at risk and carries no LIVE capability. The
        # declaration is emitted by the producer, not patched onto the artifact
        # afterwards, so a regenerated ack is declared too.
        "scope": {"capital_bearing": False, "live_bearing": False},
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
            "findings": current_findings,
        },
        "historical_findings_archive": {
            "scope": "pre-clear UPTM audits 1-3",
            "gate_counted": False,
            "findings": historical_findings,
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
        "prompt_stack": prompt_stack.cursor_metadata(),
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
    path = out_dir / "baseline_ack.json"
    path.write_text(json.dumps(ack, indent=2), encoding="utf-8")
    return {"path": str(path), "baseline_id": baseline.get("baseline_id"), "live_trading": False}
