"""
x_posts.py - Agent #5: turns the daily briefs into ready-to-post drafts for
the X (Twitter) news account. You copy each draft and post it by hand.

Run it like this:
    python agents/x_posts.py            # morning: thread, midday take, video script
    python agents/x_posts.py --close    # after the close: stocks + crypto wrap

Every post follows the same angle:
    what happened -> why it matters for your money -> what could happen next
Plain headlines are not allowed: X's Original Content Rewards program treats
them as aggregator content and does not pay for them.

The morning run reads the latest briefs the other agents wrote:
  - reports/news/    world news brief (world_news_brief.py)
  - reports/stocks/  stock brief (stock_research.py)
  - reports/crypto/  crypto brief (crypto_research.py)
  - reports/         Nasdaq and gold futures briefs (market_brief.py)
World news, politics and the presidency must never be missing: if the
world brief is empty or missing, this agent runs its own small news search
(WORLD_SEARCHES searches) for that topic. Any other brief that is missing, too
old, or came back empty is SKIPPED and the file says so. The AI is never asked
to fill a gap from memory.

The close run pulls free closing prices from Yahoo Finance (no key needed)
and writes the wrap into the same day's file. On weekends stock markets are
closed, so the wrap covers crypto only.

The drafts are saved in reports/x-posts/YYYY-MM-DD.md (plus a .json copy
of the same drafts), and X-DASHBOARD.md is rebuilt after every run: what the
posts talk about today, which topics were covered or skipped each day, and
which briefs worked. Nothing is posted:
X's API charges per post, and we are in $0 mode. Each run is ONE small call to
the cheapest model with no web search (well under a cent), plus the backup
news search (about 5 cents) on days the world brief is empty.

The API key comes from the environment (GitHub supplies it as a secret).
For a test without an API key, pass drafts you wrote yourself:
    python agents/x_posts.py --drafts my-drafts.json [--date 2026-10-24]
"""

import argparse
import json
import os
import re
import sys
import unicodedata
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from research_tools import SPENT, log_cost, run_call
from notify import send

# ---------------- SETTINGS ----------------
MODEL = "claude-haiku-5-5"                    # the cheapest model: rewriting, no research
PRICE_IN, PRICE_OUT = 0.10 / 1e6, 0.50 / 1e6  # dollars per token, Claude Haiku 5.5
EFFORT = "low"            # little thinking needed to rewrite facts we already have
MAX_TOKENS = 6000
BUDGET = 0.05             # warn in the log if a run costs more than this (dollars)
POST_LIMIT = 280          # X's limit for a free account
WORLD_TOPIC = "World, politics and the presidency"
WORLD_SEARCHES = 4        # backup news search when the world brief is empty ($0.01 each)
BACKUP_MODEL = "claude-sonnet-5-5"            # used only if the search fails on MODEL
BACKUP_PRICES = (2.00 / 1e6, 10.00 / 1e6)     # Claude Sonnet 5.5, dollars per token
X_FOLDER = os.path.join("reports", "x-posts")
X_DASHBOARD = "X-DASHBOARD.md"
DASHBOARD_DAYS = 14       # days of history on the dashboard

# (label, folder, file suffix, oldest brief to use in days). Stock and futures
# briefs don't run every day, so an older one is allowed, labelled with its date.
SOURCES = [
    (WORLD_TOPIC, os.path.join("reports", "news"), "world-brief", 0),
    ("Stocks", os.path.join("reports", "stocks"), "stock-brief", 3),
    ("Crypto", os.path.join("reports", "crypto"), "crypto-brief", 0),
    ("Nasdaq futures (macro backdrop)", "reports", "nasdaq-brief", 3),
    ("Gold futures (macro backdrop)", "reports", "gold-brief", 3),
]

# Closing prices for the after-close wrap (Yahoo Finance symbols).
STOCK_SYMBOLS = {"S&P 500": "^GSPC", "Nasdaq": "^IXIC", "Dow": "^DJI",
                 "10-yr yield": "^TNX", "Oil (WTI)": "CL=F", "Gold": "GC=F"}
