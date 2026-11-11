"""
mamba_test.py - A MambaFX-style breakout scalp, as described in public YouTube
tutorials of his breakout strategy (2026-11-04), tested next to the bot's rule.

What the tutorials describe (no official rule book was available):
  - 5-minute chart. Breakout lines on the most recent structure: the high and
    low price has been ranging in just before (here: the last LOOKBACK
    candles).
  - Enter when a candle CLOSES beyond the line with a push (here: its body at
    least PUSH times the average body of those candles), also before the
    official open ("I will enter on these breaks before the 9:30 open").
  - Stop below the structure, with room to breathe.
  - Target the previous structure, or a simple 1:1 to 1:2 risk-to-reward.
    In and out.
Fixed size (6 contracts, like the LIVE script's 2/2/2), $0.50 per contract
fees, no account limits; when a candle touches both the stop and the target,
the stop counts first. One trade per session.

Run: python3 experiments/mamba_test.py
"""
import os
import sys
from datetime import datetime, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [ROOT, os.path.join(ROOT, "agents"), os.path.join(ROOT, "experiments")]

import main as R
import time_test as T
from risk import INSTRUMENTS

CONTRACTS, FEE = 6, 0.5
OPENS = {"nasdaq": (9, 30), "gold": (20, 0)}


def trade(candles, i, d, stop, target_r, pv):
    """Play a trade entered at candles[i]'s close. Returns (dollars, exit time)."""
    entry = candles[i][1].close
    risk = abs(entry - stop)
    target = entry + d * target_r * risk
    for t, c in candles[i + 1:]:
        if (c.low <= stop) if d == 1 else (c.high >= stop):
            return -risk * pv * CONTRACTS - FEE * CONTRACTS, t
        if (c.high >= target) if d == 1 else (c.low <= target):
            return target_r * risk * pv * CONTRACTS - FEE * CONTRACTS, t
    last = candles[-1][1].close
    return d * (last - entry) * pv * CONTRACTS - FEE * CONTRACTS, candles[-1][0]


def trade_partials(candles, i, d, stop, targets, plan, moves, pv):
    """Like trade(), but sells plan[n] contracts at targets[n] (prices) and
    moves the stop after a target: moves = {1: "entry", 2: 1} means
    breakeven after Target 1, Target 1's price after Target 2."""
    entry = candles[i][1].close
    left, banked, hit = sum(plan), 0.0, 0
    for t, c in candles[i + 1:]:
        if (c.low <= stop) if d == 1 else (c.high >= stop):
            banked += d * (stop - entry) * pv * left
            return banked - FEE * sum(plan), t
        while hit < len(targets) and ((c.high >= targets[hit]) if d == 1 else (c.low <= targets[hit])):
            banked += d * (targets[hit] - entry) * pv * plan[hit]
            left -= plan[hit]
            hit += 1
            rule = moves.get(hit)
            if rule == "entry":
                new = entry
            elif isinstance(rule, tuple):         # ("candle", room): under this candle's low
                new = (c.low if d == 1 else c.high) - d * rule[1]
            elif rule is not None:
                new = targets[rule - 1]
            else:
                continue
            if d * (new - stop) > 0:              # only ever tighten the stop
                stop = new
        if left == 0:
            return banked - FEE * sum(plan), t
    banked += d * (candles[-1][1].close - entry) * pv * left
    return banked - FEE * sum(plan), candles[-1][0]


def mamba(instrument, data, days, lookback=12, push=1.0, before=60, after=60,
          target_r=1.0, stop_mode="structure", room=0.0, open_at=None, max_trades=1,
          exits=None, moves=None):
    ev = R.timeline(data[instrument])
    last = ev[-1][0]
    first = (last - timedelta(days=days)).date()
    pv = INSTRUMENTS[instrument]["point_value"]
    hour, minute = open_at or OPENS[instrument]
    results = []
    by_day = {}
    for t, c in ev:
        by_day.setdefault(t.date(), []).append((t, c))
    days_seen = sorted(by_day)
    for day in days_seen:
        if day < first:
            continue
        start = datetime(day.year, day.month, day.day, hour, minute)
        lo, hi = start - timedelta(minutes=before), start + timedelta(minutes=after)
        # candles from the window start to 8 hours after the open (for exits)
        cs = [(t, c) for t, c in ev if lo - timedelta(minutes=5 * lookback) <= t
              <= start + timedelta(hours=8)]
        taken, busy_until = 0, None
        for i in range(lookback, len(cs)):
            t, c = cs[i]
            if busy_until is not None and t <= busy_until:
                continue
            if t < lo:
                continue
            if t >= hi:
                break
            prior = [x for _, x in cs[i - lookback:i]]
            if len(prior) < lookback or (prior and (t - cs[i - lookback][0]) > timedelta(minutes=5 * lookback + 70)):
                continue     # a gap (market closed) inside the structure
            top, bottom = max(x.high for x in prior), min(x.low for x in prior)
            body = abs(c.close - (c.open if c.open is not None else prior[-1].close))
            avg = sum(abs(x.close - (x.open if x.open is not None else x.close)) for x in prior) / lookback
            d = 1 if c.close > top else -1 if c.close < bottom else 0
            if d == 0 or body < push * avg or d * (c.close - (c.open or c.close)) <= 0:
                continue
            if stop_mode == "structure":
                stop = (bottom if d == 1 else top) - d * room
            else:                                   # the breakout candle's far end
                stop = (c.low if d == 1 else c.high) - d * room
            if exits:
                kind, steps = exits
                entry = c.close
                size = abs(entry - stop) if kind == "R" else 1.0
                targets = [entry + d * k * size for k in steps]
                net, out_at = trade_partials(cs, i, d, stop, targets, [2, 2, 2],
                                             moves or {}, pv)
            else:
                net, out_at = trade(cs, i, d, stop, target_r, pv)
            results.append(net)
            taken += 1
            if taken >= max_trades or net > 0:
                break             # a win ends the day; a loss allows another try
            busy_until = out_at
    return results


def line(label, nets):
    w = sum(x for x in nets if x > 0)
    l = -sum(x for x in nets if x < 0) or 1
    won = sum(x > 0 for x in nets)
    return (f"{T.money(sum(nets))} ({won}/{len(nets)} won, "
            f"{won / len(nets):.0%}, PF {w / l:.2f})" if nets else "no trades")


if __name__ == "__main__":
    data = T.candles()
    options = []
    for stop_mode, room in (("candle", 0.0), ("structure", 0.0)):
        for target_r in (1.0, 1.5, 2.0):
            options.append((f"stop at {stop_mode}, target {target_r}R", dict(stop_mode=stop_mode, target_r=target_r, room=room)))
    options.append(("stop at candle, 1R, structure 6 candles", dict(stop_mode="candle", target_r=1.0, lookback=6)))
    options.append(("stop at candle, 1R, no push filter", dict(stop_mode="candle", target_r=1.0, push=0.0)))
    print("| Mamba-style option | Nasdaq 30d | gold 30d | Nasdaq 60d | gold 60d |")
    print("|---|---|---|---|---|")
    for label, kw in options:
        cells = [line(label, mamba(m, data, days, **kw)) for days in (30, 60) for m in ("nasdaq", "gold")]
        print(f"| {label} | " + " | ".join(cells) + " |", flush=True)
