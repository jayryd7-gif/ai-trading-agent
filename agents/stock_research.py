"""
stock_research.py - Agent #5: a daily research brief on the stock market.

Run it like this:
    python agents/stock_research.py

It covers:
  - what is pumping: the day's top gainers, small caps, and new stocks (IPOs)
  - three themes: AI and tech, nuclear and uranium, and critical minerals
  - earnings: results since yesterday versus estimates, and upcoming dates
    with the EPS and revenue estimates
  - analyst upgrades and downgrades on the theme stocks
  - insider buying and trades disclosed by members of Congress
  - government contracts and policy that affect the themes
  - company events coming up in the next 7 days

Before the AI starts, it pulls free live numbers with yfinance (no API key
needed): moves for every stock in WATCHLIST, the day's top gainers and most
active stocks, and upcoming earnings dates with analyst estimates. The AI is
told to treat these numbers as facts and to research why things are moving.

It only RESEARCHES and WRITES. It cannot trade, and it has no broker access.
It makes three AI calls: two research calls (with web search) and one short
call that writes the summary at the top. The brief is saved in reports/stocks/.

The API key comes from the environment (GitHub supplies it as a secret).
"""

import os
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import anthropic

from research_tools import research_parts, write_summary

# ---------------- SETTINGS ----------------
SEARCHES_PER_PART = 8     # cap on web searches for each research call (cost control)
MAX_TOKENS = 6000         # cap on the length of each answer
STOCK_FOLDER = os.path.join("reports", "stocks")
EARNINGS_WITHIN_DAYS = 14 # list watchlist earnings due within this many days
SCREEN_COUNT = 10         # how many stocks to take from each Yahoo screen

# The stocks to track for each theme. Add or remove tickers freely.
WATCHLIST = {
    "AI and tech": ["NVDA", "MSFT", "GOOGL", "META", "AMZN", "AAPL", "AMD", "AVGO",
                    "TSM", "MU", "ORCL", "PLTR", "ARM", "SMCI", "CRWV", "TSLA"],
    "Nuclear and uranium": ["CCJ", "CEG", "VST", "OKLO", "SMR", "NNE", "LEU", "BWXT",
                            "UEC", "URA"],
    "Critical minerals and mining": ["MP", "USAR", "ALB", "SQM", "LAC", "FCX", "SCCO",
                                     "NEM", "REMX"],
}
SCREENS = {"day_gainers": "Top gainers today (large and mid caps)",
           "small_cap_gainers": "Top small-cap gainers",
           "most_actives": "Most active by volume"}
# ------------------------------------------


def pct(value):
    return "n/a" if value is None else f"{value:+.1f}%"


def money(value):
    if not value:
        return "n/a"
    for size, unit in ((1e12, "T"), (1e9, "B"), (1e6, "M")):
        if abs(value) >= size:
            return f"${value / size:.1f}{unit}"
    return f"${value:,.0f}"


def watchlist_moves(yf):
    tickers = [t for group in WATCHLIST.values() for t in group]
    closes = yf.download(tickers, period="10d", interval="1d", progress=False,
                         auto_adjust=True)["Close"]
    lines = []
    for theme, group in WATCHLIST.items():
        lines += ["", f"{theme}: Ticker | Last close | 1 day | 5 days"]
        for t in group:
            series = closes[t].dropna() if t in closes else []
            if len(series) < 6:
                lines.append(f"{t} | no data")
                continue
            last = series.iloc[-1]
            day = (last / series.iloc[-2] - 1) * 100
            week = (last / series.iloc[-6] - 1) * 100
            lines.append(f"{t} | ${last:,.2f} | {pct(day)} | {pct(week)}")
    return lines


def screen_lines(yf):
    lines = []
    for key, title in SCREENS.items():
        try:
            quotes = yf.screen(key, count=SCREEN_COUNT)["quotes"]
        except Exception as error:
            lines += ["", f"{title}: not available ({error})"]
            continue
        lines += ["", f"{title}: Ticker | Name | Change | Price | Market cap"]
        for q in quotes:
            lines.append(f"{q.get('symbol')} | {q.get('shortName', '')} | "
                         f"{pct(q.get('regularMarketChangePercent'))} | "
                         f"${q.get('regularMarketPrice', 0):,.2f} | {money(q.get('marketCap'))}")
    return lines


