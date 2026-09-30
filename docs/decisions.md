# UPTM — Decisions Log

Founder decisions about the UPTM Runner, and where each one is enforced.

**Why this file exists.** P14 requires that constitutional and parameter changes
be made by the Founder "explicitly, with a recorded reason". A reason that lives
only in a commit message or a pull-request body is not recorded — it is
retrievable, which is not the same thing. This is where the reason lives.

**Scope.** UPTM only. Revolis.AI / RealitkaAI decisions do not belong here, and
UPTM decisions do not belong there.

**Format.** Newest first. Every entry names what was decided, why, and the
artifact that makes it real. A decision with no artifact is a plan, and says so.

---

## [2026-09-30] DEC-UPTM-018 — `account_equity` is the pack's, not the constitution's

**Decided:** Founder GO, choosing the option that builds nothing: `capital.account_equity`
stays a figure the **pack declares**; no account figure is added to
`constitution/capital-rules.json`. Preregistered in
`docs/specs/UPTM-018-account-equity-stays-in-the-pack.md` before the
implementation existed (P4).

**What was found first.** The handover carried this as "the Founder owes two
numbers, and 700 is only a fixture". It is not: `validation_capital.amount` has
been set since 2026-09-23 (`DEC-UPTM-004`, `set_by: founder`). Only
`account_equity` is missing, and it was never a repository parameter. On the
real configuration VC-I6 already gives `UNKNOWN` naming the key when a pack omits
it, `FAIL` below the tranche and `PASS` at or above it.

**Why not the other option.** A constitution-level account figure would sit
beside the pack's. The day the two differ, which one wins is `MAP-Q2` again —
closed as *neither wins*, i.e. `DENY` — so it would recreate a solved problem,
and it would put a number of the other side's kind into this constitution, which
`MAP-Q3` was written to avoid. The value is the Founder's appetite for risk and
is entered where the account is: the first real pack.

**What changed.** The note `uptm004_detector.founder_parameter_required` said the
three tranche parameters were "unset"; they have been set for a week. It is
corrected, not deleted, and now leads with a status word. A new guard makes the
status word equal the state of the parameters it describes, derived from the
data and checked in both directions. No runner behaviour changed and no number
was added; `VC-I5` and `VC-I6` are exactly as `UPTM-017` left them.

**Still open, and correctly so:** until a pack declares `account_equity`, the
capital gates end at `UNKNOWN`. That is the intended state, not a gap.

**Artifact:** `tests/test_capital_parameter_status.py`, one `mutation-gate` case
(`capital-note-claims-unset-again`), the corrected note. `LIVE_TRADING` stays
`false`.

---

## [2026-09-29] DEC-UPTM-017 — what €700 counts, and the floor that makes it real

**Decided:** Founder GO, in two parts: define the unit of `at_risk`, then adopt
**option C** for `DEC-UPTM-MAP-Q3`. Built as `UPTM-017`, preregistered in
`docs/specs/UPTM-017-at-risk-unit-and-account-floor.md` before the
implementation existed (P4).

**This closes MAP-Q3, and with it the last open governance question.**

### The question could not be answered as asked

Relating €700 to €750 turned out to be ill-posed on one side. Measured:

| `applies_to` term | what the detector reads | unambiguous |
|---|---|---|
| `cumulative_realised_loss` | `pack["cumulative_realised_loss"]` (VC-I3) | yes |
| `aggregate_open_exposure` | `pack["at_risk"]` (VC-I2) | **no** |

`aggregate_open_exposure` was a **switch, not a definition**: its presence in
`applies_to` turned on a comparison of a differently-named field against the
amount, and nothing said whether `at_risk` was notional, margin or risk to
stop. For ES/MES those differ by orders of magnitude — one MES around index
6000 is roughly $30,000 notional, ~$1,500 margin, perhaps €50 of risk to a
stop. €700 therefore meant "no trade at all", "one contract" or "fourteen
trades" depending on which nobody had said.

This repository had already caught the *name* mismatch and recorded it. The
name was fixed. **The unit never was.**

### The unit: risk to stop

Adopted because it is the only one of the three that measures **money that can
be lost**, which is what the constitution's own note says €700 is. Notional
would make P10 forbid trading outright — €700 of notional buys no contract, and
a cap permitting no test cannot be the size of the test. Margin is a broker and
exchange artefact that moves with volatility and says nothing about loss.

**Said out loud, because it decides the design: a stop is not a guarantee.**
Gaps and limit moves mean realised loss can exceed planned risk. So `at_risk`
bounds **intent** and `cumulative_realised_loss` bounds **outcome** — which is
exactly why the two terms are not redundant. One catches a plan that risks too
much; the other catches a plan that was within its limit and lost more anyway.
A single number could not do both.

### The floor: option C

A loss ceiling halts the test only while the account can reach it:

| account | €700 binds at |
|---|---|
| 1000 | 70 % |
| 750 | 93 % |
| **500** | **never — the account empties first** |

At the bottom of the recorded range, what would halt the test is the account
running out, which is not a decision anybody made. So a tranche binding
`cumulative_realised_loss` is valid only when the declared account is at least
the tranche amount, and below that the **configuration** is refused — not the
trade, because the defect is in the setup and no individual action is at fault.

**It needs no authority over the other repository.** It refuses rather than
commands, which is the shape `MAP-Q1` and `MAP-Q2` settled. Neither number is
rewritten into the other: €700 is unchanged, €750 stays recorded-and-unverified
in the map, `750` appears nowhere in this constitution, and a test asserts that.

### Blast radius, stated before it was built and then measured

`run_validation_capital_detectors` returns early for evidence carrying no
capital pack and not declaring `capital_gate`. **Non-capital gates are
untouched** — `U8` asserts it. Within capital gates the effect is real and was
not softened: a pack omitting either field denies. Two existing fixtures had to
declare what they had previously left unsaid.

### Guards re-aimed, not deleted

`test_map_q3_stays_open` became
`test_map_q3_is_decided_as_a_floor_and_copies_no_number`, and
`map-q3-marked-decided` became `map-q3-turned-into-a-ceiling`. Both now forbid
the option that was *not* chosen: making €700 a ceiling on the other
repository's account, which would impose a change on a repository this one
cannot read.

Two UPTM-015/016 tests that asserted Q3 still open now assert it closed **under
its own marker and date** — it was not swept up with the others; it stayed open
a further day and was decided separately.

### What did not change

