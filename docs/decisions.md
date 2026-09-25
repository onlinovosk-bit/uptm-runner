# UPTM — Decisions Log

Founder decisions about the UPTM Runner, and where each one is enforced.

**Why this file exists.** P14 requires that constitutional and parameter changes
be made by the Founder "explicitly, with a recorded reason". A reason that lives
only in a commit message or a pull-request body is not recorded — it is
retrievable, which is not the same thing. This is where the reason lives.

**Scope.** UPTM only. Revolis.AI / RealitkaAI decisions do not belong here, and
UPTM decisions do not belong there.

**Format.** Newest first. Every entry names what was decided, why, and the
artifact that makes it real. A decision with no artifact is a plan, and says so.

---

## [2026-09-25] DEC-UPTM-MAP-Q3 — no relation between €700 and €750 is adopted

**Decided:** Founder GO MAP-Q3, accepting the recommendation not to invent the
relation. Question 3 on `docs/architecture/governance-map.md` stays **OPEN**.
€700 remains `validation_capital.amount`, the size of the validation test.
€750 remains the other repository's paper-account capital. Neither number is a
ceiling, a subset, or a limit on the other.

**Why:** The map measured that nothing stated how they relate. Choosing one
reading would be a new risk parameter, and an unset relation stays unknown.
`validation_capital.amount` stays 700 EUR. `CONSTITUTION-CAPITAL.md` v1.0 stays
LOCKED. No principle's enforcement state moves. `LIVE_TRADING` stays false. No
P12 invalidation follows.

**Artifact:** the question 3 block in `docs/architecture/governance-map.md`
carries `OPEN (DEC-UPTM-MAP-Q3)`. Mutation `map-q3-marked-decided` replaces
that marker with a chosen relation. `test_map_q3_stays_open` goes red.

---

## [2026-09-25] DEC-UPTM-MAP-Q2 — neither repository's PASS wins a disagreement

**Decided:** Founder GO MAP-Q2, accepting the recommendation not to pick a
winner from this repository. Question 2 on `docs/architecture/governance-map.md`
stays **OPEN**. On a disagreement, neither repository's `PASS` is the winner.

**Why:** Both repositories can emit `PASS`, and neither reads the other's.
Naming `uptm-runner` the winner would make this gate override a verdict it has
not seen. Naming `onlinovosk-bit-uptm` the winner would make that repository's
`PASS` override this one without a reader. `CONSTITUTION-CAPITAL.md` v1.0 stays
LOCKED. No principle's enforcement state moves. `LIVE_TRADING` stays false. No
P12 invalidation follows.

**Artifact:** the question 2 block in `docs/architecture/governance-map.md`
carries `OPEN (DEC-UPTM-MAP-Q2)`. Mutation `map-q2-marked-decided` replaces
that marker with a chosen winner. `test_map_q2_stays_open` goes red.

---

## [2026-09-25] DEC-UPTM-MAP-Q1 — the trading-wave question stays open

**Decided:** Founder GO MAP-Q1, accepting the recommendation not to answer it
from this repository. Question 1 on `docs/architecture/governance-map.md` stays
**OPEN**. Neither answer is adopted: a trading-system wave gate is not declared
to satisfy the capital constitution, and it is not declared exempt from it.

**Why:** The map measured that nothing connects the two repositories. Answering
"yes" would invent a W8 evidence artifact this repository does not have.
Answering "no" would exempt a trading wave from P8 and P10 without a Founder
amendment. `CONSTITUTION-CAPITAL.md` v1.0 stays LOCKED. No principle's
enforcement state moves. `LIVE_TRADING` stays false. No P12 invalidation
follows.

**Artifact:** the question 1 block in `docs/architecture/governance-map.md`
carries `OPEN (DEC-UPTM-MAP-Q1)`. Mutation `map-q1-marked-decided` replaces
that marker with an adopted answer. `test_map_q1_stays_open` goes red.

---

## [2026-09-25] DEC-UPTM-APS-010 — a wave that names no agents records from the gate

**Decided:** Founder GO APS-010. A wave whose yaml `ownership.agents` is an empty
list records `passed_waves` from a PASS gate with `CRITICAL=0` and `HIGH=0`.
It does not require a `SwarmDispatch`.

**Why:** Wave 0 is the baseline lock, and its yaml says `agents: []`. Waves 2,
4, 5, 6, and 7 make the same declaration. Inventing a claim ledger for a wave
that named nobody would be a new claim, not enforcement of one the wave already
made. A non-empty list, an unreadable declaration, a ledger whose `agent_id`s
differ from the list, and a failed collect still deny. Those are APS-007
through APS-009.

**Artifact:** `runner.fsm._wave_lists_agents` returns false for an empty list.
Mutation `empty-agents-require-dispatch` forces that return to true.
`test_empty_agent_list_still_records_without_dispatch` and
`test_terminating_fsm_reaches_exit_after_all_waves_pass` go red. `LIVE_TRADING`
stays false.

