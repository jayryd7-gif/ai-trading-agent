"""
crypto_bots.py - Agent #7: two crypto paper trading bots and their dashboard.

Run it from the project folder:
    python crypto/crypto_bots.py

THE BOTS (each starts with $1,000, in two separate accounts):
  Rotation bot    Once a week, holds the 5 coins (of COINS) with the biggest
                  gain over the last 120 days, in equal amounts, but only
                  coins above their 50-day average, and only while bitcoin is
                  above its 50-day average too. Between weekly checks it
                  sells any coin whose uptrend breaks. When bitcoin's uptrend
                  breaks, it moves fully to cash.
  Buy-and-hold    Buys equal amounts of BTC, ETH and SOL on day one and never
  bot             sells. The yardstick for the rotation bot.

HOW IT RUNS: once a day after the daily close (00:00 UTC):
  - PAPER accounts start fresh with $1,000 each on PAPER_START and trade
    forward from there, with no real money.
  - BACKTEST accounts replay the same rules from BACKTEST_START (four years
    back), to show how the rules behaved in the past.
Every buy and sell is at that day's closing price, after a FEE percent fee.

It writes:
  CRYPTO-DASHBOARD.md                    the crypto dashboard
  crypto/journal-rotation.md             paper trades, rotation bot
  crypto/journal-hold.md                 paper trades, buy-and-hold bot
  crypto/backtest/journal-*.md           the four-year backtest trades
  crypto/trades.csv                      every trade from all four accounts
  crypto/charts/*.svg                    the charts
Every journal ends with the account's total profit or loss.

It places NO orders and has no exchange access.
"""

import csv
import json
import os
import sys
import time
import urllib.request
from datetime import date, datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import strategy_lab as lab
from crypto_charts import holdings_chart, value_chart, drawdown_chart

# ---------------- SETTINGS ----------------
START_CASH = 1000.0
PAPER_START = date(2026, 10, 17)     # the paper accounts' first day (buys at its close)
BACKTEST_START = date(2022, 10, 19)  # four years of history
FEE = 0.4                        # percent per dollar bought or sold
COINS = ["BTC", "ETH", "XRP", "BNB", "SOL", "DOGE", "ADA", "TRX", "LINK", "AVAX",
         "XLM", "SUI", "HYPE", "LTC", "BCH", "DOT", "TON", "UNI"]
HOLD_COINS = ["BTC", "ETH", "SOL"]
TOP, LOOKBACK, EVERY, TREND_DAYS = 5, 120, 7, 50
DASHBOARD = "CRYPTO-DASHBOARD.md"
CHARTS = os.path.join("crypto", "charts")
# ------------------------------------------

BINANCE = "https://data-api.binance.vision/api/v3/klines?symbol={}USDT&interval=1d&startTime={}&limit=1000"


