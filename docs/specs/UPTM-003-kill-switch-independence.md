# UPTM-003 — Preregistered definition: `kill_switch_not_self_clearable`, `kill_switch_drill_valid`

| | |
|---|---|
| Principle | **P8 — Independent Kill Switch** |
| Today | `DECLARATIVE` (`capital-rules.json` `principles[].mechanism: null`) |
| Status of this document | **PREREGISTERED, NOT IMPLEMENTED** |
| Constitution | `constitution/CONSTITUTION-CAPITAL.md` v1.0 (LOCKED) |

Written before evidence collection, as P4 requires. This document does not change
any principle's enforcement state. Only the implementation PR may do that, and only
after the reachability proof in §7 passes.

---

## 0. What this detector claims, and what it does not

P8 states two separable properties:

> The Runner cannot disable, bypass or modify the mechanism that stops it. An untested
> kill switch does not exist — a periodic drill is a condition of LIVE validity.
>
> *Violation:* the kill switch lives inside the Runner process, or LIVE runs without a
> drill performed at the required cadence.

**Claimed.** That the Runner does not clear its own stop, denies when it cannot read
the stop state, and holds a drill that demonstrably stopped something, recently enough,
against a known commit.

**Not claimed.** That the switch is *physically* beyond the Runner's blast radius.
A process cannot certify its own deployment topology: code that proves "I do not write
this path" cannot prove the operator did not place the path on the same host, under the
same credentials, in the same failure domain. That remains an out-of-band Founder
attestation (§6). Treating it as PASS because the code checks passed would be exactly
the illusion P9 forbids.

---

## 1. Verdict model

Identical to UPTM-002. `PASS` = demonstrably satisfied. `FAIL` = demonstrably violated,
may raise a stop condition. `UNKNOWN` = not evaluable from preregistered evidence —
resolves to DENY without asserting a violation, and is never renamed to FAIL so that it
can be recorded as a stop.

Absence is never PASS.

---

## 2. Two packs

| Pack | Evidence key | Governs |
|---|---|---|
| `kill_switch` | `evidence.kill_switch` | the switch itself and the Runner's relationship to it |
| `kill_switch_drill` | `evidence.kill_switch_drill` | the periodic drill that makes the switch real |

Both are evaluated only when LIVE is in question **or** when the evidence carries them.
See §6 on the omission path — UPTM-002 left the same door open and named it; this
document closes it for the LIVE case and names what remains.

---

## 3. `kill_switch_not_self_clearable`

### 3.1 PROVENANCE (hard fail)

| Check | Rule | Verdict |
|---|---|---|
| **KS-P1** | `stop_state.path`, `stop_state.owner` and `stop_state.runner_writable` declared | absent → `UNKNOWN` |
| **KS-P2** | `stop_state.runner_writable` is `false` | `true` → `FAIL` `safety_control_weakening` |

A declaration is not proof; KS-I1 tests it.

### 3.2 INTEGRITY

| Check | Rule | Verdict |
|---|---|---|
| **KS-I1** | No module under `runner/` opens `stop_state.path` for writing, appending or deleting. Evaluated over the repository at the evidence commit, not over a claim. | a write path exists → `FAIL` `safety_control_weakening` |
| **KS-I2** | The stop state is readable at gate time | unreadable, malformed or absent → `UNKNOWN` (P11: uncertainty halts, it does not guess) |
| **KS-I3** | If the stop state reads `ENGAGED`, the gate resolves to DENY regardless of every other input | a `PASS` verdict produced while `ENGAGED` → `FAIL` `gate_bypass_attempt` |
| **KS-I4** | Reading the stop state does not modify it: digest of the artifact before and after evaluation is equal | digests differ → `FAIL` `safety_control_weakening` |

KS-I3 is the check that makes the switch a switch. Without it "engaged" is a label.

---

## 4. `kill_switch_drill_valid`

### 4.1 Declarations required

`cadence_days` (from `capital-rules.json` `live_capability.kill_switch_drill_cadence_days`),
`last_drill_at`, `drill_commit`, `before`, `after`, `artifact_digest`.

### 4.2 Checks

