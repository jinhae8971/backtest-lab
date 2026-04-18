"""Build HTML + JSON reports from Backtrader backtest results."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


def run_analyzers_metrics(strat) -> dict:
    """Extract standard metrics from Backtrader analyzers attached to strategy."""
    metrics: dict = {}

    # Sharpe Ratio
    try:
        sharpe = strat.analyzers.sharpe.get_analysis()
        metrics["sharpe_ratio"] = (
            round(sharpe.get("sharperatio", 0.0) or 0.0, 3)
        )
    except Exception:
        metrics["sharpe_ratio"] = None

    # Drawdown
    try:
        dd = strat.analyzers.drawdown.get_analysis()
        metrics["max_drawdown_pct"] = round(dd.get("max", {}).get("drawdown", 0.0), 2)
        metrics["max_drawdown_duration"] = dd.get("max", {}).get("len", 0)
    except Exception:
        metrics["max_drawdown_pct"] = None
        metrics["max_drawdown_duration"] = None

    # Returns
    try:
        returns = strat.analyzers.returns.get_analysis()
        metrics["total_return_pct"] = round(returns.get("rtot", 0.0) * 100, 2)
        metrics["avg_return_pct"] = round(returns.get("ravg", 0.0) * 100, 4)
        metrics["annualized_return_pct"] = round(returns.get("rnorm100", 0.0), 2)
    except Exception:
        metrics["total_return_pct"] = None

    # Trade analyzer
    try:
        ta = strat.analyzers.trades.get_analysis()
        total = ta.get("total", {}).get("total", 0)
        won = ta.get("won", {}).get("total", 0)
        lost = ta.get("lost", {}).get("total", 0)
        metrics["total_trades"] = total
        metrics["won_trades"] = won
        metrics["lost_trades"] = lost
        metrics["win_rate_pct"] = round((won / total * 100) if total > 0 else 0, 2)
        avg_won = ta.get("won", {}).get("pnl", {}).get("average", 0) or 0
        avg_lost = ta.get("lost", {}).get("pnl", {}).get("average", 0) or 0
        metrics["avg_win"] = round(avg_won, 2)
        metrics["avg_loss"] = round(avg_lost, 2)
        if avg_lost and avg_lost != 0:
            metrics["profit_factor"] = round(abs(avg_won * won / (avg_lost * lost)) if lost > 0 else 0, 2)
        else:
            metrics["profit_factor"] = None
    except Exception:
        metrics["total_trades"] = 0

    return metrics


def build_json_summary(
    strategy_name: str,
    ticker: str,
    period_start: str,
    period_end: str,
    initial_cash: float,
    final_value: float,
    metrics: dict,
    trade_log: list,
) -> dict:
    """Build JSON summary of a backtest run."""
    return {
        "schema_version": "0.1.0",
        "strategy": strategy_name,
        "ticker": ticker,
        "period": {"start": period_start, "end": period_end},
        "initial_cash": initial_cash,
        "final_value": round(final_value, 2),
        "pnl": round(final_value - initial_cash, 2),
        "pnl_pct": round((final_value - initial_cash) / initial_cash * 100, 2),
        "metrics": metrics,
        "trade_count": len(trade_log),
        "trades": trade_log,
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }


_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<title>{ticker} — {strategy} Backtest Report</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
         max-width: 980px; margin: 32px auto; padding: 0 20px; color: #1e293b; }}
  h1 {{ font-size: 24px; margin-bottom: 4px; }}
  .sub {{ color: #64748b; margin-bottom: 24px; font-size: 13px; }}
  .grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 28px; }}
  .card {{ background: #f8fafc; border-left: 3px solid #2563eb; padding: 12px 14px; border-radius: 4px; }}
  .card .label {{ font-size: 11px; color: #64748b; text-transform: uppercase; letter-spacing: 0.03em; }}
  .card .val {{ font-size: 18px; font-weight: 700; margin-top: 2px; }}
  .card.pos .val {{ color: #059669; }}
  .card.neg .val {{ color: #dc2626; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th, td {{ padding: 8px 10px; text-align: left; border-bottom: 1px solid #e2e8f0; }}
  th {{ background: #f1f5f9; font-weight: 600; }}
  tr:hover {{ background: #f8fafc; }}
  .buy {{ color: #059669; font-weight: 600; }}
  .sell {{ color: #dc2626; font-weight: 600; }}
  h2 {{ font-size: 17px; margin-top: 32px; border-bottom: 2px solid #e2e8f0; padding-bottom: 6px; }}
  footer {{ margin-top: 40px; color: #94a3b8; font-size: 11px; text-align: center; }}
</style>
</head>
<body>

<h1>📊 {ticker} — {strategy}</h1>
<div class="sub">백테스트 기간: {period_start} → {period_end} | 생성: {generated_at}</div>

<h2>핵심 성과</h2>
<div class="grid">
  <div class="card {pnl_class}">
    <div class="label">총 수익률</div>
    <div class="val">{pnl_pct:+.2f}%</div>
  </div>
  <div class="card">
    <div class="label">Sharpe Ratio</div>
    <div class="val">{sharpe}</div>
  </div>
  <div class="card neg">
    <div class="label">최대 낙폭 (MDD)</div>
    <div class="val">-{mdd:.2f}%</div>
  </div>
  <div class="card">
    <div class="label">승률</div>
    <div class="val">{win_rate:.1f}%</div>
  </div>
  <div class="card">
    <div class="label">거래 횟수</div>
    <div class="val">{total_trades}</div>
  </div>
  <div class="card pos">
    <div class="label">승리 거래</div>
    <div class="val">{won_trades}</div>
  </div>
  <div class="card neg">
    <div class="label">패배 거래</div>
    <div class="val">{lost_trades}</div>
  </div>
  <div class="card">
    <div class="label">최종 자산</div>
    <div class="val">${final_value:,.0f}</div>
  </div>
</div>

<h2>상세 지표</h2>
<table>
  <tr><th>초기 자본</th><td>${initial_cash:,.2f}</td></tr>
  <tr><th>최종 자본</th><td>${final_value:,.2f}</td></tr>
  <tr><th>순손익</th><td>${pnl:+,.2f}</td></tr>
  <tr><th>연환산 수익률</th><td>{annual_return:.2f}%</td></tr>
  <tr><th>평균 수익 거래</th><td>${avg_win:+,.2f}</td></tr>
  <tr><th>평균 손실 거래</th><td>${avg_loss:+,.2f}</td></tr>
  <tr><th>Profit Factor</th><td>{profit_factor}</td></tr>
  <tr><th>MDD 지속 일수</th><td>{mdd_duration}</td></tr>
</table>

<h2>거래 이력 ({trade_count}건)</h2>
<table>
  <tr><th>날짜</th><th>액션</th><th>가격</th><th>수량</th><th>거래액</th></tr>
  {trade_rows}
</table>

<footer>
  backtest-lab v0.1.0 · generated by Backtrader
</footer>

</body>
</html>
"""


