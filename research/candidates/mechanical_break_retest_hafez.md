# Omar Hafez mechanical break/retest candidate (UNVERIFIED)

Status: UNVERIFIED research candidate.

This artifact records a possible mechanical break/retest strategy candidate attributed to Omar Hafez. It does not define a tradable system, does not enable live trading, and does not assert profitability.

## No-prediction principle

The runner may only evaluate `P(outcome | state)` from information available at the decision timestamp. It must not encode clairvoyant labels, future bars, future session context, future volume profile, or post-entry outcomes in any decision-state feature.

## Pipeline

| Stage | Entry |
| --- | --- |
| CLAIM | Omar Hafez describes or is associated with a mechanical break/retest trading concept. |
| SOURCE | UNVERIFIED. No primary source text/video/transcript is embedded in this runner artifact. |
| FORMAL DEFINITION | UNDEFINED. Exact ES vs MES instrument choice, level construction, break condition, retest condition, reaction confirmation, session window, volume-profile rule, stop placement, target, slippage, fees, and risk sizing are not defined. |
| DATA REQUIREMENT | UNDEFINED pending formal definition. Minimum future-safe data would need timestamped OHLCV or tick data, instrument metadata, session calendar, volume-profile inputs as of decision time, spread/commission/slippage model, and order simulation rules. |
| TEST | UNDEFINED pending formal definition. Any test must be chronological, walk-forward or holdout based, and must forbid future data at decision timestamp. |
| RESULT | UNVERIFIED. No statistical significance, expectancy, profitability, drawdown, or robustness result is established. |
| STATUS | UNVERIFIED / NOT IMPLEMENTABLE until mechanical rules and primary sources are supplied. |

## Undefined terms

- ES vs MES: UNDEFINED
- Exact level definition: UNDEFINED
- Break definition: UNDEFINED
- Retest definition: UNDEFINED
- Reaction/confirmation definition: UNDEFINED
- Session definition: UNDEFINED
- Volume-profile definition: UNDEFINED
- Stop definition: UNDEFINED
- Target/exit definition: UNDEFINED
- Slippage and fee model: UNDEFINED
- Statistical significance: UNDEFINED
- Profitability: UNVERIFIED

## Control-plane constraints

- Do not invent missing mechanical rules.
- Do not convert this candidate into live trading.
- Do not treat any performance statement as verified.
- Do not accept tests that use information unavailable at the decision timestamp.
