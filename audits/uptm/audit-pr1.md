# Adversarial audit report for PR #1 / branch `cursor/uptm-bootstrap-838f`

Scope inspected: actual source, tests, config, README, workflow, PR metadata for `onlinovosk-bit/onlinovosk-bit-uptm` PR #1.

Verification attempted:
- Read all source and tests under `uptm/`, `tests/`, config, workflow, lockfile.
- Read PR metadata with `gh pr view`.
- `uv run pytest -q` could not run because `uv` is not installed in this VM.
- `python3 -m pytest -q` could not run because `pytest` is not installed.
- `python3 -m uptm.cli smoke --config configs/default.toml --bars 12` ran successfully.
- Direct in-memory SQLite/Python adversarial probes were run for live refusal, kill switch, ledger tampering, manual PnL injection, and same-bar lookahead.

## Claim-by-claim verdict

| # | Claim | Verdict |
|---|---|---|
| 1 | Live trading is structurally impossible | Mostly verified for current code: no broker/exchange order integration exists and `LiveExecutionAdapter` always raises. Not architecturally sealed against future subclasses or alternate adapters. |
| 2 | Paper execution cannot accidentally reach real execution | Verified for current `PaperExecutionAdapter`: it only writes ledger events and does not call network/broker code. |
| 3 | Kill switch actually works | Partially verified: it blocks `PaperExecutionAdapter.place_order()` when enabled at construction. It is not global, persistent, dynamic, or enforced at ledger/API boundaries. |
| 4 | Ledger is append-only and tamper-resistant | Fails. Ordinary UPDATE/DELETE are blocked by triggers, but triggers can be dropped and manual INSERTs are unrestricted. No hash chain/signature/WORM guarantees. |
| 5 | PnL cannot be fabricated or manually injected | Fails. Manual ledger inserts or `TradeLedger.append()` can create arbitrary fills/profits that the auditor accepts. |
| 6 | Synthetic data cannot be mistaken for real market data | Partially verified only for generated bars and smoke output. No enforced provenance model prevents synthetic bars being passed into backtests/paper/auditor as if real. |
| 7 | Look-ahead/data leakage protections are real | Fails. Strategies receive the current full bar, including current close, then execute on that same close. |
| 8 | Walk-forward validation is correctly implemented | Fails/incomplete. Train windows are not used; strategy fitting/selection is absent; each test window resets capital and state. |
| 9 | Fees/slippage/liquidity modelling is actually applied | Partially verified in `Backtester` and paper slippage/fees. Paper loop ignores liquidity; valuation ignores liquidation costs; fees/slippage can be zero. |
| 10 | Fractional Kelly cannot bypass risk limits | Fails at system level. The Kelly proposal is bounded, but execution accepts arbitrary orders independent of the risk engine. |
| 11 | Auditor independently reconstructs results | Partially verified. It reconstructs from ledger/marks instead of strategy output, but trusts unauthenticated ledger rows and has weak mark/provenance validation. |
| 12 | Strategy lifecycle gates are enforced | Fails. Gates are local booleans in research output; paper loop ignores selected strategy/gate result. |
| 13 | Tests genuinely test claimed safety properties | Fails. Tests are shallow happy-path checks and miss adversarial bypasses. |
| 14 | Dependencies and security are acceptable | Mostly acceptable for dependencies, but CI actions are not SHA-pinned and test execution depends on unavailable `uv` in this environment. Runtime dependency footprint is minimal. |
| 15 | Architectural weaknesses, hidden stubs, fake implementations, TODOs | Significant scaffolding/stubs exist: prediction market adapter stub, unused data provenance table, fixed-rule “agents”, weak gates, no real lifecycle enforcement. |

---

## Findings

### 1. CRITICAL — Ledger append-only claim is bypassable by dropping triggers

