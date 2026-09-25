# Governance map — which constitution governs which system

**Status:** written 2026-09-23 on Founder instruction. Descriptive, not
normative: it records what is true today and names what nobody has decided. It
grants nothing, changes no status, and is not an amendment under P14.

## Why this exists

Two repositories. Two sets of rules. Two sets of `PASS` verdicts. Neither cites
the other anywhere, in either direction, except one line in this repository's
README.

Measured 2026-09-23:

```
W8_SPECIFICATION_REVIEW.md mentions of P1–P14 / validation_capital / kill switch : 0
onlinovosk-bit-uptm/constitution/                                                : does not exist
```

The risk this creates is not that either side is wrong. It is that **both can be
green at once while nothing is checking the whole**. A system with two
independently green halves and no map between them is not governed; it is
unsupervised in a way that looks supervised.

## The two repositories

| | `uptm-runner` | `onlinovosk-bit-uptm` |
|---|---|---|
| What it is | Control plane. Governance, gates, evidence rules | The trading system itself |
| Visibility | public | private |
| Holds the constitution | **yes** — `constitution/CONSTITUTION-CAPITAL.md`, P1–P14 | no |
| Holds the money rules | `validation_capital`, the €700 tranche | Safety Envelope, the €750/3.75/15 limits |
| Holds the decisions log | **yes** — `docs/decisions.md` | no |
| Waves | `waves/wave0–7.yaml` — the control plane's own build | `W0–W9` — the trading system's build |
| Evidence schema | `schemas/evidence.schema.json` | `gate_evidence_v2_rule_a` |
| Enforcement states | `ENFORCED / PARTIAL / DECLARATIVE / MISSING` | `PASS / FAIL / UNKNOWN` per gate |

`uptm-runner`'s README already says it: *"Control-plane / orchestration scaffold
around UPTM. This is not a git clone of UPTM."* That is the whole of the written
relationship, and it describes the code, not the authority.

## Name collisions — read this before quoting a status

These are the traps. Each has already caused a real error.

### "W7" means two different things

| | |
|---|---|
| `uptm-runner` `wave7.yaml` | `exit_and_archive` — the control plane's last build wave |
| `onlinovosk-bit-uptm` `W7.json` | `INDEPENDENT RED TEAM` — a trading-system wave |

A status line saying "W7 PASS" is ambiguous between them. This document's author
conflated the two earlier the same day.

### "W7 PASS" is not a wave verdict

Measured from `evidence/uptm_machine_gate_2026-09-20.json`, the only machine gate
artifact in the trading repository:

```
w7_security_status   W7-H1 = PASS, W7-H2 = PASS
critical / high / unknown   0 / 0 / 0
gate_status          UNKNOWN          ← the artifact's own overall verdict
wave                 ["W1", "W4"]     ← not W7
next_red_team_task   "None in this PR. Do not start W8 or W9 from this
                      defensive re-verification evidence."
```

`W7-H1` and `W7-H2` are **two defensive tests** — unauthorized mint and anchor
refresh are blocked. They pass. The **W7 wave** is a different thing, and the
trading repository's own README says of it: *"Wave 7: Red Team expansion is not
started."*

Both statements are true. "W7 PASS" as shorthand for the wave is not. The
artifact that carries those PASSes says in its own field not to start W8 from
them.

### "Evidence" means two different contracts

`onlinovosk-bit-uptm` runs Evidence Rule A: the artifact carries
`implementation_sha` and **must not** carry any field meaning "the commit that
contains me". The evaluated HEAD is supplied externally by CI.

`uptm-runner` has no equivalent rule. Its UPTM-006 enforcement manifest takes its
commit as a CLI argument — which means **it can attest to its own freshness**,
the exact thing Rule A exists to forbid. Rule A is the better contract and this
repository does not have it.

> **Corrected 2026-09-24, after the Founder decided question 4.** The paragraph
> above is left as written because a map that silently repairs itself is worth
> less than one that shows where it was wrong. It overstated the defect. The
> manifest is never committed (`evidence/enforcement/` is ignored), so it cannot
> attest to its *own containing commit* and the self-SHA regress Rule A forbids
> cannot arise here. The real hole was adjacent and is now closed: the commit was
> **caller-asserted and unchecked**, so a manifest could name a commit whose code
> the routes had never run against. The evaluated head is now read from the
> checkout, a dirty tree evidences no commit, and a supplied head that disagrees
> is a dispute in which neither value is adopted. See `docs/evidence-rule-a.md`
> for which half of Rule A was adopted and why the other half is inapplicable —
> conditionally, with a test that fails on the day the condition stops holding.

