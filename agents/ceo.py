"""
ceo.py - The CEO agent: checks that every agent (and you) followed the rules.

Run it from the project folder (with PYTHONPATH set to "."):
    python agents/ceo.py

It is plain code, not AI, so it costs nothing. It reads what the other agents
wrote and checks it against the rules:

  Futures paper trader     one trade per session, entry inside the window,
                           right contract count, stop moved after Target 2,
                           no trades after the max drawdown was hit
  Your trade journal       the same timing and one-trade rules, and a stop
                           loss written down for every trade
  Crypto rotation bot      buys only at the weekly check, at most 5 coins
  Crypto buy-and-hold bot  never sells
  Alpaca copy              only the bot's coins, never more than the limit
  Costs                    no run over $1, monthly spend under the budget
  Health                   no agent failing on its last run

Each check is ✅ passed, ⚠️ warning (worth a look) or ❌ broken rule.
It writes reports/ceo/latest.md (shown on the dashboard) and adds a line to
reports/ceo/history.csv every time it runs.
"""

import csv
import glob
import json
import os
import re
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import main as rules
from risk import INSTRUMENTS as CONTRACT_RULES

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "crypto"))

# ---------------- SETTINGS ----------------
FOLDER = os.path.join("reports", "ceo")
PAPER_TRADES = os.path.join("paper-trading", "trades.csv")
MY_JOURNAL = "trade-journal.md"
CRYPTO_TRADES = os.path.join("crypto", "trades.csv")
ALPACA_ORDERS = os.path.join("crypto", "alpaca-orders.csv")
COSTS = os.path.join("reports", "costs")
RUN_BUDGET = 1.00         # dollars per AI run
MONTH_BUDGET = 50.00      # dollars per month, all AI agents together
ALPACA_LIMIT = 1500       # dollars the Alpaca copy may hold
ROTATION_MAX_COINS = 5
DRAWDOWN_WARN_LEFT = 0.25 # warn when less than this share of the max drawdown is left
# ------------------------------------------

OK, WARN, BAD = "✅", "⚠️", "❌"


def read_csv(path):
    try:
        with open(path, newline="") as f:
            return list(csv.DictReader(f))
    except OSError:
        return []


class Report:
    def __init__(self):
        self.sections = []

    def section(self, title):
        self.sections.append((title, []))

    def add(self, status, text):
        self.sections[-1][1].append((status, text))

    def counts(self):
        items = [s for _, lines in self.sections for s, _ in lines]
        return items.count(OK), items.count(WARN), items.count(BAD)


def minutes_after_open(instrument, day, hhmm):
    """Minutes between the session open and an entry time, or None."""
    try:
        moment = datetime.strptime(f"{day} {hhmm}", "%Y-%m-%d %H:%M")
    except ValueError:
        return None
    config = rules.SESSIONS[instrument]
    for candidate in (moment, moment + timedelta(days=1), moment - timedelta(days=1)):
        start = rules.session_start(candidate, config)
        if start is not None:
            return (candidate - start).total_seconds() / 60
    return None


# ---------------- the checks ----------------

def check_paper_trader(r):
    r.section("Futures paper trader")
    rows = read_csv(PAPER_TRADES)
    trades = [x for x in rows if x["signal"] == "yes"]
    if not rows:
        r.add(OK, "No sessions recorded yet, nothing to check.")
        return
    window = rules.ENTRY_WINDOW_MINUTES + 5        # the confirming candle can close just after
    seen, problems = set(), 0
    for t in trades:
        key = (t["instrument"], t["session_start"])
        if key in seen:
            r.add(BAD, f"Two trades in one session: {t['instrument']} {t['session_start']}.")
            problems += 1
        seen.add(key)
        start = datetime.strptime(t["session_start"], "%Y-%m-%d %H:%M")
        entry = datetime.strptime(f"{start:%Y-%m-%d} {t['entry_time']}", "%Y-%m-%d %H:%M")
        if entry < start:
            entry += timedelta(days=1)
        late = (entry - start).total_seconds() / 60
        if late > window:
            r.add(BAD, f"{t['instrument']} {t['session_start']}: entered {late:.0f} minutes "
                       f"after the open (the window is {rules.ENTRY_WINDOW_MINUTES}).")
            problems += 1
        contracts = int(t["contracts"])
        if t["instrument"] == "nasdaq" and contracts != sum(CONTRACT_RULES["nasdaq"]["fixed_plan"]):
            r.add(BAD, f"Nasdaq {t['session_start']}: {contracts} contracts (the rule is 5).")
            problems += 1
        if t["instrument"] == "gold" and not 3 <= contracts <= 9:
            r.add(BAD, f"Gold {t['session_start']}: {contracts} contracts (allowed 3 to 9).")
            problems += 1
        events = t["events"]
        if "at Target 2" in events and "Target 3" not in events.split("at Target 2", 1)[0] \
                and "moved stop to Target 1" not in events:
            r.add(BAD, f"{t['instrument']} {t['session_start']}: Target 2 was hit but the stop "
                       "was not moved to Target 1.")
            problems += 1
    stopped = [x for x in rows if x["signal"] == "stopped"]
    if stopped:
        first = min(x["session_start"] for x in stopped)
        late_trades = [t for t in trades if t["session_start"] > first]
        if late_trades:
            r.add(BAD, f"{len(late_trades)} trade(s) taken after the max drawdown stop on {first}.")
            problems += 1
        else:
            r.add(WARN, f"The ${rules.MAX_DRAWDOWN:,} max drawdown was hit on {first}; "
                        "trading is stopped until the account is reset.")
    if not problems:
        r.add(OK, f"All {len(trades)} paper trades followed the rules (one per session, inside "
                  f"the {rules.ENTRY_WINDOW_MINUTES}-minute window, right size, stop managed).")
    # How close to the max drawdown
    equity = peak = 0.0
    for t in sorted(trades, key=lambda x: x["session_start"]):
        equity += float(t["net"])
        peak = max(peak, equity)
    left = rules.MAX_DRAWDOWN - (peak - equity)
    status = WARN if left < DRAWDOWN_WARN_LEFT * rules.MAX_DRAWDOWN else OK
    r.add(status, f"Room left before the ${rules.MAX_DRAWDOWN:,} max drawdown: ${left:,.0f}.")