- **File:** `uptm/db.py`
- **Exact component:** SQLite schema triggers `ledger_events_no_update`, `ledger_events_no_delete`
- **Problem:** Append-only is implemented only with normal SQLite triggers.
- **Why it matters:** Anyone with DB write access can drop the triggers, update/delete rows, or otherwise rewrite history. This is not tamper-resistant accounting.
- **Evidence:**
  ```python
  CREATE TRIGGER IF NOT EXISTS ledger_events_no_update
  BEFORE UPDATE ON ledger_events
  BEGIN
      SELECT RAISE(ABORT, 'ledger_events is append-only');
  END;
  ```
  ```python
  CREATE TRIGGER IF NOT EXISTS ledger_events_no_delete
  BEFORE DELETE ON ledger_events
  BEGIN
      SELECT RAISE(ABORT, 'ledger_events is append-only');
  END;
  ```
  Adversarial in-memory probe:
  ```text
  blocked UPDATE IntegrityError ledger_events is append-only
  blocked DELETE IntegrityError ledger_events is append-only
  price_after_trigger_drop 1.0
  ```
- **Recommended fix:** Add cryptographic hash chaining over canonicalized event contents, previous hash, monotonic sequence, and external anchoring/export. Restrict DB file write access. Detect missing/altered triggers during startup/audit. Consider immutable append log files or signed event journals instead of relying only on SQLite triggers.

### 2. CRITICAL — PnL can be manually fabricated by inserting fake fills

- **File:** `uptm/portfolio.py`
- **Exact component:** `snapshot_from_ledger()`
- **Problem:** The auditor/portfolio reconstruction trusts any row in `ledger_events` with `event_type='fill'`.
- **Why it matters:** A user or compromised process can insert fake sell fills and create arbitrary cash/PnL.
- **Evidence:**
  ```python
  for row in connection.execute("SELECT * FROM ledger_events ORDER BY id ASC"):
      if row["event_type"] != "fill":
          continue
      payload = json.loads(row["payload_json"])
      fee = float(payload.get("fee", 0.0))
      qty = float(row["quantity"])
      price = float(row["price"])
  ```
  Adversarial probe inserted a manual sell fill:
  ```text
  cash_after_manual_insert 999000748.0 positions {'BTC': -998.0}
  ```
- **Recommended fix:** Require signed fills from the execution layer, enforce event schemas and source identities, reject unauthenticated/manual events in audits, hash-chain all events, and distinguish correction events from execution fills.

### 3. HIGH — Ledger writer accepts arbitrary event types and values

- **File:** `uptm/ledger.py`
- **Exact component:** `LedgerEvent`, `TradeLedger.append()`
- **Problem:** `TradeLedger.append()` validates neither event type, side, quantity, price, timestamp, fee, nor currency.
- **Why it matters:** Even without raw SQL, normal application code can append nonsensical or fabricated fills that later affect PnL.
- **Evidence:**
  ```python
  @dataclass(frozen=True)
  class LedgerEvent:
      event_type: str
      symbol: str | None = None
      side: str | None = None
      quantity: float | None = None
      price: float | None = None
  ```
  ```python
  self.connection.execute(
      """
      INSERT INTO ledger_events (
          event_id, created_at, event_type, symbol, side, quantity, price,
          currency, strategy, run_id, payload_json
      )
  ```
- **Recommended fix:** Add strict event schemas per event type, reject invalid sides/negative quantities/negative prices/missing fee fields, and require events to originate from approved execution components.

### 4. HIGH — Look-ahead leakage exists in backtesting

- **File:** `uptm/backtest.py`
- **Exact component:** `Backtester.run()`
- **Problem:** The current bar is appended to `history`, strategy sees the current close, and the trade executes on that same close.
- **Why it matters:** Strategies can use information unavailable before execution. Backtest results can be materially inflated.
- **Evidence:**
  ```python
  for bar in bars:
      history.append(bar)
      target_signal = strategy.signal(history)
      close = float(bar["close"])
  ```
  Then same-bar fill:
  ```python
  fill_price = close * (1 + self.assumptions.slippage_bps / 10_000)
  ```
  Probe demonstrated a strategy reading `history[-1]["close"]` and filling at that same close:
  ```text
  trade_count 1 fill_price 101.0
  ```
