# UPTM audit knowledge (copied into Runner)

Source files mirrored from `/workspace` at scaffold time:

| File | Origin |
|------|--------|
| `audit-pr1.md` | `/workspace/uptm-audit-report.md` (PR #1 adversarial audit) |
| `audit-pr2.md` | `/workspace/uptm-audit-pr2.md` |
| `audit-pr3.md` | `/workspace/uptm-audit-pr3.md` (CRITICAL coordinated forgery confirmed) |
| `pr3-implementation-report.md` | `/workspace/uptm-pr3-report.md` |
| `pr4-implementation-report.md` | `/workspace/uptm-pr4-report.md` (claims = HYPOTHESIS) |
| `audit-pr16` | UPTM tip PR #16: CLEAR FOR MEDIUM/LOW ONLY; residuals accepted in baseline |

Machine-readable consolidation: `audits/baseline/wave0_baseline.json`.

**Runner policy:** Runner must not auto-merge any UPTM PR. UPTM tip PR #16 is CLEAR FOR MEDIUM/LOW ONLY per audit #16, but any UPTM merge still requires a machine gate: CRITICAL=0, HIGH=0, tests pass, adversarial tests pass, CI passes, and invariants hold. Live trading remains false.
