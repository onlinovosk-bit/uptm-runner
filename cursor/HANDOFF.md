# Cursor execution handoff

Cursor may not be callable from the Runner host. The `CursorExecutor` interface
defines the contract; `NullCursorExecutor` **fails closed** on `dispatch()` when
unconfigured.

## How to proceed without in-process Cursor

1. Call `NullCursorExecutor.handoff(task)` to get instructions + evidence skeleton path.
2. Run Cursor agents externally (≤ 8 parallel).
3. Deposit schema-valid evidence under `evidence/waveN/` with real probes.
4. Run `uptm-runner evaluate-gate --evidence <path>`.

## Forbidden

- Stubbing `dispatch()` to return COMPLETED without a real Cursor integration.
- Treating agent chat PASS as gate PASS.
