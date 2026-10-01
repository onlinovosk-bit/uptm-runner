# UPTM-019 — The evidence schema's blind spot is bounded, and cannot widen silently

**Status:** preregistered 2026-10-01, before the implementation exists.
**Scope:** a ratchet over *which root keys the gate reads that the evidence
schema does not know*. **No schema change, no behaviour change, no fixture
change.** `LIVE_TRADING` stays `false`.

Founder GO, 2026-10-01: *"only a ratchet, tighten nothing"*, chosen over teaching
the schema the capital and kill-switch shapes and over leaving it alone.

---

## §0 What was measured

`UPTM-010` made a schema that cannot be **loaded** a fault, and left a schema
that does not **match** soft, because the schema was measurably behind the code.
Measured today, over the whole suite, by recording every `jsonschema.validate`:

| | |
|---|---|
| validations the suite performs | 321 |
| of which fail the schema | **189** (`UPTM-010` recorded 183; it moves with every new test) |
| what a failure does | **nothing** — `_schema_errors` returns `[]` on a mismatch |

So "soft" does not mean a warning. It means no effect: the schema today catches
exactly one thing, that it cannot be read.

Where the failures come from — root keys the evidence carries and the schema
(`additionalProperties: false`) does not know, counted by instances:
`kill_switch` 54, `capital` 49, `kill_switch_drill` 46, `capital_gate` 42,
`calendars` 39, `market_data` 39, `pnl` 39, `gate_criteria` 5, plus nine
one-offs from historical fixtures.

### What this is, and what it is not

It is **not** a live hole. Each detector reads its own pack and fails closed
(`UNKNOWN`) on a missing or ill-typed field, and `LIVE_TRADING` is `false`. It is
the project's own *declared ≠ enforced* applied to the schema: a contract that
names a document shape the gate does not actually hold documents to.

### Why not teach the schema now

The shapes would be derived from **fixtures**, not from real packs. Real packs
are produced by the trading repository, which this repository cannot read —
the same reason `account_equity` stayed in the pack (`DEC-UPTM-018`). A schema
taught from fixtures encodes what the tests happen to build.

### Why the count is not what gets pinned

The first idea was to pin `189 / 321`. It is the wrong quantity: every legitimate
new test adds validations, so the number changes with no change in the gap. What
is **stable** is the *set of root keys the runner reads that the schema does not
know*. That is derived from the source, not from the tests.

Derived by reading `runner/` as an AST (`evidence.get/pop/setdefault("k")`,
`evidence["k"]`, `"k" in evidence`), today:

| | |
|---|---|
| root keys the runner reads | 19 |
| known to the schema | 11 |
| **read but unknown to the schema** | **8** — `calendars`, `capital`, `capital_gate`, `gate_criteria`, `kill_switch`, `kill_switch_drill`, `market_data`, `pnl` |
| in the schema but never read | 7 (`branch`, `commands`, `commit_sha`, `pr`, `signature`, `skeleton`, `swarm_claim`) — a superset, not a gap |

Positive control, measured before it is preregistered: the base evidence fixture
**validates** against the schema, and corrupting a known field (`wave_id` as a
string) is **rejected**. The schema bites where it knows.

---

## §1 The ratchet

The 8 are **acknowledged**, not fixed, in `schemas/schema-gaps.json`: each key
with a reason. The ratchet is two-sided and only moves one way:

- a root key the runner starts reading that the schema does not know, and that is
  not acknowledged, **fails** — the author must either teach the schema or
  acknowledge the gap *with a reason*, as a visible act;
- an acknowledged key that the schema has since learned, or that the runner no
  longer reads, **fails** — so the baseline can only shrink.

Derived, never typed: the read-set comes from the source, the known set from the
schema. Only the *reasons* are typed, because they are explanations.

**Known limit.** The scan sees reads through a variable named `evidence` or `ev`.
A read through another name is not seen. Every function in `runner/` that takes
the document names its parameter `evidence`; the limit is stated, not hidden.

---

## §2 Preregistered criteria

| # | Criterion |
|---|---|
| **K1** | The scan recognises all four read shapes on **synthetic** source, ignores other variables and non-literal keys, and yields only the **root** key for nested access (`evidence["a"]["b"]` → `a`). |
| **K2** | The scan on the real `runner/` is non-vacuous, and nothing about it is typed: it finds at least one key the schema knows **and** at least one it does not. |
| **K3** | On the real repository, the baseline **equals** the derived gap (read ∖ known), and every entry carries a non-empty reason. |
| **K4** | A new, unacknowledged gap **fails**, names the key, and names both ways out. Shown on synthetic inputs. |
| **K5** | A stale entry fails — **each cause separately**: the key is now in the schema; the key is no longer read. |
| **K6** | A blank reason, a non-object baseline, or a duplicate entry **fails**. |
| **K7** | Positive control: the base evidence fixture validates against the real schema, and a corrupted **known** field is rejected. |
| **K8** | No behaviour change. `_schema_errors` still returns `[]` on a mismatch (pinned by `UPTM-010`'s own tests, untouched); no file under `runner/` other than `mutation_gate.py` and not `schemas/evidence.schema.json` changes. Recorded in §4 with `git diff`. |

### Load-bearing

| # | Criterion |
|---|---|
| **L1** | `schema-gap-widens-silently` — the runner gains a read of a key the schema does not know; `K3` goes red. |
| **L2** | `schema-gap-baseline-goes-stale` — an acknowledged key the schema **does** know is added to the baseline; `K3`/`K5` go red. |
| **L3** | **The gap is measured.** Under `L1`'s mutation, run before the guard exists, **every existing test stays green**. If one goes red, the premise that this was unguarded is wrong. (`L2`'s mutation lives in the new baseline file, which nothing pre-existing reads, so it can only be shown red, not shown unguarded.) Recorded in §4. |