- **Recommended fix:** Generate signals from data available strictly before the execution bar, e.g. signal on bar `t-1`, execute at bar `t` open/VWAP with slippage. Add tests with adversarial leaky strategies.

### 5. HIGH — Paper loop has the same current-bar leakage pattern

- **File:** `uptm/paper.py`
- **Exact component:** `run_paper_loop()`
- **Problem:** The paper strategy receives the current bar including close, then orders at that same close.
- **Why it matters:** Paper execution can validate strategies under impossible timing.
- **Evidence:**
  ```python
  history.append(bar)
  ledger.append_mark(symbol, str(bar["timestamp"]), float(bar["close"]), "USD", "paper_loop_input")
  signal = strategy.signal(history)
  ```
  ```python
  execution.place_order(Order(symbol, "buy", quantity, strategy=strategy.name), float(bar["close"]))
  ```
- **Recommended fix:** Separate signal timestamps from execution timestamps. Use prior-bar data for signal generation and next-bar execution.

### 6. HIGH — Walk-forward validation does not actually train, fit, or gate on the training window

- **File:** `uptm/validation.py`
- **Exact component:** `walk_forward_validate()`
- **Problem:** `train_size` only advances indices. The train slice is never passed to a trainer/optimizer or used to freeze parameters.
- **Why it matters:** This is not a real walk-forward validation framework for adaptive strategies. It can give false confidence.
- **Evidence:**
  ```python
  # v0 strategies are fixed-rule; train slice is retained for future optimizer hooks.
  result = Backtester(assumptions).run(
      bars=bars[train_end:test_end],
      strategy=strategy,
      symbol=symbol,
  )
  ```
- **Recommended fix:** Define a train/freeze/test interface. Fit parameters only on train data, instantiate a frozen strategy, and evaluate only on subsequent test data. Add tests verifying train/test separation.

### 7. HIGH — Strategy lifecycle gates are not enforced by paper execution

- **File:** `uptm/cli.py`, `uptm/agents/research.py`
- **Exact component:** `cmd_smoke()`, `ResearchPipeline`, `StrategyEvolutionAgent`
- **Problem:** The selected/accepted strategy is not used to control paper execution. The paper loop always runs `MovingAverageCrossStrategy()` regardless of gate result.
- **Why it matters:** A rejected strategy can still be paper-run; an accepted selected strategy may not be what is executed.
- **Evidence:**
  ```python
  selected = StrategyEvolutionAgent().select(evaluations)
  ```
  But paper loop ignores `selected`:
  ```python
  strategy=MovingAverageCrossStrategy(),
  ```
- **Recommended fix:** Make paper execution require an accepted immutable strategy artifact/id from the lifecycle pipeline. Refuse execution if no candidate passes gates. Test that rejected strategies cannot reach paper execution.

### 8. HIGH — Fractional Kelly limits do not protect execution

- **File:** `uptm/execution.py`, `uptm/risk.py`, `uptm/paper.py`
- **Exact component:** `PaperExecutionAdapter.place_order()`, `FractionalKellyRiskEngine`
- **Problem:** The Kelly engine only proposes sizing. `PaperExecutionAdapter` accepts arbitrary positive quantities and has no equity/risk cap.
- **Why it matters:** Any caller can bypass risk sizing and submit oversized paper orders.
- **Evidence:**
  ```python
  class FractionalKellyRiskEngine:
      """Produces sizing proposals only; execution safety remains outside the engine."""
  ```
  Execution only checks:
  ```python
  if order.quantity <= 0:
      raise ValueError("Order quantity must be positive.")
  if order.side not in {"buy", "sell"}:
      raise ValueError("Order side must be 'buy' or 'sell'.")
  ```
- **Recommended fix:** Enforce risk limits at the execution boundary. Require risk approval tokens/proposals, validate quantity/notional against current equity and positions, and reject orders not tied to a current risk decision.