CRYPTO_SYMBOLS = {"Bitcoin": "BTC-USD", "Ether": "ETH-USD", "Solana": "SOL-USD"}

DISCLAIMER = "Not financial advice."
WRAP_START, WRAP_END = "<!-- close-wrap:start -->", "<!-- close-wrap:end -->"
# ------------------------------------------

STYLE_RULES = """Rules for every post:
- Each post follows this angle, in this order: what happened -> why it matters
  for the reader's money (savings, mortgage, prices, jobs, portfolio) -> what
  could happen next from this outcome. Write "what could happen next" as an
  "if ... then ..." or "watch ..." line. Never state it as a certainty.
- Never write a plain headline. The angle and the money link are what make
  the post original; X does not pay for aggregator content.
- Use ONLY facts in the material below. Copy numbers, names and dates exactly.
  Never add news, prices or events from memory. If the material says a fact is
  unconfirmed, say so or leave it out.
- If a brief is older than today, say when ("Friday's data") rather than
  presenting it as today's news. Briefs written before the 9:30 AM open
  describe the PREVIOUS trading day's moves: a stock brief written Friday
  morning shows Thursday's moves, so call them Thursday's.
- No buy, sell or hold calls, no price targets, and do not repeat the futures
  briefs' trading bias, lean or key levels. Those are for our own trading.
- Politics: report what happened and what was said. Do not take sides, insult
  anyone, or speculate about motives.
- No links in posts (links go in the suggested reply). At most one emoji and at
  most one hashtag per post. Plain, punchy language; short sentences.
- Keep every post under 260 characters, counting spaces. Keep every
  suggested reply under 200 characters (a disclaimer line is added to it)."""

MORNING_PROMPT = """You write the "Morning Money Brief" for an X (Twitter) account
that explains what happened in the world, politics, the economy, stocks and
crypto, and why it matters for ordinary people's money. Today is {weekday}
{date}.{weekend}

Write:
1. thread: a 3-5 post thread, one post per topic that has material below, in
   this order: world/politics/presidency/other countries, economy, stocks,
   crypto. The world/politics/presidency post is required whenever the
   material has anything on it. Start post 1 with "Morning Money Brief, {short_date}:" and number
   the posts "1/", "2/" and so on at the start. The last post must end with
   "{disclaimer}" Use "section" to name the topic of each post.
2. midday: ONE stand-alone take on the single biggest story in the material,
   framed as "why this matters for your wallet". "story" names the story.
3. close_watch: one line on what to watch at today's close (or, on a weekend,
   when markets reopen), using only scheduled events in the material.
4. video: a 30-60 second vertical video script called "Morning Money Brief"
   for X, YouTube Shorts and Instagram. 80-150 spoken words. A hook in the
   first sentence, then the top 2-3 stories using the same angle, and end with
   "{disclaimer} Follow for tomorrow's brief." Also give 3-6 short on-screen
   text captions.
5. reply_thread and reply_midday: the suggested first reply for the thread and
   for the midday post. Name the sources the material credits, like "Sources:
   Reuters, CoinGecko live data". Do not invent URLs.

{skipped}
""" + STYLE_RULES + """

MATERIAL (the briefs our research agents wrote):
{material}"""

CLOSE_PROMPT = """You write the after-close "stocks + crypto wrap" for an X
(Twitter) account that explains why markets matter for ordinary people's
money. Today is {weekday} {date}.{weekend}

Write 1-2 posts using ONLY the closing numbers below and, for context, this
morning's drafts. Post 1 starts with "Closing bell, {short_date}:" (on a
weekend, "Weekend crypto check, {short_date}:"). Give the key moves, why they
matter for the reader's money, and what could happen next (upcoming events
from this morning's drafts are fine). The last post must end with
"{disclaimer}" Also write a suggested reply naming the data source.

""" + STYLE_RULES + """

CLOSING NUMBERS (Yahoo Finance, may be delayed):
{numbers}

THIS MORNING'S DRAFTS (context only):
{morning}"""

