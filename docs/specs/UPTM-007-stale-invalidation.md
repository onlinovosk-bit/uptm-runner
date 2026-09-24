# UPTM-007 — STALE invalidation on dependency change

| | |
|---|---|
| Status | **PREREGISTERED** — written before `runner/staleness.py` exists (CC/P4) |
| Principle | **P12** (Evidence Has Commit & Expiry) |
| Subject | every enforcement evidence artifact, after it is generated |
| Produces | dependency digests in the manifest · `STALE` as a verdict the gate can reach |
| Founder GO | 2026-09-24, "GO na P12 STALE invalidáciu" |

## 0. A correction before anything is built

I told the Founder that STALE was *"the last half holding P12 at PARTIAL."*
Reading P12's own text disproves that. P12 demands three things, not two:

> Every PASS is bound to a precisely identified state: code commit, data
> snapshot, config, … The evidence manifest **must state explicitly what is and
> is not deterministic, including what could not be captured** (wall clock,
> network timing, broker-side state). A change to a relevant dependency
> automatically invalidates the affected PASS → `STALE`.
>
> *Violation:* a capability stays green after a change to the code or data its
> evidence came from; **or a result is called reproducible without declaring
> uncaptured inputs.**

So: commit (done, Evidence Rule A), expiry (done, `evidence_expiry_days: 7`),
**dependency STALE** (this wall, §A) and **the determinism declaration** (also
missing, §B). The violation clause names both, so an `ENFORCED` P12 needs both.
Building only §A and then advancing the status would be the typed-word defect
UPTM-006 exists to catch, applied to the principle that governs evidence.

§B is in this wall because the wall is P12, not because the GO asked for it. It
is named here, before implementation, rather than discovered afterwards.

## 1. What STALE means here

An artifact is **STALE** when a file it depended on has changed since it was
generated, even while it is inside its seven days. Freshness by clock and
freshness by content are different claims, and only the second one is about
whether the evidence still describes the system.

Three-valued, like everything else that gates money:

| | |
|---|---|
| `CURRENT` | every recorded dependency is present and its digest matches |
| `STALE` | at least one recorded dependency is present and differs |
| `UNKNOWN` | a dependency is missing or unreadable, or none were recorded |

`UNKNOWN` is not a soft `CURRENT`. Under `runner.verdict` it dominates `PASS`
and denies. An artifact that cannot say what it depended on has not been shown
to still describe anything.

## 2. The dependency set is derived, never typed

A hand-maintained list is the same failure as a hand-typed `ENFORCED`: someone
adds a detector, forgets the list, and the evidence stays green while the thing
it describes has moved. So the set is **derived from the repository**:

- every `*.py` under `runner/` (the code the routes actually exercise),
- `constitution/capital-rules.json` (the parameters the gate reads),
- `constitution/CONSTITUTION-CAPITAL.md` — the constitution says of itself:
  *"This document is an evidence dependency. A change to its version
  invalidates every PASS issued under it (P12)."*
- every file under `prompt-stacks/` (PS-R3 exists because stack bodies drift).

**Over-inclusion is the deliberate choice.** A file in the set that did not
matter causes a false `STALE`: evidence is regenerated needlessly. A file
missing from the set causes a false `CURRENT`: evidence stays green after the
thing it describes changed. The first wastes a run, the second is the P12
violation itself. When the two failure modes are not symmetric, prefer the one
that denies.

## 3. Acceptance criteria, preregistered

### §A — STALE invalidation

- **A1** The manifest carries a `dependencies` map of path → sha256, derived by
  walking the repository, not from a literal list in the source.
- **A2** `staleness(manifest, root)` returns `CURRENT` for an unmodified tree.
- **A3** Changing the content of **any** recorded dependency returns `STALE`,
  and the result names which paths changed.
- **A4** Deleting a recorded dependency returns `UNKNOWN`, not `STALE` and not
  `CURRENT` — a file that is gone cannot be compared.
- **A5** An artifact with no `dependencies` key returns `UNKNOWN`.
- **A6** Adding a new `runner/*.py` file makes the previous artifact `STALE`
  without any edit to the dependency logic. This is the criterion that proves
  §2: a hand-maintained list would pass A1–A5 and fail this.
