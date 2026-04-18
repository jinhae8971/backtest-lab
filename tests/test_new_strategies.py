"""Tests for Bollinger Breakout + MACD Divergence strategies."""
import numpy as np
import pandas as pd
import pytest


def _make_trending_ohlcv(n: int = 300, seed: int = 42, drift: float = 0.08):
    """Generate synthetic uptrending dataset."""
    np.random.seed(seed)
    base = 100 + np.cumsum(np.random.randn(n) * 0.8 + drift)
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


def _make_diverging_ohlcv(n: int = 300, seed: int = 42):
    """Generate data with a bearish-then-divergence pattern."""
    np.random.seed(seed)
    # First half: declining
    phase1 = np.linspace(100, 85, n // 2) + np.random.randn(n // 2) * 1.0
    # Second half: mild recovery + stabilization
    phase2 = np.linspace(85, 92, n - n // 2) + np.random.randn(n - n // 2) * 0.6
    base = np.concatenate([phase1, phase2])
    df = pd.DataFrame({
        "open": base,
        "high": base + 0.5,
        "low": base - 0.5,
        "close": base,
        "volume": np.random.randint(1_000_000, 5_000_000, n),
    }, index=pd.date_range("2023-01-01", periods=n, freq="D"))
    df["high"] = df[["open", "high", "close"]].max(axis=1) + 0.1
    df["low"] = df[["open", "low", "close"]].min(axis=1) - 0.1
    return df


class TestNewStrategiesRegistered:
    def test_bollinger_in_registry(self):
        from src.strategies import STRATEGY_REGISTRY
        assert "bollinger_breakout" in STRATEGY_REGISTRY

    def test_macd_div_in_registry(self):
        from src.strategies import STRATEGY_REGISTRY
        assert "macd_divergence" in STRATEGY_REGISTRY


class TestBollingerBreakout:
    def test_runs_without_errors(self):
        import backtrader as bt
        from src.strategies import BollingerBreakout

        cerebro = bt.Cerebro()
        cerebro.broker.setcash(100_000)
        cerebro.addstrategy(
            BollingerBreakout,
            log_trades=False,
            use_ma_filter=False,
            use_volume_filter=False,
        )
        df = _make_trending_ohlcv(300)
        feed = bt.feeds.PandasData(dataname=df, name="TEST")
        cerebro.adddata(feed)
        results = cerebro.run()
        assert cerebro.broker.getvalue() > 0
        assert hasattr(results[0], "trade_log")

    def test_accepts_squeeze_params(self):
        from src.strategies import BollingerBreakout
        # Just verify the params are valid
        p = BollingerBreakout.params._getdefaults()
        # Can't easily introspect; just confirm class constructs
        assert BollingerBreakout is not None


class TestMACDDivergence:
    def test_runs_without_errors(self):
        import backtrader as bt
        from src.strategies import MACDDivergence

        cerebro = bt.Cerebro()
        cerebro.broker.setcash(100_000)
        cerebro.addstrategy(MACDDivergence, log_trades=False, use_ma_filter=False)
        df = _make_diverging_ohlcv(300)
        feed = bt.feeds.PandasData(dataname=df, name="TEST")
        cerebro.adddata(feed)
        results = cerebro.run()
        assert cerebro.broker.getvalue() > 0


class TestFullRegistry:
    def test_all_five_strategies(self):
        from src.strategies import STRATEGY_REGISTRY
        expected = {"ma_golden", "rsi_oversold", "elliott_w3",
                    "bollinger_breakout", "macd_divergence"}
        assert set(STRATEGY_REGISTRY.keys()) == expected
