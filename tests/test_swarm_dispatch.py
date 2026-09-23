from __future__ import annotations

import pytest

from ruflo.adapter import (
    RufloUnavailableError,
    SwarmDispatch,
    SwarmDispatchError,
    SwarmWorkClaim,
    get_adapter,
)


def _claim(agent_id: str, paths: tuple[str, ...], *, wave_id: int = 2) -> SwarmWorkClaim:
    return SwarmWorkClaim(
        agent_id=agent_id,
        wave_id=wave_id,
        role="executor",
        stack_ids=("00", "04"),
        owned_paths=paths,
        lease_id=f"lease-{agent_id}",
        lease_expires_at="2026-09-23T21:00:00Z",
        evidence_skeleton_path=f"evidence/wave{wave_id}/{agent_id}.json",
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


def test_parallel_claim_crossing_wave_rejected():
    dispatch = SwarmDispatch(
        wave_id=2,
        claims=(_claim("agent-a", ("runner/fsm.py",), wave_id=3),),
    )
    with pytest.raises(SwarmDispatchError, match="crosses wave boundary"):
        dispatch.validate()


def test_parallel_max_agents_rejected():
    claims = tuple(_claim(f"agent-{i}", (f"owned/{i}.txt",)) for i in range(9))
    dispatch = SwarmDispatch(wave_id=2, claims=claims)
    with pytest.raises(SwarmDispatchError, match="claim count exceeds"):
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