### 9. MEDIUM — Kill switch is local/static, not a robust system-wide control

- **File:** `uptm/execution.py`, `uptm/paper.py`, `uptm/config.py`
- **Exact component:** `PaperExecutionAdapter.kill_switch_enabled`
- **Problem:** Kill switch is a constructor boolean. It is not persisted, centrally checked, dynamically reloaded, or enforced at ledger append.
- **Why it matters:** A running adapter created with `False` keeps trading if config changes. Other code paths can append fills directly.
- **Evidence:**
  ```python
  self.kill_switch_enabled = kill_switch_enabled
  ```
  ```python
  if self.kill_switch_enabled:
      raise KillSwitchEngagedError("Kill switch engaged; paper order refused.")
  ```
- **Recommended fix:** Store kill switch state in durable storage, check it immediately before every order and ledger fill append, and make direct fill appends require the same safety gate.

### 10. MEDIUM — Synthetic data labeling is advisory, not enforced

- **File:** `uptm/synthetic.py`, `uptm/backtest.py`, `uptm/paper.py`
- **Exact component:** `deterministic_synthetic_bars()`, `Backtester.run()`, `run_paper_loop()`
- **Problem:** Synthetic bars include `"synthetic": "true"`, and smoke output labels them, but consumers do not enforce or propagate provenance.
- **Why it matters:** Synthetic bars can be fed into the same backtest/paper paths as real bars without hard separation.
- **Evidence:**
  ```python
  "synthetic": "true",
  ```
  Backtester only has a generic note:
  ```python
  "Synthetic bars, if supplied, are generated test data and not market history."
  ```
  No check exists in `Backtester.run()` or `run_paper_loop()` to reject or segregate synthetic data.
- **Recommended fix:** Use typed market data objects with required provenance enum/source. Require explicit `allow_synthetic=True` in smoke/tests. Persist provenance through results and auditor inputs.

### 11. MEDIUM — Data provenance table exists but is unused

- **File:** `uptm/db.py`, `uptm/adapters/market_data.py`
- **Exact component:** `data_provenance` table and market data adapters
- **Problem:** Schema creates `data_provenance`, but adapters only write JSON cache files and never insert provenance rows.
- **Why it matters:** The database cannot prove which marks/backtests used real vs synthetic data or which source produced them.
- **Evidence:**
  ```python
  CREATE TABLE IF NOT EXISTS data_provenance (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      source TEXT NOT NULL,
      symbol TEXT NOT NULL,
      interval TEXT NOT NULL,
      fetched_at TEXT NOT NULL,
      cache_path TEXT NOT NULL,
      metadata_json TEXT NOT NULL
  );
  ```
  Adapter cache write:
  ```python
  cache_path.write_text(json.dumps(payload, indent=2, sort_keys=True))
  ```
  No adapter inserts into `data_provenance`.
- **Recommended fix:** Persist provenance records on every data fetch and link backtest/audit results to immutable data snapshot IDs.

### 12. MEDIUM — Backtest cost/liquidity model is incomplete

- **File:** `uptm/backtest.py`
- **Exact component:** `Backtester.run()`
- **Problem:** Fees/slippage/participation are applied on trades, but open positions are valued at raw last close with no exit slippage/fees. Participation uses bar volume directly and allows zero-cost assumptions.
- **Why it matters:** Ending equity can overstate realizable value, especially for illiquid assets or open positions.
- **Evidence:**
  ```python
  ending_equity = cash + position * last_close
  ```
  Validation allows zero fees/slippage:
  ```python
  if assumptions.fee_bps < 0 or assumptions.slippage_bps < 0:
      raise ValueError("Fees and slippage must be non-negative.")
  ```
- **Recommended fix:** Mark open positions using liquidation assumptions or report both mark-to-market and liquidation equity. Enforce minimum cost assumptions for promotion gates.

### 13. MEDIUM — Paper execution ignores liquidity participation entirely