MORNING_SCHEMA = {
    "type": "object",
    "properties": {
        "thread": {"type": "array", "items": {
            "type": "object",
            "properties": {"section": {"type": "string"}, "post": {"type": "string"}},
            "required": ["section", "post"], "additionalProperties": False}},
        "reply_thread": {"type": "string"},
        "midday": {"type": "object",
                   "properties": {"story": {"type": "string"}, "post": {"type": "string"}},
                   "required": ["story", "post"], "additionalProperties": False},
        "reply_midday": {"type": "string"},
        "close_watch": {"type": "string"},
        "video": {"type": "object",
                  "properties": {"script": {"type": "string"},
                                 "on_screen": {"type": "array", "items": {"type": "string"}}},
                  "required": ["script", "on_screen"], "additionalProperties": False},
    },
    "required": ["thread", "reply_thread", "midday", "reply_midday", "close_watch", "video"],
    "additionalProperties": False,
}

CLOSE_SCHEMA = {
    "type": "object",
    "properties": {"posts": {"type": "array", "items": {"type": "string"}},
                   "reply": {"type": "string"}},
    "required": ["posts", "reply"],
    "additionalProperties": False,
}


# ---------------- reading the briefs ----------------

def latest_brief(folder, suffix, today, max_age):
    """The newest '<date>-<suffix>.md' in folder that is not after today and
    at most max_age days old. Returns (date, path) or None."""
    if not os.path.isdir(folder):
        return None
    best = None
    for name in os.listdir(folder):
        m = re.fullmatch(r"(\d{4}-\d{2}-\d{2})-" + re.escape(suffix) + r"\.md", name)
        if not m:
            continue
        day = date.fromisoformat(m.group(1))
        if today - timedelta(days=max_age) <= day <= today and (not best or day > best[0]):
            best = (day, os.path.join(folder, name))
    return best


def brief_status(text):
    """'failed' when the brief has (almost) no real content, 'no-news' when its
    news search failed but live data is there, otherwise 'ok'."""
    lines = [l.strip(" -*|") for l in text.splitlines()]
    content = [l for l in lines if l and not l.startswith(("#", "Written", "---"))
               and not re.search(r"nothing found|no .{0,40}found|could not|couldn't", l, re.I)]
    top = re.search(r"^## Top things[^\n]*\n+\s*(.*)", text, re.M)
    if len(content) < 4 or (top and re.match(r"nothing found", top.group(1), re.I)):
        return "failed"
    if re.search(r"usage.limit|search tool (failed|stopped)|news search tool failed", text, re.I):
        return "no-news"
    return "ok"


def gather(today):
    """Returns (material text, list of skipped notes, list of used notes, urls)."""
    parts, skipped, used, urls = [], [], [], []
    for label, folder, suffix, max_age in SOURCES:
        found = latest_brief(folder, suffix, today, max_age)
        if not found:
            skipped.append(f"{label}: no brief from the last {max_age + 1} day(s).")
            continue
        day, path = found
        with open(path) as f:
            text = f.read()
        status = brief_status(text)
        if status == "failed":
            skipped.append(f"{label}: the {day:%a %b %d} brief came back empty "
                           "(its search failed), so this topic is left out.")
            continue
        note = f"{day:%a %b %d}" + (", today" if day == today else ", NOT today")
        if status == "no-news":
            note += "; its news search failed, so it has live data but little or no news"
        used.append(f"{label}: {path} ({note})")
        parts.append(f"===== {label} - brief dated {day:%A %Y-%m-%d} ({note}) =====\n{text}")
        urls += re.findall(r"https?://[^\s)\]>]+", text)
    return "\n\n".join(parts), skipped, used, list(dict.fromkeys(urls))


# ---------------- backup world news search ----------------

WORLD_PROMPT = """Today is {weekday} {date}. Search the web for the most important
news from the last 24 hours on:
- President Trump and the White House: what he said and did, orders, his schedule today
- US politics and policy: Congress, the courts, the Fed and Treasury
- World affairs: wars, trade and tariffs, and other countries' leaders and economies
Search efficiently: one search can cover several topics.

Write 4-6 items, most important first. For each: what happened in one or two
sentences with names, numbers and dates, then the source in brackets, like
(Reuters). Then a line "Scheduled today:" with any confirmed events and times
(New York time). Use only what you found; never add anything from memory. If
you found nothing, write only "Nothing found." Report what happened without
taking sides. Start directly with the first item."""


