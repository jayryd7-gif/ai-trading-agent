"""
weekly_report.py - One page every Sunday covering every agent's week.

Run it from the project folder (with PYTHONPATH set to "."):
    python agents/weekly_report.py              (the week ending today)
    python agents/weekly_report.py 2026-10-25   (the week ending that Sunday)

It is plain code, not AI, so it costs nothing. It reads what the other agents
wrote and adds up the week (Monday to Sunday):
  - futures paper trading: trades, wins, profit, drawdown room
  - TradingView: the strategy's results from your latest exports
  - crypto paper bots: each bot's value at the start and end of the week
  - Alpaca: orders sent
  - market briefs: how often the lean was right
  - CEO check: rules broken this week
  - costs: what the AI agents actually cost this week

It saves reports/weekly/<Sunday's date>-weekly-report.md.
"""

import csv
import glob
import os
import sys
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import main as rules
import tradingview_stats as tv

FOLDER = os.path.join("reports", "weekly")


def read_csv(path):
    try:
        with open(path, newline="") as f:
            return list(csv.DictReader(f))
    except OSError:
        return []


def money(v, cents=False):
    text = f"${abs(v):,.2f}" if cents else f"${abs(v):,.0f}"
    return ("-" if v < 0 else "") + text


def signed(v, cents=False):
    return ("+" if v > 0 else "") + money(v, cents)


def in_week(day_text, monday, sunday):
    return monday.isoformat() <= day_text[:10] <= sunday.isoformat()


def futures_section(monday, sunday):
    rows = read_csv(os.path.join("paper-trading", "trades.csv"))
    week = [r for r in rows if in_week(r["trading_day"], monday, sunday)]
    trades = [r for r in week if r["signal"] == "yes"]
    all_trades = [r for r in rows if r["signal"] == "yes"]
    nets = [float(r["net"]) for r in trades]
    out = ["## Futures paper trading", ""]
    if not week:
        return out + ["No sessions recorded this week.", ""], 0.0
    out += [f"- **This week:** {signed(sum(nets))} after fees, {len(trades)} trades "
            f"({sum(n > 0 for n in nets)} wins, {sum(n < 0 for n in nets)} losses), "
            f"{len(week) - len(trades)} sessions with no trade",
            f"- **Since paper trading began:** {signed(sum(float(r['net']) for r in all_trades))} "
            f"over {len(all_trades)} trades"]
    for name in rules.SESSIONS:
        mine = [float(r["net"]) for r in trades if r["instrument"] == name]
        out.append(f"- {rules.SESSIONS[name]['name']}: {signed(sum(mine))} over {len(mine)} trades")
    if trades:
        out += ["", "| Day | Market | Side | Entry | Result |", "|---|---|---|---|---|"]
        for r in sorted(trades, key=lambda r: r["session_start"]):
            out.append(f"| {r['trading_day']} | {r['instrument']} | {r['direction']} | "
                       f"{r['entry']} at {r['entry_time']} | {signed(float(r['net']))} |")
    return out + [""], sum(nets)


def crypto_section(monday, sunday):
    rows = read_csv(os.path.join("crypto", "paper-values.csv"))
    out = ["## Crypto paper bots", ""]
    if not rows:
        return out + ["No crypto paper values yet.", ""], {}
    bots = [k for k in rows[0] if k != "date"]
    before = [r for r in rows if r["date"] < monday.isoformat()]
    during = [r for r in rows if in_week(r["date"], monday, sunday)]
    if not during:
        return out + ["No crypto values for this week.", ""], {}
    end = during[-1]
    start = before[-1] if before else {b: "1000" for b in bots}   # started this week with $1,000
    out += ["| Bot | Start of week | End of week | Change | Since it started ($1,000) |",
            "|---|---|---|---|---|"]
    changes = {}
    for b in bots:
        s, e = float(start[b]), float(end[b])
        changes[b] = e - s
        out.append(f"| {b} | {money(s, True)} | {money(e, True)} | "
                   f"{signed(e - s, True)} ({(e / s - 1):+.1%}) | {signed(e - 1000, True)} |")
    trades = [r for r in read_csv(os.path.join("crypto", "trades.csv"))
              if r.get("account") == "paper" and in_week(r["date"], monday, sunday)]
    if trades:
        out += ["", "Trades this week:", "", "| Day | Bot | | Coin | Amount | Profit / loss |",
                "|---|---|---|---|---|---|"]
        for r in trades:
            icon = "🟢 Buy" if r["action"] == "Buy" else "🔴 Sell"
            pl = signed(float(r["profit"]), True) if r["profit"] else ""
            out.append(f"| {r['date']} | {r['bot']} | {icon} | {r['coin']} | "
                       f"{money(float(r['dollars']), True)} | {pl} |")
    orders = [o for o in read_csv(os.path.join("crypto", "alpaca-orders.csv"))
              if in_week(o["time_utc"], monday, sunday)]
    out += ["", f"**Alpaca copy:** {len(orders)} order(s) this week"
            + (": " + ", ".join(f"{o['side']} {o['coin']}" for o in orders) if orders else "."), ""]
    return out, changes


