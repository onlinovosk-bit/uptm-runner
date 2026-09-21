# UPTM Runner Constitution

| | |
|---|---|
| Version | **1.0** |
| Status | **ACTIVE** |
| Jurisdiction | Control Plane (CP) — see `constitution/GOVERNANCE.md` |
| Amended by | Founder only (CC/P14) |
| Machine rules | `constitution/rules.json` |

Machine-enforced rules for the control-plane. Agents may propose; Runner decides from evidence.

Capital authority is governed separately by `constitution/CONSTITUTION-CAPITAL.md`.
On conflict, see `constitution/GOVERNANCE.md` §4 — either plane may deny; neither may
permit alone; UNKNOWN resolves to DENY.

## Hard invariants (never relax)

1. **Live trading is ABSOLUTELY DISABLED.** Any attempt to enable live trading, broker routes, or real order placement is a STOP condition.
2. **No auto-merge.** Runner never auto-merges UPTM PRs. Any UPTM merge requires a machine gate with CRITICAL=0, HIGH=0, tests passing, adversarial tests passing, CI passing, and invariants holding.
3. **Max 8 Cursor agents** in parallel.
4. **CRITICAL = 0 and HIGH = 0** required to pass any wave gate.
5. **Evidence required.** Agent self-report alone NEVER passes a gate.
6. **Deterministic evaluation** from evidence artifacts only (schemas, probes, before/after hashes).
7. **No fabricated market data or PnL** in evidence or UPTM outputs.
8. **No safety weakening** (removing kill switches, relaxing auth, deleting adversarial tests without replacement).
9. **Patch loop max 3** attempts per failure cluster, then `HUMAN_REVIEW_REQUIRED`.
10. **Waves do not cross.** Wave N outputs are gated before Wave N+1 inputs are unlocked.
11. **Fail closed.** Missing evidence, missing probes, unconfigured Cursor/Ruflo → refuse progress.
12. **No immutability claims** for Runner itself when state is local-only.

## Trust posture

- Runner is designed to be **harder to fool than agents**.
- Prior UPTM audits (PR1–PR3) found CRITICAL coordinated DB+key+receipt forgery among other HIGH issues.
- UPTM tip PR #16 is **CLEAR FOR MEDIUM/LOW ONLY** per audit #16, with residuals explicitly accepted. This is not permission for live trading or auto-merge.
- PR4 claims are superseded by later audit history but remain recorded as historical **HYPOTHESIS** in this baseline.
- Ruflo may be unavailable — orchestration abstraction is mandatory; Ruflo is an optional adapter.
- Cursor may be unreachable from this host — execution contract is mandatory; live Cursor is optional.

## Stop conditions (immediate halt → HUMAN_REVIEW_REQUIRED)

- Live trading enablement
- Safety control weakening
- Fabricated data / PnL
- Forged evidence / fake agent PASS
- Wave skip / gate bypass
- Unauthorized merge attempt
