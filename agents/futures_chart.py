"""
futures_chart.py - Overview chart of the Nasdaq and gold paper trades (paper-trading/trades.csv):
running profit per market with the best and worst trades marked, and a card per market with
the best / worst trades (% of the account, contracts, money risked, minutes in the trade)
plus a card with the best times of day and how long winning trades lasted.

    PYTHONPATH=agents:. python agents/futures_chart.py

Writes reports/charts/futures-trades.svg (shown on the dashboard).
"""

import csv
import os
from collections import defaultdict
from datetime import date, datetime, timedelta

import overview_chart as C

TRADES = os.path.join("paper-trading", "trades.csv")
OUT = os.path.join("reports", "charts", "futures-trades.svg")
ACCOUNT = 50_000          # the Tradeify 50K practice account the paper trader sizes for
# Nasdaq now comes from the three TradingView scripts (agents/nasdaq_scripts_chart.py);
# this chart shows the gold paper trades.
MARKETS = [("gold", "Gold", "MGC micro futures · paper", C.ORANGE)]


def money(v):
    v = round(v)
    return f"{'+' if v >= 0 else '−'}${abs(v):,}"


def minutes(t):
    try:
        a = datetime.strptime(t["entry_time"], "%H:%M")
        b = datetime.strptime(t["exit_time"], "%H:%M")
    except ValueError:
        return None
    m = (b - a).total_seconds() / 60
    return int(m + 1440 if m < 0 else m)


def load():
    if not os.path.exists(TRADES):
        return []
    rows = []
    for t in csv.DictReader(open(TRADES)):
        if t.get("signal") != "yes" or t.get("contracts") in ("", "0", None) or not t.get("net"):
            continue
        t["_net"] = float(t["net"])
        t["_pct"] = t["_net"] / ACCOUNT * 100
        t["_ct"] = int(float(t["contracts"]))
        t["_risk"] = float(t["worst_dollars"]) if t.get("worst_dollars") else None
        t["_min"] = minutes(t)
        # the session the trade belongs to: gold's evening session counts on its start date
        t["_day"] = (t.get("session_start") or t["trading_day"])[:10]
        if t["instrument"] in {m[0] for m in MARKETS}:
            rows.append(t)
    return rows


def length_text(m):
    if m is None:
        return "?"
    return f"{m} min" if m < 90 else f"{m / 60:.1f} h"


def detail(t):
    risk = f"${t['_risk']:,.0f} risk" if t["_risk"] else "risk ?"
    return f"{t['_ct']} contracts · {risk} · {length_text(t['_min'])} in trade · {t['direction']}"


