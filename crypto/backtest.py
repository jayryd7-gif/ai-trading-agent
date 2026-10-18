"""
backtest.py - Test the session breakout rules on crypto, over a full year.

Run it from the project folder:
    python crypto/backtest.py                 (BTC and ETH, every combination)
    python crypto/backtest.py BTC-USD

The rules are the futures rules (key levels from the previous session, a
breakout candle plus a confirming candle in the first 30 minutes, stop at the
far end of the two candles, 3 targets selling 1/5, 2/5, 2/5, stop to Target 1
after Target 2, close at the session end). What changes for crypto:

- Crypto trades all day, every day, so a "session" is a time window we pick:
  the New York open, the Tokyo open, the London open, or the whole UTC day.
- Prices range widely over a year, so targets are a percent of the entry
  price instead of fixed points.
- Each trade is a $10,000 position. Results are in dollars per trade.
- Fees matter a lot in crypto. Results are shown before fees and after the
  fee levels in FEES (charged on the way in and on the way out).

HOW TO READ IT: picking the best of many combinations on past data always
finds something by luck. The table ranks combinations using only the FIRST
half of the year, then shows the SECOND half, which they never saw. Trust a
rule only if it also made money in the second half, after fees.
"""

import itertools
import os
import sys
from datetime import timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import main
from crypto_data import load_candles
from key_levels import check_breakout, find_key_levels
from risk import manage_trade, new_trade

# ---------------- SETTINGS ----------------
DAYS = 365
POSITION = 10000                 # dollars per trade
WINDOW = 30                      # minutes after the open to look for a breakout
FEES = {"no fees": 0.0, "0.1% (low-fee exchange)": 0.1,
        "0.4% (Coinbase / Kraken, small account)": 0.4}   # percent per side
SESSIONS = {
    "New York open": {"open": (9, 30), "zone": "America/New_York", "minutes": 390},
    "Tokyo open": {"open": (9, 0), "zone": "Asia/Tokyo", "minutes": 480},
    "London open": {"open": (8, 0), "zone": "Europe/London", "minutes": 480},
    "UTC day": {"open": (0, 0), "zone": "UTC", "minutes": 1440},
}
SEARCH = {
    "session": list(SESSIONS),
    "spacing": [0.15, 0.25, 0.5, 1.0, "risk"],   # percent of price, or 1R/2R/3R
    "weekdays_only": [True, False],
}
# ------------------------------------------


def play(session, start, key_high, key_low, spacing):
    """Returns (gross profit in dollars, fees as a share of notional) or None."""
    window = timedelta(minutes=WINDOW)
    for i, (moment, candle) in enumerate(session):
        if moment - start >= window or i + 1 >= len(session):
            return None
        direction = check_breakout(candle, key_high, key_low)
        if direction is None:
            continue
        second = session[i + 1][1]
        if check_breakout(second, key_high, key_low) != direction:
            continue
        long = direction == "long"
        entry = second.close
        stop = min(candle.low, second.low) if long else max(candle.high, second.high)
        if abs(entry - stop) <= 0:
            continue
        trade = new_trade("gold", direction, entry, stop, [1, 2, 2])
        trade["point_value"] = POSITION / entry / 5      # each "contract" is 1/5 of the position
        trade["spacing"] = abs(entry - stop) if spacing == "risk" else entry * spacing / 100
        exit_value = 0.0                                  # dollars of position sold, for fees
        for _, c in session[i + 2:]:
            before = trade["contracts"]
            actions, trade = manage_trade(trade, c.high, c.low)
            for a in actions:
                if "price" in a and "contracts" in a:
                    exit_value += a["price"] * a["contracts"] * trade["point_value"]
            if trade["contracts"] == 0:
                break
        if trade["contracts"] > 0:
            last = session[-1][1].close
            points = last - entry if long else entry - last
            trade["banked"] += points * trade["point_value"] * trade["contracts"]
            exit_value += last * trade["contracts"] * trade["point_value"]
        return trade["banked"], (POSITION + exit_value) / POSITION
    return None


def run(candles, opt, prepared_cache):
    key = (opt["session"], opt["weekdays_only"])
    if key not in prepared_cache:
        config = SESSIONS[opt["session"]]
        sessions = main.group_into_sessions(candles, config)
        if opt["weekdays_only"]:
            sessions = {s: v for s, v in sessions.items() if s.weekday() < 5}
        prepared_cache[key] = sessions
    sessions = prepared_cache[key]
    config = SESSIONS[opt["session"]]
    starts = list(sessions)
    results = []
    for i in range(1, len(starts)):
        prev = main.previous_full_session(sessions, starts, i, config)
        if prev is None:
            continue
        key_high, key_low = find_key_levels([c for _, c in sessions[prev]])
        out = play(sessions[starts[i]], starts[i], key_high, key_low, opt["spacing"])
        if out:
            results.append((starts[i], *out))
    return results


def stats(results, fee_pct, middle):
    nets = [(d, g - turnover * POSITION * fee_pct / 100) for d, g, turnover in results]
    profits = [n for _, n in nets]
    wins = [p for p in profits if p > 0]
    losses = -sum(p for p in profits if p < 0)
    return {"trades": len(profits),
            "win": f"{len(wins) / len(profits) * 100:.0f}%" if profits else "n/a",
            "total": sum(profits),
            "pf": f"{sum(wins) / losses:.2f}" if losses else "n/a",
            "first": sum(n for d, n in nets if d < middle),
            "second": sum(n for d, n in nets if d >= middle)}


def describe(opt):
    spacing = "1R/2R/3R" if opt["spacing"] == "risk" else f"{opt['spacing']}% apart"
    return (f"{opt['session']}, targets {spacing}, "
            f"{'weekdays' if opt['weekdays_only'] else 'every day'}")


def print_table(title, rows):
    print(title)
    header = f"{'Rules':<52}{'Trades':>7}{'Win %':>7}{'Total $':>10}{'PF':>7}{'1st half':>10}{'2nd half':>10}"
    print(header)
    print("-" * len(header))
    for name, s in rows:
        print(f"{name[:51]:<52}{s['trades']:>7}{s['win']:>7}{s['total']:>10.0f}{s['pf']:>7}"
              f"{s['first']:>10.0f}{s['second']:>10.0f}")
    print()


def main_run(products):
    for product in products:
        candles = load_candles(product, days=DAYS)
        first, last = candles[0].time[:10], candles[-1].time[:10]
        middle = main.parse_time(candles[len(candles) // 2].time)
        print(f"\n######## {product}: {first} to {last}, halves split at {middle:%Y-%m-%d} ########\n")
        cache, combos = {}, []
        for values in itertools.product(*SEARCH.values()):
            opt = dict(zip(SEARCH, values))
            combos.append((opt, run(candles, opt, cache)))

        for fee_name, fee in FEES.items():
            rows = [(describe(o), stats(r, fee, middle)) for o, r in combos]
            rows = [r for r in rows if r[1]["trades"] >= 20]
            top = sorted(rows, key=lambda r: r[1]["first"], reverse=True)[:8]
            both = [r for r in rows if r[1]["first"] > 0 and r[1]["second"] > 0]
            print_table(f"== Fees {fee_name}: top 8 picked on the FIRST half "
                        f"({len(both)} of {len(rows)} made money in both halves) ==", top)


if __name__ == "__main__":
    wanted = [a for a in sys.argv[1:] if a.endswith("-USD")]
    main_run(wanted or ["BTC-USD", "ETH-USD"])
