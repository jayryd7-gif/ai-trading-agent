"""
gold_variations.py - Test changes to the breakout rules on past data, side by
side with the current rules.

Run it from the project folder:
    python experiments/gold_variations.py              (gold, the variation table)
    python experiments/gold_variations.py nasdaq       (same table for Nasdaq)
    python experiments/gold_variations.py gold search  (try many combinations)

It uses the same pieces as main.py (key levels, breakout check, the 3-target
trade manager) and changes one or a few things per variation. Nothing here
changes trading-rules.md or main.py.

HOW TO READ THE SEARCH. Trying many combinations on a few dozen trades will
always turn up something that looks great by luck. So the search picks its
favorites using only the FIRST half of the data, then shows how those same
rules did on the SECOND half, which they never saw. Only trust a rule that
also made money in the second half.

This is a replay on past data. A rule that looks good here can still fail
going forward.
"""

import itertools
import os
import sys
from datetime import timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import risk
from data import SYMBOLS, load_from_yahoo
from key_levels import check_breakout, find_key_levels
from main import ENTRY_WINDOW_MINUTES, SESSIONS, group_into_sessions, parse_time
from risk import manage_trade, new_trade

PERIOD = "60d"   # Yahoo keeps about 60 days of 5-minute candles

BASE = {"window": ENTRY_WINDOW_MINUTES, "min_stop": 0, "stop_floor": 0,
        "confirm": False, "spacing": None, "breakeven_at_t1": False,
        "retest": False, "skip_if_range_above": None, "trend": False,
        "momentum": None, "levels": "previous session", "open": None}

VARIATIONS = [
    ("Current rules", {}),
    ("Skip tiny breakout candles (stop under 3 pts)", {"min_stop": 3}),
    ("Stop at least 6 pts away", {"stop_floor": 6}),
    ("Wait for a 2nd candle to confirm", {"confirm": True}),
    ("Enter on a retest of the level", {"retest": True}),
    ("Move stop to breakeven at Target 1", {"breakeven_at_t1": True}),
    ("Look for breakouts for 30 minutes", {"window": 30}),
    ("Look for breakouts for 45 minutes", {"window": 45}),
    ("Skip when the previous range was wide (>1.5x average)", {"skip_if_range_above": 1.5}),
    ("Only trade with the 24-hour trend", {"trend": True}),
    ("Only strong breakout candles (1.5x normal size)", {"momentum": 1.5}),
    ("Key levels from the last 24 hours", {"levels": "last 24 hours"}),
    ("Targets 4 pts apart (smaller)", {"spacing": 4}),
    ("Targets 8 pts apart (bigger)", {"spacing": 8}),
    ("Combo: confirm + skip wide ranges", {"confirm": True, "skip_if_range_above": 1.5}),
    ("Combo: confirm + breakeven at Target 1", {"confirm": True, "breakeven_at_t1": True}),
]

# Choices the search combines. The window stays inside the 30-45 minutes the
# trader asked for.
SEARCH = {
    "window": [30, 45],
    "confirm": [False, True],
    "skip_if_range_above": [None, 1.5],
    "breakeven_at_t1": [False, True],
    "trend": [False, True],
    "momentum": [None, 1.5],
    "levels": ["previous session", "last 24 hours"],
    "spacing": [None, 4, 8],
}
MIN_TRADES_PER_HALF = 6

# Other times gold could be traded (hour, minute in New York time).
OTHER_OPENS = [("Current: Tokyo 9:00 AM", (9, 0), "Asia/Tokyo"),
               ("Shanghai 9:00 AM (old 9 PM NY open)", (9, 0), "Asia/Shanghai"),
               ("London 8:00 AM", (8, 0), "Europe/London"),
               ("New York gold open 8:20 AM", (8, 20), "America/New_York")]


