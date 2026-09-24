# Cursor execution handoff

Cursor may not be callable from the Runner host. The `CursorExecutor` interface
defines the contract; `NullCursorExecutor` **fails closed** on `dispatch()` when
unconfigured.

## How to proceed without in-process Cursor

1. Validate a `SwarmDispatch` claim ledger.
2. Call `NullCursorExecutor.handoff_swarm(dispatch, branch=..., commit_sha=...)`
   to get one `CursorHandoff` per claim. Each handoff uses the APS-004 skeleton
   path and carries `prompt_stack` plus `swarm_claim` metadata.
3. Optionally pass `write_root` to persist those skeletons.
4. Run Cursor agents externally (≤ 8 parallel), one agent per claim.
5. Replace SKIPPED skeletons under `evidence/waveN/` with real probes and
   `files` entries whose sha256 matches the tree.
6. Run `SwarmDispatch.collect_and_verify_dir(root)`, or pass the same ledger
   and artifacts into `RunnerFSM.apply_gate` / `run_until_terminal(swarm_provider=...)`.
   A missing claim, a leftover skeleton, all-`SKIPPED` probes, a different
   prompt-stack digest, or an `evaluate_gate` failure (including a file binding
   that is not CURRENT) fails the wave and does not record `passed_waves`.
7. Run `uptm-runner evaluate-gate --evidence <path>` on each collected artifact.

Single-task `handoff(task)` remains as the documented one-agent fallback.

## Forbidden

- Stubbing `dispatch()` to return COMPLETED without a real Cursor integration.
- Treating agent chat PASS as gate PASS.
