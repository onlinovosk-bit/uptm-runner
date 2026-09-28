# UPTM-015 — Closing MAP-Q1 and MAP-Q2, and the switch left off

**Status:** preregistered 2026-09-28, before the implementation exists.
**Scope:** two governance questions, the resolution they imply, and an explicit
refusal to wire it in. No market data, no trading. `LIVE_TRADING` stays `false`.

---

## §0 Why these two are not really open

Both have sat open since 2026-09-25 as if they were preferences. Neither is.
Each has exactly one answer that survives contact with principles this
repository has already adopted, and the honest work is to show the derivation
rather than to pick.

### Q1 — must a trading-system wave gate satisfy the capital constitution?

The map states the consequence of "no" itself: *"If no, P8 and P10 are enforced
against something that never runs."*

P8 and P10 are two of the **three** principles that are actually `ENFORCED`.
Answering "no" would leave the control plane enforcing nothing — and the
constitution's own SUCCESS CONDITION is enough independent evidence of
robustness, which is not a thing a runner with no subject can produce.

So **yes**, and what was actually open was never the question. It was the
*mechanism*: no artifact links a trading wave to an evidence document. Adopting
"yes" converts an open question into a **named, unmet requirement**, which is a
worse-looking and more honest state.

### Q2 — which repository's verdict wins a disagreement?

The question assumes a tie to be broken. P11 says uncertainty halts, and
`GOVERNANCE.md` C3 says silence is not permission — a sentence this
repository's own `resolve_planes` already cites in its docstring.

A disagreement between two verdicts is **not a tie. It is uncertainty.** So
neither wins: disagreement resolves to `DENY`, and so does the absence of a
counterpart verdict. Picking a winner would be inventing a rule where an
existing one already answers.

---

## §1 What this exposes, and deliberately does not fix

Today `uptm-runner` reaches `ALLOW` **without ever asking the trading system**.
Nothing reads the other repository's verdict, so absence currently behaves as
permission — the exact thing Q2's answer forbids.

Wiring this resolution into `evaluate_gate` would deny **every** current `PASS`
until the trading system produces evidence, because there is no such evidence
and `onlinovosk-bit-uptm` is not even in this session's scope. That is a large
behavioural change and a Founder decision of its own.

**So the mechanism is built and left disconnected, and a test asserts it is
disconnected** — because a switch that is off and known is safe, while a switch
that is off and forgotten is the next `DECLARATIVE` principle.

---

## §2 Preregistered criteria

| # | Criterion |
|---|---|
| **G1** | Q1 is recorded as adopted **yes** in the map and in `docs/decisions.md`, with the reason that "no" leaves P8 and P10 enforcing nothing. |
| **G2** | Q2 is recorded as adopted **neither wins**: disagreement denies and absence denies, derived from P11 and C3 rather than chosen. |
| **G3** | `resolve_cross_repository` returns `ALLOW` only when both sides allow. Asserted over the **whole cross-product** of decisions, not examples. |
| **G4** | An absent, unreadable or unrecognised verdict on either side resolves to `DENY`. Absence is not a measurement. |
| **G5** | A disagreement is reported **as a dispute**, carrying both sides and a reason, never as one side having lost. |
| **G6** | `cross_repository_status()` measures today's state rather than asserting it: no trading-system verdict is reachable from this repository, so it reads `UNKNOWN`. |
| **G7** | The closure changes **no** principle's enforcement state; a test reads `capital-rules.json` and asserts the counts are what they were. |
| **G8** | The map states the closures in **both** places it currently states the openness, so the document cannot contradict itself. A test reads the markdown. |

### Load-bearing

One case per independent mechanism, named in advance:

| # | Criterion |
|---|---|
| **L1a** | `cross-repo-absence-allows` — absence stops denying; the named tests go red. |
| **L1b** | `cross-repo-allow-overrides-deny` — one side's `ALLOW` starts overriding the other's `DENY`; the named tests go red. |
| **L2** | **The switch stays off, and a test proves it.** `evaluate_gate` must not call the new resolution, and the test fails on the day it does — so turning it on is a deliberate act with its own GO, never a drift. |

---

## §3 Result

Built on 2026-09-28. Two of five governance questions closed. **Both closures
create work rather than finishing it.**

