# UPTM-018 — `account_equity` stays in the pack, and the note that said otherwise is corrected

**Status:** preregistered 2026-09-30, before the implementation exists.
**Scope:** one Founder decision, one stale record, and the guard that stops the
record contradicting the data again. No detector changes behaviour, no number is
added or changed. `LIVE_TRADING` stays `false`.

---

## §0 What was asked, and what was found

`UPTM-018` was carried in the handover as *"the two numbers the Founder still
owes: `capital.account_equity` and `validation_capital.amount`; without them
VC-I5 and VC-I6 end at `UNKNOWN`; 700 EUR is only a test fixture today."*

Measured against the repository, **half of that was wrong**:

| number | where it lives | state |
|---|---|---|
| `validation_capital.amount` | `constitution/capital-rules.json` | **set — 700 EUR, `set_by: founder`, `set_at: 2026-09-23`** (`DEC-UPTM-004`). Not a fixture. |
| `validation_capital.currency`, `.applies_to` | same | set, same date |
| `capital.account_equity` | **the pack under evaluation** (`pack["account_equity"]`) | not a constant anywhere in this repository — by design (`DEC-UPTM-MAP-Q3`) |

So only **one** figure is missing, and it is not a repository parameter. On the
real configuration, `check_vc_i6_account_covers_the_ceiling` gives:

| pack declares | verdict |
|---|---|
| nothing | `UNKNOWN`, naming `capital.account_equity as a number` |
| `amount − 1` | `FAIL` — the ceiling cannot bind before the account is empty |
| `amount` or more | `PASS` |

### The stale record

`constitution/capital-rules.json`, `uptm004_detector.founder_parameter_required`,
still reads *"validation_capital.amount, .currency and .applies_to are unset.
Every capital gate denies until all three are set."* All three **are** set, and
have been since 2026-09-23. The sentence was true when written and stopped being
true the day `DEC-UPTM-004` set them — the same shape as `UPTM-018a`: a record
describing a state the data has left. It is the likeliest source of the handover
believing 700 was still open.

---

## §1 The decision

**Founder GO, 2026-09-30: `capital.account_equity` stays in the pack. Nothing is
built for it in this repository.**

Why this and not a constitution-level account figure:

- `DEC-UPTM-MAP-Q3` adopted a **floor enforced against whatever a pack
  declares** precisely so that this repository never holds the other side's
  number. A constitution-level account figure is a **second number beside the
  pack's**, and the day they differ the question of which wins is `MAP-Q2` again
  — closed as *neither wins*, i.e. `DENY`. It would recreate a problem already
  solved.
- The number is the Founder's appetite for risk (`CLAUDE.md`: *do not invent
  them*). Where it is *entered* is the first real pack, produced by the system
  that holds the account. This repository cannot read that system and must not
  pretend to.
- Until a pack declares it, `UNKNOWN` is the correct verdict and it is already
  reached. Nothing is broken; nothing needs building.

---

## §2 What changes

1. **The note is corrected**, not deleted — the repository keeps closed entries
   so the hole and its closure stay auditable together. It leads with a status
   word that matches the data (`SATISFIED`), dates it, and names the one figure
   still supplied from outside this file.
2. **A guard makes the note unable to lie the same way again**: its status word
   must equal the state of the three parameters it describes. Derived from the
   data, in both directions.
3. **The decision is recorded** in `docs/decisions.md` as `DEC-UPTM-018`.

---

## §3 Preregistered criteria

### The record

| # | Criterion |
|---|---|
| **A1** | The note begins `SATISFIED` and carries its date and `DEC-UPTM-004`. |
| **A2** | It names `capital.account_equity` as the one figure still supplied from outside the file, says the pack declares it, and says an undeclared one ends `UNKNOWN`. |
| **A3** | Nothing is added: `capital-rules.json` gains **no** `account_equity` field, `validation_capital.amount` is still `700`, `750` is still absent, `CONSTITUTION-CAPITAL.md` is still v1.0 LOCKED. |
| **A4** | The `DEC-UPTM-018` entry exists, newest first, and names the option **not** taken and why. |

### The guard

| # | Criterion |
|---|---|
| **G1** | **Derived, not typed:** the expected status is `SATISFIED` iff `amount`, `currency` and `applies_to` are all set (non-empty), otherwise `REQUIRED`. The real file passes. |
| **G2** | **Both directions**, on synthetic data: all three set with a note claiming `REQUIRED` fails; any **one** of the three unset with a note claiming `SATISFIED` fails — each of the three tried separately, so the guard is not really watching only one key. |
| **G3** | A note with **no** status word fails. Silence is not agreement. |
| **G4** | The guard bites on the **actual defect**: the verbatim old sentence, against the real (set) parameters, is reported. |
| **G5** | The scan cannot pass vacuously: at least one note is found, and it is found by walking the file rather than by naming its path. |
| **G6** | On the **real** configuration the three VC-I6 outcomes in §0 hold, with the threshold taken **from the file** (`amount − 1` / `amount`), so the test does not break if the Founder later changes the tranche. |

