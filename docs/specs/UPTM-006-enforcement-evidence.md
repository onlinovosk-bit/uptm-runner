# UPTM-006 — Enforcement evidence

| | |
|---|---|
| Status | **PREREGISTERED** — written before `runner/enforcement.py` existed (CC/P4) |
| Principle | serves **P9** (No Progress Illusion) and **P12** (Evidence Has Commit & Expiry) |
| Subject | the `ENFORCED` claims in `constitution/capital-rules.json` |
| Produces | `evidence/enforcement/<commit>.json` · a test that fails when a claim is unearned |

## 0. The problem this wall guards

`capital-rules.json` currently says:

```
P8  Independent Kill Switch   ENFORCED
P10 Validation Capital        ENFORCED
```

Nothing checks that. The word is typed into a file by whoever last edited it.
Every other wall in this repository exists because *declared is not detected*
(P9) — and the table recording that principle is itself undetected.

This is not hypothetical. On 2026-09-23 `uptm003_detector.why_not_enforced`
still explained why P8 was **not** enforced, sitting three lines from a `P8`
reading `ENFORCED`. Two contradictory claims about the same principle, in the
same file, in the artifact the gate reads. It was found by someone reading the
file, which is exactly the detection method this repository refuses to accept
anywhere else.

## 1. What an `ENFORCED` claim asserts

> There is no route by which a gate can reach `PASS` while violating this
> principle.

That is a claim about **routes**, not about detectors. A detector that is
correct but unreachable enforces nothing — the lesson UPTM-002c is named after.
So the evidence is organised by route, not by check.

## 2. What the evidence must show

For every principle claiming `ENFORCED`:

1. **Routes are enumerated.** Each is a concrete piece of evidence a caller
   could submit while violating the principle — including omission, the route
   that held P8 and P10 at `PARTIAL` until UPTM-005.
2. **Every route denies**, established by calling the real
   `runner.gates.evaluate_gate` and reading its verdict. Not by reading
   `capital-rules.json`, and not by asserting that a detector function returns
   the right thing in isolation.
3. **Every denial is load-bearing.** Each route names the guards that stop it.
   Neuter all of them and the route must reach `PASS`. A route that still denies
   with its guards removed is denied by something else, and the guard it names
   is not the thing enforcing the principle.
4. **The claim is gated.** A principle marked `ENFORCED` with no registered
   route set fails the suite. `ENFORCED` becomes a status that must be earned
   rather than typed.

## 3. Routes — preregistered

### P8 — Independent Kill Switch

| Route | What the caller is doing | Guards |
|---|---|---|
| `P8-R1` | Submits evidence with no `scope` and no kill-switch pack — the pre-UPTM-005 omission | `run_scope_detector` |
| `P8-R2` | Declares `live_bearing: false` while carrying a kill-switch pack | `run_scope_detector`, `run_kill_switch_detectors` |
| `P8-R3` | Declares `live_bearing: true` and brings no packs | `run_scope_detector` |
| `P8-R4` | Brings a complete, valid pack whose stop state reads `ENGAGED` | `run_kill_switch_detectors`, `stop_is_engaged` |
| `P8-R5` | Declares the stop state writable by the Runner | `run_kill_switch_detectors` |
| `P8-R6` | Brings a drill older than the cadence | `run_kill_switch_detectors` |
| `P8-R7` | Brings a fresh drill run against a deployment that has since changed | `run_kill_switch_detectors` |
| `P8-R8` | Brings no independence attestation | `run_kill_switch_detectors` |

### P10 — Validation Capital