- **A7** `CONSTITUTION-CAPITAL.md` is in the set, so a constitutional change
  invalidates evidence, as the constitution demands of itself.
- **A8** The digest is of content, not of mtime or size.

### §B — determinism declaration

- **B1** The manifest carries a `determinism` block naming, explicitly, what
  **is** captured and what **is not**.
- **B2** The uncaptured list is non-empty and names at least the wall clock
  (`generated_at` moves every run) — P12 names it directly.
- **B3** The block is not free prose: a test asserts the required keys, so it
  cannot decay into a sentence nobody maintains.

### §C — status

- **C1** P12 changes from `PARTIAL` only if **every** criterion in §A and §B
  passes, *and* P12 has routes in the UPTM-006 registry that all deny via their
  own check, *and* `unproven_claims()` does not name it.
- **C2** If any criterion fails, P12 stays `PARTIAL` and this document records
  which one. A status is earned or it is not claimed.
- **C3** No other principle's status changes. `LIVE_TRADING` stays `false`.

## 4. What this wall does not establish

That the dependency set is *complete* in principle. It is complete over the
repository, which is not the same as complete over everything a run touches —
the Python version, installed packages and the container are not captured, and
§B names them as uncaptured rather than pretending otherwise.

It also does not make evidence reproducible. It makes evidence **honest about
having stopped being current**, which is a smaller and different thing.

---

## 5. Result, recorded against the preregistered criteria

Measured 2026-09-24, after implementation, against §3 as written.

| | |
|---|---|
| A1 derived digests in the manifest | **PASS** — 28 dependencies |
| A2 unmodified tree is `CURRENT` | **PASS** |
| A3 any changed dependency is `STALE`, named | **PASS** — all five kinds |
| A4 deleted dependency is `UNKNOWN` | **PASS** |
| A5 no dependencies recorded is `UNKNOWN` | **PASS** |
| A6 a new `runner/*.py` is picked up, no code edit | **PASS** |
| A7 `CONSTITUTION-CAPITAL.md` is in the set | **PASS** |
| A8 digest is of content, not mtime or size | **PASS** |
| B1 `determinism` block present | **PASS** |
| B2 uncaptured names the wall clock | **PASS** — 4 entries |
| B3 structured, not prose | **PASS** |
| **C1 P12 → `ENFORCED`** | **FAIL** |
| C2 status stays `PARTIAL`, reason recorded | **PASS** — this section |
| C3 nothing else moved, `LIVE_TRADING` false | **PASS** |

Proved on a live artifact rather than a fixture:

```
evidence/enforcement/72c2c88….json   28 dependencies
fresh tree                           CURRENT
runner/gates.py edited               STALE  → ('runner/gates.py',)
restored                             CURRENT
CONSTITUTION-CAPITAL.md edited       STALE  → ('constitution/CONSTITUTION-CAPITAL.md',)
restored                             CURRENT
```

### Why C1 failed, precisely

UPTM-006 defines an `ENFORCED` claim as *"there is no route by which a gate can
reach `PASS` while violating this principle"* — a claim about **routes through
`evaluate_gate`**, not about a checker existing.

`evaluate_gate` does not read dependency digests from the evidence it is handed.
It cannot, because gate evidence does not carry them: `validate_evidence_structure`
does not require a `dependencies` field, and no producer emits one. So a caller
can still submit gate evidence generated against code that has since changed, and
the gate has no way to notice. **No P12 route can be demonstrated, so P12 has
none in the registry, so P12 is not `ENFORCED`.**

What this wall did build is real and load-bearing: the *enforcement evidence
artifact* now knows when it has stopped describing the system, and says so in
three values. That is the subject this document preregistered in its header. It
is not the same as the gate refusing stale evidence.

### What would close C1

Making `dependencies` a required field of gate evidence and having
`evaluate_gate` deny when its staleness is not `CURRENT` — the same shape
APS-001 used to make `prompt_stack` mandatory. That is a **contract change**:
every producer of gate evidence must emit the field, and evidence already
written becomes invalid. It is a separate wall with its own preregistration and
its own Founder GO, and it is not started here.

The goalposts are not moved to meet what was built. C1 is recorded as failed.
