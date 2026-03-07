"""
Backtest engine for ETF portfolio strategy.

Strategy rules:
- QQQ is always held (its configured weight).
- All other ETFs are held only when the signal is ON; otherwise those allocations go to cash.
- Signal: QQQ close >= SMA(sma_window).
- signal_lag: 0 = look-ahead bias (unrealistic); 1 = realistic, recommended.
- For periods before an ETF existed, daily returns are simulated as QQQ_return × leverage.
  Note: this ignores real leveraged-ETF volatility decay (~4%/yr for QLD, ~12%/yr for TQQQ).

Futu牛牛 US stock fee schedule (2024/2025):
  Commission    : $0.0049/share, min $0.99/order   (buy & sell)
  Platform fee  : $0.005/share,  min $1.00/order   (buy & sell)
  Settlement    : $0.003/share,  max $7.00/order   (buy & sell)
  SEC fee       : $0.0000278 × trade value          (sell only)
  FINRA TAF     : $0.000166/share, min $0.01/order  (sell only)
"""

import pandas as pd

LEVERAGE_MAP = {
    "QQQ": 1,
    "QLD": 2,
    "TQQQ": 3,
    "SQQQ": -3,
    "UDOW": 3,
    "SDOW": -3,
}

SIGNAL_TICKER = "QQQ"
SMA_WINDOW = 200

# ── Futu fee constants ────────────────────────────────────────────────────────
_FUTU_COMM_PER_SHARE   = 0.0049
_FUTU_COMM_MIN         = 0.99
_FUTU_PLAT_PER_SHARE   = 0.005
_FUTU_PLAT_MIN         = 1.00
_FUTU_SETT_PER_SHARE   = 0.003
_FUTU_SETT_MAX         = 7.00
_FUTU_SEC_RATE         = 0.0000278   # sell only
_FUTU_FINRA_PER_SHARE  = 0.000166   # sell only
_FUTU_FINRA_MIN        = 0.01       # sell only


def _futu_fee(trade_value: float, price_per_share: float, is_sell: bool) -> float:
    """Return total Futu fee in USD for a single order."""
    if trade_value <= 0 or price_per_share <= 0:
        return 0.0
    shares = trade_value / price_per_share
    commission = max(_FUTU_COMM_PER_SHARE * shares, _FUTU_COMM_MIN)
    platform   = max(_FUTU_PLAT_PER_SHARE * shares, _FUTU_PLAT_MIN)
    settlement = min(_FUTU_SETT_PER_SHARE * shares, _FUTU_SETT_MAX)
    sec        = _FUTU_SEC_RATE * trade_value if is_sell else 0.0
    finra      = max(_FUTU_FINRA_PER_SHARE * shares, _FUTU_FINRA_MIN) if is_sell else 0.0
    return commission + platform + settlement + sec + finra


def _build_returns(price_data: pd.DataFrame, tickers: list[str], common_idx) -> pd.DataFrame:
    qqq_ret = price_data[SIGNAL_TICKER].reindex(common_idx).pct_change()
    out = {}
    for ticker in tickers:
        if ticker in price_data.columns:
            actual = price_data[ticker].reindex(common_idx).pct_change()
        else:
            actual = pd.Series(dtype=float, index=common_idx)
        if ticker == SIGNAL_TICKER:
            out[ticker] = actual
        else:
            lev = LEVERAGE_MAP.get(ticker, 1)
            simulated = qqq_ret * lev
            combined = simulated.copy()
            combined[actual.notna()] = actual[actual.notna()]
            out[ticker] = combined
    return pd.DataFrame(out, index=common_idx).fillna(0.0)


def _build_etf_prices(price_data: pd.DataFrame, tickers: list[str], common_idx) -> pd.DataFrame:
    """
    Return price series for each ticker.
    For simulated tickers (before inception), reconstruct from QQQ cumulative returns × leverage,
    anchored to QQQ's initial price so per-share fee math is realistic.
    """
    qqq_px = price_data[SIGNAL_TICKER].reindex(common_idx)
    qqq_ret = qqq_px.pct_change()
    out = {}
    for ticker in tickers:
        if ticker in price_data.columns:
            actual = price_data[ticker].reindex(common_idx)
        else:
            actual = pd.Series(dtype=float, index=common_idx)
        lev = LEVERAGE_MAP.get(ticker, 1)
        # Reconstruct synthetic price anchored to QQQ price × leverage
        sim_ret = qqq_ret * lev
        sim_px = (1 + sim_ret).cumprod() * qqq_px.iloc[0] * lev
        combined = sim_px.copy()
        mask = actual.notna()
        combined[mask] = actual[mask]
        out[ticker] = combined
    return pd.DataFrame(out, index=common_idx)


