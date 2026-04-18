"""RSI Oversold Bounce Strategy.

    - RSI14 < 30 + 20일선 위에 있으면 진입 (과매도 반등)
    - RSI > 70 또는 5% 손절
"""
from __future__ import annotations

import backtrader as bt


class RSIOversoldBounce(bt.Strategy):
    """Mean-reversion: buy oversold, sell overbought."""

    params = (
        ("rsi_period", 14),
        ("oversold", 30),
        ("overbought", 70),
        ("ma_filter_period", 200),  # Only buy if above 200MA
        ("use_ma_filter", True),
        ("stop_loss_pct", 0.05),
        ("risk_per_trade", 0.02),
        ("log_trades", True),
    )

    def __init__(self):
        self.rsi = bt.indicators.RSI_SMA(self.data.close, period=self.p.rsi_period)
        self.ma_filter = bt.indicators.SMA(self.data.close, period=self.p.ma_filter_period)
        self.order = None
        self.entry_price = None
        self.trade_log = []

    def log(self, msg: str) -> None:
        if self.p.log_trades:
            dt = self.data.datetime.date(0)
            print(f"[{dt}] {msg}")

    def next(self):
        if self.order:
            return

        trend_ok = (not self.p.use_ma_filter) or (self.data.close[0] > self.ma_filter[0])

        if not self.position:
            if self.rsi[0] < self.p.oversold and trend_ok:
                cash = self.broker.get_cash()
                size_value = cash * self.p.risk_per_trade / self.p.stop_loss_pct
                size = int(size_value / self.data.close[0])
                if size > 0:
                    self.order = self.buy(size=size)
                    self.entry_price = self.data.close[0]
                    self.log(f"BUY {size} @ {self.data.close[0]:.2f} (RSI={self.rsi[0]:.1f})")
        else:
            stop_hit = (
                self.entry_price
                and self.data.close[0] < self.entry_price * (1 - self.p.stop_loss_pct)
            )
            overbought = self.rsi[0] > self.p.overbought

            if stop_hit or overbought:
                reason = "stop_loss" if stop_hit else "overbought"
                self.order = self.close()
                self.log(f"SELL @ {self.data.close[0]:.2f} ({reason}, RSI={self.rsi[0]:.1f})")

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
