"""Bollinger Band Breakout Strategy.

볼린저 밴드 상단 돌파 시 진입, 하단 근접 시 청산.
추세 추종 (trend-following) 성격의 전략.

Params:
    - bb_period: 볼린저 밴드 기간 (default 20)
    - bb_dev: 표준편차 배수 (default 2.0)
    - ma_filter_period: 200MA 위에 있을 때만 진입
    - squeeze_threshold: 밴드 폭이 평균 이하일 때 "squeeze" 상태 → 돌파 신호 강함
"""
from __future__ import annotations

import backtrader as bt


class BollingerBreakout(bt.Strategy):
    """Enter on upper Bollinger band breakout, exit on band exit."""

    params = (
        ("bb_period", 20),
        ("bb_dev", 2.0),
        ("ma_filter_period", 200),
        ("use_ma_filter", True),
        ("squeeze_lookback", 60),       # How far to look for squeeze
        ("volume_confirm_multiplier", 1.2),  # volume must exceed SMA20*1.2
        ("use_volume_filter", True),
        ("stop_loss_pct", 0.05),
        ("take_profit_pct", 0.12),
        ("risk_per_trade", 0.02),
        ("log_trades", True),
    )

    def __init__(self):
        self.bbands = bt.indicators.BollingerBands(
            self.data.close,
            period=self.p.bb_period,
            devfactor=self.p.bb_dev,
        )
        self.ma_filter = bt.indicators.SMA(
            self.data.close, period=self.p.ma_filter_period,
        )
        self.volume_sma = bt.indicators.SMA(self.data.volume, period=20)
        self.band_width = (
            (self.bbands.lines.top - self.bbands.lines.bot) / self.bbands.lines.mid
        )
        self.band_width_avg = bt.indicators.SMA(
            self.band_width, period=self.p.squeeze_lookback,
        )
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

        # Filters
        trend_ok = (not self.p.use_ma_filter) or (
            self.data.close[0] > self.ma_filter[0]
        )
        volume_ok = (not self.p.use_volume_filter) or (
            self.data.volume[0] > self.volume_sma[0] * self.p.volume_confirm_multiplier
        )

        # Breakout condition: price crosses above upper band
        prev_close_inside = self.data.close[-1] <= self.bbands.lines.top[-1]
        curr_close_above = self.data.close[0] > self.bbands.lines.top[0]
        breakout = prev_close_inside and curr_close_above

        # Squeeze bonus: recent band width is narrow (higher conviction breakout)
        squeeze = self.band_width[0] < self.band_width_avg[0] * 0.85

        if not self.position:
            if breakout and trend_ok and volume_ok:
                cash = self.broker.get_cash()
                size_value = cash * self.p.risk_per_trade / self.p.stop_loss_pct
                size = int(size_value / self.data.close[0])
                if size > 0:
                    self.order = self.buy(size=size)
                    self.entry_price = self.data.close[0]
                    sq_str = " SQUEEZE" if squeeze else ""
                    self.log(
                        f"BUY {size} @ {self.data.close[0]:.2f} "
                        f"(band break{sq_str}, BW={self.band_width[0]:.3f})"
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
            # Exit on band mean-reversion back below middle
            band_rejection = self.data.close[0] < self.bbands.lines.mid[0]

            if stop_hit or tp_hit or band_rejection:
                reason = (
                    "stop_loss" if stop_hit
                    else "take_profit" if tp_hit
                    else "band_rejection"
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
