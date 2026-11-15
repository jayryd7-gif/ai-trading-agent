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
import sys
from datetime import timedelta

import yfinance as yf

import wheel_rules as R

IV_MULT = 1.2
SLIP = 0.02          # $ per share each way


def friday_near(day, days_out):
    target = day + timedelta(days=days_out)
    return target + timedelta(days=(4 - target.weekday()) % 7)


OURS = {"tp": R.TAKE_PROFIT, "put_dte": R.DTE_IDEAL, "call_dte": R.DTE_IDEAL, "time_exit": R.TIME_EXIT_DTE,
        "min_yield30": 0.0, "uptrend": False, "slot": R.MAX_PER_STOCK, "max_pos": R.MAX_POSITIONS,
        "multi": False, "reserve": 0.0}
# Options With Ryan's wheel, as summarized from his CRDO wheel video (CandleChasers write-up):
# puts ~0.30 delta 25-35 days, calls ~0.30 delta 15-25 days at/above cost, take profit ~80%,
# at least ~2.5% premium per 30 days, ~1.5 years of uptrend, max ~10% of the account per company.
RYAN = {"tp": 0.20, "put_dte": 30, "call_dte": 21, "time_exit": None,
        "min_yield30": 0.025, "uptrend": True, "slot": 0.10, "max_pos": 8,
        "multi": True, "reserve": 0.20}


