"""
scalp_test.py - Would quicker, scalp-style exits beat the current ones?

Replays the last 60 days of 5-minute candles for both markets with the bot
trading ON the Tradeify practice account (same as paper_trader.py), and
compares:
  - a time limit: close whatever is left N minutes after the entry
  - closer gold targets (4 points apart instead of 6)
  - bigger gold size (2 contracts at each target)

Run from the project folder:
    python experiments/scalp_test.py
Fills are perfect in a replay; real results can be worse.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [ROOT, os.path.join(ROOT, "agents")]

import main as R
import tradeify
from data import SYMBOLS, load_from_yahoo
from risk import INSTRUMENTS

ORIGINAL_RUN = R._run_trade
HOLD = {"minutes": None}


def run_with_time_limit(trade, session, index):
    """Same as main._run_trade, but the 'session' ends HOLD minutes after the
    entry, so whatever is left is closed at that candle's close."""
    if HOLD["minutes"]:
        session = session[:index + 1 + HOLD["minutes"] // 5]
    return ORIGINAL_RUN(trade, session, index)


R._run_trade = run_with_time_limit


def test(label, data, hold=None, gold_spacing=6, gold_plan=(1, 2, 2)):
    HOLD["minutes"] = hold
    INSTRUMENTS["gold"]["target_spacing"] = gold_spacing
    R.GOLD_SELL_PLAN = list(gold_plan)
    acct = tradeify.TradeifyAccount()
    results, _ = R.run_account(data, acct)
    attempts = acct.finish()
    nets = [r["profit"] - R.contracts_traded(r) for r in results]
    days = {}
    for r, n in zip(results, nets):
        d = R.trading_day(r["start"]).isoformat()
        days[d] = days.get(d, 0) + n
    held = [(r["exit_time"] - r["entry_time"]).total_seconds() / 60 for r in results]
    wins = sum(n > 0 for n in nets)
    gross_win = sum(n for n in nets if n > 0)
    gross_loss = -sum(n for n in nets if n < 0) or 1
    by = {}
    for r, n in zip(results, nets):
        by[r["instrument"]] = by.get(r["instrument"], 0) + n
    passed = sum(a["result"] == "Passed" for a in attempts if a["phase"] == "Evaluation")
    failed = sum(a["result"] == "Failed" for a in attempts)
    first_pass = next((a["end"] for a in attempts if a["result"] == "Passed"), "-")
    paid = sum(p for a in attempts for _, p in a["payouts"])
    print(f"{label:38s} net ${sum(nets):>7,.0f}  nas ${by.get('nasdaq', 0):>6,.0f}  "
          f"gold ${by.get('gold', 0):>6,.0f}  win {wins}/{len(nets)}  PF {gross_win / gross_loss:.2f}  "
          f"worst day ${min(days.values()):>6,.0f}  avg hold {sum(held) / len(held):3.0f}m "
          f"(max {max(held):3.0f})  evals passed {passed} failed {failed} first pass {first_pass}  "
          f"payouts ${paid:,.0f}")


if __name__ == "__main__":
    data = {k: load_from_yahoo(SYMBOLS[k], "5m", "60d") for k in R.SESSIONS}
    test("NOW (no time limit)", data)
    for hold in (30, 45, 60, 90):
        test(f"out after {hold} min", data, hold=hold)
    test("gold targets 4 pts apart", data, gold_spacing=4)
    test("gold targets 4 pts + out after 60", data, hold=60, gold_spacing=4)
    test("gold 2-2-2 contracts", data, gold_plan=(2, 2, 2))
    test("gold 2-2-2 + out after 60", data, hold=60, gold_plan=(2, 2, 2))
    test("gold 2-2-2, 4 pts + out after 60", data, hold=60, gold_spacing=4, gold_plan=(2, 2, 2))
