# UPTM-003 — Preregistered definition: `kill_switch_not_self_clearable`, `kill_switch_drill_valid`

| | |
|---|---|
| Principle | **P8 — Independent Kill Switch** |
| Today | `DECLARATIVE` (`capital-rules.json` `principles[].mechanism: null`) |
| Status of this document | **IMPLEMENTED** — `runner/detectors/kill_switch.py`, invoked by `runner.gates.evaluate_gate` |
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
`last_drill_at`, `drill_commit`, `before`, `after`, `artifact_digest`,
`drill.environment` and `stop_state.environment` (each declaring `deployment_ref`,
`credentials_ref`, `gate_path_digest`), and `stop_state.independence_attestation`
(`by`, `at`).

### 4.2 Checks

| Check | Rule | Verdict |
|---|---|---|
| **KS-D1** | `cadence_days` is a positive integer | `null` → `UNKNOWN` — **this is the Founder parameter, §8** |
| **KS-D2** | `now - last_drill_at <= cadence_days` | older → `FAIL`; `last_drill_at` absent → `UNKNOWN` |
| **KS-D3** | The drill record shows a transition: `before.state` is running and `after.state` is stopped, each carrying an artifact digest | a record whose only content is a claim (`"drill": "ok"`, a verdict with no before/after) → `FAIL` `evidence_forgery_detected` |
| **KS-D4** | `drill_commit` is present and the declared `stop_state.path` at that commit equals the one in force now | differs or absent → `UNKNOWN` (P12: evidence has commit and expiry) |
| **KS-D5** | `drill.environment` equals `stop_state.environment` on `deployment_ref`, `credentials_ref` and `gate_path_digest` | differs or either undeclared → `UNKNOWN` |
| **KS-D6** | `stop_state.independence_attestation` exists, carries `by` and `at`, is not future-dated, and is not older than `environment.changed_at` | absent, undated or stale → `UNKNOWN` |

KS-D5 and KS-D4 answer different questions. KS-D2 asks whether the drill is
recent; KS-D5 asks whether it is still *about* the system in force. The two are
independent — a drill performed an hour ago against yesterday's credentials is
fresh and worthless. KS-D4 already covered the stop path; KS-D5 covers the rest
of the blast radius.

KS-D6 does not certify deployment independence, and §0 explains why nothing here
could. It checks the one thing code can check about an attestation: that one
exists, that it is dated, and that it is not older than the deployment it
purports to describe. A PASS means there is a current attestation, not that it
is true.

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
10a. `deployment_ref`, `credentials_ref` or `gate_path_digest` changed since the drill — **even when the drill is minutes old**.
10b. Either environment undeclared.
10c. `independence_attestation` absent, missing `by` or `at`, dated in the future, or older than `environment.changed_at`.

Each of these denies. None of them accuses.

### Must return `PASS` — false-positive protection

11. A well-formed pack: `runner_writable: false`, no write path in `runner/`, stop state readable and `CLEAR`, digest stable, drill within cadence with a real before/after transition, a matching commit, an
   unchanged environment, and a current independence attestation.
12. A drill performed *more* often than the cadence.
12a. An attestation dated after the last deployment change, by an operator whose diligence code cannot assess — KS-D6 passes on currency, never on truth.
13. A stop state that reads `ENGAGED` **and** a gate that correctly resolves to DENY — the switch working is not a violation. This case exists to stop a naive implementation from treating `ENGAGED` itself as FAIL.

---

## 5a. Amendments made during implementation, before any evidence existed

P4 forbids inventing criteria once results are known. Both amendments below were
made while writing the detector, before it had produced a single verdict, and
both are recorded here rather than silently absorbed.

### A1 — KS-I1 tests the capability, not the source

**Preregistered:** *"No module under `runner/` opens `stop_state.path` for
writing, appending or deleting"*, evaluated by scanning the repository.

**Implemented:** the check asks the operating system whether **this process**
can write the stop path, or replace it by writing the parent directory
(`os.access(..., W_OK)`).

**Why.** Source scanning is both fragile and forgeable: a path assembled at
runtime, an indirect call, or a dependency writing on the Runner's behalf all
evade it, and a passing scan would have been evidence of tidy code rather than
of the property P8 wants. The access probe tests the capability itself.

A consequence worth stating plainly: for **uid 0 the probe reports writable
whatever the file mode says, and that is the correct answer** — a Runner running
as root can clear its own stop, so P8's property genuinely does not hold. The
probe is injectable so that the test suite proves the logic rather than the uid
it happens to run under.

### A2 — case 13 contradicted case 3, and case 3 wins

**Preregistered:** case 3 required `FAIL` when the stop reads `ENGAGED` and a
`PASS` was produced; case 13 required `PASS` for *"a stop state that reads
`ENGAGED` and a gate that correctly resolves to DENY"*.

