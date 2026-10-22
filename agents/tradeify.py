"""
tradeify.py - Replays trades against Tradeify's GROWTH 50K rules: the
evaluation, then the Sim Funded account with its payout rules.

Rules as written in Tradeify's help center on 2026-10-21 (help.tradeify.co:
"GROWTH Evaluation Accounts", "Growth Funded: Account Payout Policy",
"Rules: Consistency Rule", "Essential Trading Rules Overview"). Prop firms
change their rules; check those pages before relying on this.

EVALUATION
  - Pass: balance reaches $53,000 (+$3,000). No consistency rule, 1 day minimum.
  - Trailing max drawdown $2,000 below the highest END-OF-DAY balance. It is
    enforced in real time on net liquidation (open trades count): touching it
    even for a moment fails the account.
  - Daily loss limit $1,250 (soft): trading stops for the rest of the day.
SIM FUNDED
  - Same drawdown and daily loss limit, but the floor locks at $50,100 once
    the end-of-day balance reaches $52,100.
  - A payout needs: balance >= $53,000, 5 trading days with more than $150
    profit, and the 35% consistency rule (biggest day <= 35% of the profit
    since the last payout). Max payout: $1,500, $2,000, $2,500, then $3,000.
    After a payout the day count and the consistency both start over.
A trading day runs 6 PM to 5 PM New York, so the evening gold session
belongs to the next day's Nasdaq session.

Each trade passed in is a dict with: day (trading day), net (dollars after
fees), worst (dollars of open loss at the trade's worst point, >= 0).
"""

RULES = {
    "name": "Tradeify Growth 50K",
    "start": 50000,
    "target": 3000,
    "drawdown": 2000,
    "daily_loss_limit": 1250,
    "lock_at": 52100,           # funded: floor locks once EOD balance reaches this
    "locked_floor": 50100,
    "payout_balance": 53000,
    "payout_days": 5,
    "payout_day_min": 150,
    "consistency": 0.35,
    "payout_caps": [1500, 2000, 2500, 3000],
    "min_payout": 500,
}


def _new(phase, day, r):
    return {"phase": phase, "start": day, "end": day, "balance": r["start"],
            "peak_eod": r["start"], "days": 0, "result": "In progress", "note": "",
            "payouts": [], "cycle_days": [], "dll_days": 0}


def floor(a, r=RULES):
    if a["phase"] == "Funded" and a["peak_eod"] >= r["lock_at"]:
        return r["locked_floor"]
    return a["peak_eod"] - r["drawdown"]


def payout_status(a, r=RULES):
    """(eligible, text) for a funded account's current payout cycle."""
    profit = a["balance"] - (a["cycle_start_balance"])
    good_days = sum(1 for p in a["cycle_days"] if p > r["payout_day_min"])
    biggest = max([p for p in a["cycle_days"] if p > 0], default=0)
    share = biggest / profit if profit > 0 else 1.0
    checks = [a["balance"] >= r["payout_balance"], good_days >= r["payout_days"],
              share <= r["consistency"]]
    text = (f"balance ${a['balance']:,.0f} of ${r['payout_balance']:,}, "
            f"{good_days} of {r['payout_days']} days over ${r['payout_day_min']}, "
            f"biggest day {share:.0%} of profit (needs {r['consistency']:.0%} or less)")
    return all(checks), text


def simulate(trades, r=RULES):
    """Back-to-back attempts. Each evaluation that passes becomes a funded
    account the next trading day. Returns a list of attempt dicts."""
    days = {}
    for t in trades:
        days.setdefault(t["day"], []).append(t)
    attempts, a = [], None
    for day in sorted(days):
        if a is None:
            a = _new("Evaluation", day, r)
        if a["start"] is None:
            a["start"] = day                 # a funded account starts here
        if a["phase"] == "Funded" and "cycle_start_balance" not in a:
            a["cycle_start_balance"] = a["balance"]
        day_pnl, traded, failed = 0.0, False, False
        for t in days[day]:
            if day_pnl <= -r["daily_loss_limit"]:
                break                       # soft breach: done for the day
            traded = True
            low = a["balance"] + day_pnl - t["worst"]
            if low <= floor(a, r):
                a["result"] = "Failed"
                a["note"] = (f"{day}: an open trade took the account to ${low:,.0f}, "
                             f"below the ${floor(a, r):,.0f} drawdown floor")
                failed = True
                break
            if day_pnl - t["worst"] <= -r["daily_loss_limit"]:
                day_pnl = -r["daily_loss_limit"]   # closed at the daily loss limit
                a["dll_days"] += 1
                break
            day_pnl += t["net"]
        a["end"] = day
        a["days"] += 1 if traded else 0
        if failed:
            attempts.append(a)
            a = None
            continue
        a["balance"] += day_pnl
        if a["balance"] <= floor(a, r):
            a["result"] = "Failed"
            a["note"] = f"{day}: balance ${a['balance']:,.0f} at or below the floor"
            attempts.append(a)
            a = None
            continue
        a["peak_eod"] = max(a["peak_eod"], a["balance"])
        if a["phase"] == "Evaluation":
            if a["balance"] >= r["start"] + r["target"]:
                a["result"] = "Passed"
                attempts.append(a)
                a = _new("Funded", day, r)
                a["start"] = None            # starts on the next trading day
        else:
            if traded:
                a["cycle_days"].append(day_pnl)
            ok, _ = payout_status(a, r)
            if ok:
                n = len(a["payouts"])
                amount = min(r["payout_caps"][min(n, len(r["payout_caps"]) - 1)],
                             a["balance"] - r["locked_floor"])
                if amount >= r["min_payout"]:
                    a["payouts"].append((day, amount))
                    a["balance"] -= amount
                    a["cycle_days"] = []
                    a["cycle_start_balance"] = a["balance"]
    if a is not None and (a["phase"] == "Funded" or a["days"]):
        attempts.append(a)
    return attempts