def find_entry(session, start, key_high, key_low, opt, normal_size):
    """Return (index, direction, entry, stop, fill_candle) or None."""
    window = timedelta(minutes=opt["window"])
    for i, (moment, candle) in enumerate(session):
        if moment - start >= window:
            return None
        direction = check_breakout(candle, key_high, key_low)
        if direction is None:
            continue
        if opt["trend"] and direction != opt["trend_direction"]:
            continue
        if opt["momentum"] and normal_size and \
                candle.high - candle.low < opt["momentum"] * normal_size:
            continue
        long = direction == "long"
        entry = candle.close
        stop = candle.low if long else candle.high

        if opt["confirm"]:
            if i + 1 >= len(session) or session[i + 1][0] - start >= window + timedelta(minutes=5):
                return None
            nxt = session[i + 1][1]
            if check_breakout(nxt, key_high, key_low) != direction:
                continue   # the breakout did not hold; keep watching
            i, entry = i + 1, nxt.close
            stop = min(candle.low, nxt.low) if long else max(candle.high, nxt.high)

        if opt["retest"]:
            # Limit order at the broken level, good for 60 minutes. The stop
            # keeps the breakout candle's size, measured from the new entry.
            size = candle.high - candle.low
            level = key_high if long else key_low
            for j in range(i + 1, len(session)):
                if session[j][0] - session[i][0] > timedelta(minutes=60):
                    return None
                c = session[j][1]
                if (c.low <= level) if long else (c.high >= level):
                    return (j - 1, direction, level,
                            level - size if long else level + size, c)
            return None

        distance = abs(entry - stop)
        if distance < opt["min_stop"] or distance <= 0:
            continue
        if distance < opt["stop_floor"]:
            stop = entry - opt["stop_floor"] if long else entry + opt["stop_floor"]
        return i, direction, entry, stop, None
    return None


def play(instrument, session, start, key_high, key_low, opt, normal_size):
    found = find_entry(session, start, key_high, key_low, opt, normal_size)
    if found is None:
        return None
    index, direction, entry, stop, fill_candle = found
    trade = new_trade(instrument, direction, round(entry, 2), round(stop, 2),
                      [1, 2, 2] if instrument == "gold" else None)
    if opt["spacing"]:
        trade["spacing"] = opt["spacing"]

    risk.STOP_RULES = {1: "entry", 2: 1} if opt["breakeven_at_t1"] else {2: 1}
    candles = [c for _, c in session[index + 1:]]
    if fill_candle is not None:
        # Retest fill: the fill candle can still stop us out, but give it no
        # credit for targets (we don't know the order of high and low).
        long = direction == "long"
        if (fill_candle.low <= trade["stop_loss"]) if long else (fill_candle.high >= trade["stop_loss"]):
            candles = []
            trade["banked"] = -abs(entry - stop) * trade["point_value"] * trade["contracts"]
            trade["contracts"] = 0
        else:
            candles = candles[1:]
    for c in candles:
        _, trade = manage_trade(trade, c.high, c.low)
        if trade["contracts"] == 0:
            break
    if trade["contracts"] > 0:   # still open at the end of the session
        last = session[-1][1].close
        points = last - entry if direction == "long" else entry - last
        trade["banked"] += points * trade["point_value"] * trade["contracts"]
    risk.STOP_RULES = {2: 1}
    return round(trade["banked"], 2)


def prepare(instrument, candles, open_time=None, zone="America/New_York"):
    """Group candles into sessions (optionally with a different open time)."""
    config = dict(SESSIONS[instrument])
    if open_time:
        config["open"], config["zone"] = open_time, zone
    timed = sorted((parse_time(c.time), c) for c in candles)
    return group_into_sessions(candles, config), timed


def run(instrument, prepared, opt):
    sessions, timed = prepared
    starts = list(sessions)
    ranges = []
    results = []   # (session start, profit)
    for i in range(1, len(starts)):
        prev, start = starts[i - 1], starts[i]
        if (start - prev).days > 4:
            continue
        before = [c for t, c in timed if start - timedelta(hours=24) <= t < start]
        if opt["levels"] == "last 24 hours" and before:
            key_high, key_low = find_key_levels(before)
        else:
            key_high, key_low = find_key_levels([c for _, c in sessions[prev]])
        width = key_high - key_low
        avg = sum(ranges) / len(ranges) if ranges else None
        ranges.append(width)
        if opt["skip_if_range_above"] and avg and width > opt["skip_if_range_above"] * avg:
            continue
        if opt["trend"]:
            if not before:
                continue
            opt["trend_direction"] = "long" if before[-1].close > before[0].close else "short"
        prev_candles = [c for _, c in sessions[prev]]
        normal_size = sum(c.high - c.low for c in prev_candles) / len(prev_candles)
        profit = play(instrument, sessions[start], start, key_high, key_low, opt, normal_size)
        if profit is not None:
            results.append((start, profit))
    return results, len(starts) - 1


