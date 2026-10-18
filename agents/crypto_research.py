"""
crypto_research.py - Agent #4: a daily research brief on the crypto market.

Run it like this:
    python agents/crypto_research.py

It covers:
  - top things today
  - coins to research: gainers, trending coins, new alt and meme coins
  - whale watch: large buys, sells, and transfers, and who made them
  - government and regulation: US bills, SEC and CFTC, other countries
  - who is buying bitcoin and adopting crypto payments
  - the next 7 days: unlocks, upgrades, hearings

Before the AI starts, it pulls free live numbers (no API key needed) from
CoinGecko (trending coins, biggest movers) and alternative.me (the Fear and
Greed Index). The AI is told to treat these numbers as facts and to research
why each coin is moving.

It only RESEARCHES and WRITES. It cannot trade, and it has no exchange or
wallet access. It makes ONE AI call with at most SEARCHES web searches, to
keep each run under about $1 (the log shows the estimated cost). The brief
is saved in reports/crypto/.

The API key comes from the environment (GitHub supplies it as a secret).
"""

import json
import os
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

import anthropic

from research_tools import log_cost, run_call

# ---------------- SETTINGS ----------------
SEARCHES = 5              # cap on web searches per run (the main cost control)
MAX_TOKENS = 8000         # cap on the length of the answer
EFFORT = "medium"         # less thinking than the default, to keep the cost down
BUDGET = 1.00             # warn in the log if a run costs more than this (dollars)
CRYPTO_FOLDER = os.path.join("reports", "crypto")
MOVERS_TO_LIST = 12       # how many top gainers to hand the AI
WHALE_MIN_USD = "$10 million"   # what counts as a whale move
# ------------------------------------------

COINGECKO = "https://api.coingecko.com/api/v3"
STABLECOINS = {"usdt", "usdc", "dai", "usde", "fdusd", "tusd", "pyusd", "usds",
               "usd1", "rlusd", "usdd", "susds", "busd", "gusd", "usdp"}


def get_json(url):
    request = urllib.request.Request(url, headers={"User-Agent": "ai-trading-agent"})
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.load(response)


def money(value):
    if value is None:
        return "n/a"
    for size, unit in ((1e9, "B"), (1e6, "M"), (1e3, "K")):
        if abs(value) >= size:
            return f"${value / size:.1f}{unit}"
    return f"${value:,.4g}"


def pct(value):
    return "n/a" if value is None else f"{value:+.1f}%"


def market_snapshot():
    """Free live numbers as plain text. Each piece is skipped if it fails."""
    lines = []

    try:
        fng = get_json("https://api.alternative.me/fng/?limit=1")["data"][0]
        lines.append(f"Fear and Greed Index: {fng['value']} ({fng['value_classification']})")
    except Exception as error:
        lines.append(f"Fear and Greed Index: not available ({error})")

    try:
        coins = get_json(f"{COINGECKO}/coins/markets?vs_currency=usd&order=market_cap_desc"
                         "&per_page=250&page=1&price_change_percentage=24h,7d")
        majors = {c["symbol"]: c for c in coins if c["symbol"] in ("btc", "eth", "sol")}
        for symbol in ("btc", "eth", "sol"):
            c = majors.get(symbol)
            if c:
                lines.append(f"{c['name']}: ${c['current_price']:,.2f}, 24h "
                             f"{pct(c.get('price_change_percentage_24h_in_currency'))}, "
                             f"7d {pct(c.get('price_change_percentage_7d_in_currency'))}")
        movers = [c for c in coins if c["symbol"] not in STABLECOINS
                  and c.get("price_change_percentage_24h_in_currency") is not None]
        movers.sort(key=lambda c: c["price_change_percentage_24h_in_currency"], reverse=True)
        lines += ["", f"Top {MOVERS_TO_LIST} gainers in the last 24h among the 250 largest coins:",
                  "Coin | Price | 24h | 7d | Market cap | 24h volume"]
        for c in movers[:MOVERS_TO_LIST]:
            lines.append(f"{c['name']} ({c['symbol'].upper()}) | ${c['current_price']:,.6g} | "
                         f"{pct(c['price_change_percentage_24h_in_currency'])} | "
                         f"{pct(c.get('price_change_percentage_7d_in_currency'))} | "
                         f"{money(c.get('market_cap'))} | {money(c.get('total_volume'))}")
    except Exception as error:
        lines.append(f"Prices and top gainers: not available ({error})")

    try:
        trending = get_json(f"{COINGECKO}/search/trending")["coins"]
        lines += ["", "Trending searches on CoinGecko right now (often new or meme coins):",
                  "Coin | Market cap rank | 24h"]
        for entry in trending[:15]:
            item = entry["item"]
            change = (item.get("data") or {}).get("price_change_percentage_24h", {}).get("usd")
            lines.append(f"{item['name']} ({item['symbol']}) | "
                         f"{item.get('market_cap_rank') or 'unranked'} | {pct(change)}")
    except Exception as error:
        lines.append(f"Trending coins: not available ({error})")

    return "\n".join(lines)


