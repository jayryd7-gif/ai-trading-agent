"""
news_feed.py - Free headlines from Google News and a free economic calendar
(no keys, no cost).

    from news_feed import headlines_text, calendar_text
    print(headlines_text())
    print(calendar_text(now))

Used as a safety net so politics and world news are never empty: the world
brief gets these headlines as leads (and can report them if its web search
fails), and the X drafts agent uses them as its last fallback. Headlines only:
a headline plus its outlet and time, no article text.

The economic calendar (Forex Factory's free weekly feed) lists every data
release and central bank event with its time, forecast, previous value and
expected market impact. The world brief uses it for its schedule, so it does
not need to spend web searches finding the schedule.

This file is not an agent and does nothing on its own.
"""

from datetime import datetime, timedelta, timezone
import os
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo

FEED = "https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"

# (topic, Google News search). "when:1d" keeps it to the last day.
TOPICS = [
    ("President Trump and the White House", "Trump OR \"White House\" when:1d"),
    ("US politics and Congress", "Congress OR Senate OR \"Supreme Court\" OR midterms when:1d"),
    ("Economy, the Fed and tariffs", "\"Federal Reserve\" OR inflation OR tariffs OR economy when:1d"),
    ("World", "China OR Russia OR Ukraine OR Iran OR Israel OR Europe OR Canada when:1d"),
]
# Extra topics for the evening thread, which has no stock or crypto brief yet.
MARKET_TOPICS = [
    ("Stock market today", "\"stock market\" OR \"Wall Street\" OR \"S&P 500\" OR Nasdaq when:1d"),
    ("Crypto today", "bitcoin OR crypto OR ethereum when:1d"),
    ("Tomorrow and this week", "\"week ahead\" OR \"what to watch\" OR tomorrow stocks earnings when:1d"),
]
PER_TOPIC = 6


def fetch(query, count=PER_TOPIC):
    """[(title, outlet, New York time text)] for one search, newest first."""
    url = FEED.format(q=urllib.parse.quote(query))
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=20) as response:
        root = ET.fromstring(response.read())
    items = []
    for item in root.findall(".//item"):
        title = item.findtext("title") or ""
        outlet = item.findtext("source") or ""
        if outlet and title.endswith(" - " + outlet):
            title = title[: -len(" - " + outlet)]
        try:
            when = parsedate_to_datetime(item.findtext("pubDate"))
        except (TypeError, ValueError):
            continue
        items.append((when, title.strip(), outlet))
    items.sort(reverse=True)
    return [(t, o, f"{w.astimezone(ZoneInfo('America/New_York')):%a %b %d %I:%M %p} NY")
            for w, t, o in items[:count]]


def headlines_text(topics=TOPICS):
    """All topics as plain text, or "" if Google News could not be reached."""
    parts, seen = [], set()
    for topic, query in topics:
        try:
            rows = [r for r in fetch(query) if r[0].lower() not in seen]
        except Exception as error:      # never let the free feed break an agent
            print(f"Google News headlines failed for {topic}: {error}")
            continue
        seen.update(r[0].lower() for r in rows)
        if rows:
            parts.append(f"{topic}:\n" + "\n".join(f"- {t} ({o}, {w})" for t, o, w in rows))
    return "\n\n".join(parts)


CALENDAR_FEED = "https://nfs.faireconomy.media/ff_calendar_thisweek.xml"
# Which events to show: US events of medium or high impact, and only the
# high-impact ones from these other economies.
CALENDAR_OTHER = {"CAD", "EUR", "GBP", "JPY", "CNY"}
# The feed limits how often it can be fetched ("Too Many Requests"), so the
# week's copy is saved here (the world brief's run commits it) and reused
# while it still covers today: about one fetch a week.
CALENDAR_CACHE = os.path.join("reports", "news", "calendar-cache.xml")


def calendar_xml(today):
    """The week's calendar XML: the saved copy if it covers today, else the feed
    (two tries). Raises if neither works, so callers say it is unavailable
    rather than showing an old week."""
    try:
        with open(CALENDAR_CACHE, "rb") as f:
            saved = f.read()
    except OSError:
        saved = b""
    if f"{today:%m-%d-%Y}".encode() in saved:
        return saved
    for attempt in range(2):
        try:
            request = urllib.request.Request(CALENDAR_FEED, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(request, timeout=20) as response:
                data = response.read()
            os.makedirs(os.path.dirname(CALENDAR_CACHE), exist_ok=True)
            with open(CALENDAR_CACHE, "wb") as f:
                f.write(data)
            return data
        except Exception as error:
            print(f"Economic calendar fetch {attempt + 1} failed: {error}")
            time.sleep(20)
    raise OSError("the feed refused and the saved copy does not cover today")


def calendar_events(today):
    """[(New York datetime or None, currency, title, impact, forecast, previous)]
    for this week. The feed's times are UTC."""
    root = ET.fromstring(calendar_xml(today))
    events = []
    for e in root.findall("event"):
        cur, impact = e.findtext("country") or "", e.findtext("impact") or ""
        if not ((cur == "USD" and impact in ("High", "Medium"))
                or (cur in CALENDAR_OTHER and impact == "High")):
            continue
        day, clock = e.findtext("date") or "", (e.findtext("time") or "").strip()
        try:
            when = datetime.strptime(f"{day} {clock}", "%m-%d-%Y %I:%M%p").replace(tzinfo=timezone.utc)
            when = when.astimezone(ZoneInfo("America/New_York")).replace(tzinfo=None)
        except ValueError:          # "All Day" or "Tentative": keep the date only
            try:
                when = datetime.strptime(day, "%m-%d-%Y")
            except ValueError:
                continue
            clock = clock or "all day"
        events.append((when, clock, cur, e.findtext("title") or "", impact,
                       e.findtext("forecast") or "", e.findtext("previous") or ""))
    return sorted(events, key=lambda ev: ev[0])


def calendar_text(now):
    """Today's and tomorrow's events, then the rest of the week's high-impact
    ones, as plain text in New York time. "" if the feed could not be reached."""
    try:
        events = calendar_events(now.date())
    except Exception as error:      # never let the free feed break an agent
        print(f"Economic calendar failed: {error}")
        return ""
    today, tomorrow = now.date(), now.date() + timedelta(days=1)

    def line(ev):
        when, clock, cur, title, impact, forecast, previous = ev
        at = clock if clock in ("all day", "Tentative") else f"{when:%I:%M %p}".lstrip("0")
        extra = "".join([f", forecast {forecast}" if forecast else "",
                         f", previous {previous}" if previous else ""])
        return f"- {when:%a %b %d} {at} NY | {cur} | {title} | {impact} impact{extra}"

    parts = []
    for label, day in (("TODAY", today), ("TOMORROW", tomorrow)):
        rows = [line(ev) for ev in events if ev[0].date() == day]
        parts.append(f"{label} ({day:%a %b %d}):\n" + ("\n".join(rows) or "- No major events listed."))
    later = [line(ev) for ev in events if ev[0].date() > tomorrow and ev[4] == "High"]
    if later:
        parts.append("LATER THIS WEEK (high impact only):\n" + "\n".join(later))
    return "\n\n".join(parts)


if __name__ == "__main__":
    print(headlines_text() or "No headlines (Google News could not be reached).")
    print()
    print(calendar_text(datetime.now(ZoneInfo("America/New_York")).replace(tzinfo=None))
          or "No calendar (the feed could not be reached).")
