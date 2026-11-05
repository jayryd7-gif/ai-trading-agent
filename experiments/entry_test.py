"""
entry_test.py - Stricter entries and a stop with leeway (asked 2026-11-04).

Tests, on the LIVE 50K rules (time_test.run_live) for the last 30 and 60
days, with the current setup (gold 8 PM + gold-only early entries, Nasdaq
9:30):
  - the buy candle must CLOSE above the previous candle's high
  - and close strongly (wick against the trade no bigger than the body)
  - the stop a few points past the low instead of exactly at it
Run: python3 experiments/entry_test.py
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [ROOT, os.path.join(ROOT, "agents"), os.path.join(ROOT, "experiments")]

import main as R
import time_test as T

OPTIONS = [("NOW (as it trades today)", False, None, (0, 0))]
OPTIONS += [("Close above previous high", True, None, (0, 0)),
            ("Close above prev high + strong close", True, 1.0, (0, 0))]
for nq, gold in ((5, 1), (10, 2), (15, 3)):
    OPTIONS.append((f"Stop leeway Nasdaq {nq} / gold {gold} pts", False, None, (nq, gold)))
    OPTIONS.append((f"Close above + strong + leeway {nq}/{gold}", True, 1.0, (nq, gold)))

if __name__ == "__main__":
    data = T.candles()
    print("| Option | 30 days | gold | Nasdaq | won | PF | worst day | passes 30d | "
          "60 days | gold 60d | Nasdaq 60d | passes 60d (days each) |")
    print("|---" * 12 + "|")
    for label, close_prev, wick, (nq, gold) in OPTIONS:
        R.ENTRY_CLOSE_BEYOND_PREV, R.ENTRY_MAX_WICK = close_prev, wick
        R.STOP_BUFFER = {"nasdaq": nq, "gold": gold}
        a = T.run(data, {"open": (20, 0)}, "gold", 30, True)
        pa = [(y - x).days for x, y in T.run_live.pass_days]
        b = T.run(data, {"open": (20, 0)}, "gold", 60, True)
        pb = [(y - x).days for x, y in T.run_live.pass_days]
        print(f"| {label} | **{T.money(a['net'])}** | {T.money(a['gold'])} | {T.money(a['nasdaq'])} | "
              f"{a['won']}/{a['trades']} | {a['pf']:.2f} | {T.money(a['worst'])} | {pa} | "
              f"**{T.money(b['net'])}** | {T.money(b['gold'])} | {T.money(b['nasdaq'])} | {pb} |",
              flush=True)
