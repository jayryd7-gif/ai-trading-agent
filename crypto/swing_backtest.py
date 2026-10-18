"""
swing_backtest.py - Test the crypto swing strategy against buy and hold.

Run it from the project folder:
    python crypto/swing_backtest.py

THE STRATEGY ("Trend + Dip"), checked once a day at the daily close:
  1. Only own a coin while it is in an uptrend: its close is above its
     50-day average. For alt coins, bitcoin must be in an uptrend too,
     because alts usually fall harder when bitcoin weakens.
  2. In an uptrend, hold a half position (the "base").
  3. Buy the dip: when price pulls back inside the uptrend (the 3-day RSI
     falls below DIP_RSI), add the other half.
  4. Sell high: when price gets stretched (3-day RSI above TRIM_RSI), sell
     back down to the base half and keep the profit.
  5. Get out before it bleeds: when the uptrend breaks (close below the
     50-day average, or bitcoin's trend breaks for alts), sell everything
     and wait in cash. Buy back when the uptrend returns, usually lower.

Each coin gets an equal share of the money. Fees are charged on every buy
and sell. The VARIANTS table shows each piece of the strategy on its own, so
you can see what each adds. The halves check splits the history in two;
a version is more trustworthy if it beat buy and hold in both halves.
"""

import json
import sys
import time
import urllib.request
from datetime import datetime, timezone

# ---------------- SETTINGS ----------------
COINS = ["BTC", "ETH", "SOL", "XRP", "HYPE"]
EXTRA_COINS = ["DOGE", "LINK", "AVAX", "ADA"]   # not traded; a check that the rules
                                                 # work beyond the coins they were built on
START = "2019-01-01"
FEE = 0.4            # percent per buy or sell
TREND_DAYS = 50
DIP_RSI = 25
TRIM_RSI = 85
# ------------------------------------------

BINANCE = "https://data-api.binance.vision/api/v3/klines?symbol={}USDT&interval=1d&startTime={}&limit=1000"


