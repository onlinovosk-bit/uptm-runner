# UPTM-009 — The syntax gate: CI reads every file before it runs any of them

**Status:** preregistered 2026-09-25, before the implementation exists.
**Scope:** CI infrastructure. This guard enforces **no constitution principle**.
See §7 for what that means and why it is still routed.

---

## §0 Measurement first — the two failures this is built from

Both shapes were reproduced against the commits themselves, not from memory.

**M1 — `6b46cc2`, a merge that left a tuple unterminated.**

```
$ git show 6b46cc2:runner/enforcement.py | python -c "import ast,sys; ast.parse(sys.stdin.read())"
SyntaxError: '(' was never closed  | line 324
```

CI reported it as a collection error. 482 tests never ran. Nothing in the run
said *which file*; the traceback pointed at the collector.

**M2 — `a32a5ee`, a conflict resolution that kept both sides of a deleted step.**

```
$ git show a32a5ee:.github/workflows/pytest.yml
      - name: Enforcement evidence (UPTM-006)
        run: python -m runner.cli enforcement-evidence --commit "${{ github.sha }}"
      - name: Enforcement evidence (UPTM-006, Evidence Rule A)
        run: python -m runner.cli enforcement-evidence
```

The deleted step and its replacement both invoked the same subcommand. The first
exited 2 on an argument that no longer existed, so the second — the one that
mattered — never ran. `main` was red for 26 minutes before anything noticed.

Two more of the day's incidents (`b9175aa`, `5d8f384`) are **not** of this shape.
Both were semantically valid Python. This gate would not have caught either, and
this spec does not claim it would.

---

## §1 What the gate does

One CI step, before `pytest`, that parses every file the repository owns and
refuses the run when one of them does not parse.

It is deliberately **not** a linter. It answers one question — *can this file be
read at all* — and one repository-specific structural question (§3, G4).

---

## §2 Where it runs, and why there

After `pip install`, before `pytest`.

- **Not before install:** the workflow check needs a YAML parser, and PyYAML is
  a declared dependency. Install does not import the package (hatchling builds
  from source without executing it), so a syntax error in `runner/` cannot break
  the install step and hide behind it.
- **Not inside pytest:** a file that does not parse breaks *collection*. A test
  that runs after collection cannot report the thing that stopped collection.

---

## §3 Preregistered criteria

A criterion is met only if a test asserts it and that test fails when the
mechanism is removed.

| # | Criterion |
|---|---|
| **G1** | Every `.py` the repository owns parses. A file that does not is named with its path, line and the interpreter's own message. |
| **G2** | Every `.json` the repository owns parses. Same reporting. |
| **G3** | Every `.github/workflows/*.yml` parses as YAML. Same reporting. |
| **G4** | No job runs the same `runner.cli` subcommand in two steps. This is M2's shape exactly. The report names the subcommand and both step names. |
| **G5** | Every problem in the tree is reported, not just the first. A gate that stops at one turns a batch of merge damage into a queue of CI runs. |
| **G6** | The gate imports nothing from the tree it validates — stdlib and `yaml` only. Were it to import `runner.enforcement`, M1 would reach it as a traceback at import time, which is the failure it exists to replace. |
| **G7** | Exit 0 on a clean tree, exit 1 with a report on a dirty one. Nothing is written, nothing is fixed. |
| **G8** | Generated and vendored trees (`__pycache__`, `.git`, `.venv`, `node_modules`) are excluded, and the exclusion is by directory name, not by a hand-kept file list. |

### Reproduction criteria — the gate must catch the two real failures

| # | Criterion |
|---|---|
| **R1** | Given M1's exact file content, the gate reports it and exits 1. |
| **R2** | Given M2's exact workflow content, the gate reports the duplicated subcommand and exits 1. |

### Load-bearing criteria

| # | Criterion |
|---|---|
| **L1** | A `mutation-gate` case breaks the gate's own check and names the tests required to go red. A guard nobody can break on purpose is a guard whose removal is silent — the standing rule from `DEC-UPTM-APS`. |
| **L2** | The gate runs against this repository in its own test, so the criteria are asserted against the real tree and not only against fixtures. |