€700. The name `aggregate_open_exposure` — renaming a Founder parameter is P14's
business. No principle's enforcement state: still `ENFORCED 3 / PARTIAL 6 /
DECLARATIVE 1 / MISSING 4`.

**Artifact:** `runner/detectors/validation_capital.py` (VC-I5, VC-I6),
`tests/test_at_risk_unit_and_floor.py` (28 tests),
`docs/architecture/governance-map.md`, `constitution/capital-rules.json`
(P10 check count 9 → 11), two `mutation-gate` cases (32 total, `ok: true`),
830 tests passing. No market data, no network call. `LIVE_TRADING` stays
`false`.

---

## [2026-09-28] DEC-UPTM-016 — MAP-Q5 closed without a canonical numbering

**Decided:** Founder GO to close `DEC-UPTM-MAP-Q5`. Built as `UPTM-016`,
preregistered in `docs/specs/UPTM-016-close-map-q5.md` before the implementation
existed (P4).

### Why picking a canonical numbering was not the answer

The collision is real and has already cost something: this map records that its
own author conflated this repository's wave 7 (`exit_and_archive`) with the
trading repository's `W7` (`INDEPENDENT RED TEAM`) on the day it was written.

But **neither candidate fix works**:

- Renumbering this repository 0–9 would rewrite eight wave artifacts to solve a
  problem in how they are **quoted**, and every status line already written
  would stay ambiguous.
- Declaring 0–7 canonical for the other repository claims authority this one
  does not have, over a repository it cannot even read.

So **neither numbering is canonical** — that part of the open record survives
its own closure, which is an unusual shape for a decision and the honest one
here.

### What was adopted instead

**A wave reference that leaves its repository must carry it**, and the
qualification lives **in the data**.

Policing quotations would put the rule in whoever writes the status line, which
is precisely where it failed. Measured before designing: every bare `W7` in this
repository is **prose about the collision** — nine in the map, two here, one in
`evidence-rule-a.md`, one docstring. **None is a status claim.** The ambiguity
enters when a number is lifted out of a wave artifact, and those carried bare
integers.

So every `waves/wave*.yaml` now carries `repository` and `qualified_id`, and
`waves/index.json` carries the repository and the qualified list. A single field
lifted out of a file is already qualified. `qualified_id` is redundant with
`wave_id` plus `repository` **on purpose** — the failure is a lone field being
quoted — and because redundancy in data is drift waiting to happen, the
agreement is derived and checked rather than trusted.

### Which numbers are ambiguous is derived

Ours is **measured** from the files on disk. Theirs is **recorded** from the
map, with its provenance carried beside the number, because this repository
cannot read `onlinovosk-bit-uptm` and must not dress a recalled number as a
measured one. Ambiguous is the intersection.

`W8` and `W9` are **not** ambiguous — this repository has no such wave — and the
tests assert the *direction*: they are unambiguously **theirs**, not nobody's.
Adding `wave8.yaml` here would change that with nobody editing a list, and a
test proves it on a range this spec never listed.

### What was protected

`N7` preregisters a test that keeps the map's own `W7` examples alive. A later
tidy-up that qualified every reference in the document would delete the example
the document exists to give. Prose explaining the collision is not a status
claim.

### What did not change

No wave was renumbered, added or removed — `N1` and `L2` assert it against the
files. No principle's enforcement state moved.

**Four of five governance questions are now closed.** `DEC-UPTM-MAP-Q3` (€700
versus €750) is the last, and it is the one that is an appetite for risk rather
than a convention — so it is not mine to close.

**Artifact:** `runner/wave_names.py`, `tests/test_wave_names.py`,
`waves/*.yaml`, `waves/index.json`, `docs/architecture/governance-map.md`, two
`mutation-gate` cases. `LIVE_TRADING` stays `false`.

---

## [2026-09-28] DEC-UPTM-015 — MAP-Q1 and MAP-Q2 closed, and the switch left off

**Decided:** Founder GO to close `DEC-UPTM-MAP-Q1` and `DEC-UPTM-MAP-Q2`, open
since 2026-09-25. Built as `UPTM-015`, preregistered in
`docs/specs/UPTM-015-close-map-q1-q2.md` before the implementation existed (P4).

Neither was really a preference. Each has one answer that survives contact with
principles already adopted, so the work was to show the derivation rather than
to pick.

### MAP-Q1 — must a trading-system wave gate satisfy the capital constitution?

**YES.** The governance map refutes "no" in its own sentence: *"If no, P8 and
P10 are enforced against something that never runs."* Those are two of the
**three** principles that are actually `ENFORCED`, and the constitution's
SUCCESS CONDITION is independent evidence of robustness — which a runner with
no subject cannot produce.

What was open was never the question. It was the **mechanism**: no artifact
links a trading wave to an evidence document. Adopting "yes" converts an open
question into a **named unmet requirement**, which looks worse on the board and
is more honest. This repository still does not invent the link.

### MAP-Q2 — which repository's verdict wins a disagreement?

**NEITHER.** The question assumes a tie to be broken. P11 says uncertainty
halts; `GOVERNANCE.md` C3 says silence is not permission — a sentence
`resolve_planes` already cites in its own docstring.

**A disagreement is not a tie. It is uncertainty.** So disagreement resolves to
`DENY`, and so does the absence of a counterpart verdict: an unread verdict is
not an `ALLOW`. `runner/cross_repository.py` makes that executable and reports a
disagreement as a **dispute** carrying both sides, never as one side having
lost — because "the control plane's `PASS` won" would claim the other verdict
was read and overruled, when what happened is that nobody knows which is right.

### What closing them exposed

Today `evaluate_gate` reaches `ALLOW` **without ever asking the trading
system**. Absence currently behaves as permission — the exact thing Q2's answer
forbids.

**So the mechanism is built and deliberately left disconnected**, and a test
asserts it stays that way. Wiring it in would deny **every** current `PASS`,
because no trading-system verdict exists and `onlinovosk-bit-uptm` is not even
in this session's scope. That is a separate Founder decision with its own GO.

A switch that is off and known is safe. A switch that is off and forgotten is
the next `DECLARATIVE` principle, and this repository already has one of those.

### What did not change

No principle's enforcement state moved — a test reads `capital-rules.json` and
asserts the counts are still `ENFORCED 3 / PARTIAL 6 / DECLARATIVE 1 /
MISSING 4`. `CONSTITUTION-CAPITAL.md` v1.0 stays LOCKED, so no P12 invalidation
follows. MAP-Q3 and MAP-Q5 stay open and were not swept up with these two; a
test asserts that too.

**Artifact:** `runner/cross_repository.py`, `tests/test_cross_repository.py`,
`docs/architecture/governance-map.md`, two `mutation-gate` cases. Two of five
governance questions closed, and both closures **create work rather than
finishing it**. `LIVE_TRADING` stays `false`.

---

## [2026-09-28] DEC-UPTM-014 — the roll rule: two joins are admissible, and the standard one is not

**Decided:** Founder GO on the roll rule, the second undefined term `UPTM-013`
found. Built as `UPTM-014`, preregistered in `docs/specs/UPTM-014-roll-rule.md`
before the implementation existed (P4).

### Why it was decidable with no data

ES rolls quarterly, so a "continuous ES series" is a **construction, not a
measurement**. It looked like it needed data. It did not: it is a question about
information order, and `UPTM-012` already committed to the answer — nothing is
ever revised, because a withdrawn swing is one a live system may already have
acted on.

### What was measured

Two contracts ten points apart, rolling at bar 5:

| join | rewrites history |
|---|---|
| `raw_splice` | no |
| `forward_adjusted` | no |
| `back_adjusted` | **yes** |
| `ratio_back_adjusted` | **yes** |

And the collision, as numbers rather than as argument. The peak at bar 2 is
**confirmed at bar 3**, two bars before the roll. Under an admissible join it is
priced 105 then and 105 after. Under back adjustment it is priced **105 when
confirmed and 115 afterwards** — repriced by a roll that had not happened when a
live system would have acted on it. The test runs this through
`runner.swing.detect` itself, so the collision is with the real swing code.

**The refused join is the one most vendors ship.** A "standard continuous ES
file" is the thing to decline, not the thing to buy — which changes what the
four open vendor questions in `DEC-UPTM-013` are asking for.

### Admissibility is measured, not declared

`runner.roll.rewrites_history` builds the series at two moments and compares the
overlap. A list of approved methods beside the enum would be correct until
somebody adds a method and forgets the list — and that failure is silent in the
dangerous direction, because the new method reads as safe.

One trap closed: a probe with **no roll with a price gap** classifies every join
as stable, so the measurement raises rather than returning a comfortable
`False`. §3 preregistered the roll-free case; a zero-seam roll has the identical
defect, so the condition was drawn at its natural boundary and the exception is
named `UninformativeProbe`. Recorded in the spec's §5.

### What was NOT decided

The trigger and its offset — calendar days before expiry, volume crossover,
open-interest crossover — stay `UNDEFINED`. So does the pick between raw splice
and forward adjustment: **both are admissible**, and choosing needs seam sizes
nobody can measure while the source sits at `MAPPED_UNVERIFIED`. The contract
carries `roll_parameters: UNDEFINED`, and `status.rules` has not moved.

Settling the family did not close the parameters, and a test asserts exactly
that, because the easy failure here would have been to let "the roll rule is
decided" read as "the roll rule is set".

### Process

`L1` named one case per independent mechanism **in advance** — the fix recorded
in `DEC-UPTM-013` taking effect rather than being promised. Both were built as
named.

**Artifact:** `runner/roll.py`, `tests/test_roll.py` (60 tests),
`research/data_sources/es_mes_bars.json`,
`research/candidates/reversal/bearish_quasimodo.json`, two `mutation-gate` cases
(25 total, `ok: true`), 725 tests passing. No market data, no network call, no
detector, no backtest. `LIVE_TRADING` stays `false`.

---

## [2026-09-28] DEC-UPTM-013 — ES/MES is written down, and written down is not obtained

**Decided:** Founder GO to put ES/MES market data into a sourcing map. Built as
`UPTM-013`, preregistered in `docs/specs/UPTM-013-es-mes-data-sourcing.md`
before the implementation existed (P4).

### Which map, and why not the Revolis one

`RealitkaAI/docs/architecture/master-data-sourcing-map.md` is titled *"Legálne
zdroje dát pre Revolis.AI"* and covers cadastre, RPO and property portals. This
repository's CLAUDE.md says *"Sem patrí výhradne UPTM Runner. Nepatrí sem
Revolis.AI / RealitkaAI."* Both boundaries point the same way, and the standing
instruction is that UPTM records go here. So a new map was written here:
`docs/architecture/uptm-data-sourcing-map.md`, in the Revolis map's own format
— **ZDROJ → LEGÁLNOSŤ → AKO ZÍSKAŤ → AK NEVIEM, AKO ZISTIŤ** — plus one rule the
Revolis map does not have: the state is machine-readable and enforced.

Whether the Revolis map should carry a one-line pointer here is a Founder
decision. Not taken.

### What could not be done, said before anything else

The environment's network policy **denied `databento.com` and
`www.cmegroup.com`**. No vendor terms, prices, history depth or licence
conditions were read from a primary source. What was readable was search-result
summaries from 2026-09-28.

So every candidate is `terms_verified: false` and carries the exact question and
the exact URL that settles it. A summary is recorded as a lead, never as a term.
A sourcing map recalled rather than read would be worse than no map, because it
would look like research — and Directive 4's "never guess a data source" is
aimed at precisely that.

### GDPR is not the gate here; the exchange licence is

Directive 5 requires the `gdpr-advisor` skill be run against the chosen source.
**That skill does not exist in either repository** (available: `kontrolor`,
`strategic-analysis`, `task-loop`). Recorded rather than silently skipped.

The analysis points elsewhere anyway. ES/MES OHLCV is a price at a time on an
exchange: no personal data, no identifiable person, so 6(1)(f) and a balancing
test are not what gates it. What gates it is CME market-data licensing, where
these are **not the same permission**: internal research and private backtesting,
non-display use, redistribution, **publication of a derived number**, and
professional versus non-professional status.

That last distinction is the one that will matter to Revolis later: a feature
that shows a user a number computed from this feed is a different licence
question from a private backtest, and "we have the data" answers neither.

### The state is enforced, not asserted

Five rungs: `NOT_IN_MAP` → `MAPPED_UNVERIFIED` → `VERIFIED_TERMS` → `LICENSED` →
`CONNECTED`. Below `CONNECTED`, `runner.data_sources.may_run_detector` returns
`False` — Directive 4's rule as code rather than as prose. `CONNECTED` costs
evidence: an artifact and a commit, for `DEC-UPTM-010`'s reason. A state anyone
can type is one that will eventually be typed optimistically, usually by someone
in a hurry who is not lying.

The Founder task list is **derived** from the candidates, not kept beside them,
so it cannot drift from what it describes.

### Found while looking: a second undefined term

**The roll rule.** ES rolls quarterly, so a "continuous ES series" is a
construction rather than a measurement — back-adjusted, ratio-adjusted and raw
give different prices before every roll, and therefore different swings from
`UPTM-012`. Recorded as `UNDEFINED` and deliberately **not** decided: it is the
same shape as `swing_parameters` and must not be settled as a side effect of
picking a vendor.

### What moved

The contract's `data_requirement` stops saying the source is unmapped, because
that stopped being true, and now names the record it is measured against. Its
status is still `OPEN_UNKNOWN`, `swing_parameters` is still `UNDEFINED`,
`status.rules` has not moved, and `may_run_detector` returns `False`. Four vendor
questions are open. **Written down is not obtained.**

A process fix is recorded in the spec's §5: three specs running have preregistered
"a mutation case" and built two, so from `UPTM-014` L1 preregisters one case per
independent mechanism and names them.

**Artifact:** `docs/architecture/uptm-data-sourcing-map.md`,
`research/data_sources/es_mes_bars.json`, `runner/data_sources.py`,
`tests/test_data_sources.py` (28 tests), two `mutation-gate` cases (23 total,
`ok: true`), 663 tests passing. No network call, no market data, no detector, no
backtest. `LIVE_TRADING` stays `false`.

---

## [2026-09-27] DEC-UPTM-012 — a swing is defined; when it may be known is the point

**Decided:** Founder GO on defining *swing*, the root `DEC-UPTM-011` exposed.
Built as `UPTM-012`, preregistered in `docs/specs/UPTM-012-swing-definition.md`
before the implementation existed (P4).

### The recommendation that was not taken, recorded

The recommendation was to read the ebook **first**, so `source` would leave
`RESTATED_SECONDHAND` before committing a definition that all seven formations
inherit. The Founder decided otherwise. This is built on that decision, and the
risk is written into the spec's §0 rather than argued again: if the primary
source defines *swing* differently, this is what changes, and seven formations
change with it.

The risk is contained deliberately — the **parameters are not chosen**, so what
a later reading could overturn is the shape of the rule, not numbers already
baked into a contract. The contract also now records, under
`our_interpretation_not_the_source`, that the definition is ours pending the
reading.

### The definition

A bar is a swing high when its high is strictly greater than the highs of the
`pivot_bars` bars on **each** side; a swing low is the mirror on lows. It is
accepted only if it moved at least `min_amplitude` from the last accepted swing
of the opposite kind, read absolutely or as a fraction.

Two choices were made rather than inherited:

- **A plateau yields no swing.** A tie is not an extreme, and picking one of two
  equal bars would be a rule a later reader could not reconstruct from the data.
- **Nothing is ever revised.** The usual ZigZag withdraws a swing when a later
  bar makes a better one. Rejected: a withdrawn swing is one a live system may
  already have acted on. Consecutive same-kind swings are both kept instead.

### The part that matters more than the definition

A swing high at bar `i` **is not knowable at bar `i`.** The bars to its right
have not happened. Every swing therefore carries `confirmed_at = i + pivot_bars`,
and the invariant is stated so it can fail:

> For every `t`, the swings whose `confirmed_at <= t` are **exactly** the swings
> detected from `bars[:t+1]`.

Filtering the full series by confirmation time and truncating the series before
detection must give the same answer. If any future information reaches the
detector, the two diverge. Asserted at every cut of a series, for `pivot_bars`
1–3, and again with the amplitude filter engaged.

The candidate already forbade "swing points confirmed by bars later than the
decision timestamp". This is where that stopped being a sentence — and
`swing-confirmation-lag-removed` in the mutation gate is what keeps it from
becoming one again.

### The parameters are not set, and that is not a contradiction

`pivot_bars` and `min_amplitude` require bar data to choose against, and ES/MES
data is `OPEN_UNKNOWN` under Directive 4. A number picked without data would be
a fabricated parameter wearing a definition's clothes.

`DEC-UPTM-003`'s precedent applies exactly: *"`ENFORCED` and unset are not in
tension: the machinery is enforced, and it is enforcing a denial."* So
`swing_definition` becomes defined and a new term `swing_parameters` becomes
`UNDEFINED`. The contract stays unevaluable for a different reason than before,
and the derivation in `pattern_contract.required_terms` raises that requirement
*only once the root is written* — so the finding always points at whichever gap
is actually in front of the reader.

### What moved, stated small

The Quasimodo contract went from **15 undefined terms to 11**. `status.rules`
did not move and cannot: `swing_parameters`, `entry_trigger`, `break_tolerance`,
`target_exit`, `timeframe`, `instrument_es_vs_mes`, `session_window`,
`slippage_model`, `fee_model`, `risk_sizing` and `invalidation_rules` are all
still `UNDEFINED`. The root is gone; the contract is no closer to tradeable, and
nothing here claims otherwise.

Three `UPTM-011` tests were amended because facts they asserted stopped being
true — not because a bar was lowered. Each amendment is named in the spec's §5
so the claim can be checked against the diff.

**Artifact:** `runner/swing.py`, `tests/test_swing.py` (31 tests),
`research/candidates/reversal/bearish_quasimodo.json`,
`runner/pattern_contract.py`, `tests/test_pattern_contract.py` (31 tests), two
`mutation-gate` cases (21 total, `ok: true`), 633 tests passing. No market data
was read, no formation detector was built, no backtest was run. `LIVE_TRADING`
stays `false`.

---

## [2026-09-27] DEC-UPTM-011 — one pattern contract, and the root all seven rest on

**Decided:** Founder GO on a Bearish Quasimodo prototype. Built as `UPTM-011`,
preregistered in `docs/specs/UPTM-011-bearish-quasimodo-contract.md` before the
implementation existed (P4).

### What was asked, and what was built instead

The proposal was a library of seven formalised reversal formations — Head &
Shoulders, Inverse H&S, Double Top, Double Bottom, Rising Wedge, Falling Wedge,
Quasimodo. **One was built.**

Every one of the seven is written in swing highs and swing lows: "three peaks",
"two tops", `HH → HL → HH → LL → LH`. None can be evaluated until *swing* is
mechanically defined — how many bars either side, what minimum amplitude, on
what timeframe. Seven contracts written over that gap would be one unsolved
problem written seven times, and each would carry the appearance of progress.

Bearish Quasimodo was chosen over H&S because it is stated as an explicit
sequence and reaches the root fastest; H&S adds a second undefined construction,
the *neckline*, on top of the same one.

### Provenance, recorded as what it is

The rules come from the Founder's restatement of the ebook in conversation. The
runner has not read the ebook. The contract records `primary_source_read: false`
and the `source` axis sits at `RESTATED_SECONDHAND`.

The one available inference was declined: the restatement gives the retest entry
for the *bullish* mirror only, so the bearish `entry_trigger` stays `UNDEFINED`
rather than being mirrored from it. The contract records that refusal under
`our_interpretation_not_the_source`, so a later reader can see the gap was
noticed rather than missed.

The source's worked examples — individual 3R, 5R and 6R outcomes, 2007/2009
cases — are filed as illustrations. Occurrence count, failure rate, expectancy,
out-of-sample and after-cost results: none of them exist, and the contract lists
each one as missing rather than leaving the reader to notice.

### One status word replaced by six axes

The existing Hafez candidate carries a flat `status: "UNVERIFIED"`. That single
word cannot express *the rules are pinned down and nothing is known about
whether it earns* — the state a research candidate spends almost all of its life
in, and the conflation that lets "verified" drift from meaning one thing to
meaning the other.

Six ordered axes, each with its own floor: `source`, `rules`, `implementation`,
`no_leakage`, `stats`, `performance`. An axis may rise above its floor only when
every earlier axis stands at its top. `performance` therefore cannot move while
`no_leakage` reads `NOT_TESTED` — which is the claim the ordering exists to
forbid: a return measured with information the strategy could not have had at
its decision timestamp.

**Derived, never typed.** The requirement that `swing_definition` be defined is
not a list of term names kept beside the data. The code reads the sequence out
of the contract, sees that it names swings, and requires the root term on that
basis — so it holds for a contract nobody has written yet, and disappears for a
structure that names no swing at all. A test proves exactly that, on a
triple-bottom contract invented inside the test with every one of its own terms
defined.

**Checked by tests, not by a JSON Schema.** `DEC-UPTM-010` is the reason: this
repository already carries a schema that did not parse for a day while every run
reported success. A second schema nothing loads would inherit the same failure
mode.

### What this does not establish

Not that Quasimodo works. Not that the rules are right. Not that it is
implementable — it is not, and the `rules` axis says so. ES/MES market data is
**not** in `docs/architecture/master-data-sourcing-map.md`; under Directive 4
that is an open unknown recorded as `OPEN_UNKNOWN`, not a detail to settle
during implementation. `LIVE_TRADING` stays `false`.

Defining *swing* is a separate decision with its own GO. It is a modelling
choice every one of the seven formations would inherit, and it must not be made
as a side effect of writing down one of them.

**Artifact:** `research/candidates/reversal/bearish_quasimodo.json`,
`runner/pattern_contract.py`, `tests/test_pattern_contract.py` (25 tests), two
`mutation-gate` cases (19 total, `ok: true`), 594 tests passing. The Hafez
candidate and its test are untouched, and a test asserts that.

---

## [2026-09-25] DEC-UPTM-MAP-Q5 — neither wave numbering is canonical

**Decided:** Founder GO MAP-Q5, accepting the recommendation not to pick a
numbering from this repository. Question 5 on `docs/architecture/governance-map.md`
stays **OPEN**. Waves 0–7 are not declared the other repository's names, and
this repository's wave files are not renumbered to 0–9.

**Why:** The map measured two vocabularies. Choosing 0–7 as canonical would
rename the trading system's waves without reading them. Choosing 0–9 would
rename this repository's `waves/wave0.yaml` through `waves/wave7.yaml`. Neither
rename is a decision the files already contain. `CONSTITUTION-CAPITAL.md` v1.0
stays LOCKED. No principle's enforcement state moves. `LIVE_TRADING` stays
false. No P12 invalidation follows.

**Artifact:** the question 5 block in `docs/architecture/governance-map.md`
carries `OPEN (DEC-UPTM-MAP-Q5)`. Mutation `map-q5-marked-decided` replaces
that marker with waves 0–7 as the canonical numbering. `test_map_q5_stays_open`
goes red. The wave files stay `wave0.yaml` through `wave7.yaml`.

---

## [2026-09-25] DEC-UPTM-MAP-Q3 — no relation between €700 and €750 is adopted

**Decided:** Founder GO MAP-Q3, accepting the recommendation not to invent the
relation. Question 3 on `docs/architecture/governance-map.md` stays **OPEN**.
€700 remains `validation_capital.amount`, the size of the validation test.
€750 remains the other repository's paper-account capital. Neither number is a
ceiling, a subset, or a limit on the other.

**Why:** The map measured that nothing stated how they relate. Choosing one
reading would be a new risk parameter, and an unset relation stays unknown.
`validation_capital.amount` stays 700 EUR. `CONSTITUTION-CAPITAL.md` v1.0 stays
LOCKED. No principle's enforcement state moves. `LIVE_TRADING` stays false. No
P12 invalidation follows.

**Artifact:** the question 3 block in `docs/architecture/governance-map.md`
carries `OPEN (DEC-UPTM-MAP-Q3)`. Mutation `map-q3-marked-decided` replaces
that marker with a chosen relation. `test_map_q3_stays_open` goes red.

---
## [2026-09-26] DEC-UPTM-010 — a schema the gate cannot read is a fault, not a pass

**Decided:** Founder GO on the swallowed `except Exception: pass` in
`runner/evidence.py`. Built as `UPTM-010`, preregistered in
`docs/specs/UPTM-010-schema-load-is-not-optional.md` before the implementation
existed (P4). Stacked on `UPTM-009` (#40), which repaired the schema file.

### What was open

One `except` covered two unrelated events: *the schema could not be loaded* and
*the evidence did not match it*. The first is an infrastructure fault, and it
read as a pass for a full day while `schemas/evidence.schema.json` did not
parse. A check that did not run was reporting success — the exact thing
"absence is not a measurement" forbids.

### What the measurement said, before anything was designed

The swallow was instrumented for one suite run, then the instrumentation was
removed:

```
183 exceptions swallowed, all jsonschema.ValidationError, none a load failure
```

The comment being replaced blamed adversarial packs violating severity enums.
That is a minority. Most are packs — `capital`, `kill_switch`, `market_data`,
`pnl` — that the schema has never been taught, tripping
`additionalProperties: false`.

**So the old conclusion was right and its stated reason was wrong.** Mismatch
stays soft because the schema is measurably behind the evidence, not mainly
because packs attack it. Turning mismatch hard would have promoted an
out-of-date schema into a gate, and the honest route to a green suite would
have been to teach the schema every pack it does not model — a far larger
change than the one asked for.

### What was built

A load failure — unparseable, absent, not a valid JSON Schema, `jsonschema` not
importable, or anything else that stops the check completing — returns one
named error, which `evaluate_gate` turns into a `fail-closed:` denial. A
mismatch returns nothing, exactly as before.

The fault is about the *check*, so it is reported once: evidence missing eleven
fields reports eleven field errors and one schema fault.

### The judgement call, recorded before it was made

A missing `jsonschema` now denies. `jsonschema>=4.20` is a declared runtime
dependency, not an extra, and an environment quietly skipping the check is the
defect being replaced. The argument against — it can deny for a reason that has
nothing to do with the evidence — is written into the spec's §4, before the
code, rather than discovered in a diff.

### Load-bearing

A `mutation-gate` case restores the blanket swallow and names four tests
required to go red. Measured: all four do.

### What this does NOT establish

- **Not that the schema is correct or complete.** The 183 mismatches say it is
  neither. This makes a *load* failure loud; the schema's content is untouched.
- **Not that evidence matching the schema is sound.** Mismatch stays soft by
  design, so the schema still gates nothing about evidence content.
- **Not that other swallows are gone.** One `except` in one function was
  changed. No survey of the rest was done, and none is claimed.

### Settled from UPTM-009

That spec left open whether the repaired schema accepts a real gate pack. It
does — `runner.enforcement._base()` validates against it, asserted by a test
rather than assumed.

### Unchanged

`LIVE_TRADING` stays `false`. No guard loosened, no enforcement status moved,
no capability granted. 35 routes, none reaching PASS, none denying for another
reason; `claims_checked` still P8, P10, P12.

## [2026-09-25] DEC-UPTM-MAP-Q2 — neither repository's PASS wins a disagreement

**Decided:** Founder GO MAP-Q2, accepting the recommendation not to pick a
winner from this repository. Question 2 on `docs/architecture/governance-map.md`
stays **OPEN**. On a disagreement, neither repository's `PASS` is the winner.

**Why:** Both repositories can emit `PASS`, and neither reads the other's.
Naming `uptm-runner` the winner would make this gate override a verdict it has
not seen. Naming `onlinovosk-bit-uptm` the winner would make that repository's
`PASS` override this one without a reader. `CONSTITUTION-CAPITAL.md` v1.0 stays
LOCKED. No principle's enforcement state moves. `LIVE_TRADING` stays false. No
P12 invalidation follows.

**Artifact:** the question 2 block in `docs/architecture/governance-map.md`
carries `OPEN (DEC-UPTM-MAP-Q2)`. Mutation `map-q2-marked-decided` replaces
that marker with a chosen winner. `test_map_q2_stays_open` goes red.

---

## [2026-09-25] DEC-UPTM-MAP-Q1 — the trading-wave question stays open

**Decided:** Founder GO MAP-Q1, accepting the recommendation not to answer it
from this repository. Question 1 on `docs/architecture/governance-map.md` stays
**OPEN**. Neither answer is adopted: a trading-system wave gate is not declared
to satisfy the capital constitution, and it is not declared exempt from it.

**Why:** The map measured that nothing connects the two repositories. Answering
"yes" would invent a W8 evidence artifact this repository does not have.
Answering "no" would exempt a trading wave from P8 and P10 without a Founder
amendment. `CONSTITUTION-CAPITAL.md` v1.0 stays LOCKED. No principle's
enforcement state moves. `LIVE_TRADING` stays false. No P12 invalidation
follows.

**Artifact:** the question 1 block in `docs/architecture/governance-map.md`
carries `OPEN (DEC-UPTM-MAP-Q1)`. Mutation `map-q1-marked-decided` replaces
that marker with an adopted answer. `test_map_q1_stays_open` goes red.

---

## [2026-09-25] DEC-UPTM-APS-010 — a wave that names no agents records from the gate

**Decided:** Founder GO APS-010. A wave whose yaml `ownership.agents` is an empty
list records `passed_waves` from a PASS gate with `CRITICAL=0` and `HIGH=0`.
It does not require a `SwarmDispatch`.

**Why:** Wave 0 is the baseline lock, and its yaml says `agents: []`. Waves 2,
4, 5, 6, and 7 make the same declaration. Inventing a claim ledger for a wave
that named nobody would be a new claim, not enforcement of one the wave already
made. A non-empty list, an unreadable declaration, a ledger whose `agent_id`s
differ from the list, and a failed collect still deny. Those are APS-007
through APS-009.

**Artifact:** `runner.fsm._wave_lists_agents` returns false for an empty list.
Mutation `empty-agents-require-dispatch` forces that return to true.
`test_empty_agent_list_still_records_without_dispatch` and
`test_terminating_fsm_reaches_exit_after_all_waves_pass` go red. `LIVE_TRADING`
stays false.

---
## [2026-09-25] DEC-UPTM-009 — CI reads every file before it runs any of them

**Decided:** Founder GO on the syntax gate, chosen over watching `main` after
the fact. Built as `UPTM-009`, preregistered in
`docs/specs/UPTM-009-ci-syntax-gate.md` before the implementation existed (P4).

### What was open

Four merge incidents landed on `main` on 2026-09-24. Two of them were not wrong
code — they were files that could not be read at all:

- `6b46cc2` left a tuple unterminated in `runner/enforcement.py`. 482 tests
  never collected, and CI named the collector rather than the file.
- `a32a5ee` kept a deleted CI step beside the step that replaced it. Both ran
  `runner.cli enforcement-evidence`; the first exited 2 on an argument that no
  longer existed, so the second never ran. `main` was red for 26 minutes.

Both shapes were reproduced against the commits themselves before the spec was
written, not recalled.

### What was built

One CI step, after install and before `pytest`, that parses every `.py`,
`.json` and workflow the repository owns, reports **all** the ones that cannot
be read, and exits 1.

It runs as `python -m runner.syntax_gate`, not as a `runner.cli` subcommand, and
imports nothing from the tree it validates. That is load-bearing, not
housekeeping: `runner.cli` imports `enforcement`, `gates` and `fsm`, so
`6b46cc2` would have reached a subcommand as an ImportError traceback before the
first file was read — the exact failure the gate replaces.

It also refuses one structural shape: two steps of one job running the same CLI
subcommand, which is `a32a5ee` exactly. No opt-out marker. A deliberate
duplicate may be right one day, and when it is, a human should decide it in a
diff rather than have the gate wave it through.

### Where it sits in the guard taxonomy, and why it is not in NON_PRINCIPLE_GUARDS

`DEC-UPTM-APS` established that a guard enforcing no principle still has to be
routed, because a guard nobody routes is a guard whose removal is silent.
APS-001 and EVIDENCE-STRUCTURE are in `NON_PRINCIPLE_GUARDS` for that reason.

This one is deliberately **not**. That registry routes guards through
`evaluate_gate` — guards that decide whether evidence passes. The syntax gate
decides nothing about evidence; it decides whether CI can run at all. Routing it
there would assert a relationship that does not exist, which is the same error
as a typed `ENFORCED`.

The rule is met the other way: a `mutation-gate` case breaks the parse on
purpose and requires three named tests to go red. Measured — all three do.

### A fifth incident, found by the gate on its first run

`schemas/evidence.schema.json` had not parsed since `c4c409d`, a merge that
concatenated both sides' `required` lists and defined `wave_context` twice.
Repaired here as the union of the two sides.

It survived unnoticed because `runner/evidence.py` wraps the schema load in
`except Exception: pass`. The decode error was swallowed, so schema validation
has been silently inert — a check reporting the absence of a check as the
absence of a problem.

**The swallow is not changed here.** Making the schema load-bearing is a
behaviour change and needs its own GO. It is reported rather than slipped in.

### What this does not establish

- Not that the code is correct. It parses. That is the whole claim.
- Not that the workflow is right — one duplication shape is ruled out, nothing
  more.
- Not that merges are safe. Two of the four incidents behind this gate produced
  valid Python and it would have caught neither. Read it as *"no unreadable
  file reaches pytest"*, never as *"no bad merge reaches main"*.
- Not that the repaired schema accepts real evidence. It is a valid JSON Schema
  again; whether it accepts a real gate pack is untested, and inert regardless
  until the swallow is addressed.

### Unchanged

`LIVE_TRADING` stays `false`. No guard loosened, no enforcement status moved, no
capability granted. `claims_checked` is still P8, P10, P12; 35 routes, none
reaching PASS, none denying for another reason.

## [2026-09-24] DEC-UPTM-008 — the gate verifies the binding it was always handed; P12 is ENFORCED

**Decided:** Founder GO, *"GO na gate spotrebuje staleness"*. Built as
`UPTM-008`, preregistered in `docs/specs/UPTM-008-gate-verifies-its-binding.md`
before any verification code existed (P4).

### What was open, measured before anything was designed

```python
evaluate_gate(_base()).verdict                       # PASS
#   files: [{"path": "runner/gates.py", "sha256": "aaaa…"}]
evaluate_gate(_base(files=[{"path": "no/such/file.py",
                           "sha256": "bbbb…"}])).verdict   # PASS
```

**The gate passed evidence declaring a file that does not exist, with a digest
never computed from anything.** `validate_evidence_structure` required the
`files` key to be present; nothing had ever compared its contents to the
repository. That is P12's violation clause, live on `main`.

It was also a finding about my own work: every UPTM-006 route carried
`"sha256": "a" * 64` from the day that wall was built. The routes proved what
they were built to prove; none noticed the fabrication beside the proof.

### The GO was read narrowly, on purpose

"The gate consumes staleness" reads most obviously as a new `dependencies` field
on gate evidence, mirroring the enforcement manifest. **That reading was
rejected**, and the spec says why before the code: the binding already existed
in the contract and every producer already emitted it, so no schema change and
no producer migration were needed. A `dependencies` field would also be *worse* —
digests of `runner/**.py` inside a tracked artifact go stale the moment any
runner file changes, and regenerating it dirties the tree, which
`enforcement-evidence` then refuses under Evidence Rule A.

Evidence should bind the data it is **about**, not the whole repository it was
produced in. Smaller than authorised, and it closes the hole that was open.

### P12 is ENFORCED, and the word is bounded

All of §G and §R passed, so C1 authorised the change. `capital-rules.json`
carries `enforced_since`, `earned_by` naming UPTM-008, and
`what_this_does_not_establish`:

> It means there is no route to `PASS` with a **false** binding. It does not
> mean the binding is **sufficient** — a producer declaring one irrelevant file
> and omitting ten that matter satisfies every route here. This wall makes the
> declaration true, not complete.

`enforced_principles()` is now `['P8', 'P10', 'P12']`, `unproven_claims()` is
empty, 32 routes, none reaching `PASS`, none denied for another reason.

### A mutation case, because a deleted guard reads like a passing one

`evidence-binding-unverified` was added to the mutation gate from
`DEC-UPTM-MUTGATE`: remove the call and four named tests must go red. They do.
Without it, deleting this check would have been silent — the failure that gate
exists to catch.

### Unchanged

`LIVE_TRADING` stays `false`. `CONSTITUTION-CAPITAL.md` v1.0 stays LOCKED. P8,
P10 and P9 keep their status. No capability granted — refusing evidence that
lies about where it came from narrows what may pass, never widens it.

**Artifacts:** `docs/specs/UPTM-008-gate-verifies-its-binding.md` ·
`runner/binding.py` · `runner/gates.py` · `runner/mutation_gate.py` ·
`constitution/capital-rules.json` · `tests/test_binding.py` · corrected
fixtures in `tests/conftest.py` and `runner/enforcement.py`. Measured: 452
passed, mutation-gate exit 0.

---

## [2026-09-24] DEC-UPTM-APS-COMPOSER — the remaining composer denials are routes

**Decided:** the fail-closed branches of `assemble_prompt`, and the missing
`wave_context` case, are routes on guard `APS-001`. They do not become a
principle and they do not enter `capital-rules.json`.

`PS-R1` through `PS-R3` stay green if those branches are deleted. The role,
dependency, identity, and silence checks lived only in unit tests.

`wave_context` was worse than unrouted. `validate_prompt_stack_binding`
substituted `{"wave_id": evidence.wave_id}` when the binding omitted the field.
A binding assembled as exactly that object, with `wave_context` then removed,
reached `PASS` on `main` at `5e492f5`. Measured before this change.

Criteria fixed before the new measurement:

- `PS-R4` denies with `prompt_stack wave_context is required`.
- `PS-R5` denies with `may not receive stack 06`.
- `PS-R6` denies with `unknown prompt stack`.
- `PS-R7` denies with `duplicate prompt stack`.
- `PS-R8` denies with `missing prior dependencies`.
- `PS-R9` denies with `unknown role`.
- `PS-R10` denies with `no prompt stacks`.
- Neutering `validate_prompt_stack_binding` opens each of them. None is added
  to `REDUNDANT_GUARDS`.
- `enforced_principles()` stays `P8` and `P10`.

**Measured:** each new route returns `FAIL` with one gate reason:

- `PS-R4` `fail-closed: prompt_stack wave_context is required`
- `PS-R5` `fail-closed: role 'executor' may not receive stack 06`
- `PS-R6` `fail-closed: unknown prompt stack 99`
- `PS-R7` `fail-closed: duplicate prompt stack 00`
- `PS-R8` `fail-closed: stack 06 missing prior dependencies ['00', '05']`
- `PS-R9` `fail-closed: unknown role 'auditor'`
- `PS-R10` `fail-closed: no prompt stacks requested`

The loader no longer repeats `fail-closed:`; the gate adds it once.
`enforced_principles()` stayed `['P8', 'P10']`. The registry is 27 routes.

**Artifacts:** `runner/prompt_stacks.py` (`require_binding_wave_context`) ·
`runner/enforcement.py` (`PS-R4`–`PS-R10`) ·
`schemas/evidence.schema.json` · `tests/test_enforcement_evidence.py`.
## [2026-09-24] DEC-UPTM-007 — evidence now knows when it stopped being current; P12 still does not move

**Decided:** Founder GO for STALE invalidation. Built as `UPTM-007`,
preregistered in `docs/specs/UPTM-007-stale-invalidation.md` before any code
existed (P4).

**What it does.** The enforcement evidence artifact carries a sha256 of every
file it depended on, and `staleness()` answers `CURRENT` / `STALE` / `UNKNOWN`
against the tree. Expiry says how old an artifact is; this says whether it still
describes the system. An artifact can sit well inside its seven days and
describe a gate that has since been rewritten.

**The dependency set is derived, never typed.** Walking `runner/**.py`,
`capital-rules.json`, `CONSTITUTION-CAPITAL.md` and `prompt-stacks/**`. A list
someone must remember to update is the same failure as a status word someone
types, and criterion A6 is the one that proves the difference: a new `runner`
module is picked up with no edit to the dependency logic. Over-inclusion is
deliberate — a needless file costs one regeneration, a missing file leaves
evidence green after the thing it describes changed, which is the P12 violation
itself.

`UNKNOWN` is not a soft `CURRENT`, and a deleted dependency is `UNKNOWN` rather
than `STALE`: absence is not a measurement.

**Also built: the determinism declaration.** P12's violation clause forbids
calling a result reproducible without declaring uncaptured inputs. The manifest
now names what is captured and what is not — the wall clock, the Python version
and packages, the runtime identity, anything broker-side.

### A correction I owed the Founder

I described STALE as *"the last half holding P12 at PARTIAL."* Reading P12's
text disproved that: it also demands the determinism declaration, which was
missing too. That correction is written into the spec's §0, before the code, not
discovered afterwards.

### P12 stays PARTIAL, and the reason is measured

`ENFORCED` means *no route to `PASS` while violating the principle* — routes
through `evaluate_gate`. The gate does not read dependency digests from the
evidence it is handed, because gate evidence does not carry them. So no P12
route can be demonstrated, P12 has none in the registry, and criterion **C1
fails**. Per C2 the status does not move and the spec records the failure rather
than being amended to match what was built.

Closing C1 means making `dependencies` a required field of gate evidence and
denying on anything but `CURRENT` — the shape APS-001 used for `prompt_stack`.
That is a contract change affecting every producer, and it is a separate wall
with its own GO.

### Unchanged

`LIVE_TRADING` stays `false`. `CONSTITUTION-CAPITAL.md` v1.0 stays LOCKED. P8
and P10 keep their status; `enforced_principles()` is still `['P8', 'P10']` and
`unproven_claims()` is empty.

**Artifacts:** `docs/specs/UPTM-007-stale-invalidation.md` ·
`runner/staleness.py` · `runner/enforcement.py` (manifest `dependencies`,
`determinism`) · `tests/test_staleness.py`. Measured: 371 passed; live artifact
`CURRENT` → `STALE` on a real edit to `runner/gates.py` and to the constitution,
`CURRENT` again on restore.

---

## [2026-09-24] DEC-UPTM-APS-R3 — stack-body digest drift is a route

**Decided:** a change to a stack's canonical body that leaves
`prompt-stacks/index.json` `body_sha256` stale is route `PS-R3` on the existing
guard `APS-001`. It is not a new principle, it is not `ENFORCED`, and it does
not enter `capital-rules.json`.

The unit test `test_stack_body_change_without_manifest_update_invalidates_evidence`
already rejected that drift. It is not the enforcement manifest. `PS-R1` and
`PS-R2` stay green if `enforce_declared_body_digest` is deleted, because neither
submits a drifted body. A check whose removal the route manifest does not see
is the omission `DEC-UPTM-APS` exists to close.

Criteria fixed before the measurement:

- `PS-R3` denies with `prompt stack 00 digest mismatch`.
- Evidence is assembled from the real stack, and only then is the body shown to
  the gate. Drifting during assembly would write the new digest into the
  binding and the route would pass.
- Neutering `validate_prompt_stack_binding` opens `PS-R3`. The `prompt_stack`
  key is present, so this is not the `PS-R1` double hold.
- Neutering only `enforce_declared_body_digest` does not open `PS-R3`. The
  binding still carries the pre-drift digest, and the field comparison denies
  with `stack_digests mismatch`. That backstop stays out of `REDUNDANT_GUARDS`:
  the route's own expect string is the declared-digest raise, so retargeting
  the string at the backstop fails `denied_by_its_own_check`.
- `enforced_principles()` stays `P8` and `P10`.

**Measured:** `PS-R3` returns `FAIL` with
`fail-closed: prompt stack 00 digest mismatch`. The loader message does not
repeat `fail-closed:`; the gate adds that prefix to every structural error.
With `enforce_declared_body_digest` removed, the same evidence still returns
`FAIL`, now with `fail-closed: prompt_stack stack_digests mismatch` and
`fail-closed: prompt_stack assembled_prompt_digest mismatch`.
`enforced_principles()` stayed `['P8', 'P10']`. The registry is 20 routes.

**Artifacts:** `runner/prompt_stacks.py` (`enforce_declared_body_digest`) ·
`runner/enforcement.py` (`PS-R3`, `route_guard`) ·
`tests/test_enforcement_evidence.py`.
## [2026-09-24] DEC-UPTM-EXPIRY — evidence lives seven days, because the drill does

**Decided:** `evidence_expiry_days: 7`.

**Why seven and not a round number.** It is `kill_switch_drill_cadence_days`.
Enforcement evidence must never outlive the drill it rests on; if it could, a
valid-looking artifact would be propped up by a drill that had already gone
stale. Tying the two to one rhythm removes that case without a separate rule
saying so, and a test now fails if the two numbers ever drift apart.

### Setting the number was not the whole job

`evidence_expiry()` returned the string `"7 days from generated_at"`. That reads
like an expiry and can be compared to nothing. Writing the Founder's number into
a field that no code could evaluate would have produced a P12 that looked
satisfied and checked nothing — the same defect as a status word nobody earned,
which is the defect this whole wall exists to catch.

So `expires_at` is now a timestamp computed from `generated_at`, and
`expiry_status()` answers **`VALID` / `EXPIRED` / `UNKNOWN`** for an artifact at
a given time. `UNKNOWN` is not a soft `VALID`: no expiry, an unparseable one, or
one without a timezone all mean the artifact has not been shown to be current,
and under `runner.verdict` that dominates `PASS` and denies.

The lifetime itself is still never defaulted. Missing, zero, negative, boolean,
string or fractional all yield `None` — the Founder sets it or there is none.

### P12 does not become ENFORCED, and this says so out loud

P12 is *Evidence Has Commit & Expiry*. Both halves of the name are now real: the
commit is read from the repository (Rule A), the expiry is a timestamp that can
be evaluated. But the principle's recorded mechanism also names **STALE
invalidation on dependency change**, and that is not implemented. Evidence can
sit well inside its seven days and describe code that has since moved.

**P12 stays `PARTIAL`.** A test asserts it, and `capital-rules.json` carries the
reason in `evidence_expiry.does_not_satisfy_p12` rather than leaving the next
reader to infer why a parameter was set and nothing changed. Closing that
remaining half is a separate wall and has not been preregistered.

### Unchanged

`LIVE_TRADING` stays `false`. `CONSTITUTION-CAPITAL.md` v1.0 stays LOCKED. P8
and P10 keep their status for the reasons UPTM-005 and UPTM-006 established. No
capability is granted; an expiry narrows what evidence can claim, it does not
widen what the Runner may do.

**Artifacts:** `constitution/capital-rules.json` (`evidence_expiry_days`,
`evidence_expiry`) · `runner/enforcement.py` (`evidence_expiry_days`,
`evidence_expiry`, `expiry_status`, manifest `expires_at` / `expiry_days`) ·
`tests/test_enforcement_evidence.py`. Measured: 348 passed; expiry VALID at
+6d, EXPIRED at +8d, UNKNOWN on absent, unparseable and naive values.

---

## [2026-09-24] DEC-UPTM-RULEA — Evidence Rule A applies here, in one half of two

**Decided:** question 4 of the governance map. Evidence Rule A
(`onlinovosk-bit/onlinovosk-bit-uptm`, `docs/EVIDENCE_RULE_A.md`) applies to
`uptm-runner` — **half of it.** Which half, and why the other half does not, is
written in `docs/evidence-rule-a.md` rather than left to be re-derived.

**Adopted.** The evaluated head is read from the repository, never asserted by
the caller. `enforcement-evidence` no longer takes `--commit`. It reads
`git rev-parse HEAD`, requires a clean working tree, records `null` with a
stated reason when no head can be established, and treats a supplied
`--expect-head` as a cross-check in which a disagreement is a dispute and
neither value wins. CI passes no commit at all, so it cannot tell the artifact
what it evidences.

**Not adopted, conditionally.** The ban on a field meaning "the commit that
contains me" needs a tracked artifact to be meaningful. `evidence/enforcement/`
is ignored and never lands, so the self-SHA regress has nowhere to start. The
exemption rests on that condition and a test fails on the day it stops holding.

### The defect was real and I had named it wrongly

The governance map, merged this morning, said the manifest "can attest to its
own freshness, the exact thing Rule A exists to forbid." That was too strong.
The manifest is never committed, so it cannot attest to its own containing
commit at all.

The hole was adjacent: the commit was **caller-asserted and unchecked**, so a
manifest could name a commit whose code the routes had never run against, and
nothing downstream could tell. That hole is now closed.

The overstatement is corrected **in place, with the original wording left
visible** in the map. A map that silently repairs itself is worth less than one
that shows where it was wrong — and this is the third claim of mine in two days
that measurement refuted, after the P10-R2 conditional guard and the PS-R1
prediction. The pattern is the same each time: plausible reasoning, stated
confidently, never run against the thing it described.

### Unchanged

No principle changes status — P8 and P10 are `ENFORCED` for the reasons UPTM-005
and UPTM-006 established, and neither depends on this. `evidence_expiry_days` is
still unset and P12 is still `PARTIAL`. The other four governance questions are
still open. `LIVE_TRADING` stays `false`; `CONSTITUTION-CAPITAL.md` v1.0 stays
LOCKED.

**Artifacts:** `runner/provenance.py` · `runner/enforcement.py` (`manifest`) ·
`runner/cli.py` · `.github/workflows/pytest.yml` · `docs/evidence-rule-a.md` ·
`tests/test_evidence_rule_a.py` · corrected `docs/architecture/governance-map.md`.
Measured: 343 passed; `enforcement-evidence` exits 1 on a dirty tree and on a
disputed head.

---

## [2026-09-24] DEC-UPTM-APS — APS-001 is a guard, not a principle; and every guard must be routed

**Decided:** the mandatory `prompt_stack` evidence binding (APS-001) is a
**guard**, not a constitutional principle. It appears nowhere in
`capital-rules.json`, it advances no principle's status, and removing it lets no
kill-switch or capital violation through. It protects evidence integrity, which
is a different job from the one P1–P14 describe.

That classification is deliberate and is the reason the second half of this entry
exists.

### Why a guard that enforces no principle still has to be routed

UPTM-006 makes `ENFORCED` an earned status by enumerating **routes**: concrete
evidence a caller could submit while violating a principle, each one required to
be denied by its own named check. The claim is *there is no route to PASS while
violating this*.

Because APS-001 enforces no principle, nothing in that scheme required a route
for it. So none was written. For the hour between the binding landing and this
decision, the enforcement evidence would have stayed green if the binding check
had been deleted — **a guard nobody routes is a guard whose removal is silent.**

Two routes now name it:

| route | evidence submitted | denied by |
|---|---|---|
| `PS-R1` | gate evidence with no `prompt_stack` binding at all | `prompt_stack` |
| `PS-R2` | a binding whose `assembled_prompt_digest` does not match the stacks it names | `assembled_prompt_digest mismatch` |

### The standing rule this establishes

**Every group of routes beyond the `ENFORCED` principles must be declared in
`NON_PRINCIPLE_GUARDS`, with a written reason for existing.** The coverage test
fails on any undeclared group.

The rule cuts both ways, which is the point. It stops the registry quietly
accumulating routes nobody decided to add, and it stops a guard being added to
the gate with no route naming it. Declaring `APS-001` there is an act of
classification the file now forces someone to perform, rather than a status word
someone typed.

### A prediction that was written four times and refuted by the run

Written alongside the routes: neutering `validate_prompt_stack_binding` alone
would open both. **Measured: false for PS-R1.** Dropping the key trips the
required-field list in `validate_evidence_structure` as well, and each mechanism
denies on its own:

```
PS-R1  structure: ['missing field: prompt_stack', 'prompt_stack binding required']
       binding  : ['prompt_stack binding required']
PS-R2  structure: ['prompt_stack assembled_prompt_digest mismatch']
       binding  : ['prompt_stack assembled_prompt_digest mismatch']
```

Kept in `REDUNDANT_GUARDS` with the measurement and the date, surfaced in the
manifest as `redundant_guard`, and asserted in both directions. The test was
corrected to what the gate does, rather than the measurement loosened to what the
test had guessed. This is the second entry of its kind after the P10-R2
correction, and both stay in the code: a wall whose purpose is that claims must
be checked does not get to drop its own failed claim out of the record.

### Built by two sessions, an hour apart

The binding was built in one session (#18) and routed in another (#19). Neither
was wrong; the gap between them was. This is the same structural problem recorded
in `DEC-UPTM-DUP` — parallel sessions working one backlog with no shared claim on
the work — showing up as an **omission** rather than a duplicate. `NON_PRINCIPLE_GUARDS`
is the narrow fix: it makes this particular omission fail a test instead of
passing quietly. It does not fix the general problem, which is still open.

### Unchanged

No principle's status changes. UPTM-006 still advances nothing — it makes
existing claims checkable, which is smaller than making them true.
`LIVE_TRADING` stays `false`. `CONSTITUTION-CAPITAL.md` v1.0 stays LOCKED. No
Founder parameter was consumed: `evidence_expiry_days` is still unset and P12 is
still `PARTIAL`.

**Artifacts:** `runner/enforcement.py` (`NON_PRINCIPLE_GUARDS`,
`REDUNDANT_GUARDS`, `PS-R1`, `PS-R2`) ·
`tests/test_enforcement_evidence.py` · PRs #18 and #19, both on `main` at
`30e18ed`. Measured there: 334 passed, 19 routes, `unproven_claims: []`,
`routes_reaching_pass: []`.

---

## [2026-09-23] DEC-UPTM-004 — the validation tranche is set; WALL 2 is open

```yaml
validation_capital:
  currency: EUR
  amount: 700
  applies_to:
    - aggregate_open_exposure
    - cumulative_realised_loss
```

Set by the Founder 2026-09-23, superseding `DEC-UPTM-004-PRE`, where these were
preregistered but deliberately unwritten. **Writing them is the act that opens
WALL 2**, and it is why they were held back until UPTM-003 and the enforcement
evidence were done — the order the Founder set.

- **`per_position_at_risk` is not a separate cap**, by decision. It is covered by
  the stricter aggregate-open-exposure limit, so a second number would say less
  than the first.
- **PnL may be reported; profit and loss may not be an acceptance criterion.**
  €700 is the size of the test, not of the opportunity. A result that passes
  because it made money has measured the wrong thing. `VC-R1` and `VC-R2`
  enforce this, and UPTM-006 routes `P10-R5` and `P10-R9` prove they do.

**What setting it changed, measured rather than assumed:**

- Five new enforcement routes became possible (`P10-R4`, `R6`–`R9`). Until there
  was a ceiling there was nothing to step over: `VC-P1` denied every capital
  gate on the unset tranche before any other check was reached.
- `P10-R5` was unblocked. It had been recorded as unable to demonstrate its own
  guard for exactly that reason.
- It exposed a defect in UPTM-006's own capital fixture, which had invented pack
  field names the detector does not read. Nothing had ever got far enough to
  read them.

**And it refuted a prediction this project had written down four times.** The
claim was that `P10-R2` is guarded twice only because the tranche is unset, and
that setting it would leave one guard. Measured after: false — that route's
second guard is `VC-P2`, which is structural. Recorded in
`runner/enforcement.py` as `CORRECTED_PREDICTIONS`, under test.

**Artifacts:** `constitution/capital-rules.json` · `runner/enforcement.py` ·
`docs/specs/UPTM-006-enforcement-evidence.md`.

---

## [2026-09-23] DEC-UPTM-W8 — W8 specification accepted with two amendments; implementation still refused

**Decided:** accept the W8 specification review
(`onlinovosk-bit-uptm/docs/W8_SPECIFICATION_REVIEW.md`, PR #27 in that
repository) with two additions, and **do not implement W8 even so**.

**Amendment 1 — P2, Same Validated Path.** The specification asked for *"a single
deterministic end-to-end integration path"* without requiring it to be the path a
real run would take. An integration harness is by construction a mechanism for
producing a second code path. Now required: the same entrypoints as the paper
path, an enumerated list of every deliberate divergence with what each could
hide, and a test showing an unlisted divergence being caught.

**Amendment 2 — P13, No Model in Pre-Trade Path.** The specification restricted
*which strategy* may be promoted, not *what kind of thing* may sit between a
decision and its execution. Now required: no non-deterministic model in that
path, the pre-trade call chain recorded in the evidence, and determinism
demonstrated by a byte-identical repeat run rather than asserted.

Both principles are `MISSING` — enforced nowhere in either repository — which is
why they had to be written into the contract rather than assumed.

**Implementation refused, and the reason sharpened.** Not "a good stopping
point". P2 is unenforced, so an integration harness built now would produce a
result that does not describe the path a real run takes — and the Safety
Envelope cannot protect against that, because such a run costs the same money
and answers a different question. The cheaper order is P2 first.

**Two things measured while reviewing it, both worth keeping:**

- The specification is good, and in one respect better than this repository's
  own work. Evidence Rule A forbids an artifact from carrying any field meaning
  "the commit that contains me"; the UPTM-006 manifest here takes its commit as
  a CLI argument and can therefore attest to its own freshness. That is a real
  defect in UPTM-006, found by reading the other repository's rules.
- **"W7 PASS" does not mean the W7 wave passed.** `W7-H1` and `W7-H2` are two
  defensive tests. The artifact carrying them records `gate_status: UNKNOWN`,
  scopes itself to waves W1 and W4, and says in its own field: *"Do not start W8
  or W9 from this defensive re-verification evidence."* The trading repository's
  README agrees — *"Wave 7: Red Team expansion is not started."*

**Artifacts:** `onlinovosk-bit-uptm/docs/W8_SPECIFICATION_REVIEW.md` §Amendments
on acceptance · `docs/architecture/governance-map.md`.

---

## [2026-09-23] DEC-UPTM-MAP — the two repositories are mapped; five questions are left open

**Decided:** write down which constitution governs which system, because nothing
did.

Measured: the W8 specification mentions P1–P14, `validation_capital` and the kill
switch exactly **zero** times, and `onlinovosk-bit-uptm` has no `constitution/`
directory. Two sets of rules, two sets of `PASS` verdicts, no reference in either
direction.

**The gap in one sentence:** the constitution is enforced against evidence
documents, and nothing requires the trading system to produce one.

**Recorded in `docs/architecture/governance-map.md`:** what each repository
holds, where authority actually sits, and the name collisions — `W7` meaning two
different waves, "evidence" meaning two different contracts, and €700 (the
validation tranche here) versus €750 (the paper account's capital there) being
different numbers that nothing relates.

**Five questions the map deliberately does not answer**, because they are Founder
decisions: whether a trading-system wave gate must satisfy the capital
constitution; which repository's verdict wins on disagreement; how €700 and €750
relate; whether Evidence Rule A applies here; and which wave vocabulary is
canonical.

**Not an amendment.** `CONSTITUTION-CAPITAL.md` v1.0 stays LOCKED and unchanged;
no P12 invalidation follows.

**Artifact:** `docs/architecture/governance-map.md`.

---

## [2026-09-23] DEC-UPTM-005 — the scope declaration, and what it unlocked

**Decided:** the evidence scope declaration is mandatory, and **its absence
resolves to `UNKNOWN`, not to "not applicable"** (Founder, 2026-09-23).

That single choice is what moved **P8 and P10 to `ENFORCED`**. Both had been
held at `PARTIAL` for one stated reason: evidence that simply omitted the
`kill_switch` pack, or never set `capital_gate`, was never examined. A principle
a caller can step around by leaving a key out is not enforced, whatever the
detector does when the key is present. Making the declaration unconditional
closes that.

**Enforcement summary:** `ENFORCED 2 / PARTIAL 7 / DECLARATIVE 1 / MISSING 4`.
The first two `ENFORCED` entries this system has had.

**Breaking, deliberately:** evidence written before this wall carries no scope
and denies until declared. `runner.fsm.run_baseline_ack` now emits the
declaration, so wave 0 is declared at the producer rather than patched
afterwards.

**The limit that remains** is recorded and is the right one: the wall makes the
declaration mandatory and self-consistent, and cannot tell whether it is *true*.
A gate declaring `live_bearing: false` while actually bearing LIVE has not
avoided the check — it has lied in signed evidence.

**Artifacts:** `docs/specs/UPTM-005-evidence-scope-declaration.md` ·
`runner/detectors/scope.py` · `runner/gates.py` · `runner/fsm.py` · PR #10.

---

## [2026-09-23] DEC-UPTM-DUP — UPTM-003 was built twice, in parallel

**What happened.** Two sessions implemented WALL 1 at the same time, neither
aware of the other. One landed via PR #8 (merged to `main`, `97acd62`); the other
became PR #9, which sat green and mergeable for a day and was then in conflict
against a `main` that had grown its own kill-switch detector — and a
validation-capital detector besides.

**Decided:** `main`'s implementation stands. PR #9 **closed unmerged**. Two
detectors for one principle do not merge, and resolving the conflict would have
produced exactly that.

**Ported from the closed branch, on instruction, because both were in the
original brief for this wall and `main` lacked them** (PR #12):

- **KS-D5** — a drill is invalidated by a change to `deployment_ref`,
  `credentials_ref` or `gate_path_digest`, independently of the cadence window.
  `main`'s KS-D4 covered only the stop path.
- **KS-D6** — deployment independence as a **dated operator attestation**,
  checked for existence and currency, never for truth. `main` declared this as a
  limit but did not check it.

Nothing else was ported: the machine-readable spec JSON, the
preregistration-integrity tests, the omission-bypass closure under a LIVE
capability claim, and the malformed-shape hardening stay in the closed branch.

**Two things `main` does better**, recorded so the closure is not read as a
verdict on quality:

- `can_write` probes writability **in fact**, rather than trusting a declared
  `runner_write_paths` list.
- `gate_bypass_attempt` was left `DECLARATIVE`. The closed branch promoted it to
  `PARTIAL` on the strength of a single detection path; that promotion did not
  survive, and should not have been made.

**The cost, stated plainly.** This is the second time the same failure has been
recorded on this stack — `RealitkaAI/memory/decisions.md` carries
*"Bus was designed twice"* from 2026-09-21. Two sessions working the same
backlog without a shared claim on the work produce two implementations and one
of them is thrown away. That is the finding, not the detector.

**Artifacts:** PR #8 (merged) · PR #9 (closed) · PR #12 (ported checks).

---

## [2026-09-23] DEC-UPTM-003 — P8 Independent Kill Switch: cadence and ceiling

**Parameter in force:**

```yaml
live_capability:
  kill_switch_drill_cadence_days: 7
```

Set by the Founder 2026-09-23. **This supersedes the 14 given on 2026-09-22**,
against which the closed PR #9 was built. Both values were Founder-attributed;
the later one governs. Recorded because two dated parameters for one safety
control is exactly the thing that becomes unreconstructable in a month.

**Re-verification beyond the window.** A drill is required again immediately —
however recent the last one — after a change to the stop path (KS-D4) or to
`deployment_ref`, `credentials_ref` or `gate_path_digest` (KS-D5, PR #12). A
drill against a deployment that no longer exists proves nothing about the one
that does.

**The boundary the Founder drew:** *deployment independence is not to be
certified by code.* Whether the kill switch runs outside the Runner's process,
credentials and failure domain stays an **explicit operator attestation carrying
a date**. KS-D6 checks that one exists, is dated, is not dated in the future,
and is not older than the deployment it describes. It cannot check that it is
true, and no test in this repository claims otherwise.

**Status:** `DECLARATIVE → PARTIAL` with PR #8, then **`PARTIAL → ENFORCED`**
with UPTM-005 (PR #10, see `DEC-UPTM-005`). The ceiling recorded on 2026-09-22 —
that `PARTIAL` was as far as this could go — held only for as long as the
omission bypass did. Closing the hole, rather than adding checks, is what
enforced the principle.

Neither KS-D5 nor KS-D6 moved that status. They narrow what a valid drill and a
current attestation mean; P8 is enforced for a different reason entirely.

**Artifacts:** `docs/specs/UPTM-003-kill-switch-independence.md` ·
`runner/detectors/kill_switch.py` · `runner/gates.py` ·
`constitution/capital-rules.json`.

---

## [2026-09-22] DEC-UPTM-004-PRE — Validation capital parameters, preregistered and still unset

```yaml
validation_capital:
  currency: EUR
  amount: 700
  applies_to:
    - aggregate_open_exposure
    - cumulative_realised_loss
```

- **`per_position_at_risk` is not a separate €700 cap.** It is implicitly covered
  by the stricter aggregate-open-exposure limit.
- **PnL may be reported. Profit and loss may not be used as an acceptance
  criterion** of the validation experiment. €700 is the size of the test, not the
  size of the opportunity; a result that passes because it made money has
  measured the wrong thing.

**State of the repository:** the UPTM-004 **detectors exist** on `main` (PR #8,
`1227ded`), are invoked by the gate, and P10 is now `ENFORCED` (UPTM-005). The
**parameters above are still not set** — `validation_capital.amount`,
`.currency` and `.applies_to` are `null`/`[]`, VC-P1 returns `UNKNOWN`, and every
capital gate denies until the Founder sets them.

`ENFORCED` and *unset* are not in tension: the machinery is enforced, and it is
enforcing a denial. That is the correct reading of a capability that has not been
granted.

That is the correct state. `capital-rules.json` records why: the constitution
names €700 in P10's *heading*, and a heading is prose. The value that gates money
is set deliberately, not parsed out of a title.

**Ordering, as decided:** UPTM-003 → full ENFORCEMENT evidence → *then*
UPTM-004. Writing these parameters into `capital-rules.json` is the act that
starts WALL 2, so it has not been done. The detectors landing early does not
advance that order; it only means the code is waiting.

**Artifact:** detectors on `main`, P10 `ENFORCED`. Parameters: none — this half
is still a plan, and says so.

---

## [2026-09-22] DEC-UPTM-LOG — UPTM decisions are recorded in this repository

**Decided:** UPTM decisions go in `uptm-runner`, not in `RealitkaAI/memory/`.

Existing UPTM references in RealitkaAI (`memory/decisions.md`,
`memory/session-summary.md`, `docs/prompts/multi-agent-protocol-v0/`,
`docs/architecture/2026-09-21-uptm-path-to-micro-live.md`) are historical record
and were left untouched. Moving or deleting them is a separate decision.

**Artifact:** this file.
