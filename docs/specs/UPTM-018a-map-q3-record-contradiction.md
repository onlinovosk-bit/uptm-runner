# UPTM-018a — The map says Q3 is unadopted and decided in the same document

**Status:** preregistered 2026-09-29, before the implementation exists.
**Scope:** one contradiction in `docs/architecture/governance-map.md`, and the
guard that failed to see it. No code under `runner/` changes behaviour, no
number changes, no principle moves. `LIVE_TRADING` stays `false`.
**Depends on nothing:** independent of the two capital numbers `UPTM-018` still
waits for from the Founder.

---

## §0 What was found

The same document, about the same label, says two opposite things.

| where | says |
|---|---|
| line 112, under *"The two capital numbers are not the same number"* | **"DEC-UPTM-MAP-Q3 leaves that relation unadopted."** … "is not decided here." |
| line 166, question 3 | **"DECIDED (DEC-UPTM-MAP-Q3, 2026-09-29): THE ACCOUNT IS A FLOOR UNDER THE TRANCHE."** |

They are not two questions. Question 3 is titled *"How do €700 and €750
relate?"* — the same pair line 112 says nobody related. Line 112 was introduced
by `5a6ecb0` (PR #38, 2026-09-25, *"Leave the relation between EUR 700 and
EUR 750 open"*), when the label `DEC-UPTM-MAP-Q3` meant *"decided to leave it
open"*. `UPTM-017` closed the question under **the same
label**, updated the question block, and did not touch the paragraph that
described the earlier state. So the label now stands for both.

### The code is fine; the record is wrong

`check_vc_i6_account_covers_the_ceiling` reads `capital.account_equity` from the
pack under evaluation. It does not read €750 from the other repository, and
nothing in this repository does. P11 holds. Only the *explanation* of the
decision is stale.

### Why no test saw it

`test_map_q3_is_decided_as_a_floor_and_copies_no_number` slices the text from
`"3. **How do €700 and €750 relate?"` to `"\n4. "` and asserts what is *inside*
that block. It proves the decision **is present**. It cannot prove the decision
is **not also contradicted** — the contradiction lives outside the slice. The
guard is one-sided: it checks that the right thing was written, never that the
wrong thing is gone.

That is the class of defect, not this instance. Both are addressed.

---

## §1 What is measured before designing

Run over the whole map, per `DEC-UPTM-MAP-Q<n>` label, on the unmodified file:

| label | states asserted | conflict |
|---|---|---|
| `Q1` | DECIDED | no |
| `Q2` | DECIDED | no |
| `Q3` | **OPEN (line 112) and DECIDED (line 166)** | **yes** |
| `Q5` | DECIDED | no |

So the contradiction is **exactly one**, and the sibling questions are clean.
This is what makes a general guard worth its cost: it would have caught Q3 and
would keep watching Q1, Q2 and Q5, which already carry the same closure pattern.

Two facts about the document shaped the design and are recorded rather than
assumed:

1. **The question list is one paragraph.** Items 1–5 have no blank lines
   between them, so a *paragraph* is the wrong unit — it would attribute
   question 1's `DECIDED` to question 3's label. The unit must be the **list
   item**, with prose paragraphs as their own units.
2. **Question 4 carries no `DEC-UPTM-MAP-Q4` label.** It is recorded in its own
   form (struck-through title, `DECIDED 2026-09-24`). The guard therefore
   covers *labelled* questions only, and says so; it does not pretend to cover
   Q4.

The label set in the map, `{Q1, Q2, Q3, Q5}`, equals the set of
`## [date] DEC-UPTM-MAP-Q<n>` headings in `docs/decisions.md`. That equality is
what stops the scan silently skipping a label.

---

## §2 What is adopted

**No decision is made here.** The Founder decided Q3 in `DEC-UPTM-017`; this
work records that decision truthfully where it is currently misdescribed.

1. The paragraph under *"The two capital numbers…"* is rewritten to say what
   `DEC-UPTM-MAP-Q3` decided: the relation is a **floor** — a declared account
   must be at least the tranche — and it is carried by the pack's own
   `capital.account_equity`, **not** by the €750 recorded from the other
   repository. Neither number is rewritten into the other. It points to
   question 3 rather than restating the decision, so there is one place to
   maintain it.
2. A guard that checks **both directions**: per label, a document may assert
   that it is decided, or that it is open — never both.
3. One mutation case that puts the original sentence back.

---

## §3 Preregistered criteria

### The record

| # | Criterion |
|---|---|
| **R1** | The numbers paragraph names `DEC-UPTM-MAP-Q3` **and** the relation it adopted (*floor*). It is the label's whole answer in one place, not a pointer to a missing one. |
| **R2** | The numbers paragraph contains none of the openness wording (`unadopted`, `not adopted`, `not decided`, `OPEN`, `stays open`). |
| **R3** | It states that the comparison reads a figure **the pack declares**, and that €750 is recorded, not measured — so the sentence cannot be read as this repository reaching into the other. |
| **R4** | Nothing is copied: `750` is still absent from `constitution/capital-rules.json`, `validation_capital.amount` is still `700`, `CONSTITUTION-CAPITAL.md` is still v1.0 LOCKED. Asserted by the tests that already assert it, **unchanged**. |

### The guard

| # | Criterion |
|---|---|
| **G1** | For every `DEC-UPTM-MAP-Q<n>` label in the map, the states asserted across all units are one of `{DECIDED}` or `{OPEN}` — never both. |
| **G2** | Unit = list item or paragraph, **not** paragraph alone. Asserted on synthetic text: question 1 `DECIDED` and question 2 `OPEN` inside one paragraph-shaped list **pass**; question 3 both **fails**. |
| **G3** | The classifier is shown to bite on the **actual defect**: the verbatim line-112 sentence, beside a `DECIDED` line for the same label, is reported as a conflict naming the label. |
| **G4** | It is **not** a rule that everything must be decided. A label that is only `OPEN` **passes**; a label mentioned with no state word **passes**. A question may legitimately reopen through a new decision, and the guard must not forbid it — it forbids *contradiction*. |
| **G5** | No false positive across labels: `Q1` `DECIDED` and `Q2` `OPEN` anywhere in the document **passes**. |
| **G6** | The scan cannot pass vacuously on the real map: the labels it finds equal the `DEC-UPTM-MAP-Q<n>` headings in `docs/decisions.md`, and every one of them carries at least one state. |
| **G7** | The existing one-sided test is **kept, unchanged**. It answers "is the decision present". The new one answers "is it also contradicted". They are different questions and neither replaces the other. |

### Known limit, stated so it is not a surprise

The openness vocabulary is **recorded from this map's own history**, not
derived — a novel phrasing (*"remains to be chosen"*) would evade the classifier.
R1 is the second net: the numbers paragraph must positively carry the relation,
so deleting or rewording it away fails a different test. Closing the vocabulary
gap fully would need the claim in structured form, which is a larger change than
this and is not attempted.

### Load-bearing

One case, named in advance:

| # | Criterion |
|---|---|
| **L1** | `map-q3-relation-reads-unadopted-again` — the rewritten sentence is replaced by the original line-112 sentence; the two-sided guard goes red. |
| **L2** | **The gap is measured, not asserted.** Under the same mutation the existing one-sided test `test_map_q3_is_decided_as_a_floor_and_copies_no_number` must stay **green**. The gate can require a sentinel to fail but cannot require a test to pass, so this is run by hand and recorded in §4 with its output. If it does *not* stay green, the premise of §0 is wrong and the guard's claimed novelty with it. |

---

## §4 Result

Built on 2026-09-29. Written after the criteria above, in a later commit.

| artifact | what it is |
|---|---|
| `docs/architecture/governance-map.md` | the numbers paragraph now says what `DEC-UPTM-MAP-Q3` decided; nothing else touched |
| `tests/test_governance_map_consistency.py` | 18 tests, each naming its criterion |
| `runner/mutation_gate.py` | one case, `map-q3-relation-reads-unadopted-again` |

### Criteria, discharged

| # | how |
|---|---|
| R1 | `test_r1_*` — label, *floor* and `VC-I6` all in the numbers paragraph. |
| R2 | `test_r2_*` — no openness wording in it. |
| R3 | `test_r3_*` — `capital.account_equity`, *declares*, *never measured*, *nothing here commands the other repository*. |
| R4 | `test_r4_*` — `700` kept, `750` absent from `capital-rules.json`, constitution v1.0 LOCKED. |
| G1 | `test_g1_*` on the real map, plus six parametrised cases — one per recorded way of saying "open". |
| G2 | `test_g2_*` — a two-item list is two units; Q1 decided beside Q2 open passes; Q2 asserting both fails. |
| G3 | `test_g3_*` — the verbatim `5a6ecb0` sentence beside a `DECIDED` line: exactly one conflict, naming `DEC-UPTM-MAP-Q3`. |
| G4 | two tests — an open-only label passes; a state-less mention passes. |
| G5 | `test_g5_*` — a decided label and an open label do not contaminate each other. |
| G6 | `test_g6_*` — labels in the map equal the `DEC-UPTM-MAP-Q<n>` headings in the decisions log, and each asserts a state. |
| G7 | `test_g7_*` — the older one-sided test is still in `tests/test_governance.py`, untouched. |
| L1 | `map-q3-relation-reads-unadopted-again` — caught by `g1`, `r1` and `r2`. |
| L2 | measured by hand, below. |

### L2 — the gap, measured

Under exactly the L1 mutation, run individually:

```
GREEN  test_map_q3_is_decided_as_a_floor_and_copies_no_number      <- the older guard
RED    test_g1_no_label_in_the_map_is_asserted_both_decided_and_open
RED    test_r1_the_numbers_paragraph_states_the_relation_that_was_adopted
RED    test_r2_the_numbers_paragraph_carries_no_openness_wording
```

The premise of §0 holds: the older test was blind to this. What the new guard
says under the mutation:

```
DEC-UPTM-MAP-Q3 is asserted both DECIDED and OPEN:
  [DECIDED] 3. **How do €700 and €750 relate?** **DECIDED (DEC-UPTM-MAP-Q3, 2026-09-29) …
  [OPEN]    They are not in conflict, and they are not the same thing: €700 is the size …
The map is a current-state document: say what the label decided and put the
history of the earlier state in docs/decisions.md.
```

Run against `main`'s actual, unmutated map, the guard reports **exactly one**
conflict, `DEC-UPTM-MAP-Q3`, with `Q1`, `Q2` and `Q5` clean — the same result §1
measured before the design existed.

### How it was verified, and why not on `main` alone

`main` was red on the calendar when this was built (a second pinned drill date;
8 failed, 822 passed at 2026-09-29T21:03Z), and `mutation-gate` **refuses to run
on a red baseline**. The repair is a separate change, `claude/fix-drill-fixture-clock`.
So the full proof was produced on a **local, unpushed integration branch** —
this work merged with that repair:

| check | on this branch alone | on the integration branch |
|---|---|---|
| `pytest` | 8 failed, 841 passed (the 8 are the calendar, none in this change) | **851 passed** |
| syntax gate | — | every file parses |
| `mutation-gate` | refuses: baseline red | **34 cases, `ok: true`, `baseline_error: None`**, tree clean after |
| `enforcement-evidence` | — | `ok: true`, `tree_clean: true`, `unproven_claims: []` |

**CI on this branch is red until the repair merges.** That is the repair's
absence, not this change; the eight failing tests are the same eight, in
`tests/test_detector_invocation.py`.

### What this does not do

- **It does not close the vocabulary gap.** The openness wording is recorded
  from this map's history, not derived. R1 is the second net; a structured claim
  would be the real fix and is a larger change than this.
- **It does not cover question 4**, which carries no `DEC-UPTM-MAP-Q4` label.
- **It does not touch `docs/decisions.md`.** The 2026-09-25 entry for
  `DEC-UPTM-MAP-Q3` says the question "stays OPEN" and carries no forward pointer
  to `DEC-UPTM-017`. In a dated log that is normal chronology — a later entry
  supersedes an earlier one — and rewriting history is not this change's to do.
  It is **noted, not fixed**: a one-line "superseded by" pointer would be a
  Founder call.
- **It does not settle the two capital numbers** `UPTM-018` waits for. Without
  them VC-I5 and VC-I6 still end at `UNKNOWN`, which is the correct state.
