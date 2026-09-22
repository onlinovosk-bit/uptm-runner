# UPTM-004 — Preregistered definition: `validation_capital_exceeded`, `return_used_as_gate_criterion`

| | |
|---|---|
| Principle | **P10 — €700 as Validation Capital** |
| Today | `MISSING` (`capital-rules.json` `principles[].mechanism: null`) |
| Status of this document | **PREREGISTERED, NOT IMPLEMENTED** |
| Constitution | `constitution/CONSTITUTION-CAPITAL.md` v1.0 (LOCKED) |

Written before evidence collection, as P4 requires. This document does not change any
principle's enforcement state.

---

## 0. What this detector claims, and what it does not

P10 states:

> €700 is capital for validating safety and robustness, not an income engine. Return is
> not a criterion of any gate.
>
> *Violation:* a gate is judged by realised profit instead of by its preregistered
> robustness criteria.

Two separable properties, and the second is the one the constitution actually names:

1. **A ceiling.** Nothing may put more than the validation tranche at risk.
2. **A criterion ban.** No gate may be judged by return.

**Claimed.** That declared exposure stays within a declared tranche, that cumulative
realised loss does too, and that no gate's preregistered exit criteria or PASS
justification is keyed on profit.

**Not claimed.** That the exposure the evidence declares is the exposure that existed.
A run that under-declares what it risked is a fabrication problem and belongs to
UPTM-002, not here. This detector binds declarations; UPTM-002 binds declarations to
reality. Neither substitutes for the other, and saying so is part of the spec.

---

## 1. Verdict model

Identical to UPTM-002 and UPTM-003. Absence is never PASS. `UNKNOWN` denies without
accusing.

---

## 2. Packs

| Pack | Evidence key | Governs |
|---|---|---|
| `capital` | `evidence.capital` | exposure and cumulative loss against the tranche |
| `gate_criteria` | the gate's preregistered exit criteria + `evidence.agent_claim` | whether return is being used as a criterion |

**Omission is closed here by construction.** UPTM-002 recorded `omission_bypass` as an
open limit: evidence declaring no market data never reached the detectors. For a gate
marked `capital: true`, a missing `capital` pack is `UNKNOWN`, not silence. That is the
one lesson from UPTM-002 carried forward rather than repeated.

---

## 3. `validation_capital_exceeded`

### 3.1 PROVENANCE

| Check | Rule | Verdict |
|---|---|---|
| **VC-P1** | `validation_capital.amount`, `.currency` and `.applies_to` declared in `capital-rules.json` | absent or `null` → `UNKNOWN` — **Founder parameter, §7** |
| **VC-P2** | Gate declares whether it is a capital gate | undeclared → `UNKNOWN` |

### 3.2 LIMITS

| Check | Rule | Verdict |
|---|---|---|
| **VC-I1** | A capital gate's evidence carries `capital.at_risk` | absent → `UNKNOWN` (see §2) |
| **VC-I2** | `capital.at_risk <= validation_capital.amount` | exceeded → `FAIL` |
| **VC-I3** | `capital.cumulative_realised_loss <= validation_capital.amount` | exceeded → `FAIL` |
| **VC-I4** | `capital.currency == validation_capital.currency` | mismatch → `UNKNOWN`, never converted |

**VC-I3 exists because VC-I2 alone is not a ceiling.** Twenty positions of €50, each
individually under the cap, can lose the tranche and more. A per-action limit that does
not aggregate is the failure mode P10 was written against.

**VC-I4 refuses to invent an FX rate.** Converting silently would insert a number with
no source into the one calculation that decides whether the money is protected.

---

## 4. `return_used_as_gate_criterion`

| Check | Rule | Verdict |
|---|---|---|
| **VC-R1** | No preregistered exit criterion is keyed on realised profit, return, ROI or a PnL threshold | such a criterion → `FAIL` |
| **VC-R2** | `agent_claim` does not justify PASS by profit achieved | it does → `FAIL` |
| **VC-R3** | Reporting PnL is permitted | PnL present in evidence and used for no criterion → `PASS` |

VC-R3 is deliberate false-positive protection. P10 forbids *judging* by return, not
*measuring* it. A detector that made PnL itself a violation would push the system toward
not measuring — the opposite of what the constitution wants, and it would collide with
UPTM-002, which requires PnL to be declared so it can be checked.

---

## 5. Preregistered acceptance criteria

### Must return `FAIL`

1. `capital.at_risk` above the declared tranche.
2. `cumulative_realised_loss` above the tranche while every individual `at_risk` is below it.
3. An exit criterion of the form "PASS when realised return ≥ X".
4. An `agent_claim` PASS justified by profit, with robustness criteria unmet.
5. A gate marked `capital: true` whose criteria contain a PnL threshold, even when exposure is within the cap.

### Must return `UNKNOWN` — not `PASS`, not `FAIL`

6. `validation_capital.amount` undeclared.
7. A capital gate whose evidence carries no `capital` pack.
8. `capital.currency` differs from the tranche currency.
9. A gate that does not declare whether it is a capital gate.

### Must return `PASS` — false-positive protection

10. Exposure and cumulative loss both within the tranche, criteria purely robustness-based.
11. Evidence reporting a **loss** — losing money inside the tranche is the expected outcome of a validation run and must never be a gate failure on its own.
12. Evidence reporting a **profit** that no criterion references.
13. A non-capital gate carrying no `capital` pack.

Cases 11 and 12 are the heart of P10. A detector that punished loss would make the
system optimise for return; a detector that rewarded profit would do the same thing
faster.

---

## 6. Declared limits — what this will not catch

- **Semantically disguised return criteria.** "Equity curve above X" or "account balance
  ≥ Y" encode return without naming it. VC-R1 matches declared return keys and threshold
  comparisons on declared PnL fields. A criterion that reaches the same place by a
  different name is out of reach, and a reviewer still has to read the criteria.
- **Under-declared exposure.** Belongs to UPTM-002, as §0 states.
- **Leverage and notional.** `at_risk` is what the evidence declares as at risk. Whether
  a notional position of €7,000 with a stop that limits loss to €700 counts as €700 or
  €7,000 is a **Founder decision recorded in `applies_to`**, not an inference this
  detector may make.
- **Fees, funding and slippage** are inside `at_risk` only if the declaration includes
  them. UPTM-002's PL-M2 already covers whether they were accounted for.

---

## 7. Founder parameters required before this can pass

```
capital-rules.json → validation_capital: {
    amount:      <number>      # the constitution names €700; the machine-readable
                               # value is still the Founder's to set
    currency:    "EUR"
    applies_to:  <one or more of>
                 "per_position_at_risk"
                 "aggregate_open_exposure"
                 "cumulative_realised_loss"
}
```

`amount` is the one number this document will not invent even though the constitution
names it in a heading — a principle's title is prose, and the value that gates money
must be set deliberately, by the person whose money it is.

`applies_to` is the substantive choice. "€700" means three different ceilings depending
on which of the three it binds, and picking one for the Founder would be choosing their
risk appetite for them. Until it is set, VC-P1 returns `UNKNOWN` and every capital gate
denies.

---

## 8. Capability outcome and reachability proof

On implementation, P10 moves `MISSING → ENFORCED`.

Not complete until, following UPTM-002c:

- the detector is invoked from `runner.gates.evaluate_gate`, and
- `tests/` carries a spy asserting the gate calls it, **and a disconnection test asserting
  the gate's verdict changes when the detector's return value changes.**

With UPTM-003 and the P7 lease, this would be among the first principles to leave
`0 ENFORCED`.
