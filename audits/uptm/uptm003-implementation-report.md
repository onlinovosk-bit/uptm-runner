# UPTM-003 — P8 Independent Kill Switch: implementation report

Branch `uptm-003-kill-switch` from `main` (`c9ae2aa`). One wall. No other
principle was touched, and UPTM-004 (P10, validation capital) is not started.

## A. Files changed

| File | Change |
|---|---|
| `docs/specs/UPTM-003-kill-switch.md` | new — preregistration, prose |
| `docs/specs/UPTM-003-kill-switch.json` | new — preregistration, machine-readable |
| `runner/detectors/kill_switch.py` | new — the detector |
| `runner/detectors/__init__.py` | `CheckOutcome`, `worst`, `worst_verdict` moved here |
| `runner/detectors/fabrication.py` | imports those three instead of defining them |
| `runner/gates.py` | `run_kill_switch_detector`, `apply_ks_g1`, wiring in `evaluate_gate` |
| `runner/paths.py` | `SPECS`, `UPTM003_SPEC` |
| `constitution/capital-rules.json` | cadence, re-verification triggers, P8, status, `uptm003_detector` |
| `tests/test_kill_switch_detector.py` | new — 40 preregistered acceptance cases |
| `tests/test_kill_switch_invocation.py` | new — spy, disconnection, mutation, malformed shapes |
| `tests/test_uptm003_preregistration.py` | new — preregistration integrity |

## B. What was built

Ten checks. Nine live in the detector; KS-G1 lives in the gate because its input
is the gate's own composed verdict.

The stop state is read **exactly once** per evaluation, bracketed by a digest on
either side. This was not the first design: the first one let KS-S1 read the file
and KS-S2 read it again, and acceptance case MUT-03 (a reader that writes) passed
when it should have failed — the first read had already made the change, so the
second read's digests matched. The single bracketed read is what MUT-03 forced,
and `test_the_stop_state_is_read_exactly_once` now pins it.

`ENGAGED` plus an otherwise-passing gate is `gate_bypass_attempt`: a gate cannot
answer PASS while the system is stopped. `ENGAGED` while the gate already denies
is reported and accuses nobody — no permission was granted, so none was bypassed.

A declared drill verdict without a recorded transition is
`evidence_forgery_detected`. An *absent* transition with no declared verdict is
UNKNOWN. The difference is the claim, not the gap — which is why KS-D5 is its own
check and "missing parameter ⇒ UNKNOWN" survives as a rule without exceptions.

## C. What was deliberately not built

Deployment independence is **not certified by code**, by founder decision.
Whether the kill switch runs outside the runner's process, credentials and
topology is an operator attestation carrying a date (KS-D4). The detector checks
that an attestation exists, is dated, and does not predate the last relevant
change. It cannot check that it is true.

Four further limits are recorded in the spec and in `capital-rules.json`:
`attestation_is_a_human_claim`, `declared_write_paths_only`,
`drill_is_self_reported`, `omission_bypass_outside_live_claim`.

## D. Cadence

`live_capability.kill_switch_drill_cadence_days = 14`, read by the gate from the
governance artifact — not a constant in code. A corrupted or absent cadence
yields UNKNOWN, never "no limit".

The window is not the only trigger. A change to `deployment_ref`,
`credentials_ref`, `kill_switch_path_digest` or `gate_path_digest` invalidates
the drill immediately, however recent it was (KS-D3).

## E. Status change

`P8: DECLARATIVE → PARTIAL`. `gate_bypass_attempt: DECLARATIVE → PARTIAL`.
`ENFORCED 0 / PARTIAL 8 / DECLARATIVE 1 / MISSING 5`.

`PARTIAL` is the ceiling under this preregistration and
`upgrade_by_green_tests_forbidden` is `true`. No quantity of green tests moves
P8 to `ENFORCED`; that needs all four of
`deployment_independence_certified_out_of_band`,
`undeclared_write_path_detection`, `drill_transition_externally_witnessed`,
`no_omission_bypass`.

The status was changed **after** the suite was green, not alongside it.

## F. Proof that the wall is load-bearing

- **Spy** — `test_gate_actually_calls_the_kill_switch_detector` asserts a real
  `evaluate_gate` call reaches the detector, with the pack and the cadence read
  from `capital-rules.json`.
- **Disconnection** — `test_gate_verdict_depends_on_what_the_detector_returns`:
  stub the detector to PASS and a denying gate passes. The gate is not computing
  this somewhere else.
- **Mutation** — for all eleven detector-owned mutations and for KS-G1,
  `test_removing_the_detector_changes_the_gate_verdict_for_every_mutation`
  asserts the mutation is caught *and* that removing the detector stops it being
  caught. A detector whose removal changes nothing enforces nothing.
- **Malformed shapes** — a `kill_switch` that is not a pack, a detector that
  raises, an uninterpretable cadence: each resolves to UNKNOWN and DENY. A crash
  is not a verdict.

## G. Tests

`python3 -m pytest` → **236 passed**. 134 before this branch, 102 added.
No pre-existing test was modified.