### Load-bearing

| # | Criterion |
|---|---|
| **L1** | `capital-note-claims-unset-again` — the old sentence replaces the `SATISFIED` lead; the guard goes red. |
| **L2** | **The gap is measured.** Under that mutation, run before the guard exists, **no** existing test goes red. If one does, the premise that the record was unguarded is wrong and the guard's novelty with it. Run by hand and recorded in §4. |

### What this does not do

- It does **not** set `capital.account_equity`. Nobody can, until a pack exists.
- It adds **no** field or number to the constitution.
- It changes **no** runner behaviour. `VC-I5` and `VC-I6` are exactly as `UPTM-017` left them.

---

## §4 Result

Built on 2026-09-30. Written after the criteria above, in a later commit.

| artifact | what it is |
|---|---|
| `constitution/capital-rules.json` | the note corrected: leads `SATISFIED 2026-09-23 (DEC-UPTM-004)`, names `capital.account_equity` as the one figure still supplied from outside |
| `tests/test_capital_parameter_status.py` | 25 tests, each naming its criterion |
| `runner/mutation_gate.py` | one case, `capital-note-claims-unset-again` |
| `docs/decisions.md` | `DEC-UPTM-018`, newest first |

### Criteria, discharged

| # | how |
|---|---|
| A1 | `test_a1_*` — starts `SATISFIED`, carries `2026-09-23` and `DEC-UPTM-004`. |
| A2 | `test_a2_*` — `capital.account_equity`, *each pack declares it*, `UNKNOWN`, `DEC-UPTM-018`. |
| A3 | `test_a3_*` — no `account_equity` **key** anywhere in the file; `amount` still `700`; `750` absent; constitution v1.0 LOCKED. |
| A4 | `test_a4_*` — entry present, above `DEC-UPTM-017`, names the option not taken and `MAP-Q2`. |
| G1 | `test_g1_*` on the real file. |
| G2 | parametrised over the three parameters × four ways of being empty (`None`, `""`, `[]`, `{}`): `SATISFIED` fails, `REQUIRED` passes; plus all-set with `REQUIRED` fails and both consistent states pass. |
| G3 | `test_g3_*` — empty, prose without a status, a bare reference, and lower-case `satisfied` all fail. |
| G4 | `test_g4_*` — the verbatim old sentence against the real parameters is reported. |
| G5 | `test_g5_*` — the note is found by walking the file. |
| G6 | three tests on the real configuration, threshold read from the file: undeclared → `UNKNOWN` naming `capital.account_equity`; `amount − 1` → `FAIL`; `amount` and `2 × amount` → `PASS`. |
| L1 | `capital-note-claims-unset-again` — caught by `g1` and `a1`. |
| L2 | measured by hand, below. |

### L1 and L2 — measured

Under exactly the L1 mutation:

```
L2  all 804 pre-existing tests (the new file and the gate's own excluded): 804 passed
L1  the new guard: 2 failed, 23 passed
      test_g1_the_note_in_the_real_file_agrees_with_the_real_parameters
      test_a1_the_note_is_dated_and_names_the_decision_that_satisfied_it
```

The premise of §0 holds: the record was unguarded — the suite was green
(851 passed) with the stale sentence in place, and stays green under the
mutation. `a2` does not go red under it, correctly: the mutation replaces only
the lead of the note, and `a2` asserts the tail.

### Verified

| check | result |
|---|---|
| syntax gate | every file parses |
| `pytest` | **877 passed** (851 + 25 + the test the gate generates for the new case) |
| `mutation-gate` | **35 cases, `ok: true`, `baseline_error: None`**, tree clean after |
| `enforcement-evidence` | `ok: true`, `tree_clean: true`, `unproven_claims: []` — on the committed head; on a dirty tree it correctly refuses |

### What this does not do

- **It does not set `capital.account_equity`.** Nobody can until a pack exists;
  the capital gates end at `UNKNOWN`, which is the intended state.
- **It adds no field and no number to the constitution.**
- **It does not touch `docs/decisions.md` history.** The 2026-09-25 entry for
  `DEC-UPTM-MAP-Q3` still reads "stays OPEN" with no pointer forward; that is
  noted in `UPTM-018a` and remains a Founder call.
- **The guard covers this note only.** Other prose in `capital-rules.json`
  (`open_limits`, `checks_note`) can still go stale the same way; there is no
  status vocabulary there to derive an expectation from, and inventing one is a
  larger change than this.
