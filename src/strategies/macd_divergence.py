"""MACD Divergence Strategy.

강세 다이버전스(bullish divergence) 감지 시 진입:
    - 가격은 신저가를 만들었으나
    - MACD 히스토그램은 이전 저점보다 높음
    → 하락 모멘텀 약화 → 반전 가능성

Params:
    - macd_fast/slow/signal: MACD 파라미터 (default 12/26/9)
    - divergence_lookback: 다이버전스 검증 윈도우 (default 30 bars)
    - ma_filter_period: 200MA — 큰 추세 방향 확인 (default 200)
"""
from __future__ import annotations

import backtrader as bt


class MACDDivergence(bt.Strategy):
    """Detect bullish MACD divergence, enter on confirmation."""

    params = (
        ("macd_fast", 12),
        ("macd_slow", 26),
        ("macd_signal", 9),
        ("divergence_lookback", 30),
        ("ma_filter_period", 200),
        ("use_ma_filter", True),
        ("min_price_drop_pct", 0.03),    # 최소 3% 하락 후 다이버전스 봄
        ("confirmation_bars", 2),         # MACD 상승 확인 bar 수
        ("stop_loss_pct", 0.05),
        ("take_profit_pct", 0.10),
        ("risk_per_trade", 0.02),
        ("log_trades", True),
    )

    def __init__(self):
        self.macd = bt.indicators.MACD(
            self.data.close,
            period_me1=self.p.macd_fast,
            period_me2=self.p.macd_slow,
            period_signal=self.p.macd_signal,
        )
        self.macd_hist = self.macd.macd - self.macd.signal
        self.ma_filter = bt.indicators.SMA(self.data.close, period=self.p.ma_filter_period)
        self.order = None
        self.entry_price = None
        self.trade_log = []

    def log(self, msg: str) -> None:
        if self.p.log_trades:
            dt = self.data.datetime.date(0)
            print(f"[{dt}] {msg}")

    def _detect_bullish_divergence(self) -> tuple[bool, float, float]:
        """Check for bullish divergence in the recent window.

        Returns:
            (detected, price_low_old, price_low_new)
        """
        lookback = self.p.divergence_lookback
        if len(self) < lookback + 2:
            return False, 0.0, 0.0

        # Collect recent prices and MACD histogram
        prices = [self.data.low[-i] for i in range(lookback, 0, -1)]
        hists = [self.macd_hist[-i] for i in range(lookback, 0, -1)]

        # Find two most significant troughs in prices
        # Split into 2 halves, find min in each
        mid = lookback // 2
        first_half_min_idx = min(range(mid), key=lambda i: prices[i])
        second_half_min_idx = mid + min(range(lookback - mid), key=lambda i: prices[mid + i])

        price_low_old = prices[first_half_min_idx]
        price_low_new = prices[second_half_min_idx]
        hist_old = hists[first_half_min_idx]
        hist_new = hists[second_half_min_idx]

        # Bullish divergence: price made lower low, but MACD hist made higher low
        price_drop = (price_low_old - price_low_new) / price_low_old
        if price_drop < self.p.min_price_drop_pct:
            return False, price_low_old, price_low_new

        lower_low_price = price_low_new < price_low_old
        higher_low_hist = hist_new > hist_old

        # Confirmation: recent bars show MACD rising
        recent_rising = all(
            self.macd_hist[-i] > self.macd_hist[-i - 1]
            for i in range(self.p.confirmation_bars)
        )

        return (lower_low_price and higher_low_hist and recent_rising,
                price_low_old, price_low_new)

    def next(self):
        if self.order:
            return

        trend_ok = (not self.p.use_ma_filter) or (
            self.data.close[0] > self.ma_filter[0]
        )

        if not self.position:
            detected, p_old, p_new = self._detect_bullish_divergence()
            if detected and trend_ok:
                cash = self.broker.get_cash()
                size_value = cash * self.p.risk_per_trade / self.p.stop_loss_pct
                size = int(size_value / self.data.close[0])
                if size > 0:
                    self.order = self.buy(size=size)
                    self.entry_price = self.data.close[0]
                    self.log(
                        f"BUY {size} @ {self.data.close[0]:.2f} "
                        f"(bullish div: {p_old:.2f}→{p_new:.2f})"
                    )
        else:
            stop_hit = (
                self.entry_price
                and self.data.close[0] < self.entry_price * (1 - self.p.stop_loss_pct)
            )
            tp_hit = (
                self.entry_price
                and self.data.close[0] > self.entry_price * (1 + self.p.take_profit_pct)
            )
            # Exit on MACD cross below signal
            macd_cross_down = self.macd.macd[0] < self.macd.signal[0] and \
                              self.macd.macd[-1] >= self.macd.signal[-1]

            if stop_hit or tp_hit or macd_cross_down:
                reason = (
                    "stop_loss" if stop_hit
                    else "take_profit" if tp_hit
                    else "macd_cross_down"
                )
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
                    "value": float(order.executed.value),
                })

    def notify_trade(self, trade):
        if trade.isclosed:
            pnl_pct = (trade.pnl / trade.value) * 100 if trade.value else 0
            self.log(f"TRADE CLOSED — PnL: ${trade.pnl:.2f} ({pnl_pct:+.2f}%)")
