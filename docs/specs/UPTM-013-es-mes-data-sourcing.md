# UPTM-013 — ES/MES into a sourcing map, and the state that cannot lie

**Status:** preregistered 2026-09-28, before the implementation exists.
**Scope:** one data source recorded, and the machinery that stops an unconnected
source reading as a connected one. No network call, no market data, no detector,
no backtest. `LIVE_TRADING` stays `false`.

---

## §0 What was asked, and where it goes

`UPTM-011` recorded that ES/MES market data is not in
`RealitkaAI/docs/architecture/master-data-sourcing-map.md` — an open unknown
under Directive 4. The Founder gave GO to put it in a sourcing map.

**It goes in a new map in this repository, not in the Revolis one.** Both
CLAUDE.md files draw the same boundary from opposite sides: the Revolis map is
titled *"Legálne zdroje dát pre Revolis.AI"*, and this repository's own rule is
*"Sem patrí výhradne UPTM Runner. Nepatrí sem Revolis.AI / RealitkaAI."* Putting
a CME futures feed into a map of Slovak cadastre and property portals would put
a UPTM record in RealitkaAI, which the standing instruction forbids.

Whether the Revolis map should carry a one-line pointer to this one is a Founder
decision, not taken here.

---

## §1 The constraint this was built under, recorded first

This environment's network policy **denied `databento.com` and
`www.cmegroup.com`** on 2026-09-28. Vendor terms, prices and history depth could
not be read from their primary sources.

Directive 4 says never guess a data source. So the map names candidates and, for
every vendor-specific claim, records the exact question and the exact URL that
settles it — and marks the claim unverified until someone reads that page. A
sourcing map whose entries are recalled rather than read is the fabrication the
Directive exists to prevent, and it would be worse than no map, because it would
look like research.

This is the Revolis map's own convention: it already carries
`⚠️ NEOVERENÉ` entries with `AKO ZISTIŤ` steps. Nothing new is being invented.

---

## §2 Why the licence regime, not GDPR, is the binding constraint

Directive 5 requires the `gdpr-advisor` skill be run against the chosen source.
**That skill does not exist in either repository** — the available skills are
`kontrolor`, `strategic-analysis` and `task-loop`. Recorded rather than silently
skipped; running it is not possible, and claiming it ran would be worse.

The analysis it would cover is short and points elsewhere. ES/MES OHLCV is a
record of a price at a time on an exchange. It contains **no personal data** and
no natural person is identifiable from it, so GDPR is not the gate here.

What *is* the gate is exchange market-data licensing. ES and MES are CME Group
products; their data is licensed by the exchange, and a vendor supplying it is a
licensed distributor operating under that licence. Internal research use,
redistribution, derived-data publication, non-display use and professional
versus non-professional subscriber status are separate permissions. **A future
feature that publishes a number computed from this data is a different question
from one that backtests against it privately**, and the map has to keep the two
apart rather than record "we have the data".

---

## §3 The state ladder

One word cannot distinguish "we found four vendors" from "data is flowing". The
same conflation `UPTM-011` removed from pattern status is removed here:

| rung | means |
|---|---|
| `NOT_IN_MAP` | the state UPTM-011 hit: nobody has written the source down |
| `MAPPED_UNVERIFIED` | candidates named, terms recalled or summarised, not read |
| `VERIFIED_TERMS` | terms read from the vendor's own page, still no contract |
| `LICENSED` | a contract or subscription exists |
| `CONNECTED` | data actually reaches this runner, with evidence |

**No detector may run on bars, and no parameter may be chosen, below
`CONNECTED`.** `CONNECTED` requires evidence naming an artifact and a commit,
because a state anyone can type is a state that will eventually be typed
optimistically.

---

## §4 Preregistered criteria

| # | Criterion |
|---|---|
| **D1** | A source record is machine-readable and carries a `connection_state` from the fixed ladder. An invented state is an error naming the rung and the ladder. |
| **D2** | `CONNECTED` requires `evidence` naming both an artifact and a commit. Absent or empty evidence is an error, not a pass — `UPTM-010`'s shape. |
| **D3** | Detector use is refused at every rung below `CONNECTED`, asserted for **every** rung rather than one example. |
| **D4** | **Derived, not typed:** the open Founder tasks are computed from the candidates whose terms are unverified. Add a candidate and its task appears; mark it verified and the task disappears. Must hold for a source record this spec has never seen. |
| **D5** | Every candidate carries a `verification` block with a question and a URL. A candidate claiming `terms_verified: true` must name how it was verified; claiming it with no method is an error. |
| **D6** | The record points at the map document, and the pointer is checked against the filesystem rather than assumed. |
| **D7** | **Consistency, both ways.** The source is below `CONNECTED` **if and only if** `bearish_quasimodo.json` records `data_requirement.status: OPEN_UNKNOWN` and `status.implementation: NOT_STARTED`. A biconditional, so connecting the source later fails the test instead of leaving stale prose behind. |
| **D8** | The record carries the egress denial: which hosts, on what date, and that vendor terms are therefore unread from this environment. |

