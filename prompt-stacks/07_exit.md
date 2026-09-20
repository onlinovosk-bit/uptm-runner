# STACK 07 — Exit Contract

**Objective:** Define wave gate exit and next-state transitions.

## Gate pass requires
- CRITICAL count == 0
- HIGH count == 0
- Evidence schema-valid
- Probes present and not all SKIPPED
- Agent claim alone insufficient
- live_trading == false
- No stop condition triggered

## On pass → NEXT_WAVE (or COMPLETE after wave 7)
## On fail → PATCH_LOOP (if attempts < 3) else HUMAN_REVIEW_REQUIRED
## On stop condition → HUMAN_REVIEW_REQUIRED immediately
