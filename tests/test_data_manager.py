import os
import pandas as pd
import numpy as np
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_series(ticker="QQQ", n=10, end_days_ago=0):
    end = datetime.now().date() - timedelta(days=end_days_ago)
    idx = pd.bdate_range(end=end, periods=n)
    data = np.linspace(100, 110, n)
    s = pd.Series(data, index=pd.to_datetime(idx).tz_localize(None), name=ticker)
    return s


def _make_yf_df(ticker="QQQ", n=5):
    """Simulate a yfinance download result (single-level columns)."""
    idx = pd.bdate_range(end=datetime.now().date(), periods=n, tz="UTC")
    close = pd.Series(np.linspace(100, 105, n), index=idx, name=ticker)
    return pd.DataFrame({"Close": close})


# ── _download ─────────────────────────────────────────────────────────────────

class TestDownload:
    def _run(self, ticker, start=None, mock_df=None):
        import data_manager
        if mock_df is None:
            mock_df = _make_yf_df(ticker)

        with patch("data_manager.yf.download", return_value=mock_df) as mock:
            result = data_manager._download(ticker, start=start)
        return result, mock

    def test_no_start_uses_period_max(self):
        result, mock = self._run("QQQ")
        call_kwargs = mock.call_args[1]
        assert call_kwargs.get("period") == "max"
        assert "start" not in call_kwargs

    def test_with_start_uses_start(self):
        result, mock = self._run("QQQ", start="2020-01-01")
        call_kwargs = mock.call_args[1]
        assert call_kwargs.get("start") == "2020-01-01"
        assert "period" not in call_kwargs

    def test_empty_download_returns_empty_series(self):
        import data_manager
        with patch("data_manager.yf.download", return_value=pd.DataFrame()):
            result = data_manager._download("XYZ")
        assert result.empty
        assert result.name == "XYZ"

    def test_result_is_tz_naive(self):
        result, _ = self._run("QQQ")
        assert result.index.tz is None

    def test_result_name_matches_ticker(self):
        result, _ = self._run("SPY")
        assert result.name == "SPY"

    def test_multi_column_close_uses_first(self):
        import data_manager
        idx = pd.bdate_range(end=datetime.now().date(), periods=3, tz="UTC")
        # Simulate yfinance multi-ticker response: Close is a DataFrame
        close_df = pd.DataFrame(
            {"QQQ": [100, 101, 102], "SPY": [200, 201, 202]},
            index=idx,
        )
        mock_df = MagicMock()
        mock_df.empty = False
        mock_df.__getitem__ = lambda self, key: close_df if key == "Close" else None
        with patch("data_manager.yf.download", return_value=mock_df):
            result = data_manager._download("QQQ")
        assert isinstance(result, pd.Series)


# ── get_ticker_data ───────────────────────────────────────────────────────────

