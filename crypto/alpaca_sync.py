"""
alpaca_sync.py - Copies the paper rotation bot into your Alpaca PAPER account.

Run it after crypto_bots.py (the Crypto Bots workflow does this every day):
    python crypto/alpaca_sync.py

crypto_bots.py decides what the rotation bot should hold and saves it in
crypto/paper-targets.json. This script then places real orders in the Alpaca
paper account so its positions match, dollar for dollar, using only a $1,000
slice of the account (the rest of the play money is left alone). You can
watch the positions and orders in the Alpaca app.

Safety:
  - It only ever talks to Alpaca's PAPER address (no real money). It refuses
    to run with live keys (they start with "AK" instead of "PK").
  - It only trades the coins in crypto_bots.COINS, and never more than
    MAX_SLICE dollars in total.
  - Coins Alpaca does not list are skipped and shown on the dashboard.

The keys come from GitHub secrets: ALPACA_KEY_ID and ALPACA_SECRET_KEY (or
both in one secret, ALPADA_API_KEYS, separated by a space or new line).
Without them, it does nothing.
"""

import csv
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from crypto_bots import COINS, DASHBOARD, NEVER_OWN

# ---------------- SETTINGS ----------------
BASE = "https://paper-api.alpaca.markets"     # paper only, on purpose
MAX_SLICE = 1500        # never hold more than this many dollars in the bot's coins
MIN_ORDER = 10          # skip differences smaller than this (dollars)
TARGETS = os.path.join("crypto", "paper-targets.json")
ORDERS_LOG = os.path.join("crypto", "alpaca-orders.csv")
# ------------------------------------------


def request(method, path, body=None):
    key, secret = os.environ.get("ALPACA_KEY_ID"), os.environ.get("ALPACA_SECRET_KEY")
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method, headers={
        "APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret,
        "Content-Type": "application/json", "User-Agent": "ai-trading-agent"})
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            text = response.read().decode()
            return json.loads(text) if text else None
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"Alpaca said {error.code}: {error.read().decode()[:300]}") from None


def money(v):
    return f"-${-v:,.2f}" if v < 0 else f"${v:,.2f}"


def section(lines):
    """Put the Alpaca section into the crypto dashboard."""
    try:
        text = open(DASHBOARD).read()
    except OSError:
        return
    block = "\n".join(["### 🦙 Alpaca paper account (the rotation bot, copied)", ""] + lines + [""])
    open(DASHBOARD, "w").write(text.replace("<!-- ALPACA -->", block, 1))


def log_orders(rows):
    new = not os.path.exists(ORDERS_LOG)
    with open(ORDERS_LOG, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["time_utc", "coin", "side", "dollars", "qty", "status", "order_id"])
        w.writerows(rows)


def split_combined():
    """If both keys were saved in one secret (ALPADA_API_KEYS), split them:
    the part starting with PK is the Key ID, the other part is the secret."""
    parts = os.environ.get("ALPACA_COMBINED", "").replace(",", " ").split()
    key = next((p for p in parts if p.startswith(("PK", "AK"))), None)
    secret = next((p for p in parts if p != key), None)
    if key and secret and not os.environ.get("ALPACA_KEY_ID"):
        os.environ["ALPACA_KEY_ID"], os.environ["ALPACA_SECRET_KEY"] = key, secret


