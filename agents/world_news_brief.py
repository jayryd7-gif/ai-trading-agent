"""
world_news_brief.py - Agent #3: a morning briefing on news and events that
could move markets, short or long term.

Run it like this:
    python agents/world_news_brief.py

It covers what happened overnight and what is scheduled today:
  - politics and policy (White House, Congress, Fed speakers, SEC and CFTC)
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

It only RESEARCHES and WRITES. It cannot trade, and it has no broker access.
It makes three AI calls: two research calls (with web search) and one short
call that writes the summary at the top. The briefing is saved in
reports/news/.

The API key comes from the environment (GitHub supplies it as a secret).
"""

import os
from datetime import datetime
from zoneinfo import ZoneInfo

import anthropic

from research_tools import research_parts, write_summary

# ---------------- SETTINGS ----------------
SEARCHES_PER_PART = 5   # cap on web searches for each research call (cost control)
MAX_TOKENS = 5000         # cap on the length of each answer
NEWS_FOLDER = os.path.join("reports", "news")

# Countries to give a short brief for. More countries = more cost and time.
COUNTRIES = ["China", "European Union", "United Kingdom", "Japan", "India",
             "Russia", "Canada"]
# ------------------------------------------

SHARED_RULES = """Rules:
- Use only what you found in your searches. Never invent events, quotes,
  times, or places.
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
- Use plain language and short sentences."""

INTRO = """You are a news and events analyst preparing a morning briefing for a
day trader who trades Nasdaq and gold futures. Today is {weekday}, {date}.
"Overnight" means since 4 PM yesterday, New York time. Use web search to find
current information."""

PART_A = INTRO + """

Cover these sections, in this order. Keep the whole answer under 1000 words.
Do not cover stock or crypto markets; other briefs handle those.

## 1. Politics and policy that could move markets
Overnight developments and today's scheduled items: the White House, Congress,
Treasury, the Federal Reserve (which speakers today, when, and the topic if
known), and regulators. Include bills moving in Congress that could affect the
economy, and executive orders.

## 2. Economics
Data released overnight, and data due today with the time, the previous
reading, and the forecast if available (inflation, jobs, GDP, PMI, retail
sales, and so on). Any central bank decisions or speakers.

## 3. Government meetings and hearings today
Congressional hearings, central bank meetings, and other official meetings,
with times.

## 4. President Trump
What he said or announced overnight that could matter for markets. His
schedule today: each speech, rally, or press event with the time, the place,
and the topics if announced. If no schedule has been announced, say so.

""" + SHARED_RULES

PART_B = INTRO + """

Cover these sections, in this order. Keep the whole answer under 1100 words.
Do not cover stock or crypto markets; other briefs handle those.

## 5. War and conflict
Latest developments in active conflicts and anything that could affect energy,
shipping, or markets.

## 6. Trade and tariffs
New tariffs, negotiations, deadlines, and trade deals.

## 7. Country briefs
For each of these countries: {countries}. Give 3 to 4 short bullets on the
biggest political or economic news in the last day.

## 8. Other political developments abroad
Elections, leadership changes, sanctions, central bank moves, or energy
decisions elsewhere that could affect the global economy.

""" + SHARED_RULES

SUMMARY_PROMPT = """Below are two research sections written this morning for a
day trader who trades Nasdaq and gold futures. Today is {weekday}, {date}.

Write three short parts, using only the information below. Do not add any new
facts.

## Top things for today
At most 5 items, most important first. One or two sentences each, ending with
"Why it matters:" and a short phrase.

## Today's schedule (New York time)
A table with columns: Time | Event | Who or where | Confirmed? Sorted by time.
Include only scheduled items that appear in the sections. If there are none,
write "No scheduled events found."

## Event risk today
Low, Medium, or High, with one sentence explaining why. Write the word on its
own right after the heading, like: "High - ...".

Do not predict price moves and do not tell the trader to buy or sell.

SECTIONS FOLLOW

{part_a}

{part_b}
"""


def build_briefing(client, now):
    """Run the three calls. Returns (markdown_body, total_in, total_out)."""
    values = {"weekday": now.strftime("%A"), "date": now.strftime("%Y-%m-%d"),
              "countries": ", ".join(COUNTRIES)}
    parts, total_in, total_out = research_parts(
        client, [("Part A", PART_A), ("Part B", PART_B)], values,
        SEARCHES_PER_PART, MAX_TOKENS)

    summary, t_in, t_out = write_summary(
        client, SUMMARY_PROMPT.format(part_a=parts[0], part_b=parts[1], **values),
        MAX_TOKENS)
    total_in += t_in
    total_out += t_out

    body = (summary + "\n\n---\n\n# Details: US politics and the economy\n\n" + parts[0]
            + "\n\n---\n\n# Details: the world\n\n" + parts[1] + "\n")
    return body, total_in, total_out


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
    print(f"Tokens used: {tokens_in} in, {tokens_out} out")
    return path


if __name__ == "__main__":
    main()
