# UPTM-005 — Preregistered definition: `scope_undeclared`, `scope_contradicted`

| | |
|---|---|
| Principles | **P8** (Independent Kill Switch) and **P10** (Validation Capital) |
| Today | both `PARTIAL` — mechanised and invoked, steppable around by omission |
| Status of this document | **IMPLEMENTED** — `runner/detectors/scope.py`, invoked unconditionally by `runner.gates.evaluate_gate` |
| Founder decision | absence of the declaration resolves to `UNKNOWN` (2026-09-23) |

Written before the detector existed, as P4 requires.

---

## 0. The hole this closes

UPTM-003 and UPTM-004 both stopped short of `ENFORCED`, for the same reason
written twice:

> Evidence that omits the `kill_switch` pack is never examined.
> A gate that never sets `capital_gate` is never examined.

A detector cannot check a pack it is never handed. Both walls guard the door and
neither guards the doorway. This one makes the doorway mandatory.

**Not claimed.** That a declaration is true. A gate that declares
`live_bearing: false` while actually bearing LIVE has not stepped around the
check — it has lied in signed evidence, which is a different class of problem
and belongs to UPTM-002. The distinction matters and §7 is explicit about it.

---

## 1. Verdict model

As UPTM-002/003/004. Absence is never PASS. `UNKNOWN` denies without accusing;
`FAIL` asserts a demonstrated violation.

---

## 2. The declaration

```json
"scope": {
  "capital_bearing": true,
  "live_bearing": false
}
```

Every gate declares what it bears. There is no default and no inference: a gate
that says nothing says nothing, and silence denies (GOVERNANCE C3).

**This is a breaking change, deliberately.** Evidence written before this wall
carries no `scope` and will resolve to `UNKNOWN`. That is the Founder's choice
of the strict option over the compatible one, taken with the consequence stated:
existing gates stop passing until they are declared.

---

## 3. Checks

| Check | Rule | Verdict |
|---|---|---|
| **SC-P1** | `scope` present, with `capital_bearing` and `live_bearing` both boolean | absent or malformed → `UNKNOWN` |
| **SC-I1** | `capital_bearing: true` → a `capital` pack is present | absent → `UNKNOWN` |
| **SC-I2** | `live_bearing: true` → both `kill_switch` and `kill_switch_drill` are present | either absent → `UNKNOWN` |
| **SC-I3** | A pack is present while its scope declares the gate does not bear it | → `FAIL` `gate_bypass_attempt` |

**SC-I3 is the one with teeth.** Declaring yourself out of scope while carrying
the very thing the scope governs is not sloppiness; it is the step-around P8 and
P10 were open to, done explicitly. Omitting the pack *and* declaring
`false` is a different thing and is not caught here — see §7.

---

## 4. Consequences for the other two walls

- UPTM-003's checks run whenever `live_bearing: true`, and a missing pack denies
  rather than passing unexamined.
- UPTM-004 keeps `capital_gate` as the flag its own checks read, and SC-I1 makes
  it impossible to carry capital without declaring the gate.

Neither detector changes. This wall changes only whether they are reached.

---

## 5. Preregistered acceptance criteria

### Must return `FAIL`

1. `scope.capital_bearing: false` with a `capital` pack present.
2. `scope.live_bearing: false` with a `kill_switch` pack present.

### Must return `UNKNOWN` — not `PASS`, not `FAIL`

3. No `scope` key at all.
4. `scope` present but `capital_bearing` missing.
5. `capital_bearing` that is not a boolean (a string `"true"` is not a declaration).
6. `capital_bearing: true` with no `capital` pack.
7. `live_bearing: true` with a `kill_switch` pack but no `kill_switch_drill`.

### Must return `PASS`

8. `capital_bearing: false`, `live_bearing: false`, no packs — a gate that bears
   neither is a legitimate and common state, and must not be punished for it.
9. `capital_bearing: true` with a capital pack, `live_bearing: false` with no
   kill-switch pack — the two are independent.
10. Both true, both packs present.

Case 8 is the one that keeps this wall from becoming a tax on every gate in the
repository.

---

## 6. Declared limits

- **A false declaration.** As §0: this wall makes the declaration mandatory and
  self-consistent. It cannot tell whether the declaration is true.
- **Retrofit.** The eight `waves/*.yaml` and any evidence already written must be
  declared before they pass again. That is the cost of the strict option and it
  was chosen knowingly.

---

## 7. Capability outcome

The checks hold. **P8 and P10 move `PARTIAL → ENFORCED`** — the first enforced
principles in this repository.

The claim being made is precise: **the principle can no longer be avoided by
omission.** Every route that previously let a caller skip the checks by leaving a
key out now denies. What remains is a caller who states something untrue in
signed evidence, which is forgery rather than avoidance, and which UPTM-002
exists to address.

That distinction is the whole basis for the state change. Under test, every
route that previously let a caller skip the checks by leaving a key out now
denies: undeclared evidence, a declared bearing with no pack, and an opt-out
while carrying the pack. A gate that bears neither still passes, so the wall is
not a tax.

**Retrofit, as predicted.** `runner.fsm.run_baseline_ack` now emits the
declaration, and `evidence/wave0/baseline_ack.json` carries it. The producer was
changed rather than the artifact patched, so a regenerated ack is declared too.

### Reachability proof

Following UPTM-002c: a spy asserting the gate calls the detector, a disconnection
test asserting the gate's verdict follows its return value, and mutations that
must turn the suite red at the tests naming each property.
