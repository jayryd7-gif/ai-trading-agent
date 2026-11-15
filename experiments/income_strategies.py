"""
income_strategies.py - Can a $10K CAD account make $500-2,000 CAD a month selling options?
Tests several approaches over the last 1 and 3 years.

    PYTHONPATH=agents:experiments python3 experiments/income_strategies.py

Option prices are ESTIMATED with Black-Scholes (realized volatility x 1.2 as implied vol),
with $0.02/share slippage per leg and $0.65 per contract per leg. Real results will differ.

Approaches:
  1-3  Wheel variants (cash-secured puts + covered calls) on cheap volatile stocks
  4-7  Put credit spreads (sell a put, buy a cheaper put below it to cap the loss),
       which need far less cash than a cash-secured put, so more trades fit
  8    Iron condors (a put spread + a call spread) on index ETFs
"""

import json
import math
import sys
from datetime import timedelta

import pandas as pd
import yfinance as yf

import wheel_rules as R
from wheel_backtest import OURS, friday_near, simulate
from wheel_year_backtest import BIG, CHEAP, pick

IV_MULT, SLIP, FEE = 1.2, 0.02, 0.65
OUT = "experiments/income-results.json"


def spreads(closes, start_usd, days, under, dte, delta, width_pct, tp, time_exit,
            risk_per_trade, max_risk, stop=None, calls=False):
    """Credit spreads. One open spread (or condor) per underlying at a time."""
    rets = closes.pct_change()
    cash, open_ = start_usd, {}
    hist, wins, losses = [], 0, 0

    def vol(t, d):
        return max(float(rets[t].loc[:d].tail(20).std() * math.sqrt(252) * IV_MULT), 0.12)

    def value(t, d, legs):
        S, T = float(closes[t].loc[d]), max((legs["exp"] - d).days, 0) / 365
        v = vol(t, d)
        tot = 0.0
        for kind, short, long in legs["pairs"]:
            if T <= 0:
                tot += (max(0, min(short - S, short - long)) if kind == "put"
                        else max(0, min(S - short, long - short)))
            else:
                tot += R.bs_price(S, short, T, v, kind) - R.bs_price(S, long, T, v, kind)
        return tot

    for d in days:
        for t in list(open_):
            o = open_[t]
            val = value(t, d, o)
            dte_left = (o["exp"] - d).days
            done = (d >= o["exp"] or val <= o["credit"] * (1 - tp)
                    or (time_exit is not None and dte_left <= time_exit)
                    or (stop is not None and val >= o["credit"] * stop))
            if done:
                legs = 2 * len(o["pairs"])
                cost = (val + (SLIP * legs if d < o["exp"] else 0)) * 100 * o["n"] + (FEE * legs * o["n"] if d < o["exp"] else 0)
                cash -= cost
                pnl = o["credit"] * 100 * o["n"] - cost
                wins += pnl >= 0
                losses += pnl < 0
                del open_[t]
        eq = cash - sum(value(t, d, o) * 100 * o["n"] for t, o in open_.items())
        hist.append((d, eq))
        risk_now = sum(o["risk"] for o in open_.values())
        if d > days[-1] - timedelta(days=3):
            continue
        for t in under:
            if t in open_ or t not in closes or math.isnan(closes[t].loc[d]):
                continue
            S, v = float(closes[t].loc[d]), vol(t, d)
            exp = friday_near(d, dte)
            T = (exp - d).days / 365
            step = 1.0 if S >= 25 else 0.5
            w = max(step, round(S * width_pct / step) * step)
            pairs = []
            ks = R.strike_for_delta(S, T, v, "put", delta)
            pairs.append(("put", ks, ks - w))
            if calls:
                kc = R.strike_for_delta(S, T, v, "call", delta)
                pairs.append(("call", kc, kc + w))
            credit = sum(R.bs_price(S, a, T, v, k) - R.bs_price(S, b, T, v, k) for k, a, b in pairs) - SLIP * 2 * len(pairs)
            if credit <= 0.05:
                continue
            risk1 = (w - credit) * 100 + FEE * 2 * len(pairs)
            n = int(min(risk_per_trade * eq, max_risk * eq - risk_now) // risk1)
            if n < 1:
                continue
            cash += credit * 100 * n - FEE * 2 * len(pairs) * n
            open_[t] = {"exp": exp, "pairs": pairs, "credit": credit, "n": n, "risk": risk1 * n}
            risk_now += risk1 * n
    return hist, wins, losses


def summarize(name, hist, start, fx, wins, losses):
    s = pd.Series({d: e for d, e in hist})
    ends = s.groupby(s.index.to_period("M")).last()
    monthly_cad = (ends - ends.shift(1).fillna(start)) / fx
    peak = s.cummax()
    return {"name": name, "return_pct": (s.iloc[-1] / start - 1) * 100,
            "avg_month_cad": float(monthly_cad.mean()), "best_month_cad": float(monthly_cad.max()),
            "worst_month_cad": float(monthly_cad.min()), "up_months": int((monthly_cad > 0).sum()),
            "months": int(len(monthly_cad)), "max_dd_pct": float(((peak - s) / peak).max() * 100),
            "months_500": int((monthly_cad >= 500).sum()), "wins": int(wins), "losses": int(losses)}


def main():
    fx = float(yf.download("CADUSD=X", period="5d", progress=False)["Close"].dropna().iloc[-1].iloc[0])
    usd = R.START_CAD * fx
    tick = sorted(set(CHEAP + BIG + ["SPY", "QQQ", "IWM"]))
    data = yf.download(tick, period="5y", progress=False)
    c, v = data["Close"].ffill(), data["Volume"]
    out = {}
    for years in (1, 3):
        start = c.index[-1] - timedelta(days=365 * years)
        days = [x for x in c.index if x >= start]
        cheap = pick(c, v, start, 5, 17.5, 0.50, min_shares=15e6)
        big = pick(c, v, start, 20, 200, 0.45, min_dollar=1e9)
        rows = []

        def wheel(name, cfg, tickers):
            eq, dd, st, pos = simulate(c[tickers].dropna(axis=1, how="all"), usd, days, False, False, cfg)
            rows.append(summarize(name, st["history"], usd, fx, st["wins"], st["losses"]))

        def spread(name, under, **kw):
            hist, w, l = spreads(c, usd, days, under, **kw)
            rows.append(summarize(name, hist, usd, fx, w, l))

        wheel("1 Wheel, current rules (0.30 delta, 42 days)", OURS, cheap)
        wheel("2 Wheel, 0.40 delta, 30 days, 6 stocks", {**OURS, "delta": 0.40, "put_dte": 30, "call_dte": 30,
                                                          "max_pos": 6, "slot": 0.17}, cheap)
        wheel("3 Wheel, weekly (7 days, hold to expiry)", {**OURS, "put_dte": 7, "call_dte": 7, "tp": 0.0,
                                                           "time_exit": None}, cheap)
        idx = ["SPY", "QQQ", "IWM"]
        spread("4 Put spreads SPY/QQQ/IWM, 45 days, 0.30 delta, 10% risk each", idx, dte=42, delta=0.30,
               width_pct=0.02, tp=0.5, time_exit=21, risk_per_trade=0.10, max_risk=0.30)
        spread("5 Put spreads SPY/QQQ/IWM, weekly, 0.30 delta, 20% risk each", idx, dte=7, delta=0.30,
               width_pct=0.01, tp=0.5, time_exit=None, risk_per_trade=0.20, max_risk=0.60)
        spread("6 Put spreads on 10 volatile big stocks, 30 days, 0.30 delta, 10% risk each", big, dte=30,
               delta=0.30, width_pct=0.05, tp=0.5, time_exit=14, risk_per_trade=0.10, max_risk=0.60)
        spread("7 Same as 6 but 2x stop-loss", big, dte=30, delta=0.30, width_pct=0.05, tp=0.5,
               time_exit=14, risk_per_trade=0.10, max_risk=0.60, stop=2.0)
        spread("8 Iron condors SPY/QQQ, 30 days, 0.20 delta, 15% risk each", ["SPY", "QQQ"], dte=30, delta=0.20,
               width_pct=0.02, tp=0.5, time_exit=14, risk_per_trade=0.15, max_risk=0.30, calls=True)
        spy = c.loc[days, "SPY"]
        out[f"{years}y"] = {"from": str(days[0].date()), "cheap": cheap, "big": big, "rows": rows,
                            "spy_pct": float((spy.iloc[-1] / spy.iloc[0] - 1) * 100)}
        print(f"\n=== Last {years} year(s) from {days[0].date()} (SPY {out[f'{years}y']['spy_pct']:+.1f}%)")
        print(f"{'Approach':78}{'Return':>8}{'Avg/mo CAD':>11}{'Best':>7}{'Worst':>7}{'Up mo':>7}{'>=500':>6}{'MaxDD':>7}{'W/L':>9}")
        for r in rows:
            print(f"{r['name'][:77]:78}{r['return_pct']:7.1f}%{r['avg_month_cad']:11,.0f}{r['best_month_cad']:7,.0f}"
                  f"{r['worst_month_cad']:7,.0f}{r['up_months']:>4}/{r['months']:<2}{r['months_500']:6}{r['max_dd_pct']:6.1f}%"
                  f"{r['wins']:>5}/{r['losses']:<3}")
    json.dump(out, open(OUT, "w"), indent=1)


if __name__ == "__main__":
    main()
