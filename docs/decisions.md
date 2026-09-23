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

## [2026-09-22] DEC-UPTM-003 — P8 Independent Kill Switch: build, with a named ceiling

**Decided:** build WALL 1 / UPTM-003 in full — detector, gate wiring, mutation
proof, `capital-rules.json` update.

**Parameter set by the Founder:**

```yaml
live_capability:
  kill_switch_drill_cadence_days: 14
```

**Re-verification beyond the window.** A drill is required again immediately —
however recent the last one — after a change to `deployment_ref`,
`credentials_ref`, `kill_switch_path_digest` or `gate_path_digest`. A drill
against a deployment that no longer exists proves nothing about the one that does.

**The boundary the Founder drew:** *deployment independence is not to be
certified by code.* Whether the kill switch runs outside the runner's process,
credentials and topology stays an **explicit operator attestation carrying a
date**. KS-D4 checks that one exists, is dated, and does not predate the last
relevant change. It cannot check that it is true, and no test in this repository
claims otherwise.

**Status moved:** `P8: DECLARATIVE → PARTIAL`,
`gate_bypass_attempt: DECLARATIVE → PARTIAL`.
Summary: `ENFORCED 0 / PARTIAL 8 / DECLARATIVE 1 / MISSING 5`.

Moved **after** the suite was green, on the Founder's condition that the status
change only if every preregistered UPTM-003 criterion actually passes. `PARTIAL`
is the ceiling; `upgrade_by_green_tests_forbidden` stays `true`.

**Artifacts:** `docs/specs/UPTM-003-kill-switch.{md,json}` ·
`runner/detectors/kill_switch.py` · `runner/gates.py` ·
`constitution/capital-rules.json` · `audits/uptm/uptm003-implementation-report.md` ·
PR #9 (`5c3daac`, 236 tests passing).

### Why this is not a P14 amendment

`CONSTITUTION-CAPITAL.md` v1.0 is **LOCKED** and its text is unchanged, so no
`constitution_version` bump and no PASS results invalidated to `STALE` under P12.

`kill_switch_drill_required: true` was already in `live_capability`; the cadence
sat at `null`. Filling in a parameter the constitution already demanded is
parameterisation, not amendment. Recorded here so that nobody has to reconstruct
the distinction later.

### Defect found while building, kept on the record

The first design let KS-S1 read the stop state and KS-S2 read it again.
Acceptance case MUT-03 — a reader that writes — **passed when it should have
failed**: the first read had already made the change, so the second read's
digests matched. The stop state is now read exactly once per evaluation,
bracketed by a digest either side, and `test_the_stop_state_is_read_exactly_once`
pins it.

The point worth keeping: the mutation case caught this, not the design review.

---

## [2026-09-22] DEC-UPTM-004-PRE — Validation capital parameters, preregistered

**Preregistered, not built.** WALL 2 / UPTM-004 (P10) is not started. These
parameters are recorded now so the acceptance criteria cannot drift once evidence
starts arriving (P4).

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
  size of the opportunity; a result that passes because it made money is a
  result that has measured the wrong thing.

**Ordering, as decided:** UPTM-003 → full ENFORCEMENT evidence → *then* UPTM-004.
The middle step is its own deliverable and is not the same as merging PR #9.

**Artifact:** none yet. This is a plan, and says so.

---

## [2026-09-22] DEC-UPTM-LOG — UPTM decisions are recorded in this repository

**Decided:** UPTM decisions go in `uptm-runner`, not in `RealitkaAI/memory/`.

Existing UPTM references in RealitkaAI (`memory/decisions.md`,
`memory/session-summary.md`, `docs/prompts/multi-agent-protocol-v0/`,
`docs/architecture/2026-09-21-uptm-path-to-micro-live.md`) are historical record
and were left untouched. Moving or deleting them is a separate decision.

**Artifact:** this file.
