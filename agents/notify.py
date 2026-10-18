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
