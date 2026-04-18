"""CLI entry point for backtest-lab.

Usage:
    # MA Golden Alignment on SPY, 10 years
    python -m src.run --strategy ma_golden --ticker SPY --years 10

    # RSI Oversold on AAPL, custom period
    python -m src.run --strategy rsi_oversold --ticker AAPL \\
        --start 2020-01-01 --end 2025-12-31

    # Elliott Wave 3 entry on NVDA, 5 years
    python -m src.run --strategy elliott_w3 --ticker NVDA --years 5 \\
        --initial-cash 100000

    # Multiple tickers comparison
    python -m src.run --strategy ma_golden --ticker SPY,QQQ,DIA --years 5
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

import backtrader as bt

from .data.loader import load_yfinance_data
from .strategies import STRATEGY_REGISTRY
from .reports import build_html_report, build_json_summary, run_analyzers_metrics


def run_single_backtest(
    strategy_name: str,
    ticker: str,
    start: str | None,
    end: str | None,
    initial_cash: float,
    commission: float,
    log_trades: bool,
    strategy_params: dict | None = None,
) -> dict:
    """Run a single backtest and return the summary dict."""
    strategy_cls = STRATEGY_REGISTRY.get(strategy_name)
    if strategy_cls is None:
        raise ValueError(
            f"Unknown strategy '{strategy_name}'. "
            f"Available: {list(STRATEGY_REGISTRY.keys())}"
        )

    # Load data
    df = load_yfinance_data(ticker, start=start, end=end)
    period_start = df.index[0].strftime("%Y-%m-%d")
    period_end = df.index[-1].strftime("%Y-%m-%d")
    print(f"  📅 Data: {period_start} → {period_end} ({len(df)} bars)")

    # Setup Cerebro
    cerebro = bt.Cerebro()
    cerebro.broker.setcash(initial_cash)
    cerebro.broker.setcommission(commission=commission)

    # Add strategy
    params = strategy_params or {}
    params.setdefault("log_trades", log_trades)
    cerebro.addstrategy(strategy_cls, **params)

    # Add data feed
    feed = bt.feeds.PandasData(dataname=df, name=ticker)
    cerebro.adddata(feed)

    # Analyzers
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="sharpe",
                        timeframe=bt.TimeFrame.Days, compression=252)
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
    cerebro.addanalyzer(bt.analyzers.Returns, _name="returns")
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trades")

    # Run
    results = cerebro.run()
    strat = results[0]
    final_value = cerebro.broker.getvalue()

    # Extract metrics
    metrics = run_analyzers_metrics(strat)

    summary = build_json_summary(
        strategy_name=strategy_name,
        ticker=ticker,
        period_start=period_start,
        period_end=period_end,
        initial_cash=initial_cash,
        final_value=final_value,
        metrics=metrics,
        trade_log=getattr(strat, "trade_log", []),
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run a Backtrader backtest with a preset strategy",
    )
    parser.add_argument("--strategy", required=True,
                        choices=list(STRATEGY_REGISTRY.keys()),
                        help=f"One of: {list(STRATEGY_REGISTRY.keys())}")
    parser.add_argument("--ticker", required=True,
                        help="Ticker(s). Comma-separated for multiple: 'SPY,QQQ,DIA'")
    parser.add_argument("--years", type=int, default=5,
                        help="Lookback years (ignored if --start/--end used)")
    parser.add_argument("--start", default=None, help="YYYY-MM-DD")
    parser.add_argument("--end", default=None, help="YYYY-MM-DD (default: today)")
    parser.add_argument("--initial-cash", type=float, default=100000.0)
    parser.add_argument("--commission", type=float, default=0.001,
                        help="Commission per trade (0.001 = 0.1%)")
    parser.add_argument("--log-trades", action="store_true",
                        help="Print each trade to stdout")
    parser.add_argument("--output-dir", default="docs/reports",
                        help="Directory for JSON + HTML outputs")
    parser.add_argument("--no-html", action="store_true",
                        help="Skip HTML report generation")
    args = parser.parse_args()

    # Resolve dates
    if not args.start and not args.end:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=args.years * 365)
        args.start = start_date.strftime("%Y-%m-%d")
        args.end = end_date.strftime("%Y-%m-%d")

    tickers = [t.strip() for t in args.ticker.split(",") if t.strip()]
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    all_summaries = []
    for ticker in tickers:
        print(f"\n🧪 Running {args.strategy} on {ticker}...")
        try:
            summary = run_single_backtest(
                strategy_name=args.strategy,
                ticker=ticker,
                start=args.start,
                end=args.end,
                initial_cash=args.initial_cash,
                commission=args.commission,
                log_trades=args.log_trades,
            )
        except Exception as e:
            print(f"  ❌ Failed: {e}")
            continue

        # Results summary
        m = summary["metrics"]
        print(f"  📈 Total Return: {summary['pnl_pct']:+.2f}% "
              f"(${summary['pnl']:+,.0f})")
        print(f"  📊 Sharpe: {m.get('sharpe_ratio')} | "
              f"MDD: -{m.get('max_drawdown_pct') or 0:.1f}% | "
              f"Win Rate: {m.get('win_rate_pct') or 0:.1f}% "
              f"({m.get('won_trades') or 0}W / {m.get('lost_trades') or 0}L)")

        # Save JSON
        json_path = output_dir / f"{ticker}_{args.strategy}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2, default=str)
        print(f"  💾 JSON: {json_path}")

        # Save HTML
        if not args.no_html:
            html_path = output_dir / f"{ticker}_{args.strategy}.html"
            build_html_report(summary, html_path)
            print(f"  📄 HTML: {html_path}")

        all_summaries.append(summary)

    # Multi-ticker index
    if len(all_summaries) > 1:
        index_path = output_dir / "index.json"
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump({
                "strategy": args.strategy,
                "period": {"start": args.start, "end": args.end},
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "summaries": [
                    {
                        "ticker": s["ticker"],
                        "pnl_pct": s["pnl_pct"],
                        "sharpe": s["metrics"].get("sharpe_ratio"),
                        "mdd_pct": s["metrics"].get("max_drawdown_pct"),
                        "win_rate": s["metrics"].get("win_rate_pct"),
                        "total_trades": s["metrics"].get("total_trades"),
                    }
                    for s in all_summaries
                ],
            }, f, ensure_ascii=False, indent=2)
        print(f"\n📊 Multi-ticker index: {index_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