def world_search(now):
    """Our own small news search for the world topic, used when the world brief
    is empty. Returns the text, or None if nothing was found."""
    import anthropic
    client = anthropic.Anthropic()
    prompt = WORLD_PROMPT.format(weekday=now.strftime("%A"), date=f"{now:%Y-%m-%d}")
    for model, (price_in, price_out) in [(MODEL, (PRICE_IN, PRICE_OUT)), (BACKUP_MODEL, BACKUP_PRICES)]:
        before = SPENT["searches"]
        try:
            text, t_in, t_out, _ = run_call(client, prompt, use_search=True,
                                            max_searches=WORLD_SEARCHES, max_tokens=4000,
                                            model=model)
        except anthropic.BadRequestError as error:
            print(f"Backup news search on {model} failed: {error}")
            continue
        searches = SPENT["searches"] - before
        cost = log_cost("x-posts", t_in, t_out, searches, price_in, price_out)
        print(f"Backup news search on {model}: {searches} searches, ${cost:.4f}")
        if text and not text.lower().startswith("nothing found"):
            return text
    return None


# ---------------- the AI call ----------------

def ask(prompt, schema):
    """One small call with a fixed JSON shape. Returns (dict, tokens_in, tokens_out)."""
    import anthropic
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY on its own
    response = client.messages.create(
        model=MODEL, max_tokens=MAX_TOKENS,
        output_config={"effort": EFFORT, "format": {"type": "json_schema", "schema": schema}},
        messages=[{"role": "user", "content": prompt}])
    if response.stop_reason == "refusal":
        raise SystemExit("The AI declined to write the drafts, so nothing was saved.")
    if response.stop_reason == "max_tokens":
        raise SystemExit("The drafts were cut off by the length limit, so nothing was saved.")
    text = next(b.text for b in response.content if b.type == "text")
    return json.loads(text), response.usage.input_tokens, response.usage.output_tokens


def date_values(now):
    weekend = now.weekday() >= 5
    return {"weekday": now.strftime("%A"), "date": f"{now:%Y-%m-%d}",
            "short_date": f"{now:%b} {now.day}", "disclaimer": DISCLAIMER,
            "weekend": (" It is the weekend: stock markets are closed and crypto "
                        "trades 24/7." if weekend else "")}


# ---------------- formatting ----------------

def x_length(text):
    """Roughly how X counts characters: links count 23, emoji and wide
    characters count 2, everything else 1."""
    text = re.sub(r"https?://\S+", "x" * 23, text)
    return sum(2 if ord(c) > 0x2000 and (unicodedata.east_asian_width(c) in "WF"
                                         or unicodedata.category(c) == "So") else 1
               for c in text)


def post_block(text, title=None):
    """A post in a code block (easy to copy), with its length and any warning."""
    text = text.strip()
    n = x_length(text)
    head = f"**{title}** " if title else ""
    flag = f"  ⚠️ **{n}/{POST_LIMIT}: too long, trim before posting**" if n > POST_LIMIT else ""
    if re.search(r"https?://", text):
        flag += "  ⚠️ **has a link: move it to the reply**"
    return f"{head}({n}/{POST_LIMIT}){flag}\n```text\n{text}\n```\n"


def reply_block(text, urls=()):
    text = text.strip()
    if DISCLAIMER.lower() not in text.lower():
        text += f"\n{DISCLAIMER} News and analysis only."
    if urls:
        text += "\n" + "\n".join(urls[:3])
    return "Suggested reply (post it right under the main post):\n" + post_block(text)