def earnings_lines(yf, today):
    """Watchlist earnings due soon, with analyst estimates."""
    rows = []
    for t in sorted({t for group in WATCHLIST.values() for t in group}):
        try:
            cal = yf.Ticker(t).calendar or {}
        except Exception:
            continue
        dates = [d for d in cal.get("Earnings Date", []) if isinstance(d, date)]
        if not dates or not (today <= dates[0] <= today + timedelta(days=EARNINGS_WITHIN_DAYS)):
            continue
        eps = cal.get("Earnings Average")
        rows.append((dates[0], f"{dates[0]} | {t} | "
                     f"{'n/a' if eps is None else f'${eps:.2f}'} | "
                     f"{money(cal.get('Revenue Average'))}"))
    lines = ["", f"Watchlist earnings in the next {EARNINGS_WITHIN_DAYS} days "
             "(Yahoo Finance consensus): Date | Ticker | EPS estimate | Revenue estimate"]
    lines += [row for _, row in sorted(rows)] or ["None found in the watchlist."]
    return lines


def market_snapshot(today):
    """Free live numbers as plain text. Each piece is skipped if it fails."""
    try:
        import yfinance as yf  # imported here so the rest of the file loads without it
    except ImportError:
        return "Live data not available: yfinance is not installed."
    lines = []
    for label, step in (("Watchlist moves", lambda: watchlist_moves(yf)),
                        ("Screens", lambda: screen_lines(yf)),
                        ("Earnings", lambda: earnings_lines(yf, today))):
        try:
            lines += step()
        except Exception as error:
            lines += ["", f"{label}: not available ({error})"]
    return "\n".join(lines).strip()


SHARED_RULES = """Rules:
- Use only what you found in your searches or the live data above. Never
  invent tickers, prices, estimates, dates, or quotes.
- All times must be New York time. Say "before the open" or "after the close"
  for earnings when known. If something is not confirmed, write "(unconfirmed)".
- If you found nothing for a section, write "Nothing found."
- Name the source of each important item briefly, like (Reuters) or (SEC filing).
- Paraphrase in your own words. Do not copy long passages from articles.
- Report what happened. Do not tell the reader to buy or sell, and do not
  predict prices.
- Use plain language and short sentences.
- Start directly with the first section heading. Do not add a title."""

INTRO = """You are a stock market researcher writing a daily brief for an
active trader who wants to find opportunities early. Today is {weekday},
{date}. Use web search to find current information.

LIVE DATA pulled a few minutes ago (treat these numbers as facts; the moves
are from the last completed trading day):
{snapshot}
"""

PART_A = INTRO + """
Cover these sections, in this order. Keep the whole answer under 1400 words.

## 1. Market overview
Two or three sentences: how the major US indexes and futures are doing and
the main reasons given.

## 2. What is pumping
For the biggest movers in the live data screens, and any other stock you find
up sharply on news: what the company does, why it moved (earnings, a deal, a
contract, an upgrade, a short squeeze, social media hype), and its market cap.
Add a "Red flags:" note for very small companies, stocks with heavy share
dilution, or moves with no news. Cover at most 8 stocks. Then list recent IPOs
(last 2 weeks) and IPOs expected in the next 2 weeks, with dates.

## 3. AI and tech
The most important news for AI and tech stocks: chip demand, data center
spending, new AI models and products, big deals and partnerships, export
controls, and any big move in the watchlist and why.

## 4. Nuclear and uranium
Reactor approvals and restarts, small modular reactor news, power deals with
tech companies, uranium prices and supply, and government support.

## 5. Critical minerals and mining
Rare earths, lithium, copper, nickel, cobalt, and gold: prices, supply deals,
export limits (especially from China), US government stakes or funding, and
new mines.

""" + SHARED_RULES