### Load-bearing

| # | Criterion |
|---|---|
| **L1** | A `mutation-gate` case breaks the refusal to run below `CONNECTED` and requires the named tests to go red. |
| **L2** | No network call is made by any test, no market data is read, no detector or backtest is built. |

---

## §5 Result

Built on 2026-09-28. No test opens a socket; nothing reads market data.

| artifact | what it is |
|---|---|
| `docs/architecture/uptm-data-sourcing-map.md` | the map, in this repository's sibling format |
| `research/data_sources/es_mes_bars.json` | the machine-readable record |
| `runner/data_sources.py` | the ladder, the evidence rule, the refusal |
| `tests/test_data_sources.py` | 28 tests, each naming its criterion |
| `research/candidates/reversal/bearish_quasimodo.json` | `data_requirement` wired to the record |
| `runner/mutation_gate.py` | two cases |

### Criteria, discharged

| # | how |
|---|---|
| D1 | `test_d1_*` — the record sits on `MAPPED_UNVERIFIED` with no errors; an invented state and a missing state are each named and rejected. |
| D2 | `test_d2_*` — `CONNECTED` with no evidence yields two errors; each half alone yields one; whitespace does not count as evidence; and the gate is shown to be **passable**, because a gate nothing can pass is a wall. |
| D3 | `test_d3_*` — parametrised over **every** rung below `CONNECTED`; plus the real record today, plus a malformed record that claims `CONNECTED` and is still refused. |
| D4 | `test_d4_*` — the task list is read out of the candidates; on a record this spec has never seen, only the unverified candidate yields a task; adding a candidate adds its task and verifying it removes it. |
| D5 | `test_d5_*` — every candidate carries a question and an `https://` URL and claims `terms_verified: false`; claiming verification with no method is an error, and supplying the method clears it. |
| D6 | `test_d6_*` — the map pointer is checked against the filesystem, a dangling pointer is reported, and **every** record in `research/data_sources/` is validated, not only this one. |
| D7 | `test_d7_*` — the biconditional: `OPEN_UNKNOWN` holds exactly while the source is not connected. |
| D8 | `test_d8_*` — the denial, its two hosts and its date; the licence regime as the binding constraint; Directive 5's missing skill; and the roll rule as an open modelling choice. |
| L1 | `unconnected-source-may-produce-numbers` (4 sentinels). |
| L2 | No network call in any test; no detector, no backtest, no market data. |

### What was found that was not asked for

**The roll rule is a second undefined term.** ES rolls quarterly, so a
"continuous ES series" is a construction, not a measurement: back-adjusted,
ratio-adjusted and raw give different prices before every roll, and therefore
different swings from UPTM-012. It is recorded in the map as `UNDEFINED` and
explicitly **not** decided — it is the same shape as `swing_parameters`, and it
must not be settled as a side effect of picking a vendor.

### Preregistered as one thing, built as another — and the process fix

**L1 named one case; two were built**, for the third specification running. The
second (`connected-no-longer-costs-evidence`) guards a mechanism independent of
the first: the refusal still holds when the evidence rule is gone, so one
mutation cannot cover both.

Three specs in a row have ended with this same note, which means the fault is in
how L1 is written, not in the building. **From UPTM-014, L1 preregisters one
case per independent mechanism and names them**, rather than saying "a case" and
reconciling afterwards. Guarding the code beats a tidy record, so the cases were
added; the preregistration is what changes.

**One UPTM-011 test was amended.** `test_c8_market_data_is_recorded_as_an_open_unknown`
asserted the finding names `master-data-sourcing-map.md`, which was true when the
Revolis map was the only map. It now checks that whichever sourcing map the
finding names is a file that exists — what the criterion was reaching for, and
stronger than the substring it settled for.

### What was measured

- `python -m runner.syntax_gate` — every file parses.
- `python -m pytest` — 663 passed, 0 failed.
- `python -m runner.cli mutation-gate` — 23 cases, `ok: true`, no missing sentinel.

### Still open, by design

Four vendor questions, each with its URL, derived from the record rather than
listed. `swing_parameters` remains `UNDEFINED`, `status.rules` remains
`UNDEFINED`, and `may_run_detector` returns `False`.

---

## §6 What this does NOT establish

- **Not that any vendor is suitable, affordable or licensed for our use.** No
  vendor page was reachable. Every vendor claim is `terms_verified: false` with
  the question that settles it.
- **Not that ES/MES data is available to this project.** The state is
  `MAPPED_UNVERIFIED`. Written down is not obtained.
- **Not that `swing_parameters` can now be chosen.** It cannot: choosing them
  needs data, and no data is connected.
- **Not a GDPR clearance.** GDPR is argued in §2 to be the wrong gate for this
  source; that is an argument, not an approval, and the named skill does not exist.