def main():
    split_combined()
    key = os.environ.get("ALPACA_KEY_ID", "")
    if not key or not os.environ.get("ALPACA_SECRET_KEY"):
        found = "one key in ALPADA_API_KEYS but not both" if os.environ.get("ALPACA_COMBINED") else "none"
        print(f"No Alpaca keys found ({found}), so nothing was sent to Alpaca.")
        section(["Not connected yet: add the ALPACA_KEY_ID and ALPACA_SECRET_KEY secrets on GitHub."])
        return
    if not key.startswith("PK"):
        print("These do not look like PAPER keys (paper keys start with PK). Stopping.")
        section(["⚠️ The Alpaca keys on GitHub are not paper keys (they should start with PK), "
                 "so nothing was traded."])
        return

    targets = json.load(open(TARGETS))
    account = request("GET", "/v2/account")
    if account.get("crypto_status") not in (None, "ACTIVE"):
        section([f"⚠️ Crypto trading is not active on this Alpaca account "
                 f"(status: {account.get('crypto_status')}). Nothing was traded."])
        return
    assets = request("GET", "/v2/assets?asset_class=crypto&status=active")
    tradable = {a["symbol"].split("/")[0] for a in assets
                if a.get("tradable") and a["symbol"].endswith("/USD")}
    positions = {p["symbol"].replace("/", "").removesuffix("USD"): p
                 for p in request("GET", "/v2/positions") if p.get("asset_class") == "crypto"}

    wanted = {c: v for c, v in targets["holdings"].items() if c in tradable and c not in NEVER_OWN}
    skipped = sorted(c for c in targets["holdings"] if c not in tradable)
    scale = min(1.0, MAX_SLICE / max(1.0, sum(wanted.values())))
    wanted = {c: v * scale for c, v in wanted.items()}

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    orders, problems = [], []
    for coin in sorted(set(wanted) | {c for c in positions if c in COINS or c in NEVER_OWN}):
        held = float(positions[coin]["market_value"]) if coin in positions else 0.0
        target = wanted.get(coin, 0.0)
        diff = target - held
        if abs(diff) < MIN_ORDER and target > 0:
            continue
        try:
            if target == 0 and coin in positions:          # sell everything
                qty = positions[coin]["qty"]
                o = request("POST", "/v2/orders", {"symbol": f"{coin}/USD", "qty": qty, "side": "sell",
                                                   "type": "market", "time_in_force": "gtc"})
                orders.append([now, coin, "sell", f"{held:.2f}", qty, o.get("status"), o.get("id")])
            elif diff > 0:                                    # buy the difference
                o = request("POST", "/v2/orders", {"symbol": f"{coin}/USD", "notional": f"{diff:.2f}",
                                                   "side": "buy", "type": "market", "time_in_force": "gtc"})
                orders.append([now, coin, "buy", f"{diff:.2f}", "", o.get("status"), o.get("id")])
            elif diff < -MIN_ORDER:                           # sell part
                price = float(positions[coin]["current_price"])
                qty = f"{min(-diff / price, float(positions[coin]['qty'])):.8f}"
                o = request("POST", "/v2/orders", {"symbol": f"{coin}/USD", "qty": qty, "side": "sell",
                                                   "type": "market", "time_in_force": "gtc"})
                orders.append([now, coin, "sell", f"{-diff:.2f}", qty, o.get("status"), o.get("id")])
        except RuntimeError as error:
            problems.append(f"{coin}: {error}")
    if orders:
        log_orders(orders)

    lines = [f"Copies the paper rotation bot's holdings into a real Alpaca **paper** account "
             f"(play money), so you can watch it in the Alpaca app. Updated {now} UTC.", ""]
    if orders:
        lines += [f"**Orders sent today:** " + ", ".join(f"{o[2]} {o[1]} {money(float(o[3]))}" for o in orders), ""]
    else:
        lines += ["**Orders sent today:** none needed.", ""]
    after = {p["symbol"].replace("/", "").removesuffix("USD"): p
             for p in request("GET", "/v2/positions") if p.get("asset_class") == "crypto"}
    mine = {c: p for c, p in after.items() if c in COINS or c in NEVER_OWN}
    if mine:
        lines += ["| Coin | Value in Alpaca | Bot's target | Profit / loss in Alpaca |", "|---|---|---|---|"]
        for c, p in sorted(mine.items()):
            lines.append(f"| {c} | {money(float(p['market_value']))} | {money(wanted.get(c, 0))} | "
                         f"{money(float(p['unrealized_pl']))} |")
        lines.append("")
    else:
        lines += ["No coins held in Alpaca right now (matches the bot holding cash or orders still filling).", ""]
    if skipped:
        lines += [f"Alpaca does not list {', '.join(skipped)}, so those stay as cash in Alpaca. "
                  "This is why Alpaca can differ from the bot.", ""]
    if problems:
        lines += ["⚠️ Problems: " + "; ".join(problems), ""]
    lines += ["[Every Alpaca order (CSV)](crypto/alpaca-orders.csv)"]
    section(lines)
    print(f"Alpaca: {len(orders)} order(s) sent, {len(problems)} problem(s), skipped {skipped}")
    sys.path.insert(0, os.path.join(os.path.dirname(HERE), "agents"))
    from notify import send
    if orders:
        send("Alpaca orders sent", ", ".join(f"{o[2]} {o[1]} {money(float(o[3]))}" for o in orders),
             tags="moneybag")
    if problems:
        send("Alpaca problem", "\n".join(problems[:3]), priority="high", tags="warning")
    if problems:
        print("\n".join(problems))


if __name__ == "__main__":
    main()
