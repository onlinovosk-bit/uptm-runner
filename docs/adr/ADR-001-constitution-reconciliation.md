# ADR-001 — Constitution Reconciliation (Control Plane ↔ Capital Capability)

| | |
|---|---|
| Status | **ACCEPTED** — all six decisions recorded in §9 |
| Scope | Read-only analysis. No wave rewritten, no gate defined, no broker, no new prompt stack. |
| Inputs | `constitution/CONSTITUTION.md`, `constitution/rules.json`, `runner/{gates,stops,fsm}.py`, `docs/TRUST_MODEL.md`, `waves/*.yaml`, `audits/uptm/*` @ `9b120c0` |
| Produces | Jurisdiction Matrix · Conflict Resolution · Authority Model · Evidence Mapping |

## 0. Why this ADR exists

Two constitutions now exist for one system:

- **CP — Control Plane Constitution** (`constitution/CONSTITUTION.md`, in repo, partly
  machine-enforced): governs agents, waves, evidence, gates, FSM, orchestration.
- **CC — Capital Capability Constitution** (P1–P14, drafted, not in repo): governs when
  the system may be granted authority over capital — risk, execution, data integrity,
  LIVE capability, Founder authority, uncertainty.

Two constitutions without a declared hierarchy is worse than one incomplete constitution,
because every conflict becomes an interpretation — and interpretation is the failure mode
CC/P14 exists to forbid. This ADR declares the hierarchy before either is extended.

---

## 1. Authority Model

```
FOUNDER                     sole amendment authority for both constitutions
   │
   ▼
CAPITAL CAPABILITY (CC)     WHAT may be authorised, and on what evidence
   │
   ▼
CONTROL PLANE (CP)          HOW authority is mechanically withheld or granted
   │
   ▼
RUNNER / FSM / GATES        deterministic enforcement
   │
   ▼
AGENTS                      propose only; never decide
```

**Authority flows down. Enforcement flows up.** CC has authority it cannot itself
enforce: it is a policy layer with no runtime. CP is the only layer that can actually
stop anything.

**Consequence (the central rule of this ADR):**

> A CC principle that is not expressed as a CP mechanism — a rule in `rules.json`,
> a check in `gates.py`/`stops.py`, or a test — is **DECLARATIVE**. Declarative is
> not enforcement, and per P9 declarative is never PASS.

Adding P1–P14 to the repo therefore does not make the system safer by itself. It makes
the gap between claimed and enforced safety **measurable**. That is the actual
deliverable of adopting CC.

---

## 2. Jurisdiction Matrix

| Domain | CP | CC | Authority on conflict |
|---|:--:|:--:|---|
| Agent execution, dispatch, concurrency | ✓ | — | **CP** |
| Wave sequencing / wave crossing | ✓ | — | **CP** |
| Patch loop limits | ✓ | — | **CP** |
| Evidence *format* (schema, probes, digests) | ✓ | — | **CP** |
| Evidence *validity over time* (STALE) | — | ✓ | **CC** (P12) |
| Evidence sufficiency for a gate | ✓ | ✓ | **stricter rule wins** |
| Verification independence | ✓ | ✓ | **stricter rule wins** |
| Data integrity / point-in-time | — | ✓ | **CC** (P3) |
| Risk limits and their derivation inputs | — | ✓ | **CC** (P6) |
| Execution path parity (backtest↔live) | — | ✓ | **CC** (P2) |
| Pre-trade decision path composition | — | ✓ | **CC** (P13) |
| Kill switch ownership and drills | — | ✓ | **CC** (P8) |
| LIVE capability grant / expiry | — | ✓ | **CC + Founder** (P7) |
| Constitution amendment | ✓ | ✓ | **Founder only** (P14) |

CP is not subordinate in its own domain. CC does not get to rewrite how agents are
dispatched; CP does not get to decide when capital is at risk.

---

## 3. Conflict Resolution

Three conflict classes. All three resolve without interpretation.

### C1 — Proceed / halt disagreement

```
CP = ALLOW  ∧  CC = DENY   →  DENY
CP = DENY   ∧  CC = ALLOW  →  DENY
```

No context, no override, no "the other layer already checked it". Asymmetric by design:
either layer may stop the system; neither may start it alone.

### C2 — Definitional disagreement (schema, severity, threshold)

CC defines the **floor**. CP may only tighten it, never loosen it. If CP's definition
would admit an artifact that CC's definition rejects, CC's applies and the artifact is
rejected.

*Worked example:* CP accepts an evidence pack with valid probes and digests. CC/P12
additionally requires runtime identity and a declaration of non-deterministic inputs.
The pack is **rejected** — CP's acceptance does not survive CC's floor.

### C3 — Silence (neither constitution covers the case)

