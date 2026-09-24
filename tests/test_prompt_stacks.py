from __future__ import annotations

import json
import shutil

import pytest

from cursor.contract import CursorTask
from runner.gates import evaluate_gate
import runner.prompt_stacks as prompt_stacks
from runner.prompt_stacks import PromptStackError, assemble_prompt, load_stacks


def test_composer_deterministic_and_digest_stable():
    context = {"wave_id": 3, "purpose": "unit-test"}
    first = assemble_prompt(["00", "01", "02", "03"], "planner", context)
    second = assemble_prompt(["00", "01", "02", "03"], "planner", dict(reversed(context.items())))
    assert first.digest == second.digest
    assert first.body == second.body
    assert first.stack_versions == {"00": "0.1.0", "01": "0.1.0", "02": "0.1.0", "03": "0.1.0"}
    assert first.evidence_expires_at is None
    assert "registry_sha256_change" in first.stale_on
    assert first.stack_releases["03"].startswith("03@0.1.0+sha256:")
    assert len(first.registry_sha256) == 64


def test_registry_digests_match_canonical_bodies():
    stacks = load_stacks()
    assert stacks["00"].body_sha256 == "848312053ac684f39191bcd1cead87b7e7fecd1c0e761ac8983ff6a45c71b3e2"
    assert stacks["07"].body_sha256 == "ec3c6d5630637e2553c7c74e78d2f7fd95a9c3a2d7130558e54c57c23f7a9f71"


def test_forbidden_role_rejected():
    with pytest.raises(PromptStackError, match="may not receive stack 06"):
        assemble_prompt(["00", "06"], "executor", {"wave_id": 6})


def test_missing_stack_rejected():
    with pytest.raises(PromptStackError, match="unknown prompt stack"):
        assemble_prompt(["00", "99"], "commander", {"wave_id": 1})


def test_silence_rejected():
    with pytest.raises(PromptStackError, match="no prompt stacks"):
        assemble_prompt([], "commander", {"wave_id": 1})


def test_cursor_task_injects_role_metadata():
    assembled = assemble_prompt(["00", "04"], "executor", {"wave_id": 4})
    task = CursorTask(
        4,
        "04",
        "prompt-stacks/04_dispatch.md",
        role="executor",
        metadata=assembled.cursor_metadata(),
    )
    assert task.metadata["role"] == "executor"
    assert task.metadata["least_privilege"] is True
    assert task.metadata["assembled_prompt_digest"] == assembled.digest
    assert task.metadata["stack_ids"] == ["00", "04"]
    assert task.metadata["stack_releases"]["04"].startswith("04@0.1.0+sha256:")
    assert task.metadata["evidence_expires_at"] is None


def test_evidence_binding_accepts_matching_digest(valid_evidence_factory):
    assembled = assemble_prompt(["00", "04"], "executor", {"wave_id": 3})
    ev = valid_evidence_factory(prompt_stack=assembled.cursor_metadata())
    result = evaluate_gate(ev)
    assert result.passed is True


def test_evidence_binding_rejects_tampered_digest(valid_evidence_factory):
    assembled = assemble_prompt(["00", "04"], "executor", {"wave_id": 3})
    binding = assembled.cursor_metadata()
    binding["assembled_prompt_digest"] = "0" * 64
    ev = valid_evidence_factory(prompt_stack=binding)
    result = evaluate_gate(ev)
    assert result.passed is False
    assert any("assembled_prompt_digest mismatch" in reason for reason in result.reasons)


def test_evidence_binding_rejects_tampered_release_id(valid_evidence_factory):
    assembled = assemble_prompt(["00", "04"], "executor", {"wave_id": 3})
    binding = assembled.cursor_metadata()
    binding["stack_releases"]["04"] = "04@0.1.0+sha256:" + ("0" * 64)
    ev = valid_evidence_factory(prompt_stack=binding)
    result = evaluate_gate(ev)
    assert result.passed is False
    assert any("stack_releases mismatch" in reason for reason in result.reasons)


def test_stack_body_change_without_manifest_update_invalidates_evidence(
    tmp_path, monkeypatch, root, valid_evidence_factory
):
    assembled = assemble_prompt(["00", "04"], "executor", {"wave_id": 3})
    ev = valid_evidence_factory(prompt_stack=assembled.cursor_metadata())

    mutated_stacks = tmp_path / "prompt-stacks"
    shutil.copytree(root / "prompt-stacks", mutated_stacks)
    dispatch_stack = mutated_stacks / "04_dispatch.md"
    dispatch_stack.write_text(
        dispatch_stack.read_text(encoding="utf-8")
        + "\nMUTATION: unregistered stack body change.\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(prompt_stacks, "PROMPT_STACKS", mutated_stacks)

    result = evaluate_gate(ev)
    assert result.passed is False
    assert any("prompt stack 04 digest mismatch" in reason for reason in result.reasons)


def test_registry_policy_change_invalidates_evidence(
    tmp_path, monkeypatch, root, valid_evidence_factory
):
    assembled = assemble_prompt(["00", "04"], "executor", {"wave_id": 3})
    ev = valid_evidence_factory(prompt_stack=assembled.cursor_metadata())

    mutated_stacks = tmp_path / "prompt-stacks"
    shutil.copytree(root / "prompt-stacks", mutated_stacks)
    index_path = mutated_stacks / "index.json"
    registry = json.loads(index_path.read_text(encoding="utf-8"))
    registry["release_policy"]["stale_on"].append("manual_revocation")
    index_path.write_text(json.dumps(registry, indent=2), encoding="utf-8")
    monkeypatch.setattr(prompt_stacks, "PROMPT_STACKS", mutated_stacks)

    result = evaluate_gate(ev)
    assert result.passed is False
    assert any("registry_sha256 mismatch" in reason for reason in result.reasons)
    assert any("stale_on mismatch" in reason for reason in result.reasons)


def test_stack_version_change_invalidates_evidence(
    tmp_path, monkeypatch, root, valid_evidence_factory
):
    assembled = assemble_prompt(["00", "04"], "executor", {"wave_id": 3})
    ev = valid_evidence_factory(prompt_stack=assembled.cursor_metadata())

    mutated_stacks = tmp_path / "prompt-stacks"
    shutil.copytree(root / "prompt-stacks", mutated_stacks)
    index_path = mutated_stacks / "index.json"
    registry = json.loads(index_path.read_text(encoding="utf-8"))
    stack04 = next(stack for stack in registry["stacks"] if stack["id"] == "04")
    stack04["version"] = "0.1.1"
    index_path.write_text(json.dumps(registry, indent=2), encoding="utf-8")
    monkeypatch.setattr(prompt_stacks, "PROMPT_STACKS", mutated_stacks)

    result = evaluate_gate(ev)
    assert result.passed is False
    assert any("stack_versions mismatch" in reason for reason in result.reasons)
    assert any("stack_releases mismatch" in reason for reason in result.reasons)


def test_pass_without_prompt_stack_binding_rejected(valid_evidence_factory):
    ev = valid_evidence_factory()
    del ev["prompt_stack"]
    result = evaluate_gate(ev)
    assert result.passed is False
    assert any("prompt_stack binding required" in reason for reason in result.reasons)


def test_legacy_stack_claim_without_binding_rejected(valid_evidence_factory):
    ev = valid_evidence_factory(prompt_stack_id="04")
    del ev["prompt_stack"]
    result = evaluate_gate(ev)
    assert result.passed is False
    assert any("prompt_stack binding required" in reason for reason in result.reasons)
