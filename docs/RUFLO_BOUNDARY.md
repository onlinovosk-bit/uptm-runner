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

`NullRufloAdapter.available() == False`. `publish` / `subscribe` raise
`RufloUnavailableError`. No silent no-op success.

## Integrating a real Ruflo later

1. Implement `RufloAdapter`.
2. Wire `ruflo.get_adapter()` to return it only when credentials/endpoint exist.
3. Keep FSM transitions authoritative; Ruflo events are observations, not gate substitutes.
