# UPTM-012 — What a swing is, and when it is allowed to be known

**Status:** preregistered 2026-09-27, before the implementation exists.
**Scope:** one mechanical definition and the causality guard around it.
No market data, no detector for any formation, no backtest, no trading.
`LIVE_TRADING` stays `false`.

---

## §0 What this is for, and the risk taken on knowingly

`UPTM-011` established that all seven reversal formations bottom out on one
undefined term. This defines it.

The recommendation given to the Founder was to read the ebook **first**, so that
`source` leaves `RESTATED_SECONDHAND` before a definition is committed that
every formation would inherit. The Founder decided otherwise, and this is built
on that decision. The risk is recorded here rather than argued again: if the
primary source turns out to define *swing* differently, this definition is what
has to change, and the seven formations inherit the change.

That risk is contained deliberately. The parameters are **not** chosen here
(§3), so what a later reading could overturn is the *shape* of the rule, not a
set of numbers already baked into a contract.

---

## §1 The definition

A bar `i` is a **swing high** when its high is strictly greater than the high of
every one of the `pivot_bars` bars on each side of it. A **swing low** is the
same on lows, strictly lower.

A swing is then **accepted** only if it moved far enough from the last accepted
swing of the opposite kind — `min_amplitude`, read either as an absolute price
distance or as a fraction of the previous swing's price. The first swing of a
series has no opposite predecessor and is accepted without an amplitude test.

Two consequences are chosen, not inherited:

**Ties produce nothing.** A plateau — two bars sharing the same extreme — is not
a swing under either side of the comparison. A tie is not an extreme, and
picking one of the two bars would be an arbitrary rule that a later reader could
not reconstruct from the data.

**Nothing is ever revised.** The usual ZigZag construction withdraws a swing
when a later bar makes a better one. That is rejected here: a withdrawn swing is
one a live system may already have acted on, and a definition whose past changes
cannot support the invariant in §2. Consecutive same-kind swings are both kept,
so the sequence may legitimately read HIGH, HIGH, LOW.

---

## §2 The invariant that matters more than the definition

A swing high at bar `i` **is not knowable at bar `i`.** It becomes knowable at
bar `i + pivot_bars`, when the right-hand window closes — not before. Every
swing therefore carries `confirmed_at`, and it is the only timestamp a decision
is allowed to use.

`bearish_quasimodo.json` already forbids "swing points confirmed by bars later
than the decision timestamp". This is where that stops being a sentence.

**The invariant, stated so it can fail:**

> For every `t`, the swings whose `confirmed_at <= t` are **exactly** the swings
> detected from `bars[:t+1]`.

Filtering the full series by confirmation time and truncating the series before
detection must give the same answer. If any future information reaches the
detector, these two diverge. This is asserted for every `t` in a series, not for
a chosen example.

Its companion: what is known at `t` is a **prefix** of what is known later. No
swing is withdrawn, reprice, or reordered by a later bar.

---

## §3 What is deliberately left unset, and the precedent for it

`pivot_bars` and `min_amplitude` are **not chosen here.** Choosing them requires
bar data to choose against, and ES/MES data is `OPEN_UNKNOWN` under Directive 4.
A number picked without data would be a fabricated parameter wearing a
definition's clothes.

The precedent is this repository's own `DEC-UPTM-003`: the validation-capital
machinery is `ENFORCED` while `validation_capital.amount` is `null`, and the
decision log records that *"`ENFORCED` and unset are not in tension: the
machinery is enforced, and it is enforcing a denial."*

Same shape here. The definition becomes **defined**; a new term
`swing_parameters` becomes **`UNDEFINED`**, and the contract stays unevaluable
for that reason instead of the previous one. That is a real advance and a small
one, and it is reported as both.

---

## §4 Preregistered criteria

| # | Criterion |
|---|---|
| **S1** | `SwingDefinition` validates its parameters and raises on nonsense (`pivot_bars < 1`, negative amplitude, unknown amplitude mode). Silent coercion is forbidden. |
| **S2** | A swing high is strictly greater than the `pivot_bars` bars on **both** sides; a plateau yields no swing. Asserted with a constructed tie. |
| **S3** | Every swing carries `confirmed_at == index + pivot_bars`. |
| **S4** | **The invariant.** For every `t` in a constructed series, `[s for s in detect(bars) if s.confirmed_at <= t] == detect(bars[:t+1])`. Every `t`, not one. |
| **S5** | What is known at `t` is a prefix of what is known at any later `t`. No swing is withdrawn or revised. |
| **S6** | The amplitude filter measures against the last **accepted** swing of the opposite kind, and is decidable at `confirmed_at`. A move that is too small produces no swing; the same move with a lower threshold does. |
| **S7** | `HH`/`HL`/`LL`/`LH` are derived by comparing a swing to the previous swing **of the same kind**. No predecessor, or equal prices, yields no label. |
| **S8** | **Sensitivity.** Two parameter sets produce different swing sets on the same series. A result reported without its parameters is not reproducible, and the test says so by making the dependence visible. |
| **S9** | `bearish_quasimodo.json` records `swing_definition` and the four relational terms as defined, gains `swing_parameters: UNDEFINED`, and `rules` **still** cannot leave `UNDEFINED`. |
| **S10** | The required-term derivation extends: once `swing_definition` is defined, `swing_parameters` becomes required, so deleting the key does not hide it. Derived from the data, as in UPTM-011. |