---

## §4 What this does NOT establish

- **Not that the code is correct.** It parses. That is all G1 claims.
- **Not that the workflow is right.** G3 says it is YAML; G4 rules out one
  specific duplication. A step that is wrong in any other way passes.
- **Not that merges are safe.** Two of the four incidents that motivated this
  gate produced valid files. Read this gate as *"no unreadable file reaches
  pytest"*, never as *"no bad merge reaches main"*.
- **Not a principle.** See §7.

---

## §5 Result

Measured on `db36c3d`, clean tree.

| # | Criterion | Result |
|---|---|---|
| G1 | every `.py` parses, named with line and the interpreter's own message | **PASS** |
| G2 | every `.json` parses | **PASS** |
| G3 | every workflow parses as YAML | **PASS** |
| G4 | no subcommand runs twice in one job | **PASS** |
| G5 | every problem reported, not the first | **PASS** |
| G6 | imports nothing from the tree it validates | **PASS** |
| G7 | exit 0 clean / exit 1 with report | **PASS** |
| G8 | generated trees excluded by directory name | **PASS** |
| R1 | M1's shape reported | **PASS**, with the adjustment below |
| R2 | M2's workflow reported | **PASS**, quoted exactly from `a32a5ee` |
| L1 | mutation-gate case, named sentinels go red | **PASS** |
| L2 | this repository passes its own gate | **PASS** |

```
518 passed              (505 + 12 new tests + 1, the mutation registry being
                         parametrised, so the new case became a test by itself)
syntax-gate             exit 0, "every file parses"
mutation-gate           exit 0, syntax-gate-stops-parsing caught by all 3 sentinels
enforcement-evidence    exit 0, 35 routes, reaching PASS [], another reason [],
                        unproven_claims [], claims_checked P8 P10 P12
```

### R1 was preregistered stricter than it was built

§3 says *"Given M1's exact file content"*. It is implemented as M1's reproduced
**shape** — an unterminated tuple — not the 900-line file from `6b46cc2`.

The reason is `actions/checkout@v4`, which fetches one commit. A test reaching
into the history would pass locally and fail in CI. R2 has no such problem and
**is** quoted exactly from `a32a5ee`.

This is recorded rather than quietly reworded: the preregistered criterion was
the stronger one, and what got built is weaker.

### The gate's first run found a fifth incident

`schemas/evidence.schema.json` had not parsed since `c4c409d`. That merge
concatenated both sides' `required` lists — dropping the comma after `stale_on`
and duplicating `assembled_prompt_digest` — and defined `wave_context` twice.
Repaired as the union of the two sides, keeping the stricter `wave_context`
(`minProperties: 1`, from `997dc54`).

It survived a day unnoticed because `runner/evidence.py` wraps the schema load
in `except Exception: pass`. The decode error was swallowed, so schema
validation has been silently inert — the gate has been reporting the absence of
a check as the absence of a problem, which is what "absence is not a
measurement" forbids.

**That swallow is not changed here.** Making the schema load-bearing is a
behaviour change and would need its own GO. Two things are consequently still
unverified: whether the repaired schema accepts real gate evidence (no committed
artifact is of that shape), and what else the swallow has been hiding.

---

## §7 Why a guard that enforces no principle is still registered

`DEC-UPTM-APS` set the rule: a guard nobody routes is a guard whose removal is
silent. APS-001 and EVIDENCE-STRUCTURE are registered in `NON_PRINCIPLE_GUARDS`
for that reason.

This gate is **not** registered there, and the distinction is deliberate. That
registry routes guards through `evaluate_gate` — guards that decide whether
evidence passes. The syntax gate decides nothing about evidence; it decides
whether CI can run at all. Routing it through `evaluate_gate` would assert a
relationship that does not exist.

Its silence is covered instead by the mechanism built for exactly that purpose:
a `mutation-gate` case (L1). Breaking the check must turn the suite red.
