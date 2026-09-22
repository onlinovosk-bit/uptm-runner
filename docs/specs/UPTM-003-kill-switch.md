# UPTM-003 — P8 Independent Kill Switch

**Status:** PREREGISTERED. Written before `runner/detectors/kill_switch.py` existed,
so the acceptance criteria cannot drift once evidence starts arriving (CC/P4).

Machine-readable twin: `UPTM-003-kill-switch.json`. Where the two disagree, the
JSON is authoritative — the tests read it, not this file.

## What P8 requires

> The Runner cannot disable, bypass or modify the mechanism that stops it. An
> untested kill switch does not exist — a periodic drill is a condition of LIVE
> validity.
>
> — `constitution/CONSTITUTION-CAPITAL.md` §P8

Two failure modes follow: a switch the runner can reach, and a switch nobody has
ever pressed. This specification covers both, and is explicit about the third —
physical separation — which it does **not** cover.

## What these checks claim

They never report that a kill switch is independent. They report that:

- the stop state is readable and resolves to exactly one declared state,
- reading it does not change it,
- the runner declares no write path to it,
- a drill with a demonstrated before/after transition happened inside the
  cadence, and has not been invalidated by a relevant change,
- an operator has attested physical separation, with a date.

**Deployment independence is not certified by code.** Whether the kill switch
actually runs outside the runner's process, credentials and topology is an
operator attestation carrying a date. A detector that claimed otherwise would be
asserting a fact about infrastructure from inside the thing it distrusts.

## Verdicts

`PASS` / `FAIL` / `UNKNOWN`, resolved only through `runner.verdict.resolve`.
A missing preregistered parameter is `UNKNOWN`, never a default — an assumed
`DISENGAGED` would be exactly the silent permission GOVERNANCE.md C3 forbids.

`UNKNOWN` ⇒ LIVE DENY. It denies without accusing.

## The checks

| # | Layer | Stop condition | Property |
|---|---|---|---|
| KS-P1 | DECLARATION | `gate_bypass_attempt` | The pack declares the five fields the other checks read |
| KS-S1 | STOP_STATE | `gate_bypass_attempt` | Stop state is readable and determinate |
| KS-S2 | STOP_STATE | `gate_bypass_attempt` | Reading the stop state does not change it |
| KS-S3 | INDEPENDENCE | `gate_bypass_attempt` | Runner declares no write path to the stop state |
| KS-D1 | DRILL | `evidence_forgery_detected` | Last drill is within the cadence |
| KS-D2 | DRILL | `evidence_forgery_detected` | Drill records a real before/after transition ending in `ENGAGED` |
| KS-D3 | DRILL | `evidence_forgery_detected` | Drill invalidated by a relevant change |
| KS-D4 | ATTESTATION | `evidence_forgery_detected` | Operator attestation exists and post-dates the last change |
| KS-D5 | DRILL | `evidence_forgery_detected` | A declared drill verdict is substantiated by the transition |
| KS-G1 | GATE_COMPOSITION | `gate_bypass_attempt` | `ENGAGED` + an otherwise-`PASS` gate is a bypass attempt |

KS-G1 is evaluated in `runner.gates.evaluate_gate`, over the composed verdict of
every other contribution. It is the one check that cannot live in the detector,
because its input is the gate's own result.

KS-D5 exists so that "missing parameter ⇒ UNKNOWN" stays a rule without
exceptions. An absent transition is UNKNOWN (KS-D2); an absent transition
*under a declared PASS* is forgery (KS-D5). The claim is what makes the
difference, not the gap.

## Cadence and re-verification

`live_capability.kill_switch_drill_cadence_days = 14`.

The window is not the only trigger. A drill is required again — immediately, and
regardless of how recent it was — after a change to any of:

- `deployment_ref`
- `credentials_ref`
- `kill_switch_path_digest`
- `gate_path_digest`

A drill performed against a deployment that no longer exists proves nothing about
the one that does.

## Declared limits

Written down before implementation, so that no later report can imply the wall is
taller than it is.

1. **`deployment_independence_not_certified_by_code`** — physical and topological
   separation is an operator attestation with a date. No check here proves it.
2. **`attestation_is_a_human_claim`** — KS-D4 verifies an attestation exists and
   is not stale. It cannot verify that it is true.
3. **`declared_write_paths_only`** — KS-S3 reads a declaration. An undeclared
   write path is not detected.
4. **`drill_is_self_reported`** — KS-D2 verifies a transition was recorded and is
   internally consistent, not that a human physically engaged the switch.
5. **`omission_bypass_outside_live_claim`** — evidence that neither sets
   `live_capability_claim` nor carries a `kill_switch` pack never reaches the
   detector. Under a LIVE claim an absent pack resolves to `UNKNOWN`, so the
   omission is closed on the path P8 protects and open everywhere else.

## Ceiling

`target_capability: PARTIAL`. `upgrade_by_green_tests_forbidden: true`.

P8 may not be recorded as `ENFORCED` under this preregistration at any level of
test greenness. Reaching `ENFORCED` requires all four of:

- `deployment_independence_certified_out_of_band`
- `undeclared_write_path_detection`
- `drill_transition_externally_witnessed`
- `no_omission_bypass`

## Acceptance cases

40 cases in the JSON: 13 `must_fail` mutations, 20 `must_unknown` (one per
required parameter of every check), 7 `must_pass` false-positive guards.

A green suite is evidence that the detector implements this specification. It is
not evidence that P8 holds.