class TestGetTickerData:
    @pytest.fixture(autouse=True)
    def patch_data_dir(self, tmp_path, monkeypatch):
        """Redirect DATA_DIR to a temp directory for isolation."""
        import data_manager
        monkeypatch.setattr(data_manager, "DATA_DIR", str(tmp_path))
        self.tmp_path = tmp_path

    def _write_cache(self, ticker, series):
        path = self.tmp_path / f"{ticker}.csv"
        series.to_csv(str(path))
        return str(path)

    def test_no_cache_downloads_and_saves(self):
        import data_manager
        fresh = _make_series("QQQ", n=10, end_days_ago=0)
        with patch.object(data_manager, "_download", return_value=fresh) as mock_dl:
            result = data_manager.get_ticker_data("QQQ")
        mock_dl.assert_called_once_with("QQQ")
        assert len(result) == 10
        # CSV should now exist
        assert os.path.exists(self.tmp_path / "QQQ.csv")

    def test_no_cache_empty_download_returns_empty(self):
        import data_manager
        empty = pd.Series(dtype=float, name="QQQ")
        with patch.object(data_manager, "_download", return_value=empty):
            result = data_manager.get_ticker_data("QQQ")
        assert result.empty
        # CSV should NOT be created for empty data
        assert not os.path.exists(self.tmp_path / "QQQ.csv")

    def test_cache_current_no_download(self):
        import data_manager
        # Fix: use a known Monday so bdate_range ends on Friday, mock now() to return Saturday
        # That way: last_date (Fri) >= today (Sat) - 1 day (Fri) → cache is current
        fixed_today = datetime(2026, 3, 7)   # Saturday
        series = _make_series("QQQ", n=20, end_days_ago=0)
        # Force the last index entry to be Friday (last business day before fixed_today)
        fixed_series = series.copy()
        fixed_series.index = pd.bdate_range(end="2026-03-06", periods=len(series))
        self._write_cache("QQQ", fixed_series)
        with patch("data_manager.datetime") as mock_dt:
            mock_dt.now.return_value = fixed_today
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            with patch.object(data_manager, "_download") as mock_dl:
                result = data_manager.get_ticker_data("QQQ")
        mock_dl.assert_not_called()
        assert len(result) == 20

    def test_cache_one_day_old_no_download(self):
        import data_manager
        # last_date = Friday, today = Saturday → Friday >= Saturday - 1 = Friday → no download
        fixed_today = datetime(2026, 3, 7)   # Saturday
        series = _make_series("QQQ", n=20, end_days_ago=0)
        fixed_series = series.copy()
        fixed_series.index = pd.bdate_range(end="2026-03-06", periods=len(series))
        self._write_cache("QQQ", fixed_series)
        with patch("data_manager.datetime") as mock_dt:
            mock_dt.now.return_value = fixed_today
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            with patch.object(data_manager, "_download") as mock_dl:
                result = data_manager.get_ticker_data("QQQ")
        mock_dl.assert_not_called()

    def test_stale_cache_with_new_data_merges(self):
        import data_manager
        # Stale cache (5 days old)
        old_series = _make_series("QQQ", n=20, end_days_ago=5)
        self._write_cache("QQQ", old_series)
        new_series = _make_series("QQQ", n=3, end_days_ago=0)
        with patch.object(data_manager, "_download", return_value=new_series):
            result = data_manager.get_ticker_data("QQQ")
        # Combined should be larger than old alone (deduplicated)
        assert len(result) >= len(old_series)
        assert len(result) >= len(new_series)

    def test_stale_cache_no_new_data_returns_cached(self):
        import data_manager
        old_series = _make_series("QQQ", n=15, end_days_ago=5)
        self._write_cache("QQQ", old_series)
        empty = pd.Series(dtype=float, name="QQQ")
        with patch.object(data_manager, "_download", return_value=empty):
            result = data_manager.get_ticker_data("QQQ")
        assert len(result) == 15

    def test_stale_cache_incremental_download_start_arg(self):
        import data_manager
        old_series = _make_series("QQQ", n=10, end_days_ago=5)
        self._write_cache("QQQ", old_series)
        new_series = _make_series("QQQ", n=2, end_days_ago=0)
        with patch.object(data_manager, "_download", return_value=new_series) as mock_dl:
            data_manager.get_ticker_data("QQQ")
        # Should be called with a start date
        mock_dl.assert_called_once()
        call_kwargs = mock_dl.call_args
        assert call_kwargs[1].get("start") is not None or call_kwargs[0][1] is not None


# ── get_price_data ────────────────────────────────────────────────────────────

class TestGetPriceData:
    @pytest.fixture(autouse=True)
    def patch_data_dir(self, tmp_path, monkeypatch):
        import data_manager
        monkeypatch.setattr(data_manager, "DATA_DIR", str(tmp_path))

    def test_returns_dataframe_with_tickers_as_columns(self):
        import data_manager
        qqq = _make_series("QQQ", n=10)
        qld = _make_series("QLD", n=10)
        with patch.object(data_manager, "get_ticker_data", side_effect=lambda t: {"QQQ": qqq, "QLD": qld}[t]):
            result = data_manager.get_price_data(["QQQ", "QLD"])
        assert "QQQ" in result.columns
        assert "QLD" in result.columns
        assert isinstance(result, pd.DataFrame)

    def test_result_is_sorted_by_date(self):
        import data_manager
        qqq = _make_series("QQQ", n=10)
        # Shuffle the index to test sorting
        qqq = qqq.sample(frac=1, random_state=1)
        with patch.object(data_manager, "get_ticker_data", return_value=qqq):
            result = data_manager.get_price_data(["QQQ"])
        assert result.index.is_monotonic_increasing

    def test_single_ticker(self):
        import data_manager
        qqq = _make_series("QQQ", n=5)
        with patch.object(data_manager, "get_ticker_data", return_value=qqq):
            result = data_manager.get_price_data(["QQQ"])
        assert list(result.columns) == ["QQQ"]
        assert len(result) == 5
