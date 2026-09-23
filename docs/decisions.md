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

**Status:** `P8: DECLARATIVE → PARTIAL`, landed with PR #8.
`PARTIAL` is the ceiling. It is not `ENFORCED` for a stated reason:
evidence that omits the `kill_switch` pack is never examined
(`open_limits.omission_bypass`). A principle a caller can step around by leaving
a key out is not enforced, whatever the detector does when the key is present.

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
`1227ded`) and are invoked by the gate. The **parameters above are not set** —
`validation_capital.amount`, `.currency` and `.applies_to` are `null`/`[]`, VC-P1
returns `UNKNOWN`, and every capital gate denies until the Founder sets them.

That is the correct state. `capital-rules.json` records why: the constitution
names €700 in P10's *heading*, and a heading is prose. The value that gates money
is set deliberately, not parsed out of a title.

**Ordering, as decided:** UPTM-003 → full ENFORCEMENT evidence → *then*
UPTM-004. Writing these parameters into `capital-rules.json` is the act that
starts WALL 2, so it has not been done. The detectors landing early does not
advance that order; it only means the code is waiting.

**Artifact:** detectors on `main`. Parameters: none — this half is still a plan,
and says so.

---

## [2026-09-22] DEC-UPTM-LOG — UPTM decisions are recorded in this repository

**Decided:** UPTM decisions go in `uptm-runner`, not in `RealitkaAI/memory/`.

Existing UPTM references in RealitkaAI (`memory/decisions.md`,
`memory/session-summary.md`, `docs/prompts/multi-agent-protocol-v0/`,
`docs/architecture/2026-09-21-uptm-path-to-micro-live.md`) are historical record
and were left untouched. Moving or deleting them is a separate decision.

**Artifact:** this file.
