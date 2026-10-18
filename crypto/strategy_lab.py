"""
strategy_lab.py - Compare crypto strategy families over 6 years.

Run it from the project folder:
    python crypto/strategy_lab.py

Every strategy starts with $1,000, decides once a day at the daily close, pays
FEE percent on every dollar bought or sold, and never borrows (no leverage)
or shorts. Results show what $1,000 became, the worst fall along the way, and
the growth in each half of the period (a strategy is more trustworthy if it
did well in both).

THE UNIVERSE is the large coins that already existed and traded in late
2020, including ones that later did badly. Choosing only today's winners
would make every strategy look better than it really was.

WARNING about reading the results: testing many strategies and picking the
best always flatters the winner. Prefer strategies that win in both halves,
on many coins, with simple rules.
"""

import json
import os
import sys
import time
import urllib.request
from datetime import date, datetime, timezone

# ---------------- SETTINGS ----------------
START = date(2020, 10, 18)       # 6 years ago; history before this feeds the indicators
FEE = 0.4                        # percent per dollar bought or sold
UNIVERSE = ["BTC", "ETH", "XRP", "ADA", "DOGE", "LINK", "LTC", "BCH", "BNB", "TRX",
            "XLM", "EOS", "DOT", "SOL", "AVAX", "ETC", "ATOM", "UNI"]
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")
# ------------------------------------------

BINANCE = "https://data-api.binance.vision/api/v3/klines?symbol={}USDT&interval=1d&startTime={}&limit=1000"