---

## [2026-09-24] DEC-UPTM-008 — the gate verifies the binding it was always handed; P12 is ENFORCED

**Decided:** Founder GO, *"GO na gate spotrebuje staleness"*. Built as
`UPTM-008`, preregistered in `docs/specs/UPTM-008-gate-verifies-its-binding.md`
before any verification code existed (P4).

### What was open, measured before anything was designed

```python
evaluate_gate(_base()).verdict                       # PASS
#   files: [{"path": "runner/gates.py", "sha256": "aaaa…"}]
evaluate_gate(_base(files=[{"path": "no/such/file.py",
                           "sha256": "bbbb…"}])).verdict   # PASS
```

**The gate passed evidence declaring a file that does not exist, with a digest
never computed from anything.** `validate_evidence_structure` required the
`files` key to be present; nothing had ever compared its contents to the
repository. That is P12's violation clause, live on `main`.

It was also a finding about my own work: every UPTM-006 route carried
`"sha256": "a" * 64` from the day that wall was built. The routes proved what
they were built to prove; none noticed the fabrication beside the proof.

### The GO was read narrowly, on purpose

"The gate consumes staleness" reads most obviously as a new `dependencies` field
on gate evidence, mirroring the enforcement manifest. **That reading was
rejected**, and the spec says why before the code: the binding already existed
in the contract and every producer already emitted it, so no schema change and
no producer migration were needed. A `dependencies` field would also be *worse* —
digests of `runner/**.py` inside a tracked artifact go stale the moment any
runner file changes, and regenerating it dirties the tree, which
`enforcement-evidence` then refuses under Evidence Rule A.

Evidence should bind the data it is **about**, not the whole repository it was
produced in. Smaller than authorised, and it closes the hole that was open.

### P12 is ENFORCED, and the word is bounded

All of §G and §R passed, so C1 authorised the change. `capital-rules.json`
carries `enforced_since`, `earned_by` naming UPTM-008, and
`what_this_does_not_establish`:

> It means there is no route to `PASS` with a **false** binding. It does not
> mean the binding is **sufficient** — a producer declaring one irrelevant file
> and omitting ten that matter satisfies every route here. This wall makes the
> declaration true, not complete.

`enforced_principles()` is now `['P8', 'P10', 'P12']`, `unproven_claims()` is
empty, 32 routes, none reaching `PASS`, none denied for another reason.

### A mutation case, because a deleted guard reads like a passing one

`evidence-binding-unverified` was added to the mutation gate from
`DEC-UPTM-MUTGATE`: remove the call and four named tests must go red. They do.
Without it, deleting this check would have been silent — the failure that gate
exists to catch.

### Unchanged

`LIVE_TRADING` stays `false`. `CONSTITUTION-CAPITAL.md` v1.0 stays LOCKED. P8,
P10 and P9 keep their status. No capability granted — refusing evidence that
lies about where it came from narrows what may pass, never widens it.

**Artifacts:** `docs/specs/UPTM-008-gate-verifies-its-binding.md` ·
`runner/binding.py` · `runner/gates.py` · `runner/mutation_gate.py` ·
`constitution/capital-rules.json` · `tests/test_binding.py` · corrected
fixtures in `tests/conftest.py` and `runner/enforcement.py`. Measured: 452
passed, mutation-gate exit 0.

---

## [2026-09-24] DEC-UPTM-APS-COMPOSER — the remaining composer denials are routes

**Decided:** the fail-closed branches of `assemble_prompt`, and the missing
`wave_context` case, are routes on guard `APS-001`. They do not become a
principle and they do not enter `capital-rules.json`.

`PS-R1` through `PS-R3` stay green if those branches are deleted. The role,
dependency, identity, and silence checks lived only in unit tests.

`wave_context` was worse than unrouted. `validate_prompt_stack_binding`
substituted `{"wave_id": evidence.wave_id}` when the binding omitted the field.
A binding assembled as exactly that object, with `wave_context` then removed,
reached `PASS` on `main` at `5e492f5`. Measured before this change.

Criteria fixed before the new measurement:

- `PS-R4` denies with `prompt_stack wave_context is required`.
- `PS-R5` denies with `may not receive stack 06`.
- `PS-R6` denies with `unknown prompt stack`.
- `PS-R7` denies with `duplicate prompt stack`.
- `PS-R8` denies with `missing prior dependencies`.
- `PS-R9` denies with `unknown role`.
- `PS-R10` denies with `no prompt stacks`.
- Neutering `validate_prompt_stack_binding` opens each of them. None is added
  to `REDUNDANT_GUARDS`.
- `enforced_principles()` stays `P8` and `P10`.

**Measured:** each new route returns `FAIL` with one gate reason:

