"""
trend_backtest.py - Test simple daily trend-following rules on BTC and ETH.

Run it from the project folder:
    python crypto/trend_backtest.py

Each rule is checked once a day at the daily close (00:00 UTC). It either
holds the coin or holds cash; it never shorts. Fees are charged on every buy
and every sell. "Growth" is what $1 became (2.00x means it doubled), and
"Max drop" is the worst fall from a high along the way.

The halves check works like the other backtests: a rule is more trustworthy
if it grew in both halves, not just overall.
"""

import json
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone

# ---------------- SETTINGS ----------------
YEARS = 6
FEE = 0.4          # percent per buy or sell (Coinbase / Kraken, small account)
WARMUP = 100       # days of history needed before the first decision
# ------------------------------------------


def daily_candles(product, years=YEARS):
    """[(date, high, low, close)] from Coinbase, oldest first."""
    out = {}
    end = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    cursor = end - timedelta(days=365 * years)
    while cursor < end:
        stop = min(cursor + timedelta(days=300), end)
        url = (f"https://api.exchange.coinbase.com/products/{product}/candles?granularity=86400"
               f"&start={cursor:%Y-%m-%dT%H:%M:%SZ}&end={stop:%Y-%m-%dT%H:%M:%SZ}")
        request = urllib.request.Request(url, headers={"User-Agent": "ai-trading-agent"})
        with urllib.request.urlopen(request, timeout=30) as response:
            for ts, low, high, _open, close, _volume in json.load(response):
                out[ts] = (high, low, close)
        cursor = stop
        time.sleep(0.2)
    return [(datetime.fromtimestamp(k, timezone.utc).date(), *out[k]) for k in sorted(out)]


def backtest(bars, rule, fee=FEE):
    """Returns growth, max drop, number of buys, first-half and second-half growth."""
    equity, holding, buys, peak, max_drop = 1.0, 0, 0, 1.0, 0.0
    curve = []
    for i in range(WARMUP, len(bars)):
        if holding:
            equity *= bars[i][3] / bars[i - 1][3]
        wanted = rule(bars, i)
        if wanted != holding:
            equity *= 1 - fee / 100
            buys += wanted == 1
            holding = wanted
        peak = max(peak, equity)
        max_drop = max(max_drop, 1 - equity / peak)
        curve.append((bars[i][0], equity))
    half = len(curve) // 2
    return (equity, max_drop, buys, curve[half - 1][1],
            curve[-1][1] / curve[half - 1][1], curve[half][0])


def above_average(days):
    """Hold while the close is above its average of the last `days` days."""
    return lambda b, i: int(b[i][3] > sum(x[3] for x in b[i - days:i]) / days)


def channel_breakout(entry_days, exit_days):
    """Buy on a close above the highest high of the last entry_days days;
    sell on a close below the lowest low of the last exit_days days."""
    state = {"holding": 0}

    def rule(b, i):
        if b[i][3] > max(x[1] for x in b[i - entry_days:i]):
            state["holding"] = 1
        elif b[i][3] < min(x[2] for x in b[i - exit_days:i]):
            state["holding"] = 0
        return state["holding"]
    return rule


RULES = [
    ("Buy and hold", lambda b, i: 1),
    ("20-day breakout, 10-day exit", channel_breakout(20, 10)),
    ("50-day breakout, 25-day exit", channel_breakout(50, 25)),
    ("Above 50-day average", above_average(50)),
    ("Above 100-day average", above_average(100)),
]


if __name__ == "__main__":
    for product in [a for a in sys.argv[1:] if a.endswith("-USD")] or ["BTC-USD", "ETH-USD"]:
        bars = daily_candles(product)
        print(f"\n{product} daily, {bars[WARMUP][0]} to {bars[-1][0]}, {FEE}% fee per buy or sell")
        print(f"{'Rule':<34}{'Growth':>9}{'Max drop':>10}{'Buys':>6}{'1st half':>10}{'2nd half':>10}")
        for name, rule in RULES:
            growth, drop, buys, first, second, split = backtest(bars, rule)
            print(f"{name:<34}{growth:>8.2f}x{drop * 100:>9.0f}%{buys:>6}{first:>9.2f}x{second:>9.2f}x")
        print(f"Halves split at {split}")
