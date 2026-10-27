"""
world_news_brief.py - Agent #3: a morning briefing on news and events that
could move markets, short or long term.

Run it like this:
    python agents/world_news_brief.py

It covers what happened overnight and what is scheduled today:
  - politics and policy (White House, Congress, Fed speakers)
  - the SEC and CFTC (rule votes, open meetings, enforcement) and market-moving
    congressional hearings, from their official feeds
  - economics (data released and due, with times)
  - government meetings and hearings
  - President Trump: what he said, and his schedule (what, when, where)
  - war and conflict
  - trade and tariffs
  - a short brief for each country in COUNTRIES
  - political developments abroad that could affect the economy

Stocks and crypto have their own agents (stock_research.py and
crypto_research.py), so this brief leaves them out and has more room for
everything else.

FREE DATA FIRST (rebuilt 2026-10-26 to cut the cost from about $0.29 to about
$0.10 a run). Two free feeds (news_feed.py) go into the prompt:
  - Google News headlines: the President, Congress, the Fed, tariffs, wars and
    other countries, from the last 24 hours
  - an economic calendar: every important data release and central bank
    decision today, tomorrow and later this week, with times, forecasts and
    previous values
So the AI does not spend web searches finding the news or the schedule. It
uses its few searches (SEARCHES) only to get the details of the biggest
stories. Most of the old cost was the AI reading pages of search results, so
fewer searches is what makes it cheaper. If the searches fail, the brief still
reports what the headlines say, credited to each outlet, so it is never empty.

It only RESEARCHES and WRITES. It cannot trade, and it has no broker access.
It makes ONE AI call (the log shows the estimated cost). It runs every day;
weekend runs are shorter. The briefing is saved in reports/news/.

The API key comes from the environment (GitHub supplies it as a secret).
"""

import os
from datetime import datetime
from zoneinfo import ZoneInfo

import anthropic

from research_tools import log_cost, run_call
from news_feed import calendar_text, fed_text, headlines_text, regulators_text
from notify import send

# ---------------- SETTINGS ----------------
SEARCHES = 2              # web searches per run, only for the biggest stories (main cost control)
WEEKEND_SEARCHES = 1      # Saturday and Sunday: quieter news, a lighter run
MAX_TOKENS = 8000         # cap on the length of the answer
EFFORT = "medium"         # less thinking than the default, to keep the cost down
BUDGET = 1.00             # warn in the log if a run costs more than this (dollars)
NEWS_FOLDER = os.path.join("reports", "news")

# Countries to give a short brief for. More countries = more cost and time.
COUNTRIES = ["China", "European Union", "United Kingdom", "Japan", "India",
             "Russia", "Canada"]
# ------------------------------------------

SHARED_RULES = """Rules:
- Use only what is in the calendar, the headlines, or your searches. Never
  invent events, quotes, times, or places.
- All times must be New York time. If a time or place is not officially
  announced, write "(unconfirmed)".
- If you found nothing for a section, write "Nothing found."
- Report what happened or was said. Do not say whether it is good or bad, and
  do not take sides.
- Paraphrase in your own words. Do not copy long passages from articles.
- Name the source of each important item briefly, like (Reuters).
- For important items add a short "Why it matters:" phrase naming the market
  link (rates, inflation, risk appetite, energy, the dollar, and so on). Do not
  predict price moves and do not tell the trader to buy or sell.
- Start directly with the first section heading. Do not add a title.
- Use plain language and short sentences."""

PROMPT = """You are a news and events analyst preparing a short morning briefing
for a day trader who trades Nasdaq and gold futures. Today is {weekday},
{date}. "Overnight" means since 4 PM yesterday, New York time. Do not cover
stock or crypto markets; other briefs handle those.

You are given two free sources below: an ECONOMIC CALENDAR and NEWS HEADLINES.
Build the briefing from them first. Then use web search ONLY to get the facts
behind the one or two stories most likely to move markets or the economy
today (for example a war, a tariff move, a Fed or Treasury surprise, or
something the President said). You have at most {searches} search(es):
combine topics in one search, and never search for the schedule (the
calendar already has it) or for stories the headlines already make clear.
For stories you did not search, report what the headline says, credited to
its outlet, and add "(headline only)". Do not add details a headline does
not state.

Write these sections, in this order. Keep the whole briefing under 1,300 words.

## Top things for today
At most 5 items, most important first. One or two sentences each, ending with
"Why it matters:" and a short phrase.

## Today's schedule (New York time)
A table with columns: Time | Event | Who or where | Confirmed? Sorted by time.
Take economic data and central bank events from the ECONOMIC CALENDAR (with
the forecast and previous reading); they are confirmed. Add hearings and
President Trump's events from the headlines or your searches. Then one line
"Coming up this week:" with the calendar's later high-impact events. If there
are none today, write "No scheduled events found."

## Event risk today
Low, Medium, or High, with one sentence explaining why. Write the word on its
own right after the heading, like: "High - ...".

## Politics and policy
The White House, Congress (including bills that could affect the economy),
Treasury, the Federal Reserve, executive orders, and what President Trump said
overnight.

## Economics
Data released overnight and what it showed.

## SEC, CFTC and hearings
SEC and CFTC actions (rule votes, open meetings, roundtables, enforcement,
ETF decisions) and congressional hearings that could move markets (Fed,
Treasury, SEC or bank officials testifying; Senate Banking and House
Financial Services). Include upcoming hearings and meetings with their date
and time if known. Use the REGULATORS section below. If there are none,
write "Nothing found."

## War, trade and tariffs
Active conflicts that could affect energy, shipping or markets, and new
tariffs, negotiations, deadlines or trade deals.

## Country briefs
For each of these: {countries}. One or two short bullets on the biggest
political or economic news in the last day.

""" + SHARED_RULES


