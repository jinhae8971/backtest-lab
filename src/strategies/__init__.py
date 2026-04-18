"""Backtrader strategy templates.

Each strategy inherits from `bt.Strategy` and implements Elliott/MA/RSI logic.
"""
from .ma_golden_alignment import MAGoldenAlignment
from .rsi_oversold_bounce import RSIOversoldBounce
from .elliott_wave3 import ElliottWave3Entry
from .bollinger_breakout import BollingerBreakout
from .macd_divergence import MACDDivergence

STRATEGY_REGISTRY = {
    "ma_golden": MAGoldenAlignment,
    "rsi_oversold": RSIOversoldBounce,
    "elliott_w3": ElliottWave3Entry,
    "bollinger_breakout": BollingerBreakout,
    "macd_divergence": MACDDivergence,
}

__all__ = [
    "MAGoldenAlignment",
    "RSIOversoldBounce",
    "ElliottWave3Entry",
    "BollingerBreakout",
    "MACDDivergence",
    "STRATEGY_REGISTRY",
]
