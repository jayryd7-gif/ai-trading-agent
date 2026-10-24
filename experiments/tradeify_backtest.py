"""
tradeify_backtest.py - Would the bot pass Tradeify's Growth 50K evaluation and
get paid on the funded account? Replays the last 60 days of 5-minute candles
for both markets as one account (the bot's own rules, including the daily
loss limit and the risk check), then runs the trades through
agents/tradeify.py, back to back: each failed evaluation is followed by a new
one, and each pass by a funded account.

Run from the project folder:
    python experiments/tradeify_backtest.py

A replay on 60 days is a small sample, and fills are perfect. Real results
can be worse.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [ROOT, os.path.join(ROOT, "agents")]

import main as R
import tradeify
from data import SYMBOLS, load_from_yahoo
from risk import INSTRUMENTS
from trade_review import review


def trades_for(data):
    results, _ = R.run_account(data, R.Account())
    out = []
    for r in results:
        # A stop order caps the open loss at the stop (before slippage).
        worst = min(review(r, r["session"])["mae"], abs(r["entry"] - r["stop"]))
        out.append({"day": R.trading_day(r["start"]).isoformat(),
                    "net": r["profit"] - r["contracts"],
                    "worst": worst * INSTRUMENTS[r["instrument"]]["point_value"] * r["contracts"],
                    "instrument": r["instrument"]})
    return out


def report(label, trades):
    attempts = tradeify.simulate(trades)
    evals = [a for a in attempts if a["phase"] == "Evaluation"]
    funded = [a for a in attempts if a["phase"] == "Funded"]
    days = {}
    for t in trades:
        days[t["day"]] = days.get(t["day"], 0) + t["net"]
    print(f"\n=== {label}: {len(trades)} trades, net ${sum(t['net'] for t in trades):,.0f}, "
          f"best day ${max(days.values()):,.0f}, worst day ${min(days.values()):,.0f}")
    for a in attempts:
        paid = sum(p for _, p in a["payouts"])
        print(f"  {a['phase']:10s} {a['start']} -> {a['end']}  {a['days']:2d} days  "
              f"{a['result']:11s} balance ${a['balance']:,.0f}  "
              f"payouts {len(a['payouts'])} (${paid:,.0f})  {a['note']}")
        if a["phase"] == "Funded" and a["result"] == "In progress":
            print("     next payout:", tradeify.payout_status(a)[1])
    print(f"  Evaluations: {sum(a['result'] == 'Passed' for a in evals)} passed, "
          f"{sum(a['result'] == 'Failed' for a in evals)} failed. Funded accounts failed: "
          f"{sum(a['result'] == 'Failed' for a in funded)}.")


def follow(data, cap):
    """The bot trading ON a Tradeify account: sized by its real limits."""
    tradeify.TradeifyAccount.PROFIT_CAP = cap
    acct = tradeify.TradeifyAccount()
    results, _ = R.run_account(data, acct)
    attempts = acct.finish()
    days = {}
    for r in results:
        d = R.trading_day(r["start"]).isoformat()
        days[d] = days.get(d, 0) + r["profit"] - R.contracts_traded(r)
    print(f"\n=== Bot following Tradeify's limits, daily profit cap {cap}: {len(results)} trades, "
          f"net ${sum(days.values()):,.0f}, small-size trades "
          f"{sum(r['contracts'] == 3 for r in results)}")
    for a in attempts:
        paid = sum(p for _, p in a["payouts"])
        print(f"  {a['phase']:10s} {a['start']} -> {a['end']}  {a['days']:2d} days  "
              f"{a['result']:11s} balance ${a['balance']:,.0f}  "
              f"payouts {len(a['payouts'])} (${paid:,.0f})  {a['note']}")
        if a["phase"] == "Funded" and a["result"] == "In progress":
            print("     next payout:", tradeify.payout_status(a)[1])


if __name__ == "__main__":
    data = {k: load_from_yahoo(SYMBOLS[k], "5m", "60d") for k in R.SESSIONS}
    for reentry in (False, True):
        R.REENTRY = reentry
        print(f"\n##### Fakeout re-entry {'ON' if reentry else 'OFF'}")
        follow(data, 600)
    R.REENTRY = True
    if "all" not in sys.argv:
        sys.exit()
    report("Bot as it runs now ($4,000 max drawdown, daily loss limit, risk check)",
           trades_for(data))
    for cap in (600, 1000):
        R.DAILY_PROFIT_CAP = cap
        report(f"Same, plus no more trades once the day is up ${cap}", trades_for(data))
    R.DAILY_PROFIT_CAP = None
    keep = (R.MAX_DRAWDOWN, R.NEAR_LIMIT)
    R.MAX_DRAWDOWN, R.NEAR_LIMIT = 2000, 750
    report("Bot set to Tradeify's $2,000 drawdown (small size under $750 left)",
           trades_for(data))
    R.MAX_DRAWDOWN, R.NEAR_LIMIT = keep
    R.DAILY_LOSS_LIMIT = 10**9
    report("No daily loss limit or risk check (how it ran before today)",
           trades_for(data))
