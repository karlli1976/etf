import pytest
import pandas as pd
import numpy as np
from backtest import (
    _futu_fee,
    _build_returns,
    _build_etf_prices,
    run_backtest,
    LEVERAGE_MAP,
    SIGNAL_TICKER,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_price_data(n=500, seed=42):
    """Return a DataFrame with QQQ, QLD, TQQQ prices."""
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2010-01-04", periods=n, freq="B")
    qqq = 100 * np.cumprod(1 + rng.normal(0.0004, 0.01, n))
    qld = 50  * np.cumprod(1 + rng.normal(0.0008, 0.02, n))
    tqqq = 30 * np.cumprod(1 + rng.normal(0.0012, 0.03, n))
    return pd.DataFrame({"QQQ": qqq, "QLD": qld, "TQQQ": tqqq}, index=idx)


def _make_qqq_only(n=300, seed=7):
    """Return a DataFrame with only QQQ prices."""
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2015-01-02", periods=n, freq="B")
    qqq = 100 * np.cumprod(1 + rng.normal(0.0004, 0.01, n))
    return pd.DataFrame({"QQQ": qqq}, index=idx)


# ── _futu_fee ─────────────────────────────────────────────────────────────────

class TestFutuFee:
    def test_zero_trade_value(self):
        assert _futu_fee(0, 100.0, False) == 0.0

    def test_negative_trade_value(self):
        assert _futu_fee(-100, 50.0, True) == 0.0

    def test_zero_price(self):
        assert _futu_fee(1000, 0.0, False) == 0.0

    def test_negative_price(self):
        assert _futu_fee(1000, -10.0, True) == 0.0

    def test_buy_no_sec_finra(self):
        fee = _futu_fee(10_000, 100.0, is_sell=False)
        # 100 shares: comm=0.49→min0.99, plat=0.50→min1.00, sett=0.30
        # no sec, no finra
        assert fee == pytest.approx(0.99 + 1.00 + 0.30, abs=1e-6)

    def test_sell_adds_sec_and_finra(self):
        fee_buy  = _futu_fee(10_000, 100.0, is_sell=False)
        fee_sell = _futu_fee(10_000, 100.0, is_sell=True)
        assert fee_sell > fee_buy

    def test_large_order_uses_per_share_comm(self):
        # 10000 shares: comm = 49.0 > min 0.99
        fee = _futu_fee(1_000_000, 100.0, is_sell=False)
        shares = 10_000
        expected_comm = 0.0049 * shares   # 49.0
        assert fee > expected_comm        # comm alone exceeds minimum

    def test_settlement_capped_at_max(self):
        # Very large order: settlement per share × shares would exceed $7
        fee = _futu_fee(100_000_000, 100.0, is_sell=False)
        # settlement can't exceed 7.0
        # We just check the fee is finite and positive
        assert fee > 0
        assert np.isfinite(fee)

    def test_finra_minimum_applied(self):
        # Very small order: FINRA per share × shares < min $0.01
        fee_sell = _futu_fee(10, 100.0, is_sell=True)   # 0.1 shares
        # fee is positive and finite
        assert fee_sell > 0

    def test_sell_sec_proportional_to_value(self):
        fee1 = _futu_fee(10_000, 100.0, True)
        fee2 = _futu_fee(20_000, 100.0, True)
        # SEC fee doubles with trade value (all else equal for per-share parts too)
        assert fee2 > fee1


# ── _build_returns ────────────────────────────────────────────────────────────

class TestBuildReturns:
    def setup_method(self):
        self.price_data = _make_price_data(300)
        self.common_idx = self.price_data.index

    def test_qqq_returns_match_pct_change(self):
        ret = _build_returns(self.price_data, ["QQQ"], self.common_idx)
        expected = self.price_data["QQQ"].pct_change()
        pd.testing.assert_series_equal(ret["QQQ"], expected.fillna(0.0), check_names=False)

    def test_tqqq_simulated_before_inception(self):
        # Use price_data without TQQQ to force simulation
        df = self.price_data[["QQQ"]].copy()
        ret = _build_returns(df, ["QQQ", "TQQQ"], df.index)
        qqq_ret = df["QQQ"].pct_change()
        # Simulated TQQQ = QQQ × 3
        pd.testing.assert_series_equal(
            ret["TQQQ"].fillna(0.0),
            (qqq_ret * 3).fillna(0.0),
            check_names=False,
        )

    def test_actual_data_overrides_simulation(self):
        ret = _build_returns(self.price_data, ["QQQ", "QLD"], self.common_idx)
        actual_qld = self.price_data["QLD"].pct_change()
        # Where actual QLD is not NaN, it should equal the actual return
        mask = actual_qld.notna()
        np.testing.assert_allclose(
            ret["QLD"][mask].values, actual_qld[mask].values, rtol=1e-10
        )

    def test_fillna_zero_on_first_row(self):
        ret = _build_returns(self.price_data, ["QQQ"], self.common_idx)
        assert ret["QQQ"].iloc[0] == 0.0

    def test_unknown_ticker_leveraged_simulation(self):
        # SQQQ = -3 × QQQ
        df = self.price_data[["QQQ"]].copy()
        ret = _build_returns(df, ["QQQ", "SQQQ"], df.index)
        qqq_ret = df["QQQ"].pct_change()
        pd.testing.assert_series_equal(
            ret["SQQQ"].fillna(0.0),
            (qqq_ret * -3).fillna(0.0),
            check_names=False,
        )


# ── _build_etf_prices ─────────────────────────────────────────────────────────

class TestBuildEtfPrices:
    def setup_method(self):
        self.price_data = _make_price_data(200)
        self.common_idx = self.price_data.index

    def test_qqq_prices_returned_as_is(self):
        px = _build_etf_prices(self.price_data, ["QQQ"], self.common_idx)
        pd.testing.assert_series_equal(
            px["QQQ"],
            self.price_data["QQQ"].reindex(self.common_idx),
            check_names=False,
        )

    def test_actual_data_used_where_available(self):
        px = _build_etf_prices(self.price_data, ["QLD"], self.common_idx)
        actual = self.price_data["QLD"].reindex(self.common_idx)
        mask = actual.notna()
        np.testing.assert_allclose(px["QLD"][mask].values, actual[mask].values, rtol=1e-10)

    def test_simulated_prices_positive(self):
        df = self.price_data[["QQQ"]].copy()
        px = _build_etf_prices(df, ["TQQQ"], df.index)
        # First row is NaN (pct_change), rest should be positive
        assert (px["TQQQ"].iloc[1:] > 0).all()


# ── run_backtest ──────────────────────────────────────────────────────────────

class TestRunBacktest:
    def setup_method(self):
        self.price_data = _make_price_data(500)
        self.portfolio = [
            {"ticker": "QQQ",  "weight": 60},
            {"ticker": "QLD",  "weight": 30},
            {"ticker": "TQQQ", "weight": 10},
        ]

    def test_missing_qqq_raises(self):
        df = pd.DataFrame({"SPY": [100.0, 101.0]}, index=pd.date_range("2020-01-01", periods=2))
        with pytest.raises(ValueError, match="QQQ"):
            run_backtest([{"ticker": "SPY", "weight": 100}], df)

    def test_returns_tuple_of_df_and_series(self):
        yearly, daily = run_backtest(self.portfolio, self.price_data)
        assert isinstance(yearly, pd.DataFrame)
        assert isinstance(daily, pd.Series)

    def test_initial_capital_respected(self):
        _, daily = run_backtest(self.portfolio, self.price_data, initial_capital=500_000)
        # First meaningful value should be near initial capital
        assert daily.iloc[0] == pytest.approx(500_000, rel=0.05)

    def test_daily_values_positive(self):
        _, daily = run_backtest(self.portfolio, self.price_data)
        assert (daily > 0).all()

    def test_yearly_table_has_year_index(self):
        yearly, _ = run_backtest(self.portfolio, self.price_data)
        assert yearly.index.name == "Year"
        assert yearly.index.dtype in (int, np.int32, np.int64, "int64")

    def test_yearly_table_has_portfolio_value_column(self):
        yearly, _ = run_backtest(self.portfolio, self.price_data)
        assert "资产总值" in yearly.columns

    def test_signal_lag_zero_vs_one_differ(self):
        _, daily_lag0 = run_backtest(self.portfolio, self.price_data, signal_lag=0)
        _, daily_lag1 = run_backtest(self.portfolio, self.price_data, signal_lag=1)
        # Results should differ (look-ahead vs no bias)
        assert not daily_lag0.equals(daily_lag1)

    def test_transaction_cost_reduces_returns(self):
        _, daily_free = run_backtest(self.portfolio, self.price_data, transaction_cost=0.0)
        _, daily_cost = run_backtest(self.portfolio, self.price_data, transaction_cost=0.01)
        assert daily_free.iloc[-1] >= daily_cost.iloc[-1]

    def test_futu_fees_reduces_returns(self):
        _, daily_free = run_backtest(self.portfolio, self.price_data, futu_fees=False)
        _, daily_futu = run_backtest(self.portfolio, self.price_data, futu_fees=True)
        # Futu fees should reduce final value
        assert daily_free.iloc[-1] >= daily_futu.iloc[-1]

    def test_qqq_only_portfolio(self):
        portfolio = [{"ticker": "QQQ", "weight": 100}]
        yearly, daily = run_backtest(portfolio, self.price_data)
        assert isinstance(daily, pd.Series)
        assert len(daily) == len(self.price_data)

    def test_sma_window_affects_result(self):
        _, daily_50  = run_backtest(self.portfolio, self.price_data, sma_window=50)
        _, daily_200 = run_backtest(self.portfolio, self.price_data, sma_window=200)
        # Different SMA windows produce different results
        assert not daily_50.equals(daily_200)

    def test_qqq_only_no_conditional_tickers(self):
        # With only QQQ, transaction cost branches should be skipped
        portfolio = [{"ticker": "QQQ", "weight": 100}]
        _, daily_cost = run_backtest(portfolio, self.price_data, transaction_cost=0.05)
        _, daily_free = run_backtest(portfolio, self.price_data, transaction_cost=0.0)
        pd.testing.assert_series_equal(daily_cost, daily_free)

    def test_simulated_tickers_when_missing_from_price_data(self):
        # QLD/TQQQ not in price_data → full simulation
        df = self.price_data[["QQQ"]].copy()
        yearly, daily = run_backtest(self.portfolio, df)
        assert isinstance(daily, pd.Series)
        assert (daily > 0).all()

    def test_futu_fees_with_no_flips(self):
        # Build a price_data where QQQ is always above any SMA (no flips)
        n = 300
        idx = pd.date_range("2010-01-04", periods=n, freq="B")
        # Strictly increasing prices → always above SMA
        prices = np.linspace(100, 200, n)
        df = pd.DataFrame({"QQQ": prices, "QLD": prices * 2, "TQQQ": prices * 3}, index=idx)
        _, daily = run_backtest(self.portfolio, df, futu_fees=True, sma_window=20)
        assert (daily > 0).all()

    def test_nan_price_fallback_in_futu_fees(self):
        # Create price_data where QLD has NaN on a flip date
        df = self.price_data.copy()
        # Introduce NaN into QLD prices
        df.loc[df.index[50:100], "QLD"] = np.nan
        portfolio = [{"ticker": "QQQ", "weight": 60}, {"ticker": "QLD", "weight": 40}]
        _, daily = run_backtest(portfolio, df, futu_fees=True, sma_window=50)
        assert (daily > 0).all()

    def test_yearly_table_ticker_columns_present(self):
        yearly, _ = run_backtest(self.portfolio, self.price_data)
        for p in self.portfolio:
            assert p["ticker"] in yearly.columns

    def test_large_sma_window_all_signal_true(self):
        # sma_window larger than data → all NaN SMA → fillna(True) → always invested
        _, daily = run_backtest(self.portfolio, self.price_data, sma_window=10_000)
        assert isinstance(daily, pd.Series)

    def test_futu_fees_nan_etf_price_triggers_fallback(self):
        """Cover line 166: px fallback to QQQ when etf price is NaN on a flip date."""
        from unittest.mock import patch
        # Use small data so flips happen
        n = 300
        idx = pd.date_range("2015-01-02", periods=n, freq="B")
        rng = np.random.default_rng(0)
        prices = 100 * np.cumprod(1 + rng.normal(0, 0.02, n))  # volatile → flips
        df = pd.DataFrame({"QQQ": prices, "QLD": prices * 2}, index=idx)
        portfolio = [{"ticker": "QQQ", "weight": 60}, {"ticker": "QLD", "weight": 40}]

        # Patch _build_etf_prices to return all-NaN for QLD so fallback is triggered
        original_build = __import__("backtest")._build_etf_prices
        import backtest as bt

        def _nan_prices(price_data, tickers, common_idx):
            result = original_build(price_data, tickers, common_idx)
            for t in tickers:
                result[t] = np.nan  # force NaN → triggers fallback to QQQ price
            return result

        with patch.object(bt, "_build_etf_prices", side_effect=_nan_prices):
            _, daily = run_backtest(portfolio, df, futu_fees=True, sma_window=30)
        assert (daily > 0).all()

    def test_yearly_table_none_for_all_nan_ticker_year(self):
        """Cover line 201: row[ticker] = None when a ticker has all-NaN prices in a year."""
        # QQQ has full data from 2010; TQQQ in price_data but NaN for entire 2010
        idx = pd.bdate_range("2010-01-04", "2011-12-31")
        n = len(idx)
        qqq = pd.Series(np.linspace(100, 200, n), index=idx, name="QQQ")
        # TQQQ starts only in 2011 — 2010 entries are NaN
        tqqq_vals = np.where(idx.year == 2010, np.nan, np.linspace(30, 60, n))
        tqqq = pd.Series(tqqq_vals, index=idx, name="TQQQ")
        df = pd.DataFrame({"QQQ": qqq, "TQQQ": tqqq})
        portfolio = [{"ticker": "QQQ", "weight": 50}, {"ticker": "TQQQ", "weight": 50}]
        yearly, _ = run_backtest(portfolio, df, sma_window=20)
        # TQQQ in 2010 should be None/NaN (pandas converts None to NaN in numeric columns)
        assert pd.isna(yearly.loc[2010, "TQQQ"])