```
→ DENY + escalate to Founder (P11)
```

This is the most common case in practice and the one most likely to be resolved by an
agent inventing a rule. Silence is not permission.

### Structural conflict already present: `live_trading` vs. P7

CP (`rules.json`) declares `live_trading: false` as a **permanent boolean**, and
`live_trading_enablement_attempt` as a **stop condition**. CC/P7 declares LIVE as a
**leased, time-boxed, Founder-granted capability**.

Read literally, these are incompatible: any legitimate future LIVE grant trips CP's own
stop condition, so the system as built **cannot reach LIVE without violating itself**.

Proposed resolution (Founder decision required):

- `live_trading: false` is **retained permanently as an independent condition**. It is
  never replaced by, and never derived from, the lease.
- A LIVE grant requires **both** an unexpired CC lease **and** an explicit Founder flip
  of the CP boolean, recorded as an amendment under P14.
- Two independent conditions, two independent authorities. Neither alone suffices.

This is stricter than either constitution is today and should be adopted regardless of
whether the rest of CC is adopted.

---

## 4. Evidence Mapping — claimed vs. enforced

Verified by reading the code at `9b120c0`, not by reading the documents.

### 4.1 Stop conditions

`rules.json` and `runner/stops.py` both declare 8 stop conditions. Actual detection:

| Stop condition | Status | Evidence |
|---|---|---|
| `live_trading_enablement_attempt` | **ENFORCED** | `stops.check_live_trading`; `check_evidence_for_stops` requires `evidence.live_trading is False` |
| `wave_skip_attempt` | **ENFORCED** | `fsm.py:112,114` (raises `FSMError`, not `StopConditionError` — see 4.3) |
| `evidence_forgery_detected` | **PARTIAL** | only "PASS claim with empty probes" |
| `unauthorized_pr_merge` | **PARTIAL** | only the `pr4_merge_allowed` flag (`fsm.py:162`) |
| `safety_control_weakening` | **DECLARATIVE** | name in frozenset only; no detector |
| `gate_bypass_attempt` | **DECLARATIVE** | name in frozenset only; no detector |
| `fabricated_market_data` | **DECLARATIVE** | name in frozenset only; no detector |
| `fabricated_pnl` | **DECLARATIVE** | `stops.py:52-57` is a dead branch ending in `pass`; no test references `fabricat` |

**Four of eight stop conditions are names with no detector.** A system whose trust model
says it is "harder to fool than agents" currently cannot detect fabricated market data or
fabricated PnL — the two failure modes most specific to a trading system.

This is not a criticism of the build; it is exactly the ENFORCED/DECLARATIVE distinction
CC/P9 asks us to make visible. It is now visible.

### 4.2 CC principles against the existing codebase

| CC | Status | Basis |
|---|---|---|
| P5 Independence of verification | **ENFORCED** | `gates.py` rejects agent PASS without probes/results/before-after digests; detects severity downgrade |
| P11 Uncertainty halts | **ENFORCED** | `fail_closed: true`; missing/unloadable evidence → FAIL; `HUMAN_REVIEW_REQUIRED` state |
| P4 Preregistered gates | **PARTIAL** | `exit_criteria` fixed in wave YAML before execution; no rule forbidding post-hoc amendment |
| P9 No progress illusion | **PARTIAL** | capability-style gating exists; no readiness board; no DECLARATIVE≠PASS rule |
| P6 No self-expansion | **WEAK** | "no safety weakening" is declarative; does not cover redefinition of limit inputs |
| P12 Evidence commit & expiry | **HALF** | before/after digests exist; **no STALE invalidation on dependency change** |
| P8 Independent kill switch | **DECLARATIVE** | no independent switch exists |
| P7 LIVE as leased capability | **CONFLICT** | see §3 |
| P1 Reality over architecture | **MISSING** | — |
| P2 Same validated path | **MISSING** | — |
| P3 Data before evidence | **MISSING** | — |
| P10 €700 validation capital | **MISSING** | — |
| P13 No model in pre-trade path | **MISSING** | — |
| P14 Versioned amendment | **MISSING** | `rules.json` has `schema_version`; `CONSTITUTION.md` has no version and no amendment procedure |

### 4.3 Secondary findings

- **`CONSTITUTION.md` is unversioned.** P14 cannot bind evidence to a constitution
  version that does not exist. Minimum fix: add a version header.
- **`wave_skip_attempt` raises `FSMError`, not `StopConditionError`.** It is caught as a
  different class than every other stop, so it does not route through
  `raise_if_stop` and may not reach `HUMAN_REVIEW_REQUIRED` on the same path. Worth a
  targeted test either way.
