"""
x_posts.py - Agent #5: turns the daily briefs into ready-to-post drafts for
the X (Twitter) news account. You copy each draft and post it by hand.

Run it like this:
    python agents/x_posts.py            # morning: thread, midday take, video script
    python agents/x_posts.py --evening  # evening: what happened today, what to watch tomorrow

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
(WORLD_SEARCHES searches) for that topic, and if that fails too it uses free
Google News headlines (news_feed.py). Any other brief that is missing, too
old, or came back empty is SKIPPED and the file says so. The AI is never asked
to fill a gap from memory.

The evening run writes a second 5-post thread: what happened today and what to
watch tomorrow. It uses free data only: closing prices from Yahoo Finance (on
Sundays the futures that reopen at 6 PM; on Saturdays crypto only), free Google
News headlines and the free economic calendar (news_feed.py), and this
morning's briefs and drafts.

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

from research_tools import SPENT, check_budget, log_cost, run_call
from news_feed import MARKET_TOPICS, TOPICS as NEWS_TOPICS, calendar_text, fed_text, headlines_text, regulators_text
from notify import send

# ---------------- SETTINGS ----------------
MODEL = "claude-haiku-5-5"                    # the cheapest model: rewriting, no research
PRICE_IN, PRICE_OUT = 0.10 / 1e6, 0.50 / 1e6  # dollars per token, Claude Haiku 5.5
EFFORT = "low"            # little thinking needed to rewrite facts we already have
MAX_TOKENS = 16000         # room for the hidden thinking too; a cut-off answer is lost (Oct 26)
BUDGET = 0.05             # warn in the log if a run costs more than this (dollars)
POST_LIMIT = 280          # X's limit for a free account
BRAND = "Cash Flow Brief"             # the X account's name
HANDLE = "@cashflowbrief00"           # the X account's handle
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

# Prices for the evening thread (Yahoo Finance symbols).
STOCK_SYMBOLS = {"S&P 500": "^GSPC", "Nasdaq": "^IXIC", "Dow": "^DJI",
                 "10-yr yield": "^TNX", "Oil (WTI)": "CL=F", "Gold": "GC=F"}
CRYPTO_SYMBOLS = {"Bitcoin": "BTC-USD", "Ether": "ETH-USD", "Solana": "SOL-USD"}
FUTURES_SYMBOLS = {"S&P 500 futures": "ES=F", "Nasdaq futures": "NQ=F",   # Sunday evenings
                   "Oil (WTI)": "CL=F", "Gold": "GC=F"}

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

MORNING_PROMPT = """You write the morning "{brand}" for an X (Twitter) account
that explains what happened in the world, politics, the economy, stocks and
crypto, and why it matters for ordinary people's money. Today is {weekday}
{date}.{weekend}

Write:
1. thread: a 5-post thread in exactly this format (blank lines as shown).
   Post 1, section "Intro":
     1/ {brand}, {short_date} ☀️

     <one sentence: the biggest things for your wallet today>

     What happened, why it matters, and what could happen next 🧵
   Posts 2-5, sections "Politics", "Economy", "Stocks", "Crypto", in that order
   (Politics covers the President, the White House, Congress and other
   countries; it is required whenever the material has anything on it.
   Economy also covers SEC and CFTC actions and market-moving hearings; put
   crypto rules in the Crypto post):
     2/ Politics: <what happened>

     Why it matters: <the money link>

     Next: <what could happen next>
   If a topic has no material at all, leave that post out and renumber. The
   last post must end with a blank line and "{disclaimer}"
   If the material has a "What the Fed said" section or a Fed rate decision
   from the last day, add a "🏦 What the Fed said" post right after Economy
   (section "Fed", 6 posts): bullets for the decision and vote, inflation,
   jobs or the economy, and what the chair signaled, then "Why it matters".
2. midday: ONE stand-alone take on the single biggest story in the material,
   framed as "why this matters for your wallet". "story" names the story.
3. close_watch: one line on what to watch at today's close (or, on a weekend,
   when markets reopen), using only scheduled events in the material.
