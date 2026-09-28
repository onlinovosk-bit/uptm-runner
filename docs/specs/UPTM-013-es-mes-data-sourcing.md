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

*(filled in after implementation)*

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