def build_html_report(summary: dict, output_path: str | Path) -> Path:
    """Build an HTML report from a JSON summary."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    m = summary.get("metrics", {})
    trades = summary.get("trades", [])

    # Build trade rows
    trade_rows = []
    for t in trades[:200]:  # cap at 200 for readability
        action_class = "buy" if t.get("action") == "BUY" else "sell"
        trade_rows.append(
            f'<tr><td>{t.get("date", "?")}</td>'
            f'<td class="{action_class}">{t.get("action", "?")}</td>'
            f'<td>${t.get("price", 0):.2f}</td>'
            f'<td>{t.get("size", 0)}</td>'
            f'<td>${t.get("value", t.get("price", 0) * t.get("size", 0)):.2f}</td></tr>'
        )
    if len(trades) > 200:
        trade_rows.append(f'<tr><td colspan="5" style="text-align:center;color:#64748b">... {len(trades)-200} more trades (see JSON)</td></tr>')

    pnl_pct = summary.get("pnl_pct", 0)
    pnl_class = "pos" if pnl_pct >= 0 else "neg"
    sharpe = m.get("sharpe_ratio")
    sharpe_str = f"{sharpe:.2f}" if sharpe is not None else "—"

    html = _HTML_TEMPLATE.format(
        ticker=summary.get("ticker", "?"),
        strategy=summary.get("strategy", "?"),
        period_start=summary.get("period", {}).get("start", "?"),
        period_end=summary.get("period", {}).get("end", "?"),
        generated_at=summary.get("generated_at", "?"),
        pnl_class=pnl_class,
        pnl_pct=pnl_pct,
        sharpe=sharpe_str,
        mdd=m.get("max_drawdown_pct") or 0,
        win_rate=m.get("win_rate_pct") or 0,
        total_trades=m.get("total_trades") or 0,
        won_trades=m.get("won_trades") or 0,
        lost_trades=m.get("lost_trades") or 0,
        final_value=summary.get("final_value", 0),
        initial_cash=summary.get("initial_cash", 0),
        pnl=summary.get("pnl", 0),
        annual_return=m.get("annualized_return_pct") or 0,
        avg_win=m.get("avg_win") or 0,
        avg_loss=m.get("avg_loss") or 0,
        profit_factor=m.get("profit_factor") if m.get("profit_factor") is not None else "—",
        mdd_duration=m.get("max_drawdown_duration") or 0,
        trade_count=len(trades),
        trade_rows="\n  ".join(trade_rows) if trade_rows else '<tr><td colspan="5" style="text-align:center;color:#64748b">거래 없음</td></tr>',
    )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    return output_path