- **File:** `uptm/paper.py`, `uptm/execution.py`
- **Exact component:** `run_paper_loop()`, `PaperExecutionAdapter`
- **Problem:** Backtest has a max participation rate, but paper order placement has no volume/liquidity limit.
- **Why it matters:** Paper results can diverge from backtest assumptions and permit impossible fills.
- **Evidence:**
  ```python
  execution.place_order(Order(symbol, "buy", quantity, strategy=strategy.name), float(bar["close"]))
  ```
  `PaperExecutionAdapter.place_order()` computes slippage/fee only; no volume input or participation check exists.
- **Recommended fix:** Include volume/liquidity constraints in paper execution or route paper orders through a shared execution simulator.

### 14. MEDIUM — Auditor reconstruction is independent of strategy reports but not independently trustworthy

- **File:** `uptm/auditor.py`, `uptm/portfolio.py`
- **Exact component:** `PerformanceAuditor.audit()`, `snapshot_from_ledger()`
- **Problem:** Auditor reconstructs from ledger and marks, but it does not validate event authenticity, provenance, schema, monotonic timestamps, position constraints, or mark source quality.
- **Why it matters:** It independently reconstructs bad data, not necessarily true performance.
- **Evidence:**
  ```python
  snapshot = snapshot_from_ledger(
      self.connection,
      starting_cash=starting_cash,
      base_currency=base_currency,
      fx_usd_eur=fx_usd_eur,
  )
  ```
  Warning logic only checks negative cash:
  ```python
  if snapshot.cash < 0:
      warnings.append("cash balance is negative in paper ledger")
  ```
- **Recommended fix:** Auditor should verify ledger hash chain, event schema, source signatures, data provenance, mark freshness/source, no impossible positions, and reconcile execution fills to orders.

### 15. MEDIUM — Latest mark selection can be ambiguous across sources

- **File:** `uptm/portfolio.py`
- **Exact component:** `latest_marks` query in `snapshot_from_ledger()`
- **Problem:** The latest mark query groups by symbol and timestamp only, but `market_marks` uniqueness includes source. Multiple sources at the same timestamp can produce multiple rows; dictionary selection is arbitrary.
- **Why it matters:** Equity can depend on nondeterministic source ordering.
- **Evidence:**
  ```python
  SELECT symbol, MAX(marked_at) AS marked_at
  FROM market_marks
  GROUP BY symbol
  ```
  Then:
  ```python
  latest_marks = {
      row["symbol"]: row
      for row in connection.execute(...)
  }
  ```
- **Recommended fix:** Require a selected mark source per audit, deterministic source priority, or reject ambiguous marks.

### 16. MEDIUM — Tests do not cover adversarial safety properties

- **File:** `tests/test_safety.py`, `tests/test_ledger.py`, `tests/test_backtest.py`, `tests/test_risk.py`
- **Exact component:** entire test suite
- **Problem:** Tests cover basic positive/refusal cases but not bypasses.
- **Why it matters:** The claimed guarantees are stronger than the tests.
- **Evidence:**
  Kill switch test only checks constructor flag:
  ```python
  adapter = PaperExecutionAdapter(..., kill_switch_enabled=True)
  with pytest.raises(KillSwitchEngagedError):
      adapter.place_order(...)
  ```
  Ledger test only checks ordinary UPDATE/DELETE:
  ```python
  connection.execute("UPDATE ledger_events SET price = 1")
  connection.execute("DELETE FROM ledger_events")
  ```
  No tests for trigger dropping, manual inserts, auditor authenticity, lookahead strategies, walk-forward train/test separation, lifecycle enforcement, direct execution risk bypass, or synthetic/real provenance separation.
- **Recommended fix:** Add adversarial tests for each safety claim and require them in CI.

### 17. LOW — Live trading disabled for current implementation, but not structurally sealed

