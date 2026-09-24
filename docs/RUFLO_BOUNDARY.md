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

Ruflo fanout is never gate evidence.

## Integrating a real Ruflo later

1. Implement `RufloAdapter`.
2. Wire `ruflo.get_adapter()` to return it only when credentials/endpoint exist.
3. Keep FSM transitions authoritative; Ruflo events are observations, not gate substitutes.