def journal_trades():
    """Your own trades from trade-journal.md as dictionaries."""
    try:
        text = open(MY_JOURNAL).read()
    except OSError:
        return []
    trades = []
    for block in re.split(r"(?=^### Trade #)", text, flags=re.M):
        head = re.match(r"### Trade #(\S+) \| (\d{4}-\d{2}-\d{2})", block)
        if not head or head.group(1) == "__":
            continue
        field = lambda name: (re.search(rf"\*\*{name}:\*\*\s*(.*)", block) or [None, ""])[1].strip()
        trades.append({"number": head.group(1), "date": head.group(2),
                       "session": field("Session"), "entry_time": field("Entry time"),
                       "stop": field("Stop loss"), "instrument": field("Instrument")})
    return trades


def check_my_journal(r):
    r.section("Your trade journal")
    trades = journal_trades()
    if not trades:
        r.add(OK, "No trades logged yet, nothing to check.")
        return
    problems, per_session = 0, {}
    for t in trades:
        market = "gold" if "asia" in t["session"].lower() or "gold" in t["instrument"].lower() else "nasdaq"
        time_match = re.search(r"\d{1,2}:\d{2}", t["entry_time"])
        if not time_match:
            r.add(WARN, f"Trade #{t['number']} ({t['date']}): no entry time written down.")
            problems += 1
        else:
            late = minutes_after_open(market, t["date"], time_match.group(0).zfill(5))
            if late is None or late > rules.ENTRY_WINDOW_MINUTES + 5:
                r.add(BAD, f"Trade #{t['number']} ({t['date']}): entry at {time_match.group(0)} is "
                           f"outside the first {rules.ENTRY_WINDOW_MINUTES} minutes of the session.")
                problems += 1
        if not re.search(r"\d", t["stop"]):
            r.add(BAD, f"Trade #{t['number']} ({t['date']}): no stop loss written down.")
            problems += 1
        key = (t["date"], market)
        per_session[key] = per_session.get(key, 0) + 1
    for (day, market), n in per_session.items():
        if n > 1:
            r.add(BAD, f"{n} {market} trades on {day} (the rule is one per session).")
            problems += 1
    if not problems:
        r.add(OK, f"All {len(trades)} of your trades followed the rules.")


def check_crypto(r):
    r.section("Crypto bots")
    rows = [x for x in read_csv(CRYPTO_TRADES) if x.get("account") == "paper"]
    if not rows:
        r.add(OK, "No paper crypto trades yet, nothing to check.")
        return
    rotation = [x for x in rows if x["bot"] == "Rotation bot"]
    bad_buys = [x for x in rotation if x["action"] == "Buy" and not x["reason"].startswith("weekly check")]
    if bad_buys:
        for x in bad_buys:
            r.add(BAD, f"Rotation bot bought {x['coin']} on {x['date']} outside the weekly check.")
    held, most = set(), 0
    for x in sorted(rotation, key=lambda x: (x["date"], x["action"] != "Sell")):
        (held.discard if x["action"] == "Sell" else held.add)(x["coin"])
        most = max(most, len(held))
    if most > ROTATION_MAX_COINS:
        r.add(BAD, f"Rotation bot held {most} coins at once (the rule is at most {ROTATION_MAX_COINS}).")
    if not bad_buys and most <= ROTATION_MAX_COINS:
        r.add(OK, f"Rotation bot: {len(rotation)} trades, buys only at weekly checks, "
                  f"never more than {most} coins at once.")
    sells = [x for x in rows if x["bot"] == "Buy-and-hold bot" and x["action"] == "Sell"]
    r.add(BAD if sells else OK, "Buy-and-hold bot sold coins, which it must never do." if sells
          else "Buy-and-hold bot has never sold.")


