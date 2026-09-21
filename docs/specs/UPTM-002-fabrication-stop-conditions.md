# UPTM-002 — Preregistered definition: `fabricated_market_data`, `fabricated_pnl`

| | |
|---|---|
| Status | **PREREGISTERED** — criteria fixed before any detector exists (CC/P4) |
| Target capability | **PARTIAL**, preregistered. Not upgradeable to `ENFORCED` by green tests. |
| Stop conditions | `fabricated_market_data`, `fabricated_pnl` (`constitution/rules.json`) |
| Contains | no detector code |

## 0. What this detector does and does not claim

A detector cannot establish that data was fabricated. No test distinguishes a number
invented in someone's head from one that came off an exchange. A sufficiently consistent
forgery passes every check below.

What is decidable is whether data can be **traced and recomputed**. The stop condition is
therefore defined as:

> **Data or accounting whose provenance cannot be verified, or whose internal consistency
> cannot be reproduced, is treated as fabricated for safety purposes.**

The detector never reports "forgery proven". It reports that a required property of
verifiability or consistency does not hold.

## 1. Verdict model

Each check returns one of three values:

| Verdict | Meaning | Effect |
|---|---|---|
| `PASS` | property holds | check satisfied |
| `FAIL` | property is violated | **stop condition raised** |
| `UNKNOWN` | the check's preregistered parameter is absent, so the property cannot be evaluated | **DENY, no stop condition raised** |

The distinction matters. `FAIL` asserts an integrity violation. `UNKNOWN` asserts only
that we cannot tell — which under `GOVERNANCE.md` §4 C1 resolves to DENY, never to
ALLOW.

**The gate passes only if every check returns `PASS`.**

This is the spine of the whole specification. Every relaxation below — flat prices are
not automatically suspicious, zero fees are not automatically suspicious — is a
relaxation of `FAIL`, never of the requirement to declare. A missing declaration does not
buy a pass; it buys `UNKNOWN`, and `UNKNOWN` blocks.

## 2. Layers

```
PROVENANCE          identity · acquisition time · digest · coverage
INTEGRITY           digest verification · OHLC invariants · calendar · duplication
ACCOUNTING          PnL recomputation · fill lineage · position conservation
MODEL CONSISTENCY   zero-fill/PnL boundary · declared fees & slippage
```

These are four layers, not fourteen independent proofs. All four are local consistency;
none of them is external authenticity.

---

## 3. `fabricated_market_data`

### 3.1 PROVENANCE (hard fail)

Every data series referenced by evidence declares:

| Field | Missing → |
|---|---|
| `source_id` | `UNKNOWN` |
| `acquired_at_utc` | `UNKNOWN` |
| `content_digest` (algorithm + value) | `UNKNOWN` |
| `coverage` (instrument, timeframe, first and last timestamp) | `UNKNOWN` |

**MD-P1** any of the four absent → `UNKNOWN`.

### 3.2 INTEGRITY

**MD-I1 — digest verification.** Recomputed digest of the referenced snapshot ≠
`content_digest` → `FAIL`. Snapshot present but unreadable → `FAIL`.

**MD-I2 — snapshot existence.** Evidence references a snapshot that does not exist in the
evidence store → `FAIL`.

**MD-I3 — coverage sufficiency.** `coverage` does not contain the full interval over
which the result was computed → `FAIL`. Coverage declared but computation interval not
declared → `UNKNOWN`.

**MD-I4 — OHLC invariants.** For every bar: `low ≤ min(open, close)` and
`max(open, close) ≤ high`, all four finite and positive, `volume ≥ 0`. Violation →
`FAIL`.

**MD-I5 — degenerate series.** Evaluated **only** against the dataset's preregistered
invariant `min_expected_variance` for that instrument and timeframe.

- invariant declared, variance over window `W` below it → `FAIL`
- invariant declared, variance at or above it → `PASS`
- invariant **not** declared → `UNKNOWN`

A constant price is legitimate for some instruments and timeframes. It is never
legitimate to leave unstated which case this is.

**MD-I6 — trading-calendar integrity.** Evaluated against the preregistered
`calendar_id` for that instrument and market.

- bar timestamped outside the calendar's open intervals → `FAIL`
- expected interval absent with no declared gap reason → `FAIL`
- `calendar_id` not declared, or unknown to the calendar registry → `UNKNOWN`

**MD-I7 — duplicate block.** Formal definition: two **disjoint** index ranges
`[i, i+k)` and `[j, j+k)` of the same series, with `k ≥ duplicate_block_min_len`, whose
`(open, high, low, close, volume)` tuples are element-wise identical.

- such a pair exists and the dataset declares `allows_repeated_bars: false` → `FAIL`
- such a pair exists and the dataset declares `allows_repeated_bars: true` → `PASS`
- `duplicate_block_min_len` or `allows_repeated_bars` not declared → `UNKNOWN`

No default value for `duplicate_block_min_len`. A default would be this specification
guessing the instrument's behaviour, which is what MD-I5 and MD-I6 exist to prevent.

---

## 4. `fabricated_pnl`

Governing principle: **PnL is derived, never trusted.** A reported figure is an input to
be checked, never an answer to be recorded.

### 4.1 Declarations required

| Field | Missing → |
|---|---|
| `accounting_boundary`: opening position, opening cash, opening unrealized, run start and end | `UNKNOWN` |
| `quantity_convention`: signed, long positive, short negative | `UNKNOWN` |
| `pnl_tolerance`: absolute and relative, per currency | `UNKNOWN` |
| `execution_model`: declared fee schedule and slippage model | `UNKNOWN` |

