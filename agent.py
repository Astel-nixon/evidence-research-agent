"""Evidence research agent.

Given a list of portfolio holdings, the agent decides for itself, ticker
by ticker, how much source material it needs before it is willing to
report a finding: it calls fetch_snippets, judges whether that first
batch is thin, optionally calls request_additional_research to pull a
second batch, and only then calls submit_portfolio_report to finish.
That decision loop -- not just the act of calling a tool -- is what
makes this an agent rather than a single classification call.

The one rule carried over from the larger wealth-planning project this
agent supports: it is allowed to characterize sentiment and flag event
types, never to invent a number. submit_portfolio_report's schema has
no field for a price target, an expected return, or a probability --
on purpose. If it ever needs those, they come from an actual pricing
model downstream, not from this agent's own judgment.

Usage:
    export GEMINI_API_KEY=...
    python3 agent.py AAPL NVDA JPM
"""

import json
import os
import sys

import requests

from snippets import SNIPPETS

MODEL = "gemini-3.1-flash-lite"
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"

SYSTEM_PROMPT = """You are a research assistant that gathers evidence on \
stocks held in a client's portfolio, for a human investment reviewer to \
read alongside a separately computed, numeric portfolio recommendation.

For each ticker you are given:
1. Call fetch_snippets to pull source text.
2. Decide whether that first batch is enough to characterize sentiment \
and event type with reasonable confidence. A single vague snippet, or \
sources that disagree with each other, is not enough on its own -- if \
that's what you get, call request_additional_research with your reason, \
then call fetch_snippets again for a second pass.
3. Once you are satisfied, move to the next ticker.

When every ticker is covered, call submit_portfolio_report exactly once \
with your findings for all of them.

Hard rule: you characterize sentiment and event type only. Never state or \
imply a price target, an expected return, or a numeric probability -- that \
is not your job and this schema has no field for it."""

TOOLS = [{
    "functionDeclarations": [
        {
            "name": "fetch_snippets",
            "description": (
                "Fetch source text for a ticker. The first call returns an "
                "initial batch. If request_additional_research has already "
                "been called for that ticker, this returns a second, deeper "
                "batch instead."
            ),
            "parameters": {
                "type": "object",
                "properties": {"ticker": {"type": "string"}},
                "required": ["ticker"],
            },
        },
        {
            "name": "request_additional_research",
            "description": "Flag that the first batch of sources for a ticker was not enough.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string"},
                    "reason": {"type": "string"},
                },
                "required": ["ticker", "reason"],
            },
        },
        {
            "name": "submit_portfolio_report",
            "description": "Submit final findings for every ticker. Ends the run.",
            "parameters": {
                "type": "object",
                "properties": {
                    "holdings": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "ticker": {"type": "string"},
                                "event_type": {
                                    "type": "string",
                                    "enum": ["earnings", "regulatory", "supply_chain", "macro", "other"],
                                },
                                "sentiment": {
                                    "type": "string",
                                    "enum": ["positive", "negative", "neutral", "mixed"],
                                },
                                "confidence": {
                                    "type": "string",
                                    "enum": ["low", "medium", "high"],
                                },
                                "needed_second_pass": {"type": "boolean"},
                                "summary": {"type": "string"},
                            },
                            "required": [
                                "ticker", "event_type", "sentiment",
                                "confidence", "needed_second_pass", "summary",
                            ],
                        },
                    },
                },
                "required": ["holdings"],
            },
        },
    ]
}]


def fetch_snippets(ticker, deep_flags):
    bucket = SNIPPETS.get(ticker.upper())
    if bucket is None:
        return {"error": f"no sources on file for {ticker}"}
    key = "deep" if ticker.upper() in deep_flags else "initial"
    return {"ticker": ticker.upper(), "batch": key, "snippets": bucket[key]}


def request_additional_research(ticker, reason, deep_flags):
    deep_flags.add(ticker.upper())
    return {"ack": f"noted -- next fetch_snippets({ticker.upper()}) will return the deeper batch. reason: {reason}"}


def call_gemini(contents, api_key):
    resp = requests.post(
        API_URL,
        headers={"Content-Type": "application/json", "X-goog-api-key": api_key},
        json={
            "contents": contents,
            "tools": TOOLS,
            "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        },
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()


def run(tickers):
    api_key = os.environ["GEMINI_API_KEY"]
    deep_flags = set()
    contents = [{
        "role": "user",
        "parts": [{"text": "Research these holdings and report your findings: " + ", ".join(tickers)}],
    }]

    while True:
        data = call_gemini(contents, api_key)
        candidate = data["candidates"][0]
        parts = candidate["content"]["parts"]
        print(f"\n--- turn (finishReason={candidate.get('finishReason')}) ---")

        function_calls = [p for p in parts if "functionCall" in p]
        for p in parts:
            if "text" in p and p["text"].strip():
                print(f"[text] {p['text'].strip()}")

        submit_part = next((p for p in function_calls if p["functionCall"]["name"] == "submit_portfolio_report"), None)
        if submit_part is not None:
            print("[functionCall] submit_portfolio_report -- ending run")
            return submit_part["functionCall"]["args"]

        if not function_calls:
            raise RuntimeError(f"agent stopped without submitting a report (finishReason={candidate.get('finishReason')})")

        # replay the model's turn exactly, thoughtSignature included -- Gemini
        # rejects a functionCall replayed without it.
        contents.append({"role": "model", "parts": parts})

        response_parts = []
        for p in function_calls:
            call = p["functionCall"]
            name, args, call_id = call["name"], call.get("args", {}), call.get("id")
            print(f"[functionCall] {name}({json.dumps(args)})")
            if name == "fetch_snippets":
                result = fetch_snippets(args["ticker"], deep_flags)
            elif name == "request_additional_research":
                result = request_additional_research(args["ticker"], args["reason"], deep_flags)
            else:
                result = {"error": f"unknown function {name}"}
            response_parts.append({"functionResponse": {"name": name, "id": call_id, "response": result}})

        contents.append({"role": "function", "parts": response_parts})


if __name__ == "__main__":
    tickers = sys.argv[1:] or ["AAPL", "NVDA", "JPM"]
    report = run(tickers)
    print("\n=== final report ===")
    print(json.dumps(report, indent=2))
