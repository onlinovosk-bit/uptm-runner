# UPTM-014 — The roll rule, and the construction that rewrites its own past

**Status:** preregistered 2026-09-28, before the implementation exists.
**Scope:** how consecutive futures contracts are joined into one series, and
which joins are admissible. No market data, no detector, no backtest, no
trading. `LIVE_TRADING` stays `false`.

---

## §0 Why this is decidable now, with no data

`UPTM-013` found a second undefined term while mapping the data source: ES rolls
quarterly, so a "continuous ES series" is a **construction, not a measurement**.
The roll rule changes every price before each roll, and therefore changes every
swing `UPTM-012` would find.

It was recorded as `UNDEFINED` and deliberately not decided there, because
settling it as a side effect of picking a vendor is exactly how a modelling
choice becomes an accident. It is decidable now precisely because it needs no
data: it is a question about **information order**, and this repository already
committed to the answer.

---

## §1 The three decisions inside "the roll rule"

1. **When to roll.** Calendar offset from expiry, volume crossover, open-interest
   crossover. A calendar rule is knowable in advance; a crossover rule is
   knowable at the close of the day it happens. Both can be causal.
2. **How to join.** Raw splice, forward adjustment, back adjustment, ratio
   adjustment.
3. **Which contract is front** at any instant — a consequence of (1), not a
   separate choice.

This spec settles **(2) by argument** and leaves **(1) unset as a parameter**,
for the reason `DEC-UPTM-003` and `UPTM-012` both give: a number chosen without
data to choose it against is a fabricated parameter wearing a definition's
clothes.

---

## §2 The collision this exists to expose

`UPTM-012` committed to an invariant: **nothing is ever revised.** What is known
at `t` is a prefix of what is known later; a confirmed swing is never withdrawn,
repriced or reordered, because a withdrawn swing is one a live system may
already have acted on.

**Back adjustment rewrites the past by construction.** At each roll it shifts
every earlier bar so the seam disappears. A series built today and a series
built a quarter ago disagree about what the price was two years ago — and the
disagreement grows with every roll still to come, which is to say it depends on
the future.

This is not an exotic case. **A back-adjusted continuous file is what most
vendors ship**, and it is what a backtest usually reads.

So the choice between joins is not a matter of taste here. One of them
contradicts an invariant this repository already committed to, and the job of
this spec is to **measure that**, not to assert it.

---

## §3 Admissibility is measured, not declared

A hand-kept list of "safe" adjustment methods is the same failure as a hand-kept
dependency set: it is correct until someone adds a method and forgets the list.

So `rewrites_history` is **computed on a probe**: build the series as-of two
different times and compare the overlap. A method whose earlier bars change is
one that rewrites history, whoever wrote it and whenever it was added.

One trap, closed deliberately: **a probe containing no roll proves nothing** —
every method is stable on a series that never joins anything. Asked to measure
on a roll-free probe, the function must raise rather than return a comfortable
`False`.

---

## §4 Preregistered criteria

| # | Criterion |
|---|---|
| **R1** | A roll definition validates its inputs: an unknown adjustment, an empty schedule, or a schedule whose first segment does not start at the first bar is an error, not a coercion. |
| **R2** | The front contract at `t` is decided by the schedule alone. A calendar schedule is built from expiries known in advance, and building the series consults no bar later than `t`. |
| **R3** | `build_continuous(..., as_of=t)` returns no bar after `t`. |
| **R4** | **Prefix stability, measured.** For raw splice and forward adjustment, the series as-of `t` is exactly a prefix of the series as-of any later `t`, price for price, at every cut of a probe that contains a roll. |
| **R5** | **The counter-measurement.** For back adjustment it is *not*: a named earlier bar carries one price before the roll and a different one after. The test names the bar and both values rather than asserting inequality in the abstract. |
| **R6** | **The collision, shown.** A swing confirmed by `runner.swing` before a roll keeps its price under an admissible join and changes under back adjustment — so `UPTM-012`'s S5 is what forbids the method, not preference. |
| **R7** | `rewrites_history` is measured on a probe, refuses a roll-free probe by raising, and classifies **every** member of the adjustment enum — so a method added later is classified by measurement rather than by being remembered. |
| **R8** | **Admissible is not free.** Raw splice leaves a discontinuity at the seam and forward adjustment removes it; the size of that seam is asserted, so the remaining choice is visible as a trade-off rather than settled by this spec. |
| **R9** | `research/data_sources/es_mes_bars.json` moves its open modelling choice from `UNDEFINED` to the defined family, the contract gains `roll_parameters: UNDEFINED`, and `status.rules` still cannot move. |

### Load-bearing

Per the process fix recorded in `UPTM-013` §5: **one case per independent
mechanism, named here rather than reconciled afterwards.**

| # | Criterion |
|---|---|
| **L1a** | `roll-admissibility-always-true` — the refusal to use a history-rewriting join is removed; the named tests go red. |
| **L1b** | `roll-as-of-ignored` — the `as_of` cut is removed, so building at `t` returns bars from after `t`; the named tests go red. |
| **L2** | No market data is read and no network call is made. Every contract series is constructed inside the test file. |

---

## §5 Result

*(filled in after implementation)*

---

## §6 What this does NOT establish

- **Not which trigger, nor when to roll.** Calendar offset versus volume or
  open-interest crossover, and the offset itself, stay `UNDEFINED`: choosing
  needs data, and no data is connected.
- **Not raw splice versus forward adjustment.** Both are admissible. Which is
  right depends on how large the seams actually are, which is a measurement
  nobody can make yet.
- **Not that any series is correct.** Nothing here reads a price that came from
  outside a test.
- **Not that Quasimodo is implementable.** `status.rules` does not move.
