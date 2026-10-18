"""
stock_research.py - Agent #5: a daily research brief on the stock market.

Run it like this:
    python agents/stock_research.py

It covers:
  - top things today and stocks to research (big movers, new stocks)
  - AI and tech, and nuclear and critical minerals
  - earnings: results since yesterday versus estimates, and upcoming dates
    with the EPS and revenue estimates (from Yahoo Finance)
  - smart money: analyst moves, insider buying, and Congress trades

Before the AI starts, it pulls free live numbers with yfinance (no API key
needed): moves for every stock in WATCHLIST, the day's top gainers and most
active stocks, and upcoming earnings dates with analyst estimates. The AI is
told to treat these numbers as facts and to research why things are moving.

It only RESEARCHES and WRITES. It cannot trade, and it has no broker access.
It makes ONE AI call with at most SEARCHES web searches, to keep each run
under about $1 (the log shows the estimated cost). The brief is saved in
reports/stocks/.

The API key comes from the environment (GitHub supplies it as a secret).
"""

import os
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import anthropic

from research_tools import estimated_cost, run_call

# ---------------- SETTINGS ----------------
SEARCHES = 5              # cap on web searches per run (the main cost control)
MAX_TOKENS = 8000         # cap on the length of the answer
EFFORT = "medium"         # less thinking than the default, to keep the cost down
BUDGET = 1.00             # warn in the log if a run costs more than this (dollars)
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

PROMPT = """You are a stock market researcher writing a short daily brief for
an active trader who wants to find opportunities early. Today is {weekday},
{date}. Use web search for current news. Search efficiently: one search can
cover several topics, so combine them.

LIVE DATA pulled a few minutes ago (treat these numbers as facts; the moves
are from the last completed trading day, and the earnings dates and
estimates come from Yahoo Finance, so you do not need to search for them):
{snapshot}

Write these sections, in this order. Keep the whole brief under 1,100 words.

## Top things today
At most 5 items, most important first. One or two sentences each, ending with
"Why it matters:" and a short phrase.

## Stocks to research
A table with columns: Ticker | Theme | Move | Why | Red flags. Up to 6 stocks
from the live data's big movers and watchlist, plus any IPO or new stock
making a big move. Red flags: very small company, heavy dilution, or a move
with no news.

## AI and tech
The 2 to 4 most important news items for AI and chip stocks.

## Nuclear and critical minerals
The 2 to 4 most important news items for nuclear, uranium, rare earths,
lithium, copper and gold miners, including government deals and export limits.

## Earnings
First, notable results since yesterday versus estimates and how the stock
reacted. Then a table of the watchlist earnings in the live data: Date |
Ticker | Before open or after close (if known) | EPS estimate | Revenue estimate.

## Smart money
At most 4 bullets on notable analyst upgrades or downgrades, insider buying,
or trades disclosed by members of Congress in the three themes.

""" + SHARED_RULES


def build_brief(client, now):
    """One research call. Returns (markdown_body, total_in, total_out)."""
    snapshot = market_snapshot(now.date())
    prompt = PROMPT.format(weekday=now.strftime("%A"), date=now.strftime("%Y-%m-%d"),
                           snapshot=snapshot)
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
    cost = estimated_cost()
    print(f"Tokens used: {tokens_in} in, {tokens_out} out")
    print(f"Estimated cost: ${cost:.2f}" + ("  (over budget!)" if cost > BUDGET else ""))
    return path


if __name__ == "__main__":
    main()