def is_empty(text):
    """True when the search failed and the top section says "Nothing found"."""
    import re
    top = re.search(r"## Top things[^\n]*\n+\s*(.*)", text)
    return bool(top and top.group(1).lower().startswith("nothing found"))


def build_briefing(client, now):
    """One research call. Returns (markdown_body, total_in, total_out)."""
    weekend = now.weekday() >= 5
    prompt = PROMPT.format(weekday=now.strftime("%A"), date=now.strftime("%Y-%m-%d"),
                           countries=", ".join(COUNTRIES),
                           searches=WEEKEND_SEARCHES if weekend else SEARCHES)
    calendar = calendar_text(now)
    prompt += ("\n\nECONOMIC CALENDAR (free feed, New York time; official release times):\n"
               + (calendar or "(The calendar could not be reached today. Use one search for "
                              "today's US economic calendar.)"))
    fed = fed_text()
    if fed:
        prompt += ("\n\nFED DECISION (the Fed announced a rate decision in the last day). Add a "
                   "section \"## What the Fed said\" right after \"Top things for today\": short "
                   "bullets for the decision and the vote (with any dissents), the key lines on "
                   "inflation, jobs and the economy, and what the chair signaled at the press "
                   "conference (from the headlines, credited to the outlet). Quote at most a few "
                   "words.\n" + fed)
    regulators = regulators_text()
    prompt += ("\n\nREGULATORS AND HEARINGS (official SEC and CFTC press releases, and hearing "
               "headlines):\n" + (regulators or "(These feeds could not be reached today.)"))
    headlines = headlines_text()
    prompt += ("\n\nNEWS HEADLINES (Google News, last 24 hours, free feed). Never write "
               "\"Nothing found\" for a section these headlines cover.\n"
               + (headlines or "(The headline feed could not be reached today. Use your "
                               "searches for the most important overnight news.)"))
    if weekend:
        prompt += ("\n\nIt is the weekend: markets are closed. Focus on what happened "
                   "since Friday's close that could matter when markets reopen, and keep "
                   "the whole briefing under 700 words.")
    tokens_in = tokens_out = 0
    for attempt in range(2):   # politics must not be missing: one retry if it comes back empty
        text, t_in, t_out, cut = run_call(client, prompt, use_search=True,
                                          max_searches=WEEKEND_SEARCHES if weekend else SEARCHES,
                                          max_tokens=MAX_TOKENS, effort=EFFORT)
        tokens_in += t_in
        tokens_out += t_out
        if text and not is_empty(text):
            break
        print(f"Attempt {attempt + 1}: the briefing came back empty" +
              (", trying once more." if attempt == 0 else "."))
    if not text:
        raise SystemExit("The research call returned no text, so nothing was saved.")
    if cut:
        text += "\n\n(The briefing was cut off because it hit the length limit.)"
    return text + "\n", tokens_in, tokens_out


def main(now=None):
    now = now or datetime.now(ZoneInfo("America/New_York")).replace(tzinfo=None)
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY on its own

    body, tokens_in, tokens_out = build_briefing(client, now)

    os.makedirs(NEWS_FOLDER, exist_ok=True)
    path = os.path.join(NEWS_FOLDER, f"{now:%Y-%m-%d}-world-brief.md")
    with open(path, "w") as f:
        f.write(f"# World news brief - {now:%A %Y-%m-%d}\n\n")
        f.write(f"*Written {now:%Y-%m-%d %H:%M} New York time by an AI news agent. "
                "It can miss things or get them wrong, and times and places can "
                "change. Check anything you plan to act on.*\n\n")
        f.write(body)

    print(f"Saved {path}")
    if is_empty(body):
        send("World brief came back EMPTY", "The news search failed twice, so today's world "
             "and politics news is missing. The X drafts agent will search on its own.",
             priority="high", tags="warning",
             link=f"https://github.com/jayryd7-gif/ai-trading-agent/blob/main/{path}")
    import re
    first = re.search(r"^1\.\s*(.+)$", body, re.M)
    risk = re.search(r"Event risk today.{0,60}?\b(Low|Medium|High)\b", body, re.S)
    send(f"World brief: event risk {risk.group(1) if risk else 'n/a'}",
         (first.group(1)[:300] if first else "Today's world brief is ready."), priority="low",
         tags="earth_americas",
         link=f"https://github.com/jayryd7-gif/ai-trading-agent/blob/main/{path}")
    cost = log_cost("world-brief")
    print(f"Tokens used: {tokens_in} in, {tokens_out} out")
    print(f"Estimated cost: ${cost:.2f}" + ("  (over budget!)" if cost > BUDGET else ""))
    return path


if __name__ == "__main__":
    main()