---

## §3 What this does not do

- It does **not** teach the schema anything and **tightens nothing**. Mismatch is
  still silent; the 8 keys are still unknown to it.
- It does **not** cover the nine one-off keys from historical fixtures; nothing in
  `runner/` reads them.
- It does **not** pin the failing-validation count (unstable, see §0).
- It does **not** see reads through a variable not named `evidence` or `ev`.
- It does **not** change `UPTM-010`: a schema that cannot load is still a fault; a
  schema that does not match is still soft.

---

## §4 Result

Built on 2026-10-01. Written after the criteria above, in a later commit.

| artifact | what it is |
|---|---|
| `schemas/schema-gaps.json` | the 8 acknowledged keys, each with a reason |
| `tests/test_schema_gap_ratchet.py` | 39 tests, each naming its criterion |
| `runner/mutation_gate.py` | two cases, one per direction of the ratchet |

### An amendment made during implementation

**`K2` was wrong as preregistered, and is built differently.** It said the real
scan must find *at least one key the schema knows **and** at least one it does
not*. Written down, that would **fail on the day the gap is closed** — the
baseline empty, the ratchet reaching its goal — and punish the success it exists
to produce. It is built as: the scan finds reads, and some of them are keys the
schema knows (so it is demonstrably reading evidence). Nothing about the number
of unknown keys is asserted. A test (`test_k5_closing_the_whole_gap_passes_…`)
pins the success case explicitly. The flaw was found while writing the code, not
by a failing result; it is recorded here rather than rewritten into the spec above.

### Criteria, discharged

| # | how |
|---|---|
| K1 | 17 parametrised read shapes — `get`/`pop`/`setdefault`/subscript/`in`/`not in`, the `ev` alias, nested access yielding only the root, and ten things that must **not** count (other variables, non-literal keys, a non-string key, `.keys()`) — plus a read inside a nested function. |
| K2 | `test_k2_*` — as amended above. |
| K3 | `test_k3_*` — on the real repository the baseline **equals** the derived gap, and every entry carries a reason of at least five words. |
| K4 | the consistent state passes; a new gap fails naming the key, the file and **both** ways out; each way out, taken, passes. |
| K5 | stale because the schema learned the key; stale because the runner stopped reading it — each separately; and closing the whole gap passes. |
| K6 | blank, whitespace-only and non-string reasons; a duplicate; and three malformed shapes are each refused. |
| K7 | the base fixture validates against the real schema; a corrupted known field is rejected; an unknown root key is rejected **by the schema itself** (`additionalProperties: false`) — which is why the gap exists, and why it is silent. |
| K8 | `test_k8_*` asserts a mismatch is still silent in the gate; `git diff main...HEAD`: **0** files under `runner/` other than `mutation_gate.py`, **0** touching `schemas/evidence.schema.json`. |
| L1 | `schema-gap-widens-silently` — caught by `test_k3_…equals_the_derived_gap…`. |
| L2 | `schema-gap-baseline-goes-stale` — caught by the same test. |
| L3 | measured by hand, below. |

### What the ratchet says when it goes red

```
schema-gap-widens-silently:
  NEW GAP: `brand_new_pack` is read by runner/gates.py but is unknown to the evidence
  schema and not acknowledged. Either teach schemas/evidence.schema.json the key, or
  acknowledge it in schemas/schema-gaps.json with a reason.

schema-gap-baseline-goes-stale:
  STALE: `signature` is acknowledged as a gap but the schema now knows it - remove it
  from schemas/schema-gaps.json.
```

### L3 — the gap, measured

Before the guard existed, with the runner reading a new key the schema was never
taught (`evidence.get("brand_new_pack")` added to `runner/gates.py`):

```
877 passed
```

Every existing test stayed green: the gap would have widened silently. With the
guard, the same edit turns exactly one test red and names what to do.

### Verified

| check | result |
|---|---|
| syntax gate | every file parses |
| `pytest` | **918 passed** (877 + 39 + the two tests the gate generates for the new cases) |
| `mutation-gate` | **37 cases, `ok: true`, `baseline_error: None`**, tree clean after |
| `enforcement-evidence` | `ok: true`, `tree_clean: true`, `unproven_claims: []` — on the committed head |

### What this does not do

- It does **not** teach the schema anything and **tightens nothing**. Mismatch is
  still silent; the 8 keys are still unknown to it. A malformed `capital` or
  `kill_switch` pack is still caught only by its own detector, which fails closed.
- **The scan sees reads through a variable named `evidence` or `ev`.** A read
  through another name is invisible to it. Every function in `runner/` that takes
  the document names its parameter `evidence`, so today that is every read — but it
  is a convention, not a guarantee.
- It does **not** cover the nine one-off keys from historical fixtures; nothing in
  `runner/` reads them.
- It does **not** pin the failing-validation count; that number is unstable by
  construction.
- The real fix — teaching the schema the capital and kill-switch shapes — waits for
  a **real pack** from the trading system, and is then a behaviour change with its
  own GO.
