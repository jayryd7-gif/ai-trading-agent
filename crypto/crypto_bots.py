"""
crypto_bots.py - Agent #7: two crypto paper trading bots and their dashboard.

Run it from the project folder:
    python crypto/crypto_bots.py

THE BOTS (each starts with $1,000):
  Rotation bot    Once a week, holds the 5 coins (of COINS) with the biggest
                  gain over the last 120 days, in equal amounts, but only
                  coins above their 50-day average, and only while bitcoin is
                  above its 50-day average too. Between weekly checks it
                  sells any coin whose uptrend breaks. When bitcoin's uptrend
                  breaks, it moves fully to cash.
  Buy-and-hold    Buys equal amounts of BTC, ETH and SOL on day one and never
  bot             sells. The yardstick for the rotation bot.

HOW IT RUNS: once a day after the daily close (00:00 UTC), it replays both
bots from START (four years back) to the latest finished day, using real
daily closing prices. Days before GO_LIVE are a backtest (what the rules
would have done). From GO_LIVE on it is paper trading: the same rules, run
forward, with no real money. Every buy and sell is at that day's closing
price, after a FEE percent fee.

It writes:
  CRYPTO-DASHBOARD.md          the crypto dashboard
  crypto/journal-rotation.md   every rotation bot trade, with the reason
  crypto/journal-hold.md       the buy-and-hold bot's trades
  crypto/trades.csv            every trade from both bots
  crypto/charts/*.svg          the charts

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
START = date(2022, 10, 19)       # four years of history before going live
GO_LIVE = date(2026, 10, 19)     # paper trading from this day on
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


def daily_closes(coin, since=START - timedelta(days=200)):
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


def phase(day):
    return "paper" if day >= GO_LIVE else "backtest"


def trade_table(trades, newest_first=True):
    rows = ["| Date | | Coin | Price | Amount | Profit / loss | Why | Type |",
            "|---|---|---|---|---|---|---|---|"]
    for t in sorted(trades, key=lambda t: t["date"], reverse=newest_first):
        icon = "🟢 Buy" if t["action"] == "Buy" else "🔴 Sell"
        pl = "" if t["profit"] is None else money(t["profit"], True)
        rows.append(f"| {t['date']} | {icon} | {t['coin']} | {price_text(t['price'])} | "
                    f"{money(t['dollars'], True)} | {pl} | {t['reason']} | {phase(t['date'])} |")
    return rows


def holdings_table(last, market):
    if not last["holdings"]:
        return ["All cash: nothing is held right now.", ""]
    rows = ["| Coin | Value now | Paid | Profit / loss | Share of the bot |", "|---|---|---|---|---|"]
    for c, v in sorted(last["holdings"].items(), key=lambda kv: -kv[1]):
        paid = last["cost"][c]
        rows.append(f"| {c} | {money(v, True)} | {money(paid, True)} | "
                    f"{money(v - paid, True)} ({(v / paid - 1):+.1%}) | {v / last['value']:.0%} |")
    rows.append(f"| Cash | {money(last['cash'], True)} | | | {last['cash'] / last['value']:.0%} |")
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


def write_journal(path, title, about, trades):
    lines = [f"# {title}", "", about, "",
             f"Every trade, oldest first. Trades before {GO_LIVE} are a backtest (what the "
             "rules would have done); trades from then on are paper trades. No real money.", ""]
    for t in sorted(trades, key=lambda t: t["date"]):
        lines += [f"### {t['date']} | {t['action']} {t['coin']} | {phase(t['date'])}",
                  f"- **Price:** {price_text(t['price'])} (that day's close)",
                  f"- **Amount:** {money(t['dollars'], True)} for {t['units']:.6g} {t['coin']}, "
                  f"fee {money(t['fee'], True)}"]
        if t["profit"] is not None:
            lines.append(f"- **Profit / loss on this coin:** {money(t['profit'], True)}")
        lines += [f"- **Why:** {t['reason']}", ""]
    with open(path, "w") as f:
        f.write("\n".join(lines))


def build_dashboard(bots, market, now):
    rot_days, rot_trades = bots["Rotation bot"]
    hold_days, hold_trades = bots["Buy-and-hold bot"]
    last_day = rot_days[-1]["date"]
    out = ["# 🪙 Crypto Dashboard", "",
           f"*Updated {now:%Y-%m-%d %H:%M} UTC with prices up to the close on {last_day}. "
           f"Each bot started with {money(START_CASH)} on {START}. Before {GO_LIVE} the "
           "results are a backtest (what the rules would have done on real prices); from "
           f"{GO_LIVE} on they are paper trades. **No real money is used.** "
           "Prices are daily closes, after a "
           f"{FEE}% fee per trade. This is research, not financial advice.*", "",
           "[← Main dashboard](DASHBOARD.md)", "",
           "## At a glance", "",
           "| Bot | Started with | Value now | Return | Worst fall | Trades | Holding now |",
           "|---|---|---|---|---|---|---|"]
    for name, (days, trades) in bots.items():
        last = days[-1]
        held = ", ".join(c for c, _ in sorted(last["holdings"].items(), key=lambda kv: -kv[1])) or "cash"
        out.append(f"| **{name}** | {money(START_CASH)} | **{money(last['value'], True)}** | "
                   f"{last['value'] / START_CASH - 1:+.1%} | {worst_fall(days):.0%} | "
                   f"{len(trades)} | {held} |")
    out += ["", "## Charts", ""]
    for alt, path in (("Value of each bot", "value.svg"),
                      ("What the rotation bot held, and when", "rotation-holdings.svg"),
                      ("Drop from each bot's high", "drawdown.svg")):
        out += [f"![{alt}](crypto/charts/{path})", ""]

    out += ["## 🔄 Rotation bot", "",
            f"Holds up to {TOP} of the strongest coins by {LOOKBACK}-day gain, rechecked "
            f"every {EVERY} days, only while each coin and bitcoin are above their "
            f"{TREND_DAYS}-day averages. Otherwise cash.", "",
            "### Holding now", ""] + holdings_table(rot_days[-1], market)
    out += ["### Latest 10 trades", ""] + trade_table(rot_trades)[:12] + [""]
    out += ["<details>", f"<summary><b>All {len(rot_trades)} rotation trades</b></summary>", "",
            *trade_table(rot_trades), "", "</details>", "",
            "[Rotation bot journal](crypto/journal-rotation.md)", ""]

    out += ["## 🏦 Buy-and-hold bot", "",
            "Bought equal thirds of BTC, ETH and SOL on day one and never sells.", "",
            "### Holding now", ""] + holdings_table(hold_days[-1], market)
    out += trade_table(hold_trades) + ["", "[Buy-and-hold bot journal](crypto/journal-hold.md)", ""]

    out += ["## Month by month", "", "Each bot's value at the end of each month.", ""]
    out += monthly_table(bots) + [""]
    out += ["## Files", "",
            "- [Every trade, both bots (CSV)](crypto/trades.csv)",
            "- [How these strategies were chosen](crypto/STRATEGIES.md)", ""]
    return "\n".join(out)


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
    market = lab.Market(coins, data=data, start=START)

    bots = {
        "Rotation bot": run_bot("Rotation bot", market,
                                lab.rotation(coins, LOOKBACK, TOP, EVERY, TREND_DAYS),
                                rotation_reason),
        "Buy-and-hold bot": run_bot("Buy-and-hold bot", market,
                                    lab.buy_and_hold(HOLD_COINS), hold_reason),
    }

    os.makedirs(CHARTS, exist_ok=True)
    series = {n: [(d["date"], d["value"]) for d in days] for n, (days, _) in bots.items()}
    with open(os.path.join(CHARTS, "value.svg"), "w") as f:
        f.write(value_chart(series, START_CASH, GO_LIVE, bots["Rotation bot"][1]))
    with open(os.path.join(CHARTS, "rotation-holdings.svg"), "w") as f:
        f.write(holdings_chart(bots["Rotation bot"][0], GO_LIVE))
    with open(os.path.join(CHARTS, "drawdown.svg"), "w") as f:
        f.write(drawdown_chart(series))

    all_trades = sorted((t for _, tr in bots.values() for t in tr), key=lambda t: (t["date"], t["bot"]))
    with open(os.path.join("crypto", "trades.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["bot", "date", "action", "coin", "price", "units", "dollars", "fee",
                    "profit", "type", "reason"])
        for t in all_trades:
            w.writerow([t["bot"], t["date"], t["action"], t["coin"], f"{t['price']:.6g}",
                        f"{t['units']:.8g}", f"{t['dollars']:.2f}", f"{t['fee']:.2f}",
                        "" if t["profit"] is None else f"{t['profit']:.2f}",
                        phase(t["date"]), t["reason"]])
    write_journal(os.path.join("crypto", "journal-rotation.md"), "Rotation bot journal",
                  f"Holds up to {TOP} of the strongest coins by {LOOKBACK}-day gain.",
                  bots["Rotation bot"][1])
    write_journal(os.path.join("crypto", "journal-hold.md"), "Buy-and-hold bot journal",
                  "Bought equal thirds of BTC, ETH and SOL and holds them.",
                  bots["Buy-and-hold bot"][1])

    now = datetime.now(timezone.utc)
    with open(DASHBOARD, "w") as f:
        f.write(build_dashboard(bots, market, now))
    for name, (days, trades) in bots.items():
        print(f"{name}: {money(days[-1]['value'], True)} after {len(trades)} trades")
    print(f"Wrote {DASHBOARD}")


if __name__ == "__main__":
    main()
