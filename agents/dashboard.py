"""
dashboard.py - Builds DASHBOARD.md, a one-page view of your agent ecosystem.

This is plain code, not an AI agent, so it costs nothing in API credits.
It reads the files the other agents leave in reports/ and writes a page that
GitHub displays nicely, even in a private repo.

It shows: your reminders, how each agent is doing, any problems in the last
runs, the paper trade journal, the latest briefs (readable right on the page, in
expandable sections), the latest lean for each market, scorecard summary,
charts, recent results, and the agents still to be built.
"""

import glob
import json
import os
import re
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

# The project folder, for main.py and the paper trader's account rules.
sys.path.insert(1, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from charts import make_charts
from scorer import ENOUGH_CALLS, _rate, read_csv
from market_data import INSTRUMENTS
from tradingview_stats import dashboard_section as tradingview_section

# ---------------- SETTINGS ----------------
REPORT_FOLDER = "reports"
DASHBOARD = "DASHBOARD.md"
JOURNAL = "trade-journal.md"
NO_TRADE_JOURNAL = "no-trade-journal.md"
PAPER_SUMMARY = os.path.join("paper-trading", "summary.md")
PAPER_TRADES = os.path.join("paper-trading", "trades.csv")
TV_LINKS = {"nasdaq": "https://www.tradingview.com/chart/?symbol=CME_MINI%3AMNQ1%21&interval=5",
            "gold": "https://www.tradingview.com/chart/?symbol=COMEX_MINI%3AMGC1%21&interval=5"}
REMINDERS = "REMINDERS.md"
GOOD_WITHIN_HOURS = 72     # green if an agent ran within this long (covers weekends)
LATE_WITHIN_HOURS = 168    # yellow up to this long, red after that
# ------------------------------------------

LEAN_ICON = {"Bullish": "▲", "Bearish": "▼", "Neutral": "◆", "Unknown": "?"}

PLANNED = [
    ("Product selling agent (separate repo)", "Main Agent from your Obsidian notes: what to sell, sourcing, advertising"),
    ("Live demo trading", "Sends the TradingView strategy's orders to a Tradovate demo or prop challenge account, behind a risk gatekeeper"),
]


def hours_between(then, now):
    return (now - then).total_seconds() / 3600


def age_text(then, now):
    hours = hours_between(then, now)
    if hours < 1:
        return "under an hour ago"
    if hours < 48:
        return f"{hours:.0f} hours ago"
    return f"{hours / 24:.0f} days ago"


def status_icon(then, now):
    if then is None:
        return "⚪"
    hours = hours_between(then, now)
    if hours <= GOOD_WITHIN_HOURS:
        return "🟢"
    if hours <= LATE_WITHIN_HOURS:
        return "🟡"
    return "🔴"


def parse_time(date, time):
    try:
        return datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
    except (ValueError, TypeError):
        return None


def event_risk(brief_path):
    """Find 'Event risk: High/Medium/Low' in a brief file, or 'n/a'."""
    try:
        text = open(brief_path).read()
    except OSError:
        return "n/a"
    match = re.search(r"Event risk.{0,40}?\b(Low|Medium|High)\b", text, re.S)
    return match.group(1) if match else "n/a"


def paper_updated():
    """Read the 'Updated YYYY-MM-DD HH:MM' stamp from the paper trading summary."""
    try:
        text = open(PAPER_SUMMARY).read()
    except OSError:
        return None
    match = re.search(r"Updated (\d{4}-\d{2}-\d{2}) (\d{2}:\d{2})", text)
    return parse_time(match.group(1), match.group(2)) if match else None


def paper_section():
    """The paper trading summary split into (at a glance, the rest)."""
    try:
        text = open(PAPER_SUMMARY).read()
    except OSError:
        return None, None
    parts = re.split(r"^## ", text, flags=re.M)
    glance = next((p for p in parts if p.startswith("At a glance")), None)
    rest = "\n".join("## " + p for p in parts if p.startswith(("By market", "Challenge", "Daily")))
    if glance is None:   # nothing recorded yet
        return read_body(PAPER_SUMMARY), None
    return glance.split("\n", 1)[1].strip(), demote_headings(rest)


def _money(value):
    return f"-${-value:,.0f}" if value < 0 else f"${value:,.0f}"


def scoreboard_section(since="2026-11-15"):
    """Profit so far, like the tables in chat: each TradingView script since Nov 15
    (from the latest read in tradingview/script-trades/) and MAMBA's permanent log."""
    out = []
    files = sorted(glob.glob(os.path.join("tradingview", "script-trades", "*.json")))
    if files:
        data = json.load(open(files[-1]))
        out += [f"### 🏁 Scoreboard: your TradingView scripts since {since[5:7]}/{since[8:]} "
                f"(read {os.path.basename(files[-1])[:10]})", "",
                "| Market | Script | Trades | Won | Profit factor | Total |", "|---|---|---|---|---|---|"]
        for key, market in (("MNQ", "Nasdaq"), ("MGC", "Gold")):
            for name, short in (("MAMBA NQ - Breakout Scalp (50K tracking)", "MAMBA"),
                                ("OPENING RANGE - Session Breakout (tracking)", "Opening Range"),
                                ("Session Breakout - Tradeify 50K", "Session Breakout 50K")):
                nets = [t[4] for t in data.get(key, {}).get(name, {}).get("trades", []) if t[0] >= since]
                if not nets:
                    continue
                won = sum(n > 0 for n in nets)
                gw, gl = sum(n for n in nets if n > 0), -sum(n for n in nets if n < 0)
                pf = f"{gw / gl:.2f}" if gl else "no losses"
                out.append(f"| {market} | {short} | {len(nets)} | {won} ({won / len(nets):.0%}) | {pf} | "
                           f"**{_money(sum(nets))}** |")
        out += ["", "*Ask Claude to refresh from TradingView.*", ""]
    try:
        import mamba_log
        lines = mamba_log.summary(mamba_log.read_rows())
    except Exception:
        lines = []
    if lines:
        out += ["### 🐍 MAMBA, every trade kept forever (since Sep 20, updates by itself)", "",
                "| Market | Trades | Won | Profit factor | Total |", "|---|---|---|---|---|"] + lines + [
                "", "[Every MAMBA trade](paper-trading/mamba.csv) · Yahoo prices, can differ a little "
                "from TradingView", ""]
    return out


def paper_journal_section(how_many=15):
    """Every recent paper session as one table row: entry, each sale, exit,
    result, what could have gone better, and links to the chart and TradingView."""
    rows = read_csv(PAPER_TRADES)
    out = ["## 📒 Trade journal (paper)", "",
           "Newest first. Times are New York time. Each sale shows contracts @ price, time. "
           "The 📈 link opens a chart of the trade; TV opens the same market on TradingView "
           "(add [the strategy](tradingview/breakout_strategy.pine) to see each trade marked).", "",
           "| Date | Market | Side | Lots | Entry | Target 1 | Target 2 | Target 3 / out | "
           "Result | What could have gone better | See it |",
           "|---|---|---|---|---|---|---|---|---|---|---|"]
    try:
        open_now = json.load(open(os.path.join("paper-trading", "open-trades.json")))
    except (OSError, ValueError):
        open_now = {}
    live = []
    for t in open_now.values():
        sold = ", ".join(f"{f['contracts']} @ {f['price']} ({f['time']})" for f in t["sold_so_far"])
        live.append(f"- 🟢 **Open now: {'Nasdaq' if t['instrument'] == 'nasdaq' else 'Gold'} "
                    f"{t['direction']} {t['contracts']} contracts** at {t['entry']} "
                    f"({t['entry_time']}), stop {t['stop']}. Sold so far: {sold or 'nothing yet'}.")
    try:
        import main as rules
        from paper_trader import account_from
        acct = account_from(rows)
        from paper_trader import opening_range_compare, read_opening_range
        line = opening_range_compare(rows, read_opening_range())
        if line:
            live.append(f"- 📐 {line} [Details](paper-trading/summary.md)")
        import mamba_log
        mrows = mamba_log.read_rows()
        if mrows:
            mnet = sum(float(r["net"]) for r in mrows)
            mwon = sum(float(r["net"]) > 0 for r in mrows)
            last = mrows[-1]
            live.append(f"- 🐍 **MAMBA (tracking, kept forever): {_money(mnet)}** over {len(mrows)} "
                        f"trades since {mrows[0]['day']}, {mwon} won. Last: {last['day']} "
                        f"{last['market']} {last['direction']} {_money(float(last['net']))}. "
                        "[Every trade](paper-trading/mamba.csv)")
        if hasattr(acct, "attempts"):            # the Tradeify practice account
            from tradeify import RULES as T, floor, payout_status
            a = acct.a
            cushion = a["balance"] + acct.day_pnl - floor(a)
            today = (f"today {_money(acct.day_pnl)}, {_money(T['daily_loss_limit'] + acct.day_pnl)} "
                     f"left before the daily loss limit")
            if a["phase"] == "Evaluation":
                goal = f"{_money(T['start'] + T['target'] - a['balance'] - acct.day_pnl)} to pass"
            else:
                goal = "payout: " + payout_status(a)[1]
            live.insert(0, f"- **Tradeify 50K {a['phase'].lower()}: balance "
                           f"{_money(a['balance'] + acct.day_pnl)}**, {_money(cushion)} above the "
                           f"drawdown floor, {goal}; {today}. "
                           "[Details](paper-trading/summary.md)")
        else:
            now = datetime.now(ZoneInfo("America/New_York")).replace(tzinfo=None)
            if acct.stopped_on:
                state = f"⛔ stopped: the max drawdown was hit on {acct.stopped_on}"
            elif acct.paused_until and now < acct.paused_until:
                state = f"⏸️ paused until {acct.paused_until:%a %b %d %H:%M}, then small size"
            elif acct.room() < rules.NEAR_LIMIT:
                state = "🟡 small size (1 contract per target)"
            else:
                state = "🟢 normal size"
            live.insert(0, f"- **Room before the ${rules.MAX_DRAWDOWN:,} max drawdown: "
                           f"${acct.room():,.0f}** · {state}.")
    except Exception as error:   # the dashboard should never fail over this line
        print(f"Could not work out the account state: {error}")
    if live:
        out[2:2] = live + [""]
    if not rows:
        return out[:2] + live + ["", "No sessions recorded yet.", ""]
    for r in sorted(rows, key=lambda r: r["session_start"], reverse=True)[:how_many]:
        market = "Nasdaq" if r["instrument"] == "nasdaq" else "Gold"
        if r["signal"] != "yes":
            why = {"stopped": "stopped by the max drawdown",
                   "paused": "paused near the max drawdown",
                   "skipped": "skipped: risk too big",
                   "day_stopped": "skipped: daily loss limit",
                   "day_done": "skipped: daily profit cap"}.get(r["signal"], "no breakout, no trade")
            out.append(f"| {r['trading_day']} | {market} | – | 0 | {why} | | | | $0 | "
                       f"{r['events']} | [TV]({TV_LINKS[r['instrument']]}) |")
            continue
        try:
            fills = json.loads(r.get("fills") or "[]")
        except ValueError:
            fills = []
        cells = []
        for f in fills:
            label = "" if f["what"].startswith("Target") else f"{f['what'].lower()}: "
            cells.append(f"{label}{f['contracts']} @ {f['price']}, {f['time']} ({_money(f['profit'])})")
        targets = [c for c, f in zip(cells, fills) if f["what"].startswith("Target")]
        others = [c for c, f in zip(cells, fills) if not f["what"].startswith("Target")]
        cols = [targets[0] if targets else "–", targets[1] if len(targets) > 1 else "–",
                "<br>".join(targets[2:] + others) or "–"]
        lessons = "<br>".join("• " + t for t in (r.get("lessons") or "").split(" | ")
                              if t and not t.startswith("Biggest move"))
        chart = f"[📈 chart]({r['chart']}) · " if r.get("chart") else ""
        icon = "✅" if float(r["net"]) > 0 else "❌"
        out.append(f"| {r['trading_day']} | {market} | {r['direction']} | {r['contracts']} | "
                   f"{r['entry']} @ {r['entry_time']}<br>stop {r['stop']} | "
                   f"{' | '.join(cols)} | {icon} **{_money(float(r['net']))}**<br>"
                   f"out {r['exit_time']} | {lessons or '–'} | {chart}"
                   f"[TV]({TV_LINKS[r['instrument']]}) |")
    latest = next((r for r in sorted(rows, key=lambda r: r["session_start"], reverse=True)
                   if r.get("chart")), None)
    out.append("")
    if latest:
        out += [f"**Latest trade:**", "", f"![Latest paper trade]({latest['chart']})", ""]
    out += ["[Full journal with every fill](paper-trading/paper-journal.md)", ""]
    return out


def scorecard_updated():
    """Read the 'Updated YYYY-MM-DD HH:MM' stamp from the scorecard."""
    path = os.path.join(REPORT_FOLDER, "scorecard.md")
    try:
        text = open(path).read()
    except OSError:
        return None
    match = re.search(r"Updated (\d{4}-\d{2}-\d{2}) (\d{2}:\d{2})", text)
    return parse_time(match.group(1), match.group(2)) if match else None


def latest_news(subfolder="news", kind="world"):
    """Newest research brief in reports/<subfolder>/ named <date>-<kind>-brief.md:
    (date, path, written time, event risk) or None."""
    folder = os.path.join(REPORT_FOLDER, subfolder)
    try:
        files = os.listdir(folder)
    except OSError:
        return None
    pattern = re.compile(rf"^(\d{{4}}-\d{{2}}-\d{{2}})-{kind}-brief\.md$")
    found = sorted(f for f in files if pattern.match(f))
    if not found:
        return None
    newest = found[-1]
    written, risk = None, "n/a"
    try:
        text = open(os.path.join(folder, newest)).read()
        match = re.search(r"Written (\d{4}-\d{2}-\d{2}) (\d{2}:\d{2})", text)
        if match:
            written = parse_time(match.group(1), match.group(2))
        match = re.search(r"Event risk today.{0,60}?\b(Low|Medium|High)\b", text, re.S)
        if match:
            risk = match.group(1)
    except OSError:
        pass
    return pattern.match(newest).group(1), f"{REPORT_FOLDER}/{subfolder}/{newest}", written, risk


def demote_headings(text):
    """Push headings down two levels so a brief fits under a dashboard section."""
    return re.sub(r"^(#{1,4}) ", lambda m: "#" * (len(m.group(1)) + 2) + " ", text, flags=re.M)


def read_body(path, summary_only=False, drop_section=None):
    """A report file without its title and disclaimer lines, ready to embed.

    summary_only keeps just the part before the first '---' line.
    drop_section removes one '## <name>' section (like a block of raw numbers).
    """
    try:
        text = open(path).read()
    except OSError:
        return None
    lines = text.strip().splitlines()
    if lines and lines[0].startswith("# "):
        lines = lines[1:]
    while lines and (not lines[0].strip() or lines[0].startswith("*")):
        lines = lines[1:]   # blank lines and the italic disclaimer
    text = "\n".join(lines)
    if summary_only:
        text = text.split("\n---\n")[0]
    if drop_section:
        text = re.sub(rf"^## {re.escape(drop_section)}\n.*?(?=^#{{1,2}} )", "",
                      text, count=1, flags=re.M | re.S)
    return demote_headings(text.strip())


def details(title, body):
    """A section that is closed until you click it (GitHub shows these)."""
    if not body:
        return []
    return ["<details>", f"<summary><b>{title}</b></summary>", "", body, "", "</details>", ""]


def journal_entries(path, heading, how_many):
    """The newest entries in a journal, newest first."""
    try:
        text = open(path).read()
    except OSError:
        return []
    starts = [m.start() for m in re.finditer(rf"^### {heading}", text, re.M)]
    blocks = [text[a:b].strip().rstrip("-").strip()
              for a, b in zip(starts, starts[1:] + [len(text)])]
    if heading == "Trade #":
        blocks = [b for b in blocks if not b.startswith("### Trade #__")]   # template

    def entry_date(block):
        found = re.search(r"\d{4}-\d{2}-\d{2}", block.splitlines()[0])
        return found.group(0) if found else ""
    return sorted(blocks, key=entry_date, reverse=True)[:how_many]


def run_problems():
    """Research agents whose last run log shows a failure."""
    problems = []
    for folder, label in (("news", "World news brief"), ("crypto", "Crypto brief"),
                          ("stocks", "Stock brief")):
        path = os.path.join(REPORT_FOLDER, folder, "last-run-log.txt")
        try:
            text = open(path).read()
        except OSError:
            continue
        if "Traceback" in text or "Saved " not in text:
            last = [line for line in text.strip().splitlines() if line.strip()][-1:] or ["(empty log)"]
            problems.append(f"- ❌ **{label}** failed on its last run: `{last[0][:200]}` "
                            f"([full log]({path}))")
    return problems


def open_reminders():
    """Reminders written as '- [ ] text' in REMINDERS.md (done ones are '- [x]')."""
    try:
        text = open(REMINDERS).read()
    except OSError:
        return []
    return [m.group(1).strip() for m in re.finditer(r"^\s*- \[ \]\s+(.+)$", text, re.M)]


def _wheel_block(folder, heading, empty):
    summary = os.path.join(folder, "summary.md")
    out = [heading, ""]
    if not os.path.exists(summary):
        return out + [empty, ""]
    text = open(summary).read()
    table = re.search(r"^\| \| \|\n\|---\|---\|\n(?:\|.*\n)+", text, re.M)
    holdings = re.search(r"^\| Stock \| Holding.*\n(?:\|.*\n)+", text, re.M)
    updated = re.search(r"^Updated .*$", text, re.M)
    out += [updated.group(0) if updated else "", ""]
    if table:
        out += [table.group(0)]
    out += [f"![Account profit / loss]({folder}/value.svg)", "",
            f"![Holdings]({folder}/holdings.svg)", ""]
    if holdings:
        out += [holdings.group(0)]
    out += [f"[Account]({folder}/summary.md) · [Every move]({folder}/journal.md)", ""]
    return out


def _wheel_pct(folder):
    try:
        st = json.load(open(os.path.join(folder, "state.json")))
        last = st["history"][-1]["equity_usd"]
        return round((last / st["start_usd"] - 1) * 100, 1) + 0.0, st["wins"], st["losses"], len(st["positions"]), st["started"]
    except (OSError, ValueError, KeyError, IndexError):
        return None


def wheel_section():
    """Both options wheel paper accounts: a comparison line, then each one's charts and holdings."""
    out = ["## 🎡 Options wheel (paper)", "",
           "Two paper accounts run side by side: **ours** ($10K CAD, cheaper stocks) and a "
           "**Ryan-style** copy (Options With Ryan's rules, pretend $200K USD on his stocks). "
           "Compare them by **%**, since the sizes differ. "
           "[Rules and research](experiments/wheel-strategy-research.md)", ""]
    if os.path.exists(os.path.join("reports", "charts", "options-accounts-live.svg")):
        out += ["![All three options accounts, live](reports/charts/options-accounts-live.svg)", "",
                "*Live paper results, updated every weekday after the 2:37 PM run.*", ""]
    if os.path.exists(os.path.join("reports", "charts", "options-accounts-year.svg")):
        out += ["<details>", "<summary><b>Past-year backtest of all three accounts</b></summary>", "",
                "![All three options accounts over the past year](reports/charts/options-accounts-year.svg)", "",
                "*Backtest with estimated option prices. Rebuild it with "
                "`PYTHONPATH=agents:experiments python3 experiments/options_accounts_chart.py`.*", "", "</details>", ""]
    rows = [("Ours ($10K CAD)", "paper-trading/wheel"), ("Ryan-style ($200K USD)", "paper-trading/wheel-ryan")]
    stats = [(name, _wheel_pct(folder)) for name, folder in rows]
    if any(st for _, st in stats):
        out += ["| Account | Up / down % | Wins / losses | Open | Since |", "|---|---|---|---|---|"]
        for name, st in stats:
            out.append(f"| {name} | " + (f"**{st[0]:+.1f}%** | {st[1]} / {st[2]} | {st[3]} | {st[4]} |"
                                        if st else "not started | | | |"))
        out.append("")
    out += _wheel_block("paper-trading/wheel", "### Ours ($10K CAD)",
                        "Starts trading on the first weekday run (2:37 PM New York).")
    out += _wheel_block("paper-trading/wheel-ryan", "### Ryan-style ($200K USD, his stocks)",
                        "Starts trading on the first weekday run (2:37 PM New York).")
    out += condor_section()
    return out


def condor_section():
    """The $10K CAD iron condor income account: headline, charts, open condors, cash flow by month."""
    folder = "paper-trading/condor"
    summary = os.path.join(folder, "summary.md")
    out = ["## 💰 Iron condor income account (paper, $10K CAD)", "",
           "A separate cash-flow test: SPY/QQQ iron condors, about 30 days out. "
           "Backtest: about $100-250 CAD a month, with drops of 16-30% along the way.", ""]
    if not os.path.exists(summary):
        return out + ["Starts trading on the first weekday run (2:37 PM New York).", ""]
    text = open(summary).read()
    for pattern in (r"^Updated .*$", r"^\| \| \|\n\|---\|---\|\n(?:\|.*\n)+"):
        m = re.search(pattern, text, re.M)
        if m:
            out += [m.group(0), ""]
    out += [f"![Condor account profit / loss]({folder}/value.svg)", "",
            f"![Open condors]({folder}/holdings.svg)", ""]
    for pattern in (r"^\| Underlying \|.*\n(?:\|.*\n)+", r"^\| Month \| Profit / loss \|\n(?:\|.*\n)+"):
        m = re.search(pattern, text, re.M)
        if m:
            out += [m.group(0)]
    out += [f"[Account]({folder}/summary.md) · [Every move]({folder}/journal.md)", ""]
    return out


def build_dashboard(now):
    briefs = read_csv(os.path.join(REPORT_FOLDER, "bias-log.csv"))
    scores = read_csv(os.path.join(REPORT_FOLDER, "scores.csv"))

    out = ["# Agent dashboard", "",
           f"Last updated {now:%Y-%m-%d %H:%M} New York time. "
           "Everything here is written by software and AI agents. "
           "It can be wrong, so check anything you plan to act on.", "",
           "**[🪙 Open the Crypto Dashboard →](CRYPTO-DASHBOARD.md)** · "
           "**[𝕏 Open the X Brief Dashboard →](X-DASHBOARD.md)**", ""]

    # ---- Reminders ----
    reminders = open_reminders()
    if reminders:
        out += ["## Reminders", ""]
        out += [f"- ⏰ {text}" for text in reminders]
        out += ["", f"[Edit reminders]({REMINDERS})", ""]

    # ---- Agent status ----
    out += ["## Agent status", "",
            "| | Agent | What it does | Last ran | Runs |",
            "|---|---|---|---|---|"]
    latest = {}
    for name, config in INSTRUMENTS.items():
        rows = [r for r in briefs if r.get("instrument") == name]
        last = rows[-1] if rows else None
        when = parse_time(last["date"], last["time_ny"]) if last else None
        latest[name] = last
        runs = ("weekdays about 7-8 AM New York time" if name == "nasdaq"
                else "Sun-Thu evenings about 6-7 PM New York time")
        out.append(f"| {status_icon(when, now)} | Market brief: {name} | "
                   f"Writes the brief before the {config['label']} session | "
                   f"{age_text(when, now) if when else 'never'} | {runs} |")
    news = latest_news()
    news_when = news[2] if news else None
    out.append(f"| {status_icon(news_when, now)} | World news brief | Overnight news and "
               f"today's events: politics, economy, war, trade | "
               f"{age_text(news_when, now) if news_when else 'never'} | "
               f"daily about 5-6 AM New York time |")
    research = {"crypto": latest_news("crypto", "crypto"),
                "stocks": latest_news("stocks", "stock")}
    for label, key, purpose, runs in (
            ("Crypto research brief", "crypto",
             "Pumping coins, whales, government and adoption news", "daily about 5:30-6:30 AM"),
            ("Stock research brief", "stocks",
             "Movers, AI, nuclear, minerals, earnings dates and estimates",
             "Mon, Wed, Fri about 6-7 AM")):
        when = research[key][2] if research[key] else None
        out.append(f"| {status_icon(when, now)} | {label} | {purpose} | "
                   f"{age_text(when, now) if when else 'never'} | {runs} New York time |")
    paper = paper_updated()
    out.append(f"| {status_icon(paper, now)} | Paper trader | Paper trades every session "
               f"with your rules and runs a practice prop challenge | "
               f"{age_text(paper, now) if paper else 'never'} | after each session ends |")
    updated = scorecard_updated()
    out.append(f"| {status_icon(updated, now)} | Scorer | Checks each lean against "
               f"what price did | {age_text(updated, now) if updated else 'never'} | "
               f"after each session ends |")
    out += ["", "🟢 ran recently  🟡 a bit late  🔴 check it  ⚪ never ran", ""]

    # ---- Problems ----
    problems = run_problems()
    if problems:
        out += ["## ⚠️ Problems", ""] + problems + [
            "", "Open the repo's Actions tab on GitHub for more detail.", ""]

    # ---- The paper trade journal, first thing after status ----
    out += paper_journal_section()

    # ---- CEO check and weekly report ----
    try:
        ceo = open(os.path.join(REPORT_FOLDER, "ceo", "latest.md")).read()
        verdict = re.search(r"^\*\*(.+?)\*\*", ceo, re.M)
        out += ["## 👔 CEO check", "",
                f"**{verdict.group(1) if verdict else 'See the latest check'}** "
                f"([read the full check]({REPORT_FOLDER}/ceo/latest.md))", ""]
        out += details("What the CEO checked", read_body(os.path.join(REPORT_FOLDER, "ceo", "latest.md")))
    except OSError:
        out += ["## 👔 CEO check", "", "The CEO agent has not run yet.", ""]
    weeklies = sorted(glob.glob(os.path.join(REPORT_FOLDER, "weekly", "*-weekly-report.md")))
    if weeklies:
        out += ["## 📅 Weekly report", ""]
        out += details(f"Week ending {os.path.basename(weeklies[-1])[:10]}", read_body(weeklies[-1]))
        out += [f"[All weekly reports]({REPORT_FOLDER}/weekly/)", ""]

    # ---- Paper trading ----
    glance, rest = paper_section()
    out += ["## Paper trading", ""]
    out += scoreboard_section()
    if glance:
        out += [glance, ""]
        for chart, label in (("nasdaq-scripts-live.svg", "Nasdaq since Nov 15"), ("gold-scripts-live.svg", "Gold since Nov 15")):
            if os.path.exists(os.path.join("reports", "charts", chart)):
                out += [f"![{label}: MAMBA, Opening Range, Session Breakout](reports/charts/{chart})", ""]
        out += ["*Your three TradingView scripts on Nasdaq and gold from Nov 15 on, read from TradingView's "
                "Strategy Tester (saved in `tradingview/script-trades/`). Ask Claude to refresh them.*", ""]
        backtests = [c for c in ("nasdaq-scripts.svg", "gold-scripts.svg")
                     if os.path.exists(os.path.join("reports", "charts", c))]
        if backtests:
            out += ["**Results so far (Sep 20 - Nov 15):**", ""]
            out += [f"![{c}](reports/charts/{c})\n" for c in backtests]
        out += details("Challenge simulation, results by market, and daily results", rest)
        out += ["[Paper trading journal](paper-trading/paper-journal.md) · "
                "[TradingView strategy](tradingview/breakout_strategy.pine)", ""]
    else:
        out += ["No paper trades yet.", ""]

    # ---- Options wheel (paper) ----
    out += wheel_section()

    # ---- TradingView ----
    out += tradingview_section()

    # ---- Today's briefs, readable right here ----
    out += ["## Latest briefs", "",
            "Click a brief to read it here. The summary is at the top of each.", ""]
    for title, brief, folder in (("🌍 World news", news, "news"),
                                 ("🪙 Crypto", research["crypto"], "crypto"),
                                 ("📈 Stocks", research["stocks"], "stocks")):
        if not brief:
            out += [f"**{title}:** none yet", ""]
            continue
        risk = f", event risk {brief[3]}" if brief[3] != "n/a" else ""
        out += details(f"{title} brief, {brief[0]}{risk}",
                       read_body(brief[1], summary_only=True)
                       + f"\n\n[Read the full brief with all the details]({brief[1]}) · "
                       f"[All {title.split()[-1].lower()} briefs]({REPORT_FOLDER}/{folder}/)")
    for name in INSTRUMENTS:
        row = latest.get(name)
        path = f"{REPORT_FOLDER}/{row['date']}-{name}-brief.md" if row else None
        if path and os.path.exists(path):
            out += details(f"📊 {INSTRUMENTS[name]['name']} market brief, {row['date']}",
                           read_body(path, drop_section="Price data used")
                           + f"\n\n[Open the file]({path})")

    # ---- Latest lean ----
    out += ["## Latest lean for each market", "",
            "| Market | Brief written | Lean | Confidence | Event risk | Price then | Full brief |",
            "|---|---|---|---|---|---|---|"]
    for name in INSTRUMENTS:
        row = latest.get(name)
        if not row:
            out.append(f"| {name} | no brief yet | | | | | |")
            continue
        brief_file = f"{REPORT_FOLDER}/{row['date']}-{name}-brief.md"
        link = f"[read it]({brief_file})" if os.path.exists(brief_file) else "n/a"
        icon = LEAN_ICON.get(row["bias"], "?")
        out.append(f"| {name} | {row['date']} {row['time_ny']} | {icon} {row['bias']} | "
                   f"{row['confidence']} | {event_risk(brief_file)} | "
                   f"{row['price_at_brief'] or 'n/a'} | {link} |")
    out += ["", "A lean is a probability-based view, not a prediction. ▲ Bullish  ▼ Bearish  ◆ Neutral", ""]

    # ---- Scorecard ----
    directional = [r for r in scores if r["bias"] in ("Bullish", "Bearish")]
    right, wrong, flat, hit = _rate(directional)
    out += ["## Scorecard", "",
            f"- Briefs scored: **{len(scores)}** "
            f"(Bullish or Bearish calls: {len(directional)})",
            f"- Right: {right}, Wrong: {wrong}, Session ended flat: {flat}",
            f"- Hit rate when the session was decisive: **{hit}**"]
    decisive = [r for r in scores if r["outcome"] in ("Up", "Down")]
    if decisive:
        up = sum(1 for r in decisive if r["outcome"] == "Up")
        out.append(f"- For comparison, price went up in "
                   f"{up / len(decisive) * 100:.0f}% of decisive sessions")
    if len(directional) < ENOUGH_CALLS:
        out.append(f"- ⚠️ Only {len(directional)} directional calls so far. "
                   f"Treat the numbers as noise until there are at least {ENOUGH_CALLS}.")
    out += ["", "By confidence:", "",
            "| Confidence | Right | Wrong | Flat | Hit rate |", "|---|---|---|---|---|"]
    for level in ("High", "Medium", "Low"):
        r, w, f, h = _rate([x for x in directional if x["confidence"] == level])
        out.append(f"| {level} | {r} | {w} | {f} | {h} |")
    out += ["", f"[Full scorecard]({REPORT_FOLDER}/scorecard.md)", ""]

    # ---- Charts ----
    out += ["## Charts", ""]
    for alt, path in make_charts(scores):
        out += [f"![{alt}]({path})", ""]

    # ---- Recent results ----
    out += ["## Recent results", "",
            "| Brief | Market | Lean | Confidence | Session moved | Result |",
            "|---|---|---|---|---|---|"]
    if scores:
        for r in scores[-10:][::-1]:
            out.append(f"| {r['date']} | {r['instrument']} | "
                       f"{LEAN_ICON.get(r['bias'], '?')} {r['bias']} | {r['confidence']} | "
                       f"{r['outcome']} ({r['move_pct']}%) | {r['result']} |")
    else:
        out.append("| none scored yet | | | | | |")
    out.append("")

    # ---- Your journals ----
    try:
        trades = len(re.findall(r"^### Trade #\d+", open(JOURNAL).read(), re.M))
    except OSError:
        trades = 0
    try:
        skipped = len(re.findall(r"^### No-trade session \|", open(NO_TRADE_JOURNAL).read(), re.M))
    except OSError:
        skipped = 0
    out += ["## Your journals", "",
            f"- Trades logged: **{trades}**. [Open the trade journal]({JOURNAL})",
            f"- No-trade sessions explained: **{skipped}**. "
            f"[Open the no-trade journal]({NO_TRADE_JOURNAL})", ""]
    trades_text = "\n\n".join(journal_entries(JOURNAL, "Trade #", 3))
    out += details("Your latest trades", demote_headings(trades_text))
    skipped_text = "\n\n".join(journal_entries(NO_TRADE_JOURNAL, "No-trade session", 3))
    out += details("Latest no-trade sessions", demote_headings(skipped_text))

    # ---- Planned ----
    out += ["## Still to build", "", "| Agent | Purpose | Status |", "|---|---|---|"]
    for name, purpose in PLANNED:
        out.append(f"| {name} | {purpose} | ⚪ not built yet |")
    out += ["", "## Links", "",
            f"- [All reports]({REPORT_FOLDER}/)",
            f"- [Trading rules](trading-rules.md)",
            f"- [Bias log]({REPORT_FOLDER}/bias-log.csv)", ""]
    return "\n".join(out)


def main(now=None):
    now = now or datetime.now(ZoneInfo("America/New_York")).replace(tzinfo=None)
    with open(DASHBOARD, "w") as f:
        f.write(build_dashboard(now))
    print(f"Wrote {DASHBOARD}")


if __name__ == "__main__":
    main()