| Route | What the caller is doing | Guards |
|---|---|---|
| `P10-R1` | Submits evidence with no `scope` and no capital pack | `run_scope_detector` |
| `P10-R2` | Declares `capital_bearing: false` while carrying a capital pack | `run_scope_detector`, `run_validation_capital_detectors` |
| `P10-R3` | Declares `capital_bearing: true` and brings no pack | `run_scope_detector` |
| `P10-R4` | Capital at risk above the tranche | `run_validation_capital_detectors` |
| `P10-R5` | Return used as an acceptance criterion | `run_validation_capital_detectors` |
| `P10-R6` | Cumulative realised loss above the tranche | `run_validation_capital_detectors` |
| `P10-R7` | Exposure reported in a currency the ceiling is not denominated in | `run_validation_capital_detectors` |
| `P10-R8` | The tranche cleared after having been set | `run_validation_capital_detectors` |
| `P10-R9` | A PASS claim resting on what the run earned | `run_validation_capital_detectors` |

**`P10-R4` and `R6`–`R9` did not exist before 2026-09-23.** Until the Founder set
`validation_capital`, there was no ceiling to step over, so no route could test
one: `VC-P1` denied every capital gate on the unset tranche before any other
check was reached. Setting the parameter is what made the routes possible, and
it is also what exposed a defect in this module's own capital fixture — it had
invented the field names `aggregate_open_exposure` and `per_position_at_risk`,
where the detector reads `at_risk`. Nothing noticed, because nothing had ever
got far enough to read them.

Three routes are guarded twice, and the evidence records the count because
"how many independent things would have to fail" is the question a reader
actually has.

**Two of those three were found, not designed.** `P8-R2` and `P10-R2` were
preregistered above with one guard each. The load-bearing test refused both:
neutering `run_scope_detector` alone left each still denying. The registry was
corrected to what the gate actually does, rather than the test loosened to what
the specification had guessed.

### A prediction this document made, and got wrong

An earlier revision of this section said `P10-R2`'s second guard was a
circumstance rather than a mechanism — that `run_validation_capital_detectors`
denied it only because `validation_capital` was unset, and that setting the
tranche would drop the route from two guards to one.

**Measured after the tranche was set: false.** Neutering either guard alone
still leaves the route denying. The capital detector's hold on `P10-R2` was
never `VC-P1`, the unset tranche; it is `VC-P2` — a pack carried by evidence
that does not declare `capital_gate` — which is structural and does not depend
on the tranche at all. The reasoning was plausible and untested, and the count
did not change.

It is recorded in `runner/enforcement.py` as `CORRECTED_PREDICTIONS`, with a
test asserting it stays there. A wall whose purpose is that claims must be
checked does not get to drop its own failed claim out of the record.

## 4. What this evidence does **not** establish

- **That the route list is complete.** It shows that every *enumerated* route
  denies. A route nobody thought of is not covered, and no test can close that.
  This is the honest ceiling of the wall and the reason it does not itself claim
  to make anything `ENFORCED`.
- **That a declaration is true.** Inherited from UPTM-005: a gate that lies in
  signed evidence has not found a route, it has committed forgery.
- **Expiry.** P12 requires evidence to carry a commit *and* an expiry. The
  manifest carries the commit. There is no preregistered evidence lifetime in
  `capital-rules.json`, so `expires_at` is `null` and the manifest says so in
  words. An invented number would be the sourceless value UPTM-002 exists to
  catch. **This is a Founder parameter and it is open.**

## 5. Preregistered acceptance criteria

### Must FAIL the suite

1. A principle reading `ENFORCED` with no registered routes.
2. Any route whose evidence reaches `PASS`.
3. Any route that still denies when all of its named guards are neutered.
4. A route naming a guard that does not exist on `runner.gates`.

### Must PASS

5. The seventeen routes above, each denying, each denying via its own named
   check, and each load-bearing — except a route explicitly recorded as blocked.
6. A principle not claiming `ENFORCED` needs no routes.
7. The manifest states `expires_at: null` and names the missing parameter.
8. No route is recorded as blocked: `P10-R5` was unblocked by the tranche being
   set and now denies via `VC-R1`.
9. A doubly guarded route is opened by neither of its guards alone.

## 6. Ceiling

This wall does **not** advance any principle's status. It does not make P9 or
P12 `ENFORCED`; it makes two existing `ENFORCED` claims checkable. P12 in
particular stays `PARTIAL` precisely because expiry is unimplemented, and this
manifest demonstrates that gap rather than papering over it.