def run_backtest(
    portfolio: list[dict],
    price_data: pd.DataFrame,
    initial_capital: float = 1_000_000,
    sma_window: int = SMA_WINDOW,
    signal_lag: int = 1,
    transaction_cost: float = 0.0,
    futu_fees: bool = False,
) -> tuple[pd.DataFrame, pd.Series]:
    """
    Args:
        portfolio:        list of {"ticker": str, "weight": float (0-100)}
        price_data:       DataFrame of adjusted close prices
        sma_window:       SMA period for QQQ signal
        signal_lag:       Days to lag signal (1 = realistic, 0 = look-ahead bias)
        transaction_cost: Simple cost per flip as fraction of conditional position.
                          Ignored when futu_fees=True.
        futu_fees:        If True, compute exact Futu牛牛 per-share fees for each flip.
    Returns:
        (yearly_table, daily_portfolio_values)
    """
    if SIGNAL_TICKER not in price_data.columns:
        raise ValueError(f"{SIGNAL_TICKER} is required.")

    tickers = [p["ticker"] for p in portfolio]
    weights = {p["ticker"]: p["weight"] / 100.0 for p in portfolio}

    qqq_prices = price_data[SIGNAL_TICKER].dropna()
    common_idx = qqq_prices.index

    sma = qqq_prices.rolling(sma_window).mean()

    raw_signal = (qqq_prices >= sma).fillna(True)
    signal = raw_signal.shift(signal_lag).fillna(True) if signal_lag > 0 else raw_signal

    returns = _build_returns(price_data, tickers, common_idx)
    anchor = SIGNAL_TICKER
    conditional_tickers = [t for t in tickers if t != anchor]

    # ── Vectorised portfolio return (pre-fee) ─────────────────────────────────
    port_ret = weights.get(anchor, 0.0) * returns[anchor]
    for t in conditional_tickers:
        port_ret += weights.get(t, 0.0) * returns[t] * signal.astype(float)

    # ── Transaction costs ─────────────────────────────────────────────────────
    if conditional_tickers:
        flipped = signal.astype(int).diff().abs().fillna(0).astype(bool)
        flip_dates = common_idx[flipped]

        if futu_fees and len(flip_dates) > 0:
            # Compute approximate running portfolio value (pre-fee) for trade sizing
            approx_values = initial_capital * (1 + port_ret).cumprod().shift(1).fillna(initial_capital)
            etf_px = _build_etf_prices(price_data, conditional_tickers, common_idx)

            fee_series = pd.Series(0.0, index=common_idx)
            for date in flip_dates:
                pv = approx_values.loc[date]
                is_sell = not signal.loc[date]  # flipping OFF = selling conditional ETFs
                total_fee = 0.0
                for t in conditional_tickers:
                    trade_val = pv * weights.get(t, 0.0)
                    px = etf_px.loc[date, t]
                    if pd.isna(px) or px <= 0:
                        px = qqq_prices.loc[date]  # fallback
                    total_fee += _futu_fee(trade_val, px, is_sell)
                    # Also charge for the opposite leg (buy back or sell):
                    # one leg per flip, the other leg was charged at the previous flip.
                fee_series.loc[date] = total_fee / pv if pv > 0 else 0.0

            port_ret -= fee_series

        elif transaction_cost > 0:
            cond_weight = sum(weights.get(t, 0.0) for t in conditional_tickers)
            port_ret -= flipped.astype(float) * cond_weight * transaction_cost

    portfolio_values = initial_capital * (1 + port_ret).cumprod()

    # ── Yearly table ──────────────────────────────────────────────────────────
    etf_prices = {}
    for ticker in tickers:
        if ticker in price_data.columns:
            etf_prices[ticker] = price_data[ticker].reindex(common_idx)
        else:
            lev = LEVERAGE_MAP.get(ticker, 1)
            sim_ret = price_data[SIGNAL_TICKER].reindex(common_idx).pct_change() * lev
            etf_prices[ticker] = (1 + sim_ret).cumprod() * 100
    etf_price_df = pd.DataFrame(etf_prices, index=common_idx)

    rows = []
    prev_end = {}
    for year in sorted(common_idx.year.unique()):
        yd = common_idx[common_idx.year == year]
        if len(yd) == 0:
            continue
        row = {"Year": year}
        for ticker in tickers:
            yp = etf_price_df[ticker].reindex(yd).dropna()
            if yp.empty:
                row[ticker] = None
            else:
                start = prev_end.get(ticker, yp.iloc[0])
                row[ticker] = (yp.iloc[-1] / start - 1) * 100
                prev_end[ticker] = yp.iloc[-1]
        yv = portfolio_values.reindex(yd).dropna()
        row["资产总值"] = yv.iloc[-1] if not yv.empty else None
        rows.append(row)

    yearly_df = pd.DataFrame(rows).set_index("Year")
    return yearly_df, portfolio_values