- **No secrets in this repository.** A full-tree scan for credential patterns and
  ≥32-char opaque tokens returned only prose descriptions of vulnerabilities and test
  names. Repository visibility is therefore a **disclosure judgement, not a credential
  incident** — see §5.

---

## 5. Repository visibility — corrected assessment

`onlinovosk-bit/uptm-runner` is public. An earlier recommendation to flip it to private
immediately was made **before** inspecting the contents and is withdrawn as stated.

Facts:

- No credentials, keys, or tokens are present in the tree.
- `audits/uptm/` contains descriptions of **confirmed CRITICAL vulnerabilities**
  (coordinated DB + key + receipt forgery; a hardcoded fill-auth secret) in a **separate
  UPTM repository**, with fix status recorded as partly residual/accepted.
- Those descriptions name the attack paths precisely.

The exposure is therefore not "our keys are public" but "a map of our unfixed
vulnerabilities is public, and the vulnerable code is elsewhere". Whether that matters
depends entirely on the visibility and state of that other repository, which this session
cannot access.

**Update:** `onlinovosk-bit/onlinovosk-bit-uptm` exists and is **private**. The
vulnerable code is therefore not public; what is public is the description of where to
look for it. The map is public, the house is locked.

**Recommendation:** visibility of `uptm-runner` is a judgement call, no longer an
incident. It should be revisited if the UPTM repository ever becomes public, and before
any capital-gate evidence (broker identifiers, account metadata) is committed here.

---

## 6. Language of the governance corpus

`CONSTITUTION.md`, `TRUST_MODEL.md`, wave definitions and prompt stacks are in English;
the CC draft (P1–P14) is in Slovak. A governance corpus read by agents must be in **one**
language, or an agent will silently skip what it treats as commentary.

**Recommendation:** English for everything committed to the repository. Slovak remains the
working language between Founder and assistant.

---

## 7. What this ADR deliberately does NOT do

- does not rewrite or renumber waves 0–7
- does not define Gate 01 or any capital-program gate
- does not select a broker, asset class or timeframe
- does not add a prompt stack or an agent
- does not commit P1–P14 to the repository
- does not change repository visibility

---

## 8. What this ADR deliberately did NOT do

- did not rewrite or renumber waves 0–7
- did not define Gate 01 or any capital-program gate
- did not select a broker, asset class or timeframe
- did not add a prompt stack or an agent
- did not change repository visibility

## 9. Decision record (Founder)

| # | Decision | Answer |
|---|---|---|
| 1 | Two-plane model CP + CC with the Authority Model of §1 | **YES** |
| 2 | Conflict rules C1–C3, including UNKNOWN→DENY and silence→DENY | **YES** |
| 3 | `live_trading` boolean + P7 lease as independent dual control | **YES** |
| 4 | Capital programme placement | **parallel `gates/` track over the same runner — not waves 8+** |
| 5 | Governance corpus language | **English canonical** |
| 6 | Canonical repository | **`onlinovosk-bit/uptm-runner`** |

Additional principle adopted with decision 4 and recorded in `GOVERNANCE.md` §2.1:

> Capital Capability Gates may consume Control Plane evidence, but may never grant,
> weaken, bypass, or modify Control Plane authority.

## 10. What this ADR changed in the repository

| File | Change |
|---|---|
| `constitution/GOVERNANCE.md` | new — authority model, jurisdiction matrix, conflict rules, LIVE dual control, programme structure, canonical language |
| `constitution/CONSTITUTION-CAPITAL.md` | new — Capital Capability Constitution P1–P14 (English) |
| `constitution/capital-rules.json` | new — machine-readable CC rules, per-principle enforcement status, conflict matrix, LIVE conditions, pre-existing capability status |
| `constitution/CONSTITUTION.md` | version header, jurisdiction pointer, conflict pointer — text of the invariants untouched |
| `runner/paths.py` | paths for the capital plane and prompt stacks |
| `prompt-stacks/00_constitution.json` | binds both planes; six CC invariants added to `must_enforce` |
| `tests/test_governance.py` | new — 13 tests |

No wave, gate, FSM state, stop condition or control-plane rule was modified. `rules.json`
is byte-identical; a test asserts `live_trading` is still `false`.

## 11. Open, deliberately not addressed here

- Four of eight control-plane stop conditions have no detector (§4.1). Recorded as
  `DECLARATIVE` in `capital-rules.json`, not fixed. Fixing them is a control-plane task
  and needs its own GO.
- Pre-existing UPTM capabilities (backtest, walk-forward, paper loop, Kelly sizing,
  slippage controls, ledger) are recorded as `STALE` — unverified against this
  constitution, not unusable.
- No capital gate is defined. Gate criteria are written just-in-time, immediately before
  evidence collection for that gate (P4).