def summarize(name, results, middle):
    profits = [p for _, p in results]
    wins = [p for p in profits if p > 0]
    losses = [p for p in profits if p < 0]
    gross_loss = -sum(losses)
    first = [p for d, p in results if d < middle]
    second = [p for d, p in results if d >= middle]
    return {
        "name": name, "trades": len(profits),
        "win_rate": f"{len(wins) / len(profits) * 100:.0f}%" if profits else "n/a",
        "total": sum(profits),
        "avg": sum(profits) / len(profits) if profits else 0,
        "pf": f"{sum(wins) / gross_loss:.2f}" if gross_loss else ("n/a" if not wins else "all wins"),
        "worst": min(profits) if profits else 0,
        "halves": (sum(first), sum(second)), "half_trades": (len(first), len(second)),
    }


HEADER = (f"{'Variation':<58}{'Trades':>7}{'Win %':>7}{'Total $':>10}"
          f"{'Avg $':>8}{'PF':>7}{'Worst $':>9}{'1st half':>10}{'2nd half':>10}")


def print_rows(rows):
    print(HEADER)
    print("-" * len(HEADER))
    for r in rows:
        print(f"{r['name'][:57]:<58}{r['trades']:>7}{r['win_rate']:>7}{r['total']:>10.0f}"
              f"{r['avg']:>8.0f}{r['pf']:>7}{r['worst']:>9.0f}"
              f"{r['halves'][0]:>10.0f}{r['halves'][1]:>10.0f}")


def describe(change):
    parts = []
    for key, value in change.items():
        if value == BASE.get(key) and key != "window":
            continue
        parts.append({"window": f"{value} min",
                      "confirm": "confirm", "breakeven_at_t1": "BE at T1",
                      "trend": "with trend", "skip_if_range_above": "skip wide",
                      "momentum": "strong candle",
                      "levels": "24h levels", "spacing": f"targets {value} pts"}[key])
    return ", ".join(parts)


def search(instrument, prepared, middle):
    keys = list(SEARCH)
    rows = []
    for values in itertools.product(*(SEARCH[k] for k in keys)):
        change = dict(zip(keys, values))
        results, _ = run(instrument, prepared, dict(BASE, **change))
        rows.append(summarize(describe(change), results, middle))
    usable = [r for r in rows if min(r["half_trades"]) >= MIN_TRADES_PER_HALF]
    print(f"Tried {len(rows)} combinations; {len(usable)} had at least "
          f"{MIN_TRADES_PER_HALF} trades in each half.\n")

    print("Top 10, picked using the FIRST half only (the honest test is the 2nd half column):")
    print_rows(sorted(usable, key=lambda r: r["halves"][0], reverse=True)[:10])

    both = [r for r in usable if r["halves"][0] > 0 and r["halves"][1] > 0]
    print(f"\n{len(both)} of {len(usable)} combinations made money in BOTH halves. "
          "Best of those by total:")
    print_rows(sorted(both, key=lambda r: r["total"], reverse=True)[:10])
    return rows


def main():
    instrument = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in SESSIONS else "gold"
    candles = load_from_yahoo(SYMBOLS[instrument], interval="5m", period=PERIOD)
    prepared = prepare(instrument, candles)
    starts = list(prepared[0])
    middle = starts[len(starts) // 2]
    print(f"{SESSIONS[instrument]['name']}: {len(starts)} sessions from "
          f"{starts[0]:%Y-%m-%d} to {starts[-1]:%Y-%m-%d}. "
          f"Halves split at {middle:%Y-%m-%d}.\n")

    if "search" in sys.argv:
        search(instrument, prepared, middle)
    else:
        rows = []
        for name, change in VARIATIONS:
            results, _ = run(instrument, prepared, dict(BASE, **change))
            rows.append(summarize(name, results, middle))
        print_rows(rows)

        if instrument == "gold":
            print("\nSame breakout rules (45-minute window, confirm), "
                  "trading gold at a different time of day:")
            rows = []
            for name, open_time, zone in OTHER_OPENS:
                results, _ = run(instrument, prepare(instrument, candles, open_time, zone),
                                 dict(BASE, window=45, confirm=True))
                rows.append(summarize(name, results, middle))
            print_rows(rows)

    print("\nPF = profit factor: dollars won per dollar lost. Above 1 made money.")
    print("A rule is more trustworthy if both halves made money, not just the total.")


if __name__ == "__main__":
    main()
