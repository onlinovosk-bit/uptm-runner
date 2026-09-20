# UPTM Runner Trust Model

## Purpose

Runner is a **control-plane** around UPTM. It exists because agent self-reports and
local UPTM “integrity” checks have been shown insufficient (audits PR1–PR3 found
CRITICAL coordinated DB+key+receipt forgery among other HIGH issues).

## Harder to fool than agents

| Claim | Mechanism |
|------|-----------|
| Agent PASS alone never gates | `runner.gates.evaluate_gate` requires probes, results, before/after digests |
| Missing evidence fails closed | `evaluate_gate(None)` → FAIL |
| Severity downgrade detected | `V-CRIT*` / `true_severity` / `hidden_as` heuristics |
| Wave skip blocked | `RunnerFSM.assert_wave_unlocked` / unlocked set |
| Patch spam limited | max 3 attempts/cluster → `HUMAN_REVIEW_REQUIRED` |
| Live trading | constitution + baseline + evidence `const false` + stop conditions |

## What Runner does **not** claim

- **No immutability** for Runner state when it lives only on this local disk.
  Evidence under `evidence/` can be edited by anyone with filesystem write access.
- Runner does not replace an external WORM/HSM anchor for UPTM ledgers.
- Cursor and Ruflo stubs are **not** integrations; they fail closed / report unavailable.

## UPTM PR posture

- UPTM tip PR #16 is recorded as **CLEAR FOR MEDIUM/LOW ONLY** by audit #16, with accepted residuals documented in `audits/baseline/wave0_baseline.json`.
- Runner **MUST NOT** auto-merge PR #16 or any UPTM PR. `auto_merge=false`; a machine gate requires CRITICAL=0, HIGH=0, tests, adversarial tests, CI, and invariants.
- PR #4 (`cursor/pr4-audit-trust-hardening-0444`) claims are retained as historical **HYPOTHESIS** in the baseline.
- Prior audits through PR #3 remain the last **independently confirmed** vulnerability set until a fourth audit completes.

## Live trading

`live_trading=false` everywhere. Any enablement attempt is a stop condition.
