# Evidence Research Agent

A small tool-calling agent that researches a list of stock tickers and
decides, on its own, when it has enough source material to report a
finding -- rather than just running one fixed classification call per
ticker.

## Why this exists

This started as a gap I noticed in a larger project of mine, a
wealth-planning platform (see `evidence.py` there): it has a
schema-validated evidence extractor that pulls sentiment and event tags
out of text, but nothing downstream ever calls it. I wanted to see what
actually wiring that into a live research workflow looks like, as a
separate, focused piece of work rather than bolting it onto the
optimizer.

The same rule carries over: this agent characterizes sentiment and
event type, and that's it. `submit_portfolio_report`'s schema has no
field for a price target, an expected return, or a probability. If a
real number is ever needed, it comes from an actual pricing model, not
from an LLM's own judgment -- enforced here by the tool schema itself,
not just a prompt instruction.

## What makes it an agent, not just a wrapped API call

For each ticker, the loop:
1. Calls `fetch_snippets` to pull source text.
2. Judges whether that first batch is thin or one-sided. If so, it
   calls `request_additional_research` with its reasoning, then
   `fetch_snippets` again -- which returns a second, deeper batch.
3. Moves on once satisfied.

Whether it asks for that second pass is the model's own call per
ticker, not a scripted step. `sample_run.txt` is an actual run: AAPL's
first batch was enough on its own, but it flagged both NVDA (sources
were vague) and JPM (sources disagreed with each other) for a second
pass, gave real reasons for each, and only then reported.

## Running it

```
pip install -r requirements.txt
export GEMINI_API_KEY=...
python3 agent.py AAPL NVDA JPM
```

Get a free key at aistudio.google.com -- no card required. Runs on
`gemini-3.1-flash-lite`.

## What's real here and what isn't

The source snippets in `snippets.py` are illustrative sample text I
wrote, not live news or real filings -- there's no web-search tool
wired in. The agent loop itself, the tool schemas, and the decision
behavior around the second research pass are real: `sample_run.txt` is
an unedited transcript of an actual run against the live API.

## Implementation notes

Built as a manual tool-calling loop against the Gemini REST API
directly (`requests.post` in a `while True:`), rather than a
higher-level agent framework -- for a project this scoped, writing the
loop by hand means there's nothing happening that isn't visible in
`agent.py`. One real wrinkle hit while building this: Gemini's
function-call responses carry a `thoughtSignature` that must be echoed
back unchanged when you replay the model's turn in the next request, or
it rejects the call -- found by testing against the live API, not from
documentation, since the official docs site wasn't reachable from where
this was built. `agent.py` handles it by replaying the model's response
`parts` verbatim rather than reconstructing them.
