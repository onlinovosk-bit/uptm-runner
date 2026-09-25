from __future__ import annotations

import json

from runner.paths import ROOT
from runner.staleness import digest_file
from ruflo.adapter import SwarmDispatch, SwarmWorkClaim


def _claim(agent_id: str, path: str) -> SwarmWorkClaim:
    return SwarmWorkClaim(
        agent_id=agent_id,
        wave_id=2,
        role="executor",
        stack_ids=("00", "04"),
        owned_paths=(path,),
        lease_id=f"lease-{agent_id}",
        lease_expires_at="2026-09-23T21:00:00Z",
        evidence_skeleton_path=f"evidence/wave2/{agent_id}.json",
    )


def _dispatch() -> SwarmDispatch:
    return SwarmDispatch(
        wave_id=2,
        claims=(
            _claim("agent-a", "runner/fsm.py"),
            _claim("agent-b", "runner/gates.py"),
        ),
    )


def _real(claim: SwarmWorkClaim) -> dict:
    evidence = claim.evidence_skeleton(branch="collect", commit_sha="abc1234567")
    evidence["skeleton"] = False
    evidence["files"] = [
        {"path": path, "sha256": digest_file(ROOT / path)} for path in claim.owned_paths
    ]
    evidence["probes"] = [
        {
            "probe_id": "probe_live_trading",
            "outcome": "BLOCKED",
            "output_digest": "deadbeef",
        }
    ]
    evidence["results"] = {"passed": 1, "failed": 0, "findings": []}
    evidence["commands"] = [{"cmd": "pytest", "exit_code": 0}]
    evidence["agent_claim"] = {"verdict": "PASS", "notes": "executed"}
    return evidence


def test_collect_passes_when_every_claim_has_real_evidence():
    dispatch = _dispatch()
    artifacts = {claim.evidence_skeleton_path: _real(claim) for claim in dispatch.claims}
    result = dispatch.collect_and_verify(artifacts)
    assert result.passed is True
    assert result.reasons == ()


def test_collect_fails_when_a_claim_is_missing():
    dispatch = _dispatch()
    first = dispatch.claims[0]
    result = dispatch.collect_and_verify({first.evidence_skeleton_path: _real(first)})
    assert result.passed is False
    assert any("missing evidence for agent-b" in reason for reason in result.reasons)


def test_collect_fails_when_a_claim_is_still_a_skeleton():
    dispatch = _dispatch()
    artifacts = {claim.evidence_skeleton_path: _real(claim) for claim in dispatch.claims}
    skeleton = dispatch.claims[1].evidence_skeleton(branch="collect", commit_sha="abc1234567")
    artifacts[dispatch.claims[1].evidence_skeleton_path] = skeleton
    result = dispatch.collect_and_verify(artifacts)
    assert result.passed is False
    assert any("still a skeleton" in reason for reason in result.reasons)
    assert any("all SKIPPED" in reason for reason in result.reasons)


def test_collect_fails_when_probes_are_all_skipped():
    dispatch = _dispatch()
    artifacts = {claim.evidence_skeleton_path: _real(claim) for claim in dispatch.claims}
    skipped = artifacts[dispatch.claims[0].evidence_skeleton_path]
    skipped["probes"] = [
        {"probe_id": "probe_live_trading", "outcome": "SKIPPED", "output_digest": "deadbeef"}
    ]
    result = dispatch.collect_and_verify(artifacts)
    assert result.passed is False
    assert any("agent-a: probes missing or all SKIPPED" in reason for reason in result.reasons)


def test_collect_fails_when_prompt_stack_digest_differs():
    dispatch = _dispatch()
    artifacts = {claim.evidence_skeleton_path: _real(claim) for claim in dispatch.claims}
    artifacts[dispatch.claims[0].evidence_skeleton_path]["prompt_stack"][
        "assembled_prompt_digest"
    ] = "0" * 64
    result = dispatch.collect_and_verify(artifacts)
    assert result.passed is False
    assert any("agent-a: prompt_stack digest mismatch" in reason for reason in result.reasons)


def test_collect_dir_reads_one_file_per_claim(tmp_path):
    dispatch = _dispatch()
    for claim in dispatch.claims:
        path = tmp_path / claim.evidence_skeleton_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(_real(claim)), encoding="utf-8")
    result = dispatch.collect_and_verify_dir(tmp_path)
    assert result.passed is True


def test_collect_dir_fails_closed_when_a_file_is_missing(tmp_path):
    dispatch = _dispatch()
    claim = dispatch.claims[0]
    path = tmp_path / claim.evidence_skeleton_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_real(claim)), encoding="utf-8")
    result = dispatch.collect_and_verify_dir(tmp_path)
    assert result.passed is False
    assert any("missing evidence for agent-b" in reason for reason in result.reasons)
