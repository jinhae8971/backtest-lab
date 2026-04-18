"""Elliott Wave 3 Entry Strategy.

영길님 스타일: 엘리엇 2파 완료 후 3파 초입에서 진입하는 전략.

Simplified heuristic (trendline-detector 연동 없이 독립 작동):
    1. 직전 고점 → 저점 (wave 1 end → wave 2 end 가정) 형성
    2. 현재가가 wave 2 저점에서 반등 + wave 1 고점 돌파 중
    3. 거래량 + RSI 추가 필터

Full version은 trendline-detector JSON 입력을 받아 더 정밀하게 판단 가능.
"""
from __future__ import annotations

import backtrader as bt


class ElliottWave3Entry(bt.Strategy):
    """Enter on suspected Wave 3 breakout."""

    params = (
        ("lookback", 50),            # bars to detect wave structure
        ("wave2_retrace_min", 0.382),
        ("wave2_retrace_max", 0.786),
        ("rsi_period", 14),
        ("rsi_min_entry", 50),       # RSI must confirm momentum
        ("stop_loss_pct", 0.05),
        ("take_profit_pct", 0.15),   # 3:1 reward:risk default
        ("risk_per_trade", 0.02),
        ("log_trades", True),
    )

    def __init__(self):
        self.rsi = bt.indicators.RSI_SMA(self.data.close, period=self.p.rsi_period)
        self.highest = bt.indicators.Highest(self.data.high, period=self.p.lookback)
        self.lowest = bt.indicators.Lowest(self.data.low, period=self.p.lookback)
        self.order = None
        self.entry_price = None
        self.trade_log = []

    def log(self, msg: str) -> None:
        if self.p.log_trades:
            dt = self.data.datetime.date(0)
            print(f"[{dt}] {msg}")

    def _detect_wave_structure(self) -> bool:
        """Heuristic wave structure detection."""
        if len(self) < self.p.lookback + 5:
            return False

        # Find the index (within lookback) of the highest high and lowest low
        # using recent bars — simple scan
        lookback = self.p.lookback
        highs = [self.data.high[-i] for i in range(lookback, 0, -1)]
        lows = [self.data.low[-i] for i in range(lookback, 0, -1)]

        # Wave 1: find first significant peak in first half
        first_half_end = lookback // 2
        wave1_peak_idx = max(range(first_half_end), key=lambda i: highs[i])
        wave1_peak = highs[wave1_peak_idx]
        # Wave 1 start: lowest point BEFORE wave1_peak
        if wave1_peak_idx < 2:
            return False
        wave1_start = min(lows[: wave1_peak_idx])

        # Wave 2: lowest point AFTER wave1_peak, within first 2/3
        wave2_search_end = int(lookback * 0.67)
        if wave2_search_end <= wave1_peak_idx + 1:
            return False
        wave2_low_idx = wave1_peak_idx + 1 + min(
            range(wave2_search_end - wave1_peak_idx - 1),
            key=lambda i: lows[wave1_peak_idx + 1 + i],
        )
        wave2_low = lows[wave2_low_idx]

        # Wave 2 must be a retracement of wave 1 in (38.2%, 78.6%)
        wave1_range = wave1_peak - wave1_start
        if wave1_range <= 0:
            return False
        retrace = (wave1_peak - wave2_low) / wave1_range
        if not (self.p.wave2_retrace_min <= retrace <= self.p.wave2_retrace_max):
            return False

        # Current price should break above wave 1 peak (start of wave 3)
        current = self.data.close[0]
        if current <= wave1_peak:
            return False

        # RSI momentum check
        if self.rsi[0] < self.p.rsi_min_entry:
            return False

        return True

    def next(self):
        if self.order:
            return

        if not self.position:
            if self._detect_wave_structure():
                cash = self.broker.get_cash()
                size_value = cash * self.p.risk_per_trade / self.p.stop_loss_pct
                size = int(size_value / self.data.close[0])
                if size > 0:
                    self.order = self.buy(size=size)
                    self.entry_price = self.data.close[0]
                    self.log(f"BUY {size} @ {self.data.close[0]:.2f} (W3 breakout)")
        else:
            stop_hit = (
                self.entry_price
                and self.data.close[0] < self.entry_price * (1 - self.p.stop_loss_pct)
            )
            tp_hit = (
                self.entry_price
                and self.data.close[0] > self.entry_price * (1 + self.p.take_profit_pct)
            )

            if stop_hit or tp_hit:
                reason = "stop_loss" if stop_hit else "take_profit"
                self.order = self.close()
                self.log(f"SELL @ {self.data.close[0]:.2f} ({reason})")

    def notify_order(self, order):
        if order.status in (order.Completed, order.Canceled, order.Margin, order.Rejected):
            self.order = None
            if order.status == order.Completed:
                action = "BUY" if order.isbuy() else "SELL"
                self.trade_log.append({
                    "date": str(self.data.datetime.date(0)),
                    "action": action,
                    "price": float(order.executed.price),
                    "size": int(order.executed.size),
                })

    def notify_trade(self, trade):
        if trade.isclosed:
            pnl_pct = (trade.pnl / trade.value) * 100 if trade.value else 0
            self.log(f"TRADE CLOSED — PnL: ${trade.pnl:.2f} ({pnl_pct:+.2f}%)")
