"""
market_brief.py - Agent #1: writes a market brief before a trading session.

Run it like this:
    python agents/market_brief.py nasdaq     (before the New York open)
    python agents/market_brief.py gold       (before the Asia open)

It only RESEARCHES and WRITES. It cannot trade, and it has no broker access.
Each brief is saved in reports/, and its directional lean is added to
reports/bias-log.csv so you can later check how often it was right.

The API key comes from the environment (GitHub supplies it as a secret).
"""

import csv
import os
import re
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import anthropic

from market_data import INSTRUMENTS, get_market_facts

# ---------------- SETTINGS ----------------
MODEL = "claude-sonnet-5-5"   # a stronger model, since this one does research
MAX_SEARCHES = 5              # cap on web searches per run (keeps cost down)
MAX_TOKENS = 2500             # cap on the length of the answer
REPORT_FOLDER = "reports"
# ------------------------------------------

PROMPT = """You are a market research assistant for a day trader who trades
micro Nasdaq futures in the New York session (opens 9:30 AM New York time)
and micro gold futures in the Asia session (opens 9:00 PM New York time).

Today's date is {date}. This brief is for the upcoming {label} session of
{name}.

Here are real numbers pulled by software. Use these for all price levels and
volume. Never invent a level that is not in this block:

{facts}

Use web search ONLY for news and scheduled events. Write a short brief (under
600 words) with these sections:

1. What is driving {name} right now (news and recent moves).
2. Scheduled events before and during the session (releases, central bank
   speakers, big earnings), with times in New York time.
3. Key levels: from the price data, list the previous session high and low
   and any other level worth watching, and say whether the latest price is
   sitting near resistance (a high) or support (a low).
4. Volume: what the volume comparison suggests (strong or weak participation).
5. Directional lean for this session: Bullish, Bearish, or Neutral, with a
   Confidence of Low, Medium, or High. Base it on where price sits relative
   to the previous highs and lows, the volume, and the news. Explain the
   reasoning in 3 to 4 sentences. Say what would make you change the lean.
   If the signals conflict or the price data is unavailable, choose Neutral.
   This is a probability-based lean, not a prediction or a trade instruction.
6. Event risk for this session: Low, Medium, or High, with one sentence why.
7. Sources: the sites you used.

Rules:
- Only state things you found in the price data or your searches. If you
  could not verify something, say so.
- Do not give price targets or tell the trader to buy or sell.
- Use plain language and short sentences.
- Finish with one last line in exactly this format:
  BIAS: Bullish | CONFIDENCE: Medium
  (use Bullish, Bearish, or Neutral, and Low, Medium, or High)
"""


def build_report(client, instrument, facts, today):
    """Ask the model for the brief. Returns (text, input_tokens, output_tokens)."""
    config = INSTRUMENTS[instrument]
    messages = [{"role": "user", "content": PROMPT.format(
        date=today, label=config["label"], name=config["name"], facts=facts)}]
    tools = [{
        "type": "web_search_20250305",
        "name": "web_search",
        "max_uses": MAX_SEARCHES,
    }]

    input_tokens = 0
    output_tokens = 0
    response = None

    # A long search session can pause; keep going a few times if it does.
    for _ in range(4):
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            tools=tools,
            messages=messages,
        )
        input_tokens += response.usage.input_tokens
        output_tokens += response.usage.output_tokens
        if response.stop_reason != "pause_turn":
            break
        messages.append({"role": "assistant", "content": response.content})

    text = "".join(b.text for b in response.content if b.type == "text").strip()
    return text, input_tokens, output_tokens


def read_bias(text):
    """Pull (bias, confidence) out of the last line, or ('Unknown', 'Unknown')."""
    match = re.search(
        r"BIAS:\s*(Bullish|Bearish|Neutral)\s*\|\s*CONFIDENCE:\s*(Low|Medium|High)",
        text, re.IGNORECASE)
    if match:
        return match.group(1).capitalize(), match.group(2).capitalize()
    return "Unknown", "Unknown"


def log_bias(now, instrument, bias, confidence, facts):
    """Add one row to reports/bias-log.csv (creating it if needed)."""
    path = os.path.join(REPORT_FOLDER, "bias-log.csv")
    is_new = not os.path.exists(path)
    price = ""
    match = re.search(r"Latest price: ([\d.]+)", facts)
    if match:
        price = match.group(1)
    with open(path, "a", newline="") as f:
        writer = csv.writer(f)
        if is_new:
            writer.writerow(["date", "time_ny", "instrument", "bias",
                             "confidence", "price_at_brief"])
        writer.writerow([now.strftime("%Y-%m-%d"), now.strftime("%H:%M"),
                         instrument, bias, confidence, price])


def main():
    instrument = sys.argv[1] if len(sys.argv) > 1 else "nasdaq"
    if instrument not in INSTRUMENTS:
        raise SystemExit(f"Unknown instrument '{instrument}'. "
                         f"Use one of: {', '.join(INSTRUMENTS)}")

    now = datetime.now(ZoneInfo("America/New_York")).replace(tzinfo=None)
    today = now.strftime("%Y-%m-%d")

    facts = get_market_facts(instrument, now)
    print(facts, "\n")

    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY on its own
    text, tokens_in, tokens_out = build_report(client, instrument, facts, today)
    if not text:
        raise SystemExit("The model returned no text, so no report was saved.")

    os.makedirs(REPORT_FOLDER, exist_ok=True)
    path = os.path.join(REPORT_FOLDER, f"{today}-{instrument}-brief.md")
    with open(path, "w") as f:
        f.write(f"# {INSTRUMENTS[instrument]['name']} brief - {today}\n\n")
        f.write("*Written by an AI research agent. It can be wrong. "
                "Check anything you plan to act on.*\n\n")
        f.write("## Price data used\n\n```\n" + facts + "\n```\n\n")
        f.write(text + "\n")

    bias, confidence = read_bias(text)
    log_bias(now, instrument, bias, confidence, facts)

    print(f"Saved {path}")
    print(f"Lean: {bias} ({confidence} confidence)")
    print(f"Tokens used: {tokens_in} in, {tokens_out} out")


if __name__ == "__main__":
    main()
