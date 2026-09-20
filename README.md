# uptm-runner

Control-plane / orchestration scaffold around [UPTM](https://github.com/onlinovosk-bit/onlinovosk-bit-uptm).

**Live trading is ABSOLUTELY DISABLED. No auto-merge. Max 8 Cursor agents.**

This is **not** a git clone of UPTM. It will be pushed to `github.com/onlinovosk-bit/uptm-runner`.

## Layout

```
constitution/   # Immutable rules (md + json)
prompt-stacks/  # STACK 00–07 contracts
waves/          # Wave 0–7 YAML definitions
runner/         # FSM, gates, evidence, stops, CLI
ruflo/          # Adapter boundary + unavailable stub
cursor/         # Execution contract + fail-closed stub
evidence/       # Evidence artifacts (generated)
schemas/        # JSON schemas
audits/         # Baseline + copied UPTM audit knowledge
tests/          # Unit + adversarial tests
docs/           # TRUST_MODEL, RUFLO_BOUNDARY
```

## Setup (uv)

```bash
cd /workspace
uv sync --extra dev
```

## CLI

```bash
uv run uptm-runner baseline
uv run uptm-runner wave-status
uv run uptm-runner evaluate-gate --evidence evidence/wave0/baseline_ack.json
uv run uptm-runner smoke
```

## Tests

```bash
uv run pytest
```

## Real vs stub

| Component | Status |
|-----------|--------|
| Wave 0 baseline JSON | **Real** (from audits 1–3, PR4 hypotheses, and audit #16 tip reconciliation) |
| Constitution / stacks / waves | **Real** contracts |
| FSM + gates + stops + evidence validation | **Real** |
| CLI | **Real** |
| Pytest suite | **Real** |
| Cursor executor | **Stub** — `NullCursorExecutor` fails closed; handoff documented |
| Ruflo adapter | **Stub** — unavailable; local FSM is source of truth |
| UPTM live integrations | **None** (by design) |

## UPTM merge policy

UPTM tip PR #16 is recorded as **CLEAR FOR MEDIUM/LOW ONLY** per audit #16.
Runner **must not auto-merge** PR #16 or any UPTM PR. A machine gate requires
CRITICAL=0, HIGH=0, tests passing, adversarial tests passing, CI passing, and
invariants holding. Live trading remains disabled.

## Trust

See [docs/TRUST_MODEL.md](docs/TRUST_MODEL.md). Runner makes **no** immutability claims for local-only state.
