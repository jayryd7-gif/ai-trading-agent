"""
tradingview_stats.py - Turns your TradingView strategy exports into dashboard stats.

TradingView has no way for other programs to read the Strategy Tester, so
the stats come from its "List of trades" export (a CSV file):
  1. In TradingView, Strategy Tester > List of trades > export.
  2. Double-click tradingview/update-exports.command. It copies the newest
     MNQ1! and MGC1! exports from Downloads into tradingview/exports/.
  3. Push in GitHub Desktop. The dashboard updates on its next run.

TradingView lists each partial exit (Target 1, 2, 3) as its own "trade".
This file groups them back into positions, so one trade here means one
entry, matching the paper trader and the trading rules.

Used by agents/dashboard.py. Run it on its own to print the stats:
    python agents/tradingview_stats.py
"""

import csv
import glob
import os
import re
from datetime import datetime

EXPORTS = os.path.join("tradingview", "exports")
PAPER_START = "2026-10-19"     # trades from this day on count as the forward test
MARKETS = {"MNQ1!": "Nasdaq (MNQ)", "MGC1!": "Gold (MGC)"}


def latest_exports():
    """{symbol: path} for the newest export of each market (by the date in the name)."""
    found = {}
    for path in glob.glob(os.path.join(EXPORTS, "*.csv")):
        name = os.path.basename(path)
        symbol = next((s for s in MARKETS if s in name), None)
        date = re.search(r"(\d{4}-\d{2}-\d{2})", name)
        if not symbol:
            continue
        key = (date.group(1) if date else "", os.path.getsize(path))
        if symbol not in found or key > found[symbol][0]:
            found[symbol] = (key, path)
    return {s: p for s, (_, p) in found.items()}


def positions(path):
    """Group the export's rows into positions: one per entry time and side."""
    groups = {}
    with open(path, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            if not row["Type"].startswith("Entry"):
                continue
            key = (row["Date and time"], row["Type"].split()[1])
            g = groups.setdefault(key, {"entry_time": row["Date and time"],
                                        "side": row["Type"].split()[1],
                                        "price": float(row["Price USD"]),
                                        "profit": 0.0, "contracts": 0})
            g["profit"] += float(row["Net PnL USD"])
            g["contracts"] += int(float(row["Size (qty)"]))
    return sorted(groups.values(), key=lambda g: g["entry_time"])


def stats(trades):
    profits = [t["profit"] for t in trades]
    wins = [p for p in profits if p > 0]
    losses = [p for p in profits if p < 0]
    equity = peak = drawdown = 0.0
    for p in profits:
        equity += p
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)
    return {"trades": len(profits), "wins": len(wins), "losses": len(losses),
            "net": sum(profits),
            "win_rate": f"{len(wins) / len(profits):.0%}" if profits else "n/a",
            "profit_factor": f"{sum(wins) / -sum(losses):.2f}" if losses else "n/a",
            "best": max(profits, default=0.0), "worst": min(profits, default=0.0),
            "drawdown": drawdown}


def money(v):
    return f"-${-v:,.0f}" if v < 0 else f"${v:,.0f}"


def dashboard_section():
    """Markdown lines for the main dashboard."""
    out = ["## 📈 TradingView strategy results", ""]
    exports = latest_exports()
    if not exports:
        return out + ["No TradingView exports yet. Export the List of trades in TradingView, "
                      "then double-click `tradingview/update-exports.command` and push.", ""]

    out += ["From the latest **List of trades** export of each chart. One trade = one entry "
            "(TradingView counts each target as a separate trade). "
            f"Forward test = trades from {PAPER_START} on.", "",
            "| Market | Export date | Trades | Wins / losses | Win rate | Total | Profit factor "
            "| Max drawdown | Forward test |",
            "|---|---|---|---|---|---|---|---|---|"]
    all_trades = []
    for symbol, label in MARKETS.items():
        path = exports.get(symbol)
        if not path:
            out.append(f"| {label} | no export yet | | | | | | | |")
            continue
        trades = positions(path)
        for t in trades:
            t["market"] = label
        all_trades += trades
        s = stats(trades)
        fwd = stats([t for t in trades if t["entry_time"] >= PAPER_START])
        date = re.search(r"(\d{4}-\d{2}-\d{2})", os.path.basename(path))
        first = trades[0]["entry_time"][:10] if trades else ""
        out.append(f"| {label} | {date.group(1) if date else '?'} (trades since {first}) | "
                   f"{s['trades']} | {s['wins']} / {s['losses']} | {s['win_rate']} | "
                   f"**{money(s['net'])}** | {s['profit_factor']} | {money(s['drawdown'])} | "
                   f"{fwd['trades']} trades, {money(fwd['net'])} |")
    if len(exports) > 1:
        s = stats(sorted(all_trades, key=lambda t: t["entry_time"]))
        out.append(f"| **Both** | | {s['trades']} | {s['wins']} / {s['losses']} | {s['win_rate']} | "
                   f"**{money(s['net'])}** | {s['profit_factor']} | | |")
    out += ["", "<details>", "<summary><b>Latest 10 TradingView trades</b></summary>", "",
            "| Entry (New York) | Market | Side | Entry price | Contracts | Result |",
            "|---|---|---|---|---|---|"]
    for t in sorted(all_trades, key=lambda t: t["entry_time"], reverse=True)[:10]:
        icon = "✅" if t["profit"] > 0 else "❌"
        out.append(f"| {t['entry_time']} | {t['market']} | {t['side']} | {t['price']:,.2f} | "
                   f"{t['contracts']} | {icon} {money(t['profit'])} |")
    out += ["", "</details>", "",
            "To refresh: export the List of trades from each chart in TradingView, double-click "
            "`tradingview/update-exports.command`, then push in GitHub Desktop.", ""]
    return out


if __name__ == "__main__":
    print("\n".join(dashboard_section()))
