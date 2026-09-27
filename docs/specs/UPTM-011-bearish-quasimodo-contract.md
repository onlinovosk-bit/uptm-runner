# UPTM-011 — One pattern contract, and the root it bottoms out on

**Status:** preregistered 2026-09-27, before the implementation exists.
**Scope:** one research artifact and the status ladder it is expressed in.
No detector, no market data, no backtest, no trading. `LIVE_TRADING` stays `false`.

---

## §0 What was asked, and what is deliberately not being built

The Founder proposed turning a reversal-pattern ebook into a library of seven
formalised contracts: Head & Shoulders, Inverse H&S, Double Top, Double Bottom,
Rising Wedge, Falling Wedge, Quasimodo.

**One is being built, not seven.** Every one of the seven is defined in terms of
swing highs and swing lows — "three peaks", "two tops", `HH → HL → HH → LL → LH`.
None of them can be evaluated until *swing* is mechanically defined: how many
bars either side, what minimum amplitude, on what timeframe. Writing seven
contracts before that would be one unsolved problem written seven times.

Bearish Quasimodo was chosen over Head & Shoulders because it is stated as an
explicit sequence and therefore reaches that root fastest. H&S adds a second
undefined construction — the *neckline* — on top of the same one.

---

## §1 Provenance, stated honestly

The rules recorded here come from **the Founder's restatement of the ebook in
conversation**, not from the ebook. This runner has not read it.

That distinction is the whole point of the `source` axis in §2. A restatement is
a real, citable input; it is not a primary source. Recording it as
`VERIFIED_SOURCE` would assert a reading that never happened.

What the restatement says, kept separate from what it does not:

| stated | not stated |
|---|---|
| sequence `HH → HL → HH → LL → LH`, then short | what makes a swing a swing |
| stop modes: conservative above the HH, aggressive above the LH | entry trigger for the bearish case |
| the bullish mirror enters after a retest of the first low | target, session, instrument, timeframe |
| the ebook warns against entering before confirmation | tolerances, fees, slippage, sizing |

Anything in the right column is `UNDEFINED`. It is not inferred, not
interpolated from the bullish case, and not filled in from what such patterns
"usually" mean.

---

## §2 The status ladder: six axes, not one word

The existing candidate carries a single flat `status: UNVERIFIED`. That cannot
express "the rules are pinned down but nothing is known about whether it earns",
which is exactly the state a research candidate spends most of its life in, and
exactly the conflation that lets "verified" drift from meaning one thing to
meaning the other.

Six independent axes, each with its own lowest rung:

| axis | meaning | lowest rung |
|---|---|---|
| `source` | do we have what the author actually said | `RESTATED_SECONDHAND` |
| `rules` | are the rules mechanically evaluable | `UNDEFINED` |
| `implementation` | does code implement those rules | `NOT_STARTED` |
| `no_leakage` | proven to use only information available at decision time | `NOT_TESTED` |
| `stats` | tested out-of-sample, with a preregistered criterion | `NOT_TESTED` |
| `performance` | does it earn, after costs | `UNVERIFIED` |

**The ladder is ordered and each rung requires the ones below it.** A candidate
whose `performance` moved while `no_leakage` sat at `NOT_TESTED` would be
claiming a return measured with information it could not have had.

---

## §3 Preregistered criteria

| # | Criterion |
|---|---|
| **C1** | The contract records all six axes, each at its lowest rung, with `live_trading: false`. |
| **C2** | Every term the restatement does not define is present and `UNDEFINED`. Absent is not the same as undefined, and a missing key must fail. |
| **C3** | `swing_definition` is `UNDEFINED`, and the sequence is expressed in terms that *reference* it, so the dependency is visible in the data rather than only in prose. |
| **C4** | **Derived, not typed:** a test reads the sequence out of the contract, finds the swing terms it uses, and requires `swing_definition` to be defined before `rules` may leave `UNDEFINED`. The rule must hold for a contract this spec has never seen. |
| **C5** | `performance` cannot leave `UNVERIFIED` while any lower axis is below its top rung. Asserted for every axis, not for one example. |
| **C6** | The provenance block separates *claimed* from *interpreted*, and marks the source as secondhand. |
| **C7** | The no-prediction invariant is carried, with the same forbidden list the existing candidate uses. |
| **C8** | The data requirement records that ES/MES market data **is not in** `docs/architecture/master-data-sourcing-map.md` — an open unknown under Directive 4, not a detail to settle later. |

### Load-bearing

| # | Criterion |
|---|---|
| **L1** | A `mutation-gate` case loosens the ladder and requires named tests to go red. |
| **L2** | The existing Hafez candidate and its test are left exactly as they are. This adds a second candidate; it does not migrate the first. |

---

## §4 Why the contract is checked by a test and not by a JSON Schema

The obvious move is a `schemas/pattern_contract.schema.json`. It is not being
made, and `UPTM-010` is the reason: this repository already carries a schema
that did not parse for a day while every run reported success, and that is
measurably behind the evidence it describes — 183 mismatches in one suite run.

A second schema that nothing loads would inherit the same failure mode. The
contract's rules are asserted by tests that execute, on the real artifact.

---

## §5 Result

*(filled in after implementation)*

---

## §6 What this does NOT establish

- **Not that Quasimodo works.** No claim about edge, expectancy, or profitability
  is made or implied. `performance` stays `UNVERIFIED` and the ladder forbids it
  moving.
- **Not that the rules are right.** They are a secondhand restatement, recorded
  as such. `source` stays at its lowest rung until the ebook is read.
- **Not that the pattern is implementable.** It is not: `swing_definition` is
  `UNDEFINED`, and every element of the sequence depends on it.
- **Not a library.** One contract. The other six are not started, and the reason
  is in §0.
