# STACK 01 — Discover

**Objective:** Inventory UPTM repo state, open PRs, audit artifacts, and Runner constraints without mutating UPTM.

## Inputs
- Target repo metadata (read-only)
- `audits/baseline/wave0_baseline.json`
- Prior audit reports under `audits/uptm/`

## Required actions
1. Confirm `live_trading=false` in baseline and constitution.
2. List PR #1–#4 statuses from baseline (do not invent).
3. Confirm PR #4 is `claims_unverified` / not mergeable.
4. Confirm max agents ≤ 8.

## Outputs
- Discovery inventory JSON under `evidence/wave0/`
- Explicit statement: no UPTM mutations performed

## Forbidden
- Merging PRs
- Enabling live trading
- Fabricating audit results