def build(trades):
    accounts = []
    for key, name, sub, color in MARKETS:
        ts = sorted([t for t in trades if t["instrument"] == key], key=lambda t: (t["_day"], t["entry_time"]))
        series, run = [], 0.0
        for t in ts:
            run += t["_net"]
            if series and series[-1][0] == t["_day"]:
                series[-1] = (t["_day"], run)
            else:
                series.append((t["_day"], run))
        if series:
            first = date.fromisoformat(series[0][0]) - timedelta(days=1)
            series = [(first.isoformat(), 0.0)] + series
        wins = [t for t in ts if t["_net"] > 0]
        best = sorted(wins, key=lambda t: -t["_net"])[:3]
        worst = sorted([t for t in ts if t["_net"] < 0], key=lambda t: t["_net"])[:3]
        line = dict(series)
        markers = []
        for kind, rows in (("best", best[:2]), ("worst", worst[:2])):
            for t in rows:
                markers.append((t["_day"], line[t["_day"]], kind, f"{money(t['_net'])} {t['direction']}"))

        def row(t, arrow):
            d = date.fromisoformat(t["_day"])
            return (arrow, f"{d:%b} {d.day}", f"{money(t['_net'])} ({t['_pct']:+.1f}%)", detail(t))

        total = sum(t["_net"] for t in ts)
        risks = [t["_risk"] for t in ts if t["_risk"]]
        mins = [t["_min"] for t in ts if t["_min"] is not None]
        accounts.append({
            "name": name, "short": name, "sub": sub, "two_line": True,
            "color": color, "series": series, "markers": markers,
            "headline": money(total) if ts else "—",
            "headline_sub": (f"{total / ACCOUNT * 100:+.1f}% of 50K · {len(wins)}/{len(ts)} won" if ts else "no trades yet"),
            "chips": ([f"{len(ts)} trades", f"avg {sum(t['_ct'] for t in ts) / len(ts):.1f} contracts",
                       f"avg ${sum(risks) / len(risks):,.0f} risked" if risks else "risk ?",
                       f"avg {length_text(round(sum(mins) / len(mins)))} in trade" if mins else "",
                       f"{sum(t['direction'] == 'long' for t in ts)} long / {sum(t['direction'] == 'short' for t in ts)} short"]
                      if ts else []),
            "sections": [("Best trades", [row(t, "▲") for t in best]), ("Worst trades", [row(t, "▼") for t in worst])],
        })
        accounts[-1]["chips"] = [c for c in accounts[-1]["chips"] if c]

    # third card: when the money was made
    by_hour = defaultdict(lambda: [0.0, 0, 0])
    for t in trades:
        h = t["entry_time"][:2]
        mk = "NQ" if t["instrument"] == "nasdaq" else "Gold"
        b = by_hour[(mk, h)]
        b[0] += t["_net"]
        b[1] += 1
        b[2] += t["_net"] > 0
    hours = sorted(by_hour.items(), key=lambda kv: -kv[1][0])

    def hour_row(kv, arrow):
        (mk, h), (net, n, w) = kv
        return (arrow, f"{mk} {int(h) % 12 or 12}{'pm' if int(h) >= 12 else 'am'}", money(net), f"{w}/{n} won")

    wins = [t for t in trades if t["_net"] > 0 and t["_min"] is not None]
    losses = [t for t in trades if t["_net"] < 0 and t["_min"] is not None]
    best_pct = max(trades, key=lambda t: t["_pct"]) if trades else None
    accounts.append({
        "name": "Best times & trade length", "short": "", "sub": "entry time in New York",
        "color": C.AQUA, "series": [], "markers": [],
        "headline": f"{best_pct['_pct']:+.1f}%" if best_pct else "—",
        "headline_sub": (f"best single trade ({best_pct['instrument']}, {best_pct['_day'][5:]})" if best_pct else ""),
        "chips": ([f"winners avg {length_text(round(sum(t['_min'] for t in wins) / len(wins)))}" if wins else "",
                   f"losers avg {length_text(round(sum(t['_min'] for t in losses) / len(losses)))}" if losses else ""]),
        "sections": [("Most money made (entry hour)", [hour_row(kv, "▲") for kv in hours[:3] if kv[1][0] > 0]),
                     ("Most money lost (entry hour)", [hour_row(kv, "▼") for kv in sorted(hours, key=lambda kv: kv[1][0])[:3]
                                                      if kv[1][0] < 0])],
    })
    accounts[-1]["chips"] = [c for c in accounts[-1]["chips"] if c]
    return accounts


def main():
    trades = load()
    accounts = build(trades)
    lines = [a for a in accounts if a["series"]]
    days = sorted({t["_day"] for t in trades})
    sub = (f"Running profit per market · {days[0]} to {days[-1]} · ▲▼ = best / worst trades · "
           "% = share of the 50K practice account" if days else "Running profit per market")
    svg = C.draw("Gold paper trades", sub, lines + [accounts[-1]] if lines else accounts, unit="$",
                 footnote="ct = contracts · risk = money lost if the stop is hit · paper trades from "
                          "agents/paper_trader.py, not real money.")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w").write(svg)
    print(f"wrote {OUT} ({len(trades)} trades)")


if __name__ == "__main__":
    main()
