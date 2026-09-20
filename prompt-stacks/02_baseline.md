# STACK 02 — Baseline

**Objective:** Lock Wave 0 baseline as the sole machine-readable source of known UPTM risk.

## Inputs
- STACK 01 discovery
- `audits/baseline/wave0_baseline.json`

## Required actions
1. Validate baseline JSON against Runner expectations.
2. Record known CRITICAL/HIGH from audits 1–3 as OPEN unless independently re-verified.
3. Mark all PR4 claims as `HYPOTHESIS`.

## Outputs
- Baseline digest + acknowledgment evidence

## Exit
- Baseline loaded; `live_trading=false` confirmed
