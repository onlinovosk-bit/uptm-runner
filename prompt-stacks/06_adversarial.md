# STACK 06 — Adversarial Verify

**Objective:** Runner-side adversarial checks against forged evidence, fake PASS, wave skip, severity downgrade, probe-less evidence.

## Required adversarial checks
1. Forged evidence signature/digest mismatch
2. Agent PASS without probes
3. Wave skip / non-sequential unlock
4. CRITICAL reported as warning
5. Evidence without probes
6. live_trading true in evidence
