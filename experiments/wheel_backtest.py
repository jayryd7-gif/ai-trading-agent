"""
wheel_backtest.py - Estimated backtest of the options wheel on a $10K CAD account,
up to 4 stocks at once (rules in agents/wheel_rules.py).

    PYTHONPATH=agents python3 experiments/wheel_backtest.py

IMPORTANT: free data has no past option prices, so option prices here are
ESTIMATED with Black-Scholes, using each stock's 20-day realized volatility x 1.2
as a stand-in for implied volatility. Earnings dates are not checked here (the
paper trader does check them). Treat results as a rough guide.

Three versions are compared:
  A  no filters      - pick the highest-paying stocks
  B  trend filter    - only sell puts when the stock is above its 50-day average
  C  trend + IV cap  - B, and skip stocks with estimated IV over 80% (the live rules)
"""

import math
from datetime import timedelta

import yfinance as yf

import wheel_rules as R

IV_MULT = 1.2
SLIP = 0.02          # $ per share each way


def friday_near(day, days_out):
    target = day + timedelta(days=days_out)
    return target + timedelta(days=(4 - target.weekday()) % 7)


def simulate(closes, start_usd, days, trend, ivcap):
    rets = closes.pct_change()
    sma = closes.rolling(R.TREND_DAYS).mean()
    cash = start_usd
    pos = {}             # ticker -> {"shares", "basis", "opt"}
    stats = {"wins": 0, "losses": 0, "assigned": 0, "called": 0, "trades": 0}
    peak, maxdd, eq = start_usd, 0.0, start_usd

    def vol(t, d):
        v = rets[t].loc[:d].tail(20).std() * math.sqrt(252) * IV_MULT
        return max(float(v), 0.15)

    def opt_value(t, d, o):
        S = float(closes[t].loc[d])
        return R.bs_price(S, o["K"], max((o["exp"] - d).days, 0) / 365, vol(t, d), o["kind"])

    for d in days:
        # 1) manage what we hold
        for t in list(pos):
            p = pos[t]
            o = p["opt"]
            S = float(closes[t].loc[d])
            if o:
                dte = (o["exp"] - d).days
                itm = S < o["K"] if o["kind"] == "put" else S > o["K"]
                if d >= o["exp"]:
                    if itm and o["kind"] == "put":
                        p["shares"], p["basis"] = 100, o["K"] - o["credit"]
                        cash -= o["K"] * 100
                        stats["assigned"] += 1
                    elif itm and o["kind"] == "call":
                        cash += o["K"] * 100
                        stats["called"] += 1
                        stats["wins" if o["K"] >= p["basis"] else "losses"] += 1
                        p["shares"] = 0
                    else:
                        stats["wins"] += 1
                    p["opt"] = None
                else:
                    price = opt_value(t, d, o)
                    if price <= o["credit"] * R.TAKE_PROFIT or (dte <= R.TIME_EXIT_DTE and not itm):
                        cost = (price + SLIP) * 100 + R.FEE
                        cash -= cost
                        stats["wins" if o["credit"] * 100 >= cost else "losses"] += 1
                        p["opt"] = None
            if p["shares"] == 0 and not p["opt"]:
                del pos[t]
                continue
            # covered call on shares we own
            if p["shares"] and not p["opt"] and d < days[-1] - timedelta(days=3):
                exp = friday_near(d, R.DTE_IDEAL)
                T = (exp - d).days / 365
                K = max(R.strike_for_delta(S, T, vol(t, d), "call"), math.ceil(p["basis"] * 2) / 2)
                credit = R.bs_price(S, K, T, vol(t, d), "call") - SLIP
                if credit >= 0.05:
                    cash += credit * 100 - R.FEE
                    p["basis"] -= credit
                    p["opt"] = {"kind": "call", "K": K, "exp": exp, "credit": credit}
                    stats["trades"] += 1

        # account value today
        eq = cash + sum(p["shares"] * float(closes[t].loc[d]) for t, p in pos.items())
        eq -= sum(opt_value(t, d, p["opt"]) * 100 for t, p in pos.items() if p["opt"])
        peak = max(peak, eq)
        maxdd = max(maxdd, (peak - eq) / peak)

        # 2) fill empty slots with new puts
        if len(pos) < R.MAX_POSITIONS and d < days[-1] - timedelta(days=3):
            secured = sum(p["opt"]["K"] * 100 for p in pos.values() if p["opt"] and p["opt"]["kind"] == "put")
            free = cash - secured
            exp = friday_near(d, R.DTE_IDEAL)
            T = (exp - d).days / 365
            ideas = []
            for t in closes.columns:
                if t in pos:
                    continue
                S = float(closes[t].loc[d])
                if math.isnan(S) or S < R.MIN_PRICE:
                    continue
                v = vol(t, d)
                if trend and not S > float(sma[t].loc[d]):
                    continue
                if ivcap and v > R.MAX_IV:
                    continue
                K = R.strike_for_delta(S, T, v, "put")
                if K * 100 > R.slot_size(eq):
                    continue
                credit = R.bs_price(S, K, T, v, "put") - SLIP
                if credit < R.MIN_CREDIT:
                    continue
                ideas.append((credit / K, t, K, credit))
            for _, t, K, credit in sorted(ideas, reverse=True):
                if len(pos) >= R.MAX_POSITIONS or K * 100 > free:
                    continue
                cash += credit * 100 - R.FEE
                free -= K * 100
                pos[t] = {"shares": 0, "basis": 0.0,
                          "opt": {"kind": "put", "K": K, "exp": exp, "credit": credit}}
                stats["trades"] += 1
    return eq, maxdd, stats, pos


def main():
    fx = float(yf.download("CADUSD=X", period="5d", progress=False)["Close"].dropna().iloc[-1].iloc[0])
    usd = R.START_CAD * fx
    closes = yf.download(R.UNIVERSE, period="1y", progress=False)["Close"].dropna(axis=1, how="all").ffill()
    print(f"Start: ${R.START_CAD:,.0f} CAD = ${usd:,.0f} USD. Up to {R.MAX_POSITIONS} stocks, "
          f"max ${R.slot_size(usd):,.0f} USD (strike up to ${R.slot_size(usd)/100:.2f}) each.\n")
    print(f"{'Window':8}{'Version':18}{'Return':>8}{'P/L CAD':>9}{'Max DD':>8}{'Wins':>6}{'Loss':>6}"
          f"{'Assigned':>10}{'Basket hold':>13}")
    for window in (90, 60, 30):
        start = closes.index[-1] - timedelta(days=window)
        days = [d for d in closes.index if d >= start]
        first = closes.loc[days[0]]
        fits = [t for t in closes.columns if R.MIN_PRICE <= first[t] <= R.slot_size(usd) / 100]
        basket = (closes.loc[days[-1], fits] / first[fits] - 1).mean() * 100
        for name, trend, ivcap in (("A no filters", False, False), ("B trend filter", True, False),
                                   ("C trend + IV cap", True, True)):
            eq, dd, s, pos = simulate(closes, usd, days, trend, ivcap)
            print(f"{window:>4} d  {name:18}{(eq/usd-1)*100:7.1f}%{(eq-usd)/fx:9.0f}{dd*100:7.1f}%"
                  f"{s['wins']:6}{s['losses']:6}{s['assigned']:10}{basket:12.1f}%")
        print()


if __name__ == "__main__":
    main()