def render_morning(now, drafts, skipped, used, urls):
    out = [f"# X drafts - {now:%A %Y-%m-%d}\n",
           f"*Written {now:%Y-%m-%d %H:%M} New York time by an AI agent from our research "
           "briefs. Check every fact against the brief before posting: a wrong post costs "
           "trust. Post by hand; nothing here is posted automatically. "
           f"{DISCLAIMER}*\n"]

    out.append("## Sources used\n")
    out += [f"- {u}" for u in used] or ["- None."]
    if any(s.startswith(WORLD_TOPIC) for s in skipped):
        out.append("\n🚨 **No world, politics or presidency news today: the world brief AND the "
                   "backup search both failed. Check the news yourself and write that post "
                   "by hand.**")
    if skipped:
        out.append("\n**Skipped (no invented news):**")
        out += [f"- {s}" for s in skipped]
    out.append("")

    thread = drafts["thread"]
    out.append("## 1. Morning Money Brief thread (post 7-8 AM NY)\n")
    if not 3 <= len(thread) <= 5:
        out.append(f"⚠️ The thread has {len(thread)} posts (aim for 3-5).\n")
    if thread and DISCLAIMER.lower() not in thread[-1]["post"].lower():
        out.append(f"⚠️ The last post is missing \"{DISCLAIMER}\": add it.\n")
    for i, item in enumerate(thread, 1):
        out.append(post_block(item["post"], f"Post {i} - {item['section']}"))
    out.append(reply_block(drafts["reply_thread"], urls))

    out.append("## 2. Midday take: why this matters for your wallet (post 12-1 PM NY)\n")
    out.append(f"Story: {drafts['midday']['story']}\n")
    out.append(post_block(drafts["midday"]["post"]))
    out.append(reply_block(drafts["reply_midday"]))

    out.append("## 3. After-close stocks + crypto wrap (post 4:30-5:30 PM NY)\n")
    out.append(f"{WRAP_START}\nThe 5 PM run fills this in with real closing numbers.\n\n"
               f"What to watch: {drafts['close_watch']}\n{WRAP_END}\n")

    video = drafts["video"]
    words = len(video["script"].split())
    out.append("## 4. Video script: Morning Money Brief (30-60 sec vertical)\n")
    out.append("For X, YouTube Shorts and Instagram Reels. "
               f"{words} words, about {round(words / 2.5)} seconds at a normal pace.\n")
    out.append("Script:\n```text\n" + video["script"].strip() + "\n```\n")
    out.append("On-screen text:")
    out += [f"{i}. {t}" for i, t in enumerate(video["on_screen"], 1)]
    out.append("")
    return "\n".join(out)


def render_wrap(now, drafts, numbers):
    out = [WRAP_START, f"Closing numbers (Yahoo Finance, {now:%H:%M} NY, may be delayed):",
           "```text", numbers, "```\n"]
    for i, post in enumerate(drafts["posts"], 1):
        out.append(post_block(post, f"Post {i}"))
    out.append(reply_block(drafts["reply"]))
    out.append(WRAP_END)
    return "\n".join(out)


# ---------------- closing prices ----------------

def closing_numbers(now):
    """Last price and change vs the previous daily close. Returns text."""
    import yfinance as yf
    symbols = dict(CRYPTO_SYMBOLS)
    if now.weekday() < 5:
        symbols = {**STOCK_SYMBOLS, **symbols}
    closes = yf.download(list(symbols.values()), period="7d", interval="1d",
                         progress=False, auto_adjust=False)["Close"]
    lines = []
    for name, symbol in symbols.items():
        series = closes[symbol].dropna()
        if len(series) < 2:
            lines.append(f"{name}: no data")
            continue
        last, prev = float(series.iloc[-1]), float(series.iloc[-2])
        if symbol == "^TNX":
            lines.append(f"{name}: {last:.2f}% ({last - prev:+.2f} pts)")
        else:
            lines.append(f"{name}: {last:,.2f} ({(last / prev - 1) * 100:+.1f}%)")
    if now.weekday() >= 5:
        lines.append("Stock markets: closed for the weekend")
    return "\n".join(lines)


# ---------------- the dashboard ----------------

TOPICS = [("🌍 World & politics", r"world|politic|president|white house|trump|congress|war|"
                                 r"tariff|trade|countr|china|russia|europe|canada"),
          ("💵 Economy", r"econom|inflation|cpi|fed|rate|jobs|gdp|pce"),
          ("📈 Stocks", r"stock|nasdaq|s&p|earnings|equit"),
          ("🪙 Crypto", r"crypto|bitcoin|btc|ether|solana")]


