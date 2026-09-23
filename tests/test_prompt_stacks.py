from __future__ import annotations

import pytest

from cursor.contract import CursorTask
from runner.gates import evaluate_gate
from runner.prompt_stacks import PromptStackError, assemble_prompt, load_stacks


def test_composer_deterministic_and_digest_stable():
    context = {"wave_id": 3, "purpose": "unit-test"}
    first = assemble_prompt(["00", "01", "02", "03"], "planner", context)
    second = assemble_prompt(["00", "01", "02", "03"], "planner", dict(reversed(context.items())))
    assert first.digest == second.digest
    assert first.body == second.body
    assert first.stack_versions == {"00": "0.1.0", "01": "0.1.0", "02": "0.1.0", "03": "0.1.0"}


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


def test_pass_claiming_legacy_stack_without_binding_rejected(valid_evidence_factory):
    ev = valid_evidence_factory(prompt_stack_id="04")
    result = evaluate_gate(ev)
    assert result.passed is False
    assert any("prompt_stack binding required" in reason for reason in result.reasons)
