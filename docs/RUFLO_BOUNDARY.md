# Ruflo adapter boundary

## Why an abstraction

Ruflo may be unavailable in this environment. The Runner owns orchestration via
`runner.fsm.RunnerFSM`. Ruflo is an **optional** external bus/adapter.

## Boundary

| Concern | Owner |
|--------|--------|
| Wave sequencing / FSM | `runner.fsm` (required) |
| Gate evaluation | `runner.gates` (required) |
| Evidence schemas | `schemas/` (required) |
| Multi-agent fanout bus | Ruflo adapter (optional) |

## Stub behavior

`NullRufloAdapter.available() == False`. `publish` / `subscribe` /
`dispatch_swarm` raise `RufloUnavailableError`. No silent no-op success.

`SwarmDispatch` is a contract only. It validates the claim ledger before any
adapter can attempt fanout:

- max 8 parallel agents
- one wave per dispatch
- unique `agent_id` and `lease_id`
- ISO-8601 lease expiry field present
- non-overlapping file ownership, including parent/child path overlap
- role/stack envelope accepted by the prompt-stack composer
- evidence skeleton path under `evidence/waveN/*.json`

`SwarmDispatch.evidence_skeletons()` / `write_evidence_skeletons()` emit
deterministic, gate-shaped JSON for each claim. The skeleton binds
`prompt_stack`, lease metadata, and `owned_paths`. Probes are `SKIPPED` and
`agent_claim.verdict` is `PARTIAL`, so a skeleton cannot pass a gate.

`SwarmDispatch.collect_and_verify()` closes the loop. The wave passes only when
every claim has exactly one collected artifact, that artifact is not a
skeleton, its probes are not all `SKIPPED`, its `prompt_stack` digest matches
the claim's assembled prompt, and `evaluate_gate` passes. A missing claim
fails the wave. An artifact that declares no files fails the gate as binding
UNKNOWN.

`RunnerFSM.apply_gate` calls that collect when a `SwarmDispatch` is bound to
the current wave, and writes `passed_waves` only if the collect passes and the
gate is PASS with `CRITICAL=0` and `HIGH=0`. `run_until_terminal` forwards a
`swarm_provider` into that call. A ledger for a different wave denies.

Ruflo fanout is never gate evidence.

## Integrating a real Ruflo later

1. Implement `RufloAdapter`.
2. Wire `ruflo.get_adapter()` to return it only when credentials/endpoint exist.
3. Keep FSM transitions authoritative; Ruflo events are observations, not gate substitutes.