def record_path(day):
    return os.path.join(X_FOLDER, f"{day:%Y-%m-%d}.json")


def load_record(day):
    try:
        with open(record_path(day)) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_record(day, record):
    os.makedirs(X_FOLDER, exist_ok=True)
    with open(record_path(day), "w") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)


def topic_of(section):
    for name, pattern in TOPICS:
        if re.search(pattern, section, re.I):
            return name
    return section


def short(text, n=110):
    text = re.sub(r"^\d+/\s*", "", " ".join(text.split()))
    return text if len(text) <= n else text[:n - 1].rsplit(" ", 1)[0] + "…"


def month_cost(now):
    path = os.path.join("reports", "costs", "x-posts.csv")
    try:
        with open(path) as f:
            rows = [l.split(",") for l in f.read().splitlines()[1:]]
        rows = [r for r in rows if r[0].startswith(f"{now:%Y-%m}")]
        return sum(float(r[-1]) for r in rows), len(rows)
    except (OSError, ValueError, IndexError):
        return 0.0, 0


def brief_health(today, days=7):
    """Table rows: how each source brief looked on each of the last `days` days."""
    icons = {"ok": "✅", "no-news": "🟡", "failed": "❌"}
    rows = []
    for label, folder, suffix, _ in SOURCES:
        cells = []
        for back in range(days - 1, -1, -1):
            day = today - timedelta(days=back)
            path = os.path.join(folder, f"{day:%Y-%m-%d}-{suffix}.md")
            if os.path.exists(path):
                with open(path) as f:
                    cells.append(icons[brief_status(f.read())])
            else:
                cells.append("·")
        rows.append(f"| {label} | " + " | ".join(cells) + " |")
    head = " | ".join(f"{today - timedelta(days=b):%a %d}" for b in range(days - 1, -1, -1))
    return [f"| Brief | {head} |", "|---|" + "---|" * days] + rows