def _get(url, body=None):
    data = json.dumps(body).encode() if body else None
    request = urllib.request.Request(url, data=data, headers={
        "User-Agent": "ai-trading-agent", "Content-Type": "application/json"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.load(response)
        except Exception:
            if attempt == 3:
                raise
            time.sleep(2 + attempt * 3)


def daily_closes(coin, since=BACKTEST_START - timedelta(days=200)):
    """{date: close} for finished days only (today's candle is still forming)."""
    today = datetime.now(timezone.utc).date()
    ms = int(datetime(since.year, since.month, since.day, tzinfo=timezone.utc).timestamp() * 1000)
    out = {}
    if coin == "HYPE":   # not on Binance long enough; use Hyperliquid
        rows = _get("https://api.hyperliquid.xyz/info", {"type": "candleSnapshot", "req": {
            "coin": "HYPE", "interval": "1d", "startTime": ms, "endTime": int(time.time() * 1000)}})
        for r in rows:
            out[datetime.fromtimestamp(r["t"] / 1000, timezone.utc).date()] = float(r["c"])
    else:
        while True:
            rows = _get(BINANCE.format(coin, ms))
            for r in rows:
                out[datetime.fromtimestamp(r[0] / 1000, timezone.utc).date()] = float(r[4])
            if len(rows) < 1000:
                break
            ms = rows[-1][0] + 1
            time.sleep(0.2)
    return {d: p for d, p in out.items() if d < today}


# ---------------- the engine ----------------

def run_bot(name, market, rule, reason_for):
    """Replay a bot. Returns (daily rows, trades)."""
    cash, units, cost = START_CASH, {}, {}
    days, trades = [], []
    for day in market.dates:
        price = {c: market.price(c, day) for c in units}
        value = cash + sum(units[c] * price[c] for c in units)
        weights = {c: units[c] * price[c] / value for c in units}
        target = rule(market, day, weights)
        kept = {c: weights[c] for c in target if c in weights}
        fresh = {c: w for c, w in target.items() if c not in weights}

        for c in [c for c in units if c not in kept]:          # sells
            proceeds = units[c] * price[c]
            fee = proceeds * FEE / 100
            cash += proceeds - fee
            trades.append({"bot": name, "date": day, "action": "Sell", "coin": c,
                           "price": price[c], "units": units[c], "dollars": proceeds,
                           "fee": fee, "profit": proceeds - fee - cost[c],
                           "reason": reason_for(market, day, c, "Sell")})
            del units[c], cost[c]

        share_left = max(0.0, 1 - sum(kept.values()))
        scale = min(1.0, share_left / sum(fresh.values())) if fresh else 1.0
        for c, w in sorted(fresh.items()):                      # buys
            p = market.price(c, day)
            spend = min(cash, w * scale * value)
            if spend < 1:
                continue
            fee = spend * FEE / 100
            units[c] = (spend - fee) / p
            cost[c] = spend
            cash -= spend
            trades.append({"bot": name, "date": day, "action": "Buy", "coin": c, "price": p,
                           "units": units[c], "dollars": spend, "fee": fee, "profit": None,
                           "reason": reason_for(market, day, c, "Buy")})

        value = cash + sum(units[c] * market.price(c, day) for c in units)
        days.append({"date": day, "value": value, "cash": cash,
                     "holdings": {c: units[c] * market.price(c, day) for c in units},
                     "cost": dict(cost)})
    return days, trades


def rotation_reason(m, day, coin, action):
    if action == "Sell":
        if not lab.above_average(m, coin, day, TREND_DAYS):
            return f"{coin} closed below its {TREND_DAYS}-day average (its uptrend broke)"
        if not lab.above_average(m, "BTC", day, TREND_DAYS):
            return f"bitcoin closed below its {TREND_DAYS}-day average, so the bot moved to cash"
        return f"no longer one of the top {TOP} at the weekly check"
    scored = sorted(((lab.momentum(m, c, day, LOOKBACK), c) for c in COINS if m.price(c, day)
                     and lab.momentum(m, c, day, LOOKBACK) is not None
                     and lab.above_average(m, c, day, TREND_DAYS)), reverse=True)
    rank = next((i + 1 for i, (_, c) in enumerate(scored) if c == coin), None)
    gain = lab.momentum(m, coin, day, LOOKBACK)
    return (f"weekly check: #{rank} by {LOOKBACK}-day gain ({gain:+.0%}), "
            f"in an uptrend, with bitcoin in an uptrend")


def hold_reason(m, day, coin, action):
    return "day one: equal thirds of BTC, ETH and SOL, held for good"


# ---------------- reporting ----------------

def money(v, cents=False):
    if v is None:
        return ""
    sign = "-" if v < 0 else ""
    return f"{sign}${abs(v):,.2f}" if cents else f"{sign}${abs(v):,.0f}"


def price_text(p):
    return f"${p:,.2f}" if p >= 1 else f"${p:,.4f}"


def worst_fall(days):
    peak, worst = 0.0, 0.0
    for d in days:
        peak = max(peak, d["value"])
        worst = max(worst, 1 - d["value"] / peak)
    return worst


def totals(days, trades):
    """The account's totals, for the journals and the dashboard."""
    if not days:
        return None
    last = days[-1]
    realized = sum(t["profit"] for t in trades if t["profit"] is not None)
    open_pl = sum(v - last["cost"][c] for c, v in last["holdings"].items())
    return {"date": last["date"], "value": last["value"], "profit": last["value"] - START_CASH,
            "realized": realized, "open": open_pl, "fees": sum(t["fee"] for t in trades),
            "buys": sum(t["action"] == "Buy" for t in trades),
            "sells": sum(t["action"] == "Sell" for t in trades),
            "wins": sum(1 for t in trades if t["profit"] is not None and t["profit"] > 0)}


def totals_lines(t):
    if t is None:
        return ["No trades yet. The first buys happen at the first daily close."]
    return [f"- **Started with:** {money(START_CASH, True)}",
            f"- **Value on {t['date']}:** {money(t['value'], True)}",
            f"- **Total profit / loss:** **{money(t['profit'], True)} "
            f"({t['profit'] / START_CASH:+.1%})**",
            f"  - From coins already sold: {money(t['realized'], True)} "
            f"({t['wins']} of {t['sells']} sells made money)",
            f"  - On coins still held: {money(t['open'], True)}",
            f"- **Fees paid (included above):** {money(t['fees'], True)}",
            f"- **Trades:** {t['buys']} buys, {t['sells']} sells"]


def trade_table(trades, limit=None):
    rows = ["| Date | | Coin | Price | Amount | Profit / loss | Why |",
            "|---|---|---|---|---|---|---|"]
    for t in sorted(trades, key=lambda t: t["date"], reverse=True)[:limit]:
        icon = "🟢 Buy" if t["action"] == "Buy" else "🔴 Sell"
        pl = "" if t["profit"] is None else money(t["profit"], True)
        rows.append(f"| {t['date']} | {icon} | {t['coin']} | {price_text(t['price'])} | "
                    f"{money(t['dollars'], True)} | {pl} | {t['reason']} |")
    return rows


def holdings_table(days):
    if not days:
        return ["Nothing yet: the first buys happen at the first daily close.", ""]
    last = days[-1]
    if not last["holdings"]:
        return ["All cash: nothing is held right now.", ""]
    rows = ["| Coin | Value now | Paid | Profit / loss | Share of the bot |", "|---|---|---|---|---|"]
    for c, v in sorted(last["holdings"].items(), key=lambda kv: -kv[1]):
        paid = last["cost"][c]
        rows.append(f"| {c} | {money(v, True)} | {money(paid, True)} | "
                    f"{money(v - paid, True)} ({(v / paid - 1):+.1%}) | {v / last['value']:.0%} |")
    rows.append(f"| Cash | {money(last['cash'], True)} | | | {last['cash'] / last['value']:.0%} |")
    return rows + [""]


def glance_table(bots):
    rows = ["| Bot | Started with | Value now | Total profit / loss | Worst fall | Trades | Holding now |",
            "|---|---|---|---|---|---|---|"]
    for name, (days, trades) in bots.items():
        if not days:
            rows.append(f"| **{name}** | {money(START_CASH)} | {money(START_CASH)} | $0.00 | | 0 | "
                        "first buys at the next daily close |")
            continue
        last = days[-1]
        held = ", ".join(c for c, _ in sorted(last["holdings"].items(), key=lambda kv: -kv[1])) or "cash"
        rows.append(f"| **{name}** | {money(START_CASH)} | **{money(last['value'], True)}** | "
                    f"{money(last['value'] - START_CASH, True)} ({last['value'] / START_CASH - 1:+.1%}) | "
                    f"{worst_fall(days):.0%} | {len(trades)} | {held} |")
    return rows + [""]


def monthly_table(bots):
    months = {}
    for name, (days, _) in bots.items():
        for d in days:
            months.setdefault(d["date"].strftime("%Y-%m"), {})[name] = d["value"]
    rows = ["| Month end | " + " | ".join(bots) + " |", "|---" * (len(bots) + 1) + "|"]
    for month in sorted(months, reverse=True):
        rows.append(f"| {month} | " + " | ".join(money(months[month].get(n)) for n in bots) + " |")
    return rows


def write_journal(path, title, about, days, trades):
    lines = [f"# {title}", "", about, "", "Every trade, oldest first. No real money.", ""]
    for t in sorted(trades, key=lambda t: t["date"]):
        lines += [f"### {t['date']} | {t['action']} {t['coin']}",
                  f"- **Price:** {price_text(t['price'])} (that day's close)",
                  f"- **Amount:** {money(t['dollars'], True)} for {t['units']:.6g} {t['coin']}, "
                  f"fee {money(t['fee'], True)}"]
        if t["profit"] is not None:
            lines.append(f"- **Profit / loss on this coin:** {money(t['profit'], True)}")
        lines += [f"- **Why:** {t['reason']}", ""]
    lines += ["---", "", "## Total", ""] + totals_lines(totals(days, trades)) + [""]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write("\n".join(lines))


ABOUT = {"Rotation bot": f"Holds up to {TOP} of the strongest coins by {LOOKBACK}-day gain, "
                         f"rechecked every {EVERY} days, only while each coin and bitcoin are "
                         f"above their {TREND_DAYS}-day averages. Otherwise cash.",
         "Buy-and-hold bot": "Bought equal thirds of BTC, ETH and SOL on day one and never sells."}


def bot_section(name, icon, days, trades, journal, limit=10):
    out = [f"### {icon} {name}", "", ABOUT[name], "", "**Holding now**", ""] + holdings_table(days)
    if trades:
        out += [f"**Latest trades**", ""] + trade_table(trades, limit) + [""]
        if len(trades) > limit:
            out += ["<details>", f"<summary><b>All {len(trades)} trades</b></summary>", "",
                    *trade_table(trades), "", "</details>", ""]
    out += ["**Total**", ""] + totals_lines(totals(days, trades)) + ["", f"[Journal]({journal})", ""]
    return out


def build_dashboard(paper, backtest, now):
    any_days = next((d for d, _ in paper.values() if d), None) or next(d for d, _ in backtest.values())
    out = ["# 🪙 Crypto Dashboard", "",
           f"*Updated {now:%Y-%m-%d %H:%M} UTC with prices up to the close on "
           f"{any_days[-1]['date']}. **No real money is used.** Trades happen at daily closing "
           f"prices (00:00 UTC), after a {FEE}% fee. This is research, not financial advice.*", "",
           "[← Main dashboard](DASHBOARD.md)", "",
           f"## 📄 Paper trading: started {PAPER_START} with {money(START_CASH)} each", ""]
    out += glance_table(paper)
    paper_days = next(iter(paper.values()))[0]
    if len(paper_days) >= 2:
        out += ["![Paper accounts' value](crypto/charts/paper-value.svg)", ""]
    out += ["<!-- ALPACA -->", ""]   # alpaca_sync.py puts the Alpaca account here
    out += bot_section("Rotation bot", "🔄", *paper["Rotation bot"], "crypto/journal-rotation.md")
    out += bot_section("Buy-and-hold bot", "🏦", *paper["Buy-and-hold bot"], "crypto/journal-hold.md")

    out += [f"## 📚 Four-year backtest: the same rules from {BACKTEST_START}", "",
            "What the rules would have done with $1,000 each on real past prices. "
            "It keeps running forward alongside the paper accounts.", ""]
    out += glance_table(backtest)
    for alt, path in (("Value of each bot", "value.svg"),
                      ("What the rotation bot held, and when", "rotation-holdings.svg"),
                      ("Drop from each bot's high", "drawdown.svg")):
        out += [f"![{alt}](crypto/charts/{path})", ""]
    out += bot_section("Rotation bot", "🔄", *backtest["Rotation bot"],
                       "crypto/backtest/journal-rotation.md")
    out += bot_section("Buy-and-hold bot", "🏦", *backtest["Buy-and-hold bot"],
                       "crypto/backtest/journal-hold.md")
    out += ["### Month by month (backtest)", "", "Each bot's value at the end of each month.", ""]
    out += monthly_table(backtest) + [""]
    out += ["## Files", "",
            "- [Every trade, all accounts (CSV)](crypto/trades.csv)",
            "- [How these strategies were chosen](crypto/STRATEGIES.md)", ""]
    return "\n".join(out)


def run_accounts(market, coins):
    return {
        "Rotation bot": run_bot("Rotation bot", market,
                                lab.rotation(coins, LOOKBACK, TOP, EVERY, TREND_DAYS),
                                rotation_reason),
        "Buy-and-hold bot": run_bot("Buy-and-hold bot", market,
                                    lab.buy_and_hold(HOLD_COINS), hold_reason),
    }


def main():
    data = {}
    for coin in sorted(set(COINS) | set(HOLD_COINS)):
        try:
            data[coin] = daily_closes(coin)
        except Exception as error:
            print(f"Could not load {coin}: {error}")
    if "BTC" not in data:
        raise SystemExit("No bitcoin prices, so nothing was updated.")
    coins = [c for c in COINS if c in data]
    backtest = run_accounts(lab.Market(coins, data=data, start=BACKTEST_START), coins)
    paper = run_accounts(lab.Market(coins, data=data, start=PAPER_START), coins)

    os.makedirs(CHARTS, exist_ok=True)
    series = {n: [(d["date"], d["value"]) for d in days] for n, (days, _) in backtest.items()}
    with open(os.path.join(CHARTS, "value.svg"), "w") as f:
        f.write(value_chart(series, START_CASH, None, backtest["Rotation bot"][1]))
    with open(os.path.join(CHARTS, "rotation-holdings.svg"), "w") as f:
        f.write(holdings_chart(backtest["Rotation bot"][0], None))
    with open(os.path.join(CHARTS, "drawdown.svg"), "w") as f:
        f.write(drawdown_chart(series))
    paper_series = {n: [(d["date"], d["value"]) for d in days] for n, (days, _) in paper.items()}
    if all(len(s) >= 2 for s in paper_series.values()):
        with open(os.path.join(CHARTS, "paper-value.svg"), "w") as f:
            f.write(value_chart(paper_series, START_CASH, None, paper["Rotation bot"][1]))

    with open(os.path.join("crypto", "trades.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["account", "bot", "date", "action", "coin", "price", "units", "dollars",
                    "fee", "profit", "reason"])
        for account, bots in (("paper", paper), ("backtest", backtest)):
            for t in sorted((t for _, tr in bots.values() for t in tr),
                            key=lambda t: (t["date"], t["bot"])):
                w.writerow([account, t["bot"], t["date"], t["action"], t["coin"],
                            f"{t['price']:.6g}", f"{t['units']:.8g}", f"{t['dollars']:.2f}",
                            f"{t['fee']:.2f}", "" if t["profit"] is None else f"{t['profit']:.2f}",
                            t["reason"]])

    for account, bots, folder in (("Paper", paper, "crypto"),
                                  ("Backtest", backtest, os.path.join("crypto", "backtest"))):
        since = PAPER_START if account == "Paper" else BACKTEST_START
        for name, file in (("Rotation bot", "journal-rotation.md"), ("Buy-and-hold bot", "journal-hold.md")):
            write_journal(os.path.join(folder, file), f"{name} journal ({account.lower()}, since {since})",
                          ABOUT[name], *bots[name])

    # Each paper bot's value per day, for the weekly report
    with open(os.path.join("crypto", "paper-values.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date"] + list(paper))
        dates = sorted({d["date"] for days, _ in paper.values() for d in days})
        values = {n: {d["date"]: d["value"] for d in days} for n, (days, _) in paper.items()}
        for day in dates:
            w.writerow([day] + [f"{values[n].get(day, START_CASH):.2f}" for n in paper])

    # What the paper rotation bot holds now, for alpaca_sync.py to copy
    rot_days = paper["Rotation bot"][0]
    with open(os.path.join("crypto", "paper-targets.json"), "w") as f:
        json.dump({"date": str(rot_days[-1]["date"]) if rot_days else None,
                   "value": rot_days[-1]["value"] if rot_days else START_CASH,
                   "holdings": rot_days[-1]["holdings"] if rot_days else {}}, f, indent=2)

    now = datetime.now(timezone.utc)
    with open(DASHBOARD, "w") as f:
        f.write(build_dashboard(paper, backtest, now))
    for account, bots in (("Paper", paper), ("Backtest", backtest)):
        for name, (days, trades) in bots.items():
            value = days[-1]["value"] if days else START_CASH
            print(f"{account} {name}: {money(value, True)} after {len(trades)} trades")
    print(f"Wrote {DASHBOARD}")


if __name__ == "__main__":
    main()
