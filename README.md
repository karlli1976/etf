# ETF Portfolio Strategy Backtester

A web-based Python application for researching ETF portfolio strategies through historical data backtesting.

[中文](README.zh.md)

## Core Assumptions

- Starting capital: $1,000,000 USD
- Data source: Yahoo Finance historical prices (Adjusted Close)
- Default portfolio: QQQ 60%, QLD 30%, TQQQ 10%

## Features

### 1. Portfolio Configuration

- Define ETF tickers and allocation weights via an editable table; rows can be added or removed
- Weights must sum to exactly 100% before a backtest can be run
- "Reset to Default" button restores the QQQ/QLD/TQQQ starting configuration

### 2. Historical Data Management

- On first run, full history is downloaded from Yahoo Finance and cached locally to `data/<TICKER>.csv`
- Subsequent runs fetch only incremental data (from the last cached date forward)
- Coverage: QQQ from 1999; QLD from June 2006; TQQQ from February 2010
- For periods before a leveraged ETF existed, returns are simulated as QQQ daily return × leverage multiple (QLD=2×, TQQQ=3×)

### 3. Strategy Logic

- **Anchor position**: QQQ is always held at its configured weight
- **Conditional positions**: all other ETFs (e.g. QLD, TQQQ) are held when QQQ closing price ≥ SMA(N), and liquidated to cash when below
- The SMA window N is user-configurable

### 4. Backtest Correction Parameters

These parameters control backtest realism and can be adjusted to compare results:

**Signal Lag**
- 0 days: signal and return are evaluated on the same day (look-ahead bias; more pronounced with shorter SMA windows)
- 1 day (recommended): yesterday's signal determines today's positions, matching real-world execution

**Transaction Cost Mode** (choose one)
- **Futu牛牛 per-trade calculation** (default): exact fees computed for each signal flip based on position size and ETF price
  - Commission: $0.0049/share, min $0.99/order
  - Platform fee: $0.005/share, min $1.00/order
  - Settlement: $0.003/share, max $7.00/order
  - SEC regulatory fee (sells only): 0.00278% of trade value
  - FINRA TAF (sells only): $0.000166/share, min $0.01/order
  - Effective cost: ~0.015%–0.03% per trade
- **Fixed rate**: manually specify a flat cost percentage per flip
- **No cost**: ignore all friction (theoretical upper bound)

**Leveraged ETF Simulation Warning**
- QLD (2×) simulation ignores ~−4%/year volatility decay
- TQQQ (3×) simulation ignores ~−12%/year volatility decay
- Actual early-period returns will be lower than simulated values

### 5. Manual Comparison Mode (Tab 1)

- Enter up to 5 SMA values simultaneously; values can be added or removed
- Runs all strategies in sequence on clicking "Run Backtest"
- Results:
  - **Yearly table**: each ETF's annual return (%) and portfolio value for each SMA strategy
  - **Equity curve chart**: daily portfolio value per SMA strategy, with QQQ buy-and-hold as a reference line
  - **Summary stats**: final portfolio value, CAGR, and max drawdown shown per strategy

### 6. SMA Range Sweep · Top 10 (Tab 2)

**Sweep Configuration**
- Set start SMA, end SMA, and step size (default: SMA 30→250, step 5, 45 strategies total)
- Sort Top 10 by: CAGR / Final portfolio value / Max drawdown (smallest)

**Full-period Results**
- Top 10 table: SMA window | Final value | CAGR | Max drawdown
- Global CAGR bar chart across all SMA values, with Top 10 highlighted in dark blue
- Real-time progress bar during scan

**Out-of-Sample Validation** (toggle)
- User sets a train/test split date (default: 2015-01-01)
- Every SMA is ranked by CAGR separately for the training period and the test period
- Comparison table shows where each training-period Top 10 ranked in the test period, with rank change (↑/↓)
- Scatter plot: training rank (X) vs. test rank (Y) with a diagonal reference line — points close to the diagonal indicate a robust strategy; points far from it suggest overfitting
