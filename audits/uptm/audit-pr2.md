## A. Original CRITICAL/HIGH findings — FIXED / NOT FIXED

| # | Area | Status | Severity | Evidence |
|---|---|---:|---:|---|
| 1 | Ledger immutability: UPDATE/DELETE/rewrite, trigger bypass, SQL, hash-chain/anchors | **NOT FIXED** | **CRITICAL** | `uptm/db.py:27-37` uses SQLite triggers only for UPDATE/DELETE. `ledger_integrity` is mutable (`uptm/db.py:39-44`). By dropping/recreating triggers and recomputing in-repo hashes/anchors, a rewritten ledger passes `verify_ledger_integrity` (`uptm/ledger.py:160-209`). Probe output: `REWRITE_ACCEPTED orig_cash= 650.0 new_cash= 998999751.0`. |
| 2 | Fill/PnL integrity: fabricated fills, forged auth, duplicates, impossible fills, manual inserts, reconstruction | **NOT FIXED** | **CRITICAL** | Fill auth is a hardcoded in-repo HMAC key (`uptm/ledger.py:16-18`) and public helper (`uptm/ledger.py:127-157`). Direct SQL can insert a forged fill with valid digest/hash/anchor, and `snapshot_from_ledger` accepts it (`uptm/portfolio.py:26-75`). Probe output: `FORGED_APPEND_ACCEPTED cash= 998999751.0 positions= {'BTC': -999.0}`. |
| 3 | Look-ahead/leakage: same-bar, future timestamps, feature/label leakage, contamination, boundaries | **NOT FIXED** | **HIGH** | Same-bar leakage is improved for already-sorted bars (`uptm/backtest.py:57-86`, `uptm/paper.py:45-83` use prior `history`). But neither validates timestamp monotonicity. An unsorted list lets future timestamps enter `history` before earlier execution bars. Probe output: `UNSORTED_BACKTEST_TRADES [('2024-01-01T00:00:00+00:00', 'buy', 10.0)]` after seeing `2024-01-03`. |
| 4 | Walk-forward chronology | **NOT FIXED** | **HIGH** | `walk_forward_validate` partitions by list index only (`uptm/validation.py:39-65`) and never validates timestamp order. Probe accepted train/validation dates Jan 10-13 and test dates Jan 1-2: `WALK_FORWARD_CHRONOLOGY_ACCEPTED train= [...] validation= [...] test= [...]`. |
| 5 | Lifecycle gates: unapproved strategy, stale/invalid artifacts, alternate execution paths | **NOT FIXED** | **HIGH** | `run_paper_loop` trusts caller-provided `approved_strategy_artifact_id` (`uptm/paper.py:29-32`). For non-dataclass strategies, `strategy_artifact_id` hashes only name/class (`uptm/strategies.py:42-49`), ignoring mutable state/source/fit output. Probe mutated behavior after approval while artifact stayed unchanged and paper orders executed. |
| 6 | Kelly enforcement: oversized, proposal mismatch, malformed/negative/extreme values, alternate paths | **NOT FIXED** | **HIGH** | `PaperExecutionAdapter._validate_risk_proposal` checks only symbol/side and mark-price notional (`uptm/execution.py:117-131`). It accepts negative Kelly fractions if notional is positive, does not verify proposal provenance/freshness, and buy slippage can make actual fill notional exceed approved notional (`uptm/execution.py:87-90`). Probe outputs: `NEGATIVE_FRACTION_PROPOSAL_ACCEPTED ...`; `SLIPPAGE_OVERSIZED_FILL_ACCEPTED approved_notional=100.0 fill_notional=110.0`. |
| 7 | Paper/live isolation | **FIXED based on inspected evidence** | N/A | Repository-wide search found no broker/exchange live route. `LiveExecutionAdapter.place_order` always raises (`uptm/execution.py:134-143`), config rejects `live_trading=True` (`uptm/config.py:47-49`), and default config disables live (`configs/default.toml:1-3`). |
| 8 | Adversarial regression coverage | **NOT FIXED** | **HIGH** | Existing tests pass but miss the actual adversarial properties above. For example, tests reject malformed manual inserts (`tests/test_adversarial_audit.py:97-115`) but never try a correctly forged HMAC/hash/anchor; trigger tests drop triggers but do not recompute anchors and restore triggers (`tests/test_adversarial_audit.py:50-94`); Kelly tests only cover missing/oversized mark-notional proposals (`tests/test_adversarial_audit.py:272-287`). |

## B. New vulnerabilities discovered

1. **CRITICAL — Public hardcoded fill-auth secret makes “authenticated” fills forgeable**
   - **File/function:** `uptm/ledger.py:16-18`, `build_authenticated_fill_payload` at `uptm/ledger.py:127-157`.
   - **Mechanism:** The authentication key is a constant in source code. Anyone with code access can compute valid `auth_digest` values. Because SQLite accepts direct `INSERT` into `ledger_events`, and `ledger_integrity` is mutable, forged fills can be made indistinguishable from adapter fills to the verifier.
   - **Reproduction:** See forged append probe in section C.
   - **Recommended fix:** Do not use an in-repo static secret as proof of execution provenance. Bind fills to an execution service identity unavailable to arbitrary SQL/code paths, store external signed append receipts, and anchor tips/counts in an external immutable store. Add DB constraints/triggers that reject unauthenticated inserts at write time, but do not rely on SQLite alone against direct-SQL threat.