class TradeifyAccount:
    """A live Tradeify Growth 50K practice account the bot trades ON, so it
    sizes every trade by the account's real limits (same interface as
    main.Account: mode, allowance, room, record).

    - A trade is only taken if hitting its stop leaves the account above the
      drawdown floor and inside the daily loss limit, with BUFFER dollars to
      spare for slippage; otherwise the small size, otherwise skipped.
    - The daily loss limit stops the rest of the trading day.
    - Once the trading day is up PROFIT_CAP, no more trades that day (helps
      the 35% consistency rule on the funded account).
    - A failed evaluation is followed by a new one the next trading day, and
      a passed one by a funded account, like simulate().
    """

    BUFFER = 100
    PROFIT_CAP = 600
    RESET_BELOW = 400   # evaluation this close to its floor: reset it (no trade fits)

    def __init__(self, rules=RULES):
        self.r = rules
        self.attempts = []
        self.a = None
        self.day = None
        self.day_pnl = 0.0
        self.day_traded = False
        self.failed_today = False
        self.stopped_on = None      # never: a failed account is replaced
        self.paused_until = None

    # -- day handling --
    def _close_day(self):
        a, r = self.a, self.r
        if a is None or self.failed_today:
            return
        a["balance"] += self.day_pnl
        a["end"] = self.day
        if self.day_traded:
            a["days"] += 1
        a["peak_eod"] = max(a["peak_eod"], a["balance"])
        if a["phase"] == "Evaluation" and a["balance"] >= r["start"] + r["target"]:
            a["result"] = "Passed"
            self.attempts.append(a)
            self.a = _new("Funded", None, r)
            self.a["start"] = None
            return
        if a["phase"] == "Funded" and self.day_traded:
            a.setdefault("cycle_start_balance", r["start"])
            a["cycle_days"].append(self.day_pnl)
            ok, _ = payout_status(a, r)
            if ok:
                n = len(a["payouts"])
                amount = min(r["payout_caps"][min(n, len(r["payout_caps"]) - 1)],
                             a["balance"] - r["locked_floor"])
                if amount >= r["min_payout"]:
                    a["payouts"].append((self.day, amount))
                    a["balance"] -= amount
                    a["cycle_days"] = []
                    a["cycle_start_balance"] = a["balance"]

    def _roll(self, start):
        import main
        day = main.trading_day(start).isoformat()
        if day == self.day:
            return
        self._close_day()
        self.day, self.day_pnl, self.day_traded, self.failed_today = day, 0.0, False, False
        if self.a is None:
            self.a = _new("Evaluation", day, self.r)
        elif self.a["phase"] == "Evaluation" and self.room() < self.RESET_BELOW:
            self.a["result"] = "Failed"
            self.a["note"] = (f"reset on {day}: only ${self.room():,.0f} above the floor, "
                              "too close for any trade")
            self.attempts.append(self.a)
            self.a = _new("Evaluation", day, self.r)
        if self.a["start"] is None:
            self.a["start"] = day
            self.a.setdefault("cycle_start_balance", self.a["balance"])

    # -- the main.Account interface --
    def can_trade(self, start):
        self._roll(start)
        return True

    def mode(self, start):
        self._roll(start)
        if self.failed_today or self.day_pnl <= -self.r["daily_loss_limit"]:
            return "day_stopped"
        if self.PROFIT_CAP is not None and self.day_pnl >= self.PROFIT_CAP:
            return "day_done"
        return "normal"

    def room(self):
        return self.a["balance"] + self.day_pnl - floor(self.a, self.r)

    def allowance(self):
        return min(self.room(), self.r["daily_loss_limit"] + self.day_pnl) - self.BUFFER

    def record(self, profit, start=None, worst=0.0):
        """profit: the trade's result (after fees); worst: its biggest open
        loss in dollars (the stop caps it)."""
        if start is not None:
            self._roll(start)
        a = self.a
        self.day_traded = True
        if a["balance"] + self.day_pnl - worst <= floor(a, self.r):
            a["result"] = "Failed"
            a["end"] = self.day
            a["days"] += 1
            a["note"] = f"{self.day}: an open trade touched the drawdown floor"
            a["balance"] = floor(a, self.r)
            self.attempts.append(a)
            self.a = None
            self.failed_today = True
            return
        if self.day_pnl - worst <= -self.r["daily_loss_limit"]:
            self.day_pnl = -self.r["daily_loss_limit"]
            a["dll_days"] += 1
            return
        self.day_pnl += profit

    def finish(self):
        """Close the current day; returns every attempt so far, the open one last."""
        self._close_day()
        self.failed_today = True        # so a second call does not count the day twice
        return self.attempts + ([self.a] if self.a is not None else [])
