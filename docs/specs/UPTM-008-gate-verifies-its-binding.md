# UPTM-008 — the gate verifies the binding its evidence already declares

| | |
|---|---|
| Status | **PREREGISTERED** — written before any verification code exists (CC/P4) |
| Principle | **P12** (Evidence Has Commit & Expiry) |
| Subject | `runner.gates.evaluate_gate` and the `files[]` every gate artifact carries |
| Founder GO | 2026-09-24, "GO na gate spotrebuje staleness" |

## 0. Measured on `main` at `dcf77f4`, before anything was designed

```python
e = _base()                       # a UPTM-006 route's evidence
e["files"]                        # [{"path": "runner/gates.py",
                                  #   "sha256": "aaaa…aaaa"}]
evaluate_gate(e).verdict          # PASS

e2 = _base(files=[{"path": "no/such/file.py", "sha256": "bbbb…bbbb"}])
evaluate_gate(e2).verdict         # PASS
```

**The gate passes evidence that declares a file which does not exist, with a
digest that was never computed from anything.** `validate_evidence_structure`
requires the `files` key to be *present*; nothing has ever compared its contents
to the repository.

That is P12's violation clause, word for word:

> *Violation:* a capability stays green after a change to the code or data its
> evidence came from.

It is also a finding about my own work. Every UPTM-006 route has carried
`"sha256": "a" * 64` since the wall was built, and every one of them passed
structural validation with it. The routes proved what they were built to prove;
none of them noticed that the field beside the proof was a fabrication.

## 1. What changes, and what deliberately does not

**The GO said "the gate consumes staleness."** The obvious reading is a new
`dependencies` field on gate evidence, mirroring the enforcement manifest. This
document rejects that reading, and the measurement above is why.

The binding **already exists in the contract**. `files[]` is required, every
producer emits it, and the one tracked artifact
(`evidence/wave0/baseline_ack.json`) already declares a real path and a real
sha256 of `audits/baseline/wave0_baseline.json`. Nothing is missing except the
check.

So: **no new field, no schema change, no producer migration.** The gate starts
verifying what it is already handed. This is smaller than what was authorised,
and it closes the hole that is actually open.

A new `dependencies` field is also *worse*, not merely larger. Digests of
`runner/**.py` inside a tracked artifact are self-defeating: the artifact goes
stale the moment any runner file changes, including in the commit that writes
it, and regenerating it dirties the tree — which `enforcement-evidence` then
refuses under Evidence Rule A. Evidence should bind the data it is *about*, not
the whole repository it was produced in.

## 2. Three-valued, as everything that gates money is

| | |
|---|---|
| `CURRENT` | every declared file exists and its digest matches |
| `STALE` | a declared file exists and differs — the evidence describes code that moved |
| `UNKNOWN` | a declared file cannot be read, or nothing is declared |

`UNKNOWN` denies. An artifact that named a file which is now gone has not been
shown to describe anything, and absence is not a measurement — the same reason a
missing parameter is `UNKNOWN` rather than zero.

## 3. Acceptance criteria, preregistered

### §G — the gate

- **G1** `evaluate_gate` verifies every `files[].sha256` against the tree and
  denies when verification is not `CURRENT`.
- **G2** A **changed** declared file denies, and the reason names the path.
- **G3** A **missing** declared file denies as `UNKNOWN`, not `STALE`.
- **G4** A **fabricated** digest denies. This is the criterion that proves the
  wall: the exact evidence in §0 passed before it and must fail after.
- **G5** An **empty** `files` list denies. Evidence bound to nothing is not
  bound; P12 requires binding to a precisely identified state.
- **G6** A malformed entry — not a dict, no `path`, no `sha256`, a `sha256`
  that is not 64 hex characters — denies rather than being skipped. A check
  that silently ignores what it cannot parse is not a check.
- **G7** The verification is reachable: a spy proves `evaluate_gate` calls it,
  and neutering it turns a denying gate into a passing one (the mutation shape
  UPTM-002c is named after).

### §R — routes, because ENFORCED is a claim about routes

- **R1** P12 has routes in the UPTM-006 registry, one per violation shape in
  §G2–G6, each denying via its own check.
- **R2** `unproven_claims()` does not name P12.
- **R3** The existing UPTM-006 routes keep denying **for their own reasons**.
  Their fixtures must declare a real file, because the fabricated digest they
  have carried would now deny them first and every proof in that wall would
  start passing for the wrong reason.

### §C — status

- **C1** P12 → `ENFORCED` only if every criterion in §G and §R passes.
- **C2** If any fails, P12 stays `PARTIAL` and this document records which.
- **C3** No other principle moves. `LIVE_TRADING` stays `false`.

## 4. Blast radius, measured before it is caused

```
callers of evaluate_gate          67   (overwhelmingly test fixtures)
tracked gate artifacts             1   evidence/wave0/baseline_ack.json
                                       - already declares a real path + digest
producers of gate evidence         1   runner/fsm.py run_baseline_ack()
test files with evidence fixtures  4
```

Every fixture that declares a fabricated file will begin to deny. That is the
wall working, not the wall breaking — but it is a real cost and it lands on
other sessions' fixtures too, not only mine. Fixtures are repaired by declaring
a real file, never by weakening the check.

## 5. What this does not establish

That the declared set is the *right* set. A producer that declares one
irrelevant file and omits the ten that matter passes every criterion here. This
wall makes the declaration **true**; it does not make it **complete**. Choosing
what evidence must declare is a separate question and is not answered here.