- `PS-R4` `fail-closed: prompt_stack wave_context is required`
- `PS-R5` `fail-closed: role 'executor' may not receive stack 06`
- `PS-R6` `fail-closed: unknown prompt stack 99`
- `PS-R7` `fail-closed: duplicate prompt stack 00`
- `PS-R8` `fail-closed: stack 06 missing prior dependencies ['00', '05']`
- `PS-R9` `fail-closed: unknown role 'auditor'`
- `PS-R10` `fail-closed: no prompt stacks requested`

The loader no longer repeats `fail-closed:`; the gate adds it once.
`enforced_principles()` stayed `['P8', 'P10']`. The registry is 27 routes.

**Artifacts:** `runner/prompt_stacks.py` (`require_binding_wave_context`) ·
`runner/enforcement.py` (`PS-R4`–`PS-R10`) ·
`schemas/evidence.schema.json` · `tests/test_enforcement_evidence.py`.
## [2026-09-24] DEC-UPTM-007 — evidence now knows when it stopped being current; P12 still does not move

**Decided:** Founder GO for STALE invalidation. Built as `UPTM-007`,
preregistered in `docs/specs/UPTM-007-stale-invalidation.md` before any code
existed (P4).

**What it does.** The enforcement evidence artifact carries a sha256 of every
file it depended on, and `staleness()` answers `CURRENT` / `STALE` / `UNKNOWN`
against the tree. Expiry says how old an artifact is; this says whether it still
describes the system. An artifact can sit well inside its seven days and
describe a gate that has since been rewritten.

**The dependency set is derived, never typed.** Walking `runner/**.py`,
`capital-rules.json`, `CONSTITUTION-CAPITAL.md` and `prompt-stacks/**`. A list
someone must remember to update is the same failure as a status word someone
types, and criterion A6 is the one that proves the difference: a new `runner`
module is picked up with no edit to the dependency logic. Over-inclusion is
deliberate — a needless file costs one regeneration, a missing file leaves
evidence green after the thing it describes changed, which is the P12 violation
itself.

`UNKNOWN` is not a soft `CURRENT`, and a deleted dependency is `UNKNOWN` rather
than `STALE`: absence is not a measurement.

**Also built: the determinism declaration.** P12's violation clause forbids
calling a result reproducible without declaring uncaptured inputs. The manifest
now names what is captured and what is not — the wall clock, the Python version
and packages, the runtime identity, anything broker-side.

### A correction I owed the Founder

I described STALE as *"the last half holding P12 at PARTIAL."* Reading P12's
text disproved that: it also demands the determinism declaration, which was
missing too. That correction is written into the spec's §0, before the code, not
discovered afterwards.

### P12 stays PARTIAL, and the reason is measured

`ENFORCED` means *no route to `PASS` while violating the principle* — routes
through `evaluate_gate`. The gate does not read dependency digests from the
evidence it is handed, because gate evidence does not carry them. So no P12
route can be demonstrated, P12 has none in the registry, and criterion **C1
fails**. Per C2 the status does not move and the spec records the failure rather
than being amended to match what was built.

Closing C1 means making `dependencies` a required field of gate evidence and
denying on anything but `CURRENT` — the shape APS-001 used for `prompt_stack`.
That is a contract change affecting every producer, and it is a separate wall
with its own GO.

### Unchanged

`LIVE_TRADING` stays `false`. `CONSTITUTION-CAPITAL.md` v1.0 stays LOCKED. P8
and P10 keep their status; `enforced_principles()` is still `['P8', 'P10']` and
`unproven_claims()` is empty.

**Artifacts:** `docs/specs/UPTM-007-stale-invalidation.md` ·
`runner/staleness.py` · `runner/enforcement.py` (manifest `dependencies`,
`determinism`) · `tests/test_staleness.py`. Measured: 371 passed; live artifact
`CURRENT` → `STALE` on a real edit to `runner/gates.py` and to the constitution,
`CURRENT` again on restore.

---

## [2026-09-24] DEC-UPTM-APS-R3 — stack-body digest drift is a route

**Decided:** a change to a stack's canonical body that leaves
`prompt-stacks/index.json` `body_sha256` stale is route `PS-R3` on the existing
guard `APS-001`. It is not a new principle, it is not `ENFORCED`, and it does
not enter `capital-rules.json`.

The unit test `test_stack_body_change_without_manifest_update_invalidates_evidence`
already rejected that drift. It is not the enforcement manifest. `PS-R1` and
`PS-R2` stay green if `enforce_declared_body_digest` is deleted, because neither
submits a drifted body. A check whose removal the route manifest does not see
is the omission `DEC-UPTM-APS` exists to close.

Criteria fixed before the measurement:

- `PS-R3` denies with `prompt stack 00 digest mismatch`.
- Evidence is assembled from the real stack, and only then is the body shown to
  the gate. Drifting during assembly would write the new digest into the
  binding and the route would pass.
