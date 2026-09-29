# UPTM-017 — What `at_risk` measures, and the floor that makes the ceiling real

**Status:** preregistered 2026-09-29, before the implementation exists.
**Scope:** one unit, one floor, and the two checks that enforce them. No market
data, no trading. `LIVE_TRADING` stays `false`.

---

## §0 What was found, and what the Founder decided

Asked to relate €700 (`validation_capital.amount`) to €750 (the other
repository's `DEFAULT_CAPITAL_EUR`), the comparison turned out to be
**ill-posed on one side**. Measured:

| `applies_to` term | what the detector actually reads | unambiguous |
|---|---|---|
| `cumulative_realised_loss` | `pack["cumulative_realised_loss"]` (VC-I3) | yes |
| `aggregate_open_exposure` | `pack["at_risk"]` (VC-I2) | **no** |

`aggregate_open_exposure` is a **switch**, not a definition: its presence in
`applies_to` turns on a comparison of a differently-named field against the
amount, and nothing anywhere says whether `at_risk` is notional, margin or
risk-to-stop. For ES/MES those differ by orders of magnitude — one MES around
index 6000 is roughly $30,000 notional, ~$1,500 margin, and perhaps €50 of risk
to a stop. €700 therefore means "no trade at all", "one contract" or "fourteen
trades" depending on which nobody said.

The repository had already caught the *name* mismatch and recorded it in
`capital-rules.json`: the fixture *"invented the pack field names
aggregate_open_exposure and per_position_at_risk where the detector reads
at_risk"*. The name was fixed. **The unit never was.**

The Founder decided: define the unit first, then adopt **option C** — the
account floor.

---

## §1 The unit: risk to stop

`at_risk` is the **aggregate risk to stop, in the tranche currency**: summed
across open positions, `(entry − stop) × size × value per point`, taking every
stop as filling at its level.

Why this and not the other two:

- **Notional** would make P10 forbid trading outright — €700 of notional buys
  no ES or MES contract. "The size of the test" cannot mean a cap that permits
  no test.
- **Margin** is a broker and exchange artefact. It moves with volatility and
  says nothing about what can be lost; a cap denominated in it would tighten
  and loosen for reasons that have nothing to do with the experiment.
- **Risk to stop** is the only one of the three that measures *money that can
  be lost*, which is what the constitution's own note says €700 is: "EUR 700 is
  the size of the TEST", and €700 lost on a correct decision is a good
  investment.

### The part that must be said out loud

**A stop is not a guarantee.** Gaps, limit moves and thin books mean realised
loss can exceed planned risk, sometimes badly. So `at_risk` bounds **intent**
and `cumulative_realised_loss` bounds **outcome** — and that is precisely why
the two `applies_to` terms are not redundant. One catches a plan that risks too
much; the other catches a plan that was within its limit and lost more anyway.
A single number could not do both.

### What is not adopted here

The term in `applies_to` stays `aggregate_open_exposure`. Renaming a value the
Founder set on 2026-09-23 is a parameter change and belongs to the Founder
(P14), not to this spec. What this spec does is record which measurement that
switch turns on, and make a pack that does not declare its basis deny.

---

## §2 The floor: option C

`cumulative_realised_loss ≤ €700` is a ceiling only while the account can
actually reach it. Against the range recorded in the governance map
(`DEFAULT_CAPITAL_EUR` 750, min 500, max 1000):

| account | €700 loss ceiling binds at |
|---|---|
| 1000 | 70 % of the account |
| 750 | 93 % of the account |
| **500** | **never — the account empties first** |

At the bottom of that range P10 stops being what halts the test; the account
running out is. The ceiling is decorative.

**So: a capital pack must declare the account, and a tranche that binds
cumulative realised loss is valid only when the account is at least the tranche
amount.** Below that the configuration is refused — the *configuration*, not
the trade, because the defect is in the setup and no individual action is at
fault.

This is enforceable here without any authority over the other repository. It
refuses rather than commands, which is the shape `MAP-Q1` and `MAP-Q2` settled.

**The €750 figure is recorded from the governance map, not measured.** This
repository cannot read `onlinovosk-bit-uptm`, and the number may already be
stale there. The floor is enforced against whatever a pack declares, not
against 750.

---

## §3 Blast radius, stated before it is built

`run_validation_capital_detectors` returns early when evidence carries no
capital pack and does not declare `capital_gate: true`. **Non-capital gates are
untouched.** These two checks bite exactly the evidence that is about capital,
which is the intent rather than a side effect.

Within that scope the effect is real and is not softened: a capital pack that
does not declare its `at_risk` basis, or does not declare the account, resolves
`UNKNOWN` and therefore denies. Absence is not a measurement.

---

## §4 Preregistered criteria

| # | Criterion |
|---|---|
| **U1** | A capital pack declares `at_risk_basis`. Absent, or not a string, is `UNKNOWN` — never assumed. |
| **U2** | Only the adopted basis passes. `notional` and `margin` are named in the failure so the reader learns why, not merely that. |
| **U3** | The basis check binds only when the tranche binds exposure — derived from `applies_to`, as VC-I2 and VC-I3 already do, not from a typed list. |
| **U4** | A capital pack declares `account_equity`. Absent, or not a number, is `UNKNOWN`. |
| **U5** | `account_equity < tranche.amount` **fails**, and the message says the ceiling cannot bind before the account is empty. Equal passes: a ceiling exactly at the account is still reachable. |
| **U6** | The floor binds only when the tranche binds `cumulative_realised_loss` — derived, for the same reason as U3. A tranche that binds nothing but exposure has no loss ceiling to make real. |
| **U7** | Both checks reach the gate: `evaluate_gate` denies a capital pack that omits either field, and the denial names the check. Asserted through the gate, not the detector alone. |
| **U8** | A non-capital gate is unaffected: evidence with no capital pack and no `capital_gate` still resolves exactly as before. Asserted, because §3 claims it. |

### Load-bearing

One case per independent mechanism, named in advance:

| # | Criterion |
|---|---|
| **L1a** | `at-risk-basis-unchecked` — the basis check accepts anything; the named tests go red. |
| **L1b** | `account-floor-unchecked` — the floor comparison is removed; the named tests go red. |
| **L2** | No market data, no network call. `LIVE_TRADING` stays `false`, and no principle's enforcement state is moved by this change. |

---

## §5 Result

Built on 2026-09-29. **`DEC-UPTM-MAP-Q3` is closed with this, so no governance
question is left open.**

| artifact | what it is |
|---|---|
| `runner/detectors/validation_capital.py` | `AT_RISK_BASIS`, VC-I5, VC-I6 |
| `tests/test_at_risk_unit_and_floor.py` | 28 tests, each naming its criterion |
| `docs/architecture/governance-map.md` | Q3 decided, in all three places |
| `constitution/capital-rules.json` | P10's check count, 9 → 11 |
| `runner/mutation_gate.py` | L1a, L1b, and one re-aimed case |

### The measurement, per pack

| pack | VC-I5 | VC-I6 |
|---|---|---|
| declares `risk_to_stop`, account 750 | PASS | PASS |
| no `at_risk_basis` | **UNKNOWN → DENY** | PASS |
| `at_risk_basis: notional` | **FAIL** | PASS |
| account 500 | PASS | **FAIL** |
| account exactly 700 | PASS | PASS |
| no `account_equity` | PASS | **UNKNOWN → DENY** |

### Criteria, discharged

| # | how |
|---|---|
| U1 | `test_u1_*` — absent, and five kinds of non-word, are each `UNKNOWN`. |
| U2 | `test_u2_*` — the adopted basis passes; `notional` and `margin` fail **with their reason quoted**; an unrecognised basis fails without one being invented. |
| U3 | `test_u3_*` — a loss-only tranche never reads `at_risk`; `per_position_at_risk` binds it just as `aggregate_open_exposure` does. |
| U4 | `test_u4_*` — absent, and four kinds of non-number, are `UNKNOWN`. |
| U5 | `test_u5_*` — 500 against 700 fails and names both; **700 against 700 passes**, because a ceiling exactly at the account is still reachable. |
| U6 | `test_u6_*` — an exposure-only tranche has no floor; an unset amount is `UNKNOWN`, never a floor of zero. |
| U7 | `test_u7_*` — through `evaluate_gate`: the pack passes when both are declared, and omitting either denies **naming the check**. |
| U8 | `test_u8_*` — a plain pack still passes; and the checks, when they do run on an empty pack, are `UNKNOWN` rather than a quiet pass. |
| L1a | `at-risk-basis-unchecked`. |
| L1b | `account-floor-unchecked` — independent: the basis is still checked when this one is gone. |
| L2 | No network call, no market data; no enforcement state moved (`ENFORCED 3 / PARTIAL 6 / DECLARATIVE 1 / MISSING 4` still asserted by `test_g7_*`). |

### What was measured

- `python -m runner.syntax_gate` — every file parses.
- `python -m pytest` — 830 passed, 0 failed.
- `python -m runner.cli mutation-gate` — 32 cases, `ok: true`, no missing sentinel.

### Four tests amended, all because a fact changed

| test | why |
|---|---|
| `test_map_q3_stays_open` → `test_map_q3_is_decided_as_a_floor_and_copies_no_number` | Q3 closed on Founder GO. The guard **changed direction**: it now forbids the two options that were *not* chosen — a ceiling on the other repository's account, and their number copied into this constitution. |
| `test_g8_…` (UPTM-015) and `test_n8_q3_is_untouched` (UPTM-016) | both asserted Q3 still open. They now assert it closed **under its own marker and date**, which is what they were really protecting: it was not swept up with Q1/Q2 or Q5. |
| two capital fixtures | the packs now declare what they previously left unsaid. |

### Two stale sentences corrected in passing

Both said the shipped `validation_capital` is unset and every capital gate
denies until the Founder sets it. **It has been set since 2026-09-23.** They
were in the two test files this change already edits, one line from fixtures it
already touches, and a reader would have believed them. The stubbing they
justify is still right, for a different reason: a test that read the live
configuration would change meaning the next time a number changed.

The identical sentence in `capital-rules.json`'s P10 entry is **left alone** —
it is not made wrong by this change, nothing reads it, and correcting it was
not part of this GO.

### What did not move

€700 is unchanged. `aggregate_open_exposure` keeps the name the Founder set —
renaming it is P14's business. `750` still appears nowhere in this
repository's constitution, and a test asserts it.

---

## §6 What this does NOT establish

- **Not a new amount.** €700 is unchanged; this says what it counts and when it
  is meaningful. The number stays the Founder's.
- **Not a rename.** `aggregate_open_exposure` stays as the Founder set it.
- **Not a claim about the other repository.** €750 is recorded, unverified, and
  nothing here reaches into that repository or commands it.
- **Not a guarantee that €700 is enough, or that a stop will hold.** §1 says the
  opposite of the second.
