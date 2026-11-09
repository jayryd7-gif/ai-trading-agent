"""
notify.py - Sends a push notification to your phone (free, through ntfy.sh).

    from notify import send
    send("Nasdaq paper trade closed", "Long, +$660 after fees", priority="high", tags="chart")

Your phone gets it through the free ntfy app, subscribed to your private
topic name. The topic name comes from the NTFY_TOPIC secret on GitHub. If it
is not set, nothing is sent and nothing breaks.

Priorities: "min", "low", "default", "high", "urgent". Tags become emoji
in the app (for example "white_check_mark", "x", "warning", "money_with_wings").
"""

import os
import urllib.request

SERVER = "https://ntfy.sh/"


def send(title, message, priority="default", tags="", link=None):
    topic = os.environ.get("NTFY_TOPIC", "").strip()
    if not topic:
        return False
    headers = {"Title": title.encode("utf-8").decode("latin-1", "ignore") or "Agent update",
               "Priority": priority, "Tags": tags}
    if link:
        headers["Click"] = link
    request = urllib.request.Request(SERVER + topic, data=message.encode("utf-8"),
                                     headers=headers, method="POST")
    try:
        urllib.request.urlopen(request, timeout=15)
        return True
    except Exception as error:      # a failed alert must never break an agent
        print(f"Phone alert not sent: {error}")
        return False


# ntfy cuts a message at 4,096 bytes, so the phone version stops a bit before that.
PHONE_LIMIT = 3500


def plain(markdown):
    """Turns brief markdown into easy-to-read phone text."""
    import re
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", markdown)          # bold
    text = re.sub(r"(?<!\w)\*(?!\s)(.+?)\*", r"\1", text)      # italics
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)       # links -> just the words
    text = re.sub(r"^#+\s*", "", text, flags=re.M)             # headings
    text = re.sub(r"^\s*[-*]\s+", "• ", text, flags=re.M)      # bullets
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def brief_section(text, start, stop=r"^## |^\*\*\d+\.|^---"):
    """The part of a brief from the line matching `start` up to the next heading."""
    import re
    found = re.search(start, text, re.M)
    if not found:
        return ""
    rest = text[found.end():]
    end = re.search(stop, rest, re.M)
    return rest[:end.start()] if end else rest


def send_brief(title, path, sections, tags="newspaper", priority="default"):
    """Sends the key parts of a new brief to your phone, so you can read it right
    in the notification. Tap the notification to open the full brief on GitHub.

    sections: list of (label, start_regex). Each found section is added in order."""
    try:
        with open(path) as f:
            text = f.read()
    except OSError:
        return False
    parts = []
    for label, start in sections:
        chunk = plain(brief_section(text, start))
        if chunk:
            parts.append((label.upper() + "\n" if label else "") + chunk)
    message = "\n\n".join(parts) or "A new brief is ready. Tap to read it."
    if len(message.encode("utf-8")) > PHONE_LIMIT:
        message = message.encode("utf-8")[:PHONE_LIMIT].decode("utf-8", "ignore")
        message = message.rsplit("\n", 1)[0] + "\n\n… tap to read the rest."
    link = f"https://github.com/jayryd7-gif/ai-trading-agent/blob/main/{path}"
    return send(title, message, priority=priority, tags=tags, link=link)
