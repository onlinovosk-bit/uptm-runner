from __future__ import annotations

import json

import pytest

from cursor.contract import CursorNotConfiguredError, CursorTask, get_executor
from runner.gates import evaluate_gate
from runner.prompt_stacks import assemble_prompt
from ruflo.adapter import SwarmDispatch, SwarmDispatchError, SwarmWorkClaim


def _claim(
    agent_id: str,
    paths: tuple[str, ...],
    *,
    wave_id: int = 2,
    role: str = "executor",
    stack_ids: tuple[str, ...] = ("00", "04"),
) -> SwarmWorkClaim:
    return SwarmWorkClaim(
        agent_id=agent_id,
        wave_id=wave_id,
        role=role,
        stack_ids=stack_ids,
        owned_paths=paths,
        lease_id=f"lease-{agent_id}",
        lease_expires_at="2026-09-23T21:00:00Z",
        evidence_skeleton_path=f"evidence/wave{wave_id}/{agent_id}.json",
    )


def test_dispatch_remains_fail_closed():
    executor = get_executor()
    assert executor.is_configured() is False
    with pytest.raises(CursorNotConfiguredError, match="Refusing to fake"):
        executor.dispatch(CursorTask(2, "04", "prompt-stacks/04_dispatch.md"))


def test_handoff_swarm_emits_one_handoff_per_claim():
    dispatch = SwarmDispatch(
        wave_id=2,
        claims=(
            _claim("agent-a", ("runner/fsm.py",)),
            _claim("agent-b", ("runner/gates.py",)),
        ),
    )
    executor = get_executor()
    handoffs = executor.handoff_swarm(
        dispatch,
        branch="cursor/aps-001-prompt-stack-binding-619d",
        commit_sha="abc1234567",
    )
    assert len(handoffs) == 2
    assert [item.evidence_skeleton_path for item in handoffs] == [
        "evidence/wave2/agent-a.json",
        "evidence/wave2/agent-b.json",
    ]
    assert all(item.status == "HANDOFF_REQUIRED" for item in handoffs)


def test_handoff_swarm_binds_prompt_stack_and_claim_metadata():
    claim = _claim("agent-a", ("runner/fsm.py",))
    dispatch = SwarmDispatch(wave_id=2, claims=(claim,))
    assembled = assemble_prompt(
        claim.stack_ids, claim.role, {"wave_id": claim.wave_id, "agent_id": claim.agent_id}
    )
    handoff = get_executor().handoff_swarm(
        dispatch,
        branch="cursor/aps-001-prompt-stack-binding-619d",
        commit_sha="abc1234567",
    )[0]
    assert handoff.task.role == "executor"
    assert handoff.task.stack_id == "04"
    assert handoff.task.prompt_ref == "prompt-stacks/04_dispatch.md"
    assert handoff.task.metadata["assembled_prompt_digest"] == assembled.digest
    assert handoff.task.metadata["stack_ids"] == ["00", "04"]
    assert handoff.task.metadata["swarm_claim"]["lease_id"] == "lease-agent-a"
    assert handoff.task.metadata["swarm_claim"]["owned_paths"] == ["runner/fsm.py"]
    assert handoff.task.metadata["skeleton"] is True
    assert handoff.task.metadata["evidence_skeleton_path"] == handoff.evidence_skeleton_path


def test_handoff_swarm_writes_skeletons_that_cannot_pass_gate(tmp_path):
    dispatch = SwarmDispatch(
        wave_id=2,
        claims=(
            _claim("agent-a", ("runner/fsm.py",)),
            _claim("agent-b", ("runner/gates.py",)),
        ),
    )
    handoffs = get_executor().handoff_swarm(
        dispatch,
        branch="cursor/aps-001-prompt-stack-binding-619d",
        commit_sha="abc1234567",
        write_root=tmp_path,
    )
    written = [tmp_path / item.evidence_skeleton_path for item in handoffs]
    assert all(path.is_file() for path in written)
    skeletons = [json.loads(path.read_text(encoding="utf-8")) for path in written]
    assert all(item["skeleton"] is True for item in skeletons)
    assert all(evaluate_gate(item).passed is False for item in skeletons)


def test_handoff_swarm_rejects_invalid_claim_ledger():
    dispatch = SwarmDispatch(
        wave_id=2,
        claims=(
            _claim("agent-a", ("runner/fsm.py",)),
            _claim("agent-b", ("runner/fsm.py",)),
        ),
    )
    with pytest.raises(SwarmDispatchError, match="ownership conflict"):
        get_executor().handoff_swarm(
            dispatch,
            branch="cursor/aps-001-prompt-stack-binding-619d",
            commit_sha="abc1234567",
        )
