# UPTM-010 — A schema that cannot be read is a fault, not a pass

**Status:** preregistered 2026-09-26, before the implementation exists.
**Depends on:** `UPTM-009` (PR #40), which repaired `schemas/evidence.schema.json`.
This spec is built on that branch; without the repair, every gate would deny.

---

## §0 Measurement first

`runner/evidence.py` ends its schema check with:

```python
    except ImportError:
        pass
    except Exception:
        # Schema mismatch is recorded softly; structural errors above are hard.
        # Adversarial packs may intentionally violate severity enums.
        pass
```

**M1 — the swallow hid a real fault for a day.** `schemas/evidence.schema.json`
did not parse from `c4c409d` until `UPTM-009` repaired it. `_load_schema()`
raised `JSONDecodeError` on every call; `except Exception` ate it. Schema
validation was inert and every run reported success.

**M2 — the repaired schema does accept a real gate pack.** Open in `UPTM-009`
§5, answered here:

```
runner.enforcement._base() against schemas/evidence.schema.json  ->  VALID
```

**M3 — what else the swallow hides, counted rather than guessed.** The suite was
run with the swallow instrumented (and the instrumentation removed again):

```
183 exceptions swallowed, all of them jsonschema.ValidationError, none a load failure
```

They are not noise, and they are **not** all adversarial. The comment claims
severity enums; the measurement says the schema is simply behind the evidence
the code really builds:

| shape | example |
|---|---|
| packs the schema does not know | `Additional properties are not allowed ('capital', 'capital_gate', 'kill_switch', 'market_data', 'pnl')` |
| deliberate attacks | `'WARNING' is not one of ['CRITICAL', …]`, `'not-a-digest' does not match …` |
| route fixtures, denying on purpose | `'commit_sha' is a required property`, `[] should be non-empty` |

**So the comment is right about the conclusion and wrong about the reason.**
Mismatch must stay soft — but because the schema is incomplete, not only
because packs attack it. Turning mismatch hard would deny 183 evaluations the
suite expects to proceed, and would silently promote an out-of-date schema into
a gate.

---

## §1 The distinction this draws

One `except` covers two unrelated events:

| event | what it means | today | after |
|---|---|---|---|
| the schema cannot be loaded or is not a valid schema | **infrastructure fault** — the check did not run | silent pass | **fail closed, named** |
| evidence does not match the schema | a finding about the evidence | silent pass | **unchanged, still soft** |

The first is the repository's own doctrine: *absence is not a measurement*. A
check that did not run must never read as a check that passed.

---

## §2 Preregistered criteria

| # | Criterion |
|---|---|
| **S1** | A schema file that does not parse makes `validate_evidence_structure` return an error naming the file and the decoder's own message. |
| **S2** | A schema file that is absent does the same. |
| **S3** | A file that parses but is not a valid JSON Schema (`jsonschema.SchemaError`) does the same. |
| **S4** | `jsonschema` not importable does the same: the check cannot run, so it is a fault, not a pass. See §4 — this is the one judgement call in this spec. |
| **S5** | A `ValidationError` — evidence against a loadable schema — adds **no** error. Behaviour is unchanged, and M3's 183 cases still pass. |
| **S6** | The fault error is prefixed so the gate denies on it, consistent with the other fail-closed reasons in `runner/gates.py`. |
| **S7** | The schema is loaded once per call at most, and a fault is reported once, not once per evidence field. |

### Load-bearing

| # | Criterion |
|---|---|
| **L1** | A `mutation-gate` case restores the blanket swallow and names the tests required to go red. |
| **L2** | The suite still passes whole: no test that relied on the swallow is skipped, disabled or weakened to get there. |

---

## §3 Result

Measured on `e473f2f`, clean tree.

| # | Criterion | Result |
|---|---|---|
| S1 | unparseable schema → named, with the decoder's own message and line | **PASS** |
| S2 | absent schema → named | **PASS** |
| S3 | parses but is not a JSON Schema → named | **PASS** |
| S4 | `jsonschema` not importable → named | **PASS** |
| S5 | mismatch against a loadable schema → no error, unchanged | **PASS** |
| S6 | the fault denies the gate (`fail-closed: schema check could not run …`) | **PASS** |
| S7 | reported once, not once per field | **PASS** |
| L1 | mutation-gate case, named sentinels go red | **PASS**, all four |
| L2 | the suite passes whole, nothing skipped or weakened | **PASS** |

```
563 passed              553 + 9 new tests + 1, the mutation registry being
                        parametrised, so the new case became a test by itself
syntax-gate             exit 0
mutation-gate           exit 0, 15 cases, none not-ok
                        schema-faults-swallowed caught by all 4 sentinels
enforcement-evidence    exit 0, 35 routes, reaching PASS [], another reason [],
                        unproven_claims [], claims_checked P8 P10 P12
```

### Nothing was weakened to get there

L2 mattered more than it looks. The 183 mismatches of M3 are load-bearing
behaviour: had S5 been written the other way round, the honest way to a green
suite would have been to teach the schema every pack it does not know — a much
larger change than this one, and not what was asked for. The spec fixed that
before the code, so the temptation never arose.

### Two criteria that could have been quietly softened, and were not

- **S4** is the judgement call of §4. It is implemented as argued: a missing
  `jsonschema` denies. Nothing in the suite needed it relaxed.
- **S7** could have been satisfied by returning the fault only when no other
  error exists. It is instead satisfied by the fault being about the *check*:
  evidence missing eleven fields reports eleven field errors and exactly one
  schema fault.

### What the measurement changed about the original reasoning

The comment being replaced said mismatch is soft because *"adversarial packs
may intentionally violate severity enums"*. That is true of a minority. The
majority are packs the schema does not model at all. The conclusion survives;
the stated reason did not, and the code now carries the measured one.

---

## §4 The judgement call, stated before it is made

S4 turns a missing `jsonschema` into a denial. That is a real behaviour change
for any environment without it.

The argument for: `jsonschema>=4.20` is a declared runtime dependency in
`pyproject.toml`, not an extra. An environment without it is misconfigured, and
a misconfigured environment silently skipping a check is exactly M1 again.

The argument against: it is the one criterion here that can deny in an
environment that used to pass, for a reason that has nothing to do with the
evidence.

Recorded here, before the code, so the choice is visible rather than discovered
in a diff.

---

## §5 What this does NOT establish

- **Not that the schema is correct or complete.** M3 shows it is neither. This
  spec makes a *load* failure loud; it leaves the schema's content exactly as
  `UPTM-009` repaired it.
- **Not that evidence matching the schema is sound.** Mismatch stays soft by
  design, so the schema still gates nothing about evidence content.
- **Not that other swallows are gone.** This changes one `except` in one
  function. No survey of the rest was performed, and none is claimed.
