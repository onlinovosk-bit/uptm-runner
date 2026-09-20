Implemented PR #3 on new branch `cursor/pr3-audit-hardening-fc09` against default branch `main`. PR #3 is open as draft.

## A. CRITICAL/HIGH from PR #2

| Area | Status | Pre-fix exploit reproduced | Code change | Post-fix blocked by | Regression |
|---|---|---:|---|---|---|
| Ledger immutability | FIXED for SQL/trigger/rewrite threat | `REWRITE_ACCEPTED...` | `uptm/ledger.py`: per-ledger authority key + external receipt journal; verifier checks hash chain, DB anchor, triggers, and receipt chain | `REWRITE_BLOCKED LedgerIntegrityError ledger receipt event mismatch`; UPDATE/DELETE blocked | `test_ledger_receipt_journal_rejects_full_sql_history_rewrite` |
| Fill/PnL authenticity | FIXED | `FORGED_APPEND_ACCEPTED...` | Removed hardcoded public HMAC; `PaperExecutionAuthority` signs fills; direct SQL rows lack valid auth/receipt | `FORGED_APPEND_BLOCKED LedgerIntegrityError unauthenticated fill source` | `test_manual_sql_fill_is_rejected_before_pnl_reconstruction`, `test_duplicate_economic_fill_replay_by_sql_is_rejected` |
| Data chronology | FIXED | `UNSORTED_BACKTEST_TRADES...` | `uptm/chronology.py`; enforced in backtest/paper/walk-forward | `UNSORTED_BACKTEST_BLOCKED...`; `FUTURE_BAR_BLOCKED...` | `test_backtest_rejects_unsorted_and_future_dated_bars` |
| Walk-forward chronology | FIXED for future-train/past-test exploit | `WALK_FORWARD_CHRONOLOGY_ACCEPTED...` | Chronological validation before fitting/splitting | `WALK_FORWARD_CHRONOLOGY_BLOCKED...` | `test_walk_forward_rejects_future_train_before_past_test` |
| Lifecycle/artifact gate | FIXED | `MUTATED_STRATEGY_ACCEPTED...` | Approved immutable `StrategyArtifact` bound to source, state, approval, and config | `MUTATED_STRATEGY_BLOCKED...` | `test_paper_loop_refuses_post_approval_mutated_strategy`, `test_paper_loop_refuses_strategy_substitution_with_approved_artifact` |
| Kelly / exposure limits | FIXED | `NEGATIVE_FRACTION_PROPOSAL_ACCEPTED...`; `SLIPPAGE_OVERSIZED_FILL_ACCEPTED...` | Finite/bounded/approved proposal checks; final post-cost exposure validation; paper sizing by final exposure | Negative and slippage probes blocked | `test_paper_execution_rejects_negative_zero_malformed_or_unapproved_kelly`, `test_paper_execution_rejects_slippage_that_exceeds_approved_notional` |
| Paper/live isolation | PRESERVED | N/A | No live route added; live adapter/config still hard-fail | Smoke reports `"live_trading": false` | Existing `tests/test_safety.py` |

## B. New vulnerabilities discovered

- **MEDIUM residual:** receipt/key authority is local filesystem based, not external WORM/HSM anchoring. SQL-only rewrite attacks are blocked, but an attacker with same-user filesystem write access to DB, key, and receipt files could still attempt coordinated tampering. Not fixed in this PR because it requires an external immutable anchor/trust service beyond the repo-local paper bootstrap.

## C. Files changed

- `uptm/chronology.py`
- `uptm/ledger.py`
- `uptm/execution.py`
- `uptm/risk.py`
- `uptm/strategies.py`
- `uptm/backtest.py`
- `uptm/paper.py`
- `uptm/validation.py`
- `uptm/agents/research.py`
- `uptm/cli.py`
- `tests/test_adversarial_audit.py`

## D. Exact adversarial tests added

- `test_ledger_receipt_journal_rejects_full_sql_history_rewrite`
- `test_duplicate_economic_fill_replay_by_sql_is_rejected`
- `test_backtest_rejects_unsorted_and_future_dated_bars`
- `test_walk_forward_rejects_future_train_before_past_test`
- `test_paper_loop_refuses_post_approval_mutated_strategy`
- `test_paper_loop_refuses_strategy_substitution_with_approved_artifact`
- `test_paper_execution_rejects_negative_zero_malformed_or_unapproved_kelly`
- `test_paper_execution_rejects_slippage_that_exceeds_approved_notional`

## E. Full test results

Initial direct pytest:

```text
/usr/bin/python3: No module named pytest
```

Temporary pytest install + full suite:

```bash
python3 -m pip install --target /tmp/uptm-pytest pytest
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/tmp/uptm-pytest:. python3 -m pytest -q -p no:cacheprovider
```

Final output:

```text
25 passed in 0.60s
```

Targeted post-fix probes:

```text
FORGED_APPEND_BLOCKED LedgerIntegrityError unauthenticated fill source
SQL_MUTATION_BLOCKED UPDATE IntegrityError ledger_events is append-only
SQL_MUTATION_BLOCKED DELETE IntegrityError ledger_events is append-only
REWRITE_BLOCKED LedgerIntegrityError ledger receipt event mismatch
UNSORTED_BACKTEST_BLOCKED ValueError Bars must be strictly chronological with unique timestamps.
FUTURE_BAR_BLOCKED ValueError Bar timestamp is in the future...
WALK_FORWARD_CHRONOLOGY_BLOCKED ValueError Bars must be strictly chronological with unique timestamps.
MUTATED_STRATEGY_BLOCKED ValueError Paper execution requires the immutable gate-approved strategy artifact.
NEGATIVE_FRACTION_BLOCKED RiskLimitExceededError Risk proposal fraction must be finite and bounded in [0, 1].
SLIPPAGE_OVERSIZED_FILL_BLOCKED RiskLimitExceededError Final order exposure exceeds Kelly risk proposal.
```

Paper-only smoke:

```bash
PYTHONPATH=/tmp/uptm-pytest:. python3 -m uptm.cli smoke --config configs/default.toml --bars 12
```

Result: exited `0`, reported `"mode": "paper-only"`, `"live_trading": false`, and one paper fill.

## F. Remaining MEDIUM/LOW

- Local filesystem receipt/key anchoring is not equivalent to external WORM anchoring.
- Walk-forward sizes are still bar-count based, though chronology/future contamination is now enforced.
- First-audit medium/low items like synthetic provenance hard separation, richer auditor warnings, and CI SHA pinning remain outside this PR.

## G. Third adversarial audit readiness

**READY FOR THIRD ADVERSARIAL AUDIT**, with the residual filesystem-anchor limitation called out explicitly.