4. video: a 30-60 second vertical video script called "{brand}"
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

EVENING_PROMPT = """You write the evening "{brand}" for an X (Twitter) account
that explains what happened in the world, politics, the economy, stocks and
crypto, and why it matters for ordinary people's money. It is {weekday} {date},
evening, New York time.{weekend}

Write a 5-post thread about what happened TODAY and what to watch TOMORROW
({tomorrow}), in exactly this format (blank lines as shown).
Post 1, section "Intro":
  1/ {brand}: Evening, {short_date} 🌙

  <one sentence: the biggest things for your wallet today>

  What happened today and what to watch {tomorrow_short} 🧵
Posts 2-5, sections "Politics", "Economy", "Stocks", "Crypto", in that order
(Politics covers the President, the White House, Congress and other countries;
it is required. Economy also covers SEC and CFTC actions and market-moving
hearings; put crypto rules in the Crypto post):
  2/ Politics & world: <what happened today>

  Why it matters: <the money link>

  Tomorrow: <what to watch tomorrow>
The last post must end with a blank line and "{disclaimer}"

If a FED DECISION section is given below (the Fed announced a rate decision
in the last day), add one extra post right after the Economy post, section
"Fed", so the thread has 6 posts (renumber; Crypto stays last). Format:
  N/ 🏦 What the Fed said:

  • <the decision, and the vote with any dissents>
  • <the key line on inflation>
  • <the key line on jobs or the economy>
  • <what the chair signaled about next steps (press conference headlines)>

  Why it matters: <rates on mortgages, loans, savings>
Use only the official statement and the headlines. Quote at most a few
words, and mark press-conference points as reported by the outlet.

Also write reply_evening: the suggested sources reply, naming the outlets and
data the posts use, like "Sources: Reuters, AP (politics); Yahoo Finance;
CoinGecko". Do not invent URLs.

For "Tomorrow", use the ECONOMIC CALENDAR (official times, New York time) and
events named in the headlines or briefs (earnings, votes, rallies). If none are named for a topic, say what to watch as a
follow-up of today's story ("Watch whether ..."), never an invented event.
HEADLINES are headlines only: state only what a headline says, credit the
outlet, and add no details. Prices come only from the PRICES section.

""" + STYLE_RULES + """

PRICES (Yahoo Finance, may be delayed):
{numbers}

ECONOMIC CALENDAR (free feed, New York time; "TODAY" here means {date}):
{calendar}

TODAY'S HEADLINES (Google News, last 24 hours):
{headlines}

REGULATORS AND HEARINGS (official SEC and CFTC press releases, hearing headlines):
{regulators}

{fed}

THIS MORNING'S BRIEFS AND DRAFTS (context, including today's and this week's schedule):
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

EVENING_SCHEMA = {
    "type": "object",
    "properties": {
        "thread": MORNING_SCHEMA["properties"]["thread"],
        "reply_evening": {"type": "string"},
    },
    "required": ["thread", "reply_evening"],
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
    check_budget("The X drafts agent")
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


SHORTEN_PROMPT = """Each X post below is too long. Rewrite each one to at most
{limit} characters, counting spaces. Keep the same facts, numbers and names, and
the same angle: what happened -> why it matters for your money -> what could
happen next. Keep any "1/"-style number at the start and any "Not financial
advice." at the end. Cut filler words first. Return the posts in the same order.