def closes(coin):
    """{date: daily close} from Binance since 2019, cached for a day."""
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, f"{coin}-1d.json")
    if os.path.exists(path) and time.time() - os.path.getmtime(path) < 86400:
        return {date.fromisoformat(k): v for k, v in json.load(open(path)).items()}
    out, since = {}, int(datetime(2019, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)
    while True:
        request = urllib.request.Request(BINANCE.format(coin, since), headers={"User-Agent": "x"})
        rows = json.load(urllib.request.urlopen(request, timeout=30))
        for r in rows:
            out[datetime.fromtimestamp(r[0] / 1000, timezone.utc).date()] = float(r[4])
        if len(rows) < 1000:
            break
        since = rows[-1][0] + 1
        time.sleep(0.2)
    json.dump({k.isoformat(): v for k, v in out.items()}, open(path, "w"))
    return out


class Market:
    def __init__(self, coins):
        self.data = {c: closes(c) for c in coins}
        self.dates = sorted(d for d in self.data["BTC"] if d >= START)

    def price(self, coin, day):
        return self.data[coin].get(day)

    def history(self, coin, day, days):
        """The last `days` closes up to and including `day`, or None if missing."""
        keys = self._keys(coin)
        i = keys.get(day)
        if i is None or i < days:
            return None
        ordered = self._ordered(coin)
        return ordered[i - days + 1:i + 1]

    def _keys(self, coin):
        if not hasattr(self, "_k"):
            self._k, self._o = {}, {}
        if coin not in self._k:
            ordered = sorted(self.data[coin])
            self._o[coin] = [self.data[coin][d] for d in ordered]
            self._k[coin] = {d: i for i, d in enumerate(ordered)}
        return self._k[coin]

    def _ordered(self, coin):
        self._keys(coin)
        return self._o[coin]


def above_average(m, coin, day, days):
    h = m.history(coin, day, days)
    return h is not None and h[-1] > sum(h) / days


def momentum(m, coin, day, days):
    h = m.history(coin, day, days + 1)
    return None if h is None else h[-1] / h[0] - 1


def volatility(m, coin, day, days=30):
    h = m.history(coin, day, days + 1)
    if h is None:
        return None
    rets = [h[k] / h[k - 1] - 1 for k in range(1, len(h))]
    mean = sum(rets) / len(rets)
    return (sum((r - mean) ** 2 for r in rets) / len(rets)) ** 0.5 * (365 ** 0.5)


# ---- Strategies: each returns the target weights {coin: share} for today ----

def buy_and_hold(coins):
    state = {}
    def rule(m, day, weights):
        if not state:
            here = [c for c in coins if m.price(c, day)]
            state.update({c: 1 / len(here) for c in here})
        return weights or dict(state)       # buy once, never trade again
    return rule


def trend(coins, days=50, btc_filter=True):
    def rule(m, day, weights):
        btc_up = above_average(m, "BTC", day, days)
        live = [c for c in coins if m.price(c, day)]
        share = 1 / len(live)
        return {c: share for c in live
                if above_average(m, c, day, days) and (c == "BTC" or not btc_filter or btc_up)}
    return rule


def crossover(coins, fast=20, slow=100):
    """Own a coin while its fast average is above its slow average."""
    def rule(m, day, weights):
        live = [c for c in coins if m.price(c, day)]
        out = {}
        for c in live:
            f, s = m.history(c, day, fast), m.history(c, day, slow)
            if f and s and sum(f) / fast > sum(s) / slow:
                out[c] = 1 / len(live)
        return out
    return rule


def rotation(coins, lookback=60, top=3, every=7, trend_days=50):
    """Every `every` days, hold the `top` coins with the biggest gain over
    `lookback` days, if they are in an uptrend and bitcoin is too."""
    state = {"last": None, "weights": {}}
    def rule(m, day, weights):
        if state["last"] and (day - state["last"]).days < every:
            # between rebalances: only sell a coin whose uptrend breaks
            return {c: w for c, w in state["weights"].items()
                    if above_average(m, c, day, trend_days) and above_average(m, "BTC", day, trend_days)}
        state["last"] = day
        if not above_average(m, "BTC", day, trend_days):
            state["weights"] = {}
            return {}
        scored = [(momentum(m, c, day, lookback), c) for c in coins if m.price(c, day)]
        scored = [(s, c) for s, c in scored
                  if s is not None and s > 0 and above_average(m, c, day, trend_days)]
        picks = [c for _, c in sorted(scored, reverse=True)[:top]]
        state["weights"] = {c: 1 / top for c in picks}
        return dict(state["weights"])
    return rule


def dual_momentum(coins=("BTC", "ETH"), lookback=60):
    """Hold the stronger of BTC and ETH, only while its gain over `lookback`
    days is positive; otherwise cash."""
    def rule(m, day, weights):
        scored = [(momentum(m, c, day, lookback), c) for c in coins]
        scored = [x for x in scored if x[0] is not None]
        if not scored:
            return {}
        best = max(scored)
        return {best[1]: 1.0} if best[0] > 0 else {}
    return rule


def vol_sized_trend(coins, days=50, target=0.6):
    """Trend with bitcoin filter, but hold less of a coin when it is wild:
    position = target volatility / the coin's recent volatility (max 1)."""
    base = trend(coins, days)
    def rule(m, day, weights):
        out = {}
        for c, w in base(m, day, weights).items():
            v = volatility(m, c, day)
            out[c] = w * min(1.0, target / v) if v else 0
        return out
    return rule


def channel(coins, entry=20, exit_=10):
    """Buy a coin on a close above its highest close of `entry` days; sell
    on a close below its lowest close of `exit_` days."""
    held = set()
    def rule(m, day, weights):
        live = [c for c in coins if m.price(c, day)]
        for c in live:
            h = m.history(c, day, entry + 1)
            l = m.history(c, day, exit_ + 1)
            if not h or not l:
                continue
            if h[-1] > max(h[:-1]):
                held.add(c)
            elif h[-1] < min(l[:-1]):
                held.discard(c)
        return {c: 1 / len(live) for c in held if c in live}
    return rule


def simulate(m, rule, fee=FEE):
    """Run a strategy. Returns (final value of $1,000, worst fall, value curve)."""
    value, weights, curve, peak, worst = 1000.0, {}, {}, 1000.0, 0.0
    for k, day in enumerate(m.dates):
        if k:
            prev = m.dates[k - 1]
            growth = sum(w * (m.price(c, day) / m.price(c, prev) - 1)
                         for c, w in weights.items() if m.price(c, day) and m.price(c, prev))
            value *= 1 + growth
            # weights drift with prices
            total = 1 + growth
            weights = {c: w * (m.price(c, day) / m.price(c, prev)) / total
                       for c, w in weights.items() if m.price(c, day) and m.price(c, prev)}
        target = rule(m, day, weights)
        # Coins already held keep their size (winners are left to run); new
        # coins are bought with the cash available; dropped coins are sold.
        kept = {c: weights[c] for c in target if c in weights}
        fresh = {c: w for c, w in target.items() if c not in weights}
        cash = max(0.0, 1 - sum(kept.values()))
        scale = min(1.0, cash / sum(fresh.values())) if fresh else 1.0
        new = dict(kept, **{c: w * scale for c, w in fresh.items()})
        turnover = sum(abs(new.get(c, 0) - weights.get(c, 0)) for c in set(new) | set(weights))
        value *= 1 - turnover * fee / 100
        weights = new
        peak = max(peak, value)
        worst = max(worst, 1 - value / peak)
        curve[day] = value
    return value, worst, curve


def main():
    m = Market(UNIVERSE)
    main4 = ["BTC", "ETH", "SOL", "XRP"]
    strategies = [
        ("Buy and hold BTC", buy_and_hold(["BTC"])),
        ("Buy and hold all 18 coins", buy_and_hold(UNIVERSE)),
        ("Earlier pick: trend + BTC filter (4 coins)", trend(main4)),
        ("Trend + BTC filter, all 18 coins", trend(UNIVERSE)),
        ("20/100-day average crossover, 18 coins", crossover(UNIVERSE)),
        ("Volatility-sized trend, 18 coins", vol_sized_trend(UNIVERSE)),
        ("20-day channel breakout, 18 coins", channel(UNIVERSE)),
        ("Dual momentum BTC/ETH (60-day)", dual_momentum()),
        ("Rotation: top 1 by 60-day gain, weekly", rotation(UNIVERSE, 60, 1)),
        ("Rotation: top 3 by 60-day gain, weekly", rotation(UNIVERSE, 60, 3)),
        ("Rotation: top 5 by 60-day gain, weekly", rotation(UNIVERSE, 60, 5)),
        ("Rotation: top 3 by 30-day gain, weekly", rotation(UNIVERSE, 30, 3)),
        ("Rotation: top 3 by 90-day gain, weekly", rotation(UNIVERSE, 90, 3)),
        ("Rotation: top 3 by 60-day gain, every 2 weeks", rotation(UNIVERSE, 60, 3, 14)),
        ("Rotation: top 3 by 120-day gain, weekly", rotation(UNIVERSE, 120, 3)),
        ("Rotation: top 5 by 120-day gain, weekly", rotation(UNIVERSE, 120, 5)),
        ("Rotation: top 3 by 180-day gain, weekly", rotation(UNIVERSE, 180, 3)),
        ("Rotation: top 5 by 180-day gain, weekly", rotation(UNIVERSE, 180, 5)),
        ("Trend + BTC filter, 100-day average, 18 coins", trend(UNIVERSE, 100)),
        ("Volatility-sized trend, 4 coins", vol_sized_trend(main4)),
    ]
    middle = m.dates[len(m.dates) // 2]
    print(f"{m.dates[0]} to {m.dates[-1]} ({len(m.dates)} days), halves split at {middle}, "
          f"{FEE}% fee per dollar traded, no leverage")
    print(f"{'Strategy':<48}{'$1,000 became':>15}{'Worst fall':>12}{'1st half':>10}{'2nd half':>10}")
    for name, rule in strategies:
        final, worst, curve = simulate(m, rule)
        first = curve[middle] / 1000
        second = final / curve[middle]
        print(f"{name:<48}{final:>14,.0f}{worst * 100:>11.0f}%{first:>9.2f}x{second:>9.2f}x")


if __name__ == "__main__":
    main()
