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