{posts}"""

SHORT_SCHEMA = {"type": "object",
                "properties": {"posts": {"type": "array", "items": {"type": "string"}}},
                "required": ["posts"], "additionalProperties": False}
REPLY_KEYS = ("reply_thread", "reply_midday", "reply_evening", "reply")   # a disclaimer line is added to these


def shorten_long(drafts):
    """One extra small call that shortens every post over the limit (the model
    often runs a little long). Returns (tokens_in, tokens_out)."""
    slots = [(item, "post") for item in drafts.get("thread", [])]
    if drafts.get("midday"):
        slots.append((drafts["midday"], "post"))
    slots += [(drafts, key) for key in REPLY_KEYS if key in drafts]
    slots += [(drafts["posts"], i) for i in range(len(drafts.get("posts", [])))]
    limit = lambda key: 225 if key in REPLY_KEYS else 270
    long = [(box, key) for box, key in slots if x_length(box[key]) > limit(key)]
    if not long:
        return 0, 0
    text = "\n\n".join(f"POST {n}:\n{box[key]}" for n, (box, key) in enumerate(long, 1))
    answer, t_in, t_out = ask(SHORTEN_PROMPT.format(limit=250, posts=text), SHORT_SCHEMA)
    for (box, key), new in zip(long, answer.get("posts", [])):
        if x_length(new) < x_length(box[key]):
            box[key] = new.strip()
    print(f"Shortened {len(long)} post(s) that were over the limit.")
    return t_in, t_out


def date_values(now):
    weekend = now.weekday() >= 5
    tomorrow = now + timedelta(days=1)
    return {"brand": BRAND, "weekday": now.strftime("%A"),
            "tomorrow": f"{tomorrow:%A %b} {tomorrow.day}", "tomorrow_short": f"{tomorrow:%A}", "date": f"{now:%Y-%m-%d}",
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
    out.append(f"## 1. {BRAND} morning thread (post before 6 AM, or posts 1-2 then 3-5 at 8-9 AM)\n")
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

    out.append("## 3. Evening thread (post 7-9 PM NY)\n")
    out.append(f"{WRAP_START}\nThe evening run (about 6:30 PM NY) fills this in.\n\n"
               f"What to watch: {drafts['close_watch']}\n{WRAP_END}\n")

    video = drafts["video"]
    words = len(video["script"].split())
    out.append(f"## 4. Video script: {BRAND} (30-60 sec vertical)\n")
    out.append("For X, YouTube Shorts and Instagram Reels. "
               f"{words} words, about {round(words / 2.5)} seconds at a normal pace.\n")
    out.append("Script:\n```text\n" + video["script"].strip() + "\n```\n")
    out.append("On-screen text:")
    out += [f"{i}. {t}" for i, t in enumerate(video["on_screen"], 1)]
    out.append("")
    return "\n".join(out)


def render_evening(now, drafts, numbers):
    thread = drafts["thread"]
    out = [WRAP_START, f"Prices (Yahoo Finance, {now:%H:%M} NY, may be delayed):",
           "```text", numbers, "```\n"]
    if thread and DISCLAIMER.lower() not in thread[-1]["post"].lower():
        out.append(f"⚠️ The last post is missing \"{DISCLAIMER}\": add it.\n")
    for i, item in enumerate(thread, 1):
        out.append(post_block(item["post"], f"Post {i} of {len(thread)} - {item['section']}"))
    out.append(reply_block(drafts["reply_evening"]))
    out.append(WRAP_END)
    return "\n".join(out)


# ---------------- evening prices ----------------

def change_line(name, symbol, last, prev):
    if symbol == "^TNX":
        return f"{name}: {last:.2f}% ({last - prev:+.2f} pts vs the last close)"
    return f"{name}: {last:,.2f} ({(last / prev - 1) * 100:+.1f}% vs the last close)"


def evening_numbers(now):
    """Latest price and change vs the previous daily close. Weekdays: the stock
    market close; Sundays: the futures that reopen at 6 PM; always crypto."""
    import yfinance as yf
    if now.weekday() < 5:
        symbols = {**STOCK_SYMBOLS, **CRYPTO_SYMBOLS}
    elif now.weekday() == 6:
        symbols = {**FUTURES_SYMBOLS, **CRYPTO_SYMBOLS}
    else:
        symbols = dict(CRYPTO_SYMBOLS)
    lines = []
    for name, symbol in symbols.items():
        try:
            ticker = yf.Ticker(symbol)
            daily = ticker.history(period="10d", interval="1d")["Close"].dropna()
            prev = daily[[d.date() < now.date() for d in daily.index]]
            hourly = ticker.history(period="2d", interval="1h")["Close"].dropna()
            last = float(hourly.iloc[-1]) if len(hourly) else float(daily.iloc[-1])
            lines.append(change_line(name, symbol, last, float(prev.iloc[-1])))
        except Exception as error:      # one missing price never stops the thread
            lines.append(f"{name}: no data ({type(error).__name__})")
    if now.weekday() == 5:
        lines.append("Stock markets: closed for the weekend (crypto trades 24/7)")
    elif now.weekday() == 6:
        lines.append("Stock markets: closed today; futures reopened at 6 PM NY; "
                     "the stock market opens Monday 9:30 AM NY")
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
    out = [f"# 𝕏 {BRAND} Dashboard ({HANDLE})", "",
           f"*Updated {now:%Y-%m-%d %H:%M} New York time by the X drafts agent "
           "(agents/x_posts.py). Drafts only: nothing is posted automatically. "
           f"News and analysis, {DISCLAIMER.lower()}*", "",
           "[← Main dashboard](DASHBOARD.md)", ""]

    latest = records[0] if records else {}
    out += ["## Today", ""]
    if latest.get("date") != f"{today:%Y-%m-%d}":
        out += ["No drafts for today yet. The morning run is about 5 AM New York time.", ""]
    else:
        night = latest.get("evening")
        out += [f"- **Morning thread:** {'✅ ready' if latest.get('thread') else '⏳ not yet'} "
                f"→ [open today's drafts](reports/x-posts/{latest['date']}.md)",
                f"- **Evening thread:** {'✅ ready (below), reminder at 7 PM' if night else '⏳ about 6:30 PM New York time'}",
                f"- **Claude cost this month:** ${cost:.3f} ({runs} run(s) this month)", ""]
        if latest.get("skipped"):
            out += ["**Left out today (the brief failed or is missing, so nothing was made up):**"]
            out += [f"- {s}" for s in latest["skipped"]] + [""]

        if night:     # in the evening, tonight's thread goes first
            nthread = night.get("thread", [])
            out += [f"## 🌙 Tonight's thread, ready to copy ({today:%A %b %d})", "",
                    "What happened today and what to watch tomorrow. Post it in one go "
                    f"(post 1, tap **+** for each next post, **Post all**), then reply to post "
                    f"{len(nthread)} with the sources reply.", ""]
            for i, item in enumerate(nthread, 1):
                name = {"Intro": "Intro", "Fed": "🏦 Fed"}.get(item["section"]) or topic_of(item["section"])
                out.append(post_block(item["post"], f"Post {i} of {len(nthread)} · {name}"))
            if night.get("reply_evening"):
                out.append(reply_block(night["reply_evening"]).replace(
                    "Suggested reply (post it right under the main post):",
                    f"**Reply under post {len(nthread)} · sources**"))
            out += ["<details><summary>Prices used</summary>", "", "```text", night["numbers"],
                    "```", "</details>", ""]

        thread = latest.get("thread", [])
        out += [f"## 📋 {'This morning' if night else 'Today'}'s posts, ready to copy ({today:%A %b %d})", "",
                "Each box has a copy button (top right on GitHub). **Before work:** post 1 and 2 "
                "as a thread (post 1, tap **+**, post 2, **Post all**). **On your 8-9 AM break:** "
                "open post 2, tap Reply and post 3, then reply to post 3 with post 4, and post 4 "
                f"with post 5, so they join the same thread. Then reply to post {len(thread)} "
                "with the sources reply. (Or post all 5 at once before work.)", ""]
        for i, item in enumerate(thread, 1):
            name = {"Intro": "Intro", "Fed": "🏦 Fed"}.get(item["section"]) or topic_of(item["section"])
            out.append(post_block(item["post"], f"Post {i} of {len(thread)} · {name}"))
        if latest.get("reply_thread"):
            out.append(reply_block(latest["reply_thread"]).replace(
                "Suggested reply (post it right under the main post):",
                f"**Reply under post {len(thread)} · sources**"))
        if latest.get("midday"):
            out += [f"### Midday take (12-1 PM): {latest['midday']['story']}", "",
                    post_block(latest["midday"]["post"])]
        if latest.get("video"):
            out += ["<details><summary>🎬 Video script (30-60 sec)</summary>", "",
                    "```text", latest["video"]["script"].strip(), "```", "</details>", ""]
        if latest.get("close_watch"):
            out += ["**Coming up:** " + latest["close_watch"], ""]

    out += [f"## Topics covered, last {DASHBOARD_DAYS} days", "",
            "✅ covered · ⏭️ left out (its brief failed or was missing) · — no drafts that day", "",
            "| Date | " + " | ".join(n for n, _ in TOPICS) + " | Evening | Biggest story |",
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
        out.append(f"| {link} | " + " | ".join(cells) + f" | {'✅' if r.get('evening') else '—'} | "
                   f"{(r.get('midday') or {}).get('story', '')} |")
    out.append("")

    out += ["## Are the source briefs working? (last 7 days)", "",
            "The X posts can only talk about what these briefs found. "
            "✅ worked · 🟡 live prices only (its news search failed) · ❌ empty · · not run that day "
            "(the stock brief runs Mon/Wed/Fri, Nasdaq Mon-Fri, gold Sun-Thu evenings)", ""]
    out += brief_health(today) + [""]

    out += ["## 🚀 When to turn on auto-posting", "",
            "You post by hand for now. Once the account has traction, tell Claude "
            "**\"turn on X auto-posting\"** and the bot will post these drafts by itself:",
            "- 500+ followers, **or**",
            "- any post with 10,000+ views, **or**",
            "- 1,000+ views a day for a week (check the account's Analytics).", "",
            "It costs about $2.50-3 a month through X's API, within the $25 AI budget.", ""]
    out += ["## How to post", "",
            "1. Open today's drafts (link above). Each post is in its own box, with its length.",
            "2. Morning thread (ready by about 5:30 AM New York time): posts 1-2 before work, "
            "3-5 as replies on your 8-9 AM break (or all 5 at once). Sources reply under the last.",
            "3. Midday take at 12-1 PM, the evening thread at 7-9 PM.",
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
    if world_missing and not drafts_file:
        headlines = headlines_text()
        if headlines:
            skipped = [s for s in skipped if not s.startswith(WORLD_TOPIC)]
            used.insert(0, f"{WORLD_TOPIC}: the world brief and the backup search were empty, "
                           "so this uses Google News HEADLINES only (check each story before posting)")
            material = (f"===== {WORLD_TOPIC} - Google News headlines, {now:%A %Y-%m-%d} "
                        "(HEADLINES ONLY: state only what a headline says, credit the outlet, "
                        f"add no details) =====\n{headlines}\n\n{material}")
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
        t_in, t_out = shorten_long(drafts)
        tokens_in, tokens_out = tokens_in + t_in, tokens_out + t_out

    os.makedirs(X_FOLDER, exist_ok=True)
    path = os.path.join(X_FOLDER, f"{now:%Y-%m-%d}.md")
    text = render_morning(now, drafts, skipped, used, urls)
    if os.path.exists(path):   # keep an evening thread that is already there
        with open(path) as f:
            old = re.search(re.escape(WRAP_START) + ".*?" + re.escape(WRAP_END), f.read(), re.S)
        if old and "Prices (Yahoo" in old.group(0):
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


def evening(now, drafts_file=None):
    """The evening thread: what happened today, what to watch tomorrow."""
    path = os.path.join(X_FOLDER, f"{now:%Y-%m-%d}.md")
    day_text = open(path).read() if os.path.exists(path) else ""
    numbers = evening_numbers(now)
    tokens_in = tokens_out = 0
    if drafts_file:
        with open(drafts_file) as f:
            drafts = json.load(f)
    else:
        headlines = headlines_text(NEWS_TOPICS + MARKET_TOPICS)
        if not headlines:
            send("X evening thread: no headlines", "Google News could not be reached, so the "
                 "evening thread uses only this morning's briefs. Check the news before posting.",
                 priority="high", tags="warning")
        world = latest_brief(os.path.join("reports", "news"), "world-brief", now.date(), 0)
        context = [day_text[:6000] or "(no morning drafts today)"]
        if world:
            context.append(open(world[1]).read()[:6000])
        prompt = EVENING_PROMPT.format(**date_values(now), numbers=numbers,
                                       calendar=calendar_text(now) or "(not available today)",
                                       regulators=regulators_text() or "(not available today)",
                                       fed=("FED DECISION (official Federal Reserve statement and "
                                            "press conference headlines):\n" + fed) if (fed := fed_text())
                                           else "(No Fed decision today.)",
                                       headlines=headlines or "(none: the free feed failed)",
                                       morning="\n\n".join(context))
        drafts, tokens_in, tokens_out = ask(prompt, EVENING_SCHEMA)
        t_in, t_out = shorten_long(drafts)
        tokens_in, tokens_out = tokens_in + t_in, tokens_out + t_out

    section = render_evening(now, drafts, numbers)
    os.makedirs(X_FOLDER, exist_ok=True)
    if WRAP_START in day_text:
        text = re.sub(re.escape(WRAP_START) + ".*?" + re.escape(WRAP_END),
                      lambda _: section, day_text, flags=re.S)
    else:
        text = (day_text or f"# X drafts - {now:%A %Y-%m-%d}\n\n*No morning drafts today. "
                f"{DISCLAIMER}*\n") + f"\n## 3. Evening thread (post 7-9 PM NY)\n\n{section}\n"
    with open(path, "w") as f:
        f.write(text)
    record = load_record(now.date())
    record.update({"date": f"{now:%Y-%m-%d}",
                   "evening": {"numbers": numbers, "written": f"{now:%Y-%m-%d %H:%M}", **drafts}})
    save_record(now.date(), record)
    finish(path, tokens_in, tokens_out, "X evening thread ready")
    build_dashboard(now)
    return path


def remind(now):
    """7 PM phone reminder to post the evening thread (no AI, no cost)."""
    night = load_record(now.date()).get("evening")
    link = "https://github.com/jayryd7-gif/ai-trading-agent/blob/main/X-DASHBOARD.md"
    if night:
        first = night["thread"][0]["post"].split("\n")[0] if night.get("thread") else ""
        send("7 PM: post tonight's thread", f"Your evening thread is ready on the X dashboard. {first}",
             priority="high", tags="bird", link=link)
    else:
        send("7 PM: evening thread not ready", "The evening thread isn't on the X dashboard yet. "
             "Check GitHub Actions (X Post Drafts), or ask Claude to write it.",
             priority="high", tags="warning", link=link)
    print("Reminder sent." if night else "Reminder sent (thread not ready).")


def main():
    parser = argparse.ArgumentParser(description="Write X post drafts from the daily briefs.")
    parser.add_argument("--evening", "--close", action="store_true",
                        help="write the evening thread (today + tomorrow)")
    parser.add_argument("--drafts", help="use drafts from this JSON file instead of the AI")
    parser.add_argument("--date", help="pretend today is this date (YYYY-MM-DD)")
    parser.add_argument("--dashboard", action="store_true", help="only rebuild X-DASHBOARD.md")
    parser.add_argument("--remind", action="store_true", help="send the 7 PM posting reminder")
    parser.add_argument("--if-missing", action="store_true",
                        help="with --evening: do nothing if tonight's thread is already written")
    args = parser.parse_args()
    now = datetime.now(ZoneInfo("America/New_York")).replace(tzinfo=None)
    if args.date:
        now = datetime.combine(date.fromisoformat(args.date), now.time())
    if args.dashboard:
        build_dashboard(now)
    elif args.remind:
        remind(now)
    elif args.evening and args.if_missing and load_record(now.date()).get("evening"):
        print("Tonight's evening thread is already written, so this run does nothing.")
    else:
        (evening if args.evening else morning)(now, args.drafts)


if __name__ == "__main__":
    sys.exit(main())
