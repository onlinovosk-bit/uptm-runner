# STACK 04 — Parallel Dispatch

**Objective:** Dispatch ≤ 8 Cursor agents (or stubs) for the current wave via the execution contract.

## Rules
- Fail closed if Cursor adapter not configured.
- Do not fake successful agent runs.
- Each dispatch must produce an evidence skeleton with required fields.
