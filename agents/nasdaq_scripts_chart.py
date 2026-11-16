"""
nasdaq_scripts_chart.py - Overview chart of your three Nasdaq TradingView scripts, from their
"List of trades" exports in tradingview/exports/:

  MAMBA NQ - Breakout Scalp (50K tracking)          (with the retest entry)
  OPENING RANGE - Session Breakout (tracking)
  Session Breakout - Tradeify 50K Auto

Running profit per script with the best / worst trades marked, a card per script (best and
worst trades: % of the 50K account, contracts, how far it went against you, minutes in the
trade) and a card with the best entry times across all three.

    python3 agents/nasdaq_scripts_chart.py

Export each script in TradingView: Strategy Tester > List of trades > download (CSV), then
double-click tradingview/update-exports.command. Writes reports/charts/nasdaq-scripts.svg.
"""

import csv
import glob
import os
import re
import sys
from collections import defaultdict
from datetime import date, datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import overview_chart as C  # noqa: E402

EXPORTS = os.path.join("tradingview", "exports")
OUT = os.path.join("reports", "charts", "nasdaq-scripts.svg")
ACCOUNT = 50_000
BAR_MINUTES = 5
SCRIPTS = [  # (how to recognise the export file name, card name, short line label, colour)
    (lambda n: "MAMBA" in n.upper(), "MAMBA NQ (retest)", "MAMBA", C.BLUE),
    (lambda n: "OPENING_RANGE" in n.upper() or "OPENING RANGE" in n.upper(), "Opening Range", "Opening Range", C.ORANGE),
    (lambda n: "SESSION_BREAKOUT" in n.upper() and "TRADEIFY" in n.upper(), "Session Breakout 50K", "Session BO", C.AQUA),
]


def money(v):
    v = round(v)
    return f"{'+' if v >= 0 else '−'}${abs(v):,}"


def newest(match):
    files = [p for p in glob.glob(os.path.join(EXPORTS, "*MNQ1!*.csv")) if match(os.path.basename(p))]
    if not files:
        return None

    def key(p):
        d = re.search(r"(\d{4}-\d{2}-\d{2})", os.path.basename(p))
        return (d.group(1) if d else "", os.path.getmtime(p))
    return max(files, key=key)


