# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the app

```bash
.venv/bin/streamlit run app.py --server.headless true
```

The app runs on http://localhost:8501 by default. The `.venv` is Python 3.9.

## Architecture

Three source files, no framework beyond Streamlit:

- **`data_manager.py`** — Yahoo Finance data via `yfinance`. First run downloads full history and caches to `data/<TICKER>.csv`. Subsequent runs do incremental updates (only fetches dates after the last cached row). Returns `pd.Series` of adjusted close prices per ticker.

- **`backtest.py`** — Fully vectorized backtest engine. Key entry point: `run_backtest(portfolio, price_data, sma_window, signal_lag, transaction_cost, futu_fees)`. Returns `(yearly_df, daily_values)`. Critical design decisions:
  - `signal_lag=1` is the realistic default (uses yesterday's signal for today's trade); `lag=0` has look-ahead bias that artificially inflates short-SMA results.
  - When `futu_fees=True`, iterates only over signal-flip days to compute exact per-share Futu fees (`_futu_fee()`); otherwise uses a flat `transaction_cost` fraction.
  - Leveraged ETFs (QLD=2×, TQQQ=3×) are simulated for periods before their inception using `QQQ_daily_return × leverage`. This **overstates** real returns because it ignores volatility decay (~4%/yr QLD, ~12%/yr TQQQ).
  - `SIGNAL_TICKER = "QQQ"` is hardcoded as the always-held anchor and SMA signal source.

- **`app.py`** — Streamlit UI. All shared state (portfolio rows, SMA windows list) lives in `st.session_state`. Structure:
  - **Portfolio editor** (shared, top) — dynamic rows with add/delete
  - **Bias correction parameters** (shared) — `signal_lag`, fee mode (Futu / fixed % / none)
  - **Tab 1: Manual comparison** — up to 5 SMA values side-by-side; shows yearly table, line chart, summary stats
  - **Tab 2: SMA range sweep** — scans a range (e.g. SMA30→250 step 5); shows Top 10 table + CAGR bar chart; optional out-of-sample split with train/test rank comparison table and scatter plot

## Futu牛牛 fee structure (as implemented)

| Item | Rate | When |
|------|------|------|
| Commission | $0.0049/share, min $0.99 | buy & sell |
| Platform fee | $0.005/share, min $1.00 | buy & sell |
| Settlement | $0.003/share, max $7.00 | buy & sell |
| SEC fee | $0.0000278 × trade value | sell only |
| FINRA TAF | $0.000166/share, min $0.01 | sell only |

## Adding new ETFs or leverage mappings

Add to `LEVERAGE_MAP` in `backtest.py` for correct simulation and Futu fee price proxies. Tickers not in the map default to 1× leverage for simulation.