### The two capital numbers are not the same number

```
uptm-runner   validation_capital.amount   EUR 700
onlinovosk-bit-uptm   DEFAULT_CAPITAL_EUR  EUR 750   (min 500, max 1000)
```

They are not in conflict, and they are not the same thing: €700 is the size of
the validation *test* under P10; €750 is the paper account's starting capital.
**DEC-UPTM-MAP-Q3 leaves that relation unadopted.** Whether the tranche is a
ceiling on the envelope, a subset of it, or an independent limit is not decided
here. Neither number is rewritten into the other.

## Where authority actually sits, today

- **P1–P14 govern the trading system**, not the control plane. P8 is about a
  kill switch on a runner that trades; P10 is about capital at risk. Neither
  describes anything `uptm-runner` does by itself.
- **The enforcement is in `uptm-runner`.** The detectors, the gate, the routes,
  the `ENFORCED` claims.
- **The thing being governed is in `onlinovosk-bit-uptm`.** The risk engine, the
  ledger, the execution adapters, the Safety Envelope.
- **No artifact connects them.** `uptm-runner`'s gate evaluates evidence
  documents; nothing establishes that a trading-system run must produce one, or
  which of the trading system's own gates corresponds to which principle.

That last point is the gap in one sentence: **the constitution is enforced
against evidence, and nothing requires the trading system to produce that
evidence.**

## Open questions — Founder decisions, not inferences

Question 4 is decided below. Question 5 is not answered here.
Question 1 is recorded open: neither answer is adopted. Question 2 is recorded
open: neither repository's `PASS` wins. Question 3 is recorded open: no
relation between €700 and €750 is adopted.

1. **Does a trading-system wave gate have to satisfy the capital constitution?**
   If yes, W8 needs a `uptm-runner` evidence artifact and none is specified. If
   no, P8 and P10 are enforced against something that never runs.
   **OPEN (DEC-UPTM-MAP-Q1, 2026-09-25):** neither answer is adopted. This
   repository does not invent the evidence link, and it does not exempt a
   trading wave from the constitution.
2. **Which repository's verdict wins on a disagreement?** Both can emit `PASS`.
   Neither reads the other's.
   **OPEN (DEC-UPTM-MAP-Q2, 2026-09-25):** neither repository's `PASS` wins.
   This repository does not read the other verdict, and it does not treat its
   own `PASS` as the winner.
3. **How do €700 and €750 relate?**
   **OPEN (DEC-UPTM-MAP-Q3, 2026-09-25):** no relation is adopted. €700 stays
   the validation-test size. €750 stays the other repository's paper-account
   capital. This repository does not treat either number as a ceiling, a
   subset, or a limit on the other.
4. ~~**Does Evidence Rule A apply to `uptm-runner`?**~~ **DECIDED 2026-09-24:**
   half two (the evaluated head is read from the checkout, never asserted by the
   caller) is adopted; half one (no field meaning "the commit that contains me")
   is inapplicable while the artifact stays untracked, and a test enforces that
   condition. `docs/evidence-rule-a.md`.
5. **Which wave vocabulary is canonical?** Two systems numbering waves 0–7 and
   0–9 will keep colliding in status lines.

## What this document does not do

- Question 1 stays open under `DEC-UPTM-MAP-Q1`: neither answer is adopted.
  Question 2 stays open under `DEC-UPTM-MAP-Q2`: neither repository's `PASS`
  wins. Question 3 stays open under `DEC-UPTM-MAP-Q3`: no relation between €700
  and €750 is adopted. Question 4 is decided. Question 5 stays unanswered here.
- It does not change any principle's enforcement state.
- It does not make either repository's `PASS` mean anything it did not already
  mean.
- It is not an amendment: `CONSTITUTION-CAPITAL.md` v1.0 stays LOCKED and
  unchanged, so no P12 invalidation follows from it.

## How to use it

Before quoting a status across repositories, say which one. Before concluding
that "the system is green", check that both halves are green **and** that the
question you are asking is one either half actually answers.
