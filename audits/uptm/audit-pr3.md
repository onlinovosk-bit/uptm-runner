A. ORIGINAL PR #2 VULNERABILITIES — each PASS / EXPLOITABLE

1. Ledger immutability — EXPLOITABLE
   - SQL-only row mutation/replay is mostly detected, but full erasure to an empty ledger succeeds after trigger drop/restore and anchor reset.
   - Coordinated DB + authority key + receipt replacement fully forges history and passes verification.

2. Fill/PnL authenticity — EXPLOITABLE
   - Unauthenticated manual fills are rejected.
   - PnL is forgeable through unauthenticated `market_marks`.
   - Coordinated key replacement lets attacker mint valid fill HMACs.

3. Chronology/look-ahead — EXPLOITABLE
   - Bar ordering/future timestamps are checked.
   - Future-dated marks are accepted for valuation.
   - Strategy code can leak future/global data.

4. Walk-forward temporal isolation — EXPLOITABLE
   - Index slicing is correct for honest strategies.
   - Arbitrary strategy code can access global/full-series future data.

5. Strategy artifact lifecycle/substitution — EXPLOITABLE
   - Instance state/class source substitutions are caught.
   - Behavior depending on mutable module/global state is not captured by artifact hashing.

6. Kelly/final exposure — PASS, with caveat
   - Paper execution requires a proposal and checks final exposure including fee/slippage.
   - Missing, NaN, infinite, oversized, zero, negative, and unapproved proposals are rejected by existing code/tests.
   - Caveat: proposals are plain dataclasses with no freshness/source binding.

7. Paper/live isolation — PASS
   - `LiveExecutionAdapter.place_order()` always raises.
   - config rejects `live_trading=true`.
   - No env/CLI live bypass found.

8. Adversarial test integrity — EXPLOITABLE / INCOMPLETE
   - Tests pass, but miss the successful empty-ledger rewrite, DB+key+receipt coordinated forgery, mark/PnL forgery, global-state artifact bypass, and global future leak.

B. NEW VULNERABILITIES

1. CRITICAL — Coordinated DB + key + receipt forgery accepted
   - File/function: `uptm/ledger.py`, `verify_ledger_integrity`, `_load_existing_authority_key`, `_verify_receipts`
   - Attack: replaced SQLite contents, `.authority_key`, and `.receipts` with a fraudulent self-consistent history.
   - Succeeded?: Yes. Probe output: `COORDINATED_FORGERY_SUCCEEDED 10000740.0 {'BTC': -10.0}`
   - Why: all trust anchors live next to the DB and are attacker-rewritable under the stated coordinated filesystem-write threat.
   - Existing coverage: only tests SQL rewrite while keeping original key/receipt.
   - Missing coverage: coordinated DB+key+receipt replacement.
   - Remediation: move authority/anchor material outside the mutable ledger directory; use external append-only/WORM storage, remote timestamping, KMS/HSM-backed signing, or independently persisted signed checkpoints.

2. HIGH — Full ledger erasure to “empty” passes verification
   - File/function: `uptm/ledger.py`, `verify_ledger_integrity`, `_verify_receipts`
   - Attack: drop delete trigger, delete all `ledger_events`, set `ledger_integrity` to count `0` and tip `NULL`, recreate trigger.
   - Succeeded?: Yes. Probe output: `EMPTY_REWRITE_SUCCEEDED`
   - Why: `_verify_receipts()` returns early when `rows` is empty and does not reject stale receipts.
   - Existing coverage: tests deleting only the last row from a non-empty ledger.
   - Missing coverage: complete deletion/reset-to-empty attack.
   - Remediation: if a receipt journal exists, require it to match zero rows exactly; persist monotonic event count outside SQLite; reject anchor rollback.

3. HIGH — PnL/equity forgeable through unauthenticated market marks
   - File/function: `uptm/portfolio.py`, `snapshot_from_ledger`; `uptm/ledger.py`, `append_mark`
   - Attack: insert future high-price `market_marks` row.
   - Succeeded?: Yes. Probe output: `PNL_MARK_FORGERY_SUCCEEDED 650.0 1000000649.0`
   - Why: ledger integrity is verified, but marks are mutable, unauthenticated, unhashed, and future timestamps are accepted.
   - Existing coverage: none for mark tampering.
   - Missing coverage: mark UPDATE/DELETE/INSERT/future/replay/provenance attacks.
   - Remediation: make marks append-only, hash/authenticate them, validate chronology/future timestamps, bind marks to data provenance, and audit latest mark selection.