| artifact | what it is |
|---|---|
| `docs/architecture/governance-map.md` | Q1 and Q2 recorded decided, in both places |
| `runner/cross_repository.py` | the resolution, built and disconnected |
| `tests/test_cross_repository.py` | 25 tests, each naming its criterion |
| `tests/test_governance.py` | two guards re-aimed, not deleted |
| `runner/mutation_gate.py` | L1a, L1b, and two re-aimed cases |

### Criteria, discharged

| # | how |
|---|---|
| G1 | `test_g1_*` — the map records **YES**, carries the sentence that refutes "no", and says *named unmet requirement* so the adoption cannot read as a mechanism. |
| G2 | `test_g2_*` — **NEITHER WINS**, with *a tie; it is uncertainty* and *silence is not permission* both present, so the derivation travels with the decision. |
| G3 | `test_g3_*` — parametrised over the whole `Decision × Decision` product; plus the `ALLOW` case, so this is a gate and not a wall. |
| G4 | `test_g4_*` — seven kinds of non-verdict on either side, the missing side **named** rather than counted, and an absent counterpart recorded as *not a dispute* (nobody disagreed; one side never spoke). |
| G5 | `test_g5_*` — both sides kept, `disputed: True`, `P11` in the reason, and the words *overrules*, *overrides*, *wins the* asserted **absent**. |
| G6 | `test_g6_*` — `cross_repository_status()` returns `DENY` with `missing == ("onlinovosk-bit-uptm",)`: today's gap as a value rather than a paragraph. |
| G7 | `test_g7_*` — `capital-rules.json` still reads `ENFORCED 3 / PARTIAL 6 / DECLARATIVE 1 / MISSING 4`. Closing a question moved no principle. |
| G8 | `test_g8_*` — neither question is called open anywhere, **and** Q3 and Q5 still are, so they were not swept up. |
| L1a | `cross-repo-absence-allows` (4 sentinels). |
| L1b | `cross-repo-allow-overrides-deny` (2 sentinels), independent: absence still denies when this one is gone. |
| L2 | `test_l2_the_gate_does_not_consult_the_trading_system_yet` — read from `runner/gates.py`'s AST, not from memory. |

### The finding

**`evaluate_gate` reaches `ALLOW` today without ever asking the trading
system.** Absence currently behaves as permission — the exact reading Q2's
answer forbids. Wiring the resolution in would deny every current `PASS`,
because no trading-system verdict exists and that repository is not in scope
here.

So the mechanism is built and disconnected, and **L2 asserts it stays that
way**. A switch that is off and known is safe; a switch that is off and
forgotten is the next `DECLARATIVE` principle, and this repository already has
one of those.

### Two guards re-aimed rather than deleted

`map-q1-marked-decided` and `map-q2-marked-decided` existed to stop anyone
adopting an answer the Founder had not given. Their anchors stopped matching the
moment the answers were adopted — the mutation gate refusing a stale case, doing
exactly its job.

They are re-aimed at the **new** danger rather than removed:

| was | is |
|---|---|
| `map-q1-marked-decided` — nobody may decide it | `map-q1-reopened` — nobody may quietly revert it |
| `map-q2-marked-decided` — nobody may pick a winner | `map-q2-given-a-winner` — still nobody may pick a winner, now against the recorded closure |

`test_map_q1_stays_open` and `test_map_q2_stays_open` became
`test_map_q1_is_decided_yes_and_claims_no_mechanism` and
`test_map_q2_is_decided_neither_wins`. The guards changed direction; none was
weakened, and Q2's now asserts that no side is recorded as having won.

### What was measured

- `python -m runner.syntax_gate` — every file parses.
- `python -m pytest` — 753 passed, 0 failed.
- `python -m runner.cli mutation-gate` — 27 cases, `ok: true`, no missing sentinel.

---

## §4 What this does NOT establish

- **Not that the evidence link exists.** Q1 adopted "yes"; nothing in this
  repository makes a trading wave produce an evidence artifact, and this spec
  does not build it.
- **Not that the gate now consults the trading system.** It does not, on
  purpose, and L2 asserts it.
- **Not a change to any principle's state.** P8, P10 and P12 stay `ENFORCED`;
  the four `MISSING` principles stay `MISSING`.
- **Not an amendment.** `CONSTITUTION-CAPITAL.md` v1.0 stays LOCKED, so no P12
  invalidation follows.
