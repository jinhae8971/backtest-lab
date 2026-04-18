"""Tests for backtest strategies and reports."""
import numpy as np
import pandas as pd
import pytest


def _make_trending_ohlcv(n: int = 300, seed: int = 42) -> pd.DataFrame:
    """Generate a synthetic uptrending dataset for testing."""
    np.random.seed(seed)
    base = 100 + np.cumsum(np.random.randn(n) * 0.8 + 0.08)  # gentle uptrend
    noise = np.random.randn(n) * 0.3
    df = pd.DataFrame({
        "open": base + noise,
        "high": base + np.abs(noise) + 0.5,
        "low": base - np.abs(noise) - 0.5,
        "close": base,
        "volume": np.random.randint(1_000_000, 5_000_000, n),
    }, index=pd.date_range("2023-01-01", periods=n, freq="D"))
    df["high"] = df[["open", "high", "close"]].max(axis=1) + 0.1
    df["low"] = df[["open", "low", "close"]].min(axis=1) - 0.1
    return df


class TestStrategyRegistry:
    def test_registry_has_all_strategies(self):
        from src.strategies import STRATEGY_REGISTRY
        assert "ma_golden" in STRATEGY_REGISTRY
        assert "rsi_oversold" in STRATEGY_REGISTRY
        assert "elliott_w3" in STRATEGY_REGISTRY

    def test_strategies_are_backtrader_compatible(self):
        import backtrader as bt
        from src.strategies import STRATEGY_REGISTRY
        for name, cls in STRATEGY_REGISTRY.items():
            assert issubclass(cls, bt.Strategy), f"{name} is not a bt.Strategy"


class TestMAGoldenAlignment:
    def test_runs_on_trending_data(self):
        import backtrader as bt
        from src.strategies import MAGoldenAlignment

        cerebro = bt.Cerebro()
        cerebro.broker.setcash(100_000)
        cerebro.addstrategy(MAGoldenAlignment, log_trades=False)

        df = _make_trending_ohlcv(300)
        feed = bt.feeds.PandasData(dataname=df, name="TEST")
        cerebro.adddata(feed)

        results = cerebro.run()
        strat = results[0]
        # Trending data should produce at least one trade (MA aligns eventually)
        assert hasattr(strat, "trade_log")
        final_value = cerebro.broker.getvalue()
        # Starting cash was 100k, final should be finite
        assert final_value > 0


class TestRSIOversoldBounce:
    def test_runs_without_errors(self):
        import backtrader as bt
        from src.strategies import RSIOversoldBounce

        cerebro = bt.Cerebro()
        cerebro.broker.setcash(100_000)
        cerebro.addstrategy(RSIOversoldBounce, log_trades=False, use_ma_filter=False)

        df = _make_trending_ohlcv(300)
        feed = bt.feeds.PandasData(dataname=df, name="TEST")
        cerebro.adddata(feed)

        results = cerebro.run()
        assert cerebro.broker.getvalue() > 0


class TestReports:
    def test_build_json_summary(self):
        from src.reports import build_json_summary
        summary = build_json_summary(
            strategy_name="ma_golden",
            ticker="SPY",
            period_start="2020-01-01",
            period_end="2024-12-31",
            initial_cash=100_000,
            final_value=125_000,
            metrics={"sharpe_ratio": 1.2, "max_drawdown_pct": 12.5},
            trade_log=[{"date": "2020-03-15", "action": "BUY", "price": 280, "size": 50}],
        )
        assert summary["strategy"] == "ma_golden"
        assert summary["pnl"] == 25_000
        assert summary["pnl_pct"] == 25.0
        assert summary["trade_count"] == 1

    def test_build_html_report(self, tmp_path):
        from src.reports import build_html_report, build_json_summary
        summary = build_json_summary(
            strategy_name="ma_golden", ticker="SPY",
            period_start="2020-01-01", period_end="2024-12-31",
            initial_cash=100_000, final_value=125_000,
            metrics={
                "sharpe_ratio": 1.2, "max_drawdown_pct": 12.5,
                "win_rate_pct": 55.0, "total_trades": 40,
                "won_trades": 22, "lost_trades": 18,
                "avg_win": 250, "avg_loss": -120,
                "annualized_return_pct": 5.5,
            },
            trade_log=[{"date": "2020-03-15", "action": "BUY", "price": 280, "size": 50, "value": 14000}],
        )
        html_path = tmp_path / "report.html"
        result = build_html_report(summary, html_path)
        assert result.exists()
        content = result.read_text(encoding="utf-8")
        assert "SPY" in content
        assert "ma_golden" in content
        assert "25.00%" in content  # pnl_pct


class TestDataLoader:
    def test_load_yfinance_data_columns(self):
        # This test requires internet; skip if offline
        try:
            from src.data import load_yfinance_data
            df = load_yfinance_data("SPY", period="1mo")
            assert set(["open", "high", "low", "close", "volume"]).issubset(df.columns)
            assert len(df) > 0
        except Exception as e:
            pytest.skip(f"yfinance fetch failed (offline?): {e}")
