"""
Ruflo adapter boundary.

Ruflo may be unavailable. Orchestration must work through Runner FSM alone.
This module defines the adapter interface + a stub that reports unavailable.
Do NOT fake Ruflo connectivity.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
from collections.abc import Mapping
from pathlib import Path, PurePosixPath
from typing import Any

from runner.prompt_stacks import PromptStackError, assemble_prompt


class RufloUnavailableError(RuntimeError):
    """Ruflo not available; callers must use local orchestration."""


class SwarmDispatchError(ValueError):
    """Swarm dispatch contract rejected an unsafe fanout."""


@dataclass(frozen=True)
class OrchestrationEvent:
    kind: str
    payload: dict[str, Any]


@dataclass(frozen=True)
class SwarmWorkClaim:
    agent_id: str
    wave_id: int
    role: str
    stack_ids: tuple[str, ...]
    owned_paths: tuple[str, ...]
    lease_id: str
    lease_expires_at: str
    evidence_skeleton_path: str

    def evidence_skeleton(
        self, *, branch: str, commit_sha: str, pr: int | None = None
    ) -> dict[str, Any]:
        return evidence_skeleton_for_claim(self, branch=branch, commit_sha=commit_sha, pr=pr)

    def evidence_skeleton_json(
        self, *, branch: str, commit_sha: str, pr: int | None = None
    ) -> str:
        return evidence_skeleton_json(self, branch=branch, commit_sha=commit_sha, pr=pr)


@dataclass(frozen=True)
class SwarmDispatch:
    wave_id: int
    claims: tuple[SwarmWorkClaim, ...]
    max_parallel_agents: int = 8
    allow_single_threaded_cursor_handoff: bool = True

    def validate(self) -> None:
        if not self.claims:
            raise SwarmDispatchError("fail-closed: swarm dispatch has no claims")
        if self.max_parallel_agents < 1:
            raise SwarmDispatchError("fail-closed: max_parallel_agents must be positive")
        if self.max_parallel_agents > 8:
            raise SwarmDispatchError("fail-closed: max_parallel_agents exceeds 8")
        if len(self.claims) > self.max_parallel_agents:
            raise SwarmDispatchError("fail-closed: claim count exceeds max_parallel_agents")

        ownership: dict[PurePosixPath, str] = {}
        agent_ids: set[str] = set()
        lease_ids: set[str] = set()
        for claim in self.claims:
            if not claim.agent_id:
                raise SwarmDispatchError("fail-closed: agent_id required")
            if claim.agent_id in agent_ids:
                raise SwarmDispatchError(f"fail-closed: duplicate agent_id {claim.agent_id!r}")
            agent_ids.add(claim.agent_id)
            if claim.wave_id != self.wave_id:
                raise SwarmDispatchError("fail-closed: claim crosses wave boundary")
            if not claim.lease_id:
                raise SwarmDispatchError("fail-closed: work claim lease fields required")
            if claim.lease_id in lease_ids:
                raise SwarmDispatchError(f"fail-closed: duplicate lease_id {claim.lease_id!r}")
            lease_ids.add(claim.lease_id)
            _parse_lease_expiry(claim.lease_expires_at)
            _validate_prompt_envelope(claim)
            _validate_evidence_skeleton_path(claim)
            normalized_paths = _normalize_owned_paths(claim)
            for path in normalized_paths:
                for owned, owner in ownership.items():
                    if _paths_overlap(path, owned) and owner != claim.agent_id:
                        raise SwarmDispatchError(
                            f"fail-closed: ownership conflict for {str(path)!r}"
                        )
                ownership[path] = claim.agent_id

    def evidence_skeletons(
        self, *, branch: str, commit_sha: str, pr: int | None = None
    ) -> tuple[dict[str, Any], ...]:
        self.validate()
        return tuple(
            claim.evidence_skeleton(branch=branch, commit_sha=commit_sha, pr=pr)
            for claim in self.claims
        )

    def write_evidence_skeletons(
        self,
        *,
        root: Path,
        branch: str,
        commit_sha: str,
        pr: int | None = None,
    ) -> tuple[Path, ...]:
        self.validate()
        written: list[Path] = []
        for claim in self.claims:
            path = Path(root) / claim.evidence_skeleton_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                claim.evidence_skeleton_json(branch=branch, commit_sha=commit_sha, pr=pr),
                encoding="utf-8",
            )
            written.append(path)
        return tuple(written)

    def collect_and_verify(
        self, artifacts: Mapping[str, Mapping[str, Any]]
    ) -> SwarmCollectResult:
        """Require one real evidence artifact per claim before the wave can pass."""
        self.validate()
        reasons: list[str] = []
        paths = [claim.evidence_skeleton_path for claim in self.claims]
        if len(set(paths)) != len(paths):
            reasons.append("fail-closed: duplicate evidence skeleton path")
        unexpected = sorted(set(artifacts) - set(paths))
        if unexpected:
            reasons.append(f"fail-closed: unexpected evidence {unexpected}")
        for claim in self.claims:
            artifact = artifacts.get(claim.evidence_skeleton_path)
            if not isinstance(artifact, Mapping):
                reasons.append(f"fail-closed: missing evidence for {claim.agent_id}")
                continue
            reasons.extend(_verify_collected_claim(claim, dict(artifact)))
        return SwarmCollectResult(
            wave_id=self.wave_id,
            passed=not reasons,
            reasons=tuple(reasons),
        )

    def collect_and_verify_dir(self, root: Path) -> SwarmCollectResult:
        self.validate()
        artifacts: dict[str, dict[str, Any]] = {}
        reasons: list[str] = []
        for claim in self.claims:
            path = Path(root) / claim.evidence_skeleton_path
            if not path.is_file():
                continue
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                reasons.append(
                    f"fail-closed: unreadable evidence for {claim.agent_id}: {exc}"
                )
                continue
            if isinstance(payload, dict):
                artifacts[claim.evidence_skeleton_path] = payload
            else:
                reasons.append(f"fail-closed: evidence for {claim.agent_id} must be an object")
        result = self.collect_and_verify(artifacts)
        if not reasons:
            return result
        return SwarmCollectResult(
            wave_id=self.wave_id,
            passed=False,
            reasons=tuple(reasons) + result.reasons,
        )


def _parse_relative_path(raw: str, *, field: str) -> PurePosixPath:
    if not raw:
        raise SwarmDispatchError(f"fail-closed: {field} required")
    path = PurePosixPath(raw)
    if path.is_absolute() or any(part in ("", ".", "..") for part in path.parts):
        raise SwarmDispatchError(f"fail-closed: unsafe {field} {raw!r}")
    return path


def _paths_overlap(left: PurePosixPath, right: PurePosixPath) -> bool:
    return left == right or left in right.parents or right in left.parents


def _parse_lease_expiry(raw: str) -> None:
    if not raw:
        raise SwarmDispatchError("fail-closed: work claim lease fields required")
    try:
        datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SwarmDispatchError("fail-closed: lease_expires_at must be ISO-8601") from exc


def _validate_prompt_envelope(claim: SwarmWorkClaim) -> None:
    try:
        assemble_prompt(
            claim.stack_ids,
            claim.role,
            {"wave_id": claim.wave_id, "agent_id": claim.agent_id},
        )
    except PromptStackError as exc:
        raise SwarmDispatchError(str(exc)) from exc


def _validate_evidence_skeleton_path(claim: SwarmWorkClaim) -> None:
    path = _parse_relative_path(claim.evidence_skeleton_path, field="evidence skeleton path")
    expected_prefix = PurePosixPath("evidence") / f"wave{claim.wave_id}"
    if expected_prefix not in (path, *path.parents):
        raise SwarmDispatchError(
            f"fail-closed: evidence skeleton path must live under {expected_prefix}"
        )
    if path.suffix != ".json":
        raise SwarmDispatchError("fail-closed: evidence skeleton path must be json")


def _normalize_owned_paths(claim: SwarmWorkClaim) -> tuple[PurePosixPath, ...]:
    if not claim.owned_paths:
        raise SwarmDispatchError("fail-closed: owned_paths required")
    normalized: list[PurePosixPath] = []
    seen: set[PurePosixPath] = set()
    for raw in claim.owned_paths:
        path = _parse_relative_path(raw, field="owned path")
        if path in seen:
            raise SwarmDispatchError(f"fail-closed: duplicate owned path {str(path)!r}")
        for existing in normalized:
            if _paths_overlap(path, existing):
                raise SwarmDispatchError(
                    f"fail-closed: overlapping owned_paths inside claim for {str(path)!r}"
                )
        seen.add(path)
        normalized.append(path)
    return tuple(normalized)


def _digest_payload(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _claim_metadata(claim: SwarmWorkClaim) -> dict[str, Any]:
    owned_paths = tuple(str(path) for path in _normalize_owned_paths(claim))
    _parse_lease_expiry(claim.lease_expires_at)
    _validate_evidence_skeleton_path(claim)
    _validate_prompt_envelope(claim)
    return {
        "agent_id": claim.agent_id,
        "wave_id": claim.wave_id,
        "role": claim.role,
        "stack_ids": list(claim.stack_ids),
        "owned_paths": list(owned_paths),
        "lease_id": claim.lease_id,
        "lease_expires_at": claim.lease_expires_at,
        "evidence_skeleton_path": claim.evidence_skeleton_path,
    }


def evidence_skeleton_for_claim(
    claim: SwarmWorkClaim, *, branch: str, commit_sha: str, pr: int | None = None
) -> dict[str, Any]:
    """Create deterministic, gate-shaped skeleton evidence for one work claim.

    The skeleton is intentionally not passing evidence: probes are SKIPPED and
    the claim is PARTIAL until a real agent run replaces placeholders.
    """
    if not branch or not commit_sha:
        raise SwarmDispatchError("fail-closed: branch and commit_sha required")
    claim_metadata = _claim_metadata(claim)
    claim_digest = _digest_payload(claim_metadata)
    prompt_stack = assemble_prompt(
        claim.stack_ids,
        claim.role,
        {"wave_id": claim.wave_id, "agent_id": claim.agent_id},
    )
    return {
        "evidence_id": f"swarm-skeleton-wave{claim.wave_id}-{claim.agent_id}-{claim.lease_id}",
        "wave_id": claim.wave_id,
        "commit_sha": commit_sha,
        "branch": branch,
        "pr": pr,
        "files": [],
        "commands": [
            {
                "cmd": "SWARM_CLAIM_NOT_EXECUTED",
                "exit_code": 1,
                "stdout_digest": claim_digest,
            }
        ],
        "results": {
            "passed": 0,
            "failed": 1,
            "findings": [
                {
                    "id": "APS-SKELETON-NOT-EVIDENCE",
                    "severity": "INFO",
                    "status": "OPEN",
                }
            ],
        },
        "probes": [
            {
                "probe_id": "swarm_claim_skeleton_unexecuted",
                "outcome": "SKIPPED",
                "output_digest": claim_digest,
            }
        ],
        "before": {"digest": claim_digest, "summary": "swarm claim skeleton"},
        "after": {"digest": claim_digest, "summary": "awaiting agent execution"},
        "agent_claim": {
            "verdict": "PARTIAL",
            "notes": "Skeleton only; not execution evidence and not a gate PASS.",
        },
        "live_trading": False,
        "prompt_stack": prompt_stack.cursor_metadata(),
        "scope": {"capital_bearing": False, "live_bearing": False},
        "signature": None,
        "swarm_claim": claim_metadata,
        "skeleton": True,
    }


def evidence_skeleton_json(
    claim: SwarmWorkClaim, *, branch: str, commit_sha: str, pr: int | None = None
) -> str:
    skeleton = evidence_skeleton_for_claim(claim, branch=branch, commit_sha=commit_sha, pr=pr)
    return json.dumps(skeleton, sort_keys=True, indent=2, ensure_ascii=True) + "\n"


def _verify_collected_claim(claim: SwarmWorkClaim, artifact: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    prefix = f"{claim.agent_id}:"
    if artifact.get("skeleton") is True:
        reasons.append(f"{prefix} evidence is still a skeleton")
    probes = artifact.get("probes") or []
    if not isinstance(probes, list) or not probes or all(
        isinstance(probe, Mapping) and probe.get("outcome") == "SKIPPED" for probe in probes
    ):
        reasons.append(f"{prefix} probes missing or all SKIPPED")
    expected = assemble_prompt(
        claim.stack_ids,
        claim.role,
        {"wave_id": claim.wave_id, "agent_id": claim.agent_id},
    )
    binding = artifact.get("prompt_stack")
    if not isinstance(binding, Mapping):
        reasons.append(f"{prefix} prompt_stack binding required")
    else:
        if binding.get("assembled_prompt_digest") != expected.digest:
            reasons.append(f"{prefix} prompt_stack digest mismatch")
        if binding.get("role") != claim.role or list(binding.get("stack_ids") or []) != list(
            claim.stack_ids
        ):
            reasons.append(f"{prefix} prompt_stack role or stacks mismatch")
    recorded = artifact.get("swarm_claim")
    if isinstance(recorded, Mapping):
        if recorded.get("agent_id") != claim.agent_id or recorded.get("lease_id") != claim.lease_id:
            reasons.append(f"{prefix} swarm_claim identity mismatch")
    from runner.gates import evaluate_gate

    gate = evaluate_gate(artifact)
    if not gate.passed:
        reasons.append(f"{prefix} gate FAIL: {'; '.join(gate.reasons)}")
    return reasons


@dataclass(frozen=True)
class SwarmCollectResult:
    wave_id: int
    passed: bool
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class SwarmDispatchResult:
    dispatch: SwarmDispatch
    status: str
    evidence_skeleton_paths: tuple[str, ...]
    detail: str


class RufloAdapter(ABC):
    @abstractmethod
    def available(self) -> bool:
        ...

    @abstractmethod
    def publish(self, event: OrchestrationEvent) -> None:
        ...

    @abstractmethod
    def subscribe(self, topic: str) -> list[OrchestrationEvent]:
        ...

    @abstractmethod
    def dispatch_swarm(self, dispatch: SwarmDispatch) -> SwarmDispatchResult:
        ...


class NullRufloAdapter(RufloAdapter):
    """Stub: Ruflo unavailable. Local FSM remains source of truth."""

    def available(self) -> bool:
        return False

    def publish(self, event: OrchestrationEvent) -> None:
        raise RufloUnavailableError(
            "Ruflo adapter not configured. Use runner.fsm.RunnerFSM for orchestration. "
            "Refusing to pretend Ruflo accepted the event."
        )

    def subscribe(self, topic: str) -> list[OrchestrationEvent]:
        raise RufloUnavailableError(
            f"Ruflo unavailable; cannot subscribe to {topic!r}. "
            "Use local wave status / evidence collection."
        )

    def dispatch_swarm(self, dispatch: SwarmDispatch) -> SwarmDispatchResult:
        dispatch.validate()
        raise RufloUnavailableError(
            "Ruflo adapter not configured; refusing swarm fanout success. "
            "Use documented single-threaded Cursor handoff if appropriate, and collect "
            "schema-valid evidence skeletons before any gate can pass."
        )


def get_adapter() -> RufloAdapter:
    return NullRufloAdapter()
