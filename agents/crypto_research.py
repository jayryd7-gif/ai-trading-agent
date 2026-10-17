"""
crypto_research.py - Agent #4: a daily research brief on the crypto market.

Run it like this:
    python agents/crypto_research.py

It covers:
  - what is pumping: top gainers, trending coins, new alt coins and meme coins
  - whale activity: large buys, sells, and transfers, and who made them
  - money flows: bitcoin and ether ETF flows, stablecoin supply
  - government and regulation: US bills (including low-profile ones), SEC and
    CFTC actions, and crypto laws in other countries
  - adoption: countries and companies buying bitcoin, and companies adding
    crypto or stablecoin payments
  - risks and catalysts: hacks, token unlocks, and scheduled events

Before the AI starts, it pulls free live numbers (no API key needed) from
CoinGecko (trending coins, biggest movers) and alternative.me (the Fear and
Greed Index). The AI is told to treat these numbers as facts and to research
why each coin is moving.

It only RESEARCHES and WRITES. It cannot trade, and it has no exchange or
wallet access. It makes three AI calls: two research calls (with web search)
and one short call that writes the summary at the top. The brief is saved in
reports/crypto/.

The API key comes from the environment (GitHub supplies it as a secret).
"""

import json
import os
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

import anthropic

from research_tools import research_parts, write_summary

# ---------------- SETTINGS ----------------
SEARCHES_PER_PART = 8     # cap on web searches for each research call (cost control)
MAX_TOKENS = 6000         # cap on the length of each answer
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
- Use plain language and short sentences."""

INTRO = """You are a crypto market researcher writing a daily brief for an
active trader who wants to spot moves early. Today is {weekday}, {date}.
"Last day" means the last 24 hours. Use web search to find current information.

LIVE DATA pulled a few minutes ago (treat these numbers as facts):
{snapshot}
"""

PART_A = INTRO + """
Cover these sections, in this order. Keep the whole answer under 1300 words.

## 1. Market overview
Two or three sentences: how bitcoin, ether, and the overall market moved, the
Fear and Greed reading, and the main reasons given.

## 2. What is pumping
For the biggest gainers and trending coins in the live data, and any other alt
coin or meme coin you find pumping hard in the last day (including brand-new
launches on Solana, Base, or other chains): what the coin is, why it is
moving (news, listing, partnership, social media hype, a famous account
posting about it), how long it has existed, and its market cap and volume.
Add a "Red flags:" note when you see any: very new, very small market cap,
low liquidity, a few wallets holding most of the supply, anonymous team,
unlocked team tokens, or a pump with no news. Cover at most 8 coins, most
notable first.

## 3. Whale activity
Large purchases, sales, and transfers worth at least {whale_min} in the last
day, from sources such as Whale Alert, Lookonchain, Arkham, Santiment, or
on-chain news. For each: the coin, the amount and its dollar value, when it
happened, who it was if known (a fund, an exchange, a known trader, a
government, or an unknown wallet), and the direction (bought, sold, moved to
an exchange, or moved off an exchange). Note when a whale bought a small coin
early, before it pumped. Note that moves onto exchanges often come before
selling and moves off exchanges often mean holding, but do not treat this as
certain.

## 4. Money flows
Spot bitcoin and ether ETF net flows from the last trading day, any large
stablecoin minting or burning, and any notable fund or treasury flows.

""" + SHARED_RULES

PART_B = INTRO + """
Cover these sections, in this order. Keep the whole answer under 1300 words.

## 5. US government and regulation
What Congress, the White House, the Treasury, the SEC, and the CFTC said or did
about crypto in the last day, and what is scheduled. For each bill: its name
and number, what it would do, and where it stands (introduced, in committee,
passed one chamber, signed). Look for low-profile bills, amendments added to
larger bills, and quiet rule changes that got little news coverage, and say
where you found them (for example congress.gov or the Federal Register). Also
cover state-level bitcoin reserve bills.

## 6. Other countries
Crypto laws, bans, approvals, central bank digital currency news, and tax
changes in other countries in the last few days.

## 7. Who is buying bitcoin
Countries, governments, and public companies buying bitcoin or adding it to
reserves or treasuries: who, how much, when, and their total holdings if
reported. Include sovereign wealth funds and pension funds.

## 8. Adoption and payments
Companies adding crypto or stablecoin payments, banks and payment firms
launching crypto services, and big partnerships or exchange listings.

## 9. Risks
Hacks, exploits, rug pulls, exchange problems, lawsuits, and enforcement
actions in the last day.

## 10. Coming up
Scheduled events in the next 7 days that could move crypto: large token
unlocks (coin, amount, dollar value, date), network upgrades, votes or
hearings, ETF decision deadlines, and big conferences. Give dates.

""" + SHARED_RULES

SUMMARY_PROMPT = """Below are two research sections written today for a crypto
trader. Today is {weekday}, {date}.

Write four short parts, using only the information below. Do not add any new
facts.

## Top things today
At most 6 items, most important first. One or two sentences each, ending with
"Why it matters:" and a short phrase.

## Coins to research
A table with columns: Coin | 24h move | Why it is moving | Red flags. Include at
most 8 coins from the "What is pumping" section. If there are none, write
"No coins stood out today."

## Whale watch
A table with columns: When | Coin | Amount (USD) | Who | Direction. At most 8
rows, largest first. If there are none, write "No whale moves found."

## Next 7 days
A table with columns: Date | Event | Coin or topic. Sorted by date. If there
are none, write "No scheduled events found."

Do not tell the reader to buy or sell, and do not predict prices.

SECTIONS FOLLOW

{part_a}

{part_b}
"""


def build_brief(client, now):
    """Run the three calls. Returns (markdown_body, total_in, total_out)."""
    snapshot = market_snapshot()
    values = {"weekday": now.strftime("%A"), "date": now.strftime("%Y-%m-%d"),
              "snapshot": snapshot, "whale_min": WHALE_MIN_USD}
    parts, total_in, total_out = research_parts(
        client, [("Part A", PART_A), ("Part B", PART_B)], values,
        SEARCHES_PER_PART, MAX_TOKENS)

    summary, t_in, t_out = write_summary(
        client, SUMMARY_PROMPT.format(part_a=parts[0], part_b=parts[1], **values),
        MAX_TOKENS)
    total_in += t_in
    total_out += t_out

    body = (summary
            + "\n\n---\n\n# Details: market, coins, and whales\n\n" + parts[0]
            + "\n\n---\n\n# Details: government, adoption, and what is coming\n\n" + parts[1]
            + "\n\n---\n\n# Live data used\n\n```\n" + snapshot + "\n```\n")
    return body, total_in, total_out


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
    print(f"Tokens used: {tokens_in} in, {tokens_out} out")
    return path


if __name__ == "__main__":
    main()