These cannot both hold of one check. A detector that returns `PASS` on an
engaged stop is not what makes the gate deny, so something else would have to —
and then KS-I3 would not be the check that makes the switch a switch.

**Implemented as two things:**

- **KS-I3 (the mechanism)** returns `FAIL` when the stop reads `ENGAGED`, and
  its detail says in words that this is the switch working, not misconduct by an
  agent. The verdict denies; the label does not accuse.
- **KS-I3b (the invariant)** lives in `evaluate_gate`: if the folded verdict is
  `PASS` while the stop reads `ENGAGED`, it is forced to `FAIL`
  `gate_bypass_attempt`. It cannot fire unless a later change to the fold lets
  one through — which is exactly when it should.

Case 13 is kept, rewritten to the property that survives: engaging the switch
denies, is not recorded as misconduct, and does not make every other check fail.

---

## 6. Declared limits — what this will not catch

- **Deployment topology.** As §0 states: co-location, shared credentials, or a stop path on the Runner's own disk are not visible to this detector. Founder attestation, recorded with a date, not a PASS.
- **A drill against a mock.** If the drill exercised a stand-in rather than the real stop path, KS-D3 sees a valid transition. KS-D4 narrows this by pinning the commit; it does not close it.
- **Omission outside LIVE.** Evidence for a non-LIVE gate that carries neither pack is left as the gate treats it today. For LIVE the packs are required and their absence is `UNKNOWN`.
- **Time source.** KS-D2 trusts the clock it is given. A forged `last_drill_at` inside an otherwise consistent pack is not detected here.
- **Omission.** Evidence that carries no `kill_switch` pack never reaches these
  checks. This is the same hole UPTM-002 recorded as `omission_bypass`, and it
  is the reason P8 moves to `PARTIAL` rather than `ENFORCED` — see §7.
- **Root.** A Runner running as uid 0 fails KS-I1 correctly, but nothing here
  stops it from being deployed that way; it only refuses to pass the gate.

---

## 7. Capability outcome — `PARTIAL`, not `ENFORCED`

This section says less than the preregistered version promised, and the
difference is deliberate.

**Delivered:** P8 moves `DECLARATIVE → PARTIAL`. A mechanism exists, it is
invoked from the gate path, and its judgement is load-bearing — three
disconnection mutations each turn the suite red.

**Why not `ENFORCED`.** Evidence that simply omits the `kill_switch` pack is
never examined. A principle a caller can step around by leaving a key out is
not enforced, whatever the detector does when the key is present. Recording
`ENFORCED` here would repeat exactly the overstatement UPTM-001a had to walk
back, and would be the progress illusion P9 names.

**What would close it.** Requiring the pack for the gates where it matters, the
way UPTM-004 requires a `capital` pack for a gate marked `capital: true`. That
needs a declaration in the evidence schema saying which gates are LIVE-bearing,
which is a separate decision and a separate wall.

### Reachability proof

Following UPTM-002c — import proves nothing:

- `tests/test_detector_invocation.py` spies on `evaluate_gate` and asserts it
  calls both `detect_kill_switch` and `detect_kill_switch_drill`, and that the
  drill detector receives the Founder's cadence read from `capital-rules.json`.
- The disconnection test stubs the detector's return value and asserts the
  gate's verdict follows it.
- Mutations run against the finished suite: dropping the detector's verdict from
  the fold, deleting the KS-I3b invariant, and neutering the KS-I1 probe each
  turn the suite red, at the tests that name that property and no others.

---

## 7a. KS-D5 and KS-D6 — ported after the fact

These two checks were not in the original preregistration. They were written in a
parallel UPTM-003 implementation (PR #9, closed unmerged) and ported here on the
Founder's instruction, because the Founder's original brief for this wall
required both: *a drill must be re-required after a change to deployment,
credentials or the kill-switch/gate path*, and *physical separation remains an
explicit operator attestation with a date*.

Recorded as an addition rather than folded into §4.2 silently, because a
specification that quietly becomes whatever was built stops being a
specification (the rule §5a already applies to the two earlier amendments).

No evidence had been graded against §4.2 when this landed.

## 8. Founder parameter — set

```
capital-rules.json → live_capability.kill_switch_drill_cadence_days : 7
```

Set by the Founder on 2026-09-23. It was not proposed here: a cadence is a risk
appetite, not a derivation, and a number invented by the agent that wrote the
detector would be the sourceless number the UPTM-002 detector exists to catch.

The `UNKNOWN` path is kept and tested (case 7): if the value is ever cleared,
KS-D1 returns `UNKNOWN` and the gate denies rather than falling back to a
default.
