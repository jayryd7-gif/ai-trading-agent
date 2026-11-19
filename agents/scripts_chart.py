"""
scripts_chart.py - Overview charts of your three TradingView scripts on Nasdaq and on gold:

  MAMBA NQ - Breakout Scalp (50K tracking)   (with the retest entry)
  OPENING RANGE - Session Breakout (tracking)
  Session Breakout - Tradeify 50K

The trades come straight from TradingView's Strategy Tester (read by Claude from your chart
layout, saved in tradingview/script-trades/<date>.json, newest file wins). For each market:
running profit per script with the best / worst trades marked, a card per script (best and
worst trades: % of the 50K account, contracts, how far it went against you, minutes in the
trade) and a card with the best entry times across all three.

    python3 agents/scripts_chart.py

Writes reports/charts/nasdaq-scripts.svg and reports/charts/gold-scripts.svg.
"""

import glob
import json
import os
import sys
from collections import defaultdict
from datetime import date, datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import overview_chart as C  # noqa: E402

DATA = os.path.join("tradingview", "script-trades")
ACCOUNT = 50_000
MARKETS = [("MNQ", "Nasdaq", "nasdaq-scripts"), ("MGC", "Gold", "gold-scripts")]
LIVE_FROM = "2026-11-15"      # the "since today" charts count only trades from this date on
SCRIPTS = [  # (TradingView name, card name, short line label, colour)
    ("MAMBA NQ - Breakout Scalp (50K tracking)", "MAMBA (retest)", "MAMBA", C.BLUE),
    ("OPENING RANGE - Session Breakout (tracking)", "Opening Range", "Opening Range", C.ORANGE),
    ("Session Breakout - Tradeify 50K", "Session Breakout 50K", "Session BO", C.AQUA),
]


def money(v):
    v = round(v)
    return f"{'+' if v >= 0 else '−'}${abs(v):,}"


def load(first=False):
    """The newest saved read (or the first one, which holds the Sep 20 - Nov 15 results
    before TradingView dropped the oldest bars)."""
    files = sorted(glob.glob(os.path.join(DATA, "*.json")))
    return json.load(open(files[0 if first else -1])) if files else None


def trades(raw):
    """[entry 'YYYY-MM-DD HH:MM', exit 'HH:MM', 'l'/'s', contracts, net, against] -> dicts."""
    rows = []
    for e, x, side, ct, net, against in raw:
        a = datetime.strptime(e[11:16], "%H:%M")
        b = datetime.strptime(x, "%H:%M")
        m = int((b - a).total_seconds() / 60)
        rows.append({"entry": e, "day": e[:10], "side": "long" if side == "l" else "short", "contracts": ct,
                     "net": net, "pct": net / ACCOUNT * 100, "against": against, "min": m + 1440 if m < 0 else m})
    return rows


def length_text(m):
    if m is None:
        return "?"
    return f"{m} min" if m < 90 else f"{m / 60:.1f} h"


def build(market_data, since=None):
    accounts, everything, period = [], [], []
    for tv_name, name, short, color in SCRIPTS:
        ts = trades(market_data[tv_name]["trades"]) if market_data and tv_name in market_data else []
        if since:
            ts = [t for t in ts if t["day"] >= since]
        tv_dd = market_data[tv_name].get("dd") if market_data and tv_name in market_data and not since else None
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
        dd = tv_dd or dd                  # TradingView's own max drawdown (counts moves inside open trades)
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
        "sub": "all three scripts · entry time in New York",
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
    data, first = load(), load(first=True)
    saved = data.get("period", ["", ""])[1] if data else ""
    for key, label, out in MARKETS:
        for since, suffix in ((None, ""), (LIVE_FROM, "-live")):
            source = data if since else first      # the full-period chart stays the first read
            accounts, period = build(source.get(key) if source else None, since)
            if since:
                d = date.fromisoformat(since)
                title = f"{label} scripts since {d:%b} {d.day}: MAMBA vs Opening Range vs Session Breakout"
                sub = (f"Forward results from {since} · read from TradingView (latest read {saved}) · "
                       f"% = share of the 50K account")
                empty = f"Starts with the first trade from {d:%b} {d.day} on · ask Claude to refresh from TradingView"
            else:
                title = f"{label} scripts: MAMBA vs Opening Range vs Session Breakout"
                sub = (f"Running profit per script · {period[0]} to {period[-1]} · from TradingView's Strategy Tester · "
                       f"% = share of the 50K account" if period else "No TradingView trades saved yet")
                empty = "No trades saved yet"
            svg = C.draw(title, sub, accounts, unit="$",
                         footnote="went against = the furthest the trade moved against you before it closed · "
                                  "TradingView strategy results, not real money.", empty=empty)
            path = os.path.join("reports", "charts", out + suffix + ".svg")
            os.makedirs(os.path.dirname(path), exist_ok=True)
            open(path, "w").write(svg)
            print(f"wrote {path}: " + ", ".join(f"{a['name']} {a['headline']}" for a in accounts[:3]))


if __name__ == "__main__":
    main()