SHARED_RULES = """Rules:
- Use only what you found in your searches or the live data above. Never
  invent coins, prices, wallet addresses, bills, or quotes.
- All times must be New York time. If something is not confirmed, write
  "(unconfirmed)".
- If you found nothing for a section, write "Nothing found."
- Name the source of each important item briefly, like (CoinDesk) or
  (Whale Alert) or (Arkham).
- Paraphrase in your own words. Do not copy long passages from articles.
- Report what happened. Do not tell the reader to buy or sell, and do not
  predict prices.
- Use plain language and short sentences.
- Start directly with the first section heading. Do not add a title."""

PROMPT = """You are a crypto market researcher writing a short daily brief for
an active trader who wants to spot moves early. Today is {weekday}, {date}.
Use web search for current news. Search efficiently: one search can cover
several topics, so combine them.

LIVE DATA pulled a few minutes ago (treat these numbers as facts; you do not
need to search for prices):
{snapshot}

Write these sections, in this order. Keep the whole brief under 1,100 words.

## Top things today
At most 5 items, most important first. One or two sentences each, ending with
"Why it matters:" and a short phrase.

## Coins to research
A table with columns: Coin | 24h move | Why it is moving | Red flags. Up to 6
coins from the live data's gainers and trending lists, plus any new alt coin
or meme coin pumping hard. Red flags: very new, tiny market cap, low volume,
a few wallets holding most of the supply, or a pump with no news.

## Whale watch
A table with columns: When | Coin | Amount (USD) | Who | Direction. Moves of
at least {whale_min} in the last day (Whale Alert, Lookonchain, Arkham and
similar). Direction: bought, sold, onto an exchange, or off an exchange.
If none were found, write "No whale moves found."

## Government and regulation
US bills (name, what it does, where it stands), SEC and CFTC actions, and
crypto laws in other countries, in the last few days. Include low-profile
bills or amendments if you find them.

## Who is buying and adopting
Countries, governments and companies buying bitcoin, and companies adding
crypto or stablecoin payments.

## Next 7 days
A table with columns: Date | Event | Coin or topic. Token unlocks, upgrades,
hearings, ETF deadlines. If none, write "No scheduled events found."

""" + SHARED_RULES


def build_brief(client, now):
    """One research call. Returns (markdown_body, total_in, total_out)."""
    snapshot = market_snapshot()
    prompt = PROMPT.format(weekday=now.strftime("%A"), date=now.strftime("%Y-%m-%d"),
                           snapshot=snapshot, whale_min=WHALE_MIN_USD)
    text, tokens_in, tokens_out, cut = run_call(client, prompt, use_search=True,
                                                max_searches=SEARCHES, max_tokens=MAX_TOKENS,
                                                effort=EFFORT)
    if not text:
        raise SystemExit("The research call returned no text, so nothing was saved.")
    if cut:
        text += "\n\n(The brief was cut off because it hit the length limit.)"
    body = text + "\n\n---\n\n# Live data used\n\n```\n" + snapshot + "\n```\n"
    return body, tokens_in, tokens_out


def main(now=None):
    now = now or datetime.now(ZoneInfo("America/New_York")).replace(tzinfo=None)
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY on its own

    body, tokens_in, tokens_out = build_brief(client, now)

    os.makedirs(CRYPTO_FOLDER, exist_ok=True)
    path = os.path.join(CRYPTO_FOLDER, f"{now:%Y-%m-%d}-crypto-brief.md")
    with open(path, "w") as f:
        f.write(f"# Crypto research brief - {now:%A %Y-%m-%d}\n\n")
        f.write(f"*Written {now:%Y-%m-%d %H:%M} New York time by an AI research agent. "
                "It can miss things or get them wrong. Small and new coins are very "
                "risky and can lose most of their value fast. This is research, not "
                "advice. Check anything you plan to act on.*\n\n")
        f.write(body)

    print(f"Saved {path}")
    cost = log_cost("crypto-brief")
    print(f"Tokens used: {tokens_in} in, {tokens_out} out")
    print(f"Estimated cost: ${cost:.2f}" + ("  (over budget!)" if cost > BUDGET else ""))
    return path


if __name__ == "__main__":
    main()