- Neutering `validate_prompt_stack_binding` opens `PS-R3`. The `prompt_stack`
  key is present, so this is not the `PS-R1` double hold.
- Neutering only `enforce_declared_body_digest` does not open `PS-R3`. The
  binding still carries the pre-drift digest, and the field comparison denies
  with `stack_digests mismatch`. That backstop stays out of `REDUNDANT_GUARDS`:
  the route's own expect string is the declared-digest raise, so retargeting
  the string at the backstop fails `denied_by_its_own_check`.
- `enforced_principles()` stays `P8` and `P10`.

**Measured:** `PS-R3` returns `FAIL` with
`fail-closed: prompt stack 00 digest mismatch`. The loader message does not
repeat `fail-closed:`; the gate adds that prefix to every structural error.
With `enforce_declared_body_digest` removed, the same evidence still returns
`FAIL`, now with `fail-closed: prompt_stack stack_digests mismatch` and
`fail-closed: prompt_stack assembled_prompt_digest mismatch`.
`enforced_principles()` stayed `['P8', 'P10']`. The registry is 20 routes.

**Artifacts:** `runner/prompt_stacks.py` (`enforce_declared_body_digest`) ·
`runner/enforcement.py` (`PS-R3`, `route_guard`) ·
`tests/test_enforcement_evidence.py`.
## [2026-09-24] DEC-UPTM-EXPIRY — evidence lives seven days, because the drill does

**Decided:** `evidence_expiry_days: 7`.

**Why seven and not a round number.** It is `kill_switch_drill_cadence_days`.
Enforcement evidence must never outlive the drill it rests on; if it could, a
valid-looking artifact would be propped up by a drill that had already gone
stale. Tying the two to one rhythm removes that case without a separate rule
saying so, and a test now fails if the two numbers ever drift apart.

### Setting the number was not the whole job

`evidence_expiry()` returned the string `"7 days from generated_at"`. That reads
like an expiry and can be compared to nothing. Writing the Founder's number into
a field that no code could evaluate would have produced a P12 that looked
satisfied and checked nothing — the same defect as a status word nobody earned,
which is the defect this whole wall exists to catch.

So `expires_at` is now a timestamp computed from `generated_at`, and
`expiry_status()` answers **`VALID` / `EXPIRED` / `UNKNOWN`** for an artifact at
a given time. `UNKNOWN` is not a soft `VALID`: no expiry, an unparseable one, or
one without a timezone all mean the artifact has not been shown to be current,
and under `runner.verdict` that dominates `PASS` and denies.

The lifetime itself is still never defaulted. Missing, zero, negative, boolean,
string or fractional all yield `None` — the Founder sets it or there is none.

### P12 does not become ENFORCED, and this says so out loud

P12 is *Evidence Has Commit & Expiry*. Both halves of the name are now real: the
commit is read from the repository (Rule A), the expiry is a timestamp that can
be evaluated. But the principle's recorded mechanism also names **STALE
invalidation on dependency change**, and that is not implemented. Evidence can
sit well inside its seven days and describe code that has since moved.

**P12 stays `PARTIAL`.** A test asserts it, and `capital-rules.json` carries the
reason in `evidence_expiry.does_not_satisfy_p12` rather than leaving the next
reader to infer why a parameter was set and nothing changed. Closing that
remaining half is a separate wall and has not been preregistered.

### Unchanged

`LIVE_TRADING` stays `false`. `CONSTITUTION-CAPITAL.md` v1.0 stays LOCKED. P8
and P10 keep their status for the reasons UPTM-005 and UPTM-006 established. No
capability is granted; an expiry narrows what evidence can claim, it does not
widen what the Runner may do.

**Artifacts:** `constitution/capital-rules.json` (`evidence_expiry_days`,
`evidence_expiry`) · `runner/enforcement.py` (`evidence_expiry_days`,
`evidence_expiry`, `expiry_status`, manifest `expires_at` / `expiry_days`) ·
`tests/test_enforcement_evidence.py`. Measured: 348 passed; expiry VALID at
+6d, EXPIRED at +8d, UNKNOWN on absent, unparseable and naive values.

---

## [2026-09-24] DEC-UPTM-RULEA — Evidence Rule A applies here, in one half of two

**Decided:** question 4 of the governance map. Evidence Rule A
(`onlinovosk-bit/onlinovosk-bit-uptm`, `docs/EVIDENCE_RULE_A.md`) applies to
`uptm-runner` — **half of it.** Which half, and why the other half does not, is
written in `docs/evidence-rule-a.md` rather than left to be re-derived.

