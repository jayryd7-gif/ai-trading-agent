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
  - stock and crypto markets
  - US crypto legislation and regulation
  - war and conflict
  - trade and tariffs
  - a short brief for each country in COUNTRIES, including crypto bills
  - political developments abroad that could affect the economy

It only RESEARCHES and WRITES. It cannot trade, and it has no broker access.
It makes three AI calls: two research calls (with web search) and one short
call that writes the summary at the top. The briefing is saved in
reports/news/.

The API key comes from the environment (GitHub supplies it as a secret).
"""

import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import anthropic

# ---------------- SETTINGS ----------------
MODEL = "claude-sonnet-5-5"
SEARCHES_PER_PART = 10    # cap on web searches for each research call (cost control)
MAX_TOKENS = 3500         # cap on the length of each answer
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
  link (rates, inflation, risk appetite, energy, crypto, and so on). Do not
  predict price moves and do not tell the trader to buy or sell.
- Use plain language and short sentences."""

INTRO = """You are a news and events analyst preparing a morning briefing for a
day trader who trades Nasdaq and gold futures. Today is {weekday}, {date}.
"Overnight" means since 4 PM yesterday, New York time. Use web search to find
current information."""

PART_A = INTRO + """

Cover these sections, in this order. Keep the whole answer under 900 words.

## 1. Politics and policy that could move markets
Overnight developments and today's scheduled items: the White House, Congress,
Treasury, the Federal Reserve (which speakers today, when, and the topic if
known), and the SEC and CFTC (statements, meetings, rulings).

## 2. Economics
Data released overnight, and data due today with the time, the previous
reading, and the forecast if available (inflation, jobs, GDP, PMI, retail
sales, and so on). Any central bank decisions or speakers.

## 3. Government meetings and hearings today
Congressional hearings, central bank meetings, SEC open meetings, and other
official meetings.

## 4. President Trump
What he said or announced overnight that could matter for markets. His
schedule today: each speech, rally, or press event with the time, the place,
and the topics if announced. If no schedule has been announced, say so.

## 5. Stock and crypto markets
Overnight moves in US index futures, Asian and European markets, bitcoin and
ether, and the main reasons given. Major earnings today, with times.

## 6. US crypto legislation and regulation
Bills moving in Congress, SEC or CFTC actions, and anything scheduled today.

""" + SHARED_RULES

PART_B = INTRO + """

Cover these sections, in this order. Keep the whole answer under 900 words.

## 7. War and conflict
Latest developments in active conflicts and anything that could affect energy,
shipping, or markets.

## 8. Trade and tariffs
New tariffs, negotiations, deadlines, and trade deals.

## 9. Country briefs
For each of these countries: {countries}. Give 2 to 3 short bullets on the
biggest political or economic news in the last day. Then add one line on
crypto: any bill or regulation being passed or scheduled there, or "No new
crypto legislation found."

## 10. Other political developments abroad
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


def run_call(client, prompt, use_search):
    """One AI call. Returns (text, input_tokens, output_tokens, was_cut_off)."""
    messages = [{"role": "user", "content": prompt}]
    extra = {}
    if use_search:
        extra["tools"] = [{
            "type": "web_search_20250305",
            "name": "web_search",
            "max_uses": SEARCHES_PER_PART,
        }]

    tokens_in = tokens_out = 0
    response = None
    for _ in range(5):   # a long search session can pause; keep going
        response = client.messages.create(
            model=MODEL, max_tokens=MAX_TOKENS, messages=messages, **extra)
        tokens_in += response.usage.input_tokens
        tokens_out += response.usage.output_tokens
        if response.stop_reason != "pause_turn":
            break
        messages.append({"role": "assistant", "content": response.content})

    text = "".join(b.text for b in response.content if b.type == "text").strip()
    return text, tokens_in, tokens_out, response.stop_reason == "max_tokens"


def build_briefing(client, now):
    """Run the three calls. Returns (markdown_body, total_in, total_out)."""
    values = {"weekday": now.strftime("%A"), "date": now.strftime("%Y-%m-%d")}
    total_in = total_out = 0

    parts = []
    for label, template in (("Part A", PART_A), ("Part B", PART_B)):
        prompt = template.format(countries=", ".join(COUNTRIES), **values)
        text, t_in, t_out, cut = run_call(client, prompt, use_search=True)
        total_in += t_in
        total_out += t_out
        if not text:
            text = f"(This part could not be written: no text came back for {label}.)"
        elif cut:
            text += "\n\n(This part was cut off because it hit the length limit.)"
        parts.append(text)

    if all(p.startswith("(This part could not be written") for p in parts):
        raise SystemExit("Neither research call returned any text, so nothing was saved.")

    try:
        summary, t_in, t_out, _ = run_call(
            client, SUMMARY_PROMPT.format(part_a=parts[0], part_b=parts[1], **values),
            use_search=False)
        total_in += t_in
        total_out += t_out
        if not summary:
            summary = "(The summary could not be written. See the details below.)"
    except Exception as error:
        summary = f"(The summary could not be written: {error}. See the details below.)"

    body = (summary + "\n\n---\n\n# Details: US, politics, and markets\n\n" + parts[0]
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