def tradingview_section():
    out = ["## TradingView strategy", ""]
    exports = tv.latest_exports()
    if not exports:
        return out + ["No TradingView exports yet.", ""]
    out += ["| Market | Export date | Forward test (since paper start) | Whole export |",
            "|---|---|---|---|"]
    for symbol, label in tv.MARKETS.items():
        path = exports.get(symbol)
        if not path:
            continue
        trades = tv.positions(path)
        fwd = tv.stats([t for t in trades if t["entry_time"] >= tv.PAPER_START])
        whole = tv.stats(trades)
        export_date = os.path.basename(path).split("_")[-2] if "_" in path else "?"
        out.append(f"| {label} | {export_date} | {fwd['trades']} trades, {signed(fwd['net'])} | "
                   f"{whole['trades']} trades, {signed(whole['net'])}, {whole['win_rate']} wins |")
    return out + ["", "Export the List of trades from each chart and say \"update TradingView\" "
                  "to refresh these numbers.", ""]


def briefs_section(monday, sunday):
    rows = [r for r in read_csv(os.path.join("reports", "scores.csv"))
            if in_week(r["session_start"], monday, sunday)]
    out = ["## Market briefs (Nasdaq and gold)", ""]
    if not rows:
        return out + ["No briefs scored this week.", ""]
    calls = [r for r in rows if r["bias"] in ("Bullish", "Bearish")]
    right = sum(r["result"] == "Right" for r in calls)
    return out + [f"- {len(rows)} briefs scored; {len(calls)} gave a direction, "
                  f"{right} of those were right.",
                  f"- {len(rows) - len(calls)} were Neutral.", ""]


def ceo_section(monday, sunday):
    rows = [r for r in read_csv(os.path.join("reports", "ceo", "history.csv"))
            if in_week(r["time_ny"], monday, sunday)]
    out = ["## CEO check", ""]
    if not rows:
        return out + ["The CEO agent did not run this week.", ""]
    worst = max(int(r["broken"]) for r in rows)
    warnings = max(int(r["warnings"]) for r in rows)
    verdict = ("❌ Rules were broken this week" if worst else
               "⚠️ No broken rules, but there were warnings" if warnings else "✅ No rules broken all week")
    return out + [f"**{verdict}.** {len(rows)} checks ran. "
                  "[Latest CEO check](../ceo/latest.md)", ""]


def costs_section(monday, sunday):
    rows = [x for p in glob.glob(os.path.join("reports", "costs", "*.csv")) for x in read_csv(p)
            if in_week(x["time_utc"], monday, sunday)]
    out = ["## AI costs this week", ""]
    if not rows:
        return out + ["No AI runs logged this week.", ""], 0.0
    by_agent = {}
    for x in rows:
        a = by_agent.setdefault(x["agent"], [0, 0.0])
        a[0] += 1
        a[1] += float(x["cost_usd"])
    total = sum(v[1] for v in by_agent.values())
    out += ["| Agent | Runs | Cost |", "|---|---|---|"]
    for agent, (n, c) in sorted(by_agent.items(), key=lambda kv: -kv[1][1]):
        out.append(f"| {agent} | {n} | {money(c, True)} |")
    out += [f"| **Total** | {len(rows)} | **{money(total, True)}** |", "",
            f"At this pace: about {money(total / 7 * 30)} a month.", ""]
    return out, total


def build(sunday):
    monday = sunday - timedelta(days=6)
    futures, fut_total = futures_section(monday, sunday)
    crypto, crypto_changes = crypto_section(monday, sunday)
    costs, cost_total = costs_section(monday, sunday)
    headline = [f"- **Futures paper:** {signed(fut_total)} this week"]
    headline += [f"- **{b}:** {signed(v, True)} this week" for b, v in crypto_changes.items()]
    headline.append(f"- **AI costs:** {money(cost_total, True)} this week")
    out = [f"# 📅 Weekly report: {monday:%b %d} – {sunday:%b %d, %Y}", "",
           "*Written automatically every Sunday from what the agents recorded. "
           "Paper trading only: no real money.*", "",
           "## The week in one look", ""] + headline + [""]
    out += futures + tradingview_section() + crypto + briefs_section(monday, sunday)
    out += ceo_section(monday, sunday) + costs
    out += ["[Main dashboard](../../DASHBOARD.md) · [Crypto dashboard](../../CRYPTO-DASHBOARD.md)", ""]
    return "\n".join(out)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv:
        sunday = date.fromisoformat(argv[0])
    else:
        today = datetime.now(ZoneInfo("America/New_York")).date()
        sunday = today + timedelta(days=(6 - today.weekday()))   # this week's Sunday
    os.makedirs(FOLDER, exist_ok=True)
    path = os.path.join(FOLDER, f"{sunday}-weekly-report.md")
    with open(path, "w") as f:
        f.write(build(sunday))
    print(f"Saved {path}")
    return path


if __name__ == "__main__":
    main()