def check_alpaca(r):
    r.section("Alpaca copy")
    orders = read_csv(ALPACA_ORDERS)
    if not orders:
        r.add(OK, "No Alpaca orders yet.")
        return
    try:
        from crypto_bots import COINS, NEVER_OWN
    except Exception:
        COINS, NEVER_OWN = None, []
    strange = [o for o in orders if COINS and o["coin"] not in COINS
               and not (o["coin"] in NEVER_OWN and o["side"] == "sell")]
    banned = [o for o in orders if o["coin"] in NEVER_OWN and o["side"] == "buy"
              and o["time_utc"] >= "2026-10-18 12:00"]
    for o in banned:
        r.add(BAD, f"Alpaca bought {o['coin']}, which is on the never-own list.")
    for o in strange:
        r.add(BAD, f"Alpaca order for {o['coin']}, which is not one of the bot's coins.")
    days = {}
    for o in orders:
        if o["side"] == "buy":
            days[o["time_utc"][:10]] = days.get(o["time_utc"][:10], 0) + float(o["dollars"])
    big = {d: v for d, v in days.items() if v > ALPACA_LIMIT}
    for d, v in big.items():
        r.add(BAD, f"Alpaca bought ${v:,.0f} on {d}, over the ${ALPACA_LIMIT:,} limit.")
    failed = [o for o in orders if o["status"] in ("rejected", "canceled", "expired")]
    if failed:
        r.add(WARN, f"{len(failed)} Alpaca order(s) did not go through: "
                    + ", ".join(f"{o['coin']} {o['side']} ({o['status']})" for o in failed[-5:]))
    if not strange and not big and not failed:
        r.add(OK, f"All {len(orders)} Alpaca orders were for the bot's coins and within the limit.")


def check_costs(r, now):
    r.section("Costs")
    rows = [x for p in glob.glob(os.path.join(COSTS, "*.csv")) for x in read_csv(p)]
    if not rows:
        r.add(OK, "No AI runs logged yet (cost logging started on 2026-10-18).")
        return
    month = now.strftime("%Y-%m")
    this_month = [x for x in rows if x["time_utc"].startswith(month)]
    spent = sum(float(x["cost_usd"]) for x in this_month)
    over = [x for x in rows if float(x["cost_usd"]) > RUN_BUDGET]
    for x in over[-5:]:
        r.add(WARN, f"{x['agent']} cost ${float(x['cost_usd']):.2f} on {x['time_utc'][:10]} "
                    f"(budget ${RUN_BUDGET:.2f} per run).")
    day_of_month = now.day
    days_in_month = ((now.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)).day
    projected = spent / max(1, day_of_month) * days_in_month
    status = WARN if projected > MONTH_BUDGET else OK
    r.add(status, f"Spent ${spent:.2f} so far this month on {len(this_month)} AI runs; "
                  f"on pace for about ${projected:.0f} (budget ${MONTH_BUDGET:.0f}).")


def check_health(r):
    r.section("Agent health")
    bad = []
    for folder, label in (("news", "World brief"), ("crypto", "Crypto brief"), ("stocks", "Stock brief")):
        try:
            text = open(os.path.join("reports", folder, "last-run-log.txt")).read()
        except OSError:
            continue
        if "Traceback" in text or "Saved " not in text:
            bad.append(label)
    for label in bad:
        r.add(BAD, f"{label} failed on its last run. See its last-run-log.txt.")
    if not bad:
        r.add(OK, "Every research brief worked on its last run.")


# ---------------- output ----------------

def write(r, now):
    ok, warn, bad = r.counts()
    verdict = (f"{BAD} {bad} broken rule(s)" if bad else f"{WARN} {warn} thing(s) to look at"
               if warn else f"{OK} All clear")
    out = ["# 👔 CEO check", "",
           f"*Checked {now:%Y-%m-%d %H:%M} New York time. Plain code, no AI.*", "",
           f"**{verdict}**: {ok} passed, {warn} warnings, {bad} broken rules.", ""]
    for title, lines in r.sections:
        out += [f"### {title}", ""] + [f"- {s} {t}" for s, t in lines] + [""]
    os.makedirs(FOLDER, exist_ok=True)
    with open(os.path.join(FOLDER, "latest.md"), "w") as f:
        f.write("\n".join(out))
    path = os.path.join(FOLDER, "history.csv")
    new = not os.path.exists(path)
    with open(path, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["time_ny", "passed", "warnings", "broken"])
        w.writerow([now.strftime("%Y-%m-%d %H:%M"), ok, warn, bad])
    print(verdict)


def main(now=None):
    now = now or datetime.now(ZoneInfo("America/New_York")).replace(tzinfo=None)
    r = Report()
    for check in (check_paper_trader, check_my_journal, check_crypto, check_alpaca):
        try:
            check(r)
        except Exception as error:      # a broken check must never stop the others
            r.add(WARN, f"This check could not run: {error}")
    for check in (lambda rep: check_costs(rep, now), check_health):
        try:
            check(r)
        except Exception as error:
            r.add(WARN, f"This check could not run: {error}")
    write(r, now)


if __name__ == "__main__":
    main()
