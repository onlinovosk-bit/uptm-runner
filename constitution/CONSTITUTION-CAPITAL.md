# UPTM CAPITAL CAPABILITY CONSTITUTION v1.0

| | |
|---|---|
| Version | **1.0** |
| Status | **LOCKED** |
| Jurisdiction | Capital Capability (CC) — see `constitution/GOVERNANCE.md` |
| Amended by | Founder only (P14) |
| Machine rules | `constitution/capital-rules.json` |

This document is an **evidence dependency**. A change to its version invalidates every
PASS issued under it (P12).

## How this constitution is read

Every principle must be violable by a concrete act. If you cannot write the sentence
"an agent violates this by doing X", it is not a principle — it is a value, and it does
not belong in this list. Each principle therefore states what its violation looks like.

There is no length limit. There is a content limit: **the minimal complete set of
immutable principles, readable as one control artifact without depending on any other
document.**

---

## NON-GOAL

UPTM is not designed to generate meaningful income from €700. Its primary purpose is to
demonstrate that an autonomous trading system can decide and execute safely, auditably
and robustly under real execution constraints.

## SUCCESS CONDITION

Not "returned X %", but: **there is sufficient independent evidence that the system is
robust against known failure modes and may be granted a limited execution capability.**

## OPTIMISATION HIERARCHY

Survival → Safety → Robustness → Capital preservation → Risk-adjusted performance →
Profitability → Scale. A lower level is never traded for a higher one.

---

## P1 — Reality over Architecture

We do not bend reality to fit the architecture. We change the architecture to fit
reality.

*Violation:* a broker does not guarantee a property the contract assumes, and instead of
changing the contract we model the property or assume it.

## P2 — Same Validated Path

Any evidence used to authorise a higher capability must come from the same relevant data,
decision, risk and execution semantics that the target capability will use. Backtest,
Simulation, Paper, Shadow and LIVE share the execution contract, the pre-trade
enforcement path and the data pipeline — not an imitation of them.

*Violation:* a backtest runs on vendor A data and risk engine V1, live runs on vendor B
and V2, and the backtest result is used as evidence for live.

## P3 — Data Before Evidence

No validation evidence is valid without demonstrated integrity of the data it came from.
A backtest must be able to answer: **what exactly did the system know at time T?**

*Violation:* a backtest is marked validated although the data layer has not passed a data
gate, or the state of knowledge at time T cannot be reconstructed.

## P4 — Preregistered Gates

A gate's criteria and its verifier exist before evidence for that gate is collected.
Criteria are written immediately before their gate, not all in advance. Changing criteria
after collection has started is an exception with a recorded reason, not routine.

*Violation:* a criterion is added or softened after the measurement result is known.

## P5 — Independence of Verification

The verifier must not receive the producer's interpretation of the evidence, its
conclusion, or its argument. The preferred verifier is a deterministic test or a
reproducible computation. If an agent is required, it receives only the preregistered
criteria and the raw evidence. `INSUFFICIENT_EVIDENCE` is a normal, valid result.

*Violation:* a gate closes on a document titled PASS rather than on verification of the
evidence itself; or the verifier is handed the producer's summary instead of raw data.

## P6 — No Self-Expansion

The Runner must not, directly or indirectly, increase its approved risk capability,
change safety limits, or modify, reinterpret or replace the inputs, definitions,
classifications or valuation rules from which those limits are derived.

*Violation:* the limit does not move, but instrument volatility is recomputed by another
method so that the same limit permits a larger position.

## P7 — LIVE as Leased Capability

LIVE is a time-boxed, explicitly granted capability. On expiry it returns automatically
to DENY. Silence is not renewal. LIVE additionally requires the dual-control conditions
of `GOVERNANCE.md` §5.

*Violation:* `LIVE_ENABLED = true` with no expiry, or automatic renewal without Founder
action.

## P8 — Independent Kill Switch

The Runner cannot disable, bypass or modify the mechanism that stops it. An untested kill
switch does not exist — a periodic drill is a condition of LIVE validity.

*Violation:* the kill switch lives inside the Runner process, or LIVE runs without a
drill performed at the required cadence.

## P9 — No Progress Illusion

The system is assessed by capability readiness, not by percentage complete. "90 % built
and 0 % LIVE-ready" is a legitimate and expected state. Declarative is never PASS.

*Violation:* reporting of the form "we are at step 11 of 18, so 61 % done"; or a
principle counted as satisfied because it is written down.

## P10 — €700 as Validation Capital

€700 is capital for validating safety and robustness, not an income engine. Return is not
a criterion of any gate.

*Violation:* a gate is judged by realised profit instead of by its preregistered
robustness criteria.

## P11 — Uncertainty Halts

If the system cannot safely determine state, it must not guess, interpolate or continue.
It enters a safe stop and requests a human decision. This applies to orders, data,
positions, accounts, execution, configuration and evidence alike.

*Violation:* an order is resent after a lost connection without reconciliation; or a
missing value is interpolated and processing continues.

## P12 — Evidence Has Commit & Expiry

Every PASS is bound to a precisely identified state: code commit, data snapshot, config,
strategy version, risk policy version, execution contract version, model and its version
(if one was used), random seed, dependency lock, runtime/container identity, timestamp.
The evidence manifest must state explicitly **what is and is not deterministic**,
including what could not be captured (wall clock, network timing, broker-side state).
A change to a relevant dependency automatically invalidates the affected PASS → `STALE`.

*Violation:* a capability stays green after a change to the code or data its evidence
came from; or a result is called reproducible without declaring uncaptured inputs.

## P13 — No Model in Pre-Trade Path

There is no language-model call between order intent and order submission — not even an
advisory one. The pre-trade decision path (risk engine, portfolio guard, execution
policy) is deterministic code with tests. A model may analyse before a trade, evaluate
after one, propose hypotheses and generate candidate strategies.

*Violation:* a model returns a recommendation that a deterministic check merely confirms
— the model is thereby part of the final decision chain.

## P14 — Constitution is Versioned, Amended Only by Founder

Both constitutions carry a version. Only the Founder changes them, explicitly, with a
recorded reason. A constitutional change is a dependency change under P12 and invalidates
affected PASS results to `STALE`. An agent must not "interpret" a principle or "apply its
spirit". If a principle is in the way, the only legal path is to request an amendment and
**stop**.

*Violation:* an agent reads a principle more loosely instead of requesting an amendment —
reinterpretation is constitutional change without a record.
