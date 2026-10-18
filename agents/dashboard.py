"""
dashboard.py - Builds DASHBOARD.md, a one-page view of your agent ecosystem.

This is plain code, not an AI agent, so it costs nothing in API credits.
It reads the files the other agents leave in reports/ and writes a page that
GitHub displays nicely, even in a private repo.

It shows: your reminders, how each agent is doing, any problems in the last
runs, the latest briefs and reviews (readable right on the page, in
expandable sections), the latest lean for each market, the session reviews, scorecard summary,
charts, recent results, and the agents still to be built.
"""

import os
import re
from datetime import datetime
from zoneinfo import ZoneInfo

from charts import make_charts
from scorer import ENOUGH_CALLS, _rate, read_csv
from market_data import INSTRUMENTS

# ---------------- SETTINGS ----------------
REPORT_FOLDER = "reports"
DASHBOARD = "DASHBOARD.md"
JOURNAL = "trade-journal.md"
NO_TRADE_JOURNAL = "no-trade-journal.md"
PAPER_SUMMARY = os.path.join("paper-trading", "summary.md")
REMINDERS = "REMINDERS.md"
GOOD_WITHIN_HOURS = 72     # green if an agent ran within this long (covers weekends)
LATE_WITHIN_HOURS = 168    # yellow up to this long, red after that
# ------------------------------------------

LEAN_ICON = {"Bullish": "▲", "Bearish": "▼", "Neutral": "◆", "Unknown": "?"}

PLANNED = [
    ("Business research agent", "Finds fast-growing products worth selling"),
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


def scorecard_updated():
    """Read the 'Updated YYYY-MM-DD HH:MM' stamp from the scorecard."""
    path = os.path.join(REPORT_FOLDER, "scorecard.md")
    try:
        text = open(path).read()
    except OSError:
        return None
    match = re.search(r"Updated (\d{4}-\d{2}-\d{2}) (\d{2}:\d{2})", text)
    return parse_time(match.group(1), match.group(2)) if match else None


def latest_review(name):
    """Newest review file for a market: (session date, path, written time) or None."""
    folder = os.path.join(REPORT_FOLDER, "reviews")
    try:
        files = os.listdir(folder)
    except OSError:
        return None
    pattern = re.compile(rf"^(\d{{4}}-\d{{2}}-\d{{2}})-{name}-review\.md$")
    found = sorted(f for f in files if pattern.match(f))
    if not found:
        return None
    newest = found[-1]
    session_date = pattern.match(newest).group(1)
    written = None
    try:
        match = re.search(r"Written (\d{4}-\d{2}-\d{2}) (\d{2}:\d{2})",
                          open(os.path.join(folder, newest)).read())
        if match:
            written = parse_time(match.group(1), match.group(2))
    except OSError:
        pass
    return session_date, f"{REPORT_FOLDER}/reviews/{newest}", written


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


def build_dashboard(now):
    briefs = read_csv(os.path.join(REPORT_FOLDER, "bias-log.csv"))
    scores = read_csv(os.path.join(REPORT_FOLDER, "scores.csv"))

    out = ["# Agent dashboard", "",
           f"Last updated {now:%Y-%m-%d %H:%M} New York time. "
           "Everything here is written by software and AI agents. "
           "It can be wrong, so check anything you plan to act on.", "",
           "**[🪙 Open the Crypto Dashboard →](CRYPTO-DASHBOARD.md)**", ""]

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
             "weekdays about 6-7 AM")):
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
    for name, config in INSTRUMENTS.items():
        review = latest_review(name)
        when = review[2] if review else None
        out.append(f"| {status_icon(when, now)} | Post-session review: {name} | "
                   f"Reviews the {config['label']} session after it ends | "
                   f"{age_text(when, now) if when else 'never'} | "
                   f"after each session ends |")
    out += ["", "🟢 ran recently  🟡 a bit late  🔴 check it  ⚪ never ran", ""]

    # ---- Problems ----
    problems = run_problems()
    if problems:
        out += ["## ⚠️ Problems", ""] + problems + [
            "", "Open the repo's Actions tab on GitHub for more detail.", ""]

    # ---- Paper trading ----
    glance, rest = paper_section()
    out += ["## Paper trading", ""]
    if glance:
        out += [glance, ""]
        out += details("Challenge simulation, results by market, and daily results", rest)
        out += ["[Paper trading journal](paper-trading/paper-journal.md) · "
                "[TradingView strategy](tradingview/breakout_strategy.pine)", ""]
    else:
        out += ["No paper trades yet.", ""]

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

    # ---- Latest reviews ----
    out += ["## Latest session reviews", "",
            "| Market | Session | Review |", "|---|---|---|"]
    for name in INSTRUMENTS:
        review = latest_review(name)
        if review:
            out.append(f"| {name} | {review[0]} | [read it]({review[1]}) |")
        else:
            out.append(f"| {name} | none yet | |")
    out += [""]
    for name in INSTRUMENTS:
        review = latest_review(name)
        if review:
            out += details(f"📝 {name} review, session {review[0]}",
                           read_body(review[1], drop_section="Facts used"))
    out += [f"[All reviews]({REPORT_FOLDER}/reviews/)", ""]

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