def build_dashboard(now):
    today = now.date()
    records = [r for r in (load_record(today - timedelta(days=b)) for b in range(DASHBOARD_DAYS)) if r]
    cost, runs = month_cost(now)
    out = ["# 𝕏 X Brief Dashboard", "",
           f"*Updated {now:%Y-%m-%d %H:%M} New York time by the X drafts agent "
           "(agents/x_posts.py). Drafts only: nothing is posted automatically. "
           f"News and analysis, {DISCLAIMER.lower()}*", "",
           "[← Main dashboard](DASHBOARD.md)", ""]

    latest = records[0] if records else {}
    out += ["## Today", ""]
    if latest.get("date") != f"{today:%Y-%m-%d}":
        out += ["No drafts for today yet. The morning run is about 7 AM New York time.", ""]
    else:
        wrap = latest.get("wrap")
        out += [f"- **Morning drafts:** {'✅ ready' if latest.get('thread') else '⏳ not yet'} "
                f"→ [open today's drafts](reports/x-posts/{latest['date']}.md)",
                f"- **After-close wrap:** {'✅ ready' if wrap else '⏳ after the close (about 5 PM New York time)'}",
                f"- **Claude cost this month:** ${cost:.3f} ({runs} run(s) this month)", ""]
        if latest.get("skipped"):
            out += ["**Left out today (the brief failed or is missing, so nothing was made up):**"]
            out += [f"- {s}" for s in latest["skipped"]] + [""]

        out += ["## What it's talking about today", "",
                "| When | Post | Topic | What it says |", "|---|---|---|---|"]
        for i, item in enumerate(latest.get("thread", []), 1):
            out.append(f"| 7-8 AM | Thread {i} | {topic_of(item['section'])} | {short(item['post'])} |")
        if latest.get("midday"):
            out.append(f"| 12-1 PM | Midday take | {latest['midday']['story']} | "
                       f"{short(latest['midday']['post'])} |")
        for i, post in enumerate((wrap or {}).get("posts", []), 1):
            out.append(f"| After close | Wrap {i} | Closing numbers | {short(post)} |")
        if latest.get("video"):
            out.append(f"| Any time | Video | Morning Money Brief | "
                       f"{short(latest['video']['script'])} |")
        out.append("")
        if latest.get("close_watch"):
            out += ["**Coming up:** " + latest["close_watch"], ""]
        if wrap:
            out += ["**Closing numbers:**", "```text", wrap["numbers"], "```", ""]

    out += [f"## Topics covered, last {DASHBOARD_DAYS} days", "",
            "✅ covered · ⏭️ left out (its brief failed or was missing) · — no drafts that day", "",
            "| Date | " + " | ".join(n for n, _ in TOPICS) + " | Wrap | Biggest story |",
            "|---|" + "---|" * (len(TOPICS) + 2)]
    for back in range(DASHBOARD_DAYS):
        day = today - timedelta(days=back)
        r = load_record(day)
        if not r:
            if back < 7:
                out.append(f"| {day:%a %b %d} | " + " | ".join("—" for _ in TOPICS) + " | — | |")
            continue
        covered = {topic_of(t["section"]) for t in r.get("thread", [])}
        cells = ["✅" if name in covered else "⏭️" for name, _ in TOPICS]
        link = f"[{day:%a %b %d}](reports/x-posts/{day:%Y-%m-%d}.md)"
        out.append(f"| {link} | " + " | ".join(cells) + f" | {'✅' if r.get('wrap') else '—'} | "
                   f"{(r.get('midday') or {}).get('story', '')} |")
    out.append("")

    out += ["## Are the source briefs working? (last 7 days)", "",
            "The X posts can only talk about what these briefs found. "
            "✅ worked · 🟡 live prices only (its news search failed) · ❌ empty · · not run that day "
            "(the stock brief runs Mon/Wed/Fri, Nasdaq Mon-Fri, gold Sun-Thu evenings)", ""]
    out += brief_health(today) + [""]

    out += ["## How to post", "",
            "1. Open today's drafts (link above). Each post is in its own box, with its length.",
            "2. Post the thread at 7-8 AM: post 1, then reply to it with post 2, and so on. "
            "Put the suggested reply (sources) under it.",
            "3. Midday take at 12-1 PM, the after-close wrap at 4:30-5:30 PM.",
            "4. Fix anything marked ⚠️ first, and spot-check a number or two against the brief.", ""]

    with open(X_DASHBOARD, "w") as f:
        f.write("\n".join(out))
    print(f"Wrote {X_DASHBOARD}")


# ---------------- runs ----------------

def finish(path, tokens_in, tokens_out, title):
    print(f"Saved {path}")
    cost = 0.0
    if tokens_in or tokens_out:
        cost = log_cost("x-posts", tokens_in, tokens_out, 0, PRICE_IN, PRICE_OUT)
        print(f"Tokens used: {tokens_in} in, {tokens_out} out")
        print(f"Estimated cost: ${cost:.4f}" + ("  (over budget!)" if cost > BUDGET else ""))
    send(title, "Your X drafts are ready to copy and post.", priority="low", tags="bird",
         link=f"https://github.com/jayryd7-gif/ai-trading-agent/blob/main/{path}")