2. **HIGH — Strategy artifact IDs do not bind reviewed immutable behavior**
   - **File/function:** `strategy_artifact_id`, `uptm/strategies.py:42-49`; gate in `run_paper_loop`, `uptm/paper.py:29-32`.
   - **Mechanism:** Non-dataclass artifact IDs ignore instance state and method implementation. A strategy can be approved when inert, mutate afterward, keep the same ID, and execute.
   - **Reproduction:** See mutable strategy probe in section C.
   - **Recommended fix:** Persist approved artifacts as immutable serialized strategy definitions with code/version hash, parameters, training data window, validation result, expiry, and approval signature. Paper execution should load the approved artifact from registry, not accept an arbitrary object plus caller-supplied string.

3. **HIGH — Actual fill notional can exceed Kelly approval after slippage**
   - **File/function:** `_validate_risk_proposal`, `uptm/execution.py:117-131`; fill pricing at `uptm/execution.py:87-90`.
   - **Mechanism:** Approval compares `quantity * mark_price`, but fill records `quantity * fill_price`; buy slippage increases actual notional beyond approval.
   - **Recommended fix:** Validate worst-case fill notional including slippage and fees before execution, or size quantity from approved notional after slippage/fees.

## C. Tests actually executed and results

1. Existing suite with system Python:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider
```

Output:

```text
/usr/bin/python3: No module named pytest
```

2. Temporary pytest install under `/tmp`, then full suite:

```bash
python3 -m pip install --target /tmp/uptm-pytest pytest
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/tmp/uptm-pytest:. python3 -m pytest -q -p no:cacheprovider
```

Output:

```text
17 passed in 0.29s
```

3. Forged direct-SQL fill probe:

```text
FORGED_APPEND_ACCEPTED cash= 998999751.0 positions= {'BTC': -999.0} equity= 998999751.0
```

4. Trigger-bypass ledger rewrite probe:

```text
REWRITE_ACCEPTED orig_cash= 650.0 new_cash= 998999751.0 positions= {'BTC': -999.0}
```

5. Unsorted backtest chronology probe:

```text
UNSORTED_BACKTEST_TRADES [('2024-01-01T00:00:00+00:00', 'buy', 10.0)]
```

6. Walk-forward future-training probe:

```text
WALK_FORWARD_CHRONOLOGY_ACCEPTED train= ['2024-01-10T00:00:00+00:00', '2024-01-11T00:00:00+00:00', '2024-01-12T00:00:00+00:00'] validation= ['2024-01-13T00:00:00+00:00'] test= ['2024-01-01T00:00:00+00:00', '2024-01-02T00:00:00+00:00']
```

7. Mutable strategy gate probe:

```text
ARTIFACT_AFTER_MUTATION_UNCHANGED True candidate:3b36ff...
MUTATED_STRATEGY_ACCEPTED PaperLoopSummary(orders_submitted=1, fills_recorded=1, final_position=0.5)
```

8. Kelly bypass probes:

```text
NEGATIVE_FRACTION_PROPOSAL_ACCEPTED Fill(symbol='BTC', side='buy', quantity=1.0, price=100.0, fee=0.0, currency='USD')
SLIPPAGE_OVERSIZED_FILL_ACCEPTED approved_notional=100.0 fill_price= 110.00000000000001 fill_notional= 110.00000000000001
```

Repository status after audit:

```text
## cursor/critical-high-audit-fixes-b6b8
```

No repository files were modified.

## D. Remaining MEDIUM/LOW issues

- **MEDIUM:** Duplicate economic fills are not prevented. `event_id` is unique (`uptm/db.py:12`), but the same economic fill can be replayed with a new event ID and valid auth/hash.
- **MEDIUM:** Naked short / impossible inventory fills are accepted in portfolio reconstruction. `snapshot_from_ledger` permits sells that drive positions negative (`uptm/portfolio.py:46-48`).
- **LOW/MEDIUM:** `PerformanceAuditor.audit` counts ledger rows after reconstruction (`uptm/auditor.py:36`) but does not add independent anomaly warnings for duplicate fills, negative positions, stale/missing marks, or non-monotonic timestamps.

## E. Merge safety

**DO NOT MERGE.**

Multiple original CRITICAL/HIGH findings remain exploitable based on code inspection and executed probes: ledger rewrite/forged append, fabricated fill/PnL, chronology leakage, walk-forward chronology failure, lifecycle gate bypass, Kelly enforcement bypass, and insufficient adversarial coverage.

## F. Exact next action

Block PR #2 and require fixes before merge. Minimum required next work:

1. Replace SQLite-only ledger integrity with externally anchored append-only integrity that direct SQL plus repo code cannot forge.
2. Remove public/static fill-auth secrets and bind fills to an execution authority not available to arbitrary callers.
3. Enforce monotonic timestamps before backtest, paper loop, and walk-forward partitioning.
4. Replace caller-supplied strategy artifact IDs with immutable approved artifact loading/verification.
5. Validate Kelly proposals for provenance, freshness, finite sane values, fraction bounds, and worst-case fill notional including slippage/fees.
6. Add adversarial tests that reproduce the probes above and fail before the fixes.