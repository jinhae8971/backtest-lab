"""MA Golden Alignment Strategy.

영길님 수기 분석 스타일을 Backtrader로 이식:
    - MA5 > MA20 > MA60 (정배열) 진입
    - 이탈 또는 MA5 < MA20 크로스 시 청산
    - 옵션: RSI14 > 50 필터로 하락장 잡음 제거
"""
from __future__ import annotations

import backtrader as bt


class MAGoldenAlignment(bt.Strategy):
    """Enter when MA5 > MA20 > MA60; exit when alignment breaks."""

    params = (
        ("ma_short", 5),
        ("ma_mid", 20),
        ("ma_long", 60),
        ("use_rsi_filter", True),
        ("rsi_period", 14),
        ("rsi_threshold", 50),
        ("risk_per_trade", 0.02),   # 2% of portfolio per entry
        ("stop_loss_pct", 0.05),    # 5% stop loss
        ("log_trades", True),
    )

    def __init__(self):
        self.ma_short = bt.indicators.SMA(self.data.close, period=self.p.ma_short)
        self.ma_mid = bt.indicators.SMA(self.data.close, period=self.p.ma_mid)
        self.ma_long = bt.indicators.SMA(self.data.close, period=self.p.ma_long)
        self.rsi = bt.indicators.RSI_SMA(self.data.close, period=self.p.rsi_period)
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

        is_aligned = (
            self.ma_short[0] > self.ma_mid[0]
            and self.ma_mid[0] > self.ma_long[0]
        )
        rsi_ok = (not self.p.use_rsi_filter) or (self.rsi[0] > self.p.rsi_threshold)

        if not self.position:
            if is_aligned and rsi_ok:
                # Position sizing based on risk
                cash = self.broker.get_cash()
                size_value = cash * self.p.risk_per_trade / self.p.stop_loss_pct
                size = int(size_value / self.data.close[0])
                if size > 0:
                    self.order = self.buy(size=size)
                    self.entry_price = self.data.close[0]
                    self.log(f"BUY {size} @ {self.data.close[0]:.2f}")
        else:
            # Exit conditions
            stop_hit = (
                self.entry_price
                and self.data.close[0] < self.entry_price * (1 - self.p.stop_loss_pct)
            )
            alignment_broken = self.ma_short[0] < self.ma_mid[0]

            if stop_hit or alignment_broken:
                reason = "stop_loss" if stop_hit else "alignment_broken"
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
                    "comm": float(order.executed.comm),
                })

    def notify_trade(self, trade):
        if trade.isclosed:
            pnl = trade.pnl
            pnl_pct = (pnl / trade.value) * 100 if trade.value else 0
            self.log(f"TRADE CLOSED — PnL: ${pnl:.2f} ({pnl_pct:+.2f}%)")