**Adopted.** The evaluated head is read from the repository, never asserted by
the caller. `enforcement-evidence` no longer takes `--commit`. It reads
`git rev-parse HEAD`, requires a clean working tree, records `null` with a
stated reason when no head can be established, and treats a supplied
`--expect-head` as a cross-check in which a disagreement is a dispute and
neither value wins. CI passes no commit at all, so it cannot tell the artifact
what it evidences.

**Not adopted, conditionally.** The ban on a field meaning "the commit that
contains me" needs a tracked artifact to be meaningful. `evidence/enforcement/`
is ignored and never lands, so the self-SHA regress has nowhere to start. The
exemption rests on that condition and a test fails on the day it stops holding.

### The defect was real and I had named it wrongly

The governance map, merged this morning, said the manifest "can attest to its
own freshness, the exact thing Rule A exists to forbid." That was too strong.
The manifest is never committed, so it cannot attest to its own containing
commit at all.

The hole was adjacent: the commit was **caller-asserted and unchecked**, so a
manifest could name a commit whose code the routes had never run against, and
nothing downstream could tell. That hole is now closed.

The overstatement is corrected **in place, with the original wording left
visible** in the map. A map that silently repairs itself is worth less than one
that shows where it was wrong — and this is the third claim of mine in two days
that measurement refuted, after the P10-R2 conditional guard and the PS-R1
prediction. The pattern is the same each time: plausible reasoning, stated
confidently, never run against the thing it described.

### Unchanged

No principle changes status — P8 and P10 are `ENFORCED` for the reasons UPTM-005
and UPTM-006 established, and neither depends on this. `evidence_expiry_days` is
still unset and P12 is still `PARTIAL`. The other four governance questions are
still open. `LIVE_TRADING` stays `false`; `CONSTITUTION-CAPITAL.md` v1.0 stays
LOCKED.

**Artifacts:** `runner/provenance.py` · `runner/enforcement.py` (`manifest`) ·
`runner/cli.py` · `.github/workflows/pytest.yml` · `docs/evidence-rule-a.md` ·
`tests/test_evidence_rule_a.py` · corrected `docs/architecture/governance-map.md`.
Measured: 343 passed; `enforcement-evidence` exits 1 on a dirty tree and on a
disputed head.

---

## [2026-09-24] DEC-UPTM-APS — APS-001 is a guard, not a principle; and every guard must be routed

**Decided:** the mandatory `prompt_stack` evidence binding (APS-001) is a
**guard**, not a constitutional principle. It appears nowhere in
`capital-rules.json`, it advances no principle's status, and removing it lets no
kill-switch or capital violation through. It protects evidence integrity, which
is a different job from the one P1–P14 describe.

That classification is deliberate and is the reason the second half of this entry
exists.

### Why a guard that enforces no principle still has to be routed

UPTM-006 makes `ENFORCED` an earned status by enumerating **routes**: concrete
evidence a caller could submit while violating a principle, each one required to
be denied by its own named check. The claim is *there is no route to PASS while
violating this*.

Because APS-001 enforces no principle, nothing in that scheme required a route
for it. So none was written. For the hour between the binding landing and this
decision, the enforcement evidence would have stayed green if the binding check
had been deleted — **a guard nobody routes is a guard whose removal is silent.**

Two routes now name it:

| route | evidence submitted | denied by |
|---|---|---|
| `PS-R1` | gate evidence with no `prompt_stack` binding at all | `prompt_stack` |
| `PS-R2` | a binding whose `assembled_prompt_digest` does not match the stacks it names | `assembled_prompt_digest mismatch` |

### The standing rule this establishes

**Every group of routes beyond the `ENFORCED` principles must be declared in
`NON_PRINCIPLE_GUARDS`, with a written reason for existing.** The coverage test
fails on any undeclared group.

The rule cuts both ways, which is the point. It stops the registry quietly
accumulating routes nobody decided to add, and it stops a guard being added to
the gate with no route naming it. Declaring `APS-001` there is an act of
classification the file now forces someone to perform, rather than a status word
someone typed.

### A prediction that was written four times and refuted by the run

Written alongside the routes: neutering `validate_prompt_stack_binding` alone
would open both. **Measured: false for PS-R1.** Dropping the key trips the
required-field list in `validate_evidence_structure` as well, and each mechanism
denies on its own:

```
PS-R1  structure: ['missing field: prompt_stack', 'prompt_stack binding required']
       binding  : ['prompt_stack binding required']
PS-R2  structure: ['prompt_stack assembled_prompt_digest mismatch']
       binding  : ['prompt_stack assembled_prompt_digest mismatch']
```

Kept in `REDUNDANT_GUARDS` with the measurement and the date, surfaced in the
manifest as `redundant_guard`, and asserted in both directions. The test was
corrected to what the gate does, rather than the measurement loosened to what the
test had guessed. This is the second entry of its kind after the P10-R2
correction, and both stay in the code: a wall whose purpose is that claims must
be checked does not get to drop its own failed claim out of the record.

### Built by two sessions, an hour apart

