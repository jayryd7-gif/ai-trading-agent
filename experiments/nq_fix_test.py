"""
nq_fix_test.py - Nasdaq fixes asked for on 2026-11-05 (the 9:30 drop the bot
skipped): stop from the buy candle only, stop to breakeven after Target 1,
and key levels from the overnight range (6 PM to 9:30 AM). Fixed size 2/2/2,
$3 fees a trade, no account limits.
Run: python3 experiments/nq_fix_test.py
"""
import os
import sys
from datetime import datetime, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [ROOT, os.path.join(ROOT, "agents"), os.path.join(ROOT, "experiments")]

import main as R
import risk
import time_test as T

base_levels = R.key_levels_for


def run(days, levels="pre_open", stop_candles="both", stop_rules=None, confirm=True, data=None):
    R.STOP_CANDLES = stop_candles
    risk.STOP_RULES = stop_rules or {2: 1}
    R.CONFIRM_BREAKOUT["nasdaq"] = confirm
    c = data["nasdaq"]
    cfg = dict(R.SESSIONS["nasdaq"], early=0)
    ses = R.group_into_sessions(c, cfg)
    st = list(ses)
    ev = R.timeline(c)
    first = ev[-1][0] - timedelta(days=days)
    out = []
    for i in range(1, len(st)):
        if st[i] < first:
            continue
        if levels == "overnight":
            pre = [x for t, x in ev if st[i] - timedelta(hours=15, minutes=30) <= t < st[i]]
            lv = R.find_key_levels(pre) if len(pre) > 60 else None
        else:
            lv = base_levels(ses, st, i, cfg, ev)
        if lv is None:
            continue
        r = R.play_session("nasdaq", cfg, st[i], ses[st[i]], *lv, size_plan=[2, 2, 2])
        if r:
            out.append((st[i], r))
    return out


OPTIONS = [
    ("NOW", {}),
    ("stop from buy candle only", dict(stop_candles="second")),
    ("+ breakeven after T1", dict(stop_candles="second", stop_rules={1: "entry", 2: 1})),
    ("overnight lows/highs + both fixes", dict(levels="overnight", stop_candles="second", stop_rules={1: "entry", 2: 1})),
    ("overnight, 1-candle close, both fixes", dict(levels="overnight", stop_candles="second", stop_rules={1: "entry", 2: 1}, confirm=False)),
    ("breakeven after T1 only", dict(stop_rules={1: "entry", 2: 1})),
]

if __name__ == "__main__":
    data = T.candles()
    for label, kw in OPTIONS:
        cells = []
        for days in (30, 60):
            res = run(days, data=data, **kw)
            n = [r["profit"] - 3 for _, r in res]
            w = sum(x for x in n if x > 0)
            l = -sum(x for x in n if x < 0) or 1
            cells.append(f"{days}d {T.money(sum(n))} ({sum(x > 0 for x in n)}/{len(n)}, PF {w / l:.2f})")
        today = [r for s, r in run(2, data=data, **kw) if s.date() == datetime(2026, 11, 5).date()]
        t = today[0] if today else None
        tx = (f"today {t['direction']} {t['entry_time']:%H:%M} at {t['entry']} stop {t['stop']} "
              f"risk ${t['risk_dollars']:,.0f} -> {T.money(t['profit'] - 3)}") if t else "today: no trade"
        print(f"{label:40s} | " + " | ".join(cells) + f" | {tx}", flush=True)
