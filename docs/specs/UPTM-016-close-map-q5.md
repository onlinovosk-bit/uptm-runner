# UPTM-016 — Closing MAP-Q5: no canonical numbering, qualified at source

**Status:** preregistered 2026-09-28, before the implementation exists.
**Scope:** how a wave is named across a repository boundary. No market data, no
trading. `LIVE_TRADING` stays `false`.

---

## §0 What the question actually asks

> *Which wave vocabulary is canonical? Two systems numbering waves 0–7 and 0–9
> will keep colliding in status lines.*

The collision is documented and has already caused a real error — the governance
map records that its own author conflated `uptm-runner`'s wave 7
(`exit_and_archive`) with the trading repository's `W7` (`INDEPENDENT RED TEAM`)
on the day it was written.

**Picking a canonical numbering does not fix it, and cannot be done here.**

- Renumbering this repository 0–9 would rewrite eight wave artifacts to solve a
  problem in *how they are quoted*, and every status line already written would
  stay ambiguous.
- Declaring 0–7 canonical for the other repository claims authority this
  repository does not have. It cannot even read that repository.

So **neither numbering becomes canonical** — that part of the open record
survives the closure unchanged. What is adopted is the thing that actually
removes the failure: **a wave reference that leaves its own repository must
carry it.**

---

## §1 Qualify at source, not at the quote

Policing quotations does not work: the rule would live in whoever is writing the
status line, which is exactly where it failed last time.

Measured before designing: every bare `W7` in this repository today is **prose
about the collision** — nine in the governance map, two in the decisions log,
one in `docs/evidence-rule-a.md`, one in a docstring. **None is a status
claim.** The ambiguity does not enter through prose. It enters when a number is
lifted out of a wave artifact, and those artifacts carry bare integers
(`wave_id: 7`, `"waves": [0..7]`).

So the qualification goes **into the data**, where a correct quote becomes the
easy one rather than the disciplined one.

---

## §2 Which numbers are actually ambiguous

Not all of them, and the set is **derived**, not listed:

- **ours** is measured from `waves/wave*.yaml` on disk — `{0…7}` today;
- **theirs** is *recorded* as `{0…9}` from the governance map, with its source
  named. This repository cannot read `onlinovosk-bit-uptm` and must not pretend
  the number was measured;
- **ambiguous** is the intersection. `W8` and `W9` are unambiguous — this
  repository has no such wave.

Adding `wave8.yaml` here would make `W8` ambiguous **without anyone editing a
list**. That is the point.

---

## §3 Preregistered criteria

| # | Criterion |
|---|---|
| **N1** | Nothing is renumbered. Every `wave_id` keeps the value it has, asserted against the files. |
| **N2** | Every wave artifact declares its repository, so a value lifted out of it is qualified at source. |
| **N3** | `waves/index.json` agrees with the files on disk — derived, so a wave added or removed without updating the index is a finding. |
| **N4** | The ambiguity set is the intersection of the two ranges, computed. A test adds a synthetic wave and shows the set change, on a range this spec never listed. |
| **N5** | `qualify` and `parse` round-trip; a bare reference parses with no repository; `is_ambiguous` is true exactly on the intersection, and the direction of the unambiguity is asserted (`W8` is theirs, not "nobody's"). |
| **N6** | The other repository's range is recorded, **not** measured: the module says so and names the map as its source. A test asserts the provenance rather than the number alone. |
| **N7** | **Prose explaining the collision is not a status claim.** The governance map's `W7` examples must survive; a test asserts they are still there, so a later tidy-up cannot delete the teaching. |
| **N8** | The map and the decisions log record Q5 closed in **both** places the openness is currently stated, and MAP-Q3 stays open. |

### Load-bearing

One case per independent mechanism, named in advance:

| # | Criterion |
|---|---|
| **L1a** | `wave-artifact-loses-its-repository` — an artifact stops declaring which repository it belongs to; the named tests go red. |
| **L1b** | `wave-ambiguity-set-hardcoded` — the intersection is replaced by a literal set, so adding a wave no longer changes it; the named tests go red. |
| **L2** | No wave file is renumbered and no wave is added or removed by this change. |

---

## §4 Result

*(filled in after implementation)*

---

## §5 What this does NOT establish

- **Not a canonical numbering.** Neither survives as "the" vocabulary, and that
  part of `DEC-UPTM-MAP-Q5` is kept rather than overturned.
- **Not anything about the other repository's artifacts.** Its range is recorded
  from the map, unverified, and this change does not reach into it.
- **Not a rule over prose.** Documents explaining the collision keep their bare
  `W7`, and a test protects them.
- **Not a principle state change.** No enforcement state moves.