def simulate(closes, start_usd, days, trend, ivcap, cfg=OURS):
    rets = closes.pct_change()
    sma = closes.rolling(R.TREND_DAYS).mean()
    cash = start_usd
    pos = {}             # ticker -> {"shares", "basis", "opt"}
    stats = {"wins": 0, "losses": 0, "assigned": 0, "called": 0, "trades": 0, "history": [], "premium": 0.0}
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
                q = o.get("q", 1)
                if d >= o["exp"]:
                    if itm and o["kind"] == "put":
                        p["shares"], p["basis"] = 100 * q, o["K"] - o["credit"]
                        cash -= o["K"] * 100 * q
                        stats["assigned"] += 1
                    elif itm and o["kind"] == "call":
                        cash += o["K"] * 100 * q
                        stats["called"] += 1
                        stats["wins" if o["K"] >= p["basis"] else "losses"] += 1
                        p["shares"] = 0
                    else:
                        stats["wins"] += 1
                    p["opt"] = None
                else:
                    price = opt_value(t, d, o)
                    late = cfg["time_exit"] is not None and dte <= cfg["time_exit"] and not itm
                    if price <= o["credit"] * cfg["tp"] or late:
                        cost = (price + SLIP) * 100 + R.FEE
                        cash -= cost * q
                        stats["premium"] -= cost * q
                        stats["wins" if o["credit"] * 100 >= cost else "losses"] += 1
                        p["opt"] = None
            if p["shares"] == 0 and not p["opt"]:
                del pos[t]
                continue
            # covered call on shares we own
            if p["shares"] and not p["opt"] and d < days[-1] - timedelta(days=3):
                exp = friday_near(d, cfg["call_dte"])
                T = (exp - d).days / 365
                K = max(R.strike_for_delta(S, T, vol(t, d), "call", cfg.get("delta", R.TARGET_DELTA)),
                        math.ceil(p["basis"] * 2) / 2)
                credit = R.bs_price(S, K, T, vol(t, d), "call") - SLIP
                if credit >= 0.05:
                    q = p["shares"] // 100
                    cash += (credit * 100 - R.FEE) * q
                    stats["premium"] += (credit * 100 - R.FEE) * q
                    p["basis"] -= credit
                    p["opt"] = {"kind": "call", "K": K, "exp": exp, "credit": credit, "q": q}
                    stats["trades"] += 1

        # account value today
        eq = cash + sum(p["shares"] * float(closes[t].loc[d]) for t, p in pos.items())
        eq -= sum(opt_value(t, d, p["opt"]) * 100 * p["opt"].get("q", 1) for t, p in pos.items() if p["opt"])
        stats["history"].append((d, eq))
        peak = max(peak, eq)
        maxdd = max(maxdd, (peak - eq) / peak)

        # 2) fill empty slots with new puts
        if len(pos) < cfg["max_pos"] and d < days[-1] - timedelta(days=3):
            secured = sum(p["opt"]["K"] * 100 * p["opt"].get("q", 1) for p in pos.values()
                          if p["opt"] and p["opt"]["kind"] == "put")
            free = cash - secured - cfg.get("reserve", 0.0) * eq
            exp = friday_near(d, cfg["put_dte"])
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
                if cfg["uptrend"]:
                    past = closes[t].loc[:d - timedelta(days=548)]
                    if past.empty or not S > float(past.iloc[-1]):
                        continue
                K = R.strike_for_delta(S, T, v, "put", cfg.get("delta", R.TARGET_DELTA))
                if K * 100 > eq * cfg["slot"]:
                    continue
                credit = R.bs_price(S, K, T, v, "put") - SLIP
                if credit < R.MIN_CREDIT or credit / K < cfg["min_yield30"] * (T * 365 / 30):
                    continue
                ideas.append((credit / K, t, K, credit))
            for _, t, K, credit in sorted(ideas, reverse=True):
                q = max(1, int(eq * cfg["slot"] // (K * 100))) if cfg.get("multi") else 1
                while q > 1 and K * 100 * q > free:
                    q -= 1
                if len(pos) >= cfg["max_pos"] or K * 100 * q > free:
                    continue
                cash += (credit * 100 - R.FEE) * q
                stats["premium"] += (credit * 100 - R.FEE) * q
                free -= K * 100 * q
                pos[t] = {"shares": 0, "basis": 0.0,
                          "opt": {"kind": "put", "K": K, "exp": exp, "credit": credit, "q": q}}
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


def ryan_compare():
    """Ours vs Ryan's rules on our cheap stocks ($10K CAD), and Ryan's rules on his own stocks."""
    fx = float(yf.download("CADUSD=X", period="5d", progress=False)["Close"].dropna().iloc[-1].iloc[0])
    usd = R.START_CAD * fx
    ours = yf.download(R.UNIVERSE, period="3y", progress=False)["Close"].dropna(axis=1, how="all").ffill()
    his_list = ["CRDO", "NVDA", "HOOD", "BE", "PLTR", "AMD"]
    his = yf.download(his_list, period="3y", progress=False)["Close"].dropna(axis=1, how="all").ffill()
    print(f"{'Window':8}{'Version':44}{'Return':>8}{'P/L':>12}{'Max DD':>8}{'W/L':>7}{'Assigned':>9}")
    for window in (90, 60, 30):
        for name, closes, start, cfg, cur in (
                ("Ours, our stocks, $10K CAD", ours, usd, OURS, "CAD"),
                ("Ryan's rules, our stocks, $10K CAD", ours, usd, RYAN, "CAD"),
                ("Ryan's rules, his stocks, $200K USD", his, 200_000, RYAN, "USD"),
                ("Ryan's rules, his stocks, $10K CAD", his, usd, RYAN, "CAD")):
            begin = closes.index[-1] - timedelta(days=window)
            days = [d for d in closes.index if d >= begin]
            eq, dd, s, pos = simulate(closes, start, days, False, False, cfg)
            pnl = (eq - start) / (fx if cur == "CAD" else 1)
            print(f"{window:>4} d  {name:44}{(eq/start-1)*100:7.1f}%{pnl:>9,.0f} {cur}{dd*100:7.1f}%"
                  f"{s['wins']:>4}/{s['losses']:<2}{s['assigned']:>8}")
        hold = (his.iloc[-1] / his.loc[[d for d in his.index if d >= his.index[-1] - timedelta(days=window)][0]] - 1).mean() * 100
        print(f"        (holding his 6 stocks equally: {hold:+.1f}%)")
        print()


if __name__ == "__main__":
    if "--ryan" in sys.argv:
        ryan_compare()
    else:
        main()
