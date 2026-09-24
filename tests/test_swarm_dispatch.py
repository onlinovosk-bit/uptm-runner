from __future__ import annotations

import json

import pytest

from runner.gates import evaluate_gate
from runner.paths import ROOT
from runner.prompt_stacks import assemble_prompt
from runner.staleness import digest_file
from ruflo.adapter import (
    RufloUnavailableError,
    SwarmDispatch,
    SwarmDispatchError,
    SwarmWorkClaim,
    evidence_skeleton_for_claim,
    evidence_skeleton_json,
    get_adapter,
)


def _claim(
    agent_id: str,
    paths: tuple[str, ...],
    *,
    wave_id: int = 2,
    role: str = "executor",
    stack_ids: tuple[str, ...] = ("00", "04"),
    lease_id: str | None = None,
    lease_expires_at: str = "2026-09-23T21:00:00Z",
    evidence_skeleton_path: str | None = None,
) -> SwarmWorkClaim:
    return SwarmWorkClaim(
        agent_id=agent_id,
        wave_id=wave_id,
        role=role,
        stack_ids=stack_ids,
        owned_paths=paths,
        lease_id=lease_id if lease_id is not None else f"lease-{agent_id}",
        lease_expires_at=lease_expires_at,
        evidence_skeleton_path=(
            evidence_skeleton_path
            if evidence_skeleton_path is not None
            else f"evidence/wave{wave_id}/{agent_id}.json"
        ),
    )


def test_parallel_ownership_conflict_rejected():
    dispatch = SwarmDispatch(
        wave_id=2,
        claims=(
            _claim("agent-a", ("runner/fsm.py",)),
            _claim("agent-b", ("runner/fsm.py",)),
        ),
    )
    with pytest.raises(SwarmDispatchError, match="ownership conflict"):
        dispatch.validate()


def test_parent_child_ownership_conflict_rejected():
    dispatch = SwarmDispatch(
        wave_id=2,
        claims=(
            _claim("agent-a", ("runner",)),
            _claim("agent-b", ("runner/gates.py",)),
        ),
    )
    with pytest.raises(SwarmDispatchError, match="ownership conflict"):
        dispatch.validate()


def test_overlap_inside_single_claim_rejected():
    dispatch = SwarmDispatch(
        wave_id=2,
        claims=(_claim("agent-a", ("runner", "runner/gates.py")),),
    )
    with pytest.raises(SwarmDispatchError, match="overlapping owned_paths"):
        dispatch.validate()


def test_parallel_claim_crossing_wave_rejected():
    dispatch = SwarmDispatch(
        wave_id=2,
        claims=(_claim("agent-a", ("runner/fsm.py",), wave_id=3),),
    )
    with pytest.raises(SwarmDispatchError, match="crosses wave boundary"):
        dispatch.validate()


def test_duplicate_agent_rejected():
    dispatch = SwarmDispatch(
        wave_id=2,
        claims=(
            _claim("agent-a", ("runner/fsm.py",)),
            _claim("agent-a", ("runner/gates.py",), lease_id="lease-agent-a-2"),
        ),
    )
    with pytest.raises(SwarmDispatchError, match="duplicate agent_id"):
        dispatch.validate()


def test_duplicate_lease_rejected():
    dispatch = SwarmDispatch(
        wave_id=2,
        claims=(
            _claim("agent-a", ("runner/fsm.py",), lease_id="lease-shared"),
            _claim("agent-b", ("runner/gates.py",), lease_id="lease-shared"),
        ),
    )
    with pytest.raises(SwarmDispatchError, match="duplicate lease_id"):
        dispatch.validate()


def test_malformed_lease_expiry_rejected():
    dispatch = SwarmDispatch(
        wave_id=2,
        claims=(_claim("agent-a", ("runner/fsm.py",), lease_expires_at="tomorrow"),),
    )
    with pytest.raises(SwarmDispatchError, match="ISO-8601"):
        dispatch.validate()


def test_unsafe_owned_path_rejected():
    dispatch = SwarmDispatch(
        wave_id=2,
        claims=(_claim("agent-a", ("../runner/fsm.py",)),),
    )
    with pytest.raises(SwarmDispatchError, match="unsafe owned path"):
        dispatch.validate()


def test_evidence_skeleton_must_stay_in_wave_directory():
    dispatch = SwarmDispatch(
        wave_id=2,
        claims=(
            _claim(
                "agent-a",
                ("runner/fsm.py",),
                evidence_skeleton_path="evidence/wave3/agent-a.json",
            ),
        ),
    )
    with pytest.raises(SwarmDispatchError, match="evidence skeleton path must live"):
        dispatch.validate()


def test_evidence_skeleton_must_be_json():
    dispatch = SwarmDispatch(
        wave_id=2,
        claims=(
            _claim(
                "agent-a",
                ("runner/fsm.py",),
                evidence_skeleton_path="evidence/wave2/agent-a.txt",
            ),
        ),
    )
    with pytest.raises(SwarmDispatchError, match="must be json"):
        dispatch.validate()


def test_role_stack_envelope_rejected():
    dispatch = SwarmDispatch(
        wave_id=2,
        claims=(
            _claim("agent-a", ("runner/fsm.py",), role="executor", stack_ids=("00", "06")),
        ),
    )
    with pytest.raises(SwarmDispatchError, match="may not receive stack 06"):
        dispatch.validate()