### 4.2 ACCOUNTING

**PL-A1 — recomputation.** `reported_pnl` vs. PnL recomputed from the fill ledger and
marks, compared against `pnl_tolerance`. Outside tolerance → `FAIL`. Tolerance not
declared → `UNKNOWN`.

**PL-A2 — fill lineage.** Every fill references an order that passed the pre-trade gate,
and that order exists. Orphan fill → `FAIL`.

**PL-A3 — position conservation.** Under `quantity_convention`:

```
position_after == position_before + Σ signed_quantity(fills)
```

Mismatch → `FAIL`. Convention not declared → `UNKNOWN`.

### 4.3 MODEL CONSISTENCY

**PL-M1 — PnL without fills.** Evaluated strictly inside `accounting_boundary`.

- **realized** PnL ≠ 0 with zero fills in the run → `FAIL`
- **unrealized** PnL change with zero fills is legitimate when the opening position is
  non-zero and the change reconciles with marks; if it reconciles → `PASS`, if it does
  not → `FAIL`
- `accounting_boundary` not declared → `UNKNOWN`

Carry-over state is a legitimate source of PnL. It is not a legitimate reason to omit the
opening state from evidence.

**PL-M2 — fees and slippage.** This is a test of the model against its ledger, not of a
number against zero.

- `execution_model` declares non-zero fees or slippage, ledger contains zero where the
  model requires a charge → `FAIL`
- `execution_model` declares zero fees and slippage (e.g. a frictionless simulation) and
  the ledger is zero → `PASS`
- `execution_model` not declared → `UNKNOWN`

---

## 5. Preregistered acceptance criteria for the detector

Written before the detector, per CC/P4. The detector is accepted only when it produces
exactly these verdicts. Each case is a mutation applied to an otherwise valid pack.

### Must return `FAIL`

| id | Mutation |
|---|---|
| MUT-01 | one bar's `high` lowered below `close` |
| MUT-02 | one byte changed inside the snapshot, digest left as-is |
| MUT-03 | evidence references a snapshot path that does not exist |
| MUT-04 | coverage truncated to a subset of the computation interval |
| MUT-05 | bar inserted on a date the declared calendar marks closed |
| MUT-06 | 20-bar block copied to a later offset, `allows_repeated_bars: false` |
| MUT-07 | flat series below a declared `min_expected_variance` |
| MUT-08 | `reported_pnl` shifted beyond the declared tolerance |
| MUT-09 | a fill whose `order_id` matches no gated order |
| MUT-10 | `position_after` altered by one unit |
| MUT-11 | realized PnL non-zero, fill ledger empty |
| MUT-12 | fee schedule declares a charge, ledger records zero for those fills |

### Must return `UNKNOWN` (not `PASS`, not `FAIL`)

| id | Mutation |
|---|---|
| MUT-13 | `content_digest` field removed |
| MUT-14 | `min_expected_variance` undeclared, series is flat |
| MUT-15 | `calendar_id` undeclared |
| MUT-16 | `duplicate_block_min_len` undeclared, duplicate block present |
| MUT-17 | `pnl_tolerance` undeclared |
| MUT-18 | `accounting_boundary` undeclared |
| MUT-19 | `quantity_convention` undeclared |
| MUT-20 | `execution_model` undeclared |
| MUT-21 … MUT-29 | every remaining required parameter of every check, one case each — enumerated in the machine-readable preregistration |

### Must return `PASS` — false-positive protection

| id | Case |
|---|---|
| NEG-01 | flat series, `min_expected_variance: 0` declared for that instrument/timeframe |
| NEG-02 | zero fees and zero slippage, `execution_model` declares a frictionless simulation |
| NEG-03 | unrealized PnL changed with zero fills, opening position non-zero, change reconciles with marks |
| NEG-04 | repeated identical bars, `allows_repeated_bars: true` declared |
| NEG-05 | gap in bars over a declared market holiday |

A detector that passes the FAIL set but fails the UNKNOWN set is **not** accepted: it
would convert missing declarations into silent passes, which is the failure mode this
specification exists to prevent.

---

## 6. Declared limits — what this will not catch

These are preregistered so that no future report can present this control as stronger
than it is:

1. A fully consistent forged snapshot with a matching fill ledger and matching marks.
2. A compromised or dishonest upstream data source.
3. Genuine historical data replayed as a different period, where the replayed window is
   calendar-consistent with the claimed one.
4. Fabrication upstream of the snapshot — this checks the snapshot, not the world.

Closing 1–3 requires source-authenticated provenance: signed snapshots from the source,
or an external append-only anchor. That is a **separate future gate**, not part of
UPTM-002.

## 7. Capability outcome

On full acceptance of the detector, the two stop conditions move:

```
DECLARATIVE  →  PARTIAL   (local consistency verified)
```

They do **not** move to `ENFORCED`. Upgrading requires §6 items 1–3 to be closed by
external provenance authenticity, under a new preregistration. Green tests are not
grounds for the upgrade; this is preregistered precisely so that the question cannot be
reopened after the fact.

## 8. Placement note

`GOVERNANCE.md` reserves the `gates/` track for capital-capability gates. UPTM-002 is a
control-plane stop condition, so this specification sits under `docs/specs/`. Governance
is silent on where control-plane preregistrations live; this is a filing convention, not
an authority decision, and is flagged rather than assumed.