def trades(path):
    """One position per trade number: entry, exit, contracts, net, how far it went against, bars."""
    by = defaultdict(dict)
    with open(path, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            t = by[r["Trade number"]]
            if r["Type"].startswith("Entry"):
                t["entry"] = r["Date and time"]
                t["side"] = r["Type"].split()[1]
                t["contracts"] = int(float(r["Size (qty)"] or 0))
                t["net"] = float(r["Net PnL USD"] or 0)
                t["against"] = abs(float(r.get("Adverse excursion USD") or 0))
                t["bars"] = int(float(r.get("Duration (bars)") or 0))
            else:
                t["exit"] = r["Date and time"]
    out = [t for t in by.values() if "entry" in t]
    # TradingView lists each target as its own "trade": merge rows with the same entry time and side
    merged = {}
    for t in out:
        k = (t["entry"], t["side"])
        m = merged.setdefault(k, dict(t, contracts=0, net=0.0, against=0.0, bars=0))
        m["contracts"] += t["contracts"]
        m["net"] += t["net"]
        m["against"] = max(m["against"], t["against"])
        m["bars"] = max(m["bars"], t["bars"])
        m["exit"] = max(m.get("exit", ""), t.get("exit", ""))
    rows = sorted(merged.values(), key=lambda t: t["entry"])
    for t in rows:
        t["day"] = t["entry"][:10]
        t["pct"] = t["net"] / ACCOUNT * 100
        t["min"] = t["bars"] * BAR_MINUTES if t["bars"] else None
        try:
            mins = (datetime.fromisoformat(t["exit"]) - datetime.fromisoformat(t["entry"])).total_seconds() / 60
            t["min"] = int(mins) if mins >= 0 else t["min"]
        except (KeyError, ValueError):
            pass
    return rows


def length_text(m):
    if m is None:
        return "?"
    return f"{m} min" if m < 90 else f"{m / 60:.1f} h"


def build():
    accounts, everything, period = [], [], []
    for match, name, short, color in SCRIPTS:
        path = newest(match)
        ts = trades(path) if path else []
        everything += [(short, t) for t in ts]
        series, run = [], 0.0
        for t in ts:
            run += t["net"]
            if series and series[-1][0] == t["day"]:
                series[-1] = (t["day"], run)
            else:
                series.append((t["day"], run))
        if ts:
            period += [ts[0]["day"], ts[-1]["day"]]
        wins = [t for t in ts if t["net"] > 0]
        best = sorted(wins, key=lambda t: -t["net"])[:3]
        worst = sorted([t for t in ts if t["net"] < 0], key=lambda t: t["net"])[:3]
        line = dict(series)
        markers = [(t["day"], line[t["day"]], kind, f"{money(t['net'])} {short}")
                   for kind, rows in (("best", best[:2]), ("worst", worst[:2])) for t in rows]

        def row(t, arrow):
            d = date.fromisoformat(t["day"])
            return (arrow, f"{d:%b} {d.day}", f"{money(t['net'])} ({t['pct']:+.1f}%)",
                    f"{t['contracts']} contracts · went ${t['against']:,.0f} against · "
                    f"{length_text(t['min'])} · {t['side']}")

        total = sum(t["net"] for t in ts)
        mins = [t["min"] for t in ts if t["min"] is not None]
        peak = dd = run2 = 0.0
        for t in ts:
            run2 += t["net"]
            peak = max(peak, run2)
            dd = max(dd, peak - run2)
        accounts.append({
            "name": name, "short": short, "color": color, "two_line": True,
            "sub": (f"{len(ts)} trades · {ts[0]['day'][5:]} to {ts[-1]['day'][5:]}" if ts else "no export yet"),
            "series": series, "markers": markers,
            "headline": money(total) if ts else "—",
            "headline_sub": (f"{total / ACCOUNT * 100:+.1f}% of 50K · {len(wins)}/{len(ts)} won" if ts
                             else "export its List of trades"),
            "chips": ([f"avg {sum(t['contracts'] for t in ts) / len(ts):.1f} contracts",
                       f"avg {length_text(round(sum(mins) / len(mins)))} in trade" if mins else "",
                       f"worst drop {money(-dd)}",
                       f"{sum(t['side'] == 'long' for t in ts)} long / {sum(t['side'] == 'short' for t in ts)} short"]
                      if ts else []),
            "sections": [("Best trades", [row(t, "▲") for t in best]), ("Worst trades", [row(t, "▼") for t in worst])],
        })
        accounts[-1]["chips"] = [c for c in accounts[-1]["chips"] if c]

    hours = defaultdict(lambda: [0.0, 0, 0])
    for short, t in everything:
        h = int(t["entry"][11:13])
        b = hours[h]
        b[0] += t["net"]
        b[1] += 1
        b[2] += t["net"] > 0
    ranked = sorted(hours.items(), key=lambda kv: -kv[1][0])

    def hour_row(kv, arrow):
        h, (net, n, w) = kv
        return (arrow, f"{h % 12 or 12}{'pm' if h >= 12 else 'am'}", money(net), f"{w}/{n} won")

    win_m = [t["min"] for _, t in everything if t["net"] > 0 and t["min"] is not None]
    loss_m = [t["min"] for _, t in everything if t["net"] < 0 and t["min"] is not None]
    top = max(everything, key=lambda st: st[1]["pct"]) if everything else None
    accounts.append({
        "name": "Best times & trade length", "short": "", "color": C.NEUTRAL, "series": [], "markers": [],
        "sub": "all three scripts · entry time (chart time)",
        "headline": f"{top[1]['pct']:+.1f}%" if top else "—",
        "headline_sub": f"best trade ({top[0]}, {top[1]['day'][5:]})" if top else "",
        "chips": [c for c in (f"winners avg {length_text(round(sum(win_m) / len(win_m)))}" if win_m else "",
                              f"losers avg {length_text(round(sum(loss_m) / len(loss_m)))}" if loss_m else "") if c],
        "sections": [("Most money made (entry hour)", [hour_row(kv, "▲") for kv in ranked[:4] if kv[1][0] > 0]),
                     ("Most money lost (entry hour)",
                      [hour_row(kv, "▼") for kv in sorted(ranked, key=lambda kv: kv[1][0])[:3] if kv[1][0] < 0])],
    })
    return accounts, sorted(period)


def main():
    accounts, period = build()
    sub = (f"Running profit per script · {period[0]} to {period[-1]} · from TradingView's List of trades · "
           f"% = share of the 50K account" if period else "Export each script's List of trades from TradingView")
    svg = C.draw("Nasdaq scripts: MAMBA vs Opening Range vs Session Breakout", sub, accounts, unit="$",
                 footnote="went against = the furthest the trade moved against you before it closed · "
                          "TradingView backtest/forward results, not real money.",
                 empty="Waiting for the TradingView exports (List of trades) of the three scripts")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w").write(svg)
    print(f"wrote {OUT}: " + ", ".join(f"{a['name']} {a['headline']}" for a in accounts[:3]))


if __name__ == "__main__":
    main()