The binding was built in one session (#18) and routed in another (#19). Neither
was wrong; the gap between them was. This is the same structural problem recorded
in `DEC-UPTM-DUP` — parallel sessions working one backlog with no shared claim on
the work — showing up as an **omission** rather than a duplicate. `NON_PRINCIPLE_GUARDS`
is the narrow fix: it makes this particular omission fail a test instead of
passing quietly. It does not fix the general problem, which is still open.

### Unchanged

No principle's status changes. UPTM-006 still advances nothing — it makes
existing claims checkable, which is smaller than making them true.
`LIVE_TRADING` stays `false`. `CONSTITUTION-CAPITAL.md` v1.0 stays LOCKED. No
Founder parameter was consumed: `evidence_expiry_days` is still unset and P12 is
still `PARTIAL`.

**Artifacts:** `runner/enforcement.py` (`NON_PRINCIPLE_GUARDS`,
`REDUNDANT_GUARDS`, `PS-R1`, `PS-R2`) ·
`tests/test_enforcement_evidence.py` · PRs #18 and #19, both on `main` at
`30e18ed`. Measured there: 334 passed, 19 routes, `unproven_claims: []`,
`routes_reaching_pass: []`.

---

## [2026-09-23] DEC-UPTM-004 — the validation tranche is set; WALL 2 is open

```yaml
validation_capital:
  currency: EUR
  amount: 700
  applies_to:
    - aggregate_open_exposure
    - cumulative_realised_loss
```

Set by the Founder 2026-09-23, superseding `DEC-UPTM-004-PRE`, where these were
preregistered but deliberately unwritten. **Writing them is the act that opens
WALL 2**, and it is why they were held back until UPTM-003 and the enforcement
evidence were done — the order the Founder set.

- **`per_position_at_risk` is not a separate cap**, by decision. It is covered by
  the stricter aggregate-open-exposure limit, so a second number would say less
  than the first.
- **PnL may be reported; profit and loss may not be an acceptance criterion.**
  €700 is the size of the test, not of the opportunity. A result that passes
  because it made money has measured the wrong thing. `VC-R1` and `VC-R2`
  enforce this, and UPTM-006 routes `P10-R5` and `P10-R9` prove they do.

**What setting it changed, measured rather than assumed:**

- Five new enforcement routes became possible (`P10-R4`, `R6`–`R9`). Until there
  was a ceiling there was nothing to step over: `VC-P1` denied every capital
  gate on the unset tranche before any other check was reached.
- `P10-R5` was unblocked. It had been recorded as unable to demonstrate its own
  guard for exactly that reason.
- It exposed a defect in UPTM-006's own capital fixture, which had invented pack
  field names the detector does not read. Nothing had ever got far enough to
  read them.

**And it refuted a prediction this project had written down four times.** The
claim was that `P10-R2` is guarded twice only because the tranche is unset, and
that setting it would leave one guard. Measured after: false — that route's
second guard is `VC-P2`, which is structural. Recorded in
`runner/enforcement.py` as `CORRECTED_PREDICTIONS`, under test.

**Artifacts:** `constitution/capital-rules.json` · `runner/enforcement.py` ·
`docs/specs/UPTM-006-enforcement-evidence.md`.

---

## [2026-09-23] DEC-UPTM-W8 — W8 specification accepted with two amendments; implementation still refused

**Decided:** accept the W8 specification review
(`onlinovosk-bit-uptm/docs/W8_SPECIFICATION_REVIEW.md`, PR #27 in that
repository) with two additions, and **do not implement W8 even so**.

**Amendment 1 — P2, Same Validated Path.** The specification asked for *"a single
deterministic end-to-end integration path"* without requiring it to be the path a
real run would take. An integration harness is by construction a mechanism for
producing a second code path. Now required: the same entrypoints as the paper
path, an enumerated list of every deliberate divergence with what each could
hide, and a test showing an unlisted divergence being caught.

**Amendment 2 — P13, No Model in Pre-Trade Path.** The specification restricted
*which strategy* may be promoted, not *what kind of thing* may sit between a
decision and its execution. Now required: no non-deterministic model in that
path, the pre-trade call chain recorded in the evidence, and determinism
demonstrated by a byte-identical repeat run rather than asserted.

Both principles are `MISSING` — enforced nowhere in either repository — which is
why they had to be written into the contract rather than assumed.

**Implementation refused, and the reason sharpened.** Not "a good stopping
point". P2 is unenforced, so an integration harness built now would produce a
result that does not describe the path a real run takes — and the Safety
Envelope cannot protect against that, because such a run costs the same money
and answers a different question. The cheaper order is P2 first.

**Two things measured while reviewing it, both worth keeping:**

- The specification is good, and in one respect better than this repository's
  own work. Evidence Rule A forbids an artifact from carrying any field meaning
  "the commit that contains me"; the UPTM-006 manifest here takes its commit as
  a CLI argument and can therefore attest to its own freshness. That is a real
  defect in UPTM-006, found by reading the other repository's rules.
- **"W7 PASS" does not mean the W7 wave passed.** `W7-H1` and `W7-H2` are two
  defensive tests. The artifact carrying them records `gate_status: UNKNOWN`,
  scopes itself to waves W1 and W4, and says in its own field: *"Do not start W8
  or W9 from this defensive re-verification evidence."* The trading repository's
  README agrees — *"Wave 7: Red Team expansion is not started."*

**Artifacts:** `onlinovosk-bit-uptm/docs/W8_SPECIFICATION_REVIEW.md` §Amendments
on acceptance · `docs/architecture/governance-map.md`.

---

## [2026-09-23] DEC-UPTM-MAP — the two repositories are mapped; five questions are left open

**Decided:** write down which constitution governs which system, because nothing
did.

Measured: the W8 specification mentions P1–P14, `validation_capital` and the kill
switch exactly **zero** times, and `onlinovosk-bit-uptm` has no `constitution/`
directory. Two sets of rules, two sets of `PASS` verdicts, no reference in either
direction.

**The gap in one sentence:** the constitution is enforced against evidence
documents, and nothing requires the trading system to produce one.

**Recorded in `docs/architecture/governance-map.md`:** what each repository
holds, where authority actually sits, and the name collisions — `W7` meaning two
different waves, "evidence" meaning two different contracts, and €700 (the
validation tranche here) versus €750 (the paper account's capital there) being
different numbers that nothing relates.

**Five questions the map deliberately does not answer**, because they are Founder
decisions: whether a trading-system wave gate must satisfy the capital
constitution; which repository's verdict wins on disagreement; how €700 and €750
relate; whether Evidence Rule A applies here; and which wave vocabulary is
canonical.

**Not an amendment.** `CONSTITUTION-CAPITAL.md` v1.0 stays LOCKED and unchanged;
no P12 invalidation follows.

**Artifact:** `docs/architecture/governance-map.md`.

---

## [2026-09-23] DEC-UPTM-005 — the scope declaration, and what it unlocked

**Decided:** the evidence scope declaration is mandatory, and **its absence
resolves to `UNKNOWN`, not to "not applicable"** (Founder, 2026-09-23).

That single choice is what moved **P8 and P10 to `ENFORCED`**. Both had been
held at `PARTIAL` for one stated reason: evidence that simply omitted the
`kill_switch` pack, or never set `capital_gate`, was never examined. A principle
a caller can step around by leaving a key out is not enforced, whatever the
detector does when the key is present. Making the declaration unconditional
closes that.

**Enforcement summary:** `ENFORCED 2 / PARTIAL 7 / DECLARATIVE 1 / MISSING 4`.
The first two `ENFORCED` entries this system has had.

**Breaking, deliberately:** evidence written before this wall carries no scope
and denies until declared. `runner.fsm.run_baseline_ack` now emits the
declaration, so wave 0 is declared at the producer rather than patched
afterwards.

**The limit that remains** is recorded and is the right one: the wall makes the
declaration mandatory and self-consistent, and cannot tell whether it is *true*.
A gate declaring `live_bearing: false` while actually bearing LIVE has not
avoided the check — it has lied in signed evidence.

**Artifacts:** `docs/specs/UPTM-005-evidence-scope-declaration.md` ·
`runner/detectors/scope.py` · `runner/gates.py` · `runner/fsm.py` · PR #10.

---

## [2026-09-23] DEC-UPTM-DUP — UPTM-003 was built twice, in parallel

**What happened.** Two sessions implemented WALL 1 at the same time, neither
aware of the other. One landed via PR #8 (merged to `main`, `97acd62`); the other
became PR #9, which sat green and mergeable for a day and was then in conflict
against a `main` that had grown its own kill-switch detector — and a
validation-capital detector besides.

**Decided:** `main`'s implementation stands. PR #9 **closed unmerged**. Two
detectors for one principle do not merge, and resolving the conflict would have
produced exactly that.

**Ported from the closed branch, on instruction, because both were in the
original brief for this wall and `main` lacked them** (PR #12):

- **KS-D5** — a drill is invalidated by a change to `deployment_ref`,
  `credentials_ref` or `gate_path_digest`, independently of the cadence window.
  `main`'s KS-D4 covered only the stop path.
- **KS-D6** — deployment independence as a **dated operator attestation**,
  checked for existence and currency, never for truth. `main` declared this as a
  limit but did not check it.

Nothing else was ported: the machine-readable spec JSON, the
preregistration-integrity tests, the omission-bypass closure under a LIVE
capability claim, and the malformed-shape hardening stay in the closed branch.

**Two things `main` does better**, recorded so the closure is not read as a
verdict on quality:

- `can_write` probes writability **in fact**, rather than trusting a declared
  `runner_write_paths` list.
- `gate_bypass_attempt` was left `DECLARATIVE`. The closed branch promoted it to
  `PARTIAL` on the strength of a single detection path; that promotion did not
  survive, and should not have been made.

**The cost, stated plainly.** This is the second time the same failure has been
recorded on this stack — `RealitkaAI/memory/decisions.md` carries
*"Bus was designed twice"* from 2026-09-21. Two sessions working the same
backlog without a shared claim on the work produce two implementations and one
of them is thrown away. That is the finding, not the detector.

**Artifacts:** PR #8 (merged) · PR #9 (closed) · PR #12 (ported checks).

---

## [2026-09-23] DEC-UPTM-003 — P8 Independent Kill Switch: cadence and ceiling

**Parameter in force:**

```yaml
live_capability:
  kill_switch_drill_cadence_days: 7
```

Set by the Founder 2026-09-23. **This supersedes the 14 given on 2026-09-22**,
against which the closed PR #9 was built. Both values were Founder-attributed;
the later one governs. Recorded because two dated parameters for one safety
control is exactly the thing that becomes unreconstructable in a month.

**Re-verification beyond the window.** A drill is required again immediately —
however recent the last one — after a change to the stop path (KS-D4) or to
`deployment_ref`, `credentials_ref` or `gate_path_digest` (KS-D5, PR #12). A
drill against a deployment that no longer exists proves nothing about the one
that does.

**The boundary the Founder drew:** *deployment independence is not to be
certified by code.* Whether the kill switch runs outside the Runner's process,
credentials and failure domain stays an **explicit operator attestation carrying
a date**. KS-D6 checks that one exists, is dated, is not dated in the future,
and is not older than the deployment it describes. It cannot check that it is
true, and no test in this repository claims otherwise.

**Status:** `DECLARATIVE → PARTIAL` with PR #8, then **`PARTIAL → ENFORCED`**
with UPTM-005 (PR #10, see `DEC-UPTM-005`). The ceiling recorded on 2026-09-22 —
that `PARTIAL` was as far as this could go — held only for as long as the
omission bypass did. Closing the hole, rather than adding checks, is what
enforced the principle.

Neither KS-D5 nor KS-D6 moved that status. They narrow what a valid drill and a
current attestation mean; P8 is enforced for a different reason entirely.

**Artifacts:** `docs/specs/UPTM-003-kill-switch-independence.md` ·
`runner/detectors/kill_switch.py` · `runner/gates.py` ·
`constitution/capital-rules.json`.

---

## [2026-09-22] DEC-UPTM-004-PRE — Validation capital parameters, preregistered and still unset

```yaml
validation_capital:
  currency: EUR
  amount: 700
  applies_to:
    - aggregate_open_exposure
    - cumulative_realised_loss
```

- **`per_position_at_risk` is not a separate €700 cap.** It is implicitly covered
  by the stricter aggregate-open-exposure limit.
- **PnL may be reported. Profit and loss may not be used as an acceptance
  criterion** of the validation experiment. €700 is the size of the test, not the
  size of the opportunity; a result that passes because it made money has
  measured the wrong thing.

**State of the repository:** the UPTM-004 **detectors exist** on `main` (PR #8,
`1227ded`), are invoked by the gate, and P10 is now `ENFORCED` (UPTM-005). The
**parameters above are still not set** — `validation_capital.amount`,
`.currency` and `.applies_to` are `null`/`[]`, VC-P1 returns `UNKNOWN`, and every
capital gate denies until the Founder sets them.

`ENFORCED` and *unset* are not in tension: the machinery is enforced, and it is
enforcing a denial. That is the correct reading of a capability that has not been
granted.

That is the correct state. `capital-rules.json` records why: the constitution
names €700 in P10's *heading*, and a heading is prose. The value that gates money
is set deliberately, not parsed out of a title.

**Ordering, as decided:** UPTM-003 → full ENFORCEMENT evidence → *then*
UPTM-004. Writing these parameters into `capital-rules.json` is the act that
starts WALL 2, so it has not been done. The detectors landing early does not
advance that order; it only means the code is waiting.

**Artifact:** detectors on `main`, P10 `ENFORCED`. Parameters: none — this half
is still a plan, and says so.

---

## [2026-09-22] DEC-UPTM-LOG — UPTM decisions are recorded in this repository

**Decided:** UPTM decisions go in `uptm-runner`, not in `RealitkaAI/memory/`.

Existing UPTM references in RealitkaAI (`memory/decisions.md`,
`memory/session-summary.md`, `docs/prompts/multi-agent-protocol-v0/`,
`docs/architecture/2026-09-21-uptm-path-to-micro-live.md`) are historical record
and were left untouched. Moving or deleting them is a separate decision.

**Artifact:** this file.
