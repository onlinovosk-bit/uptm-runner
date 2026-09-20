# STACK 05 — Verify

**Objective:** Deterministic verification from evidence artifacts.

## Rules
- Ignore agent PASS without probes + results + before/after digests.
- CRITICAL hidden as warning → treat as CRITICAL (adversarial).
- Missing evidence → gate FAIL (fail closed).
