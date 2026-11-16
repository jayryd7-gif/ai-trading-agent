"""
options_live_chart.py - The live version of the three-account options chart, built from the
paper accounts' own records (it grows by one day with every weekday run):

  paper-trading/wheel        Wheel ($10K CAD)
  paper-trading/wheel-ryan   Ryan-style wheel ($200K USD, pretend)
  paper-trading/condor       Iron condors ($10K CAD)

    PYTHONPATH=agents python agents/options_live_chart.py

Writes reports/charts/options-accounts-live.svg (shown on the dashboard).
"""

import csv
import json
import os
from datetime import date

import overview_chart as C

OUT = os.path.join("reports", "charts", "options-accounts-live.svg")
ACCOUNTS = [
    {"folder": "paper-trading/wheel", "name": "Wheel", "short": "Wheel", "sub": "$10K CAD · cheaper stocks",
     "color": C.BLUE, "cur": "CAD"},
    {"folder": "paper-trading/wheel-ryan", "name": "Ryan-style wheel", "short": "Ryan-style",
     "sub": "$200K USD (pretend) · his stocks", "color": C.ORANGE, "cur": "USD"},
    {"folder": "paper-trading/condor", "name": "Iron condors", "short": "Condors", "sub": "$10K CAD · SPY + QQQ",
     "color": C.AQUA, "cur": "CAD"},
]


def money(v, cur):
    v = round(v)
    return f"{'+' if v >= 0 else '−'}${abs(v):,} {cur}"


def load(acc):
    try:
        st = json.load(open(os.path.join(acc["folder"], "state.json")))
    except (OSError, ValueError):
        return None
    trades = []
    path = os.path.join(acc["folder"], "trades.csv")
    if os.path.exists(path):
        trades = list(csv.DictReader(open(path)))
    return st, trades


def build():
    out = []
    for acc in ACCOUNTS:
        a = dict(acc, series=[], markers=[], chips=[], sections=[("Best trades", []), ("Worst trades", [])],
                 headline="—", headline_sub="starts on the first weekday run")
        got = load(acc)
        if got:
            st, trades = got
            fx = st["fx"]
            hist = st.get("history", [])
            a["series"] = [(h["date"], (h["equity_usd"] / st["start_usd"] - 1) * 100) for h in hist]
            if hist:
                pct = (hist[-1]["equity_usd"] / st["start_usd"] - 1) * 100
                a["headline"] = C._fmt(pct, "%")
                a["headline_sub"] = f"{money((hist[-1]['equity_usd'] - st['start_usd']) / fx, acc['cur'])} since {st['started'][5:]}"
            tickers = sorted({t["ticker"] for t in trades} | set(st.get("positions", {})))
            a["chips"] = tickers
            closed = [t for t in trades if t.get("pnl_usd") not in ("", None)]
            for t in closed:
                t["_pnl"] = float(t["pnl_usd"]) / fx
                t["_day"] = t["time_ny"][:10]
            best = sorted([t for t in closed if t["_pnl"] >= 0], key=lambda t: -t["_pnl"])[:3]
            worst = sorted([t for t in closed if t["_pnl"] < 0], key=lambda t: t["_pnl"])[:3]

            def row(t, arrow):
                d = date.fromisoformat(t["_day"])
                return (arrow, f"{d:%b} {d.day}, {d:%Y}", money(t["_pnl"], acc["cur"]), t["ticker"])

            a["sections"] = [("Best trades", [row(t, "▲") for t in best]),
                             ("Worst trades", [row(t, "▼") for t in worst])]
            line = {d: v for d, v in a["series"]}
            for kind, rows in (("best", best[:2]), ("worst", worst[:2])):
                for t in rows:
                    on = [d for d in sorted(line) if d <= t["_day"]]
                    if on:
                        lbl = f"{money(t['_pnl'], '').strip()} {t['ticker']}"
                        a["markers"].append((on[-1], line[on[-1]], kind, lbl))
        out.append(a)
    return out


def main():
    accounts = build()
    started = [a for a in accounts if len(a["series"]) >= 1]
    sub = ("% up or down for each paper account, one point per weekday · ▲▼ = best / worst closed trades · "
           "real Yahoo option prices")
    svg = C.draw("Options paper accounts: live", sub, accounts, unit="%",
                 footnote="Accounts differ in size, so compare by %. Dollar amounts are in each account's own "
                          "currency. Paper only, not financial advice.",
                 empty="Starts filling in after the first weekday run (2:37 PM New York)")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w").write(svg)
    print(f"wrote {OUT} ({len(started)} accounts with data)")


if __name__ == "__main__":
    main()