### Load-bearing

| # | Criterion |
|---|---|
| **L1** | A `mutation-gate` case breaks the confirmation lag and requires the named tests to go red. The leak guard is the mechanism that must be proven load-bearing; a definition whose causality check has quietly stopped working is worse than none. |
| **L2** | No market data is read, no formation detector is built, no backtest is run. Every series in the tests is constructed inside the test and says so. |

---

## §5 Result

Built on 2026-09-27. No market data was read; every series in the tests is
constructed inside the test file.

| artifact | what it is |
|---|---|
| `runner/swing.py` | the definition, and `confirmed_at` on every swing |
| `tests/test_swing.py` | 31 tests, each naming its criterion |
| `runner/pattern_contract.py` | `required_terms` now raises `swing_parameters` |
| `research/candidates/reversal/bearish_quasimodo.json` | root defined, parameters not |
| `tests/test_pattern_contract.py` | 31 tests (6 new for S9/S10, 3 amended) |
| `runner/mutation_gate.py` | two cases (§L1) |

### Criteria, discharged

| # | how |
|---|---|
| S1 | `test_s1_*` — six invalid parameter sets, each raising; `True` is rejected as `pivot_bars` because `bool` is an `int` and would otherwise pass as 1. |
| S2 | `test_s2_*` — a plateau yields nothing; the same shape with the tie broken by 0.01 yields one; an extreme without a full window either side yields nothing. |
| S3 | `test_s3_*` — parametrised over `pivot_bars` 1–3, asserting `confirmed_at == index + pivot_bars` **and** `confirmed_at > index`. |
| S4 | `test_s4_*` — the invariant, at **every** cut of the series, for `pivot_bars` 1–3, and again with the amplitude filter engaged. |
| S5 | `test_s5_*` — every cut's view is a prefix of the next; two rising highs with no qualifying low between them are both kept rather than one replacing the other. |
| S6 | `test_s6_*` — a move too small yields nothing; absolute and relative are shown to be genuinely different rules (0.8 points vs 80 %, on a move that is 11 points and 73 %). |
| S7 | `test_s7_*` — the six-swing walk labels `HH HL LH LL` correctly; first-of-kind and exact ties yield `None`; labelling a prefix equals the prefix of the labels. |
| S8 | `test_s8_*` — `pivot_bars` 1 vs 3 give different sets (and the wider window is a strict subset); amplitude 0 vs 12 differ; the lag tracks the parameter rather than being a constant. |
| S9 | `test_s9_*` — the root is defined and names `runner/swing.py`; the four relational terms are defined; `rules` still cannot move, and the contract records that the definition is **ours**, not the source's. |
| S10 | `test_s10_*` — `swing_parameters` is required once the root is written, deleting the key does not hide it, and the requirement is **absent** before the root is written. |
| L1 | `swing-confirmation-lag-removed` (5 sentinels) and `swing-plateau-accepted` (1). |
| L2 | No import of any data loader; `series()` and `wedge()` build every fixture, and the module docstring says so. |

### What actually moved, stated small

The Quasimodo contract went from **15 undefined terms to 11**. `rules` did not
move and cannot: `swing_parameters`, `entry_trigger`, `break_tolerance`,
`target_exit`, `timeframe`, `instrument_es_vs_mes`, `session_window`,
`slippage_model`, `fee_model`, `risk_sizing` and `invalidation_rules` are all
still `UNDEFINED`. The root is gone; the contract is no closer to being tradeable.

### Preregistered as one thing, built as another

**L1 said "a case"; two were built.** The second (`swing-plateau-accepted`) guards
a one-character choice — `<` against `<=` — that a refactor could flip with
nothing else in CI noticing.

**Three UPTM-011 tests were amended, not relaxed.** `test_c4_defining_the_root_is_what_clears_it`
asserted that writing `swing_definition` cleared the contract outright; it no
longer does, so the test now asserts *both* steps. `test_c3_…_the_root_is_undefined`
became `…_the_root_is_required`, because the fact it asserted stopped being
true while the criterion behind it did not. `NOT_STATED_BY_THE_SOURCE` swapped
`swing_definition` for `swing_parameters`. Each change is a fact that moved, not
a bar that was lowered — and each is named here so a reader can check that claim
against the diff rather than take it.

### What was measured

- `python -m runner.syntax_gate` — every file parses.
- `python -m pytest` — 633 passed, 0 failed.
- `python -m runner.cli mutation-gate` — 21 cases, `ok: true`, no missing sentinel.

---

## §6 What this does NOT establish

- **Not that any parameter value is right.** None is chosen. `swing_parameters`
  is `UNDEFINED` and the ladder blocks on it.
- **Not that Quasimodo is implementable.** `entry_trigger`, `break_tolerance`,
  `target_exit`, timeframe, instrument, fees and slippage remain `UNDEFINED`.
  `rules` does not move.
- **Not that this is what the ebook means by a swing.** `source` stays at
  `RESTATED_SECONDHAND`. §0 records that this was built ahead of the reading,
  and on whose decision.
- **Not a detector.** Nothing here looks for a formation, and nothing reads a
  price series that came from outside the test.
