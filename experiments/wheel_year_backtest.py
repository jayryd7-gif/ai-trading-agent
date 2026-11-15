"""
wheel_year_backtest.py - One year of both wheel accounts on volatile, heavily traded stocks.

    PYTHONPATH=agents python3 experiments/wheel_year_backtest.py

  Ours:       our rules, $10K CAD, the 10 most-traded volatile stocks priced $5-17.50
  Ryan-style: Ryan's rules, $200K USD, the 10 most-traded volatile stocks priced $20-200

Stocks are picked with data from BEFORE the year starts (no peeking): annual volatility
of at least 50% (cheap) / 45% (big), ranked by trading volume. Leveraged ETFs are left out.
Option prices are ESTIMATED (Black-Scholes, see wheel_backtest.py). Ryan's P/E rule can't
be backtested (no past P/E data), so it is left out here.

Writes experiments/wheel-year-results.json for the chart.
"""

import json
from datetime import timedelta

import numpy as np
import pandas as pd
import yfinance as yf

import wheel_rules as R
from wheel_backtest import OURS, RYAN, simulate

CHEAP = ["SOFI", "RIVN", "SNAP", "F", "AAL", "NIO", "LCID", "PLUG", "RIG", "NU", "GRAB", "ACHR", "MARA",
         "RIOT", "CLSK", "SOUN", "BBAI", "RKLB", "OPEN", "HIMS", "AFRM", "UPST", "DKNG", "JOBY", "RGTI",
         "QS", "AMC", "GME", "TLRY", "CLF", "INTC", "PFE", "T", "CCL", "VALE", "ITUB", "IONQ", "CIFR",
         "WULF", "HUT", "LUMN", "KGC", "AG", "HL", "CDE"]
BIG = ["TSLA", "NVDA", "AMD", "PLTR", "HOOD", "COIN", "MSTR", "SMCI", "CRDO", "BE", "SHOP", "AFRM",
       "UBER", "META", "AVGO", "MU", "NFLX", "AMZN", "GOOGL", "AAPL", "MSFT", "ARM", "APP", "RDDT",
       "SNOW", "CRWD", "PANW", "DELL", "ANET", "VST", "CEG", "OKLO", "RKLB", "IONQ", "SOFI", "UPST",
       "DKNG", "ORCL", "NET", "DDOG", "TSM", "INTC", "BABA", "PDD", "LLY", "XYZ", "PYPL", "MRVL", "RGTI", "HIMS"]
OUT = "experiments/wheel-year-results.json"


def pick(c, v, start, lo, hi, min_vol, min_dollar=0, min_shares=0, n=10):
    pre, prev = c.loc[:start].tail(60), v.loc[:start].tail(60)
    t = pd.DataFrame({"price": pre.iloc[-1], "vol": pre.pct_change().std() * np.sqrt(252),
                      "shares": prev.mean(), "dollar": (pre * prev).mean()}).dropna()
    t = t[(t.price >= lo) & (t.price <= hi) & (t.vol >= min_vol) &
          (t.dollar >= min_dollar) & (t.shares >= min_shares)]
    return list(t.sort_values("dollar", ascending=False).index[:n])


def monthly(hist, start_value):
    s = pd.Series({d: e for d, e in hist})
    ends = s.groupby(s.index.to_period("M")).last()
    prev = ends.shift(1).fillna(start_value)
    return ((ends / prev - 1) * 100).round(1)


def main():
    fx = float(yf.download("CADUSD=X", period="5d", progress=False)["Close"].dropna().iloc[-1].iloc[0])
    d = yf.download(sorted(set(CHEAP + BIG + ["SPY"])), period="3y", progress=False)
    c, v = d["Close"].ffill(), d["Volume"]
    start = c.index[-1] - timedelta(days=365)
    days = [x for x in c.index if x >= start]
    cheap = pick(c, v, start, 5, 17.5, 0.50, min_shares=15e6)
    big = pick(c, v, start, 20, 200, 0.45, min_dollar=1e9)
    usd10k = R.START_CAD * fx
    runs = {
        "Ours ($10K CAD)": (cheap, usd10k, OURS),
        "Ryan-style ($200K USD)": (big, 200_000.0, RYAN),
    }
    results, series = {}, {}
    for name, (tickers, money, cfg) in runs.items():
        eq, dd, st, pos = simulate(c[tickers].dropna(axis=1, how="all"), money, days, False, False, cfg)
        cad = name.startswith("Ours")
        mon = monthly(st["history"], money)
        results[name] = {
            "stocks": tickers, "start": money, "end": eq, "return_pct": (eq / money - 1) * 100,
            "pnl": (eq - money) / (fx if cad else 1), "currency": "CAD" if cad else "USD",
            "max_dd_pct": dd * 100, "wins": st["wins"], "losses": st["losses"], "assigned": st["assigned"],
            "called": st["called"], "premium": st["premium"] / (fx if cad else 1),
            "best_month": float(mon.max()), "worst_month": float(mon.min()),
            "up_months": int((mon > 0).sum()), "months": int(len(mon)),
            "monthly": {str(k): float(x) for k, x in mon.items()},
            "open_at_end": {t: ("shares" if p["shares"] else "put") for t, p in pos.items()},
        }
        series[name] = [(str(x.date()), round((e / money - 1) * 100, 2)) for x, e in st["history"]]
    for name, tickers in (("Hold the 10 cheap stocks", cheap), ("Hold the 10 big stocks", big), ("Hold SPY", ["SPY"])):
        first, px = c.loc[days[0], tickers], c.loc[days, tickers]
        curve = ((px / first).mean(axis=1) - 1) * 100
        series[name] = [(str(x.date()), round(float(y), 2)) for x, y in curve.items()]
        peak = (1 + curve / 100).cummax()
        results[name] = {"return_pct": float(curve.iloc[-1]),
                         "max_dd_pct": float(((peak - (1 + curve / 100)) / peak).max() * 100)}
    json.dump({"from": str(days[0].date()), "to": str(days[-1].date()), "fx": fx,
               "results": results, "series": series}, open(OUT, "w"), indent=1)
    print(f"{days[0].date()} to {days[-1].date()}")
    for name, r in results.items():
        extra = (f"  P/L {r['pnl']:+,.0f} {r['currency']}, DD {r['max_dd_pct']:.1f}%, W/L {r['wins']}/{r['losses']}, "
                 f"assigned {r['assigned']}, called {r['called']}, premium {r['premium']:,.0f}, "
                 f"up months {r['up_months']}/{r['months']}, best {r['best_month']:+.1f}%, worst {r['worst_month']:+.1f}%"
                 if "pnl" in r else f"  DD {r['max_dd_pct']:.1f}%")
        print(f"{name:28} {r['return_pct']:+6.1f}%{extra}")
        if "stocks" in r:
            print("   stocks:", ", ".join(r["stocks"]), "| open at end:", r["open_at_end"])
            print("   monthly:", r["monthly"])


if __name__ == "__main__":
    main()