| Check | Rule | Verdict |
|---|---|---|
| **KS-D1** | `cadence_days` is a positive integer | `null` → `UNKNOWN` — **this is the Founder parameter, §8** |
| **KS-D2** | `now - last_drill_at <= cadence_days` | older → `FAIL`; `last_drill_at` absent → `UNKNOWN` |
| **KS-D3** | The drill record shows a transition: `before.state` is running and `after.state` is stopped, each carrying an artifact digest | a record whose only content is a claim (`"drill": "ok"`, a verdict with no before/after) → `FAIL` `evidence_forgery_detected` |
| **KS-D4** | `drill_commit` is present and the declared `stop_state.path` at that commit equals the one in force now | differs or absent → `UNKNOWN` (P12: evidence has commit and expiry) |

KS-D3 mirrors the rule the gate already applies to agent PASS claims: a self-report with
no probes is not evidence. A drill is a probe of the one control that matters most.

---

## 5. Preregistered acceptance criteria

Written now so that the implementation cannot be graded against criteria invented after
its results are known.

### Must return `FAIL`

1. `runner_writable: true`.
2. A module under `runner/` writes the declared stop-state path, while the pack declares `runner_writable: false`.
3. Stop state reads `ENGAGED` and the gate is driven to a `PASS` verdict.
4. The stop-state artifact's digest changes across evaluation.
5. `last_drill_at` older than `cadence_days`.
6. A drill record with a verdict but no `before`/`after` transition.

### Must return `UNKNOWN` — not `PASS`, not `FAIL`

7. `kill_switch_drill_cadence_days` is `null`.
8. Stop state unreadable, or the file is absent.
9. `stop_state.owner` undeclared.
10. `drill_commit` absent, or naming a commit whose stop-state path differs from today's.

Each of these denies. None of them accuses.

### Must return `PASS` — false-positive protection

11. A well-formed pack: `runner_writable: false`, no write path in `runner/`, stop state readable and `CLEAR`, digest stable, drill within cadence with a real before/after transition and a matching commit.
12. A drill performed *more* often than the cadence.
13. A stop state that reads `ENGAGED` **and** a gate that correctly resolves to DENY — the switch working is not a violation. This case exists to stop a naive implementation from treating `ENGAGED` itself as FAIL.

---

## 6. Declared limits — what this will not catch

- **Deployment topology.** As §0 states: co-location, shared credentials, or a stop path on the Runner's own disk are not visible to this detector. Founder attestation, recorded with a date, not a PASS.
- **A drill against a mock.** If the drill exercised a stand-in rather than the real stop path, KS-D3 sees a valid transition. KS-D4 narrows this by pinning the commit; it does not close it.
- **Omission outside LIVE.** Evidence for a non-LIVE gate that carries neither pack is left as the gate treats it today. For LIVE the packs are required and their absence is `UNKNOWN`.
- **Time source.** KS-D2 trusts the clock it is given. A forged `last_drill_at` inside an otherwise consistent pack is not detected here.

---

## 7. Capability outcome and reachability proof

On implementation, P8 moves `DECLARATIVE → ENFORCED` **for the mechanised half only**,
with the topology assertion in §0/§6 recorded as an open limit — not folded into the
claim.

The implementation PR is not complete until, following UPTM-002c:

- the detector is invoked from `runner.gates.evaluate_gate`, and
- `tests/` carries a spy asserting the gate calls it, **and a disconnection test asserting
  the gate's verdict changes when the detector's return value changes.** Import alone
  proves nothing; a mechanism nothing invokes is not enforcement.

`capital-rules.json` records `status`, `invocation_path`, `reachability_proof` and
`open_limits`, as `uptm002_detector` does.

---

## 8. Founder parameter required before this can pass

```
capital-rules.json → live_capability.kill_switch_drill_cadence_days : null → <integer>
```

Not proposed here on purpose. A cadence is a risk appetite, not a derivation, and a
number invented by the agent that wrote the detector is the sourceless number the
UPTM-002 detector exists to catch. Until it is set, KS-D1 returns `UNKNOWN` and LIVE
stays DENY — which is the correct behaviour, not a gap.