def morning(now, drafts_file=None):
    material, skipped, used, urls = gather(now.date())
    tokens_in = tokens_out = 0
    world_missing = any(s.startswith(WORLD_TOPIC) for s in skipped)
    if world_missing and not drafts_file:
        news = world_search(now)
        if news:
            skipped = [s for s in skipped if not s.startswith(WORLD_TOPIC)]
            used.insert(0, f"{WORLD_TOPIC}: the world brief was empty, so the X agent "
                           f"searched the news itself ({now:%a %b %d}, today)")
            material = (f"===== {WORLD_TOPIC} - searched {now:%A %Y-%m-%d} (today) =====\n"
                        f"{news}\n\n{material}")
            world_missing = False
    if not material:
        raise SystemExit("No usable brief for today, so no drafts were written. "
                         + " ".join(skipped))
    if world_missing:
        send("X drafts: NO politics news today", "The world brief and the backup search both "
             "came back empty. Check the news yourself before posting.", priority="high",
             tags="warning")
    if drafts_file:
        with open(drafts_file) as f:
            drafts = json.load(f)
    else:
        skipped_text = ("These topics have NO material today, so leave them out "
                        "completely (do not write about them from memory):\n"
                        + "\n".join(f"- {s}" for s in skipped)) if skipped else ""
        prompt = MORNING_PROMPT.format(**date_values(now), skipped=skipped_text,
                                       material=material)
        drafts, tokens_in, tokens_out = ask(prompt, MORNING_SCHEMA)

    os.makedirs(X_FOLDER, exist_ok=True)
    path = os.path.join(X_FOLDER, f"{now:%Y-%m-%d}.md")
    text = render_morning(now, drafts, skipped, used, urls)
    if os.path.exists(path):   # keep a close wrap that is already there
        with open(path) as f:
            old = re.search(re.escape(WRAP_START) + ".*?" + re.escape(WRAP_END), f.read(), re.S)
        if old and "Closing numbers" in old.group(0):
            text = re.sub(re.escape(WRAP_START) + ".*?" + re.escape(WRAP_END),
                          lambda _: old.group(0), text, flags=re.S)
    with open(path, "w") as f:
        f.write(text)
    record = load_record(now.date())
    record.update({"date": f"{now:%Y-%m-%d}", "written": f"{now:%Y-%m-%d %H:%M}",
                   "skipped": skipped, "used": used, **drafts})
    save_record(now.date(), record)
    finish(path, tokens_in, tokens_out, "X morning drafts ready")
    build_dashboard(now)
    return path


def close(now, drafts_file=None):
    path = os.path.join(X_FOLDER, f"{now:%Y-%m-%d}.md")
    morning_text = open(path).read() if os.path.exists(path) else "(none written today)"
    numbers = closing_numbers(now)
    tokens_in = tokens_out = 0
    if drafts_file:
        with open(drafts_file) as f:
            drafts = json.load(f)
    else:
        prompt = CLOSE_PROMPT.format(**date_values(now), numbers=numbers,
                                     morning=morning_text[:6000])
        drafts, tokens_in, tokens_out = ask(prompt, CLOSE_SCHEMA)

    wrap = render_wrap(now, drafts, numbers)
    os.makedirs(X_FOLDER, exist_ok=True)
    if WRAP_START in morning_text:
        text = re.sub(re.escape(WRAP_START) + ".*?" + re.escape(WRAP_END),
                      lambda _: wrap, morning_text, flags=re.S)
    else:
        text = (f"# X drafts - {now:%A %Y-%m-%d}\n\n*No morning drafts today. "
                f"{DISCLAIMER}*\n\n## 3. After-close stocks + crypto wrap\n\n{wrap}\n")
    with open(path, "w") as f:
        f.write(text)
    record = load_record(now.date())
    record.update({"date": f"{now:%Y-%m-%d}",
                   "wrap": {"numbers": numbers, "written": f"{now:%Y-%m-%d %H:%M}", **drafts}})
    save_record(now.date(), record)
    finish(path, tokens_in, tokens_out, "X close wrap ready")
    build_dashboard(now)
    return path


def main():
    parser = argparse.ArgumentParser(description="Write X post drafts from the daily briefs.")
    parser.add_argument("--close", action="store_true", help="write the after-close wrap")
    parser.add_argument("--drafts", help="use drafts from this JSON file instead of the AI")
    parser.add_argument("--date", help="pretend today is this date (YYYY-MM-DD)")
    parser.add_argument("--dashboard", action="store_true", help="only rebuild X-DASHBOARD.md")
    args = parser.parse_args()
    now = datetime.now(ZoneInfo("America/New_York")).replace(tzinfo=None)
    if args.date:
        now = datetime.combine(date.fromisoformat(args.date), now.time())
    if args.dashboard:
        build_dashboard(now)
    else:
        (close if args.close else morning)(now, args.drafts)


if __name__ == "__main__":
    sys.exit(main())