- **File:** `uptm/execution.py`, `uptm/config.py`
- **Exact component:** `LiveExecutionAdapter`, `ExecutionInterface`, `UPTMConfig.validate()`
- **Problem:** Current live adapter always raises and config rejects `live_trading=True`, but the interface allows arbitrary future execution implementations.
- **Why it matters:** “Structurally impossible” is too strong unless adapter construction and execution routing are controlled centrally.
- **Evidence:**
  ```python
  class LiveExecutionAdapter(ExecutionInterface):
      def place_order(...):
          raise LiveTradingDisabledError("Live trading is hard-disabled in UPTM v0.")
  ```
  But:
  ```python
  class ExecutionInterface:
      def place_order(...):
          raise NotImplementedError
  ```
- **Recommended fix:** Keep current hard-disabled live adapter, but add a central execution factory that only returns paper execution in v0 and test that no live-capable adapter can be configured.

### 18. LOW — CI supply-chain pinning is weak

- **File:** `.github/workflows/tests.yml`
- **Exact component:** GitHub Actions workflow
- **Problem:** Actions are pinned to major versions, not commit SHAs.
- **Why it matters:** Major tags can move. For high-integrity trading/audit infrastructure, CI supply chain should be pinned.
- **Evidence:**
  ```yaml
  - uses: actions/checkout@v4
  - uses: astral-sh/setup-uv@v4
  ```
- **Recommended fix:** Pin GitHub Actions to full commit SHAs and enable dependency/security scanning.

### 19. LOW — Public market adapters are thin scaffolds with limited validation

- **File:** `uptm/adapters/market_data.py`
- **Exact component:** `CoinGeckoCryptoAdapter`, `StooqEquityAdapter`, `PredictionMarketAdapterStub`
- **Problem:** Adapters fetch public data and cache JSON but have little validation; prediction market adapter is intentionally stubbed.
- **Why it matters:** This is acceptable for scaffolding but not enough for serious market-data provenance or production research.
- **Evidence:**
  ```python
  class PredictionMarketAdapterStub:
      source = "prediction_market_stub"

      def fetch_ohlc(...):
          raise MarketDataUnavailable(
              "Prediction/event market adapter is stubbed in v0; configure a real provider and API key first."
          )
  ```
- **Recommended fix:** Treat adapters as non-production. Add schema validation, source metadata persistence, checksums, data quality checks, and explicit unsupported-provider failures.

---

## Positive controls actually verified

These are verified, but narrow:

- `UPTMConfig.validate()` rejects `live_trading=True`.
  ```python
  if self.safety.live_trading:
      raise ConfigurationError("LIVE_TRADING is hard-disabled in UPTM v0.")
  ```
- `LiveExecutionAdapter.place_order()` always raises.
  ```python
  raise LiveTradingDisabledError("Live trading is hard-disabled in UPTM v0.")
  ```
- `PaperExecutionAdapter.place_order()` does not call broker/network code and writes a ledger fill only.
- `PaperExecutionAdapter` blocks orders when constructed with `kill_switch_enabled=True`.
- `Backtester` applies fee/slippage/participation constraints on executed trades.
- Runtime dependency footprint is minimal: `pyproject.toml` has no runtime dependencies and only `pytest` in dev dependencies.

## Test execution notes

- Advertised command failed in this environment:
  ```text
  uv: command not found
  ```
- Direct pytest failed:
  ```text
  /usr/bin/python3: No module named pytest
  ```
- Smoke command succeeded with `python3 -m uptm.cli smoke --config configs/default.toml --bars 12`.
- Smoke output selected `buy_and_hold` as accepted for paper while the actual paper loop executed `MovingAverageCrossStrategy()`, reinforcing the lifecycle enforcement finding.

## Merge recommendation

**DO NOT MERGE.**

Justification: the PR is acceptable only as a clearly labeled toy scaffold, but it makes or implies stronger safety/audit claims than the implementation supports. Critical accounting claims fail: the ledger is not tamper-resistant, PnL can be manually fabricated, and the auditor trusts unauthenticated rows. Backtesting has same-bar lookahead leakage, walk-forward validation is incomplete, lifecycle gates are not enforced, and risk limits can be bypassed at the execution boundary. The tests do not exercise the adversarial properties being claimed.