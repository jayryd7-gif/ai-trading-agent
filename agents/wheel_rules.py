"""
wheel_rules.py - The options wheel rules and settings, shared by the backtest
(experiments/wheel_backtest.py) and the paper trader (agents/wheel_trader.py).

Research behind every rule: experiments/wheel-strategy-research.md
"""

import math
from statistics import NormalDist

# ---------------- ACCOUNT ----------------
START_CAD = 10_000.0      # paper account size in Canadian dollars
MAX_POSITIONS = 4         # up to 4 different stocks at once
MAX_PER_STOCK = 0.25      # one stock (strike x 100) may tie up at most 25% of the account
MIN_PRICE = 5.0           # skip very cheap stocks

# ---------------- TRADE RULES ----------------
TARGET_DELTA = 0.30       # sell about a 0.30 delta put / call
DTE_MIN, DTE_MAX, DTE_IDEAL = 30, 50, 42
TAKE_PROFIT = 0.50        # buy back at 50% of the credit
TIME_EXIT_DTE = 21        # at 21 days left: close if out of the money, else hold for assignment
# Filters tested in experiments/wheel_backtest.py (2026-11-14). Over the last 30, 60
# and 90 days neither helped (version A, no filters, lost least), so both start OFF.
USE_TREND_FILTER = False
TREND_DAYS = 50           # trend filter: only sell puts above the 50-day average
USE_IV_CAP = False
MAX_IV = 0.80             # IV cap: skip stocks priced for wild moves
MIN_CREDIT = 0.10         # skip options that pay less than $10 a contract
FEE = 0.65                # per contract, per side
MIN_OPEN_INTEREST = 100
MAX_SPREAD = 0.20         # bid/ask spread at most 20% of the mid price (or 10 cents for cheap options)

# Liquid stocks with weekly/monthly options. Ones priced too high for a 25%
# slot are skipped automatically (strike x 100 must fit).
UNIVERSE = ["F", "VALE", "ITUB", "NU", "AAL", "RIVN", "SOFI", "SNAP", "RIG",
            "T", "PFE", "KMI", "CCL", "HPE", "KEY", "PCG", "KHC", "CMCSA"]

RATE = 0.04
N = NormalDist()


def bs_price(S, K, T, vol, kind):
    T = max(T, 1 / 365)
    vol = max(vol, 0.05)
    d1 = (math.log(S / K) + (RATE + vol * vol / 2) * T) / (vol * math.sqrt(T))
    d2 = d1 - vol * math.sqrt(T)
    if kind == "put":
        return K * math.exp(-RATE * T) * N.cdf(-d2) - S * N.cdf(-d1)
    return S * N.cdf(d1) - K * math.exp(-RATE * T) * N.cdf(d2)


def bs_delta(S, K, T, vol, kind):
    T = max(T, 1 / 365)
    vol = max(vol, 0.05)
    d1 = (math.log(S / K) + (RATE + vol * vol / 2) * T) / (vol * math.sqrt(T))
    return N.cdf(d1) - 1 if kind == "put" else N.cdf(d1)


def strike_for_delta(S, T, vol, kind, delta=TARGET_DELTA):
    d1 = N.inv_cdf(1 - delta if kind == "put" else delta)
    K = S * math.exp(-(d1 * vol * math.sqrt(T) - (RATE + vol * vol / 2) * T))
    step = 0.5 if S < 25 else 1.0
    return round(K / step) * step


def slot_size(equity):
    """Most cash one stock may tie up."""
    return equity * MAX_PER_STOCK


# ---------------- PAPER ACCOUNTS ----------------
# Two paper accounts run side by side so they can be compared:
#   ours  - the rules above, $10K CAD, cheaper stocks
#   ryan  - Options With Ryan's wheel (as summarized from his CRDO wheel video,
#           see experiments/wheel-strategy-research.md), pretend $200K USD, his stocks
ACCOUNTS = {
    "ours": {
        "title": "Wheel paper account ($10K CAD)", "short": "Wheel",
        "folder": "paper-trading/wheel", "start_cad": START_CAD, "start_usd": None, "currency": "CAD",
        "universe": UNIVERSE, "max_pos": MAX_POSITIONS, "slot": MAX_PER_STOCK, "cash_reserve": 0.0,
        "min_price": MIN_PRICE, "delta": TARGET_DELTA,
        "put_dte": (DTE_MIN, DTE_MAX, DTE_IDEAL), "call_dte": (DTE_MIN, DTE_MAX, DTE_IDEAL),
        "prefer_monthly": True, "tp": TAKE_PROFIT, "time_exit": TIME_EXIT_DTE,
        "trend_days": TREND_DAYS if USE_TREND_FILTER else None, "uptrend_days": None,
        "min_yield30": 0.0, "max_pe": None, "iv_cap": MAX_IV if USE_IV_CAP else None,
        "skip_earnings": True, "multi_contracts": False,   # 1 contract per stock, as backtested
    },
    "ryan": {
        "title": "Ryan-style wheel paper account ($200K USD)", "short": "Ryan wheel",
        "folder": "paper-trading/wheel-ryan", "start_cad": None, "start_usd": 200_000.0, "currency": "USD",
        "universe": ["CRDO", "NVDA", "HOOD", "BE", "PLTR", "AMD"],
        "max_pos": 8, "slot": 0.10,            # about 10% of the account per company (several contracts)
        "cash_reserve": 0.20,                  # keep about 20% cash
        "min_price": 5.0, "delta": 0.28,       # puts about 0.25-0.30 delta
        "put_dte": (25, 35, 30), "call_dte": (15, 25, 21),
        "prefer_monthly": False,
        "tp": 0.20,                            # buy back at about 80% profit
        "time_exit": None,                     # no 21-day exit: hold or take 80%
        "trend_days": None, "uptrend_days": 548,   # up over about 1.5 years
        "min_yield30": 0.025,                  # at least about 2.5% premium per 30 days
        "max_pe": 100,                         # positive P/E under 100
        "iv_cap": None,
        "multi_contracts": True,
        "skip_earnings": False,                # his earnings rule isn't stated, so this account doesn't skip them
    },
}