def test_parallel_max_agents_rejected():
    claims = tuple(_claim(f"agent-{i}", (f"owned/{i}.txt",)) for i in range(9))
    dispatch = SwarmDispatch(wave_id=2, claims=claims)
    with pytest.raises(SwarmDispatchError, match="claim count exceeds"):
        dispatch.validate()


def test_valid_claim_ledger_passes_validation():
    dispatch = SwarmDispatch(
        wave_id=2,
        claims=(
            _claim("agent-a", ("runner/fsm.py",)),
            _claim("agent-b", ("runner/gates.py",)),
        ),
    )
    dispatch.validate()


def test_ruflo_unavailable_does_not_produce_fake_swarm_pass():
    dispatch = SwarmDispatch(
        wave_id=2,
        claims=(
            _claim("agent-a", ("runner/fsm.py",)),
            _claim("agent-b", ("runner/gates.py",)),
        ),
    )
    adapter = get_adapter()
    assert adapter.available() is False
    with pytest.raises(RufloUnavailableError, match="refusing swarm fanout success"):
        adapter.dispatch_swarm(dispatch)


def test_evidence_skeleton_is_deterministic():
    claim = _claim("agent-a", ("runner/fsm.py",))
    first = evidence_skeleton_for_claim(
        claim, branch="cursor/aps-001-prompt-stack-binding-619d", commit_sha="abc1234567"
    )
    second = evidence_skeleton_for_claim(
        claim, branch="cursor/aps-001-prompt-stack-binding-619d", commit_sha="abc1234567"
    )
    assert first == second
    assert evidence_skeleton_json(
        claim, branch="cursor/aps-001-prompt-stack-binding-619d", commit_sha="abc1234567"
    ) == evidence_skeleton_json(
        claim, branch="cursor/aps-001-prompt-stack-binding-619d", commit_sha="abc1234567"
    )


def test_evidence_skeleton_binds_prompt_stack_and_claim_metadata():
    claim = _claim("agent-a", ("runner/fsm.py", "runner/gates.py"))
    assembled = assemble_prompt(
        claim.stack_ids, claim.role, {"wave_id": claim.wave_id, "agent_id": claim.agent_id}
    )
    skeleton = claim.evidence_skeleton(
        branch="cursor/aps-001-prompt-stack-binding-619d", commit_sha="abc1234567"
    )
    assert skeleton["skeleton"] is True
    assert skeleton["live_trading"] is False
    assert skeleton["agent_claim"]["verdict"] == "PARTIAL"
    assert skeleton["prompt_stack"] == assembled.cursor_metadata()
    assert skeleton["swarm_claim"]["lease_id"] == "lease-agent-a"
    assert skeleton["swarm_claim"]["owned_paths"] == ["runner/fsm.py", "runner/gates.py"]
    assert skeleton["swarm_claim"]["evidence_skeleton_path"] == "evidence/wave2/agent-a.json"
    assert skeleton["probes"][0]["outcome"] == "SKIPPED"


def test_evidence_skeleton_cannot_pass_gate():
    claim = _claim("agent-a", ("runner/fsm.py",))
    skeleton = evidence_skeleton_for_claim(
        claim, branch="cursor/aps-001-prompt-stack-binding-619d", commit_sha="abc1234567"
    )
    result = evaluate_gate(skeleton)
    assert result.passed is False
    assert any("declares no files" in reason for reason in result.reasons)

    bound = dict(skeleton)
    bound["files"] = [
        {"path": "runner/fsm.py", "sha256": digest_file(ROOT / "runner/fsm.py")}
    ]
    bound_result = evaluate_gate(bound)
    assert bound_result.passed is False
    assert any("SKIPPED" in reason for reason in bound_result.reasons)


def test_evidence_skeleton_requires_branch_and_commit():
    claim = _claim("agent-a", ("runner/fsm.py",))
    with pytest.raises(SwarmDispatchError, match="branch and commit_sha"):
        evidence_skeleton_for_claim(claim, branch="", commit_sha="abc1234567")
    with pytest.raises(SwarmDispatchError, match="branch and commit_sha"):
        evidence_skeleton_for_claim(claim, branch="main", commit_sha="")


def test_dispatch_writes_one_skeleton_per_claim(tmp_path):
    dispatch = SwarmDispatch(
        wave_id=2,
        claims=(
            _claim("agent-a", ("runner/fsm.py",)),
            _claim("agent-b", ("runner/gates.py",)),
        ),
    )
    written = dispatch.write_evidence_skeletons(
        root=tmp_path,
        branch="cursor/aps-001-prompt-stack-binding-619d",
        commit_sha="abc1234567",
    )
    assert [path.relative_to(tmp_path).as_posix() for path in written] == [
        "evidence/wave2/agent-a.json",
        "evidence/wave2/agent-b.json",
    ]
    loaded = [json.loads(path.read_text(encoding="utf-8")) for path in written]
    assert [item["swarm_claim"]["agent_id"] for item in loaded] == ["agent-a", "agent-b"]
    assert all(item["skeleton"] is True for item in loaded)
    assert all(evaluate_gate(item).passed is False for item in loaded)
