# UPTM GOVERNANCE MODEL v1.0

Binding. Resolves authority between the two constitutions of this repository.

| | |
|---|---|
| Version | **1.0** |
| Status | **ACTIVE** |
| Amended by | Founder only (CC/P14) |
| Decided in | `docs/adr/ADR-001-constitution-reconciliation.md` |

## 1. The two planes

| | Control Plane (CP) | Capital Capability (CC) |
|---|---|---|
| Document | `constitution/CONSTITUTION.md` | `constitution/CONSTITUTION-CAPITAL.md` |
| Machine rules | `constitution/rules.json` | `constitution/capital-rules.json` |
| Governs | agents, orchestration, waves, evidence mechanics, verification, fail-closed behaviour | authority to risk capital: risk, execution, data integrity, LIVE, Founder authority |
| Question it answers | *How is authority mechanically withheld or granted?* | *May this capability be authorised at all?* |

## 2. Authority model

```
FOUNDER                  sole amendment authority over both constitutions
   │
   ▼
CAPITAL CAPABILITY       WHAT may be authorised, and on what evidence
   │
   ▼
CONTROL PLANE            HOW authority is mechanically withheld or granted
   │
   ▼
RUNNER / FSM / GATES     deterministic enforcement
   │
   ▼
AGENTS                   propose only; never decide
```

**Authority flows down. Enforcement flows up.** CC is a policy layer with no runtime of
its own; CP is the only layer that can actually stop anything.

### 2.1 Boundary rule

> **Capital Capability Gates may consume Control Plane evidence, but may never grant,
> weaken, bypass, or modify Control Plane authority.**

CC may always refuse. CC may never permit something CP refuses, and may never reach into
CP's mechanisms to make CP refuse less.

### 2.2 Declarative is not enforcement

> A CC principle not expressed as a CP mechanism — a rule in `rules.json` /
> `capital-rules.json`, a check in `gates.py` / `stops.py`, or a test — is
> **DECLARATIVE**. Declarative is never PASS (CC/P9).

Every principle carries an explicit enforcement status in `capital-rules.json`. A status
of `ENFORCED` requires a named mechanism; the governance test refuses the claim otherwise.

## 3. Jurisdiction matrix

| Domain | CP | CC | Authority |
|---|:--:|:--:|---|
| Agent execution, dispatch, concurrency | ✓ | — | CP |
| Wave sequencing / wave crossing | ✓ | — | CP |
| Patch loop limits | ✓ | — | CP |
| Evidence format (schema, probes, digests) | ✓ | — | CP |
| Evidence validity over time (STALE) | — | ✓ | CC (P12) |
| Evidence sufficiency for a gate | ✓ | ✓ | stricter rule wins |
| Verification independence | ✓ | ✓ | stricter rule wins |
| Data integrity / point-in-time | — | ✓ | CC (P3) |
| Risk limits and their derivation inputs | — | ✓ | CC (P6) |
| Execution path parity (backtest ↔ live) | — | ✓ | CC (P2) |
| Pre-trade decision path composition | — | ✓ | CC (P13) |
| Kill switch ownership and drills | — | ✓ | CC (P8) |
| LIVE capability grant / expiry | — | ✓ | CC + Founder (P7) |
| Constitution amendment | ✓ | ✓ | Founder only (P14) |

## 4. Conflict resolution

### C1 — Proceed / halt

| CP | CC | Result |
|---|---|---|
| ALLOW | ALLOW | **ALLOW** |
| ALLOW | DENY | **DENY** |
| DENY | ALLOW | **DENY** |
| DENY | DENY | **DENY** |
| UNKNOWN | any | **DENY** |
| any | UNKNOWN | **DENY** |

`UNKNOWN` is never resolved to `ALLOW`. Either plane may stop the system; neither may
start it alone.

### C2 — Definitional conflict (schema, severity, threshold)

CC defines the **floor**. CP may tighten it, never loosen it. If CP's definition would
admit an artifact that CC's definition rejects, CC applies and the artifact is rejected.

### C3 — Silence

Neither constitution covers the case → **DENY and escalate to Founder** (CC/P11).
Silence is not permission.

## 5. LIVE dual control

LIVE trading requires **all four** conditions simultaneously:

```
CP.live_trading == true            (Founder flip, recorded as a P14 amendment)
  AND CC.live_capability_lease == VALID   (unexpired, explicitly granted)
  AND Founder approval == VALID
  AND all required capital gates == PASS
        ↓
    LIVE ALLOWED
```

If any condition lapses → **DENY**, immediately and automatically.

`CP.live_trading` is retained permanently as an independent condition. The lease never
replaces it and it never replaces the lease. Two authorities, two mechanisms, neither
sufficient alone.

Until a Founder amendment states otherwise, `CP.live_trading` remains `false` and
`live_trading_enablement_attempt` remains a stop condition.

## 6. Programme structure

```
                    UPTM RUNNER
                         │
             ┌───────────┴───────────┐
       CONTROL PLANE            CAPITAL CAPABILITY
         WAVES 0–7                   GATES
             │                         │
             └───────────┬─────────────┘
                   SAME RUNNER
                   SAME EVIDENCE MECHANICS
                   SAME CP RULES
```

Capital gates are **not** waves 8+. Waves verify the control plane; capital gates
authorise risk. Numbering them consecutively would frame capital authorisation as the
next development milestone, which it is not. CC may withhold capital capability even
when every control-plane wave is PASS.

## 7. Canonical language

English is the canonical language for all governance documents, rules, schemas, code,
tests and agent prompts in this repository. Non-English explanations may exist outside
the repository but are never normative.
