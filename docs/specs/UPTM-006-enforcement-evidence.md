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
| `P10-R2` | Declares `capital_bearing: false` while carrying a capital pack | `run_scope_detector`, `run_validation_capital_detectors` † |
| `P10-R3` | Declares `capital_bearing: true` and brings no pack | `run_scope_detector` |
| `P10-R4` | Brings a capital gate while the tranche is unset | `run_validation_capital_detectors` |
| `P10-R5` | Uses return as an acceptance criterion | `run_validation_capital_detectors` |

Three routes are guarded twice, and the evidence records the count because
"how many independent things would have to fail" is the question a reader
actually has.

**Two of those three were found, not designed.** `P8-R2` and `P10-R2` were
preregistered above with one guard each. The load-bearing test refused both:
neutering `run_scope_detector` alone left each still denying. The registry was
corrected to what the gate actually does, rather than the test loosened to what
the specification had guessed.

**† `P10-R2`'s second guard is a circumstance, not a mechanism.**
`run_validation_capital_detectors` denies it only because `validation_capital`
is unset, so `VC-P1` fires first. The day the Founder sets the tranche that
guard falls away and `SC-I3` holds the route alone — the count drops from two to
one with no code change at all. A reassuring number that quietly decays is worse
than no number, so the manifest flags this one as conditional.

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

5. The thirteen routes above, each denying, each denying via its own named
   check, and each load-bearing — except a route explicitly recorded as blocked.
6. A principle not claiming `ENFORCED` needs no routes.
7. The manifest states `expires_at: null` and names the missing parameter.
8. `P10-R5` denies, is recorded as blocked, and is not relabelled to whatever
   check happens to fire.

## 6. Ceiling

This wall does **not** advance any principle's status. It does not make P9 or
P12 `ENFORCED`; it makes two existing `ENFORCED` claims checkable. P12 in
particular stays `PARTIAL` precisely because expiry is unimplemented, and this
manifest demonstrates that gap rather than papering over it.
