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

*(filled in after implementation)*

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
