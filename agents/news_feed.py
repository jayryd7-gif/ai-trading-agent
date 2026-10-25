"""
news_feed.py - Free headlines from Google News (RSS, no key, no cost).

    from news_feed import headlines_text
    print(headlines_text())

Used as a safety net so politics and world news are never empty: the world
brief gets these headlines as leads (and can report them if its web search
fails), and the X drafts agent uses them as its last fallback. Headlines only:
a headline plus its outlet and time, no article text.

This file is not an agent and does nothing on its own.
"""

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


def headlines_text():
    """All topics as plain text, or "" if Google News could not be reached."""
    parts, seen = [], set()
    for topic, query in TOPICS:
        try:
            rows = [r for r in fetch(query) if r[0].lower() not in seen]
        except Exception as error:      # never let the free feed break an agent
            print(f"Google News headlines failed for {topic}: {error}")
            continue
        seen.update(r[0].lower() for r in rows)
        if rows:
            parts.append(f"{topic}:\n" + "\n".join(f"- {t} ({o}, {w})" for t, o, w in rows))
    return "\n\n".join(parts)


if __name__ == "__main__":
    print(headlines_text() or "No headlines (Google News could not be reached).")