4. HIGH — Approved strategy artifact can change behavior via global mutable state
   - File/function: `uptm/strategies.py`, `_strategy_content_hash`, `verify_strategy_artifact`
   - Attack: approve strategy while global flag is false, mutate global flag, verify same artifact, changed signal behavior.
   - Succeeded?: Yes. Probe output: `ARTIFACT_GLOBAL_MUTATION_SUCCEEDED 1`
   - Why: artifact hash includes class source and instance `__dict__`, not referenced globals/imported dependency state.
   - Existing coverage: catches instance mutation and class substitution.
   - Missing coverage: globals, closures, monkeypatch/import dependency mutation.
   - Remediation: restrict strategies to pure serializable configs plus reviewed code version/SHA; run in isolated immutable environment; include dependency/code bundle digest.

5. HIGH — Walk-forward isolation bypass via global future data
   - File/function: `uptm/validation.py`, `_fit_and_freeze_strategy`; `uptm/backtest.py`, `Backtester.run`
   - Attack: strategy reads global full bar series during test signal.
   - Succeeded?: Yes. Probe output: `WF_GLOBAL_FUTURE_LEAK_TRADES 1 2024-01-01T04:00:00+00:00`
   - Why: slicing is correct, but arbitrary strategy code can access external future state.
   - Existing coverage: verifies honest `fit()` receives train/validation only.
   - Missing coverage: global/preloaded/full-series leakage.
   - Remediation: sandbox strategies; pass only immutable history; prevent module/global data access for promoted strategies; require pure strategy interface.

6. MEDIUM — CI and toolchain are not SHA-pinned
   - File/function: `.github/workflows/tests.yml`
   - Attack: dependency/action supply-chain substitution.
   - Succeeded?: Not directly probed.
   - Why: uses `actions/checkout@v4`, `astral-sh/setup-uv@v4`, and `pytest>=8.0.0`.
   - Existing coverage: none.
   - Missing coverage: pinned action/dependency integrity.
   - Remediation: pin GitHub Actions to commit SHAs and lock dev dependencies.

C. TRUST-BOUNDARY ANALYSIS (DB+key+receipt)

The current design does not survive the explicit coordinated filesystem-write threat. The authority key and receipt journal are derived from and stored adjacent to the SQLite DB path:

- DB: `uptm.sqlite3`
- key: `uptm.sqlite3.authority_key`
- receipts: `uptm.sqlite3.receipts`

If an attacker can write all three, they can create a new key, generate valid fill HMACs, recompute event hashes, write a matching anchor, generate matching receipt HMACs, restore expected triggers, and pass `verify_ledger_integrity()`.

This is CRITICAL, not MEDIUM, because the supposed independent trust anchors collapse into the same filesystem trust boundary. The verifier proves only local self-consistency, not historical authenticity.

D. ADVERSARIAL TEST QUALITY

- Test suite result: `25 passed`.
- Installed pytest only into `/tmp/uptm-pytest-target`; repository git status remained clean.
- Tests are useful but insufficient.
- They cover:
  - trigger missing/altered detection
  - hash mismatch detection
  - unauthenticated direct fills
  - partial SQL replay
  - basic chronology
  - basic walk-forward slicing
  - basic artifact mutation/substitution
  - Kelly final exposure checks
  - live adapter refusal
- They miss:
  - coordinated DB+key+receipt replacement
  - full deletion/reset-to-empty
  - unauthenticated market mark PnL forgery
  - global-state artifact mutation
  - global full-series walk-forward leakage
  - CI/action/dependency pinning
  - external anchoring or rollback protection

E. COMPLETE FINDINGS

1. CRITICAL: coordinated DB+key+receipt fraudulent history accepted.
2. HIGH: full ledger erase/reset to empty accepted.
3. HIGH: PnL forgeable with unauthenticated/future market marks.
4. HIGH: strategy artifact approval bypass via global mutable state.
5. HIGH: walk-forward temporal isolation bypass via global future state.
6. MEDIUM: CI/actions/dev deps are not SHA/fully pinned.
7. PASS: SQL-only unauthenticated fill insertion is rejected.
8. PASS: direct row mutation/replay is generally detected when receipts/key are intact.
9. PASS: backtest/paper loops use prior history and current open for honest strategies.
10. PASS: Kelly final exposure checks include fee/slippage and reject malformed proposals.
11. PASS: live trading path is hard-disabled in current code.

F. FINAL DECISION: BLOCKED — NEW FIX PR REQUIRED

Do not merge based on the passing suite. PR #3 materially improves several local checks, but the ledger trust boundary, PnL authenticity, artifact lifecycle, and walk-forward isolation still have exploitable adversarial failures. No PR was created or updated.