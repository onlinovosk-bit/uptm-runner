Implemented on new branch `cursor/pr4-audit-trust-hardening-0444` from `cursor/pr3-audit-hardening-fc09`. PR #4 was created as draft. No PR #1/#2/#3 branches were modified or merged.

## A. Exact files changed

- `.env.example`
- `README.md`
- `TRUST_MODEL.md`
- `tests/conftest.py`
- `tests/test_adversarial_audit.py`
- `uptm/backtest.py`
- `uptm/db.py`
- `uptm/execution.py`
- `uptm/ledger.py`
- `uptm/risk.py`
- `uptm/strategies.py`
- `uptm/validation.py`

## B. Exact architectural changes

- Added external monotonic trust anchor:
  - Binds ledger event count/tip hash.
  - Binds market mark count/tip hash.
  - Binds authority-key fingerprint.
  - Verification fails closed on missing, mismatched, rolled-back, or key-replaced anchor.
- Fixed empty-ledger erase/reset:
  - Empty DB no longer passes if stale receipts or external anchor indicate prior nonempty state.
- Hardened market marks:
  - Append-only triggers.
  - HMAC-authenticated marks.
  - Hash-chained marks.
  - Future/duplicate/unsorted marks rejected.
  - Portfolio valuation verifies marks before using them.
- Hardened strategy trust:
  - Paper/backtest/walk-forward safety paths only accept frozen built-in strategies.
  - Arbitrary Python strategies/globals/closures are research-only and cannot be promoted.
- Hardened Kelly/risk:
  - Proposal integrity digest.
  - In-process replay prevention.
  - Existing slippage/final exposure checks retained.

## C. Attack reproduced before fix

Source-of-truth audit #3 documented successful pre-fix probes:

- `COORDINATED_FORGERY_SUCCEEDED`
- `EMPTY_REWRITE_SUCCEEDED`
- `PNL_MARK_FORGERY_SUCCEEDED`
- `ARTIFACT_GLOBAL_MUTATION_SUCCEEDED`
- `WF_GLOBAL_FUTURE_LEAK_TRADES`

The new regression tests encode those exploit mechanics and now require them to block.

## D. Why the new defense blocks the attack

- DB + key + receipt rewrites fail because the external anchor still binds the original authority-key fingerprint and prior tips/counts.
- Empty reset fails because the external anchor/receipt state proves prior nonempty state.
- Forged/future marks fail mark auth, mark hash-chain, chronology, and/or anchor verification.
- Global/future strategy leaks fail because arbitrary Python strategies cannot enter safety-sensitive execution/validation.
- Kelly mutation/replay fails proposal digest and consumed-proposal checks.

## E. New adversarial tests

Added coverage for:

- Coordinated DB + authority-key + receipt rewrite.
- Full ledger erase/reset to empty.
- Forged SQL market marks.
- Future/duplicate/unsorted marks.
- Global future strategy in backtest.
- Global future strategy in walk-forward.
- Post-approval strategy mutation.
- Global mutable strategy approval rejection.
- Kelly proposal mutation and replay.

## F. Full test results

- `PYTHONPATH=. python3 -m compileall -q uptm tests` — passed
- `PYTHONPATH=/tmp/uptm-pytest:. python3 -m pytest -q` — `33 passed in 0.69s`
- `PYTHONPATH=. python3 -m uptm.cli smoke --config configs/default.toml --bars 48` — passed

## G. Previous exploit probe results

Standalone probes:

- `COORDINATED_FORGERY: BLOCKED`
- `EMPTY_LEDGER_ERASE_RESET: BLOCKED`
- `PNL_MARK_FORGERY: BLOCKED`
- `FUTURE_MARK: BLOCKED`
- `DIRECT_SQL_FILL: BLOCKED`
- `UNSORTED_BACKTEST: BLOCKED`
- `GLOBAL_STRATEGY_BACKTEST: BLOCKED`
- `WF_GLOBAL_FUTURE_LEAK: BLOCKED`
- `STRATEGY_ARTIFACT_MUTATION: BLOCKED`
- `KELLY_MUTATION_REPLAY: BLOCKED`
- `LIVE_EXECUTION: BLOCKED`

## H. Remaining findings

- CRITICAL/HIGH: none known under the documented trust model.
- MEDIUM: CI/action/development dependency pinning from audit #3 remains unchanged.
- Trust limitation: if an attacker can rewrite DB, local key, receipts, and the external trust anchor, repo-local immutable history is impossible.

## I. Explicit trust-boundary statement

Documented in `TRUST_MODEL.md`.

UPTM does **not** claim immutable history when all trust roots are locally rewritable. Nonempty ledger/mark state must match an independently protected external anchor. Without that anchor, verification fails closed.

## J. Status

READY FOR FOURTH ADVERSARIAL AUDIT — with the explicit caveat that the external trust anchor must be independently protected; this is not a production-readiness claim.