def _get(url, body=None):
    data = json.dumps(body).encode() if body else None
    request = urllib.request.Request(url, data=data, headers={
        "User-Agent": "ai-trading-agent", "Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def daily_closes(coin, start=START):
    """{date: close} from Binance (USDT pairs), or Hyperliquid for HYPE."""
    since = int(datetime.strptime(start, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp() * 1000)
    out = {}
    if coin == "HYPE":
        rows = _get("https://api.hyperliquid.xyz/info", {"type": "candleSnapshot", "req": {
            "coin": "HYPE", "interval": "1d", "startTime": since,
            "endTime": int(time.time() * 1000)}})
        for r in rows:
            out[datetime.fromtimestamp(r["t"] / 1000, timezone.utc).date()] = float(r["c"])
        return out
    while True:
        rows = _get(BINANCE.format(coin, since))
        for r in rows:
            out[datetime.fromtimestamp(r[0] / 1000, timezone.utc).date()] = float(r[4])
        if len(rows) < 1000:
            return out
        since = rows[-1][0] + 1
        time.sleep(0.2)


def rsi(closes, i, days=3):
    gains = losses = 0.0
    for j in range(i - days + 1, i + 1):
        change = closes[j] - closes[j - 1]
        gains += max(change, 0)
        losses += max(-change, 0)
    return 100.0 if losses == 0 else 100 - 100 / (1 + gains / losses)


def average(closes, i, days):
    return sum(closes[i - days + 1:i + 1]) / days


def target_share(coin, closes, i, btc_up, held, v):
    """How much of this coin's money should be in the coin today (0, 0.5 or 1)."""
    if v["name"] == "Buy and hold":
        return 1.0
    up = closes[i] > average(closes, i, TREND_DAYS)
    if v["btc_filter"] and coin != "BTC":
        up = up and btc_up
    if not up:
        return 0.0
    mode = v["dip"]
    r = rsi(closes, i)
    if not mode:
        return 1.0
    if mode == "wait for dip":          # trend is on, but only buy on a pullback
        return 1.0 if held or r < DIP_RSI else 0.0
    if held == 0.0:
        held = 0.5                      # trend just turned on: start with the base
    if r < DIP_RSI:
        return 1.0                      # buy the dip
    if mode == "trim" and r > TRIM_RSI:
        return 0.5                      # sell high, keep the base
    if mode == "trim extremes" and closes[i] > 1.4 * average(closes, i, TREND_DAYS):
        return 0.5                      # only sell high when far above the trend
    return held


VARIANTS = [
    {"name": "Buy and hold", "btc_filter": False, "dip": None},
    {"name": "Trend only (above 50-day average)", "btc_filter": False, "dip": None},
    {"name": "Trend + bitcoin filter", "btc_filter": True, "dip": None},
    {"name": "+ dip buying, selling high often", "btc_filter": True, "dip": "trim"},
    {"name": "+ dip buying, never selling high", "btc_filter": True, "dip": "add only"},
    {"name": "+ dip buying, sell only far above trend", "btc_filter": True, "dip": "trim extremes"},
    {"name": "+ wait for a dip to get in", "btc_filter": True, "dip": "wait for dip"},
]


def run_coin(coin, series, btc, v, fee=FEE):
    """Daily equity curve {date: value} for $1 in this coin, plus trade dates."""
    dates = sorted(series)
    closes = [series[d] for d in dates]
    btc_dates = sorted(btc)
    btc_closes = [btc[d] for d in btc_dates]
    btc_up = {d: btc_closes[k] > average(btc_closes, k, TREND_DAYS)
              for k, d in enumerate(btc_dates) if k >= TREND_DAYS}
    equity, held, trades, curve = 1.0, 0.0, [], {}
    for i in range(TREND_DAYS, len(dates)):
        equity *= 1 + held * (closes[i] / closes[i - 1] - 1)
        want = target_share(coin, closes, i, btc_up.get(dates[i], False), held, v)
        if want != held:
            equity *= 1 - abs(want - held) * fee / 100
            trades.append(dates[i])
            held = want
        curve[dates[i]] = equity
    return curve, trades


def portfolio(curves, dates):
    """Equal money in each coin that exists on the first date; returns growth."""
    start = dates[0]
    members = [c for c in curves.values() if start in c]
    return sum(c[dates[-1]] / c[start] for c in members) / len(members)


def max_drop(curves, dates):
    members = [c for c in curves.values() if dates[0] in c]
    peak, drop = 0.0, 0.0
    for d in dates:
        value = sum(c[d] / c[dates[0]] for c in members if d in c) / len(members)
        peak = max(peak, value)
        drop = max(drop, 1 - value / peak)
    return drop


def report(title, coins, data):
    btc = data["BTC"]
    print(f"\n{title}")
    common = sorted(set.intersection(*(set(data[c]) for c in coins)))[TREND_DAYS:]
    middle = common[len(common) // 2]
    print(f"Equal money in {', '.join(coins)} from {common[0]} to {common[-1]} "
          f"(halves split at {middle}), {FEE}% fee per buy or sell")
    print(f"{'Version':<38}{'Growth':>9}{'Max drop':>10}{'1st half':>10}{'2nd half':>10}{'Trades':>8}")
    for v in VARIANTS:
        curves, trades = {}, 0
        for coin in coins:
            curves[coin], dates = run_coin(coin, data[coin], btc, v)
            trades += sum(1 for d in dates if common[0] <= d <= common[-1])
        first = [d for d in common if d <= middle]
        second = [d for d in common if d >= middle]
        print(f"{v['name']:<38}{portfolio(curves, common):>8.2f}x{max_drop(curves, common) * 100:>9.0f}%"
              f"{portfolio(curves, first):>9.2f}x{portfolio(curves, second):>9.2f}x{trades:>8}")


if __name__ == "__main__":
    data = {c: daily_closes(c) for c in COINS + EXTRA_COINS}
    for c in COINS + EXTRA_COINS:
        d = sorted(data[c])
        print(f"{c}: {len(d)} days from {d[0]}")
    report("== Long test: BTC, ETH, SOL, XRP (HYPE is too new) ==", ["BTC", "ETH", "SOL", "XRP"], data)
    report("== Recent test: all five coins including HYPE ==", COINS, data)
    report("== Check on coins the strategy was not built for ==", ["BTC"] + EXTRA_COINS, data)
