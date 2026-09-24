"""Deterministic prompt stack loading, composition, and evidence binding."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from runner.paths import PROMPT_STACKS

VALID_ROLES = {"commander", "red_team", "executor", "verifier", "planner"}


class PromptStackError(ValueError):
    """Prompt stack composition failed closed."""


@dataclass(frozen=True)
class PromptStack:
    id: str
    name: str
    file: str
    version: str
    body_sha256: str
    release_id: str
    depends_on: tuple[str, ...]
    required_roles: tuple[str, ...]
    body: str


@dataclass(frozen=True)
class AssembledPrompt:
    role: str
    stack_ids: tuple[str, ...]
    stack_versions: dict[str, str]
    stack_digests: dict[str, str]
    stack_releases: dict[str, str]
    registry_sha256: str
    evidence_expires_at: str | None
    stale_on: tuple[str, ...]
    wave_context: dict[str, Any]
    body: str
    digest: str

    def cursor_metadata(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "stack_ids": list(self.stack_ids),
            "stack_versions": dict(self.stack_versions),
            "stack_digests": dict(self.stack_digests),
            "stack_releases": dict(self.stack_releases),
            "registry_sha256": self.registry_sha256,
            "assembled_prompt_digest": self.digest,
            "evidence_expires_at": self.evidence_expires_at,
            "stale_on": list(self.stale_on),
            "wave_context": dict(self.wave_context),
        }


def canonical_stack_body(path: Path) -> str:
    raw = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    if path.suffix == ".json":
        payload = json.loads(raw)
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return raw.strip() + "\n"


def digest_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _load_registry() -> dict[str, Any]:
    return json.loads((PROMPT_STACKS / "index.json").read_text(encoding="utf-8"))


def registry_sha256(registry: dict[str, Any] | None = None) -> str:
    """Digest the full prompt-stack registry, including release policy."""
    return digest_text(_canonical_json(registry if registry is not None else _load_registry()))


def release_policy(registry: dict[str, Any] | None = None) -> dict[str, Any]:
    policy = (registry if registry is not None else _load_registry()).get("release_policy") or {}
    stale_on = policy.get("stale_on") or []
    if not isinstance(stale_on, list) or not all(isinstance(item, str) for item in stale_on):
        raise PromptStackError("fail-closed: release_policy.stale_on must be a list of strings")
    return {
        "evidence_expires_at": policy.get("evidence_expires_at"),
        "stale_on": tuple(stale_on),
    }


def load_stacks() -> dict[str, PromptStack]:
    registry = _load_registry()
    stacks: dict[str, PromptStack] = {}
    for item in registry.get("stacks", []):
        stack_id = str(item.get("id", ""))
        if not stack_id:
            raise PromptStackError("fail-closed: prompt stack id missing")
        path = PROMPT_STACKS / str(item.get("file", ""))
        if not path.exists():
            raise PromptStackError(f"fail-closed: prompt stack {stack_id} file missing")
        body = canonical_stack_body(path)
        digest = digest_text(body)
        declared_digest = item.get("body_sha256")
        if declared_digest and declared_digest != digest:
            raise PromptStackError(
                f"fail-closed: prompt stack {stack_id} digest mismatch"
            )
        roles = tuple(item.get("required_roles") or ())
        unknown_roles = sorted(set(roles) - VALID_ROLES)
        if unknown_roles:
            raise PromptStackError(
                f"fail-closed: prompt stack {stack_id} unknown roles {unknown_roles}"
            )
        version = str(item.get("version") or item.get("schema_version") or "")
        release_id = f"{stack_id}@{version}+sha256:{digest}"
        stacks[stack_id] = PromptStack(
            id=stack_id,
            name=str(item.get("name", "")),
            file=str(item.get("file", "")),
            version=version,
            body_sha256=digest,
            release_id=release_id,
            depends_on=tuple(str(dep) for dep in item.get("depends_on", [])),
            required_roles=roles,
            body=body,
        )
    return stacks


def role_allowed_stacks(role: str) -> tuple[str, ...]:
    if role not in VALID_ROLES:
        raise PromptStackError(f"fail-closed: unknown role {role!r}")
    registry = _load_registry()
    taxonomy = registry.get("role_taxonomy") or {}
    allowed = taxonomy.get(role, {}).get("allowed_stack_ids")
    if not allowed:
        raise PromptStackError(f"fail-closed: role {role!r} has no stack envelope")
    return tuple(str(stack_id) for stack_id in allowed)


def assemble_prompt(
    stack_ids: list[str] | tuple[str, ...], role: str, wave_context: dict[str, Any]
) -> AssembledPrompt:
    """Assemble a prompt deterministically; unknown, silent, or overbroad input denies."""
    if not stack_ids:
        raise PromptStackError("fail-closed: no prompt stacks requested")
    if not isinstance(wave_context, dict) or not wave_context:
        raise PromptStackError("fail-closed: wave_context is required")

    stacks = load_stacks()
    allowed = set(role_allowed_stacks(role))
    requested = tuple(str(stack_id) for stack_id in stack_ids)
    seen: set[str] = set()
    for stack_id in requested:
        if stack_id in seen:
            raise PromptStackError(f"fail-closed: duplicate prompt stack {stack_id}")
        seen.add(stack_id)
        if stack_id not in stacks:
            raise PromptStackError(f"fail-closed: unknown prompt stack {stack_id}")
        stack = stacks[stack_id]
        if stack_id not in allowed or role not in stack.required_roles:
            raise PromptStackError(
                f"fail-closed: role {role!r} may not receive stack {stack_id}"
            )
        missing = [dep for dep in stack.depends_on if dep not in seen]
        if missing:
            raise PromptStackError(
                f"fail-closed: stack {stack_id} missing prior dependencies {missing}"
            )

    stack_versions = {stack_id: stacks[stack_id].version for stack_id in requested}
    stack_digests = {stack_id: stacks[stack_id].body_sha256 for stack_id in requested}
    stack_releases = {stack_id: stacks[stack_id].release_id for stack_id in requested}
    registry = _load_registry()
    policy = release_policy(registry)
    body = "\n".join(
        [
            "# UPTM Assembled Prompt",
            f"role: {role}",
            "wave_context:",
            json.dumps(wave_context, sort_keys=True, separators=(",", ":"), ensure_ascii=True),
            "",
            *[
                (
                    f"<!-- stack:{stack.id} version:{stack.version} "
                    f"sha256:{stack.body_sha256} -->\n{stack.body}"
                )
                for stack in (stacks[stack_id] for stack_id in requested)
            ],
        ]
    )
    digest_payload = {
        "role": role,
        "stack_ids": list(requested),
        "stack_versions": stack_versions,
        "stack_digests": stack_digests,
        "stack_releases": stack_releases,
        "registry_sha256": registry_sha256(registry),
        "evidence_expires_at": policy["evidence_expires_at"],
        "stale_on": list(policy["stale_on"]),
        "wave_context": wave_context,
        "body_sha256": digest_text(body),
    }
    digest = hashlib.sha256(
        json.dumps(digest_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return AssembledPrompt(
        role=role,
        stack_ids=requested,
        stack_versions=stack_versions,
        stack_digests=stack_digests,
        stack_releases=stack_releases,
        registry_sha256=registry_sha256(registry),
        evidence_expires_at=policy["evidence_expires_at"],
        stale_on=policy["stale_on"],
        wave_context=dict(wave_context),
        body=body,
        digest=digest,
    )


def validate_prompt_stack_binding(evidence: dict[str, Any]) -> list[str]:
    """Validate mandatory evidence binding to the prompt stack source."""
    binding = evidence.get("prompt_stack")
    if binding is None:
        return ["prompt_stack binding required"]
    if not isinstance(binding, dict):
        return ["prompt_stack binding must be an object"]

    required = (
        "role",
        "stack_ids",
        "stack_versions",
        "stack_digests",
        "stack_releases",
        "registry_sha256",
        "assembled_prompt_digest",
        "evidence_expires_at",
        "stale_on",
    )
    missing = [key for key in required if key not in binding]
    if missing:
        return [f"prompt_stack missing field: {key}" for key in missing]

    try:
        stack_ids = tuple(str(stack_id) for stack_id in binding["stack_ids"])
        wave_context = binding.get("wave_context") or {"wave_id": evidence.get("wave_id")}
        assembled = assemble_prompt(stack_ids, str(binding["role"]), wave_context)
    except PromptStackError as exc:
        return [str(exc)]

    errors: list[str] = []
    if binding.get("stack_versions") != assembled.stack_versions:
        errors.append("prompt_stack stack_versions mismatch")
    if binding.get("stack_digests") != assembled.stack_digests:
        errors.append("prompt_stack stack_digests mismatch")
    if binding.get("stack_releases") != assembled.stack_releases:
        errors.append("prompt_stack stack_releases mismatch")
    if binding.get("registry_sha256") != assembled.registry_sha256:
        errors.append("prompt_stack registry_sha256 mismatch")
    if binding.get("assembled_prompt_digest") != assembled.digest:
        errors.append("prompt_stack assembled_prompt_digest mismatch")
    if binding.get("evidence_expires_at") != assembled.evidence_expires_at:
        errors.append("prompt_stack evidence_expires_at mismatch")
    if tuple(binding.get("stale_on") or ()) != assembled.stale_on:
        errors.append("prompt_stack stale_on mismatch")
    return errors
