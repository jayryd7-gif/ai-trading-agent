"""
mamba_log.py - A permanent record of every MAMBA trade (tracking only).

TradingView's Strategy Tester only replays the bars a chart has loaded (about
2 months of 5-minute bars), so old MAMBA trades fall out of its Overview. This
keeps them: each run replays the last 60 days with the same rules as
tradingview/mamba_nq_strategy.pine (experiments/mamba_test.py) and ADDS any
finished session not already in paper-trading/mamba.csv. Rows are never
changed or removed, so the totals cover everything since the first run.

  Nasdaq: 9:30-11:00 AM, break of the last 30 minutes' structure on a strong
          close, skipped when it closes under 10 points past the 7:30-9:30
          high/low; 2/2/1 at 30/60/90 points + 1 runner to 300; stop 5 points
          past each target candle.
  Gold:   8-10 PM (night session), same entry; 2/2/1 at 6/12/18 points + 1
          runner to 60; stop 1 point past each target candle.

Yahoo's NQ=F / GC=F prices can differ a little from TradingView's MNQ / MGC,
so a trade here can now and then differ from the chart.

Run: python agents/mamba_log.py   (the paper trading workflow runs it)
"""
import csv
import os
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [ROOT, os.path.join(ROOT, "agents"), os.path.join(ROOT, "experiments")]

import mamba_test as M
from data import SYMBOLS, load_from_yahoo

CSV_PATH = os.path.join(ROOT, "paper-trading", "mamba.csv")
FIELDS = ["day", "market", "direction", "entry_time", "entry", "stop", "exit_time", "net"]
COMMON = dict(lookback=6, target_r=1.0, push=1.0, stop_mode="candle", before=0,
              plan=(2, 2, 1, 1))
SETTINGS = {
    "nasdaq": dict(COMMON, after=90, near_key=10, exits=("pts", [30, 60, 90, 300]),
                   moves={1: ("candle", 5), 2: ("candle", 5), 3: ("candle", 5)}),
    "gold": dict(COMMON, after=120, open_at=(20, 0), exits=("pts", [6, 12, 18, 60]),
                 moves={1: ("candle", 1), 2: ("candle", 1), 3: ("candle", 1)}),
}
# A session counts as finished (safe to record) this long after its open.
FINISHED_AFTER = {"nasdaq": timedelta(hours=6, minutes=30), "gold": timedelta(hours=8)}
OPENS = {"nasdaq": (9, 30), "gold": (20, 0)}


def read_rows():
    if not os.path.exists(CSV_PATH):
        return []
    with open(CSV_PATH, newline="") as f:
        return list(csv.DictReader(f))


def new_rows(now, done):
    rows = []
    for market, cfg in SETTINGS.items():
        data = {market: load_from_yahoo(SYMBOLS[market], "5m", "60d")}
        M.mamba(market, data, 60, **cfg)
        for t in M.mamba.details:
            key = (t["day"].isoformat(), market)
            hour, minute = OPENS[market]
            opened = datetime(t["day"].year, t["day"].month, t["day"].day, hour, minute)
            if key in done or opened + FINISHED_AFTER[market] > now:
                continue
            rows.append({"day": key[0], "market": market, "direction": t["direction"],
                         "entry_time": f"{t['entry_time']:%H:%M}", "entry": t["entry"],
                         "stop": t["stop"], "exit_time": f"{t['exit_time']:%Y-%m-%d %H:%M}",
                         "net": t["net"]})
    return rows


def summary(rows):
    """One line per market and in total, for the dashboard."""
    out = []
    for market in ("nasdaq", "gold", None):
        mine = [float(r["net"]) for r in rows if market is None or r["market"] == market]
        if not mine:
            continue
        won = sum(n > 0 for n in mine)
        gw, gl = sum(n for n in mine if n > 0), -sum(n for n in mine if n < 0)
        pf = f"{gw / gl:.2f}" if gl else "no losses"
        name = {"nasdaq": "Nasdaq", "gold": "Gold (night)", None: "**Total**"}[market]
        net = sum(mine)
        out.append(f"| {name} | {len(mine)} | {won} ({won / len(mine):.0%}) | {pf} | "
                   f"{'-$' if net < 0 else '$'}{abs(net):,.0f} |")
    return out


def main(now=None):
    now = now or datetime.now(ZoneInfo("America/New_York")).replace(tzinfo=None)
    rows = read_rows()
    done = {(r["day"], r["market"]) for r in rows}
    added = new_rows(now, done)
    rows = sorted(rows + added, key=lambda r: (r["day"], r["market"]))
    os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)
    with open(CSV_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"MAMBA log: {len(added)} new trade(s), {len(rows)} in total.")


if __name__ == "__main__":
    main()
