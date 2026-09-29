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

*(filled in after the implementation, with output.)*