PART_B = INTRO + """
Cover these sections, in this order. Keep the whole answer under 1400 words.

## 6. Earnings results since yesterday
Notable companies that reported since yesterday morning: earnings per share
and revenue versus estimates, guidance, and how the stock reacted. Focus on
the three themes and on large companies.

## 7. Earnings calendar for the next 7 days
Companies in the three themes, plus the largest US companies, that report in
the next 7 days: date, before the open or after the close, EPS estimate, and
revenue estimate. Use the estimates in the live data when they are there.
Add what the market will watch most in each report, in a few words.

## 8. Analyst moves
Upgrades, downgrades, initiations, and big price target changes on stocks in
the three themes in the last day.

## 9. Insider and Congress trades
Notable insider buying or selling (Form 4 filings) in the three themes, and
stock trades disclosed by members of Congress in the last few days. Give who,
what, how much, and when.

## 10. Government and policy
Government contracts, funding, stakes, export controls, tariffs, and
regulation that affect AI, chips, nuclear, or minerals.

## 11. Coming up
Company events in the next 7 days, such as product launches, investor days,
and big conferences, with dates.

""" + SHARED_RULES

SUMMARY_PROMPT = """Below are two research sections written today for a stock
trader. Today is {weekday}, {date}.

Write four short parts, using only the information below. Do not add any new
facts.

## Top things today
At most 6 items, most important first. One or two sentences each, ending with
"Why it matters:" and a short phrase.

## Stocks to research
A table with columns: Ticker | Theme | Move | Why | Red flags. At most 8 rows.
If there are none, write "No stocks stood out today."

## Earnings this week
A table with columns: Date | Ticker | Before open or after close | EPS estimate |
Revenue estimate. Sorted by date. If there are none, write "No earnings found."

## Smart money
At most 5 bullets on notable insider, Congress, or analyst moves.

Do not tell the reader to buy or sell, and do not predict prices.

SECTIONS FOLLOW

{part_a}

{part_b}
"""


def build_brief(client, now):
    """Run the three calls. Returns (markdown_body, total_in, total_out)."""
    snapshot = market_snapshot(now.date())
    values = {"weekday": now.strftime("%A"), "date": now.strftime("%Y-%m-%d"),
              "snapshot": snapshot}
    parts, total_in, total_out = research_parts(
        client, [("Part A", PART_A), ("Part B", PART_B)], values,
        SEARCHES_PER_PART, MAX_TOKENS)

    summary, t_in, t_out = write_summary(
        client, SUMMARY_PROMPT.format(part_a=parts[0], part_b=parts[1], **values),
        MAX_TOKENS)
    total_in += t_in
    total_out += t_out

    body = (summary
            + "\n\n---\n\n# Details: movers and themes\n\n" + parts[0]
            + "\n\n---\n\n# Details: earnings, smart money, and policy\n\n" + parts[1]
            + "\n\n---\n\n# Live data used\n\n```\n" + snapshot + "\n```\n")
    return body, total_in, total_out


def main(now=None):
    now = now or datetime.now(ZoneInfo("America/New_York")).replace(tzinfo=None)
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY on its own

    body, tokens_in, tokens_out = build_brief(client, now)

    os.makedirs(STOCK_FOLDER, exist_ok=True)
    path = os.path.join(STOCK_FOLDER, f"{now:%Y-%m-%d}-stock-brief.md")
    with open(path, "w") as f:
        f.write(f"# Stock research brief - {now:%A %Y-%m-%d}\n\n")
        f.write(f"*Written {now:%Y-%m-%d %H:%M} New York time by an AI research agent. "
                "It can miss things or get them wrong, and earnings dates and "
                "estimates change. This is research, not advice. Check anything you "
                "plan to act on.*\n\n")
        f.write(body)

    print(f"Saved {path}")
    print(f"Tokens used: {tokens_in} in, {tokens_out} out")
    return path


if __name__ == "__main__":
    main()
