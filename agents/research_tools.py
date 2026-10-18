"""
research_tools.py - Shared helper for the research agents (world news, crypto,
stocks). It makes one AI call, optionally with web search, and keeps going if
a long search session pauses.

This file is not an agent and does nothing on its own.
"""

MODEL = "claude-sonnet-5-5"

# Prices used to estimate each run's cost (dollars). Check anthropic.com/pricing.
PRICE_IN, PRICE_OUT = 2.00 / 1e6, 10.00 / 1e6    # per token, Claude Sonnet 5.5
PRICE_SEARCH = 10.00 / 1000                       # per web search

SPENT = {"in": 0, "out": 0, "searches": 0}        # running total for this run


def estimated_cost():
    """Dollars spent so far in this run, from the token and search counts."""
    return (SPENT["in"] * PRICE_IN + SPENT["out"] * PRICE_OUT
            + SPENT["searches"] * PRICE_SEARCH)


def log_cost(agent, tokens_in=None, tokens_out=None, searches=None):
    """Add this run's cost to reports/costs/<agent>.csv (one file per agent, so
    agents running at the same time never clash). Uses this run's running
    totals unless numbers are passed in. Returns the cost in dollars."""
    import csv
    import os
    from datetime import datetime, timezone
    tokens_in = SPENT["in"] if tokens_in is None else tokens_in
    tokens_out = SPENT["out"] if tokens_out is None else tokens_out
    searches = SPENT["searches"] if searches is None else searches
    cost = tokens_in * PRICE_IN + tokens_out * PRICE_OUT + searches * PRICE_SEARCH
    folder = os.path.join("reports", "costs")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, f"{agent}.csv")
    new = not os.path.exists(path)
    with open(path, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["time_utc", "agent", "tokens_in", "tokens_out", "searches", "cost_usd"])
        w.writerow([datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"), agent,
                    tokens_in, tokens_out, searches, f"{cost:.4f}"])
    return cost


def run_call(client, prompt, use_search, max_searches=5, max_tokens=3500, model=MODEL,
             effort=None):
    """One AI call. Returns (text, input_tokens, output_tokens, was_cut_off).
    effort: "low", "medium" or "high" (None = the model's default). Lower
    effort means less thinking and fewer searches, so it costs less."""
    messages = [{"role": "user", "content": prompt}]
    extra = {"output_config": {"effort": effort}} if effort else {}
    if use_search:
        extra["tools"] = [{
            "type": "web_search_20260209",
            "name": "web_search",
            "max_uses": max_searches,
        }]

    tokens_in = tokens_out = 0
    response = None
    for _ in range(5):   # a long search session can pause; keep going
        response = client.messages.create(
            model=model, max_tokens=max_tokens, messages=messages, **extra)
        tokens_in += response.usage.input_tokens
        tokens_out += response.usage.output_tokens
        tool_use = getattr(response.usage, "server_tool_use", None)
        SPENT["searches"] += getattr(tool_use, "web_search_requests", 0) or 0
        if response.stop_reason != "pause_turn":
            break
        messages.append({"role": "assistant", "content": response.content})

    SPENT["in"] += tokens_in
    SPENT["out"] += tokens_out
    text = "".join(b.text for b in response.content if b.type == "text").strip()
    if response.stop_reason == "refusal":
        text = text or "(The AI declined to write this part.)"
    return text, tokens_in, tokens_out, response.stop_reason == "max_tokens"


def research_parts(client, parts, values, max_searches, max_tokens):
    """Run each (label, prompt template) with web search.
    Returns (list of texts, total_in, total_out)."""
    texts, total_in, total_out = [], 0, 0
    for label, template in parts:
        text, t_in, t_out, cut = run_call(
            client, template.format(**values), use_search=True,
            max_searches=max_searches, max_tokens=max_tokens)
        total_in += t_in
        total_out += t_out
        if not text:
            text = f"(This part could not be written: no text came back for {label}.)"
        elif cut:
            text += "\n\n(This part was cut off because it hit the length limit.)"
        texts.append(text)

    if all(t.startswith("(This part could not be written") for t in texts):
        raise SystemExit("No research call returned any text, so nothing was saved.")
    return texts, total_in, total_out


def write_summary(client, prompt, max_tokens):
    """The short no-search summary call. Never raises.
    Returns (text, tokens_in, tokens_out)."""
    try:
        text, t_in, t_out, _ = run_call(client, prompt, use_search=False,
                                        max_tokens=max_tokens)
        return text or "(The summary could not be written. See the details below.)", t_in, t_out
    except Exception as error:
        return f"(The summary could not be written: {error}. See the details below.)", 0, 